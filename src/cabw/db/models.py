"""Database models for CABW Enterprise."""

from datetime import datetime
from enum import Enum
from typing import Any, Optional
from uuid import UUID

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy import (
    Enum as SQLEnum,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from cabw.db.base import Base


class AgentStatus(str, Enum):
    """Agent lifecycle status."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"
    TERMINATED = "terminated"


class SimulationStatus(str, Enum):
    """Simulation run status."""
    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class UserRole(str, Enum):
    """User roles for access control."""
    ADMIN = "admin"
    OPERATOR = "operator"
    VIEWER = "viewer"
    API = "api"


class User(Base):
    """User account model."""

    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    username: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255))
    full_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    role: Mapped[UserRole] = mapped_column(SQLEnum(UserRole), default=UserRole.VIEWER)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    last_login: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # Relationships
    simulations: Mapped[list["Simulation"]] = relationship(
        back_populates="owner",
        lazy="selectin"
    )
    api_keys: Mapped[list["APIKey"]] = relationship(
        back_populates="user",
        lazy="selectin"
    )


class APIKey(Base):
    """API key for programmatic access."""

    __tablename__ = "api_keys"

    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    key_hash: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(100))
    scopes: Mapped[list[str]] = mapped_column(JSON, default=list)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    is_revoked: Mapped[bool] = mapped_column(Boolean, default=False)

    # Relationships
    user: Mapped["User"] = relationship(back_populates="api_keys")


class World(Base):
    """World definition containing zones and configuration."""

    __tablename__ = "worlds"

    name: Mapped[str] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    version: Mapped[str] = mapped_column(String(50), default="1.0.0")
    config: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    width: Mapped[int] = mapped_column(Integer, default=10)
    height: Mapped[int] = mapped_column(Integer, default=10)
    is_template: Mapped[bool] = mapped_column(Boolean, default=False)

    # Relationships
    zones: Mapped[list["Zone"]] = relationship(
        back_populates="world",
        lazy="selectin",
        cascade="all, delete-orphan"
    )
    simulations: Mapped[list["Simulation"]] = relationship(
        back_populates="world",
        lazy="selectin"
    )


class Zone(Base):
    """Zone within a world."""

    __tablename__ = "zones"
    __table_args__ = (
        UniqueConstraint("world_id", "x", "y", name="uq_zone_position"),
        Index("ix_zone_world_position", "world_id", "x", "y"),
    )

    world_id: Mapped[UUID] = mapped_column(ForeignKey("worlds.id", ondelete="CASCADE"))
    x: Mapped[int] = mapped_column(Integer)
    y: Mapped[int] = mapped_column(Integer)
    terrain: Mapped[str] = mapped_column(String(50), default="grass")
    cover: Mapped[float] = mapped_column(Float, default=0.5)
    visibility: Mapped[float] = mapped_column(Float, default=0.5)
    hazard_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    hazard_severity: Mapped[float] = mapped_column(Float, default=0.0)
    properties: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)

    # Relationships
    world: Mapped["World"] = relationship(back_populates="zones")
    objects: Mapped[list["WorldObject"]] = relationship(
        back_populates="zone",
        lazy="selectin",
        cascade="all, delete-orphan"
    )


class WorldObject(Base):
    """Object placed in a zone."""

    __tablename__ = "world_objects"

    zone_id: Mapped[UUID] = mapped_column(ForeignKey("zones.id", ondelete="CASCADE"))
    object_type: Mapped[str] = mapped_column(String(50))
    name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_interactable: Mapped[bool] = mapped_column(Boolean, default=True)
    tags: Mapped[list[str]] = mapped_column(JSON, default=list)
    properties: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)

    # Relationships
    zone: Mapped["Zone"] = relationship(back_populates="objects")


class Agent(Base):
    """Agent definition and state."""

    __tablename__ = "agents"

    simulation_id: Mapped[UUID] = mapped_column(ForeignKey("simulations.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(String(255))
    agent_type: Mapped[str] = mapped_column(String(50), default="npc")
    status: Mapped[AgentStatus] = mapped_column(SQLEnum(AgentStatus), default=AgentStatus.ACTIVE)

    # Position
    zone_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("zones.id", ondelete="SET NULL"),
        nullable=True
    )

    # Vitals
    hp: Mapped[float] = mapped_column(Float, default=1.0)
    max_hp: Mapped[float] = mapped_column(Float, default=1.0)
    stamina: Mapped[float] = mapped_column(Float, default=1.0)
    max_stamina: Mapped[float] = mapped_column(Float, default=1.0)
    action_points: Mapped[float] = mapped_column(Float, default=1.0)

    # Psychology (OCEAN)
    openness: Mapped[float] = mapped_column(Float, default=0.5)
    conscientiousness: Mapped[float] = mapped_column(Float, default=0.5)
    extraversion: Mapped[float] = mapped_column(Float, default=0.5)
    agreeableness: Mapped[float] = mapped_column(Float, default=0.5)
    neuroticism: Mapped[float] = mapped_column(Float, default=0.5)

    # Emotion (PAD)
    pleasure: Mapped[float] = mapped_column(Float, default=0.0)
    arousal: Mapped[float] = mapped_column(Float, default=0.0)
    dominance: Mapped[float] = mapped_column(Float, default=0.0)

    # State
    inventory: Mapped[list[str]] = mapped_column(JSON, default=list)
    goals: Mapped[list[str]] = mapped_column(JSON, default=list)
    current_goal: Mapped[str | None] = mapped_column(String(255), nullable=True)
    properties: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)

    # Relationships
    simulation: Mapped["Simulation"] = relationship(back_populates="agents")
    memories: Mapped[list["Memory"]] = relationship(
        back_populates="agent",
        lazy="selectin",
        cascade="all, delete-orphan"
    )
    actions: Mapped[list["AgentAction"]] = relationship(
        back_populates="agent",
        lazy="selectin",
        cascade="all, delete-orphan"
    )


class Memory(Base):
    """Agent memory trace."""

    __tablename__ = "memories"
    __table_args__ = (
        Index("ix_memory_agent_strength", "agent_id", "strength"),
        Index("ix_memory_type", "memory_type"),
    )

    agent_id: Mapped[UUID] = mapped_column(ForeignKey("agents.id", ondelete="CASCADE"))
    content: Mapped[str] = mapped_column(Text)
    memory_type: Mapped[str] = mapped_column(String(50), default="observation")
    emotional_salience: Mapped[float] = mapped_column(Float, default=0.5)
    strength: Mapped[float] = mapped_column(Float, default=1.0)
    rehearsal_count: Mapped[int] = mapped_column(Integer, default=0)
    participants: Mapped[list[str]] = mapped_column(JSON, default=list)
    is_forgotten: Mapped[bool] = mapped_column(Boolean, default=False)

    # Relationships
    agent: Mapped["Agent"] = relationship(back_populates="memories")


class Relationship(Base):
    """Relationship between two agents."""

    __tablename__ = "relationships"
    __table_args__ = (
        UniqueConstraint("agent_a_id", "agent_b_id", name="uq_relationship_pair"),
        Index("ix_relationship_agent_a", "agent_a_id"),
        Index("ix_relationship_agent_b", "agent_b_id"),
    )

    agent_a_id: Mapped[UUID] = mapped_column(ForeignKey("agents.id", ondelete="CASCADE"))
    agent_b_id: Mapped[UUID] = mapped_column(ForeignKey("agents.id", ondelete="CASCADE"))

    # Metrics
    affection: Mapped[float] = mapped_column(Float, default=0.0)
    trust: Mapped[float] = mapped_column(Float, default=0.5)
    familiarity: Mapped[float] = mapped_column(Float, default=0.0)
    respect: Mapped[float] = mapped_column(Float, default=0.5)
    commitment: Mapped[float] = mapped_column(Float, default=0.0)

    # Special states
    betrayal_scar: Mapped[float] = mapped_column(Float, default=0.0)
    romantic_interest: Mapped[bool] = mapped_column(Boolean, default=False)
    power_dynamic: Mapped[float] = mapped_column(Float, default=0.0)
    stage: Mapped[str] = mapped_column(String(50), default="stranger")

    # Statistics
    interaction_count: Mapped[int] = mapped_column(Integer, default=0)
    positive_interactions: Mapped[int] = mapped_column(Integer, default=0)
    negative_interactions: Mapped[int] = mapped_column(Integer, default=0)


class Simulation(Base):
    """Simulation run."""

    __tablename__ = "simulations"
    __table_args__ = (
        Index("ix_simulation_status", "status"),
        Index("ix_simulation_owner", "owner_id"),
    )

    owner_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    world_id: Mapped[UUID] = mapped_column(ForeignKey("worlds.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[SimulationStatus] = mapped_column(
        SQLEnum(SimulationStatus),
        default=SimulationStatus.PENDING
    )

    # Configuration
    config: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    tick_rate: Mapped[float] = mapped_column(Float, default=1.0)
    max_ticks: Mapped[int] = mapped_column(Integer, default=1000)

    # Progress
    current_tick: Mapped[int] = mapped_column(Integer, default=0)
    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # Results
    results: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    owner: Mapped["User"] = relationship(back_populates="simulations")
    world: Mapped["World"] = relationship(back_populates="simulations")
    agents: Mapped[list["Agent"]] = relationship(
        back_populates="simulation",
        lazy="selectin",
        cascade="all, delete-orphan"
    )
    events: Mapped[list["SimulationEvent"]] = relationship(
        back_populates="simulation",
        lazy="selectin",
        cascade="all, delete-orphan"
    )
    audit_records: Mapped[list["AuditRecord"]] = relationship(
        back_populates="simulation",
        lazy="selectin",
        cascade="all, delete-orphan"
    )


class SimulationEvent(Base):
    """Event occurring during simulation."""

    __tablename__ = "simulation_events"
    __table_args__ = (
        Index("ix_event_simulation_tick", "simulation_id", "tick"),
        Index("ix_event_type", "event_type"),
    )

    simulation_id: Mapped[UUID] = mapped_column(ForeignKey("simulations.id", ondelete="CASCADE"))
    tick: Mapped[int] = mapped_column(Integer)
    event_type: Mapped[str] = mapped_column(String(100))
    source_id: Mapped[UUID | None] = mapped_column(ForeignKey("agents.id"), nullable=True)
    target_id: Mapped[UUID | None] = mapped_column(ForeignKey("agents.id"), nullable=True)
    data: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    priority: Mapped[int] = mapped_column(Integer, default=0)

    # Relationships
    simulation: Mapped["Simulation"] = relationship(back_populates="events")


class AgentAction(Base):
    """Action taken by an agent."""

    __tablename__ = "agent_actions"
    __table_args__ = (
        Index("ix_action_agent_tick", "agent_id", "tick"),
        Index("ix_action_type", "action_type"),
    )

    agent_id: Mapped[UUID] = mapped_column(ForeignKey("agents.id", ondelete="CASCADE"))
    tick: Mapped[int] = mapped_column(Integer)
    action_type: Mapped[str] = mapped_column(String(100))
    target_id: Mapped[UUID | None] = mapped_column(ForeignKey("agents.id"), nullable=True)
    target_zone_id: Mapped[UUID | None] = mapped_column(ForeignKey("zones.id"), nullable=True)
    params: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    cost: Mapped[float] = mapped_column(Float, default=0.0)
    approved: Mapped[bool] = mapped_column(Boolean, default=True)
    outcome: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)

    # Relationships
    agent: Mapped["Agent"] = relationship(back_populates="actions")


class AuditRecord(Base):
    """Governance audit record."""

    __tablename__ = "audit_records"
    __table_args__ = (
        Index("ix_audit_simulation_tick", "simulation_id", "tick"),
        Index("ix_audit_agent", "agent_id"),
    )

    simulation_id: Mapped[UUID] = mapped_column(ForeignKey("simulations.id", ondelete="CASCADE"))
    tick: Mapped[int] = mapped_column(Integer)
    agent_id: Mapped[UUID] = mapped_column(ForeignKey("agents.id", ondelete="CASCADE"))
    action_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("agent_actions.id"),
        nullable=True
    )

    # Decision
    decision_type: Mapped[str] = mapped_column(String(50))
    approved: Mapped[bool] = mapped_column(Boolean, default=True)
    violations: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    permits: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)

    # Agent state snapshot
    agent_state: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)

    # Relationships
    simulation: Mapped["Simulation"] = relationship(back_populates="audit_records")


class Constitution(Base):
    """Constitutional constraints definition."""

    __tablename__ = "constitutions"

    name: Mapped[str] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    version: Mapped[str] = mapped_column(String(50), default="1.0.0")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    rules: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)

    # Relationships
    simulations: Mapped[list["Simulation"]] = relationship(
        back_populates="constitution",
        lazy="selectin"
    )


# Add constitution relationship to Simulation
Simulation.constitution_id: Mapped[UUID | None] = mapped_column(
    ForeignKey("constitutions.id"),
    nullable=True
)
Simulation.constitution: Mapped[Optional["Constitution"]] = relationship(
    back_populates="simulations"
)
