"""
Deliberation Engine

Explicit deliberation loop integrating memory, emotions, personality, and relationships.
Memory → Action scoring wire.
"""

import random
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any

from .actions import ComplexAction
from .emotions import EmotionalState
from .teamwork import Team


class DeliberationFactor(Enum):
    """Factors in action deliberation."""
    PERSONALITY = auto()
    EMOTION = auto()
    MEMORY = auto()
    RELATIONSHIP = auto()
    NEED = auto()
    ENVIRONMENT = auto()
    SOCIAL = auto()


@dataclass
class ActionScore:
    """Scored action with factor breakdown."""
    action: ComplexAction
    total_score: float
    factors: dict[DeliberationFactor, float] = field(default_factory=dict)
    reasoning: list[str] = field(default_factory=list)

    def explain(self) -> str:
        """Generate explanation of scoring."""
        lines = [f"Action '{self.action.name}': {self.total_score:.3f}"]
        for factor, score in self.factors.items():
            lines.append(f"  {factor.name}: {score:.3f}")
        lines.append(f"  Reasoning: {'; '.join(self.reasoning)}")
        return '\n'.join(lines)


class DeliberationEngine:
    """
    Deliberation engine for action selection.
    Integrates all cognitive factors into explicit scoring.
    """

    def __init__(
        self,
        personality_weight: float = 0.2,
        emotion_weight: float = 0.25,
        memory_weight: float = 0.2,
        relationship_weight: float = 0.15,
        need_weight: float = 0.15,
        environment_weight: float = 0.05
    ):
        self.weights = {
            DeliberationFactor.PERSONALITY: personality_weight,
            DeliberationFactor.EMOTION: emotion_weight,
            DeliberationFactor.MEMORY: memory_weight,
            DeliberationFactor.RELATIONSHIP: relationship_weight,
            DeliberationFactor.NEED: need_weight,
            DeliberationFactor.ENVIRONMENT: environment_weight,
            DeliberationFactor.SOCIAL: 0.0  # Added dynamically
        }

        # Factor calculators
        self._calculators: dict[DeliberationFactor, Callable] = {}

    def register_calculator(
        self,
        factor: DeliberationFactor,
        calculator: Callable[[Any, ComplexAction, Any], float]
    ):
        """Register a factor calculator."""
        self._calculators[factor] = calculator

    def score_action(
        self,
        agent,
        action: ComplexAction,
        context: Any = None
    ) -> ActionScore:
        """
        Score an action using all deliberation factors.
        This is the core deliberation loop.
        """
        factors = {}
        reasoning = []

        # 1. Personality bias
        personality_score = self._score_personality(agent, action)
        factors[DeliberationFactor.PERSONALITY] = personality_score
        reasoning.append(f"OCEAN bias: {personality_score:.2f}")

        # 2. Emotional urgency
        emotion_score = self._score_emotion(agent, action)
        factors[DeliberationFactor.EMOTION] = emotion_score
        reasoning.append(f"PAD urgency: {emotion_score:.2f}")

        # 3. Memory salience (THE WIRE)
        memory_score = self._score_memory(agent, action)
        factors[DeliberationFactor.MEMORY] = memory_score
        reasoning.append(f"Memory salience: {memory_score:.2f}")

        # 4. Relationship trust gate
        relationship_score = self._score_relationship(agent, action)
        factors[DeliberationFactor.RELATIONSHIP] = relationship_score
        reasoning.append(f"Relationship trust: {relationship_score:.2f}")

        # 5. Need satisfaction
        need_score = self._score_need(agent, action)
        factors[DeliberationFactor.NEED] = need_score
        reasoning.append(f"Need match: {need_score:.2f}")

        # 6. Environment fit
        env_score = self._score_environment(agent, action, context)
        factors[DeliberationFactor.ENVIRONMENT] = env_score
        reasoning.append(f"Environment fit: {env_score:.2f}")

        # 7. Social context (if in team)
        social_score = self._score_social(agent, action)
        if social_score != 1.0:
            factors[DeliberationFactor.SOCIAL] = social_score
            reasoning.append(f"Social context: {social_score:.2f}")

        # Calculate weighted total
        total = sum(
            factors.get(factor, 0.0) * self.weights.get(factor, 0.0)
            for factor in DeliberationFactor
        )

        return ActionScore(
            action=action,
            total_score=total,
            factors=factors,
            reasoning=reasoning
        )

    def select_action(
        self,
        agent,
        actions: list[ComplexAction],
        context: Any = None,
        exploration_rate: float = 0.1
    ) -> ActionScore | None:
        """
        Select best action from candidates.
        Uses epsilon-greedy with exploration.
        """
        if not actions:
            return None

        # Score all actions
        scored = [self.score_action(agent, action, context) for action in actions]

        # Exploration: random choice
        if random.random() < exploration_rate:
            return random.choice(scored)

        # Exploitation: best score
        scored.sort(key=lambda x: x.total_score, reverse=True)
        return scored[0] if scored else None

    def _score_personality(self, agent, action: ComplexAction) -> float:
        """Score based on OCEAN personality fit."""
        if not hasattr(agent, 'ocean_traits'):
            return 0.5

        traits = agent.ocean_traits
        score = 0.5

        # Action type personality mappings
        action_traits = getattr(action, 'personality_fit', {})

        for trait, action_preference in action_traits.items():
            agent_value = traits.get(trait, 0.5)
            # Higher score when agent trait matches action preference
            match = 1.0 - abs(agent_value - action_preference)
            score += match * 0.1

        return min(1.0, max(0.0, score))

    def _score_emotion(self, agent, action: ComplexAction) -> float:
        """Score based on emotional urgency (PAD)."""
        if not hasattr(agent, 'emotional_state'):
            return 0.5

        emotions: EmotionalState = agent.emotional_state

        # Get action's emotional profile
        action_emotions = getattr(action, 'emotional_profile', {})

        # Calculate match
        score = 0.5

        # High arousal → prefer urgent actions
        if emotions.get_arousal() > 0.6:
            if action_emotions.get('urgency', 0) > 0.5:
                score += 0.2
            else:
                score -= 0.1

        # Negative valence → prefer safety actions
        if emotions.get_valence() < -0.3 and action_emotions.get('safety', 0) > 0.5:
            score += 0.2

        # Fear → prefer escape/defense
        if emotions.fear > 0.5 and action_emotions.get('defensive', 0) > 0.5:
            score += 0.3

        # Anger → prefer confrontational actions
        if emotions.anger > 0.5 and action_emotions.get('confrontational', 0) > 0.5:
            score += 0.2

        return min(1.0, max(0.0, score))

    def _score_memory(self, agent, action: ComplexAction) -> float:
        """
        Score based on memory salience.
        THE CRITICAL WIRE: memory → deliberation.
        """
        if not hasattr(agent, 'memory'):
            return 0.5

        # Recall relevant memories
        context = getattr(action, 'context', action.name)
        memories = agent.memory.recall_relevant(context, limit=3)

        if not memories:
            return 0.5  # Neutral when no memories

        # Calculate salience-weighted score
        total_salience = 0.0
        weighted_score = 0.0

        for memory in memories:
            importance = memory.get('importance', 0.5)
            outcome = memory.get('outcome', 'neutral')

            # Positive outcomes increase score
            if outcome == 'positive':
                weighted_score += importance * 1.0
            elif outcome == 'negative':
                weighted_score += importance * 0.0
            else:
                weighted_score += importance * 0.5

            total_salience += importance

        if total_salience == 0:
            return 0.5

        return weighted_score / total_salience

    def _score_relationship(self, agent, action: ComplexAction) -> float:
        """Score based on relationship trust gate."""
        target_id = getattr(action, 'target_id', None)

        if not target_id or not hasattr(agent, 'relationships'):
            return 1.0  # No relationship check needed

        # Get relationship
        relationship = agent.relationships.get(target_id)
        if not relationship:
            return 0.7  # Cautious with strangers

        # Trust gate
        trust = relationship.get('trust', 0.5)

        # Action type modifiers
        action_type = getattr(action, 'action_type', 'neutral')

        if action_type == 'cooperative':
            return trust  # Need high trust for cooperation
        elif action_type == 'competitive':
            return 1.0 - trust  # Low trust enables competition
        elif action_type == 'hostile':
            return 1.0 - relationship.get('affection', 0.5)

        return 0.5 + trust * 0.5

    def _score_need(self, agent, action: ComplexAction) -> float:
        """Score based on need satisfaction."""
        if not hasattr(agent, 'needs'):
            return 0.5

        needs = agent.needs
        priority_need, urgency = needs.get_priority_need()

        # Get action's need satisfaction
        satisfies = getattr(action, 'satisfies_needs', {})

        if priority_need in satisfies:
            return 0.5 + urgency * 0.5  # High score for satisfying urgent need

        return 0.5

    def _score_environment(
        self,
        agent,
        action: ComplexAction,
        context: Any
    ) -> float:
        """Score based on environmental fit."""
        if context is None:
            return 0.5

        score = 0.5

        # Visibility check
        if hasattr(context, 'get_visibility'):
            visibility = context.get_visibility()
            if visibility < 0.3 and getattr(action, 'risky', False):
                # Low visibility → prefer cautious actions
                score -= 0.2

        # Weather effects
        if hasattr(context, 'weather'):
            weather = context.weather
            if weather.weather_type.name in ['STORM', 'BLIZZARD'] and getattr(action, 'outdoor', False):
                # Bad weather → prefer indoor/shelter actions
                score -= 0.15

        return max(0.0, min(1.0, score))

    def _score_social(self, agent, action: ComplexAction) -> float:
        """Score based on social/team context."""
        if not hasattr(agent, 'current_team') or not agent.current_team:
            return 1.0  # No team context

        team: Team = agent.current_team
        score = 1.0

        # Check if action aligns with team goals
        team_goals = team.active_goals
        if team_goals:
            goal_alignment = getattr(action, 'team_goal_alignment', 0.5)
            score *= (0.5 + goal_alignment * 0.5)

        # Role-appropriate actions
        if hasattr(agent, 'team_role'):
            role_actions = getattr(action, 'role_appropriate', [])
            if agent.team_role in role_actions:
                score += 0.1

        return min(1.0, score)


class DeliberationLogger:
    """Logger for deliberation decisions."""

    def __init__(self):
        self.decisions: list[dict] = []

    def log_decision(
        self,
        agent_id: str,
        selected: ActionScore,
        candidates: list[ActionScore],
        tick: int
    ):
        """Log a deliberation decision."""
        self.decisions.append({
            'tick': tick,
            'agent_id': agent_id,
            'selected_action': selected.action.name,
            'selected_score': selected.total_score,
            'selected_factors': {
                k.name: v for k, v in selected.factors.items()
            },
            'candidate_count': len(candidates),
            'candidate_scores': [
                {'action': c.action.name, 'score': c.total_score}
                for c in candidates
            ],
            'reasoning': selected.reasoning
        })

    def get_agent_decisions(self, agent_id: str) -> list[dict]:
        """Get all decisions for an agent."""
        return [d for d in self.decisions if d['agent_id'] == agent_id]

    def export(self, filepath: str):
        """Export decision log."""
        import json
        with open(filepath, 'w') as f:
            json.dump(self.decisions, f, indent=2)
