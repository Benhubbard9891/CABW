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

from .emotions import (
    EmotionType,
    EmotionalState,
    EmotionalContagion,
    GroupEmotionalClimate
)

from .actions import (
    ActionPrecondition,
    ActionEffect,
    ActionCost,
    ComplexAction,
    ActionContext,
    ActionLibrary,
    ActionSequence
)

from .teamwork import (
    TeamRole,
    GoalObjective,
    SharedGoal,
    TeamMember,
    Team,
    TeamManager,
    GoalTemplates
)

from .behavior_tree import (
    NodeStatus,
    BTNode,
    CompositeNode,
    SequenceNode,
    SelectorNode,
    ParallelNode,
    DecoratorNode,
    InverterNode,
    RepeaterNode,
    CooldownNode,
    UntilFailNode,
    LeafNode,
    ActionNode,
    ConditionNode,
    WaitNode,
    Blackboard,
    BehaviorTree,
    BehaviorTreeLibrary
)

from .world_features import (
    WeatherType,
    TimeOfDay,
    Season,
    HazardType,
    HazardSeverity,
    WeatherState,
    Hazard,
    EnvironmentalEvent,
    WorldEnvironment,
    EnvironmentEffectSystem
)

from .integrated_agent import (
    AgentMemory,
    AgentNeeds,
    AgentStats,
    IntegratedAgent
)

__all__ = [
    # Emotions
    'EmotionType',
    'EmotionalState',
    'EmotionalContagion',
    'GroupEmotionalClimate',
    
    # Actions
    'ActionPrecondition',
    'ActionEffect',
    'ActionCost',
    'ComplexAction',
    'ActionContext',
    'ActionLibrary',
    'ActionSequence',
    
    # Teamwork
    'TeamRole',
    'GoalObjective',
    'SharedGoal',
    'TeamMember',
    'Team',
    'TeamManager',
    'GoalTemplates',
    
    # Behavior Trees
    'NodeStatus',
    'BTNode',
    'CompositeNode',
    'SequenceNode',
    'SelectorNode',
    'ParallelNode',
    'DecoratorNode',
    'InverterNode',
    'RepeaterNode',
    'CooldownNode',
    'UntilFailNode',
    'LeafNode',
    'ActionNode',
    'ConditionNode',
    'WaitNode',
    'Blackboard',
    'BehaviorTree',
    'BehaviorTreeLibrary',
    
    # World Features
    'WeatherType',
    'TimeOfDay',
    'Season',
    'HazardType',
    'HazardSeverity',
    'WeatherState',
    'Hazard',
    'EnvironmentalEvent',
    'WorldEnvironment',
    'EnvironmentEffectSystem',
    
    # Integrated Agent
    'AgentMemory',
    'AgentNeeds',
    'AgentStats',
    'IntegratedAgent'
]
