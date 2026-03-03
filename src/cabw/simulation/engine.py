"""
Enhanced Simulation Engine

Integrates all advanced systems:
- Integrated agents with behavior trees
- Dynamic world environment
- Teamwork and shared goals
- Security governance
- Social dynamics and emotional contagion
"""

from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from datetime import datetime
import asyncio
import json

from ..core.integrated_agent import IntegratedAgent
from ..core.world_features import WorldEnvironment, EnvironmentEffectSystem
from ..core.teamwork import Team, TeamManager, SharedGoal, GoalTemplates
from ..core.emotions import GroupEmotionalClimate
from ..governance.security import SecurityGovernor, SecurityPolicy, Capability


@dataclass
class SimulationConfig:
    """Configuration for simulation run."""
    world_size: tuple = (20, 20)
    tick_rate: float = 1.0  # ticks per second
    max_ticks: int = 1000
    
    # Agent settings
    num_agents: int = 10
    agent_personality_variance: float = 0.3
    
    # Environment settings
    weather_enabled: bool = True
    hazards_enabled: bool = True
    events_enabled: bool = True
    
    # Teamwork settings
    teamwork_enabled: bool = True
    auto_form_teams: bool = True
    min_team_size: int = 2
    max_team_size: int = 5
    
    # Security settings
    security_level: str = 'standard'  # low, standard, high, maximum
    audit_all_actions: bool = True
    
    # Callbacks
    on_tick: Optional[Callable] = None
    on_agent_action: Optional[Callable] = None
    on_event: Optional[Callable] = None


class EnhancedSimulation:
    """
    Full-featured simulation engine with all advanced systems.
    """
    
    def __init__(self, config: SimulationConfig = None):
        self.config = config or SimulationConfig()
        
        # Core systems
        self.environment = WorldEnvironment(self.config.world_size)
        self.effect_system = EnvironmentEffectSystem(self.environment)
        self.security_governor = self._setup_security()
        self.team_manager = TeamManager()
        
        # Agents
        self.agents: Dict[str, IntegratedAgent] = {}
        self.agent_positions: Dict[str, tuple] = {}
        
        # State tracking
        self.tick_count = 0
        self.running = False
        self.paused = False
        
        # History
        self.state_history: List[Dict[str, Any]] = []
        self.event_log: List[Dict[str, Any]] = []
        self.agent_action_log: List[Dict[str, Any]] = []
        
        # Group emotional climate
        self.emotional_climate = GroupEmotionalClimate()
        
        # Statistics
        self.statistics = {
            'total_actions': 0,
            'team_formations': 0,
            'goals_completed': 0,
            'hazards_resolved': 0,
            'security_violations': 0,
            'emotional_contagion_events': 0
        }
    
    def _setup_security(self) -> SecurityGovernor:
        """Set up security governor based on config."""
        governor = SecurityGovernor()
        
        # Configure based on security level
        level_configs = {
            'low': {'rate_limit': 100, 'block_threshold': 20},
            'standard': {'rate_limit': 50, 'block_threshold': 10},
            'high': {'rate_limit': 20, 'block_threshold': 5},
            'maximum': {'rate_limit': 10, 'block_threshold': 3}
        }
        
        config = level_configs.get(self.config.security_level, level_configs['standard'])
        
        # Add default policy
        default_policy = SecurityPolicy(
            policy_id='default',
            name='Default Security Policy',
            description='Standard access control',
            rules=[
                lambda s, r, c, ctx: (True, None)  # Allow all by default
            ],
            required_capabilities=[],
            rate_limit=config['rate_limit']
        )
        governor.register_policy('default', default_policy)
        
        # Add restricted action policy
        restricted_policy = SecurityPolicy(
            policy_id='restricted',
            name='Restricted Actions',
            description='Actions requiring elevated clearance',
            rules=[
                lambda s, r, c, ctx: (
                    getattr(s, 'security_clearance', 0) >= 2,
                    'Insufficient security clearance'
                )
            ],
            required_capabilities=[Capability.ACTION_EXECUTE]
        )
        governor.register_policy('restricted', restricted_policy)
        
        return governor
    
    def add_agent(
        self,
        name: str,
        ocean_traits: Optional[Dict[str, float]] = None,
        location: Optional[tuple] = None,
        behavior_tree: str = 'agent_ai'
    ) -> IntegratedAgent:
        """Add an agent to the simulation."""
        if location is None:
            import random
            location = (
                random.randint(0, self.config.world_size[0] - 1),
                random.randint(0, self.config.world_size[1] - 1)
            )
        
        agent = IntegratedAgent(
            name=name,
            ocean_traits=ocean_traits,
            initial_location=location
        )
        
        # Set up behavior tree
        agent.set_behavior_tree(behavior_tree)
        
        # Register with systems
        self.agents[agent.agent_id] = agent
        self.agent_positions[agent.agent_id] = location
        
        # Log
        self._log_event('agent_added', {
            'agent_id': agent.agent_id,
            'name': name,
            'location': location
        })
        
        return agent
    
    def initialize(self):
        """Initialize simulation with default agents."""
        import random
        
        # Create agents with varied personalities
        for i in range(self.config.num_agents):
            # Generate varied OCEAN traits
            base_traits = {
                'openness': random.uniform(0.2, 0.8),
                'conscientiousness': random.uniform(0.2, 0.8),
                'extraversion': random.uniform(0.2, 0.8),
                'agreeableness': random.uniform(0.2, 0.8),
                'neuroticism': random.uniform(0.2, 0.8)
            }
            
            agent = self.add_agent(
                name=f"Agent_{i+1}",
                ocean_traits=base_traits
            )
            
            # Assign random security clearance
            agent.security_clearance = random.randint(1, 3)
        
        self._log_event('simulation_initialized', {
            'num_agents': len(self.agents),
            'world_size': self.config.world_size
        })
    
    async def run(self):
        """Run the simulation loop."""
        self.running = True
        
        while self.running and self.tick_count < self.config.max_ticks:
            if not self.paused:
                await self.tick()
                
                if self.config.on_tick:
                    self.config.on_tick(self.tick_count, self.get_state())
            
            await asyncio.sleep(1.0 / self.config.tick_rate)
        
        self.running = False
        self._log_event('simulation_ended', {
            'total_ticks': self.tick_count,
            'statistics': self.statistics
        })
    
    async def tick(self) -> Dict[str, Any]:
        """Execute one simulation tick."""
        self.tick_count += 1
        tick_results = {
            'tick': self.tick_count,
            'agent_results': {},
            'environment_results': {},
            'team_results': {},
            'events': []
        }
        
        # 1. Update environment
        env_results = self.environment.tick()
        tick_results['environment_results'] = env_results
        
        # Log new hazards
        for hazard_id in env_results.get('new_hazards', []):
            self._log_event('hazard_spawned', {'hazard_id': hazard_id})
        
        # 2. Update group emotional climate
        agent_emotions = {
            agent_id: agent.emotional_state 
            for agent_id, agent in self.agents.items()
        }
        self.emotional_climate.update_climate(agent_emotions)
        
        # 3. Process agents
        for agent_id, agent in self.agents.items():
            if not agent.stats.is_alive():
                continue
            
            # Get nearby agents for emotional contagion
            nearby = self._get_nearby_agents(agent_id, radius=3)
            
            # Execute agent tick
            agent_result = agent.tick(
                environment=self.environment,
                security_governor=self.security_governor,
                nearby_agents=nearby
            )
            
            tick_results['agent_results'][agent_id] = agent_result
            
            # Update position tracking
            self.agent_positions[agent_id] = agent.location
            
            # Log actions
            for action in agent_result.get('actions', []):
                if isinstance(action, dict):
                    self._log_agent_action(agent_id, action)
                    self.statistics['total_actions'] += 1
            
            # Count emotional contagion
            if agent_result.get('emotional_changes'):
                self.statistics['emotional_contagion_events'] += len(
                    agent_result['emotional_changes']
                )
        
        # 4. Auto-form teams if enabled
        if self.config.teamwork_enabled and self.config.auto_form_teams:
            self._process_team_formation()
        
        # 5. Update teams and goals
        if self.config.teamwork_enabled:
            team_results = self.team_manager.update_teams()
            tick_results['team_results'] = team_results
            
            # Track completed goals
            for result in team_results.values():
                if result.get('goal_completed'):
                    self.statistics['goals_completed'] += 1
        
        # 6. Check for environmental events requiring response
        self._process_environmental_events()
        
        # 7. Record state snapshot
        if self.tick_count % 10 == 0:  # Every 10 ticks
            self.state_history.append(self.get_state())
        
        return tick_results
    
    def _get_nearby_agents(
        self, 
        agent_id: str, 
        radius: float = 3.0
    ) -> List[IntegratedAgent]:
        """Get agents within radius of given agent."""
        agent = self.agents.get(agent_id)
        if not agent:
            return []
        
        nearby = []
        for other_id, other in self.agents.items():
            if other_id != agent_id and other.stats.is_alive():
                distance = ((agent.location[0] - other.location[0])**2 +
                          (agent.location[1] - other.location[1])**2)**0.5
                if distance <= radius:
                    nearby.append(other)
        
        return nearby
    
    def _process_team_formation(self):
        """Automatically form teams based on proximity and goals."""
        import random
        
        # Find agents near hazards who could form response teams
        for hazard in self.environment.hazards.values():
            if hazard.active and hazard.get_requires_teamwork() and not hazard.contained:
                # Find nearby agents
                nearby_agents = []
                for agent_id, agent in self.agents.items():
                    if agent.stats.is_alive() and not agent.current_team:
                        distance = ((agent.location[0] - hazard.location[0])**2 +
                                  (agent.location[1] - hazard.location[1])**2)**0.5
                        if distance <= 5:
                            nearby_agents.append(agent)
                
                # Form team if enough agents
                if len(nearby_agents) >= self.config.min_team_size:
                    team = self.team_manager.create_team(
                        f"Response_{hazard.hazard_id}",
                        f"Emergency response to {hazard.hazard_type.name}"
                    )
                    
                    for agent in nearby_agents[:self.config.max_team_size]:
                        from ..core.teamwork import TeamRole, TeamMember
                        
                        role = TeamRole.LEADER if not team.members else TeamRole.MEMBER
                        member = TeamMember(
                            agent_id=agent.agent_id,
                            role=role,
                            coordination_skill=agent.team_coordination_skill
                        )
                        team.add_member(member)
                        agent.current_team = team
                        agent.team_role = role
                    
                    self.statistics['team_formations'] += 1
                    self._log_event('team_formed', {
                        'team_id': team.team_id,
                        'purpose': 'hazard_response',
                        'hazard_id': hazard.hazard_id,
                        'members': list(team.members.keys())
                    })
    
    def _process_environmental_events(self):
        """Process active environmental events."""
        for event in self.environment.events.values():
            if event.active and event.requires_teamwork and not event.resolved:
                # Check if there's a team assigned
                has_team = any(
                    agent.current_team for agent in self.agents.values()
                    if agent.location in event.affected_zones
                )
                
                if not has_team:
                    # Create response goal
                    goal = GoalTemplates.emergency_response(
                        f"Respond to {event.name}",
                        urgency=0.8
                    )
                    self.team_manager.assign_goal_to_team(goal)
    
    def create_team_goal(
        self,
        team_id: str,
        goal_type: str,
        **params
    ) -> Optional[SharedGoal]:
        """Create and assign a goal to a team."""
        team = self.team_manager.get_team(team_id)
        if not team:
            return None
        
        # Create goal from template
        if goal_type == 'exploration':
            goal = GoalTemplates.exploration(**params)
        elif goal_type == 'resource_gathering':
            goal = GoalTemplates.resource_gathering(**params)
        elif goal_type == 'defense':
            goal = GoalTemplates.defense(**params)
        elif goal_type == 'construction':
            goal = GoalTemplates.construction(**params)
        elif goal_type == 'emergency_response':
            goal = GoalTemplates.emergency_response(**params)
        else:
            return None
        
        # Assign to team
        if self.team_manager.assign_goal_to_team(goal, team_id):
            self._log_event('goal_assigned', {
                'team_id': team_id,
                'goal_type': goal_type,
                'goal_id': goal.goal_id
            })
            return goal
        
        return None
    
    def trigger_event(self, event_type: str, **kwargs) -> Any:
        """Manually trigger an environmental event."""
        event = self.environment.create_event(event_type, **kwargs)
        self._log_event('manual_event_triggered', {
            'event_type': event_type,
            'event_id': event.event_id
        })
        return event
    
    def get_state(self) -> Dict[str, Any]:
        """Get complete simulation state."""
        return {
            'tick': self.tick_count,
            'timestamp': datetime.now().isoformat(),
            'environment': self.environment.get_environmental_summary(),
            'agents': {
                agent_id: agent.get_state_summary()
                for agent_id, agent in self.agents.items()
            },
            'teams': {
                team_id: {
                    'member_count': len(team.members),
                    'active_goals': len(team.active_goals),
                    'cohesion': team.get_team_cohesion()
                }
                for team_id, team in self.team_manager.teams.items()
            },
            'emotional_climate': {
                'dominant': self.emotional_climate.get_dominant_emotion(),
                'intensity': self.emotional_climate.get_emotional_intensity(),
                'stability': self.emotional_climate.get_climate_stability()
            },
            'statistics': self.statistics
        }
    
    def _log_event(self, event_type: str, data: Dict[str, Any]):
        """Log a simulation event."""
        entry = {
            'tick': self.tick_count,
            'timestamp': datetime.now().isoformat(),
            'event_type': event_type,
            'data': data
        }
        self.event_log.append(entry)
        
        if self.config.on_event:
            self.config.on_event(event_type, data)
    
    def _log_agent_action(self, agent_id: str, action: Dict[str, Any]):
        """Log an agent action."""
        entry = {
            'tick': self.tick_count,
            'timestamp': datetime.now().isoformat(),
            'agent_id': agent_id,
            'action': action
        }
        self.agent_action_log.append(entry)
        
        if self.config.on_agent_action:
            self.config.on_agent_action(agent_id, action)
    
    def pause(self):
        """Pause simulation."""
        self.paused = True
        self._log_event('simulation_paused', {'tick': self.tick_count})
    
    def resume(self):
        """Resume simulation."""
        self.paused = False
        self._log_event('simulation_resumed', {'tick': self.tick_count})
    
    def stop(self):
        """Stop simulation."""
        self.running = False
    
    def export_results(self, filepath: str):
        """Export simulation results to file."""
        results = {
            'config': {
                'world_size': self.config.world_size,
                'num_agents': self.config.num_agents,
                'max_ticks': self.config.max_ticks,
                'security_level': self.config.security_level
            },
            'final_state': self.get_state(),
            'statistics': self.statistics,
            'event_log': self.event_log,
            'action_log': self.agent_action_log[-1000:],  # Last 1000 actions
            'state_snapshots': self.state_history
        }
        
        with open(filepath, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        
        return filepath
