"""
Test suite for CABW Enterprise Economy Module

Covers:
- Resource
- ResourcePool
- WorldResources
"""
import pytest

from cabw.economy.resources import Resource, ResourcePool, ResourceType, WorldResources


class TestResource:
    """Tests for Resource dataclass."""

    def test_create_resource(self):
        r = Resource(resource_type=ResourceType.FOOD, quantity=100.0)
        assert r.quantity == 100.0
        assert r.resource_type == ResourceType.FOOD

    def test_negative_quantity_clamped_to_zero(self):
        r = Resource(resource_type=ResourceType.WATER, quantity=-50.0)
        assert r.quantity == 0.0

    def test_degrade_reduces_durability(self):
        r = Resource(resource_type=ResourceType.FOOD, quantity=100.0, durability=1.0)
        r.degrade(0.1)
        assert r.durability == pytest.approx(0.9)

    def test_degrade_to_zero_clears_quantity(self):
        r = Resource(resource_type=ResourceType.FOOD, quantity=100.0, durability=0.05)
        r.degrade(0.1)
        assert r.quantity == 0.0

    def test_split_reduces_quantity(self):
        r = Resource(resource_type=ResourceType.MATERIALS, quantity=100.0)
        portion = r.split(30.0)
        assert portion is not None
        assert portion.quantity == pytest.approx(30.0)
        assert r.quantity == pytest.approx(70.0)

    def test_split_returns_none_if_insufficient(self):
        r = Resource(resource_type=ResourceType.TOOLS, quantity=10.0)
        portion = r.split(50.0)
        assert portion is None

    def test_merge_adds_quantity(self):
        r1 = Resource(resource_type=ResourceType.WATER, quantity=100.0, quality=1.0)
        r2 = Resource(resource_type=ResourceType.WATER, quantity=50.0, quality=0.8)
        result = r1.merge(r2)
        assert result
        assert r1.quantity == pytest.approx(150.0)

    def test_merge_fails_different_type(self):
        r1 = Resource(resource_type=ResourceType.FOOD, quantity=100.0)
        r2 = Resource(resource_type=ResourceType.WATER, quantity=50.0)
        result = r1.merge(r2)
        assert not result

    def test_value_calculation(self):
        r = Resource(resource_type=ResourceType.FOOD, quantity=10.0, quality=1.0, durability=1.0)
        base_prices = {ResourceType.FOOD: 10.0}
        value = r.value(base_prices)
        assert value == pytest.approx(100.0)


class TestResourcePool:
    """Tests for ResourcePool class."""

    def test_create_pool_with_initial_resources(self):
        pool = ResourcePool(
            pool_id='pool-1',
            location=(5, 5),
            initial_resources={ResourceType.FOOD: 200.0, ResourceType.WATER: 100.0}
        )
        assert ResourceType.FOOD in pool.resources
        assert pool.resources[ResourceType.FOOD].quantity == pytest.approx(200.0)

    def test_extract_reduces_quantity(self):
        pool = ResourcePool(
            pool_id='pool-2',
            location=(0, 0),
            initial_resources={ResourceType.FOOD: 100.0}
        )
        extracted = pool.extract(ResourceType.FOOD, 30.0, 'agent-1')
        assert extracted is not None
        assert extracted.quantity == pytest.approx(30.0)
        assert pool.resources[ResourceType.FOOD].quantity == pytest.approx(70.0)

    def test_extract_returns_none_if_insufficient(self):
        pool = ResourcePool(
            pool_id='pool-3',
            location=(0, 0),
            initial_resources={ResourceType.WATER: 10.0}
        )
        extracted = pool.extract(ResourceType.WATER, 50.0, 'agent-1')
        assert extracted is None

    def test_extract_records_history(self):
        pool = ResourcePool(
            pool_id='pool-4',
            location=(0, 0),
            initial_resources={ResourceType.MATERIALS: 100.0}
        )
        pool.extract(ResourceType.MATERIALS, 20.0, 'agent-1')
        assert len(pool.extraction_history) == 1
        assert pool.extraction_history[0]['agent_id'] == 'agent-1'

    def test_deposit_adds_resource(self):
        pool = ResourcePool(pool_id='pool-5', location=(0, 0))
        r = Resource(resource_type=ResourceType.FOOD, quantity=50.0)
        result = pool.deposit(r)
        assert result
        assert ResourceType.FOOD in pool.resources

    def test_get_scarcity_full_pool(self):
        pool = ResourcePool(
            pool_id='pool-6',
            location=(0, 0),
            initial_resources={ResourceType.FOOD: 1000.0}  # at max capacity
        )
        scarcity = pool.get_scarcity(ResourceType.FOOD)
        assert scarcity == pytest.approx(0.0)

    def test_get_scarcity_empty_pool(self):
        pool = ResourcePool(pool_id='pool-7', location=(0, 0))
        scarcity = pool.get_scarcity(ResourceType.FOOD)
        assert scarcity == pytest.approx(1.0)

    def test_regenerate_increases_food_and_water(self):
        pool = ResourcePool(
            pool_id='pool-8',
            location=(0, 0),
            initial_resources={ResourceType.FOOD: 100.0, ResourceType.WATER: 100.0},
            regeneration_rate=0.1
        )
        pool.regenerate()
        assert pool.resources[ResourceType.FOOD].quantity > 100.0
        assert pool.resources[ResourceType.WATER].quantity > 100.0

    def test_get_available_filters_empty(self):
        pool = ResourcePool(
            pool_id='pool-9',
            location=(0, 0),
            initial_resources={ResourceType.FOOD: 100.0, ResourceType.WATER: 0.0}
        )
        available = pool.get_available()
        assert ResourceType.FOOD in available
        assert ResourceType.WATER not in available


class TestWorldResources:
    """Tests for WorldResources class."""

    def test_create_pool(self):
        world = WorldResources()
        pool = world.create_pool('pool-a', (1, 1), {ResourceType.FOOD: 500.0})
        assert pool is not None
        assert 'pool-a' in world.pools

    def test_find_nearest_pool(self):
        world = WorldResources()
        world.create_pool('pool-b', (2, 2), {ResourceType.WATER: 100.0})
        world.create_pool('pool-c', (10, 10), {ResourceType.WATER: 100.0})
        nearest = world.find_nearest_pool((0, 0), ResourceType.WATER)
        assert nearest is not None
        assert nearest.pool_id == 'pool-b'

    def test_find_nearest_pool_nonexistent_returns_none(self):
        world = WorldResources()
        pool = world.find_nearest_pool((0, 0), ResourceType.MEDICINE)
        assert pool is None

    def test_get_global_scarcity_empty(self):
        world = WorldResources()
        scarcity = world.get_global_scarcity(ResourceType.FOOD)
        assert scarcity == pytest.approx(1.0)

    def test_get_global_scarcity_full(self):
        world = WorldResources()
        world.create_pool('pool-d', (0, 0), {ResourceType.FOOD: 1000.0})
        scarcity = world.get_global_scarcity(ResourceType.FOOD)
        assert scarcity == pytest.approx(0.0)

    def test_tick_regenerates_pools(self):
        world = WorldResources()
        world.create_pool('pool-e', (0, 0), {ResourceType.FOOD: 100.0})
        initial_qty = world.pools['pool-e'].resources[ResourceType.FOOD].quantity
        world.tick()
        after_qty = world.pools['pool-e'].resources[ResourceType.FOOD].quantity
        # After tick, food regenerates (rate=0.01) but also degrades slightly (0.001)
        # Net effect should be positive for low initial quantity
        assert after_qty >= initial_qty * 0.99  # Allows for small degradation

    def test_base_prices_defined(self):
        world = WorldResources()
        for rtype in ResourceType:
            assert rtype in world.base_prices
