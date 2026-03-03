"""
Machine Learning Module for CABW Enterprise

- behavior_optimization: Optimize agent behaviors using ML
- rl_agents: Reinforcement learning for agent policies
- nlp_interface: Natural language interaction with agents
"""

from .behavior_optimization import BehaviorOptimizer, DeliberationWeightOptimizer
from .nlp_interface import AgentDialogue, CommandProcessor, NLPInterface
from .rl_agents import PolicyNetwork, ReplayBuffer, RLAgent, RLTrainer

__all__ = [
    "BehaviorOptimizer",
    "DeliberationWeightOptimizer",
    "RLAgent",
    "RLTrainer",
    "PolicyNetwork",
    "ReplayBuffer",
    "NLPInterface",
    "AgentDialogue",
    "CommandProcessor",
]
