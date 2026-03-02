"""Behavior Tree nodes and library for CABW agents."""

from __future__ import annotations

from abc import ABC, abstractmethod
from enum import Enum, auto
from typing import Any, Callable, Dict, List, Optional


class BTStatus(Enum):
    """Return status of a behavior tree node tick."""

    SUCCESS = auto()
    FAILURE = auto()
    RUNNING = auto()


class BTNode(ABC):
    """Abstract base class for all behavior tree nodes."""

    def __init__(self, name: str = "") -> None:
        self.name = name or self.__class__.__name__

    @abstractmethod
    def tick(self, context: Dict[str, Any]) -> BTStatus:
        """Execute one tick of this node."""

    def reset(self) -> None:
        """Reset internal state (override in stateful nodes)."""

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(name={self.name!r})"


# ---------------------------------------------------------------------------
# Leaf nodes
# ---------------------------------------------------------------------------


class ConditionNode(BTNode):
    """Leaf node that succeeds when a callable condition returns True."""

    def __init__(self, name: str, condition: Callable[[Dict[str, Any]], bool]) -> None:
        super().__init__(name)
        self._condition = condition

    def tick(self, context: Dict[str, Any]) -> BTStatus:
        return BTStatus.SUCCESS if self._condition(context) else BTStatus.FAILURE


class ActionNode(BTNode):
    """Leaf node that executes a callable action."""

    def __init__(
        self,
        name: str,
        action: Callable[[Dict[str, Any]], BTStatus],
    ) -> None:
        super().__init__(name)
        self._action = action

    def tick(self, context: Dict[str, Any]) -> BTStatus:
        return self._action(context)


# ---------------------------------------------------------------------------
# Composite nodes
# ---------------------------------------------------------------------------


class SequenceNode(BTNode):
    """Executes children in order; fails on the first child failure."""

    def __init__(self, name: str = "Sequence", children: Optional[List[BTNode]] = None) -> None:
        super().__init__(name)
        self.children: List[BTNode] = children or []
        self._running_index: int = 0

    def tick(self, context: Dict[str, Any]) -> BTStatus:
        for i in range(self._running_index, len(self.children)):
            status = self.children[i].tick(context)
            if status == BTStatus.FAILURE:
                self._running_index = 0
                return BTStatus.FAILURE
            if status == BTStatus.RUNNING:
                self._running_index = i
                return BTStatus.RUNNING
        self._running_index = 0
        return BTStatus.SUCCESS

    def reset(self) -> None:
        self._running_index = 0
        for child in self.children:
            child.reset()


class SelectorNode(BTNode):
    """Executes children in order; succeeds on the first child success."""

    def __init__(self, name: str = "Selector", children: Optional[List[BTNode]] = None) -> None:
        super().__init__(name)
        self.children: List[BTNode] = children or []
        self._running_index: int = 0

    def tick(self, context: Dict[str, Any]) -> BTStatus:
        for i in range(self._running_index, len(self.children)):
            status = self.children[i].tick(context)
            if status == BTStatus.SUCCESS:
                self._running_index = 0
                return BTStatus.SUCCESS
            if status == BTStatus.RUNNING:
                self._running_index = i
                return BTStatus.RUNNING
        self._running_index = 0
        return BTStatus.FAILURE

    def reset(self) -> None:
        self._running_index = 0
        for child in self.children:
            child.reset()


class ParallelNode(BTNode):
    """Ticks all children simultaneously; uses threshold to determine status."""

    def __init__(
        self,
        name: str = "Parallel",
        children: Optional[List[BTNode]] = None,
        success_threshold: Optional[int] = None,
    ) -> None:
        super().__init__(name)
        self.children: List[BTNode] = children or []
        # Default: all children must succeed
        self.success_threshold: int = (
            success_threshold if success_threshold is not None else len(self.children)
        )

    def tick(self, context: Dict[str, Any]) -> BTStatus:
        successes = 0
        failures = 0
        for child in self.children:
            status = child.tick(context)
            if status == BTStatus.SUCCESS:
                successes += 1
            elif status == BTStatus.FAILURE:
                failures += 1

        if successes >= self.success_threshold:
            return BTStatus.SUCCESS
        if failures > len(self.children) - self.success_threshold:
            return BTStatus.FAILURE
        return BTStatus.RUNNING


# ---------------------------------------------------------------------------
# Decorator nodes
# ---------------------------------------------------------------------------


class InverterNode(BTNode):
    """Inverts the result of its single child."""

    def __init__(self, name: str = "Inverter", child: Optional[BTNode] = None) -> None:
        super().__init__(name)
        self.child: Optional[BTNode] = child

    def tick(self, context: Dict[str, Any]) -> BTStatus:
        if self.child is None:
            return BTStatus.FAILURE
        status = self.child.tick(context)
        if status == BTStatus.SUCCESS:
            return BTStatus.FAILURE
        if status == BTStatus.FAILURE:
            return BTStatus.SUCCESS
        return BTStatus.RUNNING


class RepeatNode(BTNode):
    """Repeats its child up to *max_repeats* times (or indefinitely if 0)."""

    def __init__(
        self,
        name: str = "Repeat",
        child: Optional[BTNode] = None,
        max_repeats: int = 0,
    ) -> None:
        super().__init__(name)
        self.child: Optional[BTNode] = child
        self.max_repeats = max_repeats
        self._count = 0

    def tick(self, context: Dict[str, Any]) -> BTStatus:
        if self.child is None:
            return BTStatus.FAILURE
        status = self.child.tick(context)
        if status == BTStatus.FAILURE:
            self._count = 0
            return BTStatus.FAILURE
        if status == BTStatus.SUCCESS:
            self._count += 1
            if self.max_repeats > 0 and self._count >= self.max_repeats:
                self._count = 0
                return BTStatus.SUCCESS
            self.child.reset()
            return BTStatus.RUNNING
        return BTStatus.RUNNING

    def reset(self) -> None:
        self._count = 0
        if self.child:
            self.child.reset()


# ---------------------------------------------------------------------------
# BehaviorTree runner
# ---------------------------------------------------------------------------


class BehaviorTree:
    """Wraps a root node and provides a tick interface."""

    def __init__(self, root: BTNode) -> None:
        self.root = root
        self.last_status: BTStatus = BTStatus.FAILURE

    def tick(self, context: Dict[str, Any]) -> BTStatus:
        self.last_status = self.root.tick(context)
        return self.last_status

    def reset(self) -> None:
        self.root.reset()


# ---------------------------------------------------------------------------
# Pre-built node library
# ---------------------------------------------------------------------------


class BTLibrary:
    """Factory helpers for common BT sub-trees."""

    @staticmethod
    def always_succeed(name: str = "AlwaysSucceed") -> ActionNode:
        return ActionNode(name, lambda _ctx: BTStatus.SUCCESS)

    @staticmethod
    def always_fail(name: str = "AlwaysFail") -> ActionNode:
        return ActionNode(name, lambda _ctx: BTStatus.FAILURE)

    @staticmethod
    def check_key(key: str, expected: Any, name: Optional[str] = None) -> ConditionNode:
        """Succeed when context[key] == expected."""
        return ConditionNode(
            name or f"Check({key}=={expected})",
            lambda ctx, k=key, v=expected: ctx.get(k) == v,
        )

    @staticmethod
    def set_key(key: str, value: Any, name: Optional[str] = None) -> ActionNode:
        """Set context[key] = value and succeed."""

        def _action(ctx: Dict[str, Any], k: str = key, v: Any = value) -> BTStatus:
            ctx[k] = v
            return BTStatus.SUCCESS

        return ActionNode(name or f"Set({key}={value})", _action)
