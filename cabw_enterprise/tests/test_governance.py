"""
Test suite for CABW Enterprise Governance Module

Covers:
- SecurityGovernor
- SecurityPolicy
- SecurityContext
- AccessDecision
- AuditRecord
"""
from cabw.governance.security import (
    AccessDecision,
    AuditRecord,
    Capability,
    SecurityContext,
    SecurityGovernor,
    SecurityLevel,
    SecurityPolicy,
)


class TestSecurityContext:
    """Tests for SecurityContext dataclass."""

    def test_create_context(self):
        ctx = SecurityContext(
            subject_id='agent-1',
            resource_id='world',
            action='move'
        )
        assert ctx.subject_id == 'agent-1'
        assert ctx.resource_id == 'world'
        assert ctx.action == 'move'

    def test_default_security_level_is_public(self):
        ctx = SecurityContext(subject_id='u', resource_id='r', action='a')
        assert ctx.security_level == SecurityLevel.PUBLIC

    def test_to_dict_contains_required_keys(self):
        ctx = SecurityContext(subject_id='u', resource_id='r', action='a')
        d = ctx.to_dict()
        assert 'subject_id' in d
        assert 'resource_id' in d
        assert 'action' in d


class TestSecurityPolicy:
    """Tests for SecurityPolicy dataclass."""

    def test_create_policy_with_defaults(self):
        policy = SecurityPolicy(name='Test Policy')
        assert policy.name == 'Test Policy'
        assert policy.effect == 'allow'
        assert policy.is_active

    def test_policy_id_backfill(self):
        policy = SecurityPolicy(policy_id='my-policy')
        assert policy.id == 'my-policy'

    def test_required_capabilities_backfill(self):
        policy = SecurityPolicy(
            required_capabilities=[Capability.READ, Capability.EXECUTE]
        )
        assert Capability.READ in policy.capabilities
        assert Capability.EXECUTE in policy.capabilities

    def test_matches_subject_by_type(self):
        policy = SecurityPolicy(subject_type='user', subject_id='alice')
        assert policy.matches_subject({'type': 'user', 'id': 'alice'})
        assert not policy.matches_subject({'type': 'role', 'id': 'alice'})

    def test_matches_subject_any_id(self):
        policy = SecurityPolicy(subject_type='user')  # No subject_id restriction
        assert policy.matches_subject({'type': 'user', 'id': 'anything'})

    def test_matches_resource_wildcard(self):
        policy = SecurityPolicy(resource_type='*')
        assert policy.matches_resource({'type': 'agent', 'id': 'res-1'})
        assert policy.matches_resource({'type': 'simulation', 'id': 'res-2'})

    def test_matches_resource_specific_type(self):
        policy = SecurityPolicy(resource_type='simulation')
        assert policy.matches_resource({'type': 'simulation', 'id': 'sim-1'})
        assert not policy.matches_resource({'type': 'agent', 'id': 'agent-1'})

    def test_check_conditions_passes_empty(self):
        policy = SecurityPolicy()
        passed, reason = policy.check_conditions({'security_level': SecurityLevel.PUBLIC})
        assert passed

    def test_check_conditions_security_level_insufficient(self):
        policy = SecurityPolicy(min_security_level=SecurityLevel.SECRET)
        passed, reason = policy.check_conditions({'security_level': SecurityLevel.PUBLIC})
        assert not passed
        assert reason is not None

    def test_not_expired_by_default(self):
        policy = SecurityPolicy()
        assert not policy.is_expired()


class TestAuditRecord:
    """Tests for AuditRecord dataclass."""

    def test_create_record(self):
        record = AuditRecord(
            subject_id='agent-1',
            action='access',
            resource_type='world',
            resource_id='world-1',
            decision='allow'
        )
        assert record.subject_id == 'agent-1'
        assert record.decision == 'allow'

    def test_compute_hash_returns_string(self):
        record = AuditRecord(
            subject_id='agent-1',
            action='access',
            resource_type='world',
            resource_id='world-1',
            decision='allow'
        )
        h = record.compute_hash()
        assert isinstance(h, str)
        assert len(h) == 16

    def test_hash_is_deterministic(self):
        record = AuditRecord(
            subject_id='agent-1',
            action='access',
            resource_type='world',
            resource_id='world-1',
            decision='allow'
        )
        assert record.compute_hash() == record.compute_hash()


class TestAccessDecision:
    """Tests for AccessDecision dataclass."""

    def test_create_granted(self):
        decision = AccessDecision(granted=True, reason='Policy matched')
        assert decision.granted
        assert decision.decision_id is not None

    def test_create_denied(self):
        decision = AccessDecision(granted=False, reason='Default deny')
        assert not decision.granted

    def test_to_dict_contains_keys(self):
        decision = AccessDecision(granted=True)
        d = decision.to_dict()
        assert 'granted' in d
        assert 'decision_id' in d
        assert 'security_level' in d


class TestSecurityGovernor:
    """Tests for SecurityGovernor class."""

    def test_initializes_with_default_policies(self):
        governor = SecurityGovernor()
        assert len(governor.policies) > 0

    def test_default_deny_policy_exists(self):
        governor = SecurityGovernor()
        deny_policies = [p for p in governor.policies if p.effect == 'deny']
        assert len(deny_policies) >= 1

    def test_evaluate_access_default_deny(self):
        """Unknown subject/resource pair should be denied by default."""
        governor = SecurityGovernor()

        class FakeSubject:
            agent_id = 'unknown-agent'

        class FakeResource:
            pass

        ctx = SecurityContext(
            subject_id='unknown-agent',
            resource_id='world',
            action='destroy'
        )
        allowed, reason = governor.evaluate_access(
            subject=FakeSubject(),
            resource=FakeResource(),
            capability=Capability.DELETE,
            context=ctx
        )
        assert not allowed

    def test_audit_log_grows_on_evaluation(self):
        governor = SecurityGovernor()

        class FakeSubject:
            agent_id = 'agent-x'

        class FakeResource:
            pass

        ctx = SecurityContext(subject_id='agent-x', resource_id='res', action='read')
        governor.evaluate_access(
            subject=FakeSubject(),
            resource=FakeResource(),
            capability=Capability.READ,
            context=ctx
        )
        assert len(governor.audit_log) >= 1

    def test_register_policy(self):
        governor = SecurityGovernor()
        initial_count = len(governor.policies)
        policy = SecurityPolicy(
            name='Test Allow',
            subject_type='user',
            subject_id='test-user',
            resource_type='*',
            capabilities={Capability.READ},
            effect='allow',
            priority=5
        )
        governor.policies.append(policy)
        assert len(governor.policies) == initial_count + 1
