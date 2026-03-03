"""
Enhanced Simulation API Routes

Exposes all advanced simulation capabilities:
- Integrated agents with behavior trees
- Dynamic environment control
- Teamwork management
- Security governance
- Real-time WebSocket updates
"""

import asyncio
import os
from datetime import datetime
from typing import Any

from fastapi import APIRouter, BackgroundTasks, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from ...core.world_features import WeatherType
from ...simulation.engine import EnhancedSimulation, SimulationConfig

router = APIRouter(prefix="/simulation", tags=["simulation"])

# Active simulations store
active_simulations: dict[str, EnhancedSimulation] = {}
simulation_tasks: dict[str, asyncio.Task] = {}


# ============== Pydantic Models ==============

class AgentCreateRequest(BaseModel):
    name: str = Field(..., description="Agent name")
    ocean_traits: dict[str, float] | None = Field(
        None,
        description="OCEAN personality traits (0.0-1.0)"
    )
    location: tuple | None = Field(None, description="Initial location (x, y)")
    behavior_tree: str = Field("agent_ai", description="Behavior tree type")


class TeamCreateRequest(BaseModel):
    name: str = Field(..., description="Team name")
    description: str = Field("", description="Team description")
    member_ids: list[str] = Field(default_factory=list, description="Initial member IDs")


class GoalAssignRequest(BaseModel):
    team_id: str = Field(..., description="Target team ID")
    goal_type: str = Field(..., description="Goal type (exploration, resource_gathering, defense, etc.)")
    params: dict[str, Any] = Field(default_factory=dict, description="Goal parameters")


class WeatherControlRequest(BaseModel):
    weather_type: str = Field(..., description="Weather type to set")
    intensity: float = Field(0.5, ge=0.0, le=1.0, description="Weather intensity")


class EventTriggerRequest(BaseModel):
    event_type: str = Field(..., description="Event type to trigger")
    params: dict[str, Any] = Field(default_factory=dict, description="Event parameters")


class SimulationConfigRequest(BaseModel):
    world_size: tuple = Field((20, 20), description="World dimensions")
    num_agents: int = Field(10, ge=1, le=100, description="Number of agents")
    tick_rate: float = Field(1.0, ge=0.1, le=10.0, description="Ticks per second")
    max_ticks: int = Field(1000, ge=10, description="Maximum simulation ticks")
    security_level: str = Field("standard", description="Security level (low, standard, high, maximum)")
    teamwork_enabled: bool = Field(True, description="Enable teamwork system")
    weather_enabled: bool = Field(True, description="Enable weather system")
    hazards_enabled: bool = Field(True, description="Enable dynamic hazards")


# ============== HTTP Routes ==============

@router.post("/create", response_model=dict[str, str])
async def create_simulation(config: SimulationConfigRequest):
    """Create a new simulation instance."""
    sim_id = f"sim_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    sim_config = SimulationConfig(
        world_size=config.world_size,
        num_agents=config.num_agents,
        tick_rate=config.tick_rate,
        max_ticks=config.max_ticks,
        security_level=config.security_level,
        teamwork_enabled=config.teamwork_enabled,
        weather_enabled=config.weather_enabled,
        hazards_enabled=config.hazards_enabled
    )

    simulation = EnhancedSimulation(sim_config)
    simulation.initialize()

    active_simulations[sim_id] = simulation

    return {
        "simulation_id": sim_id,
        "status": "created",
        "agents_created": str(len(simulation.agents))
    }


@router.post("/{sim_id}/start")
async def start_simulation(sim_id: str, background_tasks: BackgroundTasks):
    """Start a simulation."""
    if sim_id not in active_simulations:
        raise HTTPException(status_code=404, detail="Simulation not found")

    simulation = active_simulations[sim_id]

    if simulation.running:
        raise HTTPException(status_code=400, detail="Simulation already running")

    # Start in background
    task = asyncio.create_task(simulation.run())
    simulation_tasks[sim_id] = task

    return {"status": "started", "simulation_id": sim_id}


@router.post("/{sim_id}/pause")
async def pause_simulation(sim_id: str):
    """Pause a running simulation."""
    if sim_id not in active_simulations:
        raise HTTPException(status_code=404, detail="Simulation not found")

    simulation = active_simulations[sim_id]
    simulation.pause()

    return {"status": "paused", "tick": simulation.tick_count}


@router.post("/{sim_id}/resume")
async def resume_simulation(sim_id: str):
    """Resume a paused simulation."""
    if sim_id not in active_simulations:
        raise HTTPException(status_code=404, detail="Simulation not found")

    simulation = active_simulations[sim_id]
    simulation.resume()

    return {"status": "resumed", "tick": simulation.tick_count}


@router.post("/{sim_id}/stop")
async def stop_simulation(sim_id: str):
    """Stop a simulation."""
    if sim_id not in active_simulations:
        raise HTTPException(status_code=404, detail="Simulation not found")

    simulation = active_simulations[sim_id]
    simulation.stop()

    # Cancel task
    if sim_id in simulation_tasks:
        simulation_tasks[sim_id].cancel()
        del simulation_tasks[sim_id]

    return {"status": "stopped", "tick": simulation.tick_count}


@router.get("/{sim_id}/state")
async def get_simulation_state(sim_id: str):
    """Get current simulation state."""
    if sim_id not in active_simulations:
        raise HTTPException(status_code=404, detail="Simulation not found")

    simulation = active_simulations[sim_id]
    return simulation.get_state()


@router.get("/{sim_id}/agents")
async def list_agents(sim_id: str):
    """List all agents in simulation."""
    if sim_id not in active_simulations:
        raise HTTPException(status_code=404, detail="Simulation not found")

    simulation = active_simulations[sim_id]
    return {
        "agents": [
            {
                "agent_id": agent_id,
                "name": agent.name,
                "location": agent.location,
                "health": agent.stats.health,
                "alive": agent.stats.is_alive(),
                "emotional_state": agent.emotional_state.get_dominant_emotion(),
                "team": agent.current_team.id if agent.current_team else None
            }
            for agent_id, agent in simulation.agents.items()
        ]
    }


@router.post("/{sim_id}/agents")
async def add_agent(sim_id: str, request: AgentCreateRequest):
    """Add a new agent to simulation."""
    if sim_id not in active_simulations:
        raise HTTPException(status_code=404, detail="Simulation not found")

    simulation = active_simulations[sim_id]

    agent = simulation.add_agent(
        name=request.name,
        ocean_traits=request.ocean_traits,
        location=request.location,
        behavior_tree=request.behavior_tree
    )

    return {
        "agent_id": agent.agent_id,
        "name": agent.name,
        "location": agent.location,
        "status": "added"
    }


@router.get("/{sim_id}/agents/{agent_id}")
async def get_agent_details(sim_id: str, agent_id: str):
    """Get detailed agent information."""
    if sim_id not in active_simulations:
        raise HTTPException(status_code=404, detail="Simulation not found")

    simulation = active_simulations[sim_id]
    agent = simulation.agents.get(agent_id)

    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    return agent.get_state_summary()


@router.get("/{sim_id}/teams")
async def list_teams(sim_id: str):
    """List all teams in simulation."""
    if sim_id not in active_simulations:
        raise HTTPException(status_code=404, detail="Simulation not found")

    simulation = active_simulations[sim_id]

    return {
        "teams": [
            {
                "team_id": team_id,
                "name": team.name,
                "member_count": len(team.members),
                "active_goals": len(team.active_goals),
                "coordination_bonus": team.get_coordination_bonus(),
                "members": list(team.members.keys())
            }
            for team_id, team in simulation.team_manager.teams.items()
        ]
    }


@router.post("/{sim_id}/teams")
async def create_team(sim_id: str, request: TeamCreateRequest):
    """Create a new team."""
    if sim_id not in active_simulations:
        raise HTTPException(status_code=404, detail="Simulation not found")

    simulation = active_simulations[sim_id]

    team = simulation.team_manager.create_team(request.name, request.description)

    # Add members
    for agent_id in request.member_ids:
        agent = simulation.agents.get(agent_id)
        if agent:
            from ...core.teamwork import TeamRole
            role = TeamRole.LEADER if not team.members else TeamRole.MEMBER
            team.add_member(agent_id, role)
            agent.current_team = team

    return {
        "team_id": team.id,
        "name": team.name,
        "members_added": len(request.member_ids)
    }


@router.post("/{sim_id}/teams/goal")
async def assign_team_goal(sim_id: str, request: GoalAssignRequest):
    """Assign a goal to a team."""
    if sim_id not in active_simulations:
        raise HTTPException(status_code=404, detail="Simulation not found")

    simulation = active_simulations[sim_id]

    goal = simulation.create_team_goal(
        team_id=request.team_id,
        goal_type=request.goal_type,
        **request.params
    )

    if not goal:
        raise HTTPException(status_code=400, detail="Failed to assign goal")

    return {
        "goal_id": goal.id,
        "team_id": request.team_id,
        "goal_type": request.goal_type,
        "status": "assigned"
    }


@router.post("/{sim_id}/weather")
async def control_weather(sim_id: str, request: WeatherControlRequest):
    """Control simulation weather."""
    if sim_id not in active_simulations:
        raise HTTPException(status_code=404, detail="Simulation not found")

    simulation = active_simulations[sim_id]

    try:
        weather_type = WeatherType[request.weather_type.upper()]
    except KeyError:
        raise HTTPException(status_code=400, detail=f"Invalid weather type: {request.weather_type}") from None

    # Set weather
    simulation.environment.weather = simulation.environment.weather.__class__(
        weather_type=weather_type,
        intensity=request.intensity,
        temperature=simulation.environment._get_seasonal_temperature(weather_type),
        humidity=0.5,
        wind_speed=20.0 if weather_type in [WeatherType.STORM, WeatherType.BLIZZARD] else 5.0
    )

    return {
        "weather_type": weather_type.name,
        "intensity": request.intensity,
        "status": "set"
    }


@router.post("/{sim_id}/events")
async def trigger_event(sim_id: str, request: EventTriggerRequest):
    """Trigger an environmental event."""
    if sim_id not in active_simulations:
        raise HTTPException(status_code=404, detail="Simulation not found")

    simulation = active_simulations[sim_id]

    try:
        event = simulation.trigger_event(request.event_type, **request.params)
        return {
            "event_id": event.event_id,
            "event_type": request.event_type,
            "status": "triggered"
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.get("/{sim_id}/environment")
async def get_environment_state(sim_id: str):
    """Get current environment state."""
    if sim_id not in active_simulations:
        raise HTTPException(status_code=404, detail="Simulation not found")

    simulation = active_simulations[sim_id]
    return simulation.environment.get_environmental_summary()


@router.get("/{sim_id}/hazards")
async def list_hazards(sim_id: str):
    """List active hazards."""
    if sim_id not in active_simulations:
        raise HTTPException(status_code=404, detail="Simulation not found")

    simulation = active_simulations[sim_id]

    return {
        "hazards": [
            {
                "hazard_id": h.hazard_id,
                "type": h.hazard_type.name,
                "severity": h.severity.name,
                "location": h.location,
                "radius": h.radius,
                "active": h.active,
                "contained": h.contained
            }
            for h in simulation.environment.hazards.values()
        ]
    }


@router.get("/{sim_id}/statistics")
async def get_statistics(sim_id: str):
    """Get simulation statistics."""
    if sim_id not in active_simulations:
        raise HTTPException(status_code=404, detail="Simulation not found")

    simulation = active_simulations[sim_id]

    return {
        "statistics": simulation.statistics,
        "tick": simulation.tick_count,
        "agent_count": len(simulation.agents),
        "alive_count": sum(1 for a in simulation.agents.values() if a.stats.is_alive()),
        "team_count": len(simulation.team_manager.teams),
        "hazard_count": len(simulation.environment.hazards)
    }


@router.get("/{sim_id}/events/log")
async def get_event_log(sim_id: str, limit: int = 100):
    """Get recent simulation events."""
    if sim_id not in active_simulations:
        raise HTTPException(status_code=404, detail="Simulation not found")

    simulation = active_simulations[sim_id]
    return {"events": simulation.event_log[-limit:]}


@router.post("/{sim_id}/export")
async def export_results(sim_id: str):
    """Export simulation results to file."""
    if sim_id not in active_simulations:
        raise HTTPException(status_code=404, detail="Simulation not found")

    simulation = active_simulations[sim_id]

    filepath = f"/tmp/simulation_{sim_id}_results.json"
    simulation.export_results(filepath)

    return {
        "status": "exported",
        "filepath": filepath,
        "download_url": f"/simulation/{sim_id}/download"
    }


@router.get("/{sim_id}/download")
async def download_results(sim_id: str):
    """Download simulation results file."""
    filepath = f"/tmp/simulation_{sim_id}_results.json"

    if not os.path.exists(filepath):
        raise HTTPException(status_code=404, detail="Export file not found")

    return FileResponse(
        filepath,
        media_type="application/json",
        filename=f"simulation_{sim_id}_results.json"
    )


# ============== WebSocket Routes ==============

@router.websocket("/{sim_id}/ws")
async def simulation_websocket(websocket: WebSocket, sim_id: str):
    """WebSocket for real-time simulation updates."""
    await websocket.accept()

    if sim_id not in active_simulations:
        await websocket.send_json({"error": "Simulation not found"})
        await websocket.close()
        return

    simulation = active_simulations[sim_id]

    try:
        # Send initial state
        await websocket.send_json({
            "type": "initial_state",
            "data": simulation.get_state()
        })

        # Subscribe to updates
        last_tick = simulation.tick_count

        while True:
            # Check for updates
            if simulation.tick_count > last_tick:
                await websocket.send_json({
                    "type": "tick_update",
                    "tick": simulation.tick_count,
                    "data": {
                        "agents": {
                            aid: {
                                "location": a.location,
                                "health": a.stats.health,
                                "emotional_state": a.emotional_state.get_dominant_emotion(),
                                "current_action": a.current_action
                            }
                            for aid, a in simulation.agents.items()
                        },
                        "environment": simulation.environment.get_environmental_summary()
                    }
                })
                last_tick = simulation.tick_count

            # Check for messages from client
            try:
                message = await asyncio.wait_for(
                    websocket.receive_json(),
                    timeout=0.1
                )

                # Handle commands
                if message.get("command") == "get_agent_details":
                    agent_id = message.get("agent_id")
                    agent = simulation.agents.get(agent_id)
                    if agent:
                        await websocket.send_json({
                            "type": "agent_details",
                            "agent_id": agent_id,
                            "data": agent.get_state_summary()
                        })

                elif message.get("command") == "trigger_event":
                    event_type = message.get("event_type")
                    params = message.get("params", {})
                    event = simulation.trigger_event(event_type, **params)
                    await websocket.send_json({
                        "type": "event_triggered",
                        "event_id": event.event_id
                    })

            except asyncio.TimeoutError:
                pass

            await asyncio.sleep(0.1)

    except WebSocketDisconnect:
        pass
    except Exception as e:
        await websocket.send_json({"error": str(e)})
        await websocket.close()


@router.websocket("/{sim_id}/agents/{agent_id}/ws")
async def agent_websocket(websocket: WebSocket, sim_id: str, agent_id: str):
    """WebSocket for individual agent updates."""
    await websocket.accept()

    if sim_id not in active_simulations:
        await websocket.send_json({"error": "Simulation not found"})
        await websocket.close()
        return

    simulation = active_simulations[sim_id]
    agent = simulation.agents.get(agent_id)

    if not agent:
        await websocket.send_json({"error": "Agent not found"})
        await websocket.close()
        return

    try:
        # Send initial state
        await websocket.send_json({
            "type": "initial_state",
            "data": agent.get_state_summary()
        })

        last_action_count = len(simulation.agent_action_log)

        while True:
            # Check for new actions by this agent
            new_actions = [
                entry for entry in simulation.agent_action_log[last_action_count:]
                if entry.get("agent_id") == agent_id
            ]

            if new_actions:
                await websocket.send_json({
                    "type": "actions",
                    "actions": new_actions
                })
                last_action_count = len(simulation.agent_action_log)

            # Periodic state update
            if simulation.tick_count % 5 == 0:  # Every 5 ticks
                await websocket.send_json({
                    "type": "state_update",
                    "data": {
                        "location": agent.location,
                        "health": agent.stats.health,
                        "energy": agent.stats.energy,
                        "emotional_state": agent.emotional_state.get_dominant_emotion(),
                        "current_action": agent.current_action,
                        "needs": {
                            "priority": agent.needs.get_priority_need()[0],
                            "urgency": agent.needs.get_priority_need()[1]
                        }
                    }
                })

            await asyncio.sleep(0.2)

    except WebSocketDisconnect:
        pass
    except Exception as e:
        await websocket.send_json({"error": str(e)})
        await websocket.close()
