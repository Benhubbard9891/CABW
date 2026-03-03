"""
Complex Action System for CABW Enterprise.

Implements:
- Actions with preconditions and effects
- Action composition (sequences, conditionals)
- Resource costs and requirements
- Failure modes and recovery
- Social actions with relationship effects
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto
from typing import Any

from cabw.utils.logging import get_logger

logger = get_logger(__name__)


class ActionCategory(Enum):
    """Categories of actions."""
    PHYSICAL = auto()
    COGNITIVE = auto()
    SOCIAL = auto()
    EMOTIONAL = auto()
    COMBAT = auto()
    CRAFTING = auto()
    MOVEMENT = auto()
    PERCEPTION = auto()
    META = auto()


class ActionPhase(Enum):
    """Execution phases of actions."""
    PREPARATION = auto()    # Setup, gather resources
    EXECUTION = auto()      # Main action
    RECOVERY = auto()       # Cooldown, exhaustion


class ActionOutcome(Enum):
    """Possible action outcomes."""
    SUCCESS = auto()
    PARTIAL_SUCCESS = auto()
    FAILURE = auto()
    CRITICAL_FAILURE = auto()
    CANCELLED = auto()
    INTERRUPTED = auto()


@dataclass
class ActionCost:
    """Resource costs for an action."""
    stamina: float = 0.0
    action_points: float = 0.0
    mana: float = 0.0  # For magical actions
    items: dict[str, int] = field(default_factory=dict)
    time: float = 1.0  # Time units

    def can_afford(self, resources: dict[str, Any]) -> bool:
        """Check if resources are sufficient."""
        if resources.get('stamina', 0) < self.stamina:
            return False
        if resources.get('action_points', 0) < self.action_points:
            return False
        if resources.get('mana', 0) < self.mana:
            return False

        inventory = resources.get('inventory', {})
        return all(inventory.get(item, 0) >= count for item, count in self.items.items())

    def deduct(self, resources: dict[str, Any]) -> None:
        """Deduct costs from resources."""
        resources['stamina'] = resources.get('stamina', 0) - self.stamina
        resources['action_points'] = resources.get('action_points', 0) - self.action_points
        resources['mana'] = resources.get('mana', 0) - self.mana

        inventory = resources.get('inventory', {})
        for item, count in self.items.items():
            inventory[item] = inventory.get(item, 0) - count


@dataclass
class ActionPrecondition:
    """Precondition for an action."""
    condition_type: str  # 'skill', 'item', 'state', 'relationship', 'zone'
    key: str
    operator: str  # 'eq', 'gt', 'lt', 'gte', 'lte', 'in', 'contains'
    value: Any
    error_message: str | None = None

    def check(self, context: dict[str, Any]) -> tuple[bool, str | None]:
        """Check if precondition is satisfied."""
        # Get value from context
        if self.condition_type == 'skill':
            actual = context.get('skills', {}).get(self.key)
        elif self.condition_type == 'item':
            actual = context.get('inventory', {}).get(self.key, 0)
        elif self.condition_type == 'state':
            actual = context.get('state', {}).get(self.key)
        elif self.condition_type == 'relationship':
            rel = context.get('relationships', {}).get(self.key)
            actual = rel.get('trust') if rel else None
        elif self.condition_type == 'zone':
            actual = context.get('zone', {}).get(self.key)
        else:
            actual = context.get(self.key)

        # Compare
        result = self._compare(actual, self.operator, self.value)

        if not result:
            msg = self.error_message or f"Precondition failed: {self.key} {self.operator} {self.value}"
            return False, msg

        return True, None

    def _compare(self, actual: Any, op: str, expected: Any) -> bool:
        """Compare values."""
        if actual is None:
            return False

        if op == 'eq':
            return actual == expected
        elif op == 'gt':
            return actual > expected
        elif op == 'lt':
            return actual < expected
        elif op == 'gte':
            return actual >= expected
        elif op == 'lte':
            return actual <= expected
        elif op == 'in':
            return actual in expected
        elif op == 'contains':
            return expected in actual

        return False


@dataclass
class ActionEffect:
    """Effect of an action."""
    effect_type: str  # 'stat', 'item', 'emotion', 'relationship', 'zone', 'memory'
    target: str
    operation: str  # 'set', 'add', 'multiply', 'remove'
    value: Any
    duration: float | None = None  # Temporary effect duration
    probability: float = 1.0  # Effect probability (0-1)

    def apply(self, context: dict[str, Any]) -> dict[str, Any]:
        """Apply effect to context."""
        if self.probability < 1.0:
            import random
            if random.random() > self.probability:
                return {'applied': False, 'reason': 'probability'}

        result = {'applied': True, 'effect_type': self.effect_type}

        if self.effect_type == 'stat':
            stats = context.setdefault('stats', {})
            current = stats.get(self.target, 0)
            new_val = self._apply_operation(current, self.operation, self.value)
            stats[self.target] = new_val
            result['old_value'] = current
            result['new_value'] = new_val

        elif self.effect_type == 'item':
            inventory = context.setdefault('inventory', {})
            if self.operation == 'add':
                inventory[self.target] = inventory.get(self.target, 0) + self.value
            elif self.operation == 'remove':
                inventory[self.target] = max(0, inventory.get(self.target, 0) - self.value)
            result['new_count'] = inventory.get(self.target, 0)

        elif self.effect_type == 'emotion':
            emotions = context.setdefault('emotions', {})
            current = emotions.get(self.target, 0)
            new_val = self._apply_operation(current, self.operation, self.value)
            emotions[self.target] = max(0, min(1, new_val))
            result['old_value'] = current
            result['new_value'] = emotions[self.target]

        elif self.effect_type == 'relationship':
            relationships = context.setdefault('relationships', {})
            rel = relationships.get(self.target, {})
            metric = self.value.get('metric', 'affection')
            change = self.value.get('change', 0)
            old_val = rel.get(metric, 0)
            rel[metric] = self._apply_operation(old_val, 'add', change)
            relationships[self.target] = rel
            result['metric'] = metric
            result['old_value'] = old_val
            result['new_value'] = rel[metric]

        elif self.effect_type == 'memory':
            memories = context.setdefault('memories', [])
            memories.append({
                'content': self.value.get('content', ''),
                'type': self.value.get('type', 'observation'),
                'timestamp': datetime.utcnow().isoformat(),
            })
            result['memory_added'] = True

        return result

    def _apply_operation(self, current: float, op: str, value: Any) -> float:
        """Apply mathematical operation."""
        if op == 'set':
            return value
        elif op == 'add':
            return current + value
        elif op == 'multiply':
            return current * value
        elif op == 'remove':
            return max(0, current - value)
        return current


@dataclass
class ComplexAction:
    """
    Complex action with preconditions, costs, and effects.

    Actions can be:
    - Atomic (single execution)
    - Sequential (multiple actions in order)
    - Conditional (branch based on state)
    - Parallel (multiple actions simultaneously)
    """
    id: str
    name: str
    description: str
    category: ActionCategory

    # Requirements
    preconditions: list[ActionPrecondition] = field(default_factory=list)
    costs: ActionCost = field(default_factory=ActionCost)

    # Effects
    effects: list[ActionEffect] = field(default_factory=list)
    failure_effects: list[ActionEffect] = field(default_factory=list)

    # Execution
    duration: float = 1.0  # Base duration
    interruptible: bool = True
    requires_target: bool = False
    valid_targets: list[str] = field(default_factory=list)

    # Composition
    sub_actions: list[ComplexAction] = field(default_factory=list)
    composition_type: str = 'atomic'  # 'atomic', 'sequence', 'choice', 'parallel'

    # Metadata
    skill_requirements: dict[str, float] = field(default_factory=dict)
    tags: set[str] = field(default_factory=set)

    def can_execute(self, context: dict[str, Any]) -> tuple[bool, list[str]]:
        """Check if action can be executed."""
        failures = []

        # Check preconditions
        for precond in self.preconditions:
            ok, msg = precond.check(context)
            if not ok:
                failures.append(msg or f"Precondition failed: {precond.key}")

        # Check costs
        if not self.costs.can_afford(context):
            failures.append("Insufficient resources")

        # Check skill requirements
        skills = context.get('skills', {})
        for skill, level in self.skill_requirements.items():
            if skills.get(skill, 0) < level:
                failures.append(f"Insufficient {skill} skill (need {level})")

        return len(failures) == 0, failures

    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        """
        Execute the action.

        Returns execution result with effects applied.
        """
        # Check can execute
        can_exec, failures = self.can_execute(context)
        if not can_exec:
            return {
                'success': False,
                'outcome': ActionOutcome.FAILURE,
                'reason': 'precondition_failed',
                'failures': failures,
            }

        # Deduct costs
        self.costs.deduct(context)

        # Apply effects
        results = []
        for effect in self.effects:
            result = effect.apply(context)
            results.append(result)

        return {
            'success': True,
            'outcome': ActionOutcome.SUCCESS,
            'effects_applied': results,
            'duration': self.duration,
        }

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'category': self.category.name,
            'duration': self.duration,
            'interruptible': self.interruptible,
            'requires_target': self.requires_target,
            'skill_requirements': self.skill_requirements,
            'tags': list(self.tags),
        }


# Predefined complex actions
class ActionLibrary:
    """Library of predefined complex actions."""

    @staticmethod
    def create_attack_action() -> ComplexAction:
        """Create attack action."""
        return ComplexAction(
            id='attack',
            name='Attack',
            description='Attack a target with equipped weapon',
            category=ActionCategory.COMBAT,
            preconditions=[
                ActionPrecondition('state', 'in_combat', 'eq', True, 'Must be in combat'),
                ActionPrecondition('state', 'stunned', 'eq', False, 'Cannot attack while stunned'),
            ],
            costs=ActionCost(stamina=15.0, action_points=1.0),
            effects=[
                ActionEffect('stat', 'target_hp', 'add', -10.0, probability=0.8),
                ActionEffect('emotion', 'anger', 'add', 0.1),
                ActionEffect('memory', 'combat', 'add', {
                    'content': 'Attacked an enemy',
                    'type': 'combat'
                }),
            ],
            failure_effects=[
                ActionEffect('emotion', 'frustration', 'add', 0.2),
            ],
            duration=1.0,
            requires_target=True,
            skill_requirements={'combat': 0.1},
            tags={'combat', 'aggressive'},
        )

    @staticmethod
    def create_heal_action() -> ComplexAction:
        """Create heal action."""
        return ComplexAction(
            id='heal',
            name='Heal',
            description='Heal self or ally',
            category=ActionCategory.PHYSICAL,
            preconditions=[
                ActionPrecondition('item', 'healing_potion', 'gte', 1, 'Need healing potion'),
            ],
            costs=ActionCost(
                stamina=5.0,
                action_points=1.0,
                items={'healing_potion': 1}
            ),
            effects=[
                ActionEffect('stat', 'hp', 'add', 25.0),
                ActionEffect('emotion', 'gratitude', 'add', 0.1),
            ],
            duration=2.0,
            tags={'healing', 'support'},
        )

    @staticmethod
    def create_persuade_action() -> ComplexAction:
        """Create social persuasion action."""
        return ComplexAction(
            id='persuade',
            name='Persuade',
            description='Attempt to persuade someone',
            category=ActionCategory.SOCIAL,
            preconditions=[
                ActionPrecondition('relationship', 'target', 'gte', 0, 'Cannot persuade enemies'),
            ],
            costs=ActionCost(stamina=5.0, action_points=1.0),
            effects=[
                ActionEffect('relationship', 'target', 'add', {
                    'metric': 'trust',
                    'change': 0.1
                }, probability=0.6),
                ActionEffect('emotion', 'pride', 'add', 0.1, probability=0.5),
            ],
            failure_effects=[
                ActionEffect('relationship', 'target', 'add', {
                    'metric': 'trust',
                    'change': -0.05
                }),
            ],
            duration=3.0,
            requires_target=True,
            skill_requirements={'social': 0.3},
            tags={'social', 'diplomatic'},
        )

    @staticmethod
    def create_coordinate_action() -> ComplexAction:
        """Create teamwork coordination action."""
        return ComplexAction(
            id='coordinate',
            name='Coordinate',
            description='Coordinate with teammates for tactical advantage',
            category=ActionCategory.SOCIAL,
            preconditions=[
                ActionPrecondition('state', 'has_team', 'eq', True, 'Need teammates'),
                ActionPrecondition('state', 'in_combat', 'eq', True, 'Must be in combat'),
            ],
            costs=ActionCost(stamina=8.0, action_points=0.5),
            effects=[
                ActionEffect('stat', 'team_coordination', 'set', 1.0),
                ActionEffect('stat', 'tactical_bonus', 'add', 0.2),
                ActionEffect('emotion', 'trust', 'add', 0.05),
                ActionEffect('memory', 'teamwork', 'add', {
                    'content': 'Successfully coordinated with team',
                    'type': 'achievement'
                }),
            ],
            duration=2.0,
            skill_requirements={'leadership': 0.2},
            tags={'teamwork', 'leadership', 'tactical'},
        )

    @staticmethod
    def create_cover_ally_action() -> ComplexAction:
        """Create cover ally action."""
        return ComplexAction(
            id='cover_ally',
            name='Cover Ally',
            description='Protect an ally from incoming attacks',
            category=ActionCategory.COMBAT,
            preconditions=[
                ActionPrecondition('state', 'in_combat', 'eq', True),
                ActionPrecondition('relationship', 'target', 'gte', 0.3, 'Must trust ally'),
            ],
            costs=ActionCost(stamina=10.0, action_points=1.0),
            effects=[
                ActionEffect('stat', 'ally_defense', 'add', 0.5),
                ActionEffect('relationship', 'target', 'add', {
                    'metric': 'affection',
                    'change': 0.05
                }),
                ActionEffect('emotion', 'pride', 'add', 0.05),
            ],
            duration=1.5,
            requires_target=True,
            tags={'teamwork', 'defensive', 'protective'},
        )


# Action sequencer for complex behaviors
class ActionSequence:
    """Sequence of actions to execute."""

    def __init__(self, name: str):
        """Initialize action sequence."""
        self.name = name
        self.actions: list[ComplexAction] = []
        self.current_index: int = 0
        self.completed: list[dict] = []
        self.failed: dict | None = None

    def add(self, action: ComplexAction) -> ActionSequence:
        """Add action to sequence."""
        self.actions.append(action)
        return self

    def execute_next(self, context: dict[str, Any]) -> dict | None:
        """Execute next action in sequence."""
        if self.current_index >= len(self.actions):
            return None

        action = self.actions[self.current_index]
        result = action.execute(context)

        if result['success']:
            self.completed.append({
                'action': action.id,
                'result': result,
            })
            self.current_index += 1
        else:
            self.failed = {
                'action': action.id,
                'result': result,
            }

        return result

    def is_complete(self) -> bool:
        """Check if sequence is complete."""
        return self.current_index >= len(self.actions) or self.failed is not None

    def get_summary(self) -> dict[str, Any]:
        """Get execution summary."""
        return {
            'name': self.name,
            'total_actions': len(self.actions),
            'completed': len(self.completed),
            'failed': self.failed is not None,
            'completed_actions': [c['action'] for c in self.completed],
            'failure': self.failed,
        }


__all__ = [
    'ActionCategory',
    'ActionPhase',
    'ActionOutcome',
    'ActionCost',
    'ActionPrecondition',
    'ActionEffect',
    'ComplexAction',
    'ActionLibrary',
    'ActionSequence',
]
