"""Team formation and shared goal management for CABW agents."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Dict, List, Optional, Set
import uuid


class TeamRole(Enum):
    """Roles that agents can hold within a team."""

    LEADER = auto()
    MEMBER = auto()
    OBSERVER = auto()


class GoalStatus(Enum):
    """Lifecycle status of a team goal."""

    PENDING = auto()
    ACTIVE = auto()
    COMPLETED = auto()
    FAILED = auto()
    ABANDONED = auto()


@dataclass
class TeamGoal:
    """A shared goal pursued by a team."""

    description: str
    target_state: Dict[str, Any] = field(default_factory=dict)
    priority: int = 1
    status: GoalStatus = GoalStatus.PENDING
    goal_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    progress: float = 0.0   # 0.0 – 1.0

    def activate(self) -> None:
        self.status = GoalStatus.ACTIVE

    def complete(self) -> None:
        self.status = GoalStatus.COMPLETED
        self.progress = 1.0

    def fail(self) -> None:
        self.status = GoalStatus.FAILED

    def abandon(self) -> None:
        self.status = GoalStatus.ABANDONED

    def update_progress(self, progress: float) -> None:
        self.progress = max(0.0, min(1.0, progress))
        if self.progress >= 1.0:
            self.complete()


@dataclass
class TeamMember:
    """Represents an agent's membership in a team."""

    agent_id: str
    role: TeamRole = TeamRole.MEMBER
    contribution_score: float = 0.0

    def promote(self) -> None:
        self.role = TeamRole.LEADER

    def demote(self) -> None:
        self.role = TeamRole.MEMBER


class Team:
    """A group of agents working toward shared goals."""

    def __init__(self, name: str, max_size: int = 10) -> None:
        self.name = name
        self.max_size = max_size
        self.team_id: str = str(uuid.uuid4())
        self._members: Dict[str, TeamMember] = {}
        self._goals: List[TeamGoal] = []

    # ------------------------------------------------------------------
    # Membership management
    # ------------------------------------------------------------------

    def add_member(self, agent_id: str, role: TeamRole = TeamRole.MEMBER) -> bool:
        """Add an agent to the team. Returns False if the team is full."""
        if len(self._members) >= self.max_size:
            return False
        if agent_id not in self._members:
            self._members[agent_id] = TeamMember(agent_id=agent_id, role=role)
        return True

    def remove_member(self, agent_id: str) -> bool:
        """Remove an agent from the team. Returns False if not a member."""
        if agent_id in self._members:
            del self._members[agent_id]
            return True
        return False

    def set_leader(self, agent_id: str) -> bool:
        """Assign the leader role to a member."""
        if agent_id not in self._members:
            return False
        for member in self._members.values():
            member.role = TeamRole.MEMBER
        self._members[agent_id].role = TeamRole.LEADER
        return True

    @property
    def leader(self) -> Optional[TeamMember]:
        for member in self._members.values():
            if member.role == TeamRole.LEADER:
                return member
        return None

    @property
    def members(self) -> List[TeamMember]:
        return list(self._members.values())

    @property
    def member_ids(self) -> Set[str]:
        return set(self._members.keys())

    # ------------------------------------------------------------------
    # Goal management
    # ------------------------------------------------------------------

    def add_goal(self, goal: TeamGoal) -> None:
        self._goals.append(goal)

    def active_goals(self) -> List[TeamGoal]:
        return [g for g in self._goals if g.status == GoalStatus.ACTIVE]

    def pending_goals(self) -> List[TeamGoal]:
        return [g for g in self._goals if g.status == GoalStatus.PENDING]

    def get_goal(self, goal_id: str) -> Optional[TeamGoal]:
        for goal in self._goals:
            if goal.goal_id == goal_id:
                return goal
        return None

    # ------------------------------------------------------------------
    # Utility
    # ------------------------------------------------------------------

    def update_contribution(self, agent_id: str, delta: float) -> None:
        if agent_id in self._members:
            self._members[agent_id].contribution_score += delta

    def __repr__(self) -> str:
        return (
            f"Team(name={self.name!r}, members={len(self._members)}, "
            f"goals={len(self._goals)})"
        )


class TeamFormationStrategy:
    """Strategies for forming teams from a pool of agents."""

    @staticmethod
    def form_by_skill(
        agent_skills: Dict[str, List[str]],
        required_skills: List[str],
        team_name: str = "auto-team",
    ) -> Team:
        """Form a team that collectively covers all *required_skills*."""
        team = Team(name=team_name)
        covered: Set[str] = set()
        for agent_id, skills in agent_skills.items():
            if covered >= set(required_skills):
                break
            if any(s in required_skills for s in skills):
                team.add_member(agent_id)
                covered.update(skills)
        return team

    @staticmethod
    def form_random(
        agent_ids: List[str],
        size: int,
        team_name: str = "random-team",
    ) -> Team:
        """Form a team of *size* agents chosen from *agent_ids* (in order)."""
        team = Team(name=team_name, max_size=size)
        for agent_id in agent_ids[:size]:
            team.add_member(agent_id)
        return team
