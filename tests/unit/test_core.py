"""Unit tests for core CABW modules."""

import pytest


@pytest.mark.unit
def test_imports():
    """Smoke test: verify core modules can be imported."""
    from cabw.core.actions import ActionContext, ActionEffect, ActionPrecondition, ComplexAction
    from cabw.core.emotions import EmotionalState, MoodState
    from cabw.worldgen.terrain import TerrainGenerator

    assert ActionContext is not None
    assert ActionPrecondition is not None
    assert ActionEffect is not None
    assert ComplexAction is not None
    assert EmotionalState is not None
    assert MoodState is not None
    assert TerrainGenerator is not None


@pytest.mark.unit
def test_action_condition_compare():
    """Test ActionPrecondition comparison logic."""
    from cabw.core.actions import ActionPrecondition

    cond = ActionPrecondition(condition_type="state", key="health", operator="gt", value=50)
    assert cond._compare(100, "gt", 50) is True
    assert cond._compare(30, "gt", 50) is False
    assert cond._compare(5, "eq", 5) is True
    assert cond._compare(5, "lt", 10) is True
    assert cond._compare(5, "lte", 5) is True
    assert cond._compare(5, "gte", 5) is True
    assert cond._compare("a", "in", ["a", "b"]) is True
    assert cond._compare("hello", "contains", "ell") is True
    assert cond._compare(None, "eq", 5) is False


@pytest.mark.unit
def test_emotional_state():
    """Test EmotionalState basic functionality."""
    from cabw.core.emotions import EmotionalState

    state = EmotionalState()
    assert state is not None
    assert state.mood is not None


@pytest.mark.unit
def test_terrain_generator_noise():
    """Test TerrainGenerator Perlin noise."""
    from cabw.worldgen.terrain import TerrainGenerator

    gen = TerrainGenerator(seed=42)
    value = gen.elevation_noise.noise(0.5, 0.5)
    assert isinstance(value, float)
    assert -1.0 <= value <= 1.0
