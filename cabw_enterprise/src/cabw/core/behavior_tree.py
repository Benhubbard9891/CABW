"""
Behavior Tree System for Emergent Agent Architecture.

Implements:
- Behavior tree nodes (composite, decorator, leaf)
- Blackboard for shared state
- Runtime tree execution
- Dynamic tree modification
- Emergent behavior composition
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

from cabw.utils.logging import get_logger

logger = get_logger(__name__)


class NodeStatus(Enum):
    """Status of behavior tree node execution."""
    SUCCESS = auto()
    FAILURE = auto()
    RUNNING = auto()
    IDLE = auto()


class Blackboard:
    """
    Shared memory for behavior tree nodes.
    
    Acts as working memory for agents during decision-making.
    """
    
    def __init__(self, owner_id: str = ""):
        """Initialize blackboard."""
        self.owner_id = owner_id
        self._data: Dict[str, Any] = {}
        self._observers: Dict[str, List[Callable]] = {}
    
    def set(self, key: str, value: Any) -> None:
        """Set a value in the blackboard."""
        old_value = self._data.get(key)
        self._data[key] = value
        
        # Notify observers
        if key in self._observers:
            for callback in self._observers[key]:
                try:
                    callback(key, old_value, value)
                except Exception as e:
                    logger.warning(f"Blackboard observer error: {e}")
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get a value from the blackboard."""
        return self._data.get(key, default)
    
    def has(self, key: str) -> bool:
        """Check if key exists."""
        return key in self._data
    
    def remove(self, key: str) -> bool:
        """Remove a key."""
        if key in self._data:
            del self._data[key]
            return True
        return False
    
    def observe(self, key: str, callback: Callable) -> None:
        """Register observer for key changes."""
        if key not in self._observers:
            self._observers[key] = []
        self._observers[key].append(callback)
    
    def clear(self) -> None:
        """Clear all data."""
        self._data.clear()
        self._observers.clear()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return self._data.copy()


class BTNode(ABC):
    """Base class for behavior tree nodes."""
    
    def __init__(self, name: str = ""):
        """Initialize node."""
        self.name = name or self.__class__.__name__
        self.status = NodeStatus.IDLE
        self.parent: Optional[BTNode] = None
    
    @abstractmethod
    def tick(self, blackboard: Blackboard) -> NodeStatus:
        """Execute one tick of this node."""
        pass
    
    def reset(self) -> None:
        """Reset node state."""
        self.status = NodeStatus.IDLE
    
    def abort(self) -> None:
        """Abort execution."""
        self.reset()


# Composite Nodes

class CompositeNode(BTNode, ABC):
    """Base class for composite nodes (have children)."""
    
    def __init__(self, name: str = ""):
        """Initialize composite node."""
        super().__init__(name)
        self.children: List[BTNode] = []
        self.current_child_index: int = 0
    
    def add_child(self, child: BTNode) -> CompositeNode:
        """Add child node."""
        child.parent = self
        self.children.append(child)
        return self
    
    def reset(self) -> None:
        """Reset composite node."""
        super().reset()
        self.current_child_index = 0
        for child in self.children:
            child.reset()


class SequenceNode(CompositeNode):
    """
    Sequence node: executes children in order until one fails.
    
    Succeeds only if all children succeed.
    """
    
    def tick(self, blackboard: Blackboard) -> NodeStatus:
        """Execute sequence."""
        while self.current_child_index < len(self.children):
            child = self.children[self.current_child_index]
            status = child.tick(blackboard)
            
            if status == NodeStatus.RUNNING:
                self.status = NodeStatus.RUNNING
                return NodeStatus.RUNNING
            
            elif status == NodeStatus.FAILURE:
                self.reset()
                self.status = NodeStatus.FAILURE
                return NodeStatus.FAILURE
            
            # Success - move to next child
            self.current_child_index += 1
        
        # All children succeeded
        self.reset()
        self.status = NodeStatus.SUCCESS
        return NodeStatus.SUCCESS


class SelectorNode(CompositeNode):
    """
    Selector node: executes children until one succeeds.
    
    Fails only if all children fail.
    """
    
    def tick(self, blackboard: Blackboard) -> NodeStatus:
        """Execute selector."""
        while self.current_child_index < len(self.children):
            child = self.children[self.current_child_index]
            status = child.tick(blackboard)
            
            if status == NodeStatus.RUNNING:
                self.status = NodeStatus.RUNNING
                return NodeStatus.RUNNING
            
            elif status == NodeStatus.SUCCESS:
                self.reset()
                self.status = NodeStatus.SUCCESS
                return NodeStatus.SUCCESS
            
            # Failure - try next child
            self.current_child_index += 1
        
        # All children failed
        self.reset()
        self.status = NodeStatus.FAILURE
        return NodeStatus.FAILURE


class ParallelNode(CompositeNode):
    """
    Parallel node: executes all children simultaneously.
    
    Succeeds based on policy (all succeed, any succeed, etc.)
    """
    
    def __init__(self, name: str = "", success_threshold: int = 1):
        """Initialize parallel node."""
        super().__init__(name)
        self.success_threshold = success_threshold
        self.child_statuses: List[NodeStatus] = []
    
    def tick(self, blackboard: Blackboard) -> NodeStatus:
        """Execute all children in parallel."""
        if not self.child_statuses:
            self.child_statuses = [NodeStatus.IDLE] * len(self.children)
        
        success_count = 0
        running_count = 0
        
        for i, child in enumerate(self.children):
            if self.child_statuses[i] not in [NodeStatus.SUCCESS, NodeStatus.FAILURE]:
                status = child.tick(blackboard)
                self.child_statuses[i] = status
            
            if self.child_statuses[i] == NodeStatus.SUCCESS:
                success_count += 1
            elif self.child_statuses[i] == NodeStatus.RUNNING:
                running_count += 1
        
        # Check completion
        if success_count >= self.success_threshold:
            self.reset()
            self.status = NodeStatus.SUCCESS
            return NodeStatus.SUCCESS
        
        if running_count > 0:
            self.status = NodeStatus.RUNNING
            return NodeStatus.RUNNING
        
        # All done, not enough successes
        self.reset()
        self.status = NodeStatus.FAILURE
        return NodeStatus.FAILURE
    
    def reset(self) -> None:
        """Reset parallel node."""
        super().reset()
        self.child_statuses = []


# Decorator Nodes

class DecoratorNode(BTNode, ABC):
    """Base class for decorator nodes (have single child)."""
    
    def __init__(self, name: str = "", child: Optional[BTNode] = None):
        """Initialize decorator node."""
        super().__init__(name)
        self.child = child
        if child:
            child.parent = self
    
    def set_child(self, child: BTNode) -> DecoratorNode:
        """Set child node."""
        self.child = child
        child.parent = self
        return self
    
    def reset(self) -> None:
        """Reset decorator node."""
        super().reset()
        if self.child:
            self.child.reset()


class InverterNode(DecoratorNode):
    """Inverts child result (success <-> failure)."""
    
    def tick(self, blackboard: Blackboard) -> NodeStatus:
        """Execute and invert."""
        if not self.child:
            self.status = NodeStatus.FAILURE
            return NodeStatus.FAILURE
        
        status = self.child.tick(blackboard)
        
        if status == NodeStatus.RUNNING:
            self.status = NodeStatus.RUNNING
            return NodeStatus.RUNNING
        
        if status == NodeStatus.SUCCESS:
            self.status = NodeStatus.FAILURE
            return NodeStatus.FAILURE
        
        self.status = NodeStatus.SUCCESS
        return NodeStatus.SUCCESS


class RepeaterNode(DecoratorNode):
    """Repeats child execution N times."""
    
    def __init__(self, name: str = "", child: Optional[BTNode] = None, count: int = 1):
        """Initialize repeater."""
        super().__init__(name, child)
        self.count = count
        self.current_count = 0
    
    def tick(self, blackboard: Blackboard) -> NodeStatus:
        """Execute repeatedly."""
        if not self.child:
            self.status = NodeStatus.FAILURE
            return NodeStatus.FAILURE
        
        while self.current_count < self.count:
            status = self.child.tick(blackboard)
            
            if status == NodeStatus.RUNNING:
                self.status = NodeStatus.RUNNING
                return NodeStatus.RUNNING
            
            if status == NodeStatus.FAILURE:
                self.reset()
                self.status = NodeStatus.FAILURE
                return NodeStatus.FAILURE
            
            # Success - repeat
            self.child.reset()
            self.current_count += 1
        
        self.reset()
        self.status = NodeStatus.SUCCESS
        return NodeStatus.SUCCESS
    
    def reset(self) -> None:
        """Reset repeater."""
        super().reset()
        self.current_count = 0


class UntilFailNode(DecoratorNode):
    """Repeats child until it fails."""
    
    def tick(self, blackboard: Blackboard) -> NodeStatus:
        """Execute until failure."""
        if not self.child:
            self.status = NodeStatus.FAILURE
            return NodeStatus.FAILURE
        
        while True:
            status = self.child.tick(blackboard)
            
            if status == NodeStatus.RUNNING:
                self.status = NodeStatus.RUNNING
                return NodeStatus.RUNNING
            
            if status == NodeStatus.FAILURE:
                self.reset()
                self.status = NodeStatus.SUCCESS
                return NodeStatus.SUCCESS
            
            # Success - repeat
            self.child.reset()


class CooldownNode(DecoratorNode):
    """Prevents child execution for cooldown period after success."""
    
    def __init__(self, name: str = "", child: Optional[BTNode] = None, cooldown: float = 5.0):
        """Initialize cooldown node."""
        super().__init__(name, child)
        self.cooldown = cooldown
        self.last_success_time: Optional[float] = None
    
    def tick(self, blackboard: Blackboard) -> NodeStatus:
        """Execute with cooldown."""
        import time
        
        # Check cooldown
        if self.last_success_time is not None:
            elapsed = time.time() - self.last_success_time
            if elapsed < self.cooldown:
                self.status = NodeStatus.FAILURE
                return NodeStatus.FAILURE
        
        if not self.child:
            self.status = NodeStatus.FAILURE
            return NodeStatus.FAILURE
        
        status = self.child.tick(blackboard)
        
        if status == NodeStatus.SUCCESS:
            self.last_success_time = time.time()
        
        self.status = status
        return status


# Leaf Nodes

class LeafNode(BTNode, ABC):
    """Base class for leaf behavior tree nodes."""

    pass

class ActionNode(LeafNode):
    """Leaf node that executes an action."""
    
    def __init__(
        self,
        name: str = "",
        action: Optional[Callable[[Blackboard], NodeStatus]] = None
    ):
        """Initialize action node."""
        super().__init__(name)
        self.action = action
    
    def tick(self, blackboard: Blackboard) -> NodeStatus:
        """Execute action."""
        if not self.action:
            self.status = NodeStatus.FAILURE
            return NodeStatus.FAILURE
        
        try:
            self.status = self.action(blackboard)
            return self.status
        except Exception as e:
            logger.error(f"Action node error: {e}")
            self.status = NodeStatus.FAILURE
            return NodeStatus.FAILURE


class ConditionNode(LeafNode):
    """Leaf node that checks a condition."""
    
    def __init__(
        self,
        name: str = "",
        condition: Optional[Callable[[Blackboard], bool]] = None
    ):
        """Initialize condition node."""
        super().__init__(name)
        self.condition = condition
    
    def tick(self, blackboard: Blackboard) -> NodeStatus:
        """Check condition."""
        if not self.condition:
            self.status = NodeStatus.FAILURE
            return NodeStatus.FAILURE
        
        try:
            result = self.condition(blackboard)
            self.status = NodeStatus.SUCCESS if result else NodeStatus.FAILURE
            return self.status
        except Exception as e:
            logger.error(f"Condition node error: {e}")
            self.status = NodeStatus.FAILURE
            return NodeStatus.FAILURE


class WaitNode(LeafNode):
    """Leaf node that waits for specified duration."""
    
    def __init__(self, name: str = "", duration: float = 1.0):
        """Initialize wait node."""
        super().__init__(name)
        self.duration = duration
        self.start_time: Optional[float] = None
    
    def tick(self, blackboard: Blackboard) -> NodeStatus:
        """Wait for duration."""
        import time
        
        if self.start_time is None:
            self.start_time = time.time()
        
        elapsed = time.time() - self.start_time
        
        if elapsed >= self.duration:
            self.reset()
            self.status = NodeStatus.SUCCESS
            return NodeStatus.SUCCESS
        
        self.status = NodeStatus.RUNNING
        return NodeStatus.RUNNING
    
    def reset(self) -> None:
        """Reset wait node."""
        super().reset()
        self.start_time = None


# Behavior Tree Builder

class BehaviorTree:
    """Complete behavior tree for an agent."""
    
    def __init__(
        self,
        root: Optional[BTNode] = None,
        owner_id: str = "",
        blackboard: Optional[Blackboard] = None,
    ):
        """Initialize behavior tree."""
        self.root = root
        self.blackboard = blackboard or Blackboard(owner_id)
        self.tick_count = 0
    
    def tick(self) -> NodeStatus:
        """Execute one tick of the behavior tree."""
        if not self.root:
            return NodeStatus.FAILURE
        
        self.tick_count += 1
        self.blackboard.set("tick_count", self.tick_count)
        
        return self.root.tick(self.blackboard)
    
    def reset(self) -> None:
        """Reset behavior tree."""
        if self.root:
            self.root.reset()
        self.tick_count = 0
    
    def set_root(self, root: BTNode) -> None:
        """Set root node."""
        self.root = root
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert tree structure to dictionary."""
        def node_to_dict(node: BTNode) -> Dict[str, Any]:
            result = {
                'type': node.__class__.__name__,
                'name': node.name,
                'status': node.status.name,
            }
            
            if isinstance(node, CompositeNode):
                result['children'] = [node_to_dict(child) for child in node.children]
            
            if isinstance(node, DecoratorNode) and node.child:
                result['child'] = node_to_dict(node.child)
            
            return result
        
        if self.root:
            return node_to_dict(self.root)
        return {}


# Predefined behavior trees

class BehaviorTreeLibrary:
    """Library of predefined behavior trees."""

    def create_tree(self, tree_name: str, blackboard: Optional[Blackboard] = None) -> BehaviorTree:
        """Create a behavior tree by name with optional external blackboard."""
        creators = {
            'combat': self.create_combat_tree,
            'exploration': self.create_exploration_tree,
            'social': self.create_social_tree,
            'agent_ai': self.create_full_agent_tree,
        }
        tree = creators.get(tree_name, self.create_full_agent_tree)()
        if blackboard is not None:
            tree.blackboard = blackboard
        return tree
    
    @staticmethod
    def create_combat_tree() -> BehaviorTree:
        """Create combat behavior tree."""
        # Combat selector: choose between attack, defend, or flee
        combat_root = SelectorNode("Combat")
        
        # Flee if health is low
        flee_sequence = SequenceNode("FleeIfLowHealth")
        flee_sequence.add_child(ConditionNode("HealthLow", lambda bb: bb.get("hp", 1.0) < 0.3))
        flee_sequence.add_child(ActionNode("Flee", lambda bb: NodeStatus.SUCCESS))
        combat_root.add_child(flee_sequence)
        
        # Defend if ally needs help
        defend_sequence = SequenceNode("DefendAlly")
        defend_sequence.add_child(ConditionNode("AllyNeedsHelp", lambda bb: bb.get("ally_danger", False)))
        defend_sequence.add_child(ActionNode("CoverAlly", lambda bb: NodeStatus.SUCCESS))
        combat_root.add_child(defend_sequence)
        
        # Default: attack
        attack_sequence = SequenceNode("Attack")
        attack_sequence.add_child(ConditionNode("HasTarget", lambda bb: bb.get("target") is not None))
        attack_sequence.add_child(ActionNode("AttackTarget", lambda bb: NodeStatus.SUCCESS))
        combat_root.add_child(attack_sequence)
        
        return BehaviorTree(combat_root)
    
    @staticmethod
    def create_exploration_tree() -> BehaviorTree:
        """Create exploration behavior tree."""
        root = SelectorNode("Explore")
        
        # Investigate interesting objects
        investigate = SequenceNode("Investigate")
        investigate.add_child(ConditionNode("HasInterestingObject", lambda bb: bb.get("interesting_object") is not None))
        investigate.add_child(ActionNode("MoveToObject", lambda bb: NodeStatus.SUCCESS))
        investigate.add_child(ActionNode("ExamineObject", lambda bb: NodeStatus.SUCCESS))
        root.add_child(investigate)
        
        # Explore new areas
        explore = SequenceNode("ExploreNewArea")
        explore.add_child(ConditionNode("HasUnexploredArea", lambda bb: len(bb.get("unexplored", [])) > 0))
        explore.add_child(ActionNode("MoveToUnexplored", lambda bb: NodeStatus.SUCCESS))
        root.add_child(explore)
        
        # Wander
        wander = ActionNode("Wander", lambda bb: NodeStatus.SUCCESS)
        root.add_child(wander)
        
        return BehaviorTree(root)
    
    @staticmethod
    def create_social_tree() -> BehaviorTree:
        """Create social interaction behavior tree."""
        root = SelectorNode("Social")
        
        # Help teammates
        help_team = SequenceNode("HelpTeam")
        help_team.add_child(ConditionNode("TeammateNeedsHelp", lambda bb: bb.get("teammate_request") is not None))
        help_team.add_child(ActionNode("RespondToRequest", lambda bb: NodeStatus.SUCCESS))
        root.add_child(help_team)
        
        # Coordinate with team
        coordinate = SequenceNode("Coordinate")
        coordinate.add_child(ConditionNode("InTeam", lambda bb: bb.get("team_id") is not None))
        coordinate.add_child(ConditionNode("CoordinationNeeded", lambda bb: bb.get("coordination_needed", False)))
        coordinate.add_child(ActionNode("CoordinateAction", lambda bb: NodeStatus.SUCCESS))
        root.add_child(coordinate)
        
        # Chat with nearby agents
        chat = SequenceNode("Chat")
        chat.add_child(ConditionNode("HasNearbyAgent", lambda bb: len(bb.get("nearby_agents", [])) > 0))
        chat.add_child(ActionNode("InitiateChat", lambda bb: NodeStatus.SUCCESS))
        root.add_child(chat)
        
        return BehaviorTree(root)
    
    @staticmethod
    def create_full_agent_tree() -> BehaviorTree:
        """Create complete agent behavior tree."""
        root = SelectorNode("AgentAI")
        
        # Survival priority
        survival = SequenceNode("Survival")
        survival.add_child(ConditionNode("InDanger", lambda bb: bb.get("danger_level", 0) > 0.7))
        survival.add_child(BehaviorTreeLibrary.create_combat_tree().root)
        root.add_child(survival)
        
        # Team coordination
        team = SequenceNode("Team")
        team.add_child(ConditionNode("HasActiveGoal", lambda bb: bb.get("active_goal") is not None))
        team.add_child(BehaviorTreeLibrary.create_social_tree().root)
        root.add_child(team)
        
        # Exploration
        explore = SequenceNode("Explore")
        explore.add_child(ConditionNode("NoImmediateThreat", lambda bb: bb.get("danger_level", 0) < 0.3))
        explore.add_child(BehaviorTreeLibrary.create_exploration_tree().root)
        root.add_child(explore)
        
        # Idle
        idle = ActionNode("Idle", lambda bb: NodeStatus.SUCCESS)
        root.add_child(idle)
        
        return BehaviorTree(root)


__all__ = [
    'NodeStatus',
    'Blackboard',
    'BTNode',
    'CompositeNode',
    'SequenceNode',
    'SelectorNode',
    'ParallelNode',
    'DecoratorNode',
    'InverterNode',
    'RepeaterNode',
    'UntilFailNode',
    'CooldownNode',
    'LeafNode',
    'ActionNode',
    'ConditionNode',
    'WaitNode',
    'BehaviorTree',
    'BehaviorTreeLibrary',
]
