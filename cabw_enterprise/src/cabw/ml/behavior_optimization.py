"""
Behavior Optimization using Machine Learning

Optimizes agent behavior trees, deliberation weights, and action selection
using evolutionary algorithms and gradient-based optimization.
"""

import json
import random
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any


@dataclass
class BehaviorMetrics:
    """Metrics for evaluating agent behavior."""
    survival_rate: float = 0.0
    goal_completion: float = 0.0
    team_coordination: float = 0.0
    resource_efficiency: float = 0.0
    emotional_stability: float = 0.0
    social_integration: float = 0.0

    def overall_score(self) -> float:
        """Calculate overall behavior score."""
        weights = [0.2, 0.25, 0.2, 0.15, 0.1, 0.1]
        values = [
            self.survival_rate,
            self.goal_completion,
            self.team_coordination,
            self.resource_efficiency,
            self.emotional_stability,
            self.social_integration
        ]
        return sum(w * v for w, v in zip(weights, values, strict=False))


class DeliberationWeightOptimizer:
    """
    Optimize deliberation factor weights using evolutionary algorithm.
    """

    def __init__(
        self,
        population_size: int = 50,
        mutation_rate: float = 0.1,
        crossover_rate: float = 0.7,
        elite_ratio: float = 0.1
    ):
        self.population_size = population_size
        self.mutation_rate = mutation_rate
        self.crossover_rate = crossover_rate
        self.elite_ratio = elite_ratio

        # Factor names
        self.factors = [
            'personality', 'emotion', 'memory',
            'relationship', 'need', 'environment', 'social'
        ]

        # Population: list of (weights_dict, fitness) tuples
        self.population: list[tuple[dict[str, float], float]] = []
        self.generation = 0
        self.best_weights: dict[str, float] | None = None
        self.best_fitness = 0.0

        # History
        self.fitness_history: list[float] = []

        self._init_population()

    def _init_population(self):
        """Initialize random population."""
        for _ in range(self.population_size):
            weights = {f: random.uniform(0.05, 0.3) for f in self.factors}
            # Normalize to sum to 1
            total = sum(weights.values())
            weights = {k: v / total for k, v in weights.values()}
            self.population.append((weights, 0.0))

    def evaluate_fitness(
        self,
        weights: dict[str, float],
        simulation_runner: Callable[[dict[str, float]], BehaviorMetrics]
    ) -> float:
        """Evaluate fitness of weight configuration."""
        metrics = simulation_runner(weights)
        return metrics.overall_score()

    def evolve_generation(
        self,
        simulation_runner: Callable[[dict[str, float]], BehaviorMetrics]
    ):
        """Evolve one generation."""
        # Evaluate fitness
        evaluated = []
        for weights, _ in self.population:
            fitness = self.evaluate_fitness(weights, simulation_runner)
            evaluated.append((weights, fitness))

        # Sort by fitness
        evaluated.sort(key=lambda x: x[1], reverse=True)

        # Update best
        if evaluated[0][1] > self.best_fitness:
            self.best_weights = evaluated[0][0].copy()
            self.best_fitness = evaluated[0][1]

        self.fitness_history.append(evaluated[0][1])

        # Elitism: keep top performers
        elite_count = int(self.population_size * self.elite_ratio)
        new_population = evaluated[:elite_count]

        # Generate offspring
        while len(new_population) < self.population_size:
            parent1 = self._tournament_select(evaluated)
            parent2 = self._tournament_select(evaluated)

            if random.random() < self.crossover_rate:
                child = self._crossover(parent1, parent2)
            else:
                child = parent1.copy()

            if random.random() < self.mutation_rate:
                child = self._mutate(child)

            new_population.append((child, 0.0))

        self.population = new_population
        self.generation += 1

    def _tournament_select(
        self,
        population: list[tuple[dict[str, float], float]],
        tournament_size: int = 3
    ) -> dict[str, float]:
        """Tournament selection."""
        tournament = random.sample(population, tournament_size)
        tournament.sort(key=lambda x: x[1], reverse=True)
        return tournament[0][0].copy()

    def _crossover(
        self,
        parent1: dict[str, float],
        parent2: dict[str, float]
    ) -> dict[str, float]:
        """Blend crossover."""
        alpha = random.uniform(0, 1)
        child = {}
        for factor in self.factors:
            child[factor] = alpha * parent1[factor] + (1 - alpha) * parent2[factor]

        # Normalize
        total = sum(child.values())
        return {k: v / total for k, v in child.items()}

    def _mutate(self, weights: dict[str, float]) -> dict[str, float]:
        """Gaussian mutation."""
        mutated = weights.copy()
        factor = random.choice(self.factors)
        mutated[factor] += random.gauss(0, 0.05)
        mutated[factor] = max(0.01, min(0.5, mutated[factor]))

        # Normalize
        total = sum(mutated.values())
        return {k: v / total for k, v in mutated.items()}

    def train(
        self,
        simulation_runner: Callable[[dict[str, float]], BehaviorMetrics],
        generations: int = 100,
        target_fitness: float = 0.9
    ) -> dict[str, float]:
        """Train until convergence or max generations."""
        for gen in range(generations):
            self.evolve_generation(simulation_runner)

            if self.best_fitness >= target_fitness:
                print(f"Target fitness reached at generation {gen}")
                break

            if gen % 10 == 0:
                print(f"Generation {gen}: best fitness = {self.best_fitness:.4f}")

        return self.best_weights

    def export_weights(self, filepath: str):
        """Export optimized weights."""
        data = {
            'weights': self.best_weights,
            'fitness': self.best_fitness,
            'generations': self.generation,
            'fitness_history': self.fitness_history
        }
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)


class BehaviorOptimizer:
    """
    High-level behavior optimizer coordinating multiple optimization strategies.
    """

    def __init__(self):
        self.deliberation_optimizer = DeliberationWeightOptimizer()
        self.behavior_tree_optimizer = None  # Placeholder for BT optimization
        self.action_sequence_optimizer = None  # Placeholder for action sequence opt

        # Optimization history
        self.optimization_runs: list[dict] = []

    def optimize_deliberation_weights(
        self,
        simulation_runner: Callable[[dict[str, float]], BehaviorMetrics],
        generations: int = 100
    ) -> dict[str, float]:
        """Optimize deliberation weights."""
        print("Starting deliberation weight optimization...")
        weights = self.deliberation_optimizer.train(
            simulation_runner,
            generations=generations
        )

        self.optimization_runs.append({
            'type': 'deliberation_weights',
            'generations': self.deliberation_optimizer.generation,
            'best_fitness': self.deliberation_optimizer.best_fitness,
            'weights': weights
        })

        return weights

    def recommend_behavior_tree_modifications(
        self,
        agent,
        performance_history: list[BehaviorMetrics]
    ) -> list[dict[str, Any]]:
        """
        Recommend behavior tree modifications based on performance.
        Uses rule-based analysis for now; ML-based in future.
        """
        recommendations = []

        if not performance_history:
            return recommendations

        recent = performance_history[-10:]
        avg_survival = sum(m.survival_rate for m in recent) / len(recent)
        avg_goals = sum(m.goal_completion for m in recent) / len(recent)

        # Low survival → add more defensive nodes
        if avg_survival < 0.5:
            recommendations.append({
                'type': 'add_node',
                'location': 'selector.combat',
                'node': 'health_check',
                'reason': 'Low survival rate - add health monitoring'
            })

        # Low goal completion → adjust priorities
        if avg_goals < 0.3:
            recommendations.append({
                'type': 'reorder',
                'sequence': 'exploration',
                'new_priority': 'goal_finding',
                'reason': 'Low goal completion - prioritize goal detection'
            })

        # Emotional instability → add regulation
        avg_stability = sum(m.emotional_stability for m in recent) / len(recent)
        if avg_stability < 0.4:
            recommendations.append({
                'type': 'add_decorator',
                'location': 'root',
                'decorator': 'cooldown',
                'params': {'duration': 5},
                'reason': 'Emotional instability - add action cooldowns'
            })

        return recommendations

    def get_optimization_report(self) -> dict[str, Any]:
        """Get report of all optimization runs."""
        return {
            'total_runs': len(self.optimization_runs),
            'runs': self.optimization_runs,
            'current_best_weights': self.deliberation_optimizer.best_weights,
            'current_best_fitness': self.deliberation_optimizer.best_fitness
        }
