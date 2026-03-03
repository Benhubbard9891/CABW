"""
Teamwork and Shared Goal System for CABW Enterprise.

Implements:
- Team formation and management
- Shared goals with contribution tracking
- Role assignment and coordination
- Team performance metrics
- Emergent team behaviors
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto
from typing import Any, Dict, List, Optional, Set, Tuple
from uuid import UUID, uuid4

from cabw.utils.logging import get_logger

logger = get_logger(__name__)


class TeamRole(Enum):
    """Roles within a team."""
    LEADER = "leader"
    TACTICIAN = "tactician"
    SUPPORT = "support"
    DAMAGE = "damage"
    TANK = "tank"
    SCOUT = "scout"
    MEDIC = "medic"
    SPECIALIST = "specialist"


class GoalStatus(Enum):
    """Status of a team goal."""
    PENDING = auto()
    ACTIVE = auto()
    COMPLETED = auto()
    FAILED = auto()
    ABANDONED = auto()


class GoalPriority(Enum):
    """Priority levels for goals."""
    CRITICAL = 4
    HIGH = 3
    MEDIUM = 2
    LOW = 1
    OPTIONAL = 0


@dataclass
class GoalObjective:
    """Individual objective within a larger goal."""
    id: str
    description: str
    required_role: Optional[TeamRole] = None
    completion_condition: Dict[str, Any] = field(default_factory=dict)
    is_completed: bool = False
    assigned_to: Optional[str] = None
    
    def check_completion(self, context: Dict[str, Any]) -> bool:
        """Check if objective is completed."""
        if self.is_completed:
            return True
        
        condition_type = self.completion_condition.get('type')
        
        if condition_type == 'location':
            zone = context.get('zone')
            target = self.completion_condition.get('zone_id')
            return zone == target
        
        elif condition_type == 'item':
            inventory = context.get('inventory', {})
            item = self.completion_condition.get('item')
            count = self.completion_condition.get('count', 1)
            return inventory.get(item, 0) >= count
        
        elif condition_type == 'defeat':
            defeated = context.get('defeated', [])
            target = self.completion_condition.get('target')
            return target in defeated
        
        elif condition_type == 'protect':
            protected = context.get('protected', [])
            target = self.completion_condition.get('target')
            return target in protected
        
        return False


@dataclass
class SharedGoal:
    """
    A goal shared among team members.
    
    Goals have:
    - Multiple objectives that can be completed in parallel
    - Contribution tracking per member
    - Rewards distributed upon completion
    """
    id: str = field(default_factory=lambda: str(uuid4()))
    name: str = ""
    description: str = ""
    goal_type: str = "generic"  # 'combat', 'exploration', 'escort', 'gather', 'defend'
    priority: GoalPriority = GoalPriority.MEDIUM
    status: GoalStatus = GoalStatus.PENDING
    
    # Objectives
    objectives: List[GoalObjective] = field(default_factory=list)
    
    # Team assignment
    team_id: Optional[str] = None
    required_members: int = 2
    max_members: int = 6
    
    # Progress
    progress: float = 0.0  # 0-1
    contributions: Dict[str, float] = field(default_factory=dict)
    
    # Rewards
    rewards: Dict[str, Any] = field(default_factory=dict)
    
    # Timing
    created_at: datetime = field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    deadline: Optional[datetime] = None
    
    # Metadata
    difficulty: float = 1.0  # 0-2, affects rewards
    tags: Set[str] = field(default_factory=set)
    
    def start(self) -> None:
        """Activate the goal."""
        self.status = GoalStatus.ACTIVE
        self.started_at = datetime.utcnow()
        logger.info(f"Goal '{self.name}' started")
    
    def update_progress(self) -> None:
        """Recalculate progress based on objectives."""
        if not self.objectives:
            self.progress = 0.0
            return
        
        completed = sum(1 for obj in self.objectives if obj.is_completed)
        self.progress = completed / len(self.objectives)
        
        # Check for completion
        if self.progress >= 1.0:
            self.complete()
    
    def complete(self) -> None:
        """Mark goal as completed."""
        self.status = GoalStatus.COMPLETED
        self.completed_at = datetime.utcnow()
        self.progress = 1.0
        logger.info(f"Goal '{self.name}' completed!")
    
    def fail(self, reason: str = "") -> None:
        """Mark goal as failed."""
        self.status = GoalStatus.FAILED
        logger.info(f"Goal '{self.name}' failed: {reason}")
    
    def add_contribution(self, agent_id: str, amount: float) -> None:
        """Add contribution from an agent."""
        current = self.contributions.get(agent_id, 0)
        self.contributions[agent_id] = current + amount
    
    def get_top_contributors(self, n: int = 3) -> List[Tuple[str, float]]:
        """Get top contributors to this goal."""
        sorted_contribs = sorted(
            self.contributions.items(),
            key=lambda x: x[1],
            reverse=True
        )
        return sorted_contribs[:n]
    
    def calculate_rewards(self) -> Dict[str, Any]:
        """Calculate rewards based on completion and contributions."""
        if self.status != GoalStatus.COMPLETED:
            return {}
        
        base_rewards = self.rewards.copy()
        
        # Scale by difficulty
        for key in ['xp', 'gold', 'reputation']:
            if key in base_rewards:
                base_rewards[key] = int(base_rewards[key] * self.difficulty)
        
        # Distribute based on contribution
        total_contribution = sum(self.contributions.values())
        if total_contribution > 0:
            individual_rewards = {}
            for agent_id, contribution in self.contributions.items():
                share = contribution / total_contribution
                individual_rewards[agent_id] = {
                    k: int(v * share) if isinstance(v, (int, float)) else v
                    for k, v in base_rewards.items()
                }
            base_rewards['individual'] = individual_rewards
        
        return base_rewards
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'type': self.goal_type,
            'priority': self.priority.name,
            'status': self.status.name,
            'progress': round(self.progress, 2),
            'objectives': [
                {
                    'id': obj.id,
                    'description': obj.description,
                    'completed': obj.is_completed,
                    'assigned_to': obj.assigned_to,
                }
                for obj in self.objectives
            ],
            'contributions': self.contributions,
            'top_contributors': self.get_top_contributors(),
            'rewards': self.rewards,
            'created_at': self.created_at.isoformat(),
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
        }


@dataclass
class TeamMember:
    """Member of a team with role and status."""
    agent_id: str
    role: TeamRole = TeamRole.SPECIALIST
    joined_at: datetime = field(default_factory=datetime.utcnow)
    
    # Performance tracking
    goals_completed: int = 0
    goals_failed: int = 0
    contribution_score: float = 0.0
    reliability_score: float = 0.5
    
    # Status
    is_active: bool = True
    is_available: bool = True
    last_action: Optional[datetime] = None
    
    # Preferences
    preferred_roles: List[TeamRole] = field(default_factory=list)
    
    def record_goal_completion(self, success: bool, contribution: float) -> None:
        """Record goal completion."""
        if success:
            self.goals_completed += 1
        else:
            self.goals_failed += 1
        
        self.contribution_score += contribution
        
        # Update reliability
        total = self.goals_completed + self.goals_failed
        if total > 0:
            self.reliability_score = self.goals_completed / total
        
        self.last_action = datetime.utcnow()


@dataclass
class Team:
    """
    A team of agents working together.
    
    Teams have:
    - Members with assigned roles
    - Shared goals
    - Coordination mechanisms
    - Performance metrics
    """
    id: str = field(default_factory=lambda: str(uuid4()))
    name: str = ""
    description: str = ""
    
    # Members
    members: Dict[str, TeamMember] = field(default_factory=dict)
    leader_id: Optional[str] = None
    
    # Goals
    active_goals: List[SharedGoal] = field(default_factory=list)
    completed_goals: List[SharedGoal] = field(default_factory=list)
    
    # Performance
    formation_time: datetime = field(default_factory=datetime.utcnow)
    total_goals_completed: int = 0
    total_goals_failed: int = 0
    
    # Coordination
    coordination_level: float = 0.0  # 0-1
    communication_efficiency: float = 0.5
    
    # Metadata
    team_type: str = "ad_hoc"  # 'ad_hoc', 'guild', 'squad', 'party'
    tags: Set[str] = field(default_factory=set)
    
    def add_member(self, agent_id: str, role: TeamRole = TeamRole.SPECIALIST) -> TeamMember:
        """Add member to team."""
        member = TeamMember(agent_id=agent_id, role=role)
        self.members[agent_id] = member
        
        # Set as leader if first member
        if len(self.members) == 1:
            self.leader_id = agent_id
            member.role = TeamRole.LEADER
        
        logger.info(f"Agent {agent_id} joined team {self.name} as {role.value}")
        return member
    
    def remove_member(self, agent_id: str) -> bool:
        """Remove member from team."""
        if agent_id not in self.members:
            return False
        
        was_leader = self.leader_id == agent_id
        del self.members[agent_id]
        
        # Reassign leader if needed
        if was_leader and self.members:
            self.leader_id = next(iter(self.members.keys()))
            self.members[self.leader_id].role = TeamRole.LEADER
        
        logger.info(f"Agent {agent_id} left team {self.name}")
        return True
    
    def assign_role(self, agent_id: str, role: TeamRole) -> bool:
        """Assign role to team member."""
        if agent_id not in self.members:
            return False
        
        self.members[agent_id].role = role
        
        # Handle leader assignment
        if role == TeamRole.LEADER:
            if self.leader_id and self.leader_id != agent_id:
                self.members[self.leader_id].role = TeamRole.SPECIALIST
            self.leader_id = agent_id
        
        return True
    
    def add_goal(self, goal: SharedGoal) -> None:
        """Add shared goal to team."""
        goal.team_id = self.id
        self.active_goals.append(goal)
        goal.start()
        
        # Assign objectives to members based on roles
        self._assign_objectives(goal)
        
        logger.info(f"Goal '{goal.name}' added to team {self.name}")
    
    def _assign_objectives(self, goal: SharedGoal) -> None:
        """Assign objectives to team members based on roles."""
        for objective in goal.objectives:
            if objective.required_role:
                # Find member with required role
                for agent_id, member in self.members.items():
                    if member.role == objective.required_role and member.is_available:
                        objective.assigned_to = agent_id
                        break
            
            # If not assigned, assign to least busy member
            if not objective.assigned_to:
                available = [
                    (aid, m) for aid, m in self.members.items()
                    if m.is_available
                ]
                if available:
                    # Sort by current objective count
                    objective.assigned_to = available[0][0]
    
    def update_goals(self) -> List[Dict]:
        """Update all active goals and return changes."""
        changes = []
        completed = []
        failed = []
        
        for goal in self.active_goals:
            old_status = goal.status
            goal.update_progress()
            
            if goal.status != old_status:
                changes.append({
                    'goal_id': goal.id,
                    'old_status': old_status.name,
                    'new_status': goal.status.name,
                })
            
            if goal.status == GoalStatus.COMPLETED:
                completed.append(goal)
                self.total_goals_completed += 1
            elif goal.status == GoalStatus.FAILED:
                failed.append(goal)
                self.total_goals_failed += 1
        
        # Move completed/failed goals
        for goal in completed + failed:
            self.active_goals.remove(goal)
            self.completed_goals.append(goal)
        
        return changes
    
    def get_coordination_bonus(self) -> float:
        """Calculate team coordination bonus for actions."""
        if len(self.members) < 2:
            return 0.0
        
        # Base coordination from team history
        total_goals = self.total_goals_completed + self.total_goals_failed
        if total_goals > 0:
            success_rate = self.total_goals_completed / total_goals
        else:
            success_rate = 0.5
        
        # Member reliability average
        avg_reliability = sum(
            m.reliability_score for m in self.members.values()
        ) / len(self.members)
        
        # Communication efficiency
        comm_factor = self.communication_efficiency
        
        # Combined bonus (max 0.5)
        bonus = (success_rate * 0.2 + avg_reliability * 0.2 + comm_factor * 0.1)
        
        return min(0.5, bonus)
    
    def get_role_distribution(self) -> Dict[TeamRole, int]:
        """Get distribution of roles in team."""
        distribution: Dict[TeamRole, int] = {}
        for member in self.members.values():
            distribution[member.role] = distribution.get(member.role, 0) + 1
        return distribution
    
    def is_viable(self) -> Tuple[bool, List[str]]:
        """Check if team is viable for missions."""
        issues = []
        
        if len(self.members) < 2:
            issues.append("Team has fewer than 2 members")
        
        active_members = sum(1 for m in self.members.values() if m.is_active)
        if active_members < 2:
            issues.append("Fewer than 2 active members")
        
        if not self.leader_id:
            issues.append("No leader assigned")
        
        return len(issues) == 0, issues
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'member_count': len(self.members),
            'members': [
                {
                    'agent_id': m.agent_id,
                    'role': m.role.value,
                    'reliability': round(m.reliability_score, 2),
                    'contribution': round(m.contribution_score, 2),
                    'is_active': m.is_active,
                }
                for m in self.members.values()
            ],
            'leader_id': self.leader_id,
            'active_goals': [g.to_dict() for g in self.active_goals],
            'completed_goals_count': len(self.completed_goals),
            'coordination_bonus': round(self.get_coordination_bonus(), 2),
            'role_distribution': {
                role.value: count
                for role, count in self.get_role_distribution().items()
            },
            'formation_time': self.formation_time.isoformat(),
        }


class TeamManager:
    """Manager for all teams in the system."""
    
    def __init__(self):
        """Initialize team manager."""
        self.teams: Dict[str, Team] = {}
        self.agent_teams: Dict[str, Set[str]] = {}  # agent_id -> team_ids
    
    def create_team(
        self,
        name: str,
        description: str = "",
        creator_id: Optional[str] = None
    ) -> Team:
        """Create a new team."""
        team = Team(name=name, description=description)
        
        if creator_id:
            team.add_member(creator_id, TeamRole.LEADER)
            self.agent_teams.setdefault(creator_id, set()).add(team.id)
        
        self.teams[team.id] = team
        logger.info(f"Team created: {name} ({team.id})")
        return team
    
    def disband_team(self, team_id: str) -> bool:
        """Disband a team."""
        if team_id not in self.teams:
            return False
        
        team = self.teams[team_id]
        
        # Remove agent associations
        for agent_id in team.members:
            if agent_id in self.agent_teams:
                self.agent_teams[agent_id].discard(team_id)
        
        del self.teams[team_id]
        logger.info(f"Team disbanded: {team.name}")
        return True
    
    def get_agent_teams(self, agent_id: str) -> List[Team]:
        """Get all teams an agent belongs to."""
        team_ids = self.agent_teams.get(agent_id, set())
        return [self.teams[tid] for tid in team_ids if tid in self.teams]
    
    def get_active_teams(self) -> List[Team]:
        """Get all active teams."""
        return [
            team for team in self.teams.values()
            if team.is_viable()[0]
        ]
    
    def find_team_for_goal(self, goal: SharedGoal) -> Optional[Team]:
        """Find most suitable team for a goal."""
        candidates = []
        
        for team in self.teams.values():
            viable, _ = team.is_viable()
            if not viable:
                continue
            
            # Check if team has capacity
            if len(team.active_goals) >= 3:
                continue
            
            # Calculate suitability score
            score = 0.0
            
            # Role match
            required_roles = set(
                obj.required_role for obj in goal.objectives
                if obj.required_role
            )
            team_roles = set(team.get_role_distribution().keys())
            role_match = len(required_roles & team_roles) / max(1, len(required_roles))
            score += role_match * 0.4
            
            # Coordination bonus
            score += team.get_coordination_bonus() * 0.3
            
            # Reliability
            avg_reliability = sum(
                m.reliability_score for m in team.members.values()
            ) / max(1, len(team.members))
            score += avg_reliability * 0.3
            
            candidates.append((team, score))
        
        if candidates:
            return max(candidates, key=lambda x: x[1])[0]
        
        return None
    
    def update_all_teams(self) -> Dict[str, List[Dict]]:
        """Update all teams and return changes."""
        all_changes = {}
        
        for team_id, team in self.teams.items():
            changes = team.update_goals()
            if changes:
                all_changes[team_id] = changes
        
        return all_changes


# Predefined goal templates
class GoalTemplates:
    """Templates for common goal types."""
    
    @staticmethod
    def create_defend_goal(target: str, duration: int = 10) -> SharedGoal:
        """Create defend location/person goal."""
        return SharedGoal(
            name=f"Defend {target}",
            description=f"Protect {target} from enemies",
            goal_type="defend",
            priority=GoalPriority.HIGH,
            objectives=[
                GoalObjective(
                    id=f"defend_{target}",
                    description=f"Keep {target} safe",
                    required_role=TeamRole.TANK,
                    completion_condition={'type': 'protect', 'target': target}
                ),
            ],
            rewards={'xp': 100, 'reputation': 10},
            difficulty=1.2,
            tags={'defensive', 'protection'}
        )
    
    @staticmethod
    def create_escort_goal(target: str, destination: str) -> SharedGoal:
        """Create escort goal."""
        return SharedGoal(
            name=f"Escort {target} to {destination}",
            description=f"Safely escort {target} to {destination}",
            goal_type="escort",
            priority=GoalPriority.HIGH,
            objectives=[
                GoalObjective(
                    id=f"escort_{target}",
                    description=f"Protect {target} during journey",
                    required_role=TeamRole.TANK,
                ),
                GoalObjective(
                    id=f"reach_{destination}",
                    description=f"Reach {destination}",
                    completion_condition={'type': 'location', 'zone_id': destination}
                ),
            ],
            rewards={'xp': 150, 'gold': 50},
            difficulty=1.3,
            tags={'escort', 'travel'}
        )
    
    @staticmethod
    def create_assault_goal(target: str) -> SharedGoal:
        """Create assault/combat goal."""
        return SharedGoal(
            name=f"Assault {target}",
            description=f"Defeat {target} in combat",
            goal_type="combat",
            priority=GoalPriority.CRITICAL,
            objectives=[
                GoalObjective(
                    id=f"defeat_{target}",
                    description=f"Defeat {target}",
                    required_role=TeamRole.DAMAGE,
                    completion_condition={'type': 'defeat', 'target': target}
                ),
            ],
            rewards={'xp': 200, 'reputation': 20},
            difficulty=1.5,
            tags={'combat', 'offensive'}
        )
    
    @staticmethod
    def create_gather_goal(item: str, count: int) -> SharedGoal:
        """Create resource gathering goal."""
        return SharedGoal(
            name=f"Gather {count} {item}",
            description=f"Collect {count} units of {item}",
            goal_type="gather",
            priority=GoalPriority.MEDIUM,
            objectives=[
                GoalObjective(
                    id=f"gather_{item}",
                    description=f"Collect {item}",
                    completion_condition={'type': 'item', 'item': item, 'count': count}
                ),
            ],
            rewards={'xp': 50, 'gold': 30},
            difficulty=0.8,
            tags={'gathering', 'resources'}
        )


__all__ = [
    'TeamRole',
    'GoalStatus',
    'GoalPriority',
    'GoalObjective',
    'SharedGoal',
    'TeamMember',
    'Team',
    'TeamManager',
    'GoalTemplates',
]
