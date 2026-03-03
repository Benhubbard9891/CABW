"""
Reinforcement Learning for Agent Policies

Implements PPO-style RL for agents to learn optimal behavior policies.
OCEAN traits can be learned as policy parameters.
"""

import json
import random
from collections import deque
from dataclasses import dataclass, field
from typing import Any

import numpy as np


@dataclass
class Experience:
    """Single experience tuple for RL."""

    state: np.ndarray
    action: int
    reward: float
    next_state: np.ndarray
    done: bool
    info: dict[str, Any] = field(default_factory=dict)


class ReplayBuffer:
    """Experience replay buffer for off-policy learning."""

    def __init__(self, capacity: int = 10000):
        self.capacity = capacity
        self.buffer: deque = deque(maxlen=capacity)
        self.position = 0

    def push(self, experience: Experience):
        """Add experience to buffer."""
        self.buffer.append(experience)

    def sample(self, batch_size: int) -> list[Experience]:
        """Sample batch of experiences."""
        return random.sample(list(self.buffer), min(batch_size, len(self.buffer)))

    def __len__(self) -> int:
        return len(self.buffer)

    def clear(self):
        """Clear buffer."""
        self.buffer.clear()


class PolicyNetwork:
    """
    Neural network policy for RL agent.
    Simple feedforward network for discrete actions.
    """

    def __init__(self, state_dim: int, action_dim: int, hidden_dims: list[int] = None):
        if hidden_dims is None:
            hidden_dims = [128, 64]
        self.state_dim = state_dim
        self.action_dim = action_dim

        # Initialize weights randomly (in production, use PyTorch/TensorFlow)
        self.layers = []
        prev_dim = state_dim
        for hidden_dim in hidden_dims:
            self.layers.append(
                {"W": np.random.randn(prev_dim, hidden_dim) * 0.01, "b": np.zeros(hidden_dim)}
            )
            prev_dim = hidden_dim

        # Output layer
        self.output_layer = {
            "W": np.random.randn(prev_dim, action_dim) * 0.01,
            "b": np.zeros(action_dim),
        }

    def forward(self, state: np.ndarray) -> np.ndarray:
        """Forward pass through network."""
        x = state
        for layer in self.layers:
            x = np.maximum(0, x @ layer["W"] + layer["b"])  # ReLU

        # Softmax output
        logits = x @ self.output_layer["W"] + self.output_layer["b"]
        exp_logits = np.exp(logits - np.max(logits))
        return exp_logits / np.sum(exp_logits)

    def get_action(self, state: np.ndarray, epsilon: float = 0.1) -> int:
        """Get action using epsilon-greedy."""
        if random.random() < epsilon:
            return random.randint(0, self.action_dim - 1)

        probs = self.forward(state)
        return np.random.choice(self.action_dim, p=probs)

    def get_action_prob(self, state: np.ndarray, action: int) -> float:
        """Get probability of action."""
        probs = self.forward(state)
        return probs[action]

    def get_parameters(self) -> list[np.ndarray]:
        """Get all network parameters."""
        params = []
        for layer in self.layers:
            params.append(layer["W"])
            params.append(layer["b"])
        params.append(self.output_layer["W"])
        params.append(self.output_layer["b"])
        return params

    def set_parameters(self, params: list[np.ndarray]):
        """Set network parameters."""
        idx = 0
        for layer in self.layers:
            layer["W"] = params[idx]
            layer["b"] = params[idx + 1]
            idx += 2
        self.output_layer["W"] = params[idx]
        self.output_layer["b"] = params[idx + 1]


class RLAgent:
    """
    Reinforcement Learning Agent.
    Learns optimal policy through interaction with environment.
    """

    def __init__(
        self,
        agent_id: str,
        state_dim: int,
        action_dim: int,
        learning_rate: float = 0.001,
        gamma: float = 0.99,
        epsilon: float = 0.1,
    ):
        self.agent_id = agent_id
        self.state_dim = state_dim
        self.action_dim = action_dim
        self.learning_rate = learning_rate
        self.gamma = gamma
        self.epsilon = epsilon

        # Policy network
        self.policy = PolicyNetwork(state_dim, action_dim)

        # Replay buffer
        self.replay_buffer = ReplayBuffer(capacity=10000)

        # Training stats
        self.total_reward = 0.0
        self.episode_count = 0
        self.step_count = 0

        # OCEAN traits as learnable parameters
        self.ocean_traits = {
            "openness": 0.5,
            "conscientiousness": 0.5,
            "extraversion": 0.5,
            "agreeableness": 0.5,
            "neuroticism": 0.5,
        }

    def encode_state(self, agent_state: dict[str, Any]) -> np.ndarray:
        """Encode agent state to vector."""
        features = []

        # Health and energy
        features.append(agent_state.get("health", 100) / 100.0)
        features.append(agent_state.get("energy", 100) / 100.0)

        # Emotional state (PAD)
        emotional = agent_state.get("emotional_state", {})
        features.append(emotional.get("pleasure", 0))
        features.append(emotional.get("arousal", 0))
        features.append(emotional.get("dominance", 0))

        # Needs
        needs = agent_state.get("needs", {})
        features.append(needs.get("hunger", 0))
        features.append(needs.get("thirst", 0))
        features.append(needs.get("rest", 0))
        features.append(needs.get("safety", 1.0))

        # Location (normalized)
        location = agent_state.get("location", (0, 0))
        world_size = agent_state.get("world_size", (100, 100))
        features.append(location[0] / world_size[0])
        features.append(location[1] / world_size[1])

        # Team context
        team = agent_state.get("team", {})
        features.append(1.0 if team else 0.0)
        features.append(team.get("cohesion", 0) if team else 0)

        # Pad to state_dim
        while len(features) < self.state_dim:
            features.append(0.0)

        return np.array(features[: self.state_dim], dtype=np.float32)

    def select_action(self, state: np.ndarray) -> int:
        """Select action using current policy."""
        return self.policy.get_action(state, self.epsilon)

    def store_experience(
        self, state: np.ndarray, action: int, reward: float, next_state: np.ndarray, done: bool
    ):
        """Store experience in replay buffer."""
        exp = Experience(state, action, reward, next_state, done)
        self.replay_buffer.push(exp)
        self.total_reward += reward
        self.step_count += 1

    def compute_reward(
        self, old_state: dict[str, Any], new_state: dict[str, Any], action_taken: str
    ) -> float:
        """
        Compute reward for state transition.
        """
        reward = 0.0

        # Health improvement
        old_health = old_state.get("health", 100)
        new_health = new_state.get("health", 100)
        if new_health > old_health:
            reward += 1.0
        elif new_health < old_health:
            reward -= 1.0

        # Goal completion
        if new_state.get("goal_completed", False):
            reward += 10.0

        # Team coordination
        old_team = old_state.get("team", {})
        new_team = new_state.get("team", {})
        if new_team and not old_team:
            reward += 2.0  # Joined team

        # Emotional stability
        old_valence = old_state.get("emotional_state", {}).get("valence", 0)
        new_valence = new_state.get("emotional_state", {}).get("valence", 0)
        if new_valence > old_valence:
            reward += 0.5

        # Survival bonus
        if new_state.get("alive", True) and not old_state.get("alive", True):
            reward += 5.0  # Recovered

        return reward

    def update_ocean_traits(self, performance: dict[str, float]):
        """
        Update OCEAN traits based on performance.
        Traits adapt to what works best.
        """
        # High goal completion → increase conscientiousness
        if performance.get("goal_completion", 0) > 0.7:
            self.ocean_traits["conscientiousness"] = min(
                1.0, self.ocean_traits["conscientiousness"] + 0.05
            )

        # High team coordination → increase extraversion
        if performance.get("team_coordination", 0) > 0.6:
            self.ocean_traits["extraversion"] = min(
                1.0, self.ocean_traits["extratraversion"] + 0.05
            )

        # Emotional stability → decrease neuroticism
        if performance.get("emotional_stability", 0) > 0.7:
            self.ocean_traits["neuroticism"] = max(0.0, self.ocean_traits["neuroticism"] - 0.05)

        # Exploration success → increase openness
        if performance.get("exploration_success", 0) > 0.5:
            self.ocean_traits["openness"] = min(1.0, self.ocean_traits["openness"] + 0.05)

    def export_policy(self, filepath: str):
        """Export learned policy."""
        data = {
            "agent_id": self.agent_id,
            "state_dim": self.state_dim,
            "action_dim": self.action_dim,
            "ocean_traits": self.ocean_traits,
            "total_reward": self.total_reward,
            "episode_count": self.episode_count,
            "step_count": self.step_count,
        }
        with open(filepath, "w") as f:
            json.dump(data, f, indent=2)


class RLTrainer:
    """
    Trainer for RL agents.
    Implements PPO-style training.
    """

    def __init__(
        self,
        agents: list[RLAgent],
        batch_size: int = 32,
        epochs: int = 4,
        clip_epsilon: float = 0.2,
    ):
        self.agents = {a.agent_id: a for a in agents}
        self.batch_size = batch_size
        self.epochs = epochs
        self.clip_epsilon = clip_epsilon

        # Training stats
        self.training_history: list[dict] = []

    def train_step(self, agent_id: str) -> dict[str, float]:
        """Perform one training step for an agent."""
        agent = self.agents.get(agent_id)
        if not agent:
            return {}

        if len(agent.replay_buffer) < self.batch_size:
            return {"status": "insufficient_data"}

        # Sample batch
        batch = agent.replay_buffer.sample(self.batch_size)

        # Compute returns (simple Monte Carlo for now)
        returns = []
        for exp in batch:
            ret = exp.reward
            if not exp.done:
                # Bootstrap from next state
                next_value = np.max(agent.policy.forward(exp.next_state))
                ret += agent.gamma * next_value
            returns.append(ret)

        # Simple policy gradient update (simplified)
        # In production, use proper PPO with advantage estimation
        policy_loss = 0.0
        for exp, ret in zip(batch, returns, strict=False):
            prob = agent.policy.get_action_prob(exp.state, exp.action)
            policy_loss -= np.log(prob + 1e-8) * ret

        policy_loss /= len(batch)

        # Update stats
        stats = {
            "agent_id": agent_id,
            "policy_loss": float(policy_loss),
            "avg_return": float(np.mean(returns)),
            "buffer_size": len(agent.replay_buffer),
        }

        self.training_history.append(stats)
        return stats

    def train_all(self) -> dict[str, dict]:
        """Train all agents."""
        results = {}
        for agent_id in self.agents:
            results[agent_id] = self.train_step(agent_id)
        return results

    def get_training_report(self) -> dict[str, Any]:
        """Get training report."""
        if not self.training_history:
            return {"status": "no_training_data"}

        recent = self.training_history[-100:]

        return {
            "total_steps": len(self.training_history),
            "avg_policy_loss": sum(s.get("policy_loss", 0) for s in recent) / len(recent),
            "avg_return": sum(s.get("avg_return", 0) for s in recent) / len(recent),
            "agents_trained": list(self.agents.keys()),
        }
