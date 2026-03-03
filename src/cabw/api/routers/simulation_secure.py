"""
Secure Simulation API Routes

Authenticated and authorized API with:
- JWT-based authentication
- PBAC authorization
- Execution token enforcement
- Deterministic replay support
"""

import asyncio
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field

from ...core.deliberation import DeliberationLogger
from ...governance.enforcement import ConstitutionalLayer
from ...governance.security import Capability
from ...simulation.deterministic import DeterministicSimulation
from ...simulation.engine import EnhancedSimulation, SimulationConfig
from ..auth import (
    APIPrincipal,
    WebSocketAuth,
    auth_manager,
    get_current_principal,
    require_capability,
)

router = APIRouter(prefix="/simulation", tags=["simulation"])

# Active simulations store
active_simulations: dict[str, EnhancedSimulation] = {}
deterministic_sims: dict[str, DeterministicSimulation] = {}
simulation_tasks: dict[str, asyncio.Task] = {}
constitutional_layers: dict[str, ConstitutionalLayer] = {}
deliberation_loggers: dict[str, DeliberationLogger] = {}


# ============== Pydantic Models ==============


class LoginRequest(BaseModel):
    username: str
    password: str


class SimulationConfigRequest(BaseModel):
    world_size: tuple = Field((20, 20))
    num_agents: int = Field(10, ge=1, le=100)
    tick_rate: float = Field(1.0, ge=0.1, le=10.0)
    max_ticks: int = Field(1000, ge=10)
    security_level: str = Field("standard")
    teamwork_enabled: bool = Field(True)
    weather_enabled: bool = Field(True)
    hazards_enabled: bool = Field(True)
    deterministic: bool = Field(False)
    seed: int | None = Field(None)


class ActionRequest(BaseModel):
    action_type: str
    params: dict[str, Any] = Field(default_factory=dict)


# ============== Authentication Routes ==============


@router.post("/auth/login")
async def login(request: LoginRequest):
    """Authenticate and get access token."""
    principal = auth_manager.authenticate_user(request.username, request.password)

    if not principal:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = auth_manager.create_access_token(principal)

    return {
        "access_token": token,
        "token_type": "bearer",
        "role": principal.role.name,
        "capabilities": [c.name for c in principal.capabilities],
    }


# ============== Simulation Management (Protected) ==============


@router.post("/create")
async def create_simulation(
    request: SimulationConfigRequest,
    principal: APIPrincipal = Depends(require_capability(Capability.CREATE)),
):
    """Create a new simulation instance (requires CREATE capability)."""
    sim_id = f"sim_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    sim_config = SimulationConfig(
        world_size=request.world_size,
        num_agents=request.num_agents,
        tick_rate=request.tick_rate,
        max_ticks=request.max_ticks,
        security_level=request.security_level,
        teamwork_enabled=request.teamwork_enabled,
        weather_enabled=request.weather_enabled,
        hazards_enabled=request.hazards_enabled,
    )

    simulation = EnhancedSimulation(sim_config)
    simulation.initialize()

    active_simulations[sim_id] = simulation

    # Setup constitutional layer
    constitutional = ConstitutionalLayer()
    constitutional_layers[sim_id] = constitutional

    # Setup deliberation logger
    deliberation_loggers[sim_id] = DeliberationLogger()

    # Setup deterministic mode if requested
    if request.deterministic:
        deterministic = DeterministicSimulation(
            seed=request.seed or hash(sim_id) % (2**32),
            config=sim_config.__dict__,
            agents=simulation.agents,
        )
        deterministic_sims[sim_id] = deterministic

    # Log creation through governor so the hash chain and threat detection run
    from ...governance.security import AccessDecision
    from ...governance.security import Capability as _Cap

    constitutional.governor._audit(
        subject={"id": principal.principal_id, "type": "api_principal"},
        resource={"id": sim_id, "type": "simulation"},
        capability=_Cap.ACTION_EXECUTE,
        decision=AccessDecision(granted=True, reason=f"Created by {principal.principal_id}"),
        context={"action": "create_simulation"},
    )

    return {
        "simulation_id": sim_id,
        "status": "created",
        "agents_created": len(simulation.agents),
        "deterministic": request.deterministic,
        "seed": deterministic.seed.rng_seed if request.deterministic else None,
    }


@router.post("/{sim_id}/start")
async def start_simulation(
    sim_id: str, principal: APIPrincipal = Depends(require_capability(Capability.ACTION_EXECUTE))
):
    """Start a simulation (requires EXECUTE capability)."""
    # Check access
    allowed, reason = auth_manager.check_api_access(principal, "control", sim_id)
    if not allowed:
        raise HTTPException(status_code=403, detail=reason)

    if sim_id not in active_simulations:
        raise HTTPException(status_code=404, detail="Simulation not found")

    simulation = active_simulations[sim_id]

    if simulation.running:
        raise HTTPException(status_code=400, detail="Simulation already running")

    # Require constitutional layer — it must have been created during /create
    constitutional = constitutional_layers.get(sim_id)
    if not constitutional:
        raise HTTPException(status_code=500, detail="Constitutional layer not initialized")

    async def run_with_governance():
        """Run simulation with governance enforcement on every tick."""
        while simulation.running and simulation.tick_count < simulation.config.max_ticks:
            if not simulation.paused:
                # Check constitutional invariants before each tick
                passed, reason = constitutional.check_invariants(simulation, None, {})
                if not passed:
                    simulation.running = False
                    break

                # Emit tick event
                if sim_id in deterministic_sims:
                    det = deterministic_sims[sim_id]
                    det.tick()
                else:
                    await simulation.tick()

            await asyncio.sleep(1.0 / simulation.config.tick_rate)

    task = asyncio.create_task(run_with_governance())
    simulation_tasks[sim_id] = task

    return {"status": "started", "simulation_id": sim_id}


@router.post("/{sim_id}/pause")
async def pause_simulation(
    sim_id: str, principal: APIPrincipal = Depends(require_capability(Capability.ACTION_EXECUTE))
):
    """Pause a running simulation."""
    allowed, reason = auth_manager.check_api_access(principal, "control", sim_id)
    if not allowed:
        raise HTTPException(status_code=403, detail=reason)

    if sim_id not in active_simulations:
        raise HTTPException(status_code=404, detail="Simulation not found")

    simulation = active_simulations[sim_id]
    simulation.pause()

    return {"status": "paused", "tick": simulation.tick_count}


@router.get("/{sim_id}/state")
async def get_simulation_state(
    sim_id: str, principal: APIPrincipal = Depends(get_current_principal)
):
    """Get current simulation state (requires VIEW capability)."""
    allowed, reason = auth_manager.check_api_access(principal, "view", sim_id)
    if not allowed:
        raise HTTPException(status_code=403, detail=reason)

    if sim_id not in active_simulations:
        raise HTTPException(status_code=404, detail="Simulation not found")

    simulation = active_simulations[sim_id]
    return simulation.get_state()


@router.post("/{sim_id}/agents/{agent_id}/action")
async def execute_agent_action(
    sim_id: str,
    agent_id: str,
    request: ActionRequest,
    principal: APIPrincipal = Depends(require_capability(Capability.ACTION_EXECUTE)),
):
    """
    Execute action through constitutional layer.
    Requires token from ActionBudget.
    """
    allowed, reason = auth_manager.check_api_access(principal, "modify", sim_id)
    if not allowed:
        raise HTTPException(status_code=403, detail=reason)

    if sim_id not in active_simulations:
        raise HTTPException(status_code=404, detail="Simulation not found")

    simulation = active_simulations[sim_id]
    agent = simulation.agents.get(agent_id)

    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    # Get constitutional layer
    constitutional = constitutional_layers.get(sim_id)
    if not constitutional:
        raise HTTPException(status_code=500, detail="Constitutional layer not initialized")

    # Create action object
    from ...core.actions import ComplexAction

    action = ComplexAction(
        id=f"action_{request.action_type}",
        name=request.action_type,
        preconditions=[],
        costs=None,
        effects=[],
        constraints=request.params,
    )

    # Execute through constitutional layer
    def action_func():
        # Actual action execution
        return {"status": "executed", "action": request.action_type}

    receipt = constitutional.execute(agent, action, action_func)

    if not receipt:
        raise HTTPException(status_code=403, detail="Action denied by constitutional layer")

    return {
        "status": "executed",
        "token_id": receipt.token_id,
        "success": receipt.success,
        "result": receipt.result,
    }


@router.post("/{sim_id}/export")
async def export_simulation(sim_id: str, principal: APIPrincipal = Depends(get_current_principal)):
    """Export simulation for replay."""
    allowed, reason = auth_manager.check_api_access(principal, "view", sim_id)
    if not allowed:
        raise HTTPException(status_code=403, detail=reason)

    if sim_id not in active_simulations:
        raise HTTPException(status_code=404, detail="Simulation not found")

    simulation = active_simulations[sim_id]

    # Export based on mode
    if sim_id in deterministic_sims:
        det = deterministic_sims[sim_id]
        filepath = f"/tmp/simulation_{sim_id}_replay.json"
        det.export_for_replay(filepath)
    else:
        filepath = f"/tmp/simulation_{sim_id}_results.json"
        simulation.export_results(filepath)

    return {
        "status": "exported",
        "filepath": filepath,
        "download_url": f"/simulation/{sim_id}/download",
    }


@router.post("/{sim_id}/replay")
async def replay_simulation(
    sim_id: str, principal: APIPrincipal = Depends(require_capability(Capability.ACTION_EXECUTE))
):
    """Replay simulation from event log."""
    allowed, reason = auth_manager.check_api_access(principal, "control", sim_id)
    if not allowed:
        raise HTTPException(status_code=403, detail=reason)

    if sim_id not in deterministic_sims:
        raise HTTPException(status_code=400, detail="Simulation not in deterministic mode")

    det = deterministic_sims[sim_id]

    # Get event history
    events = det.event_queue.get_history()

    # Replay
    success = det.replay(events)

    return {"replayed": success, "events_replayed": len(events), "ticks": det.tick}


@router.get("/{sim_id}/audit")
async def get_audit_trail(
    sim_id: str,
    agent_id: str | None = None,
    principal: APIPrincipal = Depends(get_current_principal),
):
    """Get constitutional audit trail."""
    allowed, reason = auth_manager.check_api_access(principal, "view", sim_id)
    if not allowed:
        raise HTTPException(status_code=403, detail=reason)

    if sim_id not in constitutional_layers:
        raise HTTPException(status_code=404, detail="Simulation not found")

    constitutional = constitutional_layers[sim_id]
    trail = constitutional.get_audit_trail(agent_id)

    return {"audit_trail": trail, "count": len(trail)}


# ============== WebSocket (Authenticated) ==============


@router.websocket("/{sim_id}/ws")
async def simulation_websocket(websocket: WebSocket, sim_id: str):
    """Authenticated WebSocket for real-time updates."""
    await websocket.accept()

    # Authenticate
    principal = await WebSocketAuth.authenticate(websocket)
    if not principal:
        return

    # Check access
    allowed, reason = auth_manager.check_api_access(principal, "view", sim_id)
    if not allowed:
        await websocket.send_json({"error": reason})
        await websocket.close()
        return

    if sim_id not in active_simulations:
        await websocket.send_json({"error": "Simulation not found"})
        await websocket.close()
        return

    simulation = active_simulations[sim_id]

    try:
        # Send initial state
        await websocket.send_json(
            {
                "type": "authenticated",
                "principal": principal.principal_id,
                "role": principal.role.name,
            }
        )

        await websocket.send_json({"type": "initial_state", "data": simulation.get_state()})

        last_tick = simulation.tick_count

        while True:
            if simulation.tick_count > last_tick:
                await websocket.send_json(
                    {
                        "type": "tick_update",
                        "tick": simulation.tick_count,
                        "data": simulation.get_state(),
                    }
                )
                last_tick = simulation.tick_count

            try:
                message = await asyncio.wait_for(websocket.receive_json(), timeout=0.1)

                # Handle commands based on role
                if message.get("command") == "trigger_event":
                    if not principal.has_capability(Capability.ACTION_EXECUTE):
                        await websocket.send_json({"error": "Missing EXECUTE capability"})
                        continue

                    event_type = message.get("event_type")
                    params = message.get("params", {})
                    event = simulation.trigger_event(event_type, **params)
                    await websocket.send_json(
                        {"type": "event_triggered", "event_id": event.event_id}
                    )

            except asyncio.TimeoutError:
                pass

            await asyncio.sleep(0.1)

    except WebSocketDisconnect:
        pass
    except Exception as e:
        await websocket.send_json({"error": str(e)})
        await websocket.close()
