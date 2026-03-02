"""Unified agent class that integrates all CABW core systems."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
import uuid

from cabw.core.actions import (
    Action,
    ActionContext,
    ActionQueue,
    ActionStatus,
)
from cabw.core.behavior_tree import BehaviorTree, BTStatus
from cabw.core.emotions import EmotionalContagion, EmotionalMemory, EmotionalState
from cabw.core.teamwork import Team, TeamRole
from cabw.core.world_features import Position, WorldEnvironment


@dataclass
class AgentConfig:
    """Configuration parameters for an IntegratedAgent."""

    perception_radius: float = 10.0
    max_speed: float = 1.0
    energy: float = 100.0
    contagion_rate: float = 0.1
    emotion_decay_rate: float = 0.05
    memory_size: int = 100


class IntegratedAgent:
    """Unified agent that combines emotions, actions, teamwork, and behavior trees.

    This class serves as the main agent abstraction in CABW.  It wires together
    the individual sub-systems so that each simulation tick:

    1. The behavior tree is evaluated and produces an *intended action*.
    2. The action is queued and executed with an :class:`ActionContext`.
    3. Neighboring agents' emotional states are collected and contagion is applied.
    4. The resulting emotional state is persisted to memory.
    """

    def __init__(
        self,
        agent_id: Optional[str] = None,
        config: Optional[AgentConfig] = None,
        behavior_tree: Optional[BehaviorTree] = None,
    ) -> None:
        self.agent_id: str = agent_id or str(uuid.uuid4())
        self.config = config or AgentConfig()

        # Sub-systems
        self.emotion: EmotionalState = EmotionalState()
        self._contagion = EmotionalContagion(
            contagion_rate=self.config.contagion_rate,
            decay_rate=self.config.emotion_decay_rate,
        )
        self.memory = EmotionalMemory(max_history=self.config.memory_size)
        self.action_queue = ActionQueue()
        self.behavior_tree: Optional[BehaviorTree] = behavior_tree

        # World state
        self.position: Position = Position()
        self.energy: float = self.config.energy
        self.alive: bool = True

        # Team membership (agent may belong to at most one team at a time)
        self._team: Optional[Team] = None
        self._team_role: TeamRole = TeamRole.MEMBER

        # Arbitrary metadata storage
        self.metadata: Dict[str, Any] = {}

        # Per-tick context snapshot
        self._world_state: Dict[str, Any] = {}

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def team(self) -> Optional[Team]:
        return self._team

    @property
    def team_role(self) -> TeamRole:
        return self._team_role

    # ------------------------------------------------------------------
    # Team management helpers
    # ------------------------------------------------------------------

    def join_team(self, team: Team, role: TeamRole = TeamRole.MEMBER) -> bool:
        result = team.add_member(self.agent_id, role)
        if result:
            self._team = team
            self._team_role = role
        return result

    def leave_team(self) -> None:
        if self._team:
            self._team.remove_member(self.agent_id)
            self._team = None
            self._team_role = TeamRole.MEMBER

    # ------------------------------------------------------------------
    # Tick interface
    # ------------------------------------------------------------------

    def tick(
        self,
        world_state: Dict[str, Any],
        environment: Optional[WorldEnvironment] = None,
        neighbor_emotions: Optional[List[EmotionalState]] = None,
        tick_number: int = 0,
    ) -> Optional[Action]:
        """Execute one simulation tick.

        Parameters
        ----------
        world_state:
            Snapshot of the current world state.
        environment:
            Optional global environment object.
        neighbor_emotions:
            Emotional states of nearby agents (used for contagion).
        tick_number:
            Current simulation tick index.

        Returns
        -------
        The action that was executed this tick, or *None*.
        """
        if not self.alive:
            return None

        self._world_state = dict(world_state)
        if environment:
            self._world_state["environment"] = environment

        # 1. Evaluate behavior tree to populate action queue
        if self.behavior_tree:
            bt_context = {**self._world_state, "agent": self}
            self.behavior_tree.tick(bt_context)

        # 2. Execute the highest-priority queued action
        executed_action: Optional[Action] = None
        action = self.action_queue.pop()
        if action:
            context = ActionContext(
                agent_id=self.agent_id,
                world_state=self._world_state,
                tick=tick_number,
            )
            if action.check_preconditions(context):
                result = action.execute(context)
                if result.status == ActionStatus.SUCCESS:
                    self.energy = max(0.0, self.energy - action.cost)
                executed_action = action

        # 3. Apply emotional contagion
        self.emotion = self._contagion.apply_contagion(
            self.emotion,
            neighbor_emotions or [],
        )

        # 4. Record emotional state to memory
        self.memory.record(self.emotion)

        # 5. Check survival condition
        if self.energy <= 0:
            self.alive = False

        return executed_action

    # ------------------------------------------------------------------
    # Utility
    # ------------------------------------------------------------------

    def perceive(self, agents: List["IntegratedAgent"]) -> List["IntegratedAgent"]:
        """Return agents within the perception radius."""
        return [
            a
            for a in agents
            if a.agent_id != self.agent_id
            and self.position.distance_to(a.position) <= self.config.perception_radius
        ]

    def update_emotion(self, delta_pleasure: float = 0.0, delta_arousal: float = 0.0, delta_dominance: float = 0.0) -> None:
        """Directly modify the agent's current emotional state."""
        self.emotion = EmotionalState(
            pleasure=self.emotion.pleasure + delta_pleasure,
            arousal=self.emotion.arousal + delta_arousal,
            dominance=self.emotion.dominance + delta_dominance,
        )

    def summary(self) -> Dict[str, Any]:
        """Return a serializable summary of the agent's current state."""
        return {
            "agent_id": self.agent_id,
            "alive": self.alive,
            "energy": self.energy,
            "position": self.position.as_tuple(),
            "emotion_label": self.emotion.label(),
            "emotion_pad": self.emotion.as_vector(),
            "team": self._team.name if self._team else None,
            "team_role": self._team_role.name,
            "pending_actions": len(self.action_queue),
        }

    def __repr__(self) -> str:
        return (
            f"IntegratedAgent(id={self.agent_id!r}, "
            f"alive={self.alive}, energy={self.energy:.1f})"
        )
