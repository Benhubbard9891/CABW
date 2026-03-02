"""Database models for CABW using SQLAlchemy."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Dict, Optional

try:
    from sqlalchemy import (
        JSON,
        Boolean,
        Column,
        DateTime,
        Float,
        ForeignKey,
        Integer,
        String,
        Text,
    )
    from sqlalchemy.orm import DeclarativeBase, relationship

    class Base(DeclarativeBase):
        """Shared declarative base for all CABW ORM models."""


    class SimulationRun(Base):
        """Persists metadata about a simulation run."""

        __tablename__ = "simulation_runs"

        id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
        name = Column(String(256), nullable=False)
        created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
        started_at = Column(DateTime, nullable=True)
        finished_at = Column(DateTime, nullable=True)
        max_ticks = Column(Integer, default=1000)
        world_width = Column(Integer, default=50)
        world_height = Column(Integer, default=50)
        random_seed = Column(Integer, nullable=True)
        status = Column(String(32), default="pending")   # pending / running / completed / failed
        config_json = Column(JSON, nullable=True)

        agents = relationship("AgentRecord", back_populates="simulation", cascade="all, delete-orphan")
        snapshots = relationship("SimulationSnapshot", back_populates="simulation", cascade="all, delete-orphan")

        def __repr__(self) -> str:
            return f"<SimulationRun id={self.id!r} name={self.name!r} status={self.status!r}>"


    class AgentRecord(Base):
        """Persists an agent and its final state."""

        __tablename__ = "agents"

        id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
        simulation_id = Column(String(36), ForeignKey("simulation_runs.id"), nullable=False)
        agent_type = Column(String(128), nullable=False, default="IntegratedAgent")
        created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
        alive = Column(Boolean, default=True)
        energy = Column(Float, default=100.0)
        pos_x = Column(Float, default=0.0)
        pos_y = Column(Float, default=0.0)
        emotion_pleasure = Column(Float, default=0.0)
        emotion_arousal = Column(Float, default=0.0)
        emotion_dominance = Column(Float, default=0.0)
        team_name = Column(String(256), nullable=True)
        metadata_json = Column(JSON, nullable=True)

        simulation = relationship("SimulationRun", back_populates="agents")

        def __repr__(self) -> str:
            return f"<AgentRecord id={self.id!r} alive={self.alive}>"


    class SimulationSnapshot(Base):
        """Stores a point-in-time snapshot of the simulation state."""

        __tablename__ = "simulation_snapshots"

        id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
        simulation_id = Column(String(36), ForeignKey("simulation_runs.id"), nullable=False)
        tick = Column(Integer, nullable=False)
        recorded_at = Column(DateTime, default=datetime.utcnow, nullable=False)
        state_json = Column(JSON, nullable=False)

        simulation = relationship("SimulationRun", back_populates="snapshots")

        def __repr__(self) -> str:
            return f"<SimulationSnapshot sim={self.simulation_id!r} tick={self.tick}>"


    class AuditEntry(Base):
        """Stores audit log entries from the security governance layer."""

        __tablename__ = "audit_entries"

        id = Column(Integer, primary_key=True, autoincrement=True)
        timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)
        event_type = Column(String(128), nullable=False)
        principal_id = Column(String(256), nullable=False)
        resource = Column(String(256), nullable=False)
        success = Column(Boolean, nullable=False)
        details_json = Column(JSON, nullable=True)

        def __repr__(self) -> str:
            return (
                f"<AuditEntry event={self.event_type!r} "
                f"principal={self.principal_id!r} success={self.success}>"
            )

except ImportError:  # SQLAlchemy not installed – provide lightweight stubs
    class Base:  # type: ignore[no-redef]
        """Stub base when SQLAlchemy is unavailable."""

    class SimulationRun:  # type: ignore[no-redef]
        """Stub model."""

    class AgentRecord:  # type: ignore[no-redef]
        """Stub model."""

    class SimulationSnapshot:  # type: ignore[no-redef]
        """Stub model."""

    class AuditEntry:  # type: ignore[no-redef]
        """Stub model."""
