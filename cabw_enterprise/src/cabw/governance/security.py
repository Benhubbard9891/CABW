"""Security-first governance layer for CABW simulations."""

from __future__ import annotations

import hashlib
import hmac
import logging
import re
import time
from dataclasses import dataclass, field
from enum import Enum, auto
from functools import wraps
from typing import Any, Callable, Dict, List, Optional, Set

logger = logging.getLogger(__name__)


class Permission(Enum):
    """Permissions that can be granted to users/agents."""

    READ_SIMULATION = auto()
    WRITE_SIMULATION = auto()
    START_SIMULATION = auto()
    STOP_SIMULATION = auto()
    MANAGE_AGENTS = auto()
    ADMIN = auto()


class SecurityLevel(Enum):
    """Security classification levels."""

    PUBLIC = 0
    INTERNAL = 1
    CONFIDENTIAL = 2
    SECRET = 3


@dataclass
class SecurityPolicy:
    """Defines access rules for a resource or operation."""

    name: str
    required_permissions: Set[Permission] = field(default_factory=set)
    min_security_level: SecurityLevel = SecurityLevel.PUBLIC
    rate_limit: int = 0        # requests per minute; 0 = unlimited
    allow_list: List[str] = field(default_factory=list)   # allowed principal IDs
    deny_list: List[str] = field(default_factory=list)    # denied principal IDs


@dataclass
class Principal:
    """Represents an authenticated user or service account."""

    principal_id: str
    permissions: Set[Permission] = field(default_factory=set)
    security_level: SecurityLevel = SecurityLevel.PUBLIC
    metadata: Dict[str, Any] = field(default_factory=dict)

    def has_permission(self, perm: Permission) -> bool:
        return perm in self.permissions or Permission.ADMIN in self.permissions

    def has_all_permissions(self, perms: Set[Permission]) -> bool:
        return all(self.has_permission(p) for p in perms)


class RateLimiter:
    """Token-bucket rate limiter."""

    def __init__(self, max_requests: int, window_seconds: float = 60.0) -> None:
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._buckets: Dict[str, List[float]] = {}

    def allow(self, key: str) -> bool:
        if self.max_requests <= 0:
            return True  # unlimited
        now = time.monotonic()
        bucket = self._buckets.setdefault(key, [])
        # Remove timestamps outside the window
        self._buckets[key] = [t for t in bucket if now - t < self.window_seconds]
        if len(self._buckets[key]) < self.max_requests:
            self._buckets[key].append(now)
            return True
        return False


class AuditLog:
    """Append-only audit log for security-relevant events."""

    def __init__(self, max_entries: int = 10_000) -> None:
        self._log: List[Dict[str, Any]] = []
        self.max_entries = max_entries

    def record(
        self,
        event_type: str,
        principal_id: str,
        resource: str,
        success: bool,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        entry = {
            "timestamp": time.time(),
            "event_type": event_type,
            "principal_id": principal_id,
            "resource": resource,
            "success": success,
            "details": details or {},
        }
        self._log.append(entry)
        if len(self._log) > self.max_entries:
            self._log.pop(0)
        level = logging.INFO if success else logging.WARNING
        logger.log(level, "AUDIT %s principal=%s resource=%s", event_type, principal_id, resource)

    def query(
        self,
        principal_id: Optional[str] = None,
        event_type: Optional[str] = None,
        success: Optional[bool] = None,
    ) -> List[Dict[str, Any]]:
        entries = self._log
        if principal_id:
            entries = [e for e in entries if e["principal_id"] == principal_id]
        if event_type:
            entries = [e for e in entries if e["event_type"] == event_type]
        if success is not None:
            entries = [e for e in entries if e["success"] == success]
        return entries


class SecurityManager:
    """Central authority for authentication, authorisation, and auditing."""

    def __init__(self, secret_key: bytes = b"cabw-default-secret") -> None:
        self._secret_key = secret_key
        self._principals: Dict[str, Principal] = {}
        self._policies: Dict[str, SecurityPolicy] = {}
        self._rate_limiters: Dict[str, RateLimiter] = {}
        self.audit_log = AuditLog()

    # ------------------------------------------------------------------
    # Principal management
    # ------------------------------------------------------------------

    def register_principal(self, principal: Principal) -> None:
        self._principals[principal.principal_id] = principal

    def get_principal(self, principal_id: str) -> Optional[Principal]:
        return self._principals.get(principal_id)

    # ------------------------------------------------------------------
    # Policy management
    # ------------------------------------------------------------------

    def register_policy(self, policy: SecurityPolicy) -> None:
        self._policies[policy.name] = policy
        if policy.rate_limit > 0:
            self._rate_limiters[policy.name] = RateLimiter(policy.rate_limit)

    # ------------------------------------------------------------------
    # Authorisation
    # ------------------------------------------------------------------

    def authorize(self, principal_id: str, policy_name: str) -> bool:
        """Return True when *principal_id* is allowed by *policy_name*."""
        principal = self._principals.get(principal_id)
        policy = self._policies.get(policy_name)

        if principal is None or policy is None:
            self.audit_log.record("AUTHORIZE", principal_id, policy_name, False,
                                  {"reason": "unknown principal or policy"})
            return False

        # Deny list takes precedence
        if principal_id in policy.deny_list:
            self.audit_log.record("AUTHORIZE", principal_id, policy_name, False,
                                  {"reason": "deny list"})
            return False

        # Allow list short-circuits permission checks
        if policy.allow_list and principal_id not in policy.allow_list:
            self.audit_log.record("AUTHORIZE", principal_id, policy_name, False,
                                  {"reason": "not in allow list"})
            return False

        # Security level check
        if principal.security_level.value < policy.min_security_level.value:
            self.audit_log.record("AUTHORIZE", principal_id, policy_name, False,
                                  {"reason": "insufficient security level"})
            return False

        # Permission check
        if not principal.has_all_permissions(policy.required_permissions):
            self.audit_log.record("AUTHORIZE", principal_id, policy_name, False,
                                  {"reason": "missing permissions"})
            return False

        # Rate limiting
        limiter = self._rate_limiters.get(policy_name)
        if limiter and not limiter.allow(principal_id):
            self.audit_log.record("AUTHORIZE", principal_id, policy_name, False,
                                  {"reason": "rate limit exceeded"})
            return False

        self.audit_log.record("AUTHORIZE", principal_id, policy_name, True)
        return True

    # ------------------------------------------------------------------
    # Token helpers
    # ------------------------------------------------------------------

    def generate_token(self, principal_id: str) -> str:
        """Generate an HMAC-SHA256 token for the given principal."""
        timestamp = str(int(time.time()))
        message = f"{principal_id}:{timestamp}".encode()
        signature = hmac.new(self._secret_key, message, hashlib.sha256).hexdigest()
        return f"{principal_id}:{timestamp}:{signature}"

    def verify_token(self, token: str) -> Optional[str]:
        """Verify a token and return the principal ID, or None if invalid."""
        parts = token.split(":")
        if len(parts) != 3:
            return None
        principal_id, timestamp, signature = parts
        message = f"{principal_id}:{timestamp}".encode()
        expected = hmac.new(self._secret_key, message, hashlib.sha256).hexdigest()
        if not hmac.compare_digest(expected, signature):
            return None
        # Token valid for 1 hour
        if time.time() - float(timestamp) > 3600:
            return None
        return principal_id

    # ------------------------------------------------------------------
    # Input sanitisation helpers
    # ------------------------------------------------------------------

    @staticmethod
    def sanitize_string(value: str, max_length: int = 256) -> str:
        """Strip dangerous characters and truncate to *max_length*."""
        sanitized = re.sub(r"[<>\"'%;()&+]", "", value)
        return sanitized[:max_length]

    @staticmethod
    def validate_agent_id(agent_id: str) -> bool:
        """Return True when *agent_id* contains only safe characters."""
        return bool(re.match(r"^[a-zA-Z0-9_\-]{1,64}$", agent_id))


def require_permission(permission: Permission, policy_name: str = "default"):
    """Decorator that enforces a permission check before calling a function.

    The decorated function must receive a ``security_manager`` and
    ``principal_id`` keyword argument.
    """

    def decorator(fn: Callable) -> Callable:
        @wraps(fn)
        def wrapper(*args: Any, security_manager: SecurityManager, principal_id: str, **kwargs: Any) -> Any:
            if not security_manager.authorize(principal_id, policy_name):
                raise PermissionError(
                    f"Principal {principal_id!r} does not have permission {permission.name!r}"
                )
            return fn(*args, security_manager=security_manager, principal_id=principal_id, **kwargs)

        return wrapper

    return decorator
