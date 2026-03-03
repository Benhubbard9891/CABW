"""
CABW Core Module - Enhanced Agent Systems

This module provides all core agent capabilities:
- emotions: Advanced emotional system with trauma and contagion
- actions: Complex actions with preconditions and effects
- teamwork: Team formation, shared goals, and coordination
- behavior_tree: Hierarchical agent decision-making
- world_features: Dynamic environment (weather, hazards, events)
- integrated_agent: Unified agent combining all systems
"""

from .actions import (
    ActionContext,
    ActionCost,
    ActionEffect,
    ActionLibrary,
    ActionPrecondition,
    ActionSequence,
    ComplexAction,
)
from .behavior_tree import (
    ActionNode,
    BehaviorTree,
    BehaviorTreeLibrary,
    Blackboard,
    BTNode,
    CompositeNode,
    ConditionNode,
    CooldownNode,
    DecoratorNode,
    InverterNode,
    NodeStatus,
    ParallelNode,
    RepeaterNode,
    SelectorNode,
    SequenceNode,
    UntilFailNode,
    WaitNode,
)
from .emotions import EmotionalContagion, EmotionalState, EmotionType, GroupEmotionalClimate
from .integrated_agent import AgentMemory, AgentNeeds, AgentStats, IntegratedAgent
from .teamwork import (
    GoalObjective,
    GoalTemplates,
    SharedGoal,
    Team,
    TeamManager,
    TeamMember,
    TeamRole,
)
from .world_features import (
    EnvironmentalEvent,
    EnvironmentEffectSystem,
    Hazard,
    HazardSeverity,
    HazardType,
    Season,
    TimeOfDay,
    WeatherState,
    WeatherType,
    WorldEnvironment,
)

__all__ = [
    # Emotions
    "EmotionType",
    "EmotionalState",
    "EmotionalContagion",
    "GroupEmotionalClimate",
    # Actions
    "ActionPrecondition",
    "ActionEffect",
    "ActionCost",
    "ActionContext",
    "ComplexAction",
    "ActionLibrary",
    "ActionSequence",
    # Teamwork
    "TeamRole",
    "GoalObjective",
    "SharedGoal",
    "TeamMember",
    "Team",
    "TeamManager",
    "GoalTemplates",
    # Behavior Trees
    "NodeStatus",
    "BTNode",
    "CompositeNode",
    "SequenceNode",
    "SelectorNode",
    "ParallelNode",
    "DecoratorNode",
    "InverterNode",
    "RepeaterNode",
    "CooldownNode",
    "UntilFailNode",
    "ActionNode",
    "ConditionNode",
    "WaitNode",
    "Blackboard",
    "BehaviorTree",
    "BehaviorTreeLibrary",
    # World Features
    "WeatherType",
    "TimeOfDay",
    "Season",
    "HazardType",
    "HazardSeverity",
    "WeatherState",
    "Hazard",
    "EnvironmentalEvent",
    "WorldEnvironment",
    "EnvironmentEffectSystem",
    # Integrated Agent
    "AgentMemory",
    "AgentNeeds",
    "AgentStats",
    "IntegratedAgent",
]
