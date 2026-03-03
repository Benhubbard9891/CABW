"""Simulations router."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from cabw.api.routers.auth import get_current_active_user
from cabw.api.schemas import (
    AgentActionResponse,
    SimulationCreate,
    SimulationEventResponse,
    SimulationResponse,
    SimulationUpdate,
)
from cabw.config import settings
from cabw.db.base import db_manager
from cabw.db.models import (
    Agent,
    AgentAction,
    Simulation,
    SimulationEvent,
    SimulationStatus,
)
from cabw.utils.logging import get_logger

logger = get_logger(__name__)
router = APIRouter()


@router.post("", response_model=SimulationResponse, status_code=status.HTTP_201_CREATED)
async def create_simulation(
    simulation_data: SimulationCreate,
    current_user=Depends(get_current_active_user),
    session: AsyncSession = Depends(db_manager.get_session),
) -> Simulation:
    """Create new simulation."""
    simulation = Simulation(
        owner_id=current_user.id,
        world_id=simulation_data.world_id,
        name=simulation_data.name,
        description=simulation_data.description,
        config=simulation_data.config,
        tick_rate=simulation_data.tick_rate or settings.simulation.tick_rate,
        max_ticks=simulation_data.max_ticks or settings.simulation.max_ticks,
    )

    session.add(simulation)
    await session.commit()
    await session.refresh(simulation)

    logger.info(f"Simulation created: {simulation.name} ({simulation.id})")
    return simulation


@router.get("", response_model=list[SimulationResponse])
async def list_simulations(
    status: SimulationStatus | None = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    current_user=Depends(get_current_active_user),
    session: AsyncSession = Depends(db_manager.get_session),
) -> list[Simulation]:
    """List simulations."""
    query = select(Simulation).where(Simulation.owner_id == current_user.id)

    if status:
        query = query.where(Simulation.status == status)

    query = query.offset(skip).limit(limit).order_by(Simulation.created_at.desc())

    result = await session.execute(query)
    return list(result.scalars().all())


@router.get("/{simulation_id}", response_model=SimulationResponse)
async def get_simulation(
    simulation_id: UUID,
    current_user=Depends(get_current_active_user),
    session: AsyncSession = Depends(db_manager.get_session),
) -> Simulation:
    """Get simulation by ID."""
    result = await session.execute(
        select(Simulation).where(
            (Simulation.id == simulation_id) & (Simulation.owner_id == current_user.id)
        )
    )
    simulation = result.scalar_one_or_none()

    if not simulation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Simulation not found")

    return simulation


@router.patch("/{simulation_id}", response_model=SimulationResponse)
async def update_simulation(
    simulation_id: UUID,
    update_data: SimulationUpdate,
    current_user=Depends(get_current_active_user),
    session: AsyncSession = Depends(db_manager.get_session),
) -> Simulation:
    """Update simulation."""
    result = await session.execute(
        select(Simulation).where(
            (Simulation.id == simulation_id) & (Simulation.owner_id == current_user.id)
        )
    )
    simulation = result.scalar_one_or_none()

    if not simulation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Simulation not found")

    # Update fields
    for field, value in update_data.model_dump(exclude_unset=True).items():
        setattr(simulation, field, value)

    await session.commit()
    await session.refresh(simulation)

    logger.info(f"Simulation updated: {simulation.name} ({simulation.id})")
    return simulation


@router.post("/{simulation_id}/start", response_model=SimulationResponse)
async def start_simulation(
    simulation_id: UUID,
    current_user=Depends(get_current_active_user),
    session: AsyncSession = Depends(db_manager.get_session),
) -> Simulation:
    """Start simulation."""
    result = await session.execute(
        select(Simulation).where(
            (Simulation.id == simulation_id) & (Simulation.owner_id == current_user.id)
        )
    )
    simulation = result.scalar_one_or_none()

    if not simulation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Simulation not found")

    if simulation.status not in [SimulationStatus.PENDING, SimulationStatus.PAUSED]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot start simulation with status: {simulation.status}",
        )

    # Start simulation
    simulation.status = SimulationStatus.RUNNING
    from datetime import datetime

    simulation.started_at = datetime.utcnow()

    await session.commit()
    await session.refresh(simulation)

    # Start simulation engine in background
    # This would typically be done via Celery task
    logger.info(f"Simulation started: {simulation.name} ({simulation.id})")

    return simulation


@router.post("/{simulation_id}/pause", response_model=SimulationResponse)
async def pause_simulation(
    simulation_id: UUID,
    current_user=Depends(get_current_active_user),
    session: AsyncSession = Depends(db_manager.get_session),
) -> Simulation:
    """Pause simulation."""
    result = await session.execute(
        select(Simulation).where(
            (Simulation.id == simulation_id) & (Simulation.owner_id == current_user.id)
        )
    )
    simulation = result.scalar_one_or_none()

    if not simulation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Simulation not found")

    if simulation.status != SimulationStatus.RUNNING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Simulation is not running"
        )

    simulation.status = SimulationStatus.PAUSED
    await session.commit()
    await session.refresh(simulation)

    logger.info(f"Simulation paused: {simulation.name} ({simulation.id})")
    return simulation


@router.post("/{simulation_id}/stop", response_model=SimulationResponse)
async def stop_simulation(
    simulation_id: UUID,
    current_user=Depends(get_current_active_user),
    session: AsyncSession = Depends(db_manager.get_session),
) -> Simulation:
    """Stop simulation."""
    result = await session.execute(
        select(Simulation).where(
            (Simulation.id == simulation_id) & (Simulation.owner_id == current_user.id)
        )
    )
    simulation = result.scalar_one_or_none()

    if not simulation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Simulation not found")

    if simulation.status not in [SimulationStatus.RUNNING, SimulationStatus.PAUSED]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Simulation is not active"
        )

    simulation.status = SimulationStatus.COMPLETED
    from datetime import datetime

    simulation.completed_at = datetime.utcnow()

    await session.commit()
    await session.refresh(simulation)

    logger.info(f"Simulation stopped: {simulation.name} ({simulation.id})")
    return simulation


@router.get("/{simulation_id}/events", response_model=list[SimulationEventResponse])
async def get_simulation_events(
    simulation_id: UUID,
    tick: int | None = None,
    event_type: str | None = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    current_user=Depends(get_current_active_user),
    session: AsyncSession = Depends(db_manager.get_session),
) -> list[SimulationEvent]:
    """Get simulation events."""
    query = select(SimulationEvent).where(SimulationEvent.simulation_id == simulation_id)

    if tick is not None:
        query = query.where(SimulationEvent.tick == tick)

    if event_type:
        query = query.where(SimulationEvent.event_type == event_type)

    query = query.offset(skip).limit(limit).order_by(SimulationEvent.tick.desc())

    result = await session.execute(query)
    return list(result.scalars().all())


@router.get("/{simulation_id}/actions", response_model=list[AgentActionResponse])
async def get_simulation_actions(
    simulation_id: UUID,
    agent_id: UUID | None = None,
    tick: int | None = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    current_user=Depends(get_current_active_user),
    session: AsyncSession = Depends(db_manager.get_session),
) -> list[AgentAction]:
    """Get agent actions in simulation."""
    # First verify simulation exists and belongs to user
    sim_result = await session.execute(
        select(Simulation).where(
            (Simulation.id == simulation_id) & (Simulation.owner_id == current_user.id)
        )
    )
    if not sim_result.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Simulation not found")

    query = select(AgentAction).join(Agent).where(Agent.simulation_id == simulation_id)

    if agent_id:
        query = query.where(AgentAction.agent_id == agent_id)

    if tick is not None:
        query = query.where(AgentAction.tick == tick)

    query = query.offset(skip).limit(limit).order_by(AgentAction.tick.desc())

    result = await session.execute(query)
    return list(result.scalars().all())


@router.delete("/{simulation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_simulation(
    simulation_id: UUID,
    current_user=Depends(get_current_active_user),
    session: AsyncSession = Depends(db_manager.get_session),
) -> None:
    """Delete simulation."""
    result = await session.execute(
        select(Simulation).where(
            (Simulation.id == simulation_id) & (Simulation.owner_id == current_user.id)
        )
    )
    simulation = result.scalar_one_or_none()

    if not simulation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Simulation not found")

    await session.delete(simulation)
    await session.commit()

    logger.info(f"Simulation deleted: {simulation_id}")
