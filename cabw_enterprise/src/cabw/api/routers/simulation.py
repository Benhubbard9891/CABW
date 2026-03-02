"""API endpoints for simulation management."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

try:
    from fastapi import APIRouter, BackgroundTasks, HTTPException, status
    from pydantic import BaseModel, Field

    router = APIRouter()

    # ---------------------------------------------------------------------------
    # Request / Response schemas
    # ---------------------------------------------------------------------------

    class SimulationCreateRequest(BaseModel):
        name: str = Field(..., min_length=1, max_length=256)
        max_ticks: int = Field(default=1000, ge=1, le=100_000)
        world_width: int = Field(default=50, ge=5, le=1000)
        world_height: int = Field(default=50, ge=5, le=1000)
        agent_count: int = Field(default=10, ge=1, le=1000)
        random_seed: Optional[int] = None

    class SimulationResponse(BaseModel):
        simulation_id: str
        name: str
        status: str
        current_tick: int
        max_ticks: int
        agents_alive: int
        agents_dead: int

    class AgentSummaryResponse(BaseModel):
        agent_id: str
        alive: bool
        energy: float
        position: List[float]
        emotion_label: str
        emotion_pad: List[float]
        team: Optional[str]
        team_role: str
        pending_actions: int

    class SnapshotResponse(BaseModel):
        tick: int
        environment: Dict[str, Any]
        agents: List[Dict[str, Any]]
        stats: Dict[str, Any]

    # ---------------------------------------------------------------------------
    # In-memory simulation registry (replace with DB-backed store in production)
    # ---------------------------------------------------------------------------
    _simulations: Dict[str, Any] = {}

    def _get_sim_or_404(simulation_id: str) -> Any:
        sim = _simulations.get(simulation_id)
        if sim is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Simulation not found")
        return sim

    # ---------------------------------------------------------------------------
    # Endpoints
    # ---------------------------------------------------------------------------

    @router.post("/", response_model=SimulationResponse, status_code=status.HTTP_201_CREATED)
    async def create_simulation(body: SimulationCreateRequest) -> SimulationResponse:
        """Create and register a new simulation."""
        from cabw.core.integrated_agent import AgentConfig, IntegratedAgent
        from cabw.simulation.engine import SimulationConfig, SimulationEngine
        import uuid

        sim_id = str(uuid.uuid4())
        config = SimulationConfig(
            max_ticks=body.max_ticks,
            world_width=body.world_width,
            world_height=body.world_height,
            random_seed=body.random_seed,
        )
        engine = SimulationEngine(config)
        for _ in range(body.agent_count):
            engine.add_agent(IntegratedAgent(config=AgentConfig()))

        _simulations[sim_id] = {
            "id": sim_id,
            "name": body.name,
            "engine": engine,
            "status": "created",
        }
        return SimulationResponse(
            simulation_id=sim_id,
            name=body.name,
            status="created",
            current_tick=0,
            max_ticks=body.max_ticks,
            agents_alive=len(engine.alive_agents),
            agents_dead=0,
        )

    @router.get("/", response_model=List[Dict[str, Any]])
    async def list_simulations() -> List[Dict[str, Any]]:
        """List all registered simulations."""
        return [
            {
                "simulation_id": sim["id"],
                "name": sim["name"],
                "status": sim["status"],
            }
            for sim in _simulations.values()
        ]

    @router.get("/{simulation_id}", response_model=SimulationResponse)
    async def get_simulation(simulation_id: str) -> SimulationResponse:
        """Get details of a specific simulation."""
        sim = _get_sim_or_404(simulation_id)
        engine = sim["engine"]
        return SimulationResponse(
            simulation_id=sim["id"],
            name=sim["name"],
            status=sim["status"],
            current_tick=engine.current_tick,
            max_ticks=engine.config.max_ticks,
            agents_alive=len(engine.alive_agents),
            agents_dead=len(engine.agents) - len(engine.alive_agents),
        )

    @router.post("/{simulation_id}/start", status_code=status.HTTP_202_ACCEPTED)
    async def start_simulation(simulation_id: str, background_tasks: BackgroundTasks) -> Dict[str, str]:
        """Start a simulation run in the background."""
        sim = _get_sim_or_404(simulation_id)
        if sim["status"] == "running":
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Simulation already running")
        sim["status"] = "running"

        def _run() -> None:
            try:
                sim["engine"].run()
                sim["status"] = "completed"
            except Exception:  # noqa: BLE001
                sim["status"] = "failed"

        background_tasks.add_task(_run)
        return {"detail": "Simulation started", "simulation_id": simulation_id}

    @router.post("/{simulation_id}/stop", status_code=status.HTTP_200_OK)
    async def stop_simulation(simulation_id: str) -> Dict[str, str]:
        """Request a running simulation to stop."""
        sim = _get_sim_or_404(simulation_id)
        sim["engine"].stop()
        sim["status"] = "stopped"
        return {"detail": "Stop requested", "simulation_id": simulation_id}

    @router.post("/{simulation_id}/step", status_code=status.HTTP_200_OK)
    async def step_simulation(simulation_id: str) -> SnapshotResponse:
        """Advance the simulation by a single tick and return the new state."""
        sim = _get_sim_or_404(simulation_id)
        engine = sim["engine"]
        engine.step()
        snapshot = engine.snapshot()
        return SnapshotResponse(**snapshot)

    @router.get("/{simulation_id}/snapshot", response_model=SnapshotResponse)
    async def get_snapshot(simulation_id: str) -> SnapshotResponse:
        """Return the current state snapshot of the simulation."""
        sim = _get_sim_or_404(simulation_id)
        snapshot = sim["engine"].snapshot()
        return SnapshotResponse(**snapshot)

    @router.get("/{simulation_id}/agents", response_model=List[AgentSummaryResponse])
    async def list_agents(simulation_id: str) -> List[AgentSummaryResponse]:
        """List all agents in a simulation."""
        sim = _get_sim_or_404(simulation_id)
        return [AgentSummaryResponse(**a.summary()) for a in sim["engine"].agents]

    @router.delete("/{simulation_id}", status_code=status.HTTP_204_NO_CONTENT)
    async def delete_simulation(simulation_id: str) -> None:
        """Delete a simulation and free its resources."""
        _get_sim_or_404(simulation_id)
        del _simulations[simulation_id]

except ImportError:
    # FastAPI / Pydantic not installed
    router = None  # type: ignore[assignment]
