"""
Procedural Terrain Generation

Uses Perlin noise and cellular automata to generate realistic terrain.
"""

import random
import math
from typing import Dict, List, Optional, Tuple, Set
from dataclasses import dataclass
from enum import Enum, auto


class TerrainType(Enum):
    """Types of terrain."""
    DEEP_WATER = auto()
    SHALLOW_WATER = auto()
    BEACH = auto()
    PLAINS = auto()
    FOREST = auto()
    HILLS = auto()
    MOUNTAINS = auto()
    SNOW = auto()
    DESERT = auto()
    SWAMP = auto()


@dataclass
class Biome:
    """Biome definition."""
    name: str
    terrain_types: List[TerrainType]
    resource_abundance: Dict[str, float]
    hazard_chance: float
    movement_cost: float


class PerlinNoise:
    """
    Simple Perlin noise implementation for terrain generation.
    """
    
    def __init__(self, seed: Optional[int] = None):
        self.seed = seed or random.randint(0, 10000)
        self.permutation = list(range(256))
        random.seed(self.seed)
        random.shuffle(self.permutation)
        self.permutation = self.permutation * 2
    
    def _fade(self, t: float) -> float:
        """Fade function."""
        return t * t * t * (t * (t * 6 - 15) + 10)
    
    def _lerp(self, t: float, a: float, b: float) -> float:
        """Linear interpolation."""
        return a + t * (b - a)
    
    def _grad(self, hash: int, x: float, y: float) -> float:
        """Gradient function."""
        h = hash & 15
        u = x if h < 8 else y
        v = y if h < 4 else (x if h == 12 or h == 14 else 0)
        return (u if (h & 1) == 0 else -u) + (v if (h & 2) == 0 else -v)
    
    def noise(self, x: float, y: float) -> float:
        """Generate Perlin noise at (x, y)."""
        X = int(math.floor(x)) & 255
        Y = int(math.floor(y)) & 255
        
        x -= math.floor(x)
        y -= math.floor(y)
        
        u = self._fade(x)
        v = self._fade(y)
        
        A = self.permutation[X] + Y
        B = self.permutation[X + 1] + Y
        
        return self._lerp(v,
            self._lerp(u,
                self._grad(self.permutation[A], x, y),
                self._grad(self.permutation[B], x - 1, y)
            ),
            self._lerp(u,
                self._grad(self.permutation[A + 1], x, y - 1),
                self._grad(self.permutation[B + 1], x - 1, y - 1)
            )
        )
    
    def octave_noise(
        self,
        x: float,
        y: float,
        octaves: int = 4,
        persistence: float = 0.5
    ) -> float:
        """Generate octave noise."""
        total = 0.0
        frequency = 1.0
        amplitude = 1.0
        max_value = 0.0
        
        for _ in range(octaves):
            total += self.noise(x * frequency, y * frequency) * amplitude
            max_value += amplitude
            amplitude *= persistence
            frequency *= 2
        
        return total / max_value


class TerrainGenerator:
    """
    Procedural terrain generator using Perlin noise.
    """
    
    # Terrain type thresholds (elevation 0-1)
    ELEVATION_THRESHOLDS = [
        (0.0, TerrainType.DEEP_WATER),
        (0.3, TerrainType.SHALLOW_WATER),
        (0.35, TerrainType.BEACH),
        (0.5, TerrainType.PLAINS),
        (0.6, TerrainType.FOREST),
        (0.7, TerrainType.HILLS),
        (0.85, TerrainType.MOUNTAINS),
        (1.0, TerrainType.SNOW)
    ]
    
    # Biome definitions
    BIOMES = {
        'temperate': Biome(
            name='Temperate',
            terrain_types=[TerrainType.PLAINS, TerrainType.FOREST, TerrainType.HILLS],
            resource_abundance={'food': 0.8, 'wood': 0.9, 'stone': 0.5},
            hazard_chance=0.1,
            movement_cost=1.0
        ),
        'desert': Biome(
            name='Desert',
            terrain_types=[TerrainType.DESERT],
            resource_abundance={'food': 0.2, 'water': 0.1, 'minerals': 0.7},
            hazard_chance=0.3,
            movement_cost=1.5
        ),
        'arctic': Biome(
            name='Arctic',
            terrain_types=[TerrainType.SNOW, TerrainType.MOUNTAINS],
            resource_abundance={'food': 0.3, 'fur': 0.8, 'minerals': 0.6},
            hazard_chance=0.4,
            movement_cost=2.0
        ),
        'coastal': Biome(
            name='Coastal',
            terrain_types=[TerrainType.BEACH, TerrainType.SHALLOW_WATER],
            resource_abundance={'food': 0.9, 'water': 1.0, 'fish': 0.9},
            hazard_chance=0.2,
            movement_cost=0.8
        )
    }
    
    def __init__(self, seed: Optional[int] = None):
        self.seed = seed or random.randint(0, 100000)
        self.elevation_noise = PerlinNoise(self.seed)
        self.moisture_noise = PerlinNoise(self.seed + 1)
        self.temperature_noise = PerlinNoise(self.seed + 2)
    
    def generate_terrain(
        self,
        width: int,
        height: int,
        scale: float = 0.05
    ) -> List[List[TerrainType]]:
        """
        Generate terrain map.
        
        Returns 2D grid of TerrainType.
        """
        terrain = []
        
        for y in range(height):
            row = []
            for x in range(width):
                # Sample noise
                nx = x * scale
                ny = y * scale
                
                elevation = self.elevation_noise.octave_noise(nx, ny, octaves=6)
                # Normalize to 0-1
                elevation = (elevation + 1) / 2
                
                # Determine terrain type
                terrain_type = self._elevation_to_terrain(elevation)
                row.append(terrain_type)
            
            terrain.append(row)
        
        # Apply cellular automata smoothing
        terrain = self._smooth_terrain(terrain, iterations=2)
        
        return terrain
    
    def _elevation_to_terrain(self, elevation: float) -> TerrainType:
        """Convert elevation to terrain type."""
        for threshold, terrain_type in self.ELEVATION_THRESHOLDS:
            if elevation <= threshold:
                return terrain_type
        return TerrainType.SNOW
    
    def _smooth_terrain(
        self,
        terrain: List[List[TerrainType]],
        iterations: int = 1
    ) -> List[List[TerrainType]]:
        """Smooth terrain using cellular automata."""
        height = len(terrain)
        width = len(terrain[0]) if terrain else 0
        
        for _ in range(iterations):
            new_terrain = [row[:] for row in terrain]
            
            for y in range(height):
                for x in range(width):
                    # Count neighbors of each type
                    neighbor_counts: Dict[TerrainType, int] = {}
                    
                    for dy in [-1, 0, 1]:
                        for dx in [-1, 0, 1]:
                            if dx == 0 and dy == 0:
                                continue
                            
                            nx, ny = x + dx, y + dy
                            if 0 <= nx < width and 0 <= ny < height:
                                neighbor = terrain[ny][nx]
                                neighbor_counts[neighbor] = neighbor_counts.get(neighbor, 0) + 1
                    
                    # If current cell is different from majority of neighbors, change it
                    if neighbor_counts:
                        majority = max(neighbor_counts, key=neighbor_counts.get)
                        if neighbor_counts[majority] >= 5:
                            new_terrain[y][x] = majority
            
            terrain = new_terrain
        
        return terrain
    
    def generate_biome_map(
        self,
        width: int,
        height: int,
        scale: float = 0.03
    ) -> List[List[str]]:
        """Generate biome map."""
        biome_map = []
        
        for y in range(height):
            row = []
            for x in range(width):
                nx = x * scale
                ny = y * scale
                
                temperature = self.temperature_noise.octave_noise(nx, ny)
                moisture = self.moisture_noise.octave_noise(nx + 100, ny + 100)
                
                # Determine biome from temperature and moisture
                biome = self._temperature_moisture_to_biome(temperature, moisture)
                row.append(biome)
            
            biome_map.append(row)
        
        return biome_map
    
    def _temperature_moisture_to_biome(
        self,
        temperature: float,
        moisture: float
    ) -> str:
        """Convert temperature and moisture to biome."""
        # Normalize
        temp = (temperature + 1) / 2  # 0 to 1
        moist = (moisture + 1) / 2
        
        if temp < 0.2:
            return 'arctic'
        elif temp > 0.8:
            return 'desert' if moist < 0.3 else 'temperate'
        elif moist > 0.7:
            return 'coastal'
        else:
            return 'temperate'
    
    def find_spawn_locations(
        self,
        terrain: List[List[TerrainType]],
        count: int,
        preferred: List[TerrainType] = None
    ) -> List[Tuple[int, int]]:
        """Find suitable spawn locations."""
        preferred = preferred or [TerrainType.PLAINS, TerrainType.FOREST]
        
        candidates = []
        height = len(terrain)
        width = len(terrain[0]) if terrain else 0
        
        for y in range(height):
            for x in range(width):
                if terrain[y][x] in preferred:
                    candidates.append((x, y))
        
        # Select random locations
        if len(candidates) >= count:
            return random.sample(candidates, count)
        else:
            return candidates
    
    def export_heightmap(
        self,
        width: int,
        height: int,
        scale: float = 0.05
    ) -> List[List[float]]:
        """Export raw heightmap for external use."""
        heightmap = []
        
        for y in range(height):
            row = []
            for x in range(width):
                nx = x * scale
                ny = y * scale
                elevation = self.elevation_noise.octave_noise(nx, ny, octaves=6)
                row.append((elevation + 1) / 2)  # Normalize to 0-1
            heightmap.append(row)
        
        return heightmap
