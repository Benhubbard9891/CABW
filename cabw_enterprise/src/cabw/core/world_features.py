"""Environment dynamics and world features for CABW simulations."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Callable, Dict, List, Optional, Tuple
import math


class TerrainType(Enum):
    """Basic terrain classifications."""

    OPEN = auto()
    FOREST = auto()
    URBAN = auto()
    WATER = auto()
    MOUNTAIN = auto()


class WeatherCondition(Enum):
    """Weather conditions that affect agent behavior."""

    CLEAR = auto()
    CLOUDY = auto()
    RAIN = auto()
    STORM = auto()
    FOG = auto()
    SNOW = auto()


@dataclass
class Position:
    """2-D position in the world grid."""

    x: float = 0.0
    y: float = 0.0

    def distance_to(self, other: "Position") -> float:
        return math.sqrt((self.x - other.x) ** 2 + (self.y - other.y) ** 2)

    def __add__(self, other: "Position") -> "Position":
        return Position(self.x + other.x, self.y + other.y)

    def __sub__(self, other: "Position") -> "Position":
        return Position(self.x - other.x, self.y - other.y)

    def as_tuple(self) -> Tuple[float, float]:
        return (self.x, self.y)


@dataclass
class WorldCell:
    """A single cell in the world grid."""

    position: Position
    terrain: TerrainType = TerrainType.OPEN
    passable: bool = True
    movement_cost: float = 1.0
    visibility: float = 1.0       # 0.0 (opaque) – 1.0 (fully visible)
    properties: Dict[str, Any] = field(default_factory=dict)

    def update_terrain(self, terrain: TerrainType) -> None:
        self.terrain = terrain
        # Apply default terrain costs
        defaults = {
            TerrainType.OPEN: (1.0, 1.0),
            TerrainType.FOREST: (2.0, 0.6),
            TerrainType.URBAN: (1.5, 0.7),
            TerrainType.WATER: (4.0, 0.5),
            TerrainType.MOUNTAIN: (3.0, 0.4),
        }
        cost, vis = defaults.get(terrain, (1.0, 1.0))
        self.movement_cost = cost
        self.visibility = vis
        self.passable = terrain != TerrainType.WATER


@dataclass
class WorldEnvironment:
    """Global environment state shared across the simulation."""

    width: int = 50
    height: int = 50
    weather: WeatherCondition = WeatherCondition.CLEAR
    time_of_day: float = 0.0       # 0.0 – 24.0 hours
    temperature: float = 20.0      # Celsius
    wind_speed: float = 0.0        # m/s
    wind_direction: float = 0.0    # degrees (0 = North)
    properties: Dict[str, Any] = field(default_factory=dict)

    def advance_time(self, hours: float) -> None:
        self.time_of_day = (self.time_of_day + hours) % 24.0

    def is_daytime(self) -> bool:
        return 6.0 <= self.time_of_day < 20.0

    def visibility_modifier(self) -> float:
        """Return a multiplier for agent visibility based on conditions."""
        modifiers = {
            WeatherCondition.CLEAR: 1.0,
            WeatherCondition.CLOUDY: 0.85,
            WeatherCondition.RAIN: 0.6,
            WeatherCondition.STORM: 0.3,
            WeatherCondition.FOG: 0.2,
            WeatherCondition.SNOW: 0.5,
        }
        base = modifiers.get(self.weather, 1.0)
        if not self.is_daytime():
            base *= 0.5
        return base


class WorldGrid:
    """Rectangular grid of WorldCell objects."""

    def __init__(self, width: int, height: int) -> None:
        self.width = width
        self.height = height
        self._cells: Dict[Tuple[int, int], WorldCell] = {}
        self._initialize_cells()

    def _initialize_cells(self) -> None:
        for x in range(self.width):
            for y in range(self.height):
                pos = Position(float(x), float(y))
                self._cells[(x, y)] = WorldCell(position=pos)

    def get_cell(self, x: int, y: int) -> Optional[WorldCell]:
        return self._cells.get((x, y))

    def set_terrain(self, x: int, y: int, terrain: TerrainType) -> None:
        cell = self.get_cell(x, y)
        if cell:
            cell.update_terrain(terrain)

    def neighbors(self, x: int, y: int, diagonal: bool = False) -> List[WorldCell]:
        """Return passable neighboring cells."""
        directions = [(0, 1), (1, 0), (0, -1), (-1, 0)]
        if diagonal:
            directions += [(1, 1), (1, -1), (-1, 1), (-1, -1)]
        result = []
        for dx, dy in directions:
            cell = self.get_cell(x + dx, y + dy)
            if cell and cell.passable:
                result.append(cell)
        return result

    def apply_to_region(
        self,
        x1: int,
        y1: int,
        x2: int,
        y2: int,
        fn: Callable[[WorldCell], None],
    ) -> None:
        """Apply *fn* to every cell within the inclusive bounding box."""
        for x in range(min(x1, x2), max(x1, x2) + 1):
            for y in range(min(y1, y2), max(y1, y2) + 1):
                cell = self.get_cell(x, y)
                if cell:
                    fn(cell)


@dataclass
class WorldEvent:
    """A discrete event that occurs in the world."""

    event_type: str
    position: Optional[Position] = None
    radius: float = 0.0
    payload: Dict[str, Any] = field(default_factory=dict)
    tick: int = 0

    def affects_position(self, pos: Position) -> bool:
        if self.position is None:
            return True  # Global event
        return self.position.distance_to(pos) <= self.radius


class WorldEventBus:
    """Simple publish/subscribe event bus for world events."""

    def __init__(self) -> None:
        self._listeners: Dict[str, List[Callable[[WorldEvent], None]]] = {}
        self._history: List[WorldEvent] = []

    def subscribe(self, event_type: str, callback: Callable[[WorldEvent], None]) -> None:
        self._listeners.setdefault(event_type, []).append(callback)

    def publish(self, event: WorldEvent) -> None:
        self._history.append(event)
        for callback in self._listeners.get(event.event_type, []):
            callback(event)
        for callback in self._listeners.get("*", []):
            callback(event)

    def recent_events(self, n: int = 10) -> List[WorldEvent]:
        return self._history[-n:]
