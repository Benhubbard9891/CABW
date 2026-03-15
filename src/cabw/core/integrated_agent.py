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

from collections import deque
from dataclasses import dataclass, field
from typing import Deque, Dict, List, Optional, Tuple, Any, Callable
from datetime import datetime
import uuid
import random

from .emotions import EmotionalState, EmotionType, EmotionalContagion
from .actions import ComplexAction, ActionLibrary, ActionContext
from .behavior_tree import BehaviorTree, Blackboard, BehaviorTreeLibrary
from .teamwork import Team, TeamRole, SharedGoal
from ..governance.security import SecurityGovernor, Capability, SecurityContext


@dataclass
class AgentMemory:
    """Agent's working and long-term memory."""
    short_term: List[Dict[str, Any]] = field(default_factory=list)
    long_term: Dict[str, Any] = field(default_factory=dict)
    max_short_term: int = 10
    
    def add_experience(self, experience: Dict[str, Any], importance: float = 0.5):
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
    
    def recall_relevant(self, context: str, limit: int = 3) -> List[Dict[str, Any]]:
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
    
    def get_priority_need(self) -> Tuple[str, float]:
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
    
    def tick(self, environment_effects: Dict[str, float] = None):
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
        agent_id: Optional[str] = None,
        name: str = "Agent",
        ocean_traits: Optional[Dict[str, float]] = None,
        initial_location: Tuple[int, int] = (0, 0),
        agent_role: str = 'executor',
    ):
        self.agent_id = agent_id or str(uuid.uuid4())
        self.name = name
        self.location = initial_location

        # Governance role – drives token QoS allocation in SecurityGovernor.
        # Valid values: 'executor', 'monitor', 'builder', 'coordinator', 'manager'
        self.agent_role: str = agent_role
        
        # Core systems
        self.ocean_traits = ocean_traits or {
            'openness': 0.5,
            'conscientiousness': 0.5,
            'extraversion': 0.5,
            'agreeableness': 0.5,
            'neuroticism': 0.5
        }
        
        self.emotional_state = EmotionalState()
        self.emotional_state.influenced_by_personality(self.ocean_traits)
        
        self.memory = AgentMemory()
        self.needs = AgentNeeds()
        self.stats = AgentStats()
        
        # Action system
        self.action_library = ActionLibrary()
        self.known_actions: List[str] = ['move', 'rest', 'eat', 'drink']
        self.action_cooldowns: Dict[str, int] = {}
        
        # Behavior tree
        self.behavior_tree: Optional[BehaviorTree] = None
        self.blackboard = Blackboard()
        self._setup_blackboard()
        
        # Teamwork
        self.current_team: Optional[Team] = None
        self.team_role: Optional[TeamRole] = None
        self.team_coordination_skill: float = random.uniform(0.3, 0.8)
        
        # Security
        self.security_clearance: int = 1
        self.assigned_capabilities: List[Capability] = []

        # State tracking
        self.current_action: Optional[str] = None
        self.action_progress: float = 0.0
        self.tick_count: int = 0

        # --- Divergence / AMPA tracking (AMPA 1.7.1 Precipice Metric) ---
        # Rolling window of governance events for threshold detection.
        self.divergence_history: Deque[Dict[str, Any]] = deque(maxlen=30)
        # Set True when >15% of the last 15 events are critical (severity > 0.1).
        # Provides 20-30 tick advance warning before coherence collapse.
        self.at_threshold: bool = False
        # Cumulative violation counter (exposed in AMPA metrics)
        self.violations: int = 0
        # Drift signatures detected (e.g. repeated denial patterns)
        self.drift_signatures: List[str] = []

        # Callbacks
        self.on_action_complete: Optional[Callable] = None
        self.on_emotion_change: Optional[Callable] = None
        self.on_team_join: Optional[Callable] = None
    
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
        security_governor: Optional[SecurityGovernor] = None,
        nearby_agents: List['IntegratedAgent'] = None
    ) -> Dict[str, Any]:
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
            contagion = EmotionalContagion()
            for other in nearby_agents:
                if self._distance_to(other) <= 3:  # Within emotional contagion range
                    changes = contagion.spread_emotion(self.emotional_state, other.emotional_state)
                    if changes:
                        results['emotional_changes'].append({
                            'source': other.agent_id,
                            'changes': changes
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
    
    def _perceive_environment(self, environment) -> List[Dict[str, Any]]:
        """Perceive the environment and return observations."""
        perceptions = []
        
        # Check visibility
        visibility = 1.0
        if hasattr(environment, 'get_visibility'):
            visibility = environment.get_visibility()
        
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
    
    def _apply_environmental_effects(self, effects: Dict[str, Any]):
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
    
    def _update_blackboard(self, environment, nearby_agents: List['IntegratedAgent']):
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
        security_governor: Optional[SecurityGovernor]
    ) -> Dict[str, Any]:
        """Execute the current action."""
        action_name = self.current_action
        
        # Security check
        if security_governor:
            security_context = SecurityContext(
                subject_id=self.agent_id,
                resource_id='world',
                action=action_name
            )
            allowed, reason = security_governor.evaluate_access(
                subject=self,
                resource=environment,
                capability=Capability.ACTION_EXECUTE,
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
    
    def _move_toward(self, target: Tuple[int, int]):
        """Move one step toward target."""
        dx = 1 if target[0] > self.location[0] else -1 if target[0] < self.location[0] else 0
        dy = 1 if target[1] > self.location[1] else -1 if target[1] < self.location[1] else 0
        
        self.location = (self.location[0] + dx, self.location[1] + dy)
        self.stats.modify_energy(-2.0)
    
    def _distance_to(self, other: 'IntegratedAgent') -> float:
        """Calculate distance to another agent."""
        return self._distance_to_point(other.location)
    
    def _distance_to_point(self, point: Tuple[int, int]) -> float:
        """Calculate distance to a point."""
        return ((self.location[0] - point[0])**2 + 
                (self.location[1] - point[1])**2)**0.5
    
    def join_team(self, team: Team, role: TeamRole = TeamRole.MEMBER) -> bool:
        """Join a team."""
        from .teamwork import TeamMember
        
        member = TeamMember(
            agent_id=self.agent_id,
            role=role,
            coordination_skill=self.team_coordination_skill,
            commitment=0.7
        )
        
        if team.add_member(member):
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
    
    def coherence_score(self) -> float:
        """Compute a 0–1 coherence score (0 = incoherent, 1 = fully coherent).

        Combines health, energy and emotional stability.  Used by the governor's
        cascade-threshold detector (check_cascade_threshold).
        """
        health_factor = self.stats.health / max(self.stats.max_health, 1)
        energy_factor = self.stats.energy / max(self.stats.max_energy, 1)

        # Emotional stability: high arousal and extreme valence reduce coherence
        valence = self.emotional_state.get_valence()   # typically -1..1
        arousal = self.emotional_state.get_arousal()   # typically 0..1
        emotional_stability = max(
            0.0,
            1.0 - abs(valence) * 0.5 - arousal * 0.3
        )

        return (health_factor * 0.4 + energy_factor * 0.3 + emotional_stability * 0.3)

    def record_governance_event(self, event_type: str, severity: float) -> None:
        """Record a governance event and check the divergence threshold.

        Args:
            event_type: One of 'denial', 'violation', 'timeout'.
            severity:   Normalised severity in [0, 1].  Events with severity > 0.1
                        count toward the threshold rate.

        Sets self.at_threshold = True when >15% of the last 15 events are critical,
        giving a 20-30 tick early warning of impending coherence collapse.
        """
        self.divergence_history.append({
            'tick': self.tick_count,
            'type': event_type,
            'severity': severity,
        })

        if event_type == 'violation':
            self.violations += 1
            if 'REPEATED_DENIAL' not in self.drift_signatures:
                denial_count = sum(
                    1 for e in self.divergence_history if e['type'] == 'denial'
                )
                if denial_count >= 5:
                    self.drift_signatures.append('REPEATED_DENIAL')

        # Threshold detection – 15-event rolling window, >15% critical events
        if len(self.divergence_history) >= 15:
            recent = list(self.divergence_history)[-15:]
            threshold_rate = sum(1 for e in recent if e['severity'] > 0.1) / 15
            self.at_threshold = threshold_rate > 0.15
        else:
            self.at_threshold = False

    def get_state_summary(self) -> Dict[str, Any]:
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
            'team': self.current_team.team_id if self.current_team else None,
            'team_role': self.team_role.name if self.team_role else None,
            'agent_role': self.agent_role,
            'coherence': round(self.coherence_score(), 3),
            'at_threshold': self.at_threshold,
            'violations': self.violations,
        }
