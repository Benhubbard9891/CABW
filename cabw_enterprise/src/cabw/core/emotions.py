"""Emotional system with contagion for CABW agents."""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional


# Supported emotion dimensions (PAD model: Pleasure, Arousal, Dominance)
EMOTION_DIMENSIONS = ("pleasure", "arousal", "dominance")


@dataclass
class EmotionalState:
    """Represents the emotional state of an agent using the PAD model."""

    pleasure: float = 0.0    # Valence: -1.0 (negative) to 1.0 (positive)
    arousal: float = 0.0     # Arousal: -1.0 (calm) to 1.0 (excited)
    dominance: float = 0.0   # Dominance: -1.0 (submissive) to 1.0 (dominant)

    def __post_init__(self) -> None:
        self._clamp()

    def _clamp(self) -> None:
        self.pleasure = max(-1.0, min(1.0, self.pleasure))
        self.arousal = max(-1.0, min(1.0, self.arousal))
        self.dominance = max(-1.0, min(1.0, self.dominance))

    def as_vector(self) -> List[float]:
        return [self.pleasure, self.arousal, self.dominance]

    def distance(self, other: "EmotionalState") -> float:
        """Euclidean distance between two emotional states."""
        return math.sqrt(
            (self.pleasure - other.pleasure) ** 2
            + (self.arousal - other.arousal) ** 2
            + (self.dominance - other.dominance) ** 2
        )

    def blend(self, other: "EmotionalState", weight: float = 0.5) -> "EmotionalState":
        """Return a new state blended with *other* by *weight* (0=self, 1=other)."""
        weight = max(0.0, min(1.0, weight))
        return EmotionalState(
            pleasure=self.pleasure + weight * (other.pleasure - self.pleasure),
            arousal=self.arousal + weight * (other.arousal - self.arousal),
            dominance=self.dominance + weight * (other.dominance - self.dominance),
        )

    def label(self) -> str:
        """Return a human-readable emotion label based on PAD values."""
        if self.pleasure > 0.3 and self.arousal > 0.3:
            return "excited"
        if self.pleasure > 0.3 and self.arousal <= 0.3:
            return "content"
        if self.pleasure <= -0.3 and self.arousal > 0.3:
            return "angry"
        if self.pleasure <= -0.3 and self.arousal <= -0.3:
            return "depressed"
        if self.pleasure <= -0.3:
            return "sad"
        return "neutral"


@dataclass
class EmotionalContagion:
    """Models how emotional states spread between agents in proximity."""

    contagion_rate: float = 0.1   # How strongly emotions spread per step
    decay_rate: float = 0.05      # How quickly emotions decay toward neutral

    def apply_contagion(
        self,
        agent_state: EmotionalState,
        neighbor_states: List[EmotionalState],
        proximity_weights: Optional[List[float]] = None,
    ) -> EmotionalState:
        """Compute the new emotional state after contagion from neighbors.

        Parameters
        ----------
        agent_state:
            Current emotional state of the agent.
        neighbor_states:
            Emotional states of neighboring agents.
        proximity_weights:
            Optional per-neighbor weight (e.g., based on distance). Defaults to
            uniform weighting.
        """
        if not neighbor_states:
            return self._apply_decay(agent_state)

        if proximity_weights is None:
            proximity_weights = [1.0 / len(neighbor_states)] * len(neighbor_states)
        else:
            total = sum(proximity_weights) or 1.0
            proximity_weights = [w / total for w in proximity_weights]

        avg_pleasure = sum(
            w * s.pleasure for w, s in zip(proximity_weights, neighbor_states)
        )
        avg_arousal = sum(
            w * s.arousal for w, s in zip(proximity_weights, neighbor_states)
        )
        avg_dominance = sum(
            w * s.dominance for w, s in zip(proximity_weights, neighbor_states)
        )

        new_state = EmotionalState(
            pleasure=agent_state.pleasure
            + self.contagion_rate * (avg_pleasure - agent_state.pleasure),
            arousal=agent_state.arousal
            + self.contagion_rate * (avg_arousal - agent_state.arousal),
            dominance=agent_state.dominance
            + self.contagion_rate * (avg_dominance - agent_state.dominance),
        )
        return self._apply_decay(new_state)

    def _apply_decay(self, state: EmotionalState) -> EmotionalState:
        """Move the emotional state slightly toward neutral (0, 0, 0)."""
        return EmotionalState(
            pleasure=state.pleasure * (1.0 - self.decay_rate),
            arousal=state.arousal * (1.0 - self.decay_rate),
            dominance=state.dominance * (1.0 - self.decay_rate),
        )


@dataclass
class EmotionalMemory:
    """Stores a history of emotional states for an agent."""

    max_history: int = 100
    history: List[EmotionalState] = field(default_factory=list)

    def record(self, state: EmotionalState) -> None:
        self.history.append(state)
        if len(self.history) > self.max_history:
            self.history.pop(0)

    def average_state(self) -> EmotionalState:
        """Return the average emotional state over recorded history."""
        if not self.history:
            return EmotionalState()
        n = len(self.history)
        return EmotionalState(
            pleasure=sum(s.pleasure for s in self.history) / n,
            arousal=sum(s.arousal for s in self.history) / n,
            dominance=sum(s.dominance for s in self.history) / n,
        )

    def mood_trend(self) -> Dict[str, float]:
        """Return the trend (slope) of each emotion dimension over history."""
        n = len(self.history)
        if n < 2:
            return {"pleasure": 0.0, "arousal": 0.0, "dominance": 0.0}
        indices = list(range(n))
        mean_i = (n - 1) / 2.0

        def slope(values: List[float]) -> float:
            mean_v = sum(values) / n
            numerator = sum((i - mean_i) * (v - mean_v) for i, v in zip(indices, values))
            denominator = sum((i - mean_i) ** 2 for i in indices) or 1.0
            return numerator / denominator

        return {
            "pleasure": slope([s.pleasure for s in self.history]),
            "arousal": slope([s.arousal for s in self.history]),
            "dominance": slope([s.dominance for s in self.history]),
        }
