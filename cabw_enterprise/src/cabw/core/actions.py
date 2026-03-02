"""Complex action framework for CABW agents."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Callable, Dict, List, Optional


class ActionStatus(Enum):
    """Result status of an action execution."""

    PENDING = auto()
    RUNNING = auto()
    SUCCESS = auto()
    FAILURE = auto()
    CANCELLED = auto()


class ActionPriority(Enum):
    """Priority levels for action scheduling."""

    LOW = 1
    NORMAL = 2
    HIGH = 3
    CRITICAL = 4


@dataclass
class ActionContext:
    """Context passed to an action when it is executed."""

    agent_id: str
    world_state: Dict[str, Any] = field(default_factory=dict)
    parameters: Dict[str, Any] = field(default_factory=dict)
    tick: int = 0


@dataclass
class ActionResult:
    """Outcome of an action execution."""

    status: ActionStatus
    data: Dict[str, Any] = field(default_factory=dict)
    message: str = ""


class Action:
    """Base class for all agent actions."""

    def __init__(
        self,
        name: str,
        priority: ActionPriority = ActionPriority.NORMAL,
        cost: float = 1.0,
        preconditions: Optional[List[Callable[[ActionContext], bool]]] = None,
    ) -> None:
        self.name = name
        self.priority = priority
        self.cost = cost
        self.preconditions: List[Callable[[ActionContext], bool]] = preconditions or []
        self.status = ActionStatus.PENDING

    def check_preconditions(self, context: ActionContext) -> bool:
        """Return True only if all preconditions are satisfied."""
        return all(cond(context) for cond in self.preconditions)

    def execute(self, context: ActionContext) -> ActionResult:
        """Execute the action. Override in subclasses."""
        raise NotImplementedError

    def cancel(self) -> None:
        self.status = ActionStatus.CANCELLED

    def __repr__(self) -> str:
        return f"Action(name={self.name!r}, priority={self.priority.name}, status={self.status.name})"


class LambdaAction(Action):
    """Action backed by a callable for quick inline definitions."""

    def __init__(
        self,
        name: str,
        fn: Callable[[ActionContext], ActionResult],
        **kwargs: Any,
    ) -> None:
        super().__init__(name, **kwargs)
        self._fn = fn

    def execute(self, context: ActionContext) -> ActionResult:
        self.status = ActionStatus.RUNNING
        try:
            result = self._fn(context)
            self.status = result.status
            return result
        except Exception as exc:  # noqa: BLE001
            self.status = ActionStatus.FAILURE
            return ActionResult(status=ActionStatus.FAILURE, message=str(exc))


class ActionQueue:
    """Priority queue of actions waiting to be executed."""

    def __init__(self) -> None:
        self._queue: List[Action] = []

    def push(self, action: Action) -> None:
        self._queue.append(action)
        self._queue.sort(key=lambda a: a.priority.value, reverse=True)

    def pop(self) -> Optional[Action]:
        if self._queue:
            return self._queue.pop(0)
        return None

    def peek(self) -> Optional[Action]:
        return self._queue[0] if self._queue else None

    def __len__(self) -> int:
        return len(self._queue)

    def clear(self) -> None:
        self._queue.clear()


class ActionPlanner:
    """Simple forward-chaining action planner."""

    def __init__(self, actions: List[Action]) -> None:
        self.available_actions = actions

    def plan(
        self,
        context: ActionContext,
        goal: Callable[[Dict[str, Any]], bool],
        max_depth: int = 10,
    ) -> List[Action]:
        """Return a sequence of actions that leads to the *goal* state.

        Uses a greedy best-first strategy based on action priority.
        Returns an empty list when no plan is found within *max_depth* steps.
        """
        plan: List[Action] = []
        state = dict(context.world_state)

        for _ in range(max_depth):
            if goal(state):
                break
            candidates = [
                a
                for a in self.available_actions
                if a.check_preconditions(ActionContext(context.agent_id, state))
            ]
            if not candidates:
                break
            best = max(candidates, key=lambda a: a.priority.value)
            plan.append(best)
            # Simulate optimistic state change
            state[f"after_{best.name}"] = True

        return plan


@dataclass
class CompositeAction(Action):
    """Executes a sequence of sub-actions in order."""

    sub_actions: List[Action] = field(default_factory=list)

    def execute(self, context: ActionContext) -> ActionResult:
        self.status = ActionStatus.RUNNING
        for action in self.sub_actions:
            if not action.check_preconditions(context):
                self.status = ActionStatus.FAILURE
                return ActionResult(
                    status=ActionStatus.FAILURE,
                    message=f"Precondition failed for sub-action {action.name!r}",
                )
            result = action.execute(context)
            if result.status == ActionStatus.FAILURE:
                self.status = ActionStatus.FAILURE
                return result
        self.status = ActionStatus.SUCCESS
        return ActionResult(status=ActionStatus.SUCCESS)
