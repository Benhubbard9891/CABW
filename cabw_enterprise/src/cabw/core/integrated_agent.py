"""
Integrated Agent System

Combines all enhanced components into a unified agent architecture:
- Advanced emotional system with trauma and contagion
- Complex actions with preconditions and effects
- Behavior tree-driven decision making
- Teamwork capabilities
- Security-aware operation
- Environmental responsiveness
"""

import random
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from ..governance.security import Capability, SecurityContext, SecurityGovernor
from .actions import ActionContext, ActionLibrary
from .behavior_tree import BehaviorTree, BehaviorTreeLibrary, Blackboard
from .emotions import EmotionalContagion, EmotionalState, EmotionType
from .teamwork import Team, TeamRole


@dataclass
class AgentMemory:
    """Agent's working and long-term memory."""
    short_term: list[dict[str, Any]] = field(default_factory=list)
    long_term: dict[str, Any] = field(default_factory=dict)
    max_short_term: int = 10

    def add_experience(self, experience: dict[str, Any], importance: float = 0.5):
        """Add experience to memory."""
        experience['timestamp'] = datetime.now().isoformat()
        experience['importance'] = importance

        self.short_term.append(experience)

        # Keep short-term memory limited
        if len(self.short_term) > self.max_short_term:
            # Move least important to long-term
            removed = min(self.short_term, key=lambda x: x.get('importance', 0))
            self.short_term.remove(removed)

            # Consolidate to long-term if important enough
            if removed.get('importance', 0) > 0.7:
                key = f"memory_{removed['timestamp']}"
                self.long_term[key] = removed

    def recall_relevant(self, context: str, limit: int = 3) -> list[dict[str, Any]]:
        """Recall memories relevant to context."""
        all_memories = self.short_term + list(self.long_term.values())

        # Simple relevance scoring
        scored = []
        for mem in all_memories:
            score = 0.0
            if context.lower() in str(mem).lower():
                score += 0.5
            score += mem.get('importance', 0.0) * 0.5
            scored.append((mem, score))

        scored.sort(key=lambda x: x[1], reverse=True)
        return [m[0] for m in scored[:limit]]


@dataclass
class AgentNeeds:
    """Agent's physiological and psychological needs."""
    hunger: float = 0.0  # 0 = satisfied, 1 = starving
    thirst: float = 0.0
    rest: float = 0.0    # 0 = rested, 1 = exhausted
    safety: float = 1.0  # 1 = safe, 0 = threatened
    social: float = 0.5  # 0 = isolated, 1 = fully connected
    achievement: float = 0.0  # Need for accomplishment

    def get_priority_need(self) -> tuple[str, float]:
        """Get the most pressing need."""
        needs = {
            'hunger': self.hunger,
            'thirst': self.thirst,
            'rest': self.rest,
            'safety': 1.0 - self.safety,  # Invert so higher = more urgent
            'social': 1.0 - self.social if self.social < 0.3 else 0,
            'achievement': 1.0 - self.achievement if self.achievement < 0.2 else 0
        }

        priority = max(needs.items(), key=lambda x: x[1])
        return priority

    def tick(self, environment_effects: dict[str, float] | None = None):
        """Advance needs over time."""
        self.hunger = min(1.0, self.hunger + 0.02)
        self.thirst = min(1.0, self.thirst + 0.03)
        self.rest = min(1.0, self.rest + 0.01)
        self.achievement = max(0.0, self.achievement - 0.005)

        if environment_effects:
            self.safety = max(0.0, min(1.0,
                self.safety + environment_effects.get('safety_change', 0)))


@dataclass
class AgentStats:
    """Agent's current status and vitals."""
    health: float = 100.0
    max_health: float = 100.0
    energy: float = 100.0
    max_energy: float = 100.0

    # Status effects
    injured: bool = False
    sick: bool = False
    stressed: bool = False
    buffed: bool = False

    # Combat stats
    attack_power: float = 10.0
    defense: float = 5.0
    speed: float = 5.0

    def is_alive(self) -> bool:
        return self.health > 0

    def get_health_percent(self) -> float:
        return self.health / self.max_health

    def get_energy_percent(self) -> float:
        return self.energy / self.max_energy

    def modify_health(self, amount: float):
        self.health = max(0.0, min(self.max_health, self.health + amount))
        if self.health < self.max_health * 0.3:
            self.injured = True

    def modify_energy(self, amount: float):
        self.energy = max(0.0, min(self.max_energy, self.energy + amount))


class IntegratedAgent:
    """
    Fully-featured agent with all enhanced capabilities.
    """

    def __init__(
        self,
        agent_id: str | None = None,
        name: str = "Agent",
        ocean_traits: dict[str, float] | None = None,
        initial_location: tuple[int, int] = (0, 0)
    ):
        self.agent_id = agent_id or str(uuid.uuid4())
        self.name = name
        self.location = initial_location

        # Core systems
        self.ocean_traits = ocean_traits or {
            'openness': 0.5,
            'conscientiousness': 0.5,
            'extraversion': 0.5,
            'agreeableness': 0.5,
            'neuroticism': 0.5
        }

        self.emotional_state = EmotionalState()
        # TODO: Implement influenced_by_personality method in EmotionalState
        # self.emotional_state.influenced_by_personality(self.ocean_traits)

        self.memory = AgentMemory()
        self.needs = AgentNeeds()
        self.stats = AgentStats()

        # Action system
        self.action_library = ActionLibrary()
        self.known_actions: list[str] = ['move', 'rest', 'eat', 'drink']
        self.action_cooldowns: dict[str, int] = {}

        # Behavior tree
        self.behavior_tree: BehaviorTree | None = None
        self.blackboard = Blackboard()
        self._setup_blackboard()

        # Teamwork
        self.current_team: Team | None = None
        self.team_role: TeamRole | None = None
        self.team_coordination_skill: float = random.uniform(0.3, 0.8)

        # Security
        self.security_clearance: int = 1
        self.assigned_capabilities: list[Capability] = []

        # State tracking
        self.current_action: str | None = None
        self.action_progress: float = 0.0
        self.tick_count: int = 0

        # Callbacks
        self.on_action_complete: Callable | None = None
        self.on_emotion_change: Callable | None = None
        self.on_team_join: Callable | None = None

    def _setup_blackboard(self):
        """Initialize behavior tree blackboard."""
        self.blackboard.set('agent', self)
        self.blackboard.set('location', self.location)
        self.blackboard.set('emotional_state', self.emotional_state)
        self.blackboard.set('needs', self.needs)
        self.blackboard.set('stats', self.stats)
        self.blackboard.set('memory', self.memory)
        self.blackboard.set('current_action', None)
        self.blackboard.set('target_location', None)
        self.blackboard.set('threat_detected', False)
        self.blackboard.set('team_available', False)

    def set_behavior_tree(self, tree_name: str = 'agent_ai'):
        """Set up behavior tree from library."""
        library = BehaviorTreeLibrary()
        self.behavior_tree = library.create_tree(tree_name, self.blackboard)

    def tick(
        self,
        environment,
        security_governor: SecurityGovernor | None = None,
        nearby_agents: list['IntegratedAgent'] | None = None
    ) -> dict[str, Any]:
        """
        Execute one agent tick with all systems.
        """
        self.tick_count += 1
        results = {
            'agent_id': self.agent_id,
            'actions': [],
            'emotional_changes': [],
            'perceptions': [],
            'decisions': []
        }

        # 1. Perceive environment
        perceptions = self._perceive_environment(environment)
        results['perceptions'] = perceptions

        # 2. Update needs
        env_effects = environment.get_emotional_modifiers() if hasattr(environment, 'get_emotional_modifiers') else {}
        self.needs.tick(env_effects)

        # 3. Apply environmental effects
        if hasattr(environment, 'apply_to_agent'):
            effects = environment.apply_to_agent(self)
            self._apply_environmental_effects(effects)

        # 4. Emotional contagion from nearby agents
        if nearby_agents:
            for other in nearby_agents:
                if self._distance_to(other) <= 3:  # Within emotional contagion range
                    # Calculate contagion strength
                    dominant_emotion, intensity = other.emotional_state.get_dominant_emotion()
                    strength = EmotionalContagion.calculate_contagion_strength(
                        source_emotion=intensity,
                        relationship_trust=0.5,
                        relationship_affection=0.5,
                        target_empathy=self.ocean_traits.get('agreeableness', 0.5),
                        distance=self._distance_to(other) / 10.0,
                        source_expressiveness=other.ocean_traits.get('extraversion', 0.5)
                    )
                    if strength > 0.1:
                        contagion_result = EmotionalContagion.apply_contagion(
                            source_state=other.emotional_state,
                            target_state=self.emotional_state,
                            emotion=dominant_emotion,
                            strength=strength
                        )
                        if contagion_result.get('transferred', 0) > 0:
                            results['emotional_changes'].append({
                                'source': other.agent_id,
                                'changes': contagion_result
                            })

        # 5. Update blackboard with current state
        self._update_blackboard(environment, nearby_agents)

        # 6. Execute behavior tree
        if self.behavior_tree:
            status = self.behavior_tree.tick()
            results['bt_status'] = status.name

            # Check for action execution
            current = self.blackboard.get('current_action')
            if current and current != self.current_action:
                self.current_action = current
                results['actions'].append(f"started_{current}")

        # 7. Execute current action
        if self.current_action:
            action_result = self._execute_current_action(environment, security_governor)
            results['actions'].append(action_result)

        # 8. Regenerate energy
        self.stats.modify_energy(2.0)

        # 9. Update cooldowns
        for action in list(self.action_cooldowns.keys()):
            self.action_cooldowns[action] -= 1
            if self.action_cooldowns[action] <= 0:
                del self.action_cooldowns[action]

        # 10. Record memory
        self.memory.add_experience({
            'tick': self.tick_count,
            'location': self.location,
            'action': self.current_action,
            'emotional_state': self.emotional_state.get_dominant_emotion(),
            'health': self.stats.health,
            'energy': self.stats.energy
        }, importance=0.5)

        return results

    def _perceive_environment(self, environment) -> list[dict[str, Any]]:
        """Perceive the environment and return observations."""
        perceptions = []

        # Check visibility
        if hasattr(environment, 'get_visibility'):
            environment.get_visibility()

        # Detect hazards
        if hasattr(environment, 'get_active_threats'):
            threats = environment.get_active_threats(self.location)
            for threat in threats:
                perceptions.append({
                    'type': 'threat',
                    'hazard_type': threat.hazard_type.name,
                    'severity': threat.severity.name,
                    'distance': self._distance_to_point(threat.location),
                    'urgency': threat.severity.value / 5.0
                })

                # Emotional response to threat
                self.emotional_state.apply_stimulus(
                    EmotionType.FEAR,
                    threat.severity.value / 10.0
                )

        # Detect events
        if hasattr(environment, 'events'):
            for event in environment.events.values():
                if event.active and self.location in event.affected_zones:
                    perceptions.append({
                        'type': 'event',
                        'event_name': event.name,
                        'requires_teamwork': event.requires_teamwork
                    })

        # Weather perception
        if hasattr(environment, 'weather'):
            weather = environment.weather
            perceptions.append({
                'type': 'weather',
                'condition': weather.weather_type.name,
                'temperature': weather.temperature,
                'comfort': 1.0 - abs(weather.temperature - 20) / 40
            })

        return perceptions

    def _apply_environmental_effects(self, effects: dict[str, Any]):
        """Apply environmental effects to agent."""
        # Health effects
        if 'health_effects' in effects:
            self.stats.modify_health(effects['health_effects'])

        # Emotional effects
        if 'emotional_changes' in effects:
            for emotion, value in effects['emotional_changes'].items():
                try:
                    emotion_type = EmotionType[emotion.upper()]
                    self.emotional_state.apply_stimulus(emotion_type, value)
                except (KeyError, ValueError):
                    pass

        # Action modifiers
        if 'action_modifiers' in effects:
            # Store for action execution
            self.blackboard.set('action_modifiers', effects['action_modifiers'])

    def _update_blackboard(self, environment, nearby_agents: list['IntegratedAgent'] | None):
        """Update behavior tree blackboard."""
        self.blackboard.set('location', self.location)
        self.blackboard.set('emotional_state', self.emotional_state)
        self.blackboard.set('needs', self.needs)
        self.blackboard.set('stats', self.stats)

        # Update threat detection
        has_threat = any(
            p['type'] == 'threat' and p['urgency'] > 0.5
            for p in self._perceive_environment(environment)
        )
        self.blackboard.set('threat_detected', has_threat)

        # Update team availability
        team_available = (
            self.current_team is not None and
            len(self.current_team.members) >= 2
        )
        self.blackboard.set('team_available', team_available)

        # Update nearby agents
        self.blackboard.set('nearby_agents', nearby_agents)

        # Check for priority needs
        priority_need, urgency = self.needs.get_priority_need()
        self.blackboard.set('priority_need', priority_need)
        self.blackboard.set('need_urgency', urgency)

    def _execute_current_action(
        self,
        environment,
        security_governor: SecurityGovernor | None
    ) -> dict[str, Any]:
        """Execute the current action."""
        action_name = self.current_action

        # Security check
        if security_governor and action_name:
            security_context = SecurityContext(
                subject_id=self.agent_id,
                resource_id='world',
                action=action_name
            )
            allowed, reason = security_governor.evaluate_access(
                subject=self,
                resource=environment,
                capability=Capability.EXECUTE,
                context=security_context
            )
            if not allowed:
                self.current_action = None
                return {
                    'action': action_name,
                    'status': 'denied',
                    'reason': reason
                }

        # Execute action
        if action_name in self.known_actions:
            action = self.action_library.get_action(action_name)
            if action:
                context = ActionContext(
                    agent=self,
                    location=self.location,
                    world_state=environment
                )

                can_execute, reasons = action.can_execute(context)
                if can_execute:
                    result = action.execute(context)
                    self.action_progress = 0.0

                    # Apply costs
                    self.stats.modify_energy(-action.costs.energy_cost)
                    self.needs.hunger = min(1.0, self.needs.hunger + action.costs.hunger_increase)

                    # Apply emotional effects
                    for emotion, value in action.costs.emotional_stress.items():
                        try:
                            emotion_type = EmotionType[emotion.upper()]
                            self.emotional_state.apply_stimulus(emotion_type, value)
                        except (KeyError, ValueError):
                            pass

                    self.current_action = None

                    return {
                        'action': action_name,
                        'status': 'completed',
                        'result': result
                    }
                else:
                    return {
                        'action': action_name,
                        'status': 'cannot_execute',
                        'reasons': reasons
                    }

        # Default: simple actions
        if action_name == 'move':
            target = self.blackboard.get('target_location')
            if target:
                self._move_toward(target)
                return {'action': 'move', 'status': 'in_progress'}

        elif action_name == 'rest':
            self.stats.modify_energy(20.0)
            self.needs.rest = max(0.0, self.needs.rest - 0.3)
            self.current_action = None
            return {'action': 'rest', 'status': 'completed'}

        return {'action': action_name, 'status': 'unknown_action'}

    def _move_toward(self, target: tuple[int, int]):
        """Move one step toward target."""
        dx = 1 if target[0] > self.location[0] else -1 if target[0] < self.location[0] else 0
        dy = 1 if target[1] > self.location[1] else -1 if target[1] < self.location[1] else 0

        self.location = (self.location[0] + dx, self.location[1] + dy)
        self.stats.modify_energy(-2.0)

    def _distance_to(self, other: 'IntegratedAgent') -> float:
        """Calculate distance to another agent."""
        return self._distance_to_point(other.location)

    def _distance_to_point(self, point: tuple[int, int]) -> float:
        """Calculate distance to a point."""
        return ((self.location[0] - point[0])**2 +
                (self.location[1] - point[1])**2)**0.5

    def join_team(self, team: Team, role: TeamRole = TeamRole.MEMBER) -> bool:
        """Join a team."""
        if team.add_member(self.agent_id, role):
            self.current_team = team
            self.team_role = role

            if self.on_team_join:
                self.on_team_join(team, role)

            return True
        return False

    def leave_team(self):
        """Leave current team."""
        if self.current_team:
            self.current_team.remove_member(self.agent_id)
            self.current_team = None
            self.team_role = None

    def get_state_summary(self) -> dict[str, Any]:
        """Get comprehensive agent state summary."""
        return {
            'agent_id': self.agent_id,
            'name': self.name,
            'location': self.location,
            'health': self.stats.health,
            'energy': self.stats.energy,
            'alive': self.stats.is_alive(),
            'emotional_state': {
                'dominant': self.emotional_state.get_dominant_emotion(),
                'valence': self.emotional_state.get_valence(),
                'arousal': self.emotional_state.get_arousal()
            },
            'needs': {
                'priority': self.needs.get_priority_need()[0],
                'urgency': self.needs.get_priority_need()[1]
            },
            'current_action': self.current_action,
            'team': self.current_team.id if self.current_team else None,
            'team_role': self.team_role.name if self.team_role else None
        }
