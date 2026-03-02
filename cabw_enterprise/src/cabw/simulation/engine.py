"""Enhanced simulation engine for CABW."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

from cabw.core.integrated_agent import IntegratedAgent
from cabw.core.world_features import WorldEnvironment, WorldEventBus, WorldGrid


@dataclass
class SimulationConfig:
    """Configuration for a simulation run."""

    max_ticks: int = 1000
    tick_delay_seconds: float = 0.0   # Wall-clock pause between ticks (0 = as fast as possible)
    world_width: int = 50
    world_height: int = 50
    enable_emotional_contagion: bool = True
    enable_team_dynamics: bool = True
    random_seed: Optional[int] = None


@dataclass
class SimulationStats:
    """Aggregated statistics collected during a simulation run."""

    total_ticks: int = 0
    agents_alive: int = 0
    agents_dead: int = 0
    total_actions_executed: int = 0
    elapsed_seconds: float = 0.0
    per_tick_data: List[Dict[str, Any]] = field(default_factory=list)

    def record_tick(self, tick: int, data: Dict[str, Any]) -> None:
        self.total_ticks = tick
        self.per_tick_data.append({"tick": tick, **data})


class SimulationEngine:
    """Orchestrates agents, world, and events across simulation ticks.

    Usage::

        engine = SimulationEngine(config)
        engine.add_agent(agent1)
        engine.add_agent(agent2)
        engine.run()
    """

    def __init__(self, config: Optional[SimulationConfig] = None) -> None:
        self.config = config or SimulationConfig()
        self.grid = WorldGrid(self.config.world_width, self.config.world_height)
        self.environment = WorldEnvironment(
            width=self.config.world_width,
            height=self.config.world_height,
        )
        self.event_bus = WorldEventBus()
        self._agents: Dict[str, IntegratedAgent] = {}
        self._tick: int = 0
        self._running: bool = False
        self._tick_hooks: List[Callable[["SimulationEngine", int], None]] = []
        self.stats = SimulationStats()

    # ------------------------------------------------------------------
    # Agent management
    # ------------------------------------------------------------------

    def add_agent(self, agent: IntegratedAgent) -> None:
        self._agents[agent.agent_id] = agent

    def remove_agent(self, agent_id: str) -> bool:
        if agent_id in self._agents:
            del self._agents[agent_id]
            return True
        return False

    @property
    def agents(self) -> List[IntegratedAgent]:
        return list(self._agents.values())

    @property
    def alive_agents(self) -> List[IntegratedAgent]:
        return [a for a in self._agents.values() if a.alive]

    # ------------------------------------------------------------------
    # Hooks
    # ------------------------------------------------------------------

    def add_tick_hook(self, fn: Callable[["SimulationEngine", int], None]) -> None:
        """Register a callback invoked at the end of every tick."""
        self._tick_hooks.append(fn)

    # ------------------------------------------------------------------
    # Run controls
    # ------------------------------------------------------------------

    def run(self) -> SimulationStats:
        """Run the simulation for up to *max_ticks* ticks.

        Returns
        -------
        SimulationStats collected over the run.
        """
        self._running = True
        start = time.monotonic()

        while self._running and self._tick < self.config.max_ticks:
            self._step()
            if self.config.tick_delay_seconds > 0:
                time.sleep(self.config.tick_delay_seconds)
            if not self.alive_agents:
                break  # All agents dead – no point continuing

        self._running = False
        self.stats.elapsed_seconds = time.monotonic() - start
        self.stats.agents_alive = len(self.alive_agents)
        self.stats.agents_dead = len(self._agents) - self.stats.agents_alive
        return self.stats

    def step(self) -> None:
        """Advance the simulation by exactly one tick (useful for interactive control)."""
        self._step()

    def stop(self) -> None:
        """Request the simulation to stop after the current tick."""
        self._running = False

    # ------------------------------------------------------------------
    # Internal tick logic
    # ------------------------------------------------------------------

    def _step(self) -> None:
        self._tick += 1
        world_state = self._build_world_state()
        actions_this_tick = 0

        for agent in self.alive_agents:
            # Gather neighbor emotions for contagion
            neighbors = agent.perceive(self.alive_agents)
            neighbor_emotions = [n.emotion for n in neighbors] if self.config.enable_emotional_contagion else []

            executed = agent.tick(
                world_state=world_state,
                environment=self.environment,
                neighbor_emotions=neighbor_emotions,
                tick_number=self._tick,
            )
            if executed is not None:
                actions_this_tick += 1

        self.stats.total_actions_executed += actions_this_tick

        # Advance environment time
        self.environment.advance_time(hours=1 / 60)  # Each tick = 1 minute

        tick_data = {
            "alive": len(self.alive_agents),
            "actions": actions_this_tick,
        }
        self.stats.record_tick(self._tick, tick_data)

        for hook in self._tick_hooks:
            hook(self, self._tick)

    def _build_world_state(self) -> Dict[str, Any]:
        return {
            "tick": self._tick,
            "agent_positions": {
                aid: a.position.as_tuple() for aid, a in self._agents.items() if a.alive
            },
            "time_of_day": self.environment.time_of_day,
            "weather": self.environment.weather.name,
        }

    # ------------------------------------------------------------------
    # Utility
    # ------------------------------------------------------------------

    @property
    def current_tick(self) -> int:
        return self._tick

    def snapshot(self) -> Dict[str, Any]:
        """Return a serializable snapshot of the current simulation state."""
        return {
            "tick": self._tick,
            "environment": {
                "time_of_day": self.environment.time_of_day,
                "weather": self.environment.weather.name,
                "temperature": self.environment.temperature,
            },
            "agents": [a.summary() for a in self._agents.values()],
            "stats": {
                "total_ticks": self.stats.total_ticks,
                "alive": len(self.alive_agents),
                "dead": len(self._agents) - len(self.alive_agents),
                "actions_executed": self.stats.total_actions_executed,
            },
        }
