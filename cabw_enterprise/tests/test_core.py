"""
Test suite for CABW Enterprise Core Module

Covers:
- AgentMemory
- AgentNeeds
- AgentStats
- IntegratedAgent
- EmotionalState / EmotionalContagion
- Team / TeamManager / SharedGoal
- Memory DB model (rehearsal strengthening cap)
"""
import pytest

from cabw.core.emotions import EmotionalContagion, EmotionalState, EmotionType, MoodState
from cabw.core.integrated_agent import AgentMemory, AgentNeeds, AgentStats, IntegratedAgent
from cabw.core.teamwork import GoalObjective, GoalStatus, SharedGoal, Team, TeamManager, TeamRole
from cabw.db.models import Memory

# ============================================================
# AgentMemory
# ============================================================

class TestAgentMemory:
    """Tests for AgentMemory data class."""

    def test_add_experience_stores_in_short_term(self):
        memory = AgentMemory()
        memory.add_experience({'event': 'test'}, importance=0.5)
        assert len(memory.short_term) == 1

    def test_short_term_capped_at_max(self):
        memory = AgentMemory(max_short_term=3)
        for i in range(5):
            memory.add_experience({'event': i}, importance=0.5)
        assert len(memory.short_term) <= 3

    def test_important_memory_moves_to_long_term(self):
        memory = AgentMemory(max_short_term=2)
        # Fill short-term with two high-importance items (0.9 each)
        memory.add_experience({'event': 'a'}, importance=0.9)
        memory.add_experience({'event': 'b'}, importance=0.9)
        # Adding a third item (importance=0.85) exceeds max_short_term,
        # causing eviction of the minimum-importance item (0.85). Since
        # 0.85 > 0.7, the evicted item is promoted to long-term memory.
        memory.add_experience({'event': 'c'}, importance=0.85)
        assert len(memory.long_term) >= 1

    def test_recall_relevant_returns_limited_results(self):
        memory = AgentMemory()
        for i in range(5):
            memory.add_experience({'event': f'fire_event_{i}'}, importance=0.5)
        results = memory.recall_relevant('fire', limit=2)
        assert len(results) <= 2

    def test_recall_relevant_context_match(self):
        memory = AgentMemory()
        memory.add_experience({'event': 'flood_emergency'}, importance=0.9)
        memory.add_experience({'event': 'sunny_day'}, importance=0.1)
        results = memory.recall_relevant('flood', limit=5)
        assert any('flood' in str(r) for r in results)

    def test_experience_has_timestamp(self):
        memory = AgentMemory()
        memory.add_experience({'event': 'test'})
        assert 'timestamp' in memory.short_term[0]


# ============================================================
# AgentNeeds
# ============================================================

class TestAgentNeeds:
    """Tests for AgentNeeds data class."""

    def test_initial_values_in_range(self):
        needs = AgentNeeds()
        for attr in ['hunger', 'thirst', 'rest']:
            assert 0.0 <= getattr(needs, attr) <= 1.0

    def test_tick_increases_hunger_and_thirst(self):
        needs = AgentNeeds()
        initial_hunger = needs.hunger
        initial_thirst = needs.thirst
        needs.tick()
        assert needs.hunger > initial_hunger
        assert needs.thirst > initial_thirst

    def test_tick_caps_needs_at_one(self):
        needs = AgentNeeds(hunger=0.99, thirst=0.99, rest=0.99)
        for _ in range(10):
            needs.tick()
        assert needs.hunger <= 1.0
        assert needs.thirst <= 1.0
        assert needs.rest <= 1.0

    def test_get_priority_need_returns_tuple(self):
        needs = AgentNeeds(hunger=0.9, thirst=0.1)
        name, urgency = needs.get_priority_need()
        assert isinstance(name, str)
        assert isinstance(urgency, float)

    def test_get_priority_need_picks_highest(self):
        # When achievement < 0.2, its urgency is (1.0 - achievement), which could
        # exceed hunger's urgency of 0.9. Set achievement=0.5 (>= 0.2) so it
        # contributes 0, ensuring hunger (0.9) has the highest urgency.
        needs = AgentNeeds(hunger=0.9, thirst=0.1, rest=0.0, achievement=0.5)
        name, urgency = needs.get_priority_need()
        assert name == 'hunger'

    def test_tick_applies_env_effects(self):
        needs = AgentNeeds(safety=1.0)
        needs.tick(environment_effects={'safety_change': -0.3})
        assert needs.safety < 1.0


# ============================================================
# AgentStats
# ============================================================

class TestAgentStats:
    """Tests for AgentStats data class."""

    def test_initial_health_at_max(self):
        stats = AgentStats()
        assert stats.health == stats.max_health

    def test_is_alive_when_health_positive(self):
        stats = AgentStats(health=50.0)
        assert stats.is_alive()

    def test_is_not_alive_when_health_zero(self):
        stats = AgentStats(health=0.0)
        assert not stats.is_alive()

    def test_modify_health_clamped(self):
        stats = AgentStats()
        stats.modify_health(-200)
        assert stats.health == 0.0
        stats.modify_health(200)
        assert stats.health == stats.max_health

    def test_modify_energy_clamped(self):
        stats = AgentStats()
        stats.modify_energy(-200)
        assert stats.energy == 0.0
        stats.modify_energy(200)
        assert stats.energy == stats.max_energy

    def test_get_health_percent(self):
        stats = AgentStats(health=50.0, max_health=100.0)
        assert stats.get_health_percent() == pytest.approx(0.5)

    def test_low_health_sets_injured(self):
        stats = AgentStats()
        stats.modify_health(-80)
        assert stats.injured

    def test_get_energy_percent(self):
        stats = AgentStats(energy=75.0, max_energy=100.0)
        assert stats.get_energy_percent() == pytest.approx(0.75)


# ============================================================
# IntegratedAgent
# ============================================================

class TestIntegratedAgent:
    """Tests for IntegratedAgent class."""

    def test_creates_with_defaults(self):
        agent = IntegratedAgent()
        assert agent.agent_id is not None
        assert agent.name == 'Agent'
        assert agent.location == (0, 0)

    def test_creates_with_custom_parameters(self):
        agent = IntegratedAgent(
            agent_id='test-001',
            name='Alice',
            initial_location=(5, 7)
        )
        assert agent.agent_id == 'test-001'
        assert agent.name == 'Alice'
        assert agent.location == (5, 7)

    def test_has_all_core_systems(self):
        agent = IntegratedAgent()
        assert agent.emotional_state is not None
        assert agent.memory is not None
        assert agent.needs is not None
        assert agent.stats is not None
        assert agent.blackboard is not None
        assert agent.action_library is not None

    def test_ocean_traits_default_to_neutral(self):
        agent = IntegratedAgent()
        for trait in ['openness', 'conscientiousness', 'extraversion', 'agreeableness', 'neuroticism']:
            assert 0.0 <= agent.ocean_traits[trait] <= 1.0

    def test_ocean_traits_custom(self):
        traits = {'openness': 0.8, 'conscientiousness': 0.2,
                  'extraversion': 0.6, 'agreeableness': 0.9, 'neuroticism': 0.1}
        agent = IntegratedAgent(ocean_traits=traits)
        assert agent.ocean_traits['openness'] == pytest.approx(0.8)

    def test_get_state_summary(self):
        agent = IntegratedAgent(name='Bob')
        summary = agent.get_state_summary()
        assert summary['name'] == 'Bob'
        assert 'health' in summary
        assert 'energy' in summary
        assert 'alive' in summary
        assert 'emotional_state' in summary
        assert 'needs' in summary

    def test_distance_to_self_is_zero(self):
        agent = IntegratedAgent(initial_location=(3, 4))
        assert agent._distance_to(agent) == pytest.approx(0.0)

    def test_distance_to_other_agent(self):
        a1 = IntegratedAgent(initial_location=(0, 0))
        a2 = IntegratedAgent(initial_location=(3, 4))
        assert a1._distance_to(a2) == pytest.approx(5.0)

    def test_join_and_leave_team(self):
        agent = IntegratedAgent()
        team = Team(name='Alpha')
        result = agent.join_team(team, TeamRole.MEMBER)
        assert result
        assert agent.current_team is not None
        agent.leave_team()
        assert agent.current_team is None


# ============================================================
# EmotionalState
# ============================================================

class TestEmotionalState:
    """Tests for EmotionalState dataclass."""

    def test_initial_values_in_range(self):
        state = EmotionalState()
        for attr in ['joy', 'sadness', 'anger', 'fear', 'trust']:
            assert 0.0 <= getattr(state, attr) <= 1.0

    def test_apply_stimulus_increases_emotion(self):
        state = EmotionalState()
        initial_joy = state.joy
        state.apply_stimulus(EmotionType.JOY, 0.5)
        assert state.joy >= initial_joy

    def test_get_dominant_emotion_returns_tuple(self):
        state = EmotionalState(joy=0.9)
        emotion, intensity = state.get_dominant_emotion()
        assert isinstance(emotion, EmotionType)
        assert 0.0 <= intensity <= 1.0

    def test_high_joy_is_dominant(self):
        state = EmotionalState(joy=0.9, sadness=0.1, anger=0.0, fear=0.0)
        emotion, _ = state.get_dominant_emotion()
        assert emotion == EmotionType.JOY

    def test_get_valence_positive_for_happy(self):
        state = EmotionalState(joy=0.8, trust=0.7)
        assert state.get_valence() > 0

    def test_get_valence_negative_for_sad(self):
        state = EmotionalState(sadness=0.8, fear=0.7, anger=0.6)
        assert state.get_valence() < 0

    def test_get_arousal_returns_float(self):
        state = EmotionalState()
        arousal = state.get_arousal()
        assert isinstance(arousal, float)
        assert 0.0 <= arousal <= 1.0

    def test_mood_starts_neutral(self):
        state = EmotionalState()
        assert state.mood == MoodState.NEUTRAL


class TestEmotionalContagion:
    """Tests for EmotionalContagion utility class."""

    def test_calculate_contagion_strength_returns_float(self):
        strength = EmotionalContagion.calculate_contagion_strength(
            source_emotion=0.8,
            relationship_trust=0.6,
            relationship_affection=0.5,
            target_empathy=0.7,
            distance=0.2,
            source_expressiveness=0.6
        )
        assert isinstance(strength, float)
        assert strength >= 0.0

    def test_high_distance_reduces_contagion(self):
        near = EmotionalContagion.calculate_contagion_strength(
            source_emotion=0.8, relationship_trust=0.6,
            relationship_affection=0.5, target_empathy=0.7,
            distance=0.1, source_expressiveness=0.6
        )
        far = EmotionalContagion.calculate_contagion_strength(
            source_emotion=0.8, relationship_trust=0.6,
            relationship_affection=0.5, target_empathy=0.7,
            distance=0.9, source_expressiveness=0.6
        )
        assert near >= far

    def test_apply_contagion_returns_dict(self):
        source = EmotionalState(joy=0.9)
        target = EmotionalState()
        result = EmotionalContagion.apply_contagion(
            source_state=source,
            target_state=target,
            emotion=EmotionType.JOY,
            strength=0.3
        )
        assert isinstance(result, dict)


# ============================================================
# Team / SharedGoal / TeamManager
# ============================================================

class TestTeam:
    """Tests for Team dataclass."""

    def test_add_member_returns_member(self):
        team = Team(name='Bravo')
        member = team.add_member('agent-1')
        assert member is not None
        assert 'agent-1' in team.members

    def test_first_member_becomes_leader(self):
        team = Team(name='Charlie')
        team.add_member('agent-1')
        assert team.leader_id == 'agent-1'

    def test_remove_member(self):
        team = Team(name='Delta')
        team.add_member('agent-1')
        team.add_member('agent-2')
        result = team.remove_member('agent-1')
        assert result
        assert 'agent-1' not in team.members

    def test_remove_leader_reassigns(self):
        team = Team(name='Echo')
        team.add_member('agent-1')
        team.add_member('agent-2')
        team.remove_member('agent-1')
        assert team.leader_id == 'agent-2'

    def test_assign_role(self):
        team = Team(name='Foxtrot')
        team.add_member('agent-1')
        team.add_member('agent-2')
        result = team.assign_role('agent-2', TeamRole.SUPPORT)
        assert result
        assert team.members['agent-2'].role == TeamRole.SUPPORT

    def test_add_goal_activates_it(self):
        team = Team(name='Golf')
        team.add_member('agent-1')
        goal = SharedGoal(name='Explore Zone')
        team.add_goal(goal)
        assert goal.status == GoalStatus.ACTIVE
        assert len(team.active_goals) == 1

    def test_get_coordination_bonus_is_float(self):
        team = Team(name='Hotel')
        team.add_member('agent-1')
        team.add_member('agent-2')
        bonus = team.get_coordination_bonus()
        assert isinstance(bonus, float)
        assert 0.0 <= bonus <= 0.5

    def test_get_role_distribution(self):
        team = Team(name='India')
        team.add_member('agent-1')
        team.add_member('agent-2')
        dist = team.get_role_distribution()
        assert isinstance(dist, dict)
        assert len(dist) > 0


class TestSharedGoal:
    """Tests for SharedGoal dataclass."""

    def test_initial_status_pending(self):
        goal = SharedGoal(name='Test Goal')
        assert goal.status == GoalStatus.PENDING

    def test_start_activates_goal(self):
        goal = SharedGoal(name='Gather Resources')
        goal.start()
        assert goal.status == GoalStatus.ACTIVE
        assert goal.started_at is not None

    def test_complete_sets_status(self):
        goal = SharedGoal(name='Defend Base')
        goal.start()
        goal.complete()
        assert goal.status == GoalStatus.COMPLETED
        assert goal.progress == 1.0

    def test_fail_sets_status(self):
        goal = SharedGoal(name='Rescue Mission')
        goal.start()
        goal.fail('Time ran out')
        assert goal.status == GoalStatus.FAILED

    def test_add_contribution(self):
        goal = SharedGoal(name='Build Shelter')
        goal.add_contribution('agent-1', 0.5)
        goal.add_contribution('agent-1', 0.3)
        assert goal.contributions['agent-1'] == pytest.approx(0.8)

    def test_get_top_contributors(self):
        goal = SharedGoal(name='Explore')
        goal.add_contribution('agent-1', 0.9)
        goal.add_contribution('agent-2', 0.3)
        top = goal.get_top_contributors(n=1)
        assert top[0][0] == 'agent-1'

    def test_update_progress_with_objectives(self):
        goal = SharedGoal(name='Multi-objective')
        obj1 = GoalObjective(id='obj-1', description='First', is_completed=True)
        obj2 = GoalObjective(id='obj-2', description='Second', is_completed=False)
        goal.objectives = [obj1, obj2]
        goal.start()
        goal.update_progress()
        assert goal.progress == pytest.approx(0.5)

    def test_to_dict_contains_required_fields(self):
        goal = SharedGoal(name='Map Territory')
        data = goal.to_dict()
        assert 'id' in data
        assert 'name' in data
        assert 'status' in data
        assert 'progress' in data


class TestTeamManager:
    """Tests for TeamManager class."""

    def test_create_team(self):
        manager = TeamManager()
        team = manager.create_team('Alpha Squad')
        assert team is not None
        assert team.name == 'Alpha Squad'

    def test_team_stored_in_teams_dict(self):
        manager = TeamManager()
        team = manager.create_team('Beta Squad')
        assert team.id in manager.teams
        assert manager.teams[team.id] is team

    def test_disband_team(self):
        manager = TeamManager()
        team = manager.create_team('Gamma Squad')
        manager.disband_team(team.id)
        assert team.id not in manager.teams

    def test_get_agent_teams(self):
        manager = TeamManager()
        team = manager.create_team('Delta Squad')
        team.add_member('agent-99')
        manager.agent_teams.setdefault('agent-99', set()).add(team.id)
        found_teams = manager.get_agent_teams('agent-99')
        assert any(t.id == team.id for t in found_teams)

    def test_get_active_teams_requires_viable_team(self):
        manager = TeamManager()
        team = manager.create_team('Echo Squad')
        team.add_member('agent-1')
        team.add_member('agent-2')
        active = manager.get_active_teams()
        assert any(t.id == team.id for t in active)


# ============================================================
# Memory DB model — rehearsal strengthening cap
# ============================================================

class TestMemoryRehearsalCap:
    """Tests for Memory.rehearse() and its strength ceiling."""

    def _make_memory_like(self, strength: float = 1.0, rehearsal_count: int = 0):
        """
        Create a SimpleNamespace that mirrors the Memory model's attribute
        interface.  This avoids triggering SQLAlchemy's full mapper
        initialisation (which is blocked by a pre-existing ORM configuration
        issue in Agent.actions) while still exercising the rehearse() method.
        """
        from types import SimpleNamespace
        return SimpleNamespace(
            strength=strength,
            rehearsal_count=rehearsal_count,
            MAX_REHEARSAL_STRENGTH=Memory.MAX_REHEARSAL_STRENGTH,
        )

    def test_rehearse_increments_rehearsal_count(self):
        mem = self._make_memory_like()
        Memory.rehearse(mem)
        assert mem.rehearsal_count == 1
        assert mem.strength == pytest.approx(1.0 + 0.1)  # default boost = 0.1

    def test_rehearse_increases_strength(self):
        mem = self._make_memory_like(strength=1.0)
        Memory.rehearse(mem, boost=0.5)
        assert mem.strength > 1.0

    def test_rehearse_returns_new_strength(self):
        mem = self._make_memory_like(strength=1.0)
        result = Memory.rehearse(mem, boost=0.3)
        assert result == mem.strength

    def test_rehearse_does_not_exceed_cap(self):
        mem = self._make_memory_like(strength=Memory.MAX_REHEARSAL_STRENGTH - 0.05)
        Memory.rehearse(mem, boost=1.0)
        assert mem.strength == Memory.MAX_REHEARSAL_STRENGTH

    def test_rehearse_many_times_stays_at_cap(self):
        mem = self._make_memory_like(strength=1.0)
        for _ in range(1000):
            Memory.rehearse(mem, boost=0.1)
        assert mem.strength == Memory.MAX_REHEARSAL_STRENGTH

    def test_max_rehearsal_strength_constant_exists(self):
        assert hasattr(Memory, "MAX_REHEARSAL_STRENGTH")
        assert Memory.MAX_REHEARSAL_STRENGTH > 0
