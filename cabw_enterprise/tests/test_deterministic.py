"""
Test suite for CABW Enterprise Deterministic Simulation Module

Covers:
- SimulationEvent
- SimulationSeed
- SeededRandom
- EventQueue
- DeterministicSimulation
"""
import pytest

from cabw.simulation.deterministic import (
    DeterministicSimulation,
    EventQueue,
    EventType,
    SeededRandom,
    SimulationEvent,
)


class TestSimulationEvent:
    """Tests for SimulationEvent frozen dataclass."""

    def test_create_event(self):
        event = SimulationEvent(
            event_id='evt-1',
            tick=0,
            event_type=EventType.AGENT_ACTION,
            source_id='agent-1',
            payload={'action': 'move'}
        )
        assert event.event_id == 'evt-1'
        assert event.tick == 0
        assert event.event_type == EventType.AGENT_ACTION

    def test_event_is_immutable(self):
        event = SimulationEvent(
            event_id='evt-1',
            tick=0,
            event_type=EventType.WORLD_TICK,
            source_id='world'
        )
        with pytest.raises((AttributeError, TypeError)):
            event.tick = 99  # type: ignore

    def test_hash_returns_string(self):
        event = SimulationEvent(
            event_id='evt-2',
            tick=1,
            event_type=EventType.AGENT_MOVE,
            source_id='agent-2'
        )
        h = event.hash()
        assert isinstance(h, str)
        assert len(h) == 16

    def test_hash_is_deterministic(self):
        event = SimulationEvent(
            event_id='evt-3',
            tick=2,
            event_type=EventType.TEAM_FORM,
            source_id='team-1'
        )
        assert event.hash() == event.hash()

    def test_to_dict_contains_required_fields(self):
        event = SimulationEvent(
            event_id='evt-4',
            tick=3,
            event_type=EventType.WEATHER_CHANGE,
            source_id='env'
        )
        d = event.to_dict()
        assert 'event_id' in d
        assert 'tick' in d
        assert 'event_type' in d
        assert 'source_id' in d
        assert 'hash' in d


class TestSeededRandom:
    """Tests for SeededRandom class."""

    def test_random_returns_float(self):
        rng = SeededRandom(42)
        value = rng.random()
        assert isinstance(value, float)
        assert 0.0 <= value <= 1.0

    def test_randint_in_range(self):
        rng = SeededRandom(42)
        value = rng.randint(1, 10)
        assert 1 <= value <= 10

    def test_uniform_in_range(self):
        rng = SeededRandom(42)
        value = rng.uniform(0.5, 1.5)
        assert 0.5 <= value <= 1.5

    def test_choice_returns_element(self):
        rng = SeededRandom(42)
        seq = ['a', 'b', 'c']
        value = rng.choice(seq)
        assert value in seq

    def test_same_seed_produces_same_sequence(self):
        rng1 = SeededRandom(99)
        rng2 = SeededRandom(99)
        seq1 = [rng1.random() for _ in range(10)]
        seq2 = [rng2.random() for _ in range(10)]
        assert seq1 == seq2

    def test_different_seeds_produce_different_sequences(self):
        rng1 = SeededRandom(1)
        rng2 = SeededRandom(2)
        seq1 = [rng1.random() for _ in range(10)]
        seq2 = [rng2.random() for _ in range(10)]
        assert seq1 != seq2

    def test_get_state_returns_string(self):
        rng = SeededRandom(42)
        state = rng.get_state()
        assert isinstance(state, str)

    def test_call_count_increments(self):
        rng = SeededRandom(42)
        for _ in range(5):
            rng.random()
        assert rng._call_count == 5


class TestEventQueue:
    """Tests for EventQueue class."""

    def test_emit_adds_to_queue(self):
        rng = SeededRandom(42)
        queue = EventQueue(rng)
        queue.emit(EventType.WORLD_TICK, 'world', {'tick': 0})
        assert len(queue._queue) == 1

    def test_process_tick_clears_queue(self):
        rng = SeededRandom(42)
        queue = EventQueue(rng)
        queue.emit(EventType.WORLD_TICK, 'world', {})
        queue.emit(EventType.AGENT_ACTION, 'agent-1', {'action': 'move'})
        processed = queue.process_tick()
        assert len(queue._queue) == 0
        assert len(processed) == 2

    def test_process_tick_increments_tick(self):
        rng = SeededRandom(42)
        queue = EventQueue(rng)
        assert queue._tick == 0
        queue.process_tick()
        assert queue._tick == 1

    def test_get_history_returns_processed_events(self):
        rng = SeededRandom(42)
        queue = EventQueue(rng)
        queue.emit(EventType.WORLD_TICK, 'world', {})
        queue.process_tick()
        history = queue.get_history()
        assert len(history) == 1

    def test_get_history_filtered_by_tick(self):
        rng = SeededRandom(42)
        queue = EventQueue(rng)
        queue.emit(EventType.WORLD_TICK, 'world', {})
        queue.process_tick()
        queue.emit(EventType.AGENT_ACTION, 'agent-1', {})
        queue.process_tick()
        tick0_events = queue.get_history(tick=0)
        assert len(tick0_events) == 1

    def test_register_and_call_handler(self):
        rng = SeededRandom(42)
        queue = EventQueue(rng)
        called = []

        def handler(event):
            called.append(event)

        queue.register_handler(EventType.WORLD_TICK, handler)
        queue.emit(EventType.WORLD_TICK, 'world', {})
        queue.process_tick()
        assert len(called) == 1

    def test_get_agent_events(self):
        rng = SeededRandom(42)
        queue = EventQueue(rng)
        queue.emit(EventType.AGENT_ACTION, 'agent-a', {'action': 'move'})
        queue.emit(EventType.AGENT_ACTION, 'agent-b', {'action': 'rest'})
        queue.process_tick()
        agent_events = queue.get_agent_events('agent-a')
        assert len(agent_events) == 1
        assert agent_events[0].source_id == 'agent-a'


class TestDeterministicSimulation:
    """Tests for DeterministicSimulation class."""

    def test_create_deterministic_simulation(self):
        config = {'world_size': (10, 10), 'num_agents': 3}
        sim = DeterministicSimulation(seed=42, config=config, agents={})
        assert sim is not None

    def test_seed_stored(self):
        config = {'test': True}
        sim = DeterministicSimulation(seed=123, config=config, agents={})
        assert sim.seed.rng_seed == 123

    def test_config_hash_matches(self):
        config = {'world_size': (10, 10)}
        sim = DeterministicSimulation(seed=42, config=config, agents={})
        assert sim.seed.verify_config(config)

    def test_config_hash_fails_different_config(self):
        config = {'world_size': (10, 10)}
        sim = DeterministicSimulation(seed=42, config=config, agents={})
        different_config = {'world_size': (20, 20)}
        assert not sim.seed.verify_config(different_config)

    def test_same_seed_same_rng_sequence(self):
        config = {'x': 1}
        sim1 = DeterministicSimulation(seed=77, config=config, agents={})
        sim2 = DeterministicSimulation(seed=77, config=config, agents={})
        seq1 = [sim1.rng.random() for _ in range(5)]
        seq2 = [sim2.rng.random() for _ in range(5)]
        assert seq1 == seq2

    def test_emit_and_process_event(self):
        config = {}
        sim = DeterministicSimulation(seed=42, config=config, agents={})
        sim.event_queue.emit(EventType.WORLD_TICK, 'world', {'tick': 0})
        processed = sim.event_queue.process_tick()
        assert len(processed) == 1
