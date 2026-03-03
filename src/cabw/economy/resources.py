"""
Resource System for Economic Simulation

Defines resource types, quantities, and pools with scarcity mechanics.
"""

from dataclasses import dataclass
from enum import Enum, auto
from typing import Optional


class ResourceType(Enum):
    """Types of resources in the economy."""
    FOOD = auto()
    WATER = auto()
    MEDICINE = auto()
    FUEL = auto()
    MATERIALS = auto()
    TOOLS = auto()
    INFORMATION = auto()
    CURRENCY = auto()


@dataclass
class Resource:
    """Instance of a resource."""
    resource_type: ResourceType
    quantity: float
    quality: float = 1.0  # 0.0 to 1.0
    durability: float = 1.0  # Degrades over time
    owner_id: str | None = None
    location: tuple | None = None

    def __post_init__(self):
        if self.quantity < 0:
            self.quantity = 0

    def degrade(self, amount: float = 0.01):
        """Degrade resource quality over time."""
        self.durability -= amount
        if self.durability <= 0:
            self.quantity = 0

    def split(self, amount: float) -> Optional['Resource']:
        """Split off a portion of this resource."""
        if amount > self.quantity:
            return None

        self.quantity -= amount
        return Resource(
            resource_type=self.resource_type,
            quantity=amount,
            quality=self.quality,
            durability=self.durability,
            owner_id=self.owner_id,
            location=self.location
        )

    def merge(self, other: 'Resource') -> bool:
        """Merge another resource into this one."""
        if other.resource_type != self.resource_type:
            return False

        # Weighted average of quality
        total = self.quantity + other.quantity
        self.quality = (self.quantity * self.quality + other.quantity * other.quality) / total
        self.quantity = total
        return True

    def value(self, base_prices: dict[ResourceType, float]) -> float:
        """Calculate resource value."""
        base = base_prices.get(self.resource_type, 1.0)
        return self.quantity * base * self.quality * self.durability


class ResourcePool:
    """
    Pool of resources with scarcity mechanics.
    """

    def __init__(
        self,
        pool_id: str,
        location: tuple,
        initial_resources: dict[ResourceType, float] | None = None,
        regeneration_rate: float = 0.01
    ):
        self.pool_id = pool_id
        self.location = location
        self.resources: dict[ResourceType, Resource] = {}
        self.regeneration_rate = regeneration_rate

        # Initialize resources
        if initial_resources:
            for rtype, quantity in initial_resources.items():
                self.resources[rtype] = Resource(
                    resource_type=rtype,
                    quantity=quantity,
                    location=location
                )

        # Extraction history
        self.extraction_history: list[dict] = []

    def extract(
        self,
        resource_type: ResourceType,
        amount: float,
        agent_id: str
    ) -> Resource | None:
        """
        Extract resource from pool.
        Returns extracted resource or None if insufficient.
        """
        resource = self.resources.get(resource_type)
        if not resource or resource.quantity < amount:
            return None

        extracted = resource.split(amount)
        if extracted:
            extracted.owner_id = agent_id

            self.extraction_history.append({
                'agent_id': agent_id,
                'resource_type': resource_type.name,
                'amount': amount,
                'remaining': resource.quantity
            })

        return extracted

    def deposit(self, resource: Resource) -> bool:
        """Deposit resource into pool."""
        if resource.resource_type not in self.resources:
            self.resources[resource.resource_type] = Resource(
                resource_type=resource.resource_type,
                quantity=0,
                location=self.location
            )

        return self.resources[resource.resource_type].merge(resource)

    def get_scarcity(self, resource_type: ResourceType) -> float:
        """
        Get scarcity level (0.0 = abundant, 1.0 = scarce).
        """
        resource = self.resources.get(resource_type)
        if not resource:
            return 1.0  # Completely scarce (none exists)

        # Define capacity thresholds
        max_capacity = 1000.0  # Arbitrary max
        current = resource.quantity

        scarcity = 1.0 - (current / max_capacity)
        return max(0.0, min(1.0, scarcity))

    def regenerate(self):
        """Regenerate renewable resources."""
        for resource in self.resources.values():
            if resource.resource_type in [ResourceType.FOOD, ResourceType.WATER]:
                resource.quantity += resource.quantity * self.regeneration_rate
                resource.quantity = min(resource.quantity, 1000.0)  # Cap

    def get_available(self) -> dict[ResourceType, float]:
        """Get available quantities."""
        return {
            rtype: res.quantity
            for rtype, res in self.resources.items()
            if res.quantity > 0
        }


class WorldResources:
    """
    Global resource manager for the world.
    """

    def __init__(self):
        self.pools: dict[str, ResourcePool] = {}
        self.base_prices: dict[ResourceType, float] = {
            ResourceType.FOOD: 10.0,
            ResourceType.WATER: 5.0,
            ResourceType.MEDICINE: 50.0,
            ResourceType.FUEL: 20.0,
            ResourceType.MATERIALS: 15.0,
            ResourceType.TOOLS: 30.0,
            ResourceType.INFORMATION: 100.0,
            ResourceType.CURRENCY: 1.0
        }

    def create_pool(
        self,
        pool_id: str,
        location: tuple,
        resources: dict[ResourceType, float]
    ) -> ResourcePool:
        """Create a new resource pool."""
        pool = ResourcePool(
            pool_id=pool_id,
            location=location,
            initial_resources=resources
        )
        self.pools[pool_id] = pool
        return pool

    def find_nearest_pool(
        self,
        location: tuple,
        resource_type: ResourceType
    ) -> ResourcePool | None:
        """Find nearest pool with available resource."""
        available = [
            pool for pool in self.pools.values()
            if pool.resources.get(resource_type, Resource(resource_type, 0)).quantity > 0
        ]

        if not available:
            return None

        # Find nearest
        nearest = min(available, key=lambda p:
            ((p.location[0] - location[0]) ** 2 +
             (p.location[1] - location[1]) ** 2) ** 0.5
        )

        return nearest

    def get_global_scarcity(self, resource_type: ResourceType) -> float:
        """Get global scarcity for resource type."""
        total = sum(
            pool.resources.get(resource_type, Resource(resource_type, 0)).quantity
            for pool in self.pools.values()
        )

        max_capacity = len(self.pools) * 1000.0
        return 1.0 - (total / max_capacity) if max_capacity > 0 else 1.0

    def tick(self):
        """Update all pools."""
        for pool in self.pools.values():
            pool.regenerate()
            for resource in pool.resources.values():
                resource.degrade(0.001)  # Slow degradation
