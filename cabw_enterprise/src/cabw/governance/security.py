"""
Security-First Governance System for CABW Enterprise.

Implements:
- Capability-based access control (PBAC)
- Security clearance levels
- Audit logging
- Threat detection
- Compliance enforcement
"""

from __future__ import annotations

import hashlib
import hmac
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum, auto
from typing import Any, Dict, List, Optional, Set, Tuple
from uuid import UUID, uuid4

from cabw.utils.logging import get_logger

logger = get_logger(__name__)


class SecurityLevel(Enum):
    """Security clearance levels."""
    PUBLIC = 0
    INTERNAL = 1
    CONFIDENTIAL = 2
    SECRET = 3
    TOP_SECRET = 4


class Capability(Enum):
    """System capabilities that can be granted."""
    # Generic capability aliases (used by API/auth integration)
    READ = "read"
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    EXECUTE = "execute"
    ADMIN = "admin"

    # Agent capabilities
    AGENT_CREATE = "agent:create"
    AGENT_READ = "agent:read"
    AGENT_UPDATE = "agent:update"
    AGENT_DELETE = "agent:delete"
    AGENT_CONTROL = "agent:control"
    
    # Simulation capabilities
    SIM_CREATE = "sim:create"
    SIM_READ = "sim:read"
    SIM_UPDATE = "sim:update"
    SIM_DELETE = "sim:delete"
    SIM_START = "sim:start"
    SIM_STOP = "sim:stop"
    
    # World capabilities
    WORLD_CREATE = "world:create"
    WORLD_READ = "world:read"
    WORLD_UPDATE = "world:update"
    WORLD_DELETE = "world:delete"
    
    # Governance capabilities
    GOV_READ = "gov:read"
    GOV_MODIFY = "gov:modify"
    GOV_AUDIT = "gov:audit"
    
    # Admin capabilities
    ADMIN_USERS = "admin:users"
    ADMIN_SYSTEM = "admin:system"
    ADMIN_SECURITY = "admin:security"


class ThreatLevel(Enum):
    """Threat assessment levels."""
    NONE = 0
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4


@dataclass
class SecurityContext:
    """Context for security policy evaluation."""
    subject_id: str
    resource_id: str
    action: str
    security_level: SecurityLevel = SecurityLevel.PUBLIC
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    session_id: Optional[str] = None
    request_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary expected by the policy engine."""
        context = {
            'subject_id': self.subject_id,
            'resource_id': self.resource_id,
            'action': self.action,
            'security_level': self.security_level,
            'ip_address': self.ip_address,
            'user_agent': self.user_agent,
            'session_id': self.session_id,
            'request_id': self.request_id,
        }
        context.update(self.metadata)
        return context


@dataclass
class SecurityPolicy:
    """
    Security policy defining access rules.
    
    Policies are evaluated in order of specificity:
    1. Explicit denials
    2. Explicit allows
    3. Default deny
    """
    id: str = field(default_factory=lambda: str(uuid4()))
    policy_id: Optional[str] = None
    name: str = ""
    description: str = ""
    
    # Subject matching
    subject_type: str = "user"  # 'user', 'role', 'group', 'agent'
    subject_id: Optional[str] = None
    subject_pattern: Optional[str] = None  # Regex pattern
    
    # Resource matching
    resource_type: str = "*"  # 'agent', 'simulation', 'world', '*'
    resource_id: Optional[str] = None
    resource_pattern: Optional[str] = None
    
    # Action
    capabilities: Set[Capability] = field(default_factory=set)
    required_capabilities: List[Capability] = field(default_factory=list)
    rules: List[Any] = field(default_factory=list)
    effect: str = "allow"  # 'allow', 'deny'
    
    # Conditions
    conditions: Dict[str, Any] = field(default_factory=dict)
    
    # Security level required
    min_security_level: SecurityLevel = SecurityLevel.PUBLIC
    
    # Time-based restrictions
    time_restrictions: Dict[str, Any] = field(default_factory=dict)
    
    # Rate limiting
    rate_limit: Optional[int] = None  # Requests per minute
    
    # Audit settings
    audit_on_access: bool = True
    audit_on_deny: bool = True
    
    # Metadata
    priority: int = 100  # Lower = evaluated first
    is_active: bool = True
    created_at: datetime = field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = None

    def __post_init__(self) -> None:
        """Backfill compatibility fields used across the codebase."""
        if self.policy_id:
            self.id = self.policy_id
        if self.required_capabilities and not self.capabilities:
            self.capabilities = set(self.required_capabilities)
    
    def matches_subject(self, subject: Dict[str, Any]) -> bool:
        """Check if policy matches subject."""
        if self.subject_type != subject.get('type', 'user'):
            return False
        
        if self.subject_id and self.subject_id != subject.get('id'):
            return False
        
        if self.subject_pattern:
            import re
            if not re.match(self.subject_pattern, subject.get('id', '')):
                return False
        
        return True
    
    def matches_resource(self, resource: Dict[str, Any]) -> bool:
        """Check if policy matches resource."""
        if self.resource_type != "*" and self.resource_type != resource.get('type'):
            return False
        
        if self.resource_id and self.resource_id != resource.get('id'):
            return False
        
        if self.resource_pattern:
            import re
            if not re.match(self.resource_pattern, resource.get('id', '')):
                return False
        
        return True
    
    def check_conditions(self, context: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """Check if conditions are met."""
        # Time restrictions
        if self.time_restrictions:
            now = datetime.utcnow()
            allowed_hours = self.time_restrictions.get('hours')
            if allowed_hours and now.hour not in allowed_hours:
                return False, "Access denied: outside allowed hours"
            
            allowed_days = self.time_restrictions.get('days')
            if allowed_days and now.weekday() not in allowed_days:
                return False, "Access denied: outside allowed days"
        
        # Security level
        subject_level = context.get('security_level', SecurityLevel.PUBLIC)
        if subject_level.value < self.min_security_level.value:
            return False, f"Insufficient security clearance (need {self.min_security_level.name})"
        
        # Custom conditions
        for key, expected in self.conditions.items():
            actual = context.get(key)
            if actual != expected:
                return False, f"Condition not met: {key}"
        
        return True, None
    
    def is_expired(self) -> bool:
        """Check if policy has expired."""
        if self.expires_at:
            return datetime.utcnow() > self.expires_at
        return False


@dataclass
class AccessDecision:
    """Result of an access control decision."""
    granted: bool
    decision_id: str = field(default_factory=lambda: str(uuid4()))
    policy_id: Optional[str] = None
    reason: Optional[str] = None
    security_level: SecurityLevel = SecurityLevel.PUBLIC
    audit_log_id: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'granted': self.granted,
            'decision_id': self.decision_id,
            'policy_id': self.policy_id,
            'reason': self.reason,
            'security_level': self.security_level.name,
        }


@dataclass
class AuditRecord:
    """Security audit record."""
    id: str = field(default_factory=lambda: str(uuid4()))
    timestamp: datetime = field(default_factory=datetime.utcnow)
    
    # Subject
    subject_type: str = ""
    subject_id: str = ""
    subject_name: Optional[str] = None
    
    # Action
    action: str = ""  # 'access', 'modify', 'delete', 'create'
    capability: Optional[str] = None
    
    # Resource
    resource_type: str = ""
    resource_id: str = ""
    resource_name: Optional[str] = None
    
    # Decision
    decision: str = ""  # 'allow', 'deny', 'error'
    decision_reason: Optional[str] = None
    policy_id: Optional[str] = None
    
    # Context
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    session_id: Optional[str] = None
    request_id: Optional[str] = None
    
    # Security
    security_level: SecurityLevel = SecurityLevel.PUBLIC
    threat_level: ThreatLevel = ThreatLevel.NONE
    
    # Additional data
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def compute_hash(self) -> str:
        """Compute tamper-evident hash of record."""
        data = f"{self.id}:{self.timestamp.isoformat()}:{self.subject_id}:{self.action}:{self.resource_id}"
        return hashlib.sha256(data.encode()).hexdigest()[:16]


class SecurityGovernor:
    """
    Central security governor implementing capability-based access control.
    
    Security-first design:
    - Default deny: All access denied unless explicitly allowed
    - Principle of least privilege: Minimum capabilities granted
    - Defense in depth: Multiple security layers
    - Audit everything: All access attempts logged
    """
    
    def __init__(self):
        """Initialize security governor."""
        self.policies: List[SecurityPolicy] = []
        self.audit_log: List[AuditRecord] = []
        self.rate_counters: Dict[str, List[datetime]] = {}
        
        # Threat detection
        self.threat_indicators: Dict[str, Any] = {}
        self.blocked_subjects: Set[str] = set()
        
        # Subject clearance registry (NOT stored on agent objects)
        # This prevents self-escalation attacks
        self._subject_clearances: Dict[str, SecurityLevel] = {}
        
        # Initialize default policies
        self._init_default_policies()
    
    def _init_default_policies(self) -> None:
        """Initialize default security policies."""
        # Default deny all
        self.policies.append(SecurityPolicy(
            name="Default Deny",
            description="Deny all access by default",
            subject_type="*",
            resource_type="*",
            effect="deny",
            priority=9999,
        ))
        
        # Admin full access
        self.policies.append(SecurityPolicy(
            name="Admin Full Access",
            description="Administrators have full system access",
            subject_type="role",
            subject_id="admin",
            resource_type="*",
            capabilities=set(Capability),
            effect="allow",
            min_security_level=SecurityLevel.INTERNAL,
            priority=10,
        ))
        
        # Operator simulation access
        self.policies.append(SecurityPolicy(
            name="Operator Simulation Access",
            description="Operators can manage simulations",
            subject_type="role",
            subject_id="operator",
            resource_type="simulation",
            capabilities={
                Capability.SIM_CREATE,
                Capability.SIM_READ,
                Capability.SIM_UPDATE,
                Capability.SIM_START,
                Capability.SIM_STOP,
            },
            effect="allow",
            min_security_level=SecurityLevel.INTERNAL,
            priority=20,
        ))
        
        # Viewer read-only
        self.policies.append(SecurityPolicy(
            name="Viewer Read-Only",
            description="Viewers have read-only access",
            subject_type="role",
            subject_id="viewer",
            resource_type="*",
            capabilities={
                Capability.AGENT_READ,
                Capability.SIM_READ,
                Capability.WORLD_READ,
                Capability.GOV_READ,
            },
            effect="allow",
            min_security_level=SecurityLevel.PUBLIC,
            priority=30,
        ))
    
    def evaluate_access(
        self,
        subject: Any,
        resource: Any,
        capability: Capability,
        context: Optional[Any] = None
    ) -> Tuple[bool, Optional[str]]:
        """
        Evaluate access request.
        
        Implements security-first evaluation:
        1. Check if subject is blocked
        2. Check rate limits
        3. Evaluate policies in priority order
        4. Default deny if no policy matches
        """
        subject_dict = self._normalize_subject(subject)
        resource_dict = self._normalize_resource(resource)
        context_dict = self._normalize_context(context)
        subject_id = subject_dict.get('id', 'unknown')
        
        # Check if subject is blocked
        if subject_id in self.blocked_subjects:
            decision = AccessDecision(
                granted=False,
                reason="Subject is blocked due to security concerns"
            )
            self._audit(subject_dict, resource_dict, capability, decision, context_dict)
            return decision.granted, decision.reason
        
        # Check rate limits
        if not self._check_rate_limit(subject_id):
            decision = AccessDecision(
                granted=False,
                reason="Rate limit exceeded"
            )
            self._audit(subject_dict, resource_dict, capability, decision, context_dict)
            return decision.granted, decision.reason
        
        # Evaluate policies (sorted by priority)
        sorted_policies = sorted(self.policies, key=lambda p: p.priority)
        
        for policy in sorted_policies:
            if not policy.is_active or policy.is_expired():
                continue
            
            if not policy.matches_subject(subject_dict):
                continue
            
            if not policy.matches_resource(resource_dict):
                continue
            
            if capability not in policy.capabilities and policy.capabilities:
                continue
            
            # Check conditions
            conditions_met, reason = policy.check_conditions(context_dict)
            if not conditions_met:
                if policy.effect == "allow":
                    # Conditions not met for allow policy
                    continue
            
            # Policy matches - apply effect
            if policy.effect == "deny":
                decision = AccessDecision(
                    granted=False,
                    policy_id=policy.id,
                    reason=reason or "Access denied by policy"
                )
                self._audit(subject_dict, resource_dict, capability, decision, context_dict)
                return decision.granted, decision.reason
            
            elif policy.effect == "allow":
                decision = AccessDecision(
                    granted=True,
                    policy_id=policy.id,
                    security_level=policy.min_security_level
                )
                self._audit(subject_dict, resource_dict, capability, decision, context_dict)
                return decision.granted, decision.reason
        
        # No matching policy - default deny
        decision = AccessDecision(
            granted=False,
            reason="No matching policy found (default deny)"
        )
        self._audit(subject_dict, resource_dict, capability, decision, context_dict)
        return decision.granted, decision.reason

    def _normalize_subject(self, subject: Any) -> Dict[str, Any]:
        """Normalize dict/object subjects into policy subject format."""
        if isinstance(subject, dict):
            return {
                'type': subject.get('type', 'agent'),
                'id': subject.get('id') or subject.get('subject_id', 'unknown'),
                'name': subject.get('name'),
                'claims': subject.get('claims', {}),
            }

        return {
            'type': 'agent',
            'id': getattr(subject, 'agent_id', getattr(subject, 'principal_id', getattr(subject, 'id', 'unknown'))),
            'name': getattr(subject, 'name', None),
            'claims': {},
        }

    def _normalize_resource(self, resource: Any) -> Dict[str, Any]:
        """Normalize dict/object resources into policy resource format."""
        if isinstance(resource, dict):
            return {
                'type': resource.get('type', resource.get('resource_type', 'resource')),
                'id': resource.get('id', resource.get('resource_id', 'unknown')),
                'name': resource.get('name'),
                'sensitive': resource.get('sensitive', False),
            }

        return {
            'type': resource.__class__.__name__.lower() if resource is not None else 'resource',
            'id': getattr(resource, 'action_id', getattr(resource, 'id', 'unknown')),
            'name': getattr(resource, 'name', None),
            'sensitive': False,
        }

    def _normalize_context(self, context: Optional[Any]) -> Dict[str, Any]:
        """Normalize SecurityContext/dict context to dictionary."""
        if context is None:
            return {}
        if isinstance(context, SecurityContext):
            return context.to_dict()
        if isinstance(context, dict):
            return context
        return {'action': getattr(context, 'action', 'access')}
    
    def _check_rate_limit(self, subject_id: str) -> bool:
        """Check if subject has exceeded rate limit."""
        now = datetime.utcnow()
        window = timedelta(minutes=1)
        
        # Get recent requests
        requests = self.rate_counters.get(subject_id, [])
        recent = [r for r in requests if now - r < window]
        
        # Update counter
        self.rate_counters[subject_id] = recent
        
        # Check limit (default 100 req/min)
        return len(recent) < 100
    
    def _audit(
        self,
        subject: Dict[str, Any],
        resource: Dict[str, Any],
        capability: Capability,
        decision: AccessDecision,
        context: Dict[str, Any]
    ) -> None:
        """Create audit record."""
        record = AuditRecord(
            subject_type=subject.get('type', 'unknown'),
            subject_id=subject.get('id', 'unknown'),
            subject_name=subject.get('name'),
            action=context.get('action', 'access'),
            capability=capability.value,
            resource_type=resource.get('type', 'unknown'),
            resource_id=resource.get('id', 'unknown'),
            resource_name=resource.get('name'),
            decision='allow' if decision.granted else 'deny',
            decision_reason=decision.reason,
            policy_id=decision.policy_id,
            ip_address=context.get('ip_address'),
            user_agent=context.get('user_agent'),
            session_id=context.get('session_id'),
            request_id=context.get('request_id'),
            security_level=decision.security_level,
            threat_level=self._assess_threat_level(subject, resource, context),
            metadata={
                'policy_evaluation_time': context.get('eval_time'),
                'additional_claims': subject.get('claims', {}),
            }
        )
        
        self.audit_log.append(record)
        decision.audit_log_id = record.id
        
        # Log security events
        if not decision.granted:
            logger.warning(
                f"Access denied: {subject.get('id')} -> {resource.get('id')} "
                f"({capability.value}): {decision.reason}"
            )
        
        # Threat detection
        self._update_threat_detection(subject, resource, decision, context)
    
    def _assess_threat_level(
        self,
        subject: Dict[str, Any],
        resource: Dict[str, Any],
        context: Dict[str, Any]
    ) -> ThreatLevel:
        """Assess threat level of access attempt."""
        indicators = 0
        
        # Multiple failed attempts
        subject_id = subject.get('id', 'unknown')
        recent_denials = sum(
            1 for r in self.audit_log[-100:]
            if r.subject_id == subject_id and r.decision == 'deny'
        )
        if recent_denials > 10:
            indicators += 2
        elif recent_denials > 5:
            indicators += 1
        
        # Unusual access patterns
        if context.get('unusual_time', False):
            indicators += 1
        
        # High-value resource access
        if resource.get('sensitive', False):
            indicators += 1
        
        # Determine threat level
        if indicators >= 4:
            return ThreatLevel.CRITICAL
        elif indicators >= 3:
            return ThreatLevel.HIGH
        elif indicators >= 2:
            return ThreatLevel.MEDIUM
        elif indicators >= 1:
            return ThreatLevel.LOW
        
        return ThreatLevel.NONE
    
    def _update_threat_detection(
        self,
        subject: Dict[str, Any],
        resource: Dict[str, Any],
        decision: AccessDecision,
        context: Dict[str, Any]
    ) -> None:
        """Update threat detection indicators."""
        subject_id = subject.get('id', 'unknown')
        
        # Track failed attempts
        if not decision.granted:
            if subject_id not in self.threat_indicators:
                self.threat_indicators[subject_id] = {
                    'failed_attempts': 0,
                    'first_failure': datetime.utcnow(),
                    'resources_attempted': set(),
                }
            
            self.threat_indicators[subject_id]['failed_attempts'] += 1
            self.threat_indicators[subject_id]['resources_attempted'].add(
                resource.get('id', 'unknown')
            )
            
            # Auto-block on too many failures
            if self.threat_indicators[subject_id]['failed_attempts'] > 20:
                self.blocked_subjects.add(subject_id)
                logger.critical(f"Subject {subject_id} auto-blocked due to excessive failures")
    
    def add_policy(self, policy: SecurityPolicy) -> None:
        """Add a new security policy."""
        self.policies.append(policy)
        logger.info(f"Security policy added: {policy.name}")

    def register_policy(self, policy_id: str, policy: SecurityPolicy) -> None:
        """Compatibility wrapper for legacy policy registration."""
        policy.id = policy_id
        self.add_policy(policy)
    
    def remove_policy(self, policy_id: str) -> bool:
        """Remove a security policy."""
        for i, policy in enumerate(self.policies):
            if policy.id == policy_id:
                del self.policies[i]
                logger.info(f"Security policy removed: {policy_id}")
                return True
        return False
    
    def unblock_subject(self, subject_id: str) -> bool:
        """Manually unblock a subject."""
        if subject_id in self.blocked_subjects:
            self.blocked_subjects.remove(subject_id)
            self.threat_indicators.pop(subject_id, None)
            logger.info(f"Subject {subject_id} unblocked")
            return True
        return False
    
    def set_clearance(self, subject_id: str, level: SecurityLevel) -> None:
        """
        Set security clearance for a subject.
        Stored in governor's registry, NOT on agent object.
        Prevents self-escalation attacks.
        """
        self._subject_clearances[subject_id] = level
        logger.info(f"Security clearance set: {subject_id} -> {level.name}")
    
    def get_clearance(self, subject_id: str) -> SecurityLevel:
        """
        Get security clearance for a subject.
        Looks up from governor's registry, not agent object.
        Default: PUBLIC
        """
        return self._subject_clearances.get(subject_id, SecurityLevel.PUBLIC)
    
    def revoke_clearance(self, subject_id: str) -> bool:
        """Revoke security clearance for a subject."""
        if subject_id in self._subject_clearances:
            del self._subject_clearances[subject_id]
            logger.info(f"Security clearance revoked: {subject_id}")
            return True
        return False
    
    def get_audit_log(
        self,
        subject_id: Optional[str] = None,
        resource_id: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 100
    ) -> List[AuditRecord]:
        """Query audit log."""
        results = self.audit_log
        
        if subject_id:
            results = [r for r in results if r.subject_id == subject_id]
        
        if resource_id:
            results = [r for r in results if r.resource_id == resource_id]
        
        if start_time:
            results = [r for r in results if r.timestamp >= start_time]
        
        if end_time:
            results = [r for r in results if r.timestamp <= end_time]
        
        return results[-limit:]
    
    def get_security_report(self) -> Dict[str, Any]:
        """Generate security status report."""
        recent_audits = self.audit_log[-1000:]
        
        total_access = len(recent_audits)
        allowed = sum(1 for r in recent_audits if r.decision == 'allow')
        denied = sum(1 for r in recent_audits if r.decision == 'deny')
        
        threat_counts = {}
        for r in recent_audits:
            level = r.threat_level.name
            threat_counts[level] = threat_counts.get(level, 0) + 1
        
        return {
            'total_policies': len(self.policies),
            'active_policies': sum(1 for p in self.policies if p.is_active),
            'blocked_subjects': len(self.blocked_subjects),
            'audit_log_size': len(self.audit_log),
            'recent_activity': {
                'total': total_access,
                'allowed': allowed,
                'denied': denied,
                'allow_rate': round(allowed / total_access, 2) if total_access > 0 else 0,
            },
            'threat_summary': threat_counts,
            'top_blocked': list(self.blocked_subjects)[:10],
        }


# Global security governor instance
security_governor = SecurityGovernor()


__all__ = [
    'SecurityLevel',
    'Capability',
    'ThreatLevel',
    'SecurityContext',
    'SecurityPolicy',
    'AccessDecision',
    'AuditRecord',
    'SecurityGovernor',
    'security_governor',
]
