"""
Test suite for CABW Enterprise World Generation Module

Covers:
- PerlinNoise
- TerrainGenerator
- Biome
"""
import pytest
from cabw.worldgen.terrain import PerlinNoise, TerrainGenerator, TerrainType, Biome


class TestPerlinNoise:
    """Tests for PerlinNoise class."""

    def test_creates_with_seed(self):
        noise = PerlinNoise(seed=42)
        assert noise.seed == 42

    def test_creates_without_seed(self):
        noise = PerlinNoise()
        assert noise.seed is not None
        assert isinstance(noise.seed, int)

    def test_noise_returns_float(self):
        noise = PerlinNoise(seed=1)
        value = noise.noise(0.5, 0.5)
        assert isinstance(value, float)

    def test_noise_is_deterministic_with_same_seed(self):
        n1 = PerlinNoise(seed=99)
        n2 = PerlinNoise(seed=99)
        assert n1.noise(0.3, 0.7) == pytest.approx(n2.noise(0.3, 0.7))

    def test_noise_differs_with_different_seeds(self):
        n1 = PerlinNoise(seed=1)
        n2 = PerlinNoise(seed=2)
        # High chance values are different at the same coordinates
        assert n1.noise(0.5, 0.5) != n2.noise(0.5, 0.5)

    def test_octave_noise_returns_float(self):
        noise = PerlinNoise(seed=7)
        value = noise.octave_noise(0.5, 0.5)
        assert isinstance(value, float)


class TestTerrainGenerator:
    """Tests for TerrainGenerator class."""

    def test_creates_with_seed(self):
        gen = TerrainGenerator(seed=42)
        assert gen.seed == 42

    def test_generate_terrain_returns_correct_size(self):
        gen = TerrainGenerator(seed=10)
        grid = gen.generate_terrain(width=5, height=5)
        assert len(grid) == 5
        assert all(len(row) == 5 for row in grid)

    def test_generate_terrain_returns_terrain_types(self):
        gen = TerrainGenerator(seed=10)
        grid = gen.generate_terrain(width=5, height=5)
        for row in grid:
            for cell in row:
                assert isinstance(cell, TerrainType)

    def test_generate_larger_grid(self):
        gen = TerrainGenerator(seed=20)
        grid = gen.generate_terrain(width=20, height=20)
        assert len(grid) == 20
        assert len(grid[0]) == 20

    def test_same_seed_produces_same_terrain(self):
        gen1 = TerrainGenerator(seed=55)
        gen2 = TerrainGenerator(seed=55)
        grid1 = gen1.generate_terrain(5, 5)
        grid2 = gen2.generate_terrain(5, 5)
        for r in range(5):
            for c in range(5):
                assert grid1[r][c] == grid2[r][c]

    def test_different_seeds_produce_different_terrain(self):
        gen1 = TerrainGenerator(seed=1)
        gen2 = TerrainGenerator(seed=2)
        grid1 = gen1.generate_terrain(10, 10)
        grid2 = gen2.generate_terrain(10, 10)
        # Expect at least one different cell in a 10x10 grid
        differences = sum(
            1 for r in range(10) for c in range(10)
            if grid1[r][c] != grid2[r][c]
        )
        assert differences > 0

    def test_terrain_types_are_valid(self):
        gen = TerrainGenerator(seed=77)
        grid = gen.generate_terrain(10, 10)
        valid_types = set(TerrainType)
        for row in grid:
            for cell in row:
                assert cell in valid_types

