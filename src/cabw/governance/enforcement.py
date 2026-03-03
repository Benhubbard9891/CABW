"""
Governance Enforcement Layer

Structural enforcement of constitutional constraints.
No action executes without an ExecutionToken issued by the Governor.
"""

import hashlib
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto
from typing import Any
from uuid import uuid4

from .security import AccessDecision, Capability, SecurityContext, SecurityGovernor


class ExecutionStatus(Enum):
    """Status of action execution."""
    PENDING = auto()
    AUTHORIZED = auto()
    EXECUTING = auto()
    COMPLETED = auto()
    REVOKED = auto()
    DENIED = auto()


@dataclass(frozen=True)
class ExecutionToken:
    """
    Immutable token authorizing a single action execution.
    Cannot be forged, cannot be reused.
    """
    token_id: str
    action_id: str
    agent_id: str
    capability: Capability
    issued_at: str
    expires_at: str
    audit_id: str
    constraints: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        # Validate token integrity
        if not self.token_id or not self.audit_id:
            raise ValueError("Invalid token: missing required fields")

    def to_dict(self) -> dict[str, Any]:
        return {
            'token_id': self.token_id,
            'action_id': self.action_id,
            'agent_id': self.agent_id,
            'capability': self.capability.name,
            'issued_at': self.issued_at,
            'expires_at': self.expires_at,
            'audit_id': self.audit_id,
            'constraints': self.constraints
        }

    def verify(self, action_id: str, agent_id: str) -> bool:
        """Verify token matches action and agent."""
        return self.action_id == action_id and self.agent_id == agent_id


@dataclass
class ExecutionReceipt:
    """Receipt of completed action execution."""
    token_id: str
    action_id: str
    agent_id: str
    started_at: str
    completed_at: str
    success: bool
    result: Any
    side_effects: list[str] = field(default_factory=list)

    def hash(self) -> str:
        """Generate tamper-evident hash."""
        data = f"{self.token_id}:{self.action_id}:{self.started_at}:{self.completed_at}:{self.success}"
        return hashlib.sha256(data.encode()).hexdigest()[:16]


class ActionBudget:
    """
    Budget manager for agent actions.
    All actions must commit through here.
    Structural enforcement: no token = no execution.
    """

    def __init__(
        self,
        governor: SecurityGovernor,
        max_concurrent: int = 100,
        default_ttl_seconds: int = 30
    ):
        self.governor = governor
        self.max_concurrent = max_concurrent
        self.default_ttl = default_ttl_seconds

        # Active tokens
        self._active_tokens: dict[str, ExecutionToken] = {}
        self._executing: dict[str, datetime] = {}
        self._receipts: dict[str, ExecutionReceipt] = {}

        # Penalty callbacks
        self._on_denial: Callable[[Any, str], None] | None = None

        # Statistics
        self.stats = {
            'tokens_issued': 0,
            'tokens_revoked': 0,
            'executions_completed': 0,
            'denials': 0,
            'violations_attempted': 0
        }

    def set_denial_callback(self, callback: Callable[[Any, str], None]):
        """Set callback for when action is denied."""
        self._on_denial = callback

    def commit(
        self,
        action,
        agent,
        context: SecurityContext | None = None
    ) -> ExecutionToken | None:
        """
        Request execution token for action.
        Returns None if denied.
        This is the ONLY path to authorized execution.
        """
        # Check concurrent limit
        if len(self._active_tokens) >= self.max_concurrent:
            self._penalize_pad(agent, "System at capacity")
            return None

        # Evaluate through governor
        ctx_dict = (context.to_dict() if isinstance(context, SecurityContext) else context) or {
            'action': getattr(action, 'name', 'unknown'),
        }
        decision = self.governor.evaluate_access(
            subject={'id': getattr(agent, 'agent_id', 'unknown'), 'type': 'agent'},
            resource={'id': getattr(action, 'action_id', 'unknown'), 'type': 'action'},
            capability=getattr(action, 'required_capability', Capability.ACTION_EXECUTE),
            context=ctx_dict,
        )

        if not decision.granted:
            self.stats['denials'] += 1
            self._penalize_pad(agent, decision.reason)
            return None

        # Issue token — use uuid4 to prevent timestamp-based collisions
        now = datetime.now()
        import datetime as _dt
        token = ExecutionToken(
            token_id=f"tok_{uuid4().hex}",
            action_id=getattr(action, 'action_id', 'unknown'),
            agent_id=getattr(agent, 'agent_id', 'unknown'),
            capability=Capability.ACTION_EXECUTE,
            issued_at=now.isoformat(),
            expires_at=(now + _dt.timedelta(seconds=self.default_ttl)).isoformat(),
            audit_id=self.governor.audit_log[-1].id if self.governor.audit_log else 'none',
            constraints=getattr(action, 'constraints', {})
        )

        self._active_tokens[token.token_id] = token
        self.stats['tokens_issued'] += 1

        return token

    def execute(
        self,
        token: ExecutionToken,
        action_func: Callable,
        *args,
        **kwargs
    ) -> ExecutionReceipt:
        """
        Execute action with token.
        Token is consumed (cannot be reused).
        """
        # Verify token is active
        if token.token_id not in self._active_tokens:
            self.stats['violations_attempted'] += 1
            raise SecurityViolation(
                f"Invalid or expired token: {token.token_id}",
                agent_id=token.agent_id
            )

        # Remove from active (single use)
        del self._active_tokens[token.token_id]
        self._executing[token.token_id] = datetime.now()

        # Execute
        started = datetime.now()
        try:
            result = action_func(*args, **kwargs)
            success = True
            side_effects = []
        except Exception as e:
            result = str(e)
            success = False
            side_effects = [f"exception:{type(e).__name__}"]

        completed = datetime.now()
        del self._executing[token.token_id]

        # Create receipt
        receipt = ExecutionReceipt(
            token_id=token.token_id,
            action_id=token.action_id,
            agent_id=token.agent_id,
            started_at=started.isoformat(),
            completed_at=completed.isoformat(),
            success=success,
            result=result,
            side_effects=side_effects
        )

        self._receipts[receipt.token_id] = receipt
        self.stats['executions_completed'] += 1

        return receipt

    def _penalize_pad(self, agent, reason: str):
        """Apply PAD penalty for denied action."""
        # Trigger denial callback
        if self._on_denial:
            self._on_denial(agent, reason)

        # Apply emotional penalty
        if hasattr(agent, 'emotional_state'):
            from ..core.emotions import EmotionType
            agent.emotional_state.apply_stimulus(EmotionType.ANGER, 0.1)
            agent.emotional_state.apply_stimulus(EmotionType.FRUSTRATION, 0.15)

        # Log to agent memory
        if hasattr(agent, 'memory'):
            agent.memory.add_experience({
                'type': 'action_denied',
                'reason': reason,
                'timestamp': datetime.now().isoformat()
            }, importance=0.6)

    def revoke(self, token_id: str, reason: str) -> bool:
        """Revoke an active token."""
        if token_id in self._active_tokens:
            del self._active_tokens[token_id]
            self.stats['tokens_revoked'] += 1

            # Route through governor._audit() so threat detection runs and
            # the hash chain is maintained — do NOT append directly to audit_log.
            self.governor._audit(
                subject={'id': 'system', 'type': 'system', 'name': 'enforcement'},
                resource={'id': token_id, 'type': 'token'},
                capability=Capability.ACTION_EXECUTE,
                decision=AccessDecision(granted=False, reason=reason),
                context={'action': 'revoke_token'},
            )
            return True
        return False

    def get_active_count(self) -> int:
        """Get number of active tokens."""
        return len(self._active_tokens)

    def get_receipt(self, token_id: str) -> ExecutionReceipt | None:
        """Get execution receipt."""
        return self._receipts.get(token_id)

    def cleanup_expired(self):
        """Remove expired tokens."""
        now = datetime.now()
        expired = []

        for token_id, token in self._active_tokens.items():
            expires = datetime.fromisoformat(token.expires_at)
            if now > expires:
                expired.append(token_id)

        for token_id in expired:
            del self._active_tokens[token_id]
            self.stats['tokens_revoked'] += 1


class SecurityViolation(Exception):
    """Exception for security violations."""

    def __init__(self, message: str, agent_id: str):
        super().__init__(message)
        self.agent_id = agent_id
        self.timestamp = datetime.now().isoformat()


class ConstitutionalLayer:
    """
    Top-level constitutional enforcement.
    Wraps all governance components.
    """

    def __init__(self):
        self.governor = SecurityGovernor()
        self.budget = ActionBudget(self.governor)

        # Constitutional invariants
        self.invariants: list[Callable[[Any, Any, Any], tuple[bool, str]]] = []

        # Violation handlers
        self._on_violation: Callable[[SecurityViolation], None] | None = None

    def add_invariant(
        self,
        invariant: Callable[[Any, Any, Any], tuple[bool, str]]
    ):
        """Add constitutional invariant."""
        self.invariants.append(invariant)

    def set_violation_handler(self, handler: Callable[[SecurityViolation], None]):
        """Set handler for security violations."""
        self._on_violation = handler

    def check_invariants(
        self,
        agent,
        action,
        context
    ) -> tuple[bool, str | None]:
        """Check all constitutional invariants."""
        for invariant in self.invariants:
            passed, reason = invariant(agent, action, context)
            if not passed:
                return False, reason
        return True, None

    def execute(
        self,
        agent,
        action,
        action_func: Callable,
        *args,
        **kwargs
    ) -> ExecutionReceipt | None:
        """
        Execute action through constitutional layer.
        Checks invariants, gets token, executes.
        """
        # Check invariants
        invariants_pass, reason = self.check_invariants(agent, action, kwargs.get('context'))
        if not invariants_pass:
            if self._on_violation:
                self._on_violation(SecurityViolation(reason, agent.agent_id))
            return None

        # Get execution token
        token = self.budget.commit(action, agent, kwargs.get('context'))
        if not token:
            return None

        # Execute
        try:
            receipt = self.budget.execute(token, action_func, *args, **kwargs)
            return receipt
        except SecurityViolation as e:
            if self._on_violation:
                self._on_violation(e)
            return None

    def get_audit_trail(self, agent_id: str | None = None) -> list[dict]:
        """Get audit trail, optionally filtered by agent."""
        records = []

        # Governor audit log
        for record in self.governor.audit_log:
            if agent_id is None or record.subject_id == agent_id:
                records.append({
                    'source': 'governor',
                    'record': record.to_dict()
                })

        # Budget receipts
        for receipt in self.budget._receipts.values():
            if agent_id is None or receipt.agent_id == agent_id:
                records.append({
                    'source': 'budget',
                    'receipt': receipt.__dict__
                })

        # Sort by timestamp
        records.sort(key=lambda x:
            x.get('record', {}).get('timestamp', '') or
            x.get('receipt', {}).get('started_at', '')
        )

        return records
