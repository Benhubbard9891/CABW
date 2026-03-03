"""
Deterministic Simulation Engine

Event-queue architecture for:
- Deterministic replay
- Race condition elimination
- Full auditability
"""

import hashlib
import json
import random
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto
from typing import Any


class EventType(Enum):
    """Types of simulation events."""

    AGENT_ACTION = auto()
    AGENT_MOVE = auto()
    AGENT_EMOTION = auto()
    AGENT_NEED = auto()
    TEAM_FORM = auto()
    TEAM_GOAL = auto()
    TEAM_UPDATE = auto()
    WEATHER_CHANGE = auto()
    HAZARD_SPAWN = auto()
    HAZARD_UPDATE = auto()
    HAZARD_CONTAIN = auto()
    ENV_EVENT = auto()
    EMOTION_CONTAGION = auto()
    WORLD_TICK = auto()


@dataclass(frozen=True)
class SimulationEvent:
    """
    Immutable simulation event.
    All state changes happen through events.
    """

    event_id: str
    tick: int
    event_type: EventType
    source_id: str  # Agent, system, or environment ID
    payload: dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    rng_state: str | None = None  # For replay verification

    def hash(self) -> str:
        """Generate event hash for integrity."""
        data = f"{self.event_id}:{self.tick}:{self.event_type.name}:{self.source_id}"
        return hashlib.sha256(data.encode()).hexdigest()[:16]

    def to_dict(self) -> dict:
        return {
            "event_id": self.event_id,
            "tick": self.tick,
            "event_type": self.event_type.name,
            "source_id": self.source_id,
            "payload": self.payload,
            "timestamp": self.timestamp,
            "rng_state": self.rng_state,
            "hash": self.hash(),
        }


@dataclass
class SimulationSeed:
    """Seed for reproducible simulation."""

    rng_seed: int
    config_hash: str
    agent_init_states: list[dict[str, Any]]
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def verify_config(self, current_config: dict) -> bool:
        """Verify current config matches seed."""
        current_hash = hashlib.sha256(
            json.dumps(current_config, sort_keys=True).encode()
        ).hexdigest()[:32]
        return current_hash == self.config_hash


class SeededRandom:
    """Seeded random number generator with state tracking."""

    def __init__(self, seed: int):
        self._seed = seed
        self._rng = random.Random(seed)
        self._call_count = 0
        self._state_history: dict[int, str] = {}

    def random(self) -> float:
        """Get random value and track state."""
        value = self._rng.random()
        self._call_count += 1
        self._state_history[self._call_count] = self.get_state()
        return value

    def randint(self, a: int, b: int) -> int:
        """Get random integer."""
        value = self._rng.randint(a, b)
        self._call_count += 1
        self._state_history[self._call_count] = self.get_state()
        return value

    def choice(self, seq):
        """Get random choice."""
        value = self._rng.choice(seq)
        self._call_count += 1
        self._state_history[self._call_count] = self.get_state()
        return value

    def uniform(self, a: float, b: float) -> float:
        """Get uniform random."""
        value = self._rng.uniform(a, b)
        self._call_count += 1
        self._state_history[self._call_count] = self.get_state()
        return value

    def get_state(self) -> str:
        """Get current state as string."""
        state = self._rng.getstate()
        return hashlib.sha256(str(state).encode()).hexdigest()[:16]

    def get_state_at(self, call_number: int) -> str | None:
        """Get state at specific call number."""
        return self._state_history.get(call_number)

    def set_state(self, state):
        """Restore state."""
        self._rng.setstate(state)


class EventQueue:
    """
    Deterministic event queue.
    All state changes flow through here.
    """

    def __init__(self, seeded_random: SeededRandom):
        self.rng = seeded_random
        self._queue: list[SimulationEvent] = []
        self._history: list[SimulationEvent] = []
        self._handlers: dict[EventType, list[Callable]] = {}
        self._tick = 0
        self._event_counter = 0

    def register_handler(self, event_type: EventType, handler: Callable):
        """Register event handler."""
        if event_type not in self._handlers:
            self._handlers[event_type] = []
        self._handlers[event_type].append(handler)

    def emit(
        self, event_type: EventType, source_id: str, payload: dict[str, Any]
    ) -> SimulationEvent:
        """Emit an event to the queue."""
        self._event_counter += 1

        event = SimulationEvent(
            event_id=f"evt_{self._tick}_{self._event_counter}",
            tick=self._tick,
            event_type=event_type,
            source_id=source_id,
            payload=payload,
            rng_state=self.rng.get_state(),
        )

        self._queue.append(event)
        return event

    def process_tick(self) -> list[SimulationEvent]:
        """
        Process all events for current tick.
        Returns processed events.
        """
        processed = []

        # Sort queue deterministically
        self._queue.sort(key=lambda e: (e.event_type.value, e.source_id))

        # Process each event
        while self._queue:
            event = self._queue.pop(0)

            # Call handlers
            handlers = self._handlers.get(event.event_type, [])
            for handler in handlers:
                try:
                    handler(event)
                except Exception as e:
                    # Log error but continue
                    print(f"Handler error for {event.event_type.name}: {e}")

            # Record in history
            self._history.append(event)
            processed.append(event)

        self._tick += 1
        return processed

    def get_history(self, tick: int | None = None) -> list[SimulationEvent]:
        """Get event history, optionally filtered by tick."""
        if tick is None:
            return list(self._history)
        return [e for e in self._history if e.tick == tick]

    def get_agent_events(self, agent_id: str) -> list[SimulationEvent]:
        """Get all events for an agent."""
        return [e for e in self._history if e.source_id == agent_id]

    def export_history(self, filepath: str):
        """Export event history for replay."""
        data = {
            "tick_count": self._tick,
            "event_count": len(self._history),
            "events": [e.to_dict() for e in self._history],
        }

        with open(filepath, "w") as f:
            json.dump(data, f, indent=2)


class DeterministicSimulation:
    """
    Deterministic simulation using event-queue architecture.
    Guarantees reproducibility and eliminates race conditions.
    """

    def __init__(self, seed: int, config: dict[str, Any], agents: dict[str, Any]):
        # Create seed
        config_hash = hashlib.sha256(json.dumps(config, sort_keys=True).encode()).hexdigest()[:32]

        self.seed = SimulationSeed(
            rng_seed=seed,
            config_hash=config_hash,
            agent_init_states=[
                {
                    "agent_id": aid,
                    "state": a.get_state_summary() if hasattr(a, "get_state_summary") else {},
                }
                for aid, a in agents.items()
            ],
        )

        # Seeded RNG
        self.rng = SeededRandom(seed)

        # Event queue
        self.event_queue = EventQueue(self.rng)

        # State
        self.tick = 0
        self.agents = agents
        self.config = config

        # Statistics
        self.stats = {"events_processed": 0, "ticks_completed": 0}

        # Setup handlers
        self._setup_handlers()

    def _setup_handlers(self):
        """Setup event handlers."""
        # Agent action handler
        self.event_queue.register_handler(EventType.AGENT_ACTION, self._handle_agent_action)

        # Agent move handler
        self.event_queue.register_handler(EventType.AGENT_MOVE, self._handle_agent_move)

        # Emotion contagion handler
        self.event_queue.register_handler(
            EventType.EMOTION_CONTAGION, self._handle_emotion_contagion
        )

        # Weather change handler
        self.event_queue.register_handler(EventType.WEATHER_CHANGE, self._handle_weather_change)

        # Hazard spawn handler
        self.event_queue.register_handler(EventType.HAZARD_SPAWN, self._handle_hazard_spawn)

    def tick(self) -> dict[str, Any]:
        """
        Execute one deterministic tick.
        All state changes happen through events.
        """
        # Emit world tick event
        self.event_queue.emit(EventType.WORLD_TICK, "world", {"tick": self.tick})

        # Generate agent events
        for agent_id, agent in self.agents.items():
            if hasattr(agent, "stats") and not agent.stats.is_alive():
                continue

            # Agent decides action
            if hasattr(agent, "decide_action"):
                action = agent.decide_action()
                if action:
                    self.event_queue.emit(EventType.AGENT_ACTION, agent_id, {"action": action})

        # Process all events
        processed = self.event_queue.process_tick()

        self.tick += 1
        self.stats["ticks_completed"] = self.tick
        self.stats["events_processed"] += len(processed)

        return {
            "tick": self.tick,
            "events_processed": len(processed),
            "rng_calls": self.rng._call_count,
        }

    def _handle_agent_action(self, event: SimulationEvent):
        """Handle agent action event."""
        agent = self.agents.get(event.source_id)
        if agent and hasattr(agent, "execute_action"):
            action = event.payload.get("action")
            agent.execute_action(action)

    def _handle_agent_move(self, event: SimulationEvent):
        """Handle agent move event."""
        agent = self.agents.get(event.source_id)
        if agent and hasattr(agent, "location"):
            new_loc = event.payload.get("location")
            agent.location = new_loc

    def _handle_emotion_contagion(self, event: SimulationEvent):
        """Handle emotion contagion event."""
        source_id = event.payload.get("source_id")
        target_id = event.payload.get("target_id")
        emotion = event.payload.get("emotion")
        intensity = event.payload.get("intensity")

        source = self.agents.get(source_id)
        target = self.agents.get(target_id)

        if source and target and hasattr(target, "emotional_state"):
            from ..core.emotions import EmotionType

            try:
                emotion_type = EmotionType[emotion]
                target.emotional_state.apply_stimulus(emotion_type, intensity)
            except (KeyError, ValueError):
                pass

    def _handle_weather_change(self, event: SimulationEvent):
        """Handle weather change event."""
        # Implementation depends on environment
        pass

    def _handle_hazard_spawn(self, event: SimulationEvent):
        """Handle hazard spawn event."""
        # Implementation depends on environment
        pass

    def replay(self, event_log: list[SimulationEvent]) -> bool:
        """
        Replay simulation from event log.
        Returns True if replay matches original.
        """
        # Reset state
        self.tick = 0
        self.rng = SeededRandom(self.seed.rng_seed)
        self.event_queue = EventQueue(self.rng)
        self._setup_handlers()

        # Replay events
        for event in event_log:
            # Verify RNG state if available
            if event.rng_state:
                current_state = self.rng.get_state()
                if current_state != event.rng_state:
                    print(f"RNG mismatch at tick {event.tick}")
                    return False

            # Emit and process
            self.event_queue.emit(event.event_type, event.source_id, event.payload)

            if event.event_type == EventType.WORLD_TICK:
                self.event_queue.process_tick()
                self.tick += 1

        return True

    def export_for_replay(self, filepath: str):
        """Export simulation state for replay."""
        data = {
            "seed": {
                "rng_seed": self.seed.rng_seed,
                "config_hash": self.seed.config_hash,
                "agent_init_states": self.seed.agent_init_states,
                "created_at": self.seed.created_at,
            },
            "config": self.config,
            "final_tick": self.tick,
            "statistics": self.stats,
            "event_history": [e.to_dict() for e in self.event_queue._history],
        }

        with open(filepath, "w") as f:
            json.dump(data, f, indent=2)

        return filepath

    @classmethod
    def from_replay_file(cls, filepath: str) -> "DeterministicSimulation":
        """Load simulation from replay file."""
        with open(filepath) as f:
            data = json.load(f)

        seed_data = data["seed"]

        # Create minimal simulation for replay
        sim = cls.__new__(cls)
        sim.seed = SimulationSeed(**seed_data)
        sim.rng = SeededRandom(sim.seed.rng_seed)
        sim.event_queue = EventQueue(sim.rng)
        sim.tick = 0
        sim.agents = {}
        sim.config = data["config"]
        sim.stats = {"events_processed": 0, "ticks_completed": 0}

        return sim


class ReplayVerifier:
    """Verify replay correctness."""

    @staticmethod
    def verify_replay(
        original_events: list[SimulationEvent], replayed_events: list[SimulationEvent]
    ) -> dict:
        """Verify replay matches original."""
        results = {
            "match": True,
            "event_count_match": len(original_events) == len(replayed_events),
            "differences": [],
        }

        if not results["event_count_match"]:
            results["match"] = False
            results["differences"].append(
                f"Event count mismatch: {len(original_events)} vs {len(replayed_events)}"
            )
            return results

        for i, (orig, replay) in enumerate(zip(original_events, replayed_events, strict=False)):
            if orig.hash() != replay.hash():
                results["match"] = False
                results["differences"].append(
                    {
                        "index": i,
                        "tick": orig.tick,
                        "original": orig.to_dict(),
                        "replayed": replay.to_dict(),
                    }
                )

        return results
