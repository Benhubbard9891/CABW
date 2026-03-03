"""
Test suite for CABW Enterprise Simulation System
"""
import pytest

from cabw.simulation.engine import EnhancedSimulation, SimulationConfig


class TestSimulationCreation:
    """Test simulation initialization and configuration."""

    def test_create_simulation_with_defaults(self):
        """Test creating a simulation with default configuration."""
        config = SimulationConfig()
        simulation = EnhancedSimulation(config)

        assert simulation is not None
        assert simulation.config.world_size == (20, 20)
        assert simulation.tick_count == 0
        assert not simulation.running

    def test_create_simulation_with_custom_config(self):
        """Test creating a simulation with custom configuration."""
        config = SimulationConfig(
            world_size=(10, 10),
            num_agents=5,
            tick_rate=2.0,
            max_ticks=500
        )
        simulation = EnhancedSimulation(config)

        assert simulation.config.world_size == (10, 10)
        assert simulation.config.num_agents == 5
        assert simulation.config.tick_rate == 2.0
        assert simulation.config.max_ticks == 500

    def test_simulation_systems_initialized(self):
        """Test that all simulation systems are properly initialized."""
        simulation = EnhancedSimulation()

        assert simulation.environment is not None
        assert simulation.effect_system is not None
        assert simulation.security_governor is not None
        assert simulation.team_manager is not None
        assert simulation.emotional_climate is not None
        assert len(simulation.agents) == 0


class TestSimulationAgents:
    """Test agent creation and management in simulation."""

    def test_initialize_creates_agents(self):
        """Test that initialize() creates the configured number of agents."""
        config = SimulationConfig(num_agents=5)
        simulation = EnhancedSimulation(config)
        simulation.initialize()

        assert len(simulation.agents) == 5

    def test_agents_have_unique_ids(self):
        """Test that all agents have unique IDs."""
        config = SimulationConfig(num_agents=10)
        simulation = EnhancedSimulation(config)
        simulation.initialize()

        agent_ids = [agent.agent_id for agent in simulation.agents.values()]
        assert len(agent_ids) == len(set(agent_ids))

    def test_agents_have_valid_properties(self):
        """Test that agents are properly initialized with required properties."""
        config = SimulationConfig(num_agents=3)
        simulation = EnhancedSimulation(config)
        simulation.initialize()

        for agent in simulation.agents.values():
            assert agent.agent_id is not None
            assert agent.name is not None
            assert agent.emotional_state is not None
            assert agent.ocean_traits is not None
            assert 0.0 <= agent.ocean_traits['openness'] <= 1.0
            assert agent.needs is not None
            assert agent.memory is not None


class TestSimulationExecution:
    """Test simulation execution and tick mechanics."""

    @pytest.mark.asyncio
    async def test_run_single_tick(self):
        """Test running a single simulation tick."""
        config = SimulationConfig(num_agents=3)
        simulation = EnhancedSimulation(config)
        simulation.initialize()

        initial_tick = simulation.tick_count
        await simulation.tick()

        assert simulation.tick_count == initial_tick + 1

    @pytest.mark.asyncio
    async def test_run_multiple_ticks(self):
        """Test running multiple simulation ticks."""
        config = SimulationConfig(num_agents=5, max_ticks=10)
        simulation = EnhancedSimulation(config)
        simulation.initialize()

        for _i in range(5):
            await simulation.tick()

        assert simulation.tick_count == 5

    @pytest.mark.asyncio
    async def test_simulation_state_tracking(self):
        """Test that simulation tracks state changes."""
        config = SimulationConfig(num_agents=3)
        simulation = EnhancedSimulation(config)
        simulation.initialize()

        initial_state_count = len(simulation.state_history)
        await simulation.tick()

        # State should be tracked
        assert len(simulation.state_history) >= initial_state_count


class TestSimulationEnvironment:
    """Test environment system in simulation."""

    def test_environment_initialized(self):
        """Test that environment is properly initialized."""
        config = SimulationConfig(world_size=(15, 15))
        simulation = EnhancedSimulation(config)

        assert simulation.environment.world_size == (15, 15)

    def test_weather_system_enabled(self):
        """Test that weather system is enabled when configured."""
        config = SimulationConfig(weather_enabled=True)
        simulation = EnhancedSimulation(config)
        simulation.initialize()

        assert simulation.environment.weather is not None

    def test_environment_effects(self):
        """Test that environment effect system is functional."""
        simulation = EnhancedSimulation()
        simulation.initialize()

        assert simulation.effect_system is not None


class TestSimulationStatistics:
    """Test simulation statistics tracking."""

    def test_statistics_initialized(self):
        """Test that statistics are properly initialized."""
        simulation = EnhancedSimulation()

        assert 'total_actions' in simulation.statistics
        assert 'team_formations' in simulation.statistics
        assert 'goals_completed' in simulation.statistics
        assert 'hazards_resolved' in simulation.statistics
        assert 'security_violations' in simulation.statistics
        assert 'emotional_contagion_events' in simulation.statistics

    def test_statistics_start_at_zero(self):
        """Test that all statistics start at zero."""
        simulation = EnhancedSimulation()

        for key, value in simulation.statistics.items():
            assert value == 0, f"Statistic {key} should start at 0"


class TestSimulationIntegration:
    """Integration tests for full simulation scenarios."""

    @pytest.mark.asyncio
    async def test_full_simulation_run(self):
        """Test a complete simulation run from creation to completion."""
        config = SimulationConfig(
            num_agents=5,
            max_ticks=10,
            tick_rate=1.0
        )
        simulation = EnhancedSimulation(config)
        simulation.initialize()

        # Run simulation for specified ticks
        for _ in range(10):
            await simulation.tick()

        assert simulation.tick_count == 10
        assert len(simulation.agents) == 5

    @pytest.mark.asyncio
    async def test_simulation_with_all_features(self):
        """Test simulation with all features enabled."""
        config = SimulationConfig(
            num_agents=10,
            weather_enabled=True,
            hazards_enabled=True,
            teamwork_enabled=True,
            security_level='standard'
        )
        simulation = EnhancedSimulation(config)
        simulation.initialize()

        # Run a few ticks
        for _ in range(5):
            await simulation.tick()

        assert simulation.tick_count == 5
        assert len(simulation.agents) == 10
        assert simulation.team_manager is not None
        assert simulation.security_governor is not None
