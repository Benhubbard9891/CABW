"""Database models for CABW Enterprise."""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Enum as SQLEnum,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
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
    
    # Required fields first
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    username: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255))
    
    # Optional fields with defaults
    role: Mapped[UserRole] = mapped_column(SQLEnum(UserRole), default=UserRole.VIEWER)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    full_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, default=None)
    last_login: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True, default=None)
    
    # Relationships
    simulations: Mapped[List["Simulation"]] = relationship(
        back_populates="owner",
        lazy="selectin",
        init=False,
        default_factory=list
    )
    api_keys: Mapped[List["APIKey"]] = relationship(
        back_populates="user",
        lazy="selectin",
        init=False,
        default_factory=list
    )


class APIKey(Base):
    """API key for programmatic access."""
    
    __tablename__ = "api_keys"
    
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    key_hash: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(100))
    
    is_revoked: Mapped[bool] = mapped_column(Boolean, default=False)
    scopes: Mapped[List[str]] = mapped_column(JSON, default_factory=list)
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True, default=None)
    last_used_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True, default=None)
    
    # Relationships
    user: Mapped["User"] = relationship(back_populates="api_keys", init=False)


class World(Base):
    """World definition containing zones and configuration."""
    
    __tablename__ = "worlds"
    
    name: Mapped[str] = mapped_column(String(255))
    
    version: Mapped[str] = mapped_column(String(50), default="1.0.0")
    width: Mapped[int] = mapped_column(Integer, default=10)
    height: Mapped[int] = mapped_column(Integer, default=10)
    is_template: Mapped[bool] = mapped_column(Boolean, default=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True, default=None)
    config: Mapped[Dict[str, Any]] = mapped_column(JSON, default_factory=dict)
    
    # Relationships
    zones: Mapped[List["Zone"]] = relationship(
        back_populates="world",
        lazy="selectin",
        cascade="all, delete-orphan",
        init=False,
        default_factory=list
    )
    simulations: Mapped[List["Simulation"]] = relationship(
        back_populates="world",
        lazy="selectin",
        init=False,
        default_factory=list
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
    hazard_severity: Mapped[float] = mapped_column(Float, default=0.0)
    hazard_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, default=None)
    properties: Mapped[Dict[str, Any]] = mapped_column(JSON, default_factory=dict)
    
    # Relationships
    world: Mapped["World"] = relationship(back_populates="zones", init=False)
    objects: Mapped[List["WorldObject"]] = relationship(
        back_populates="zone",
        lazy="selectin",
        cascade="all, delete-orphan",
        init=False,
        default_factory=list
    )


class WorldObject(Base):
    """Object placed in a zone."""
    
    __tablename__ = "world_objects"
    
    zone_id: Mapped[UUID] = mapped_column(ForeignKey("zones.id", ondelete="CASCADE"))
    object_type: Mapped[str] = mapped_column(String(50))
    
    is_interactable: Mapped[bool] = mapped_column(Boolean, default=True)
    name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, default=None)
    tags: Mapped[List[str]] = mapped_column(JSON, default_factory=list)
    properties: Mapped[Dict[str, Any]] = mapped_column(JSON, default_factory=dict)
    
    # Relationships
    zone: Mapped["Zone"] = relationship(back_populates="objects", init=False)


class Agent(Base):
    """Agent definition and state."""
    
    __tablename__ = "agents"
    
    simulation_id: Mapped[UUID] = mapped_column(ForeignKey("simulations.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(String(255))
    
    agent_type: Mapped[str] = mapped_column(String(50), default="npc")
    status: Mapped[AgentStatus] = mapped_column(SQLEnum(AgentStatus), default=AgentStatus.ACTIVE)
    
    # Position
    zone_id: Mapped[Optional[UUID]] = mapped_column(
        ForeignKey("zones.id", ondelete="SET NULL"),
        nullable=True,
        default=None
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
    inventory: Mapped[List[str]] = mapped_column(JSON, default_factory=list)
    goals: Mapped[List[str]] = mapped_column(JSON, default_factory=list)
    current_goal: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, default=None)
    properties: Mapped[Dict[str, Any]] = mapped_column(JSON, default_factory=dict)
    
    # Relationships
    simulation: Mapped["Simulation"] = relationship(back_populates="agents", init=False)
    memories: Mapped[List["Memory"]] = relationship(
        back_populates="agent",
        lazy="selectin",
        cascade="all, delete-orphan",
        init=False,
        default_factory=list
    )
    actions: Mapped[List["AgentAction"]] = relationship(
        back_populates="agent",
        lazy="selectin",
        cascade="all, delete-orphan",
        init=False,
        default_factory=list
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
    is_forgotten: Mapped[bool] = mapped_column(Boolean, default=False)
    participants: Mapped[List[str]] = mapped_column(JSON, default_factory=list)
    
    # Relationships
    agent: Mapped["Agent"] = relationship(back_populates="memories", init=False)


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
    
    status: Mapped[SimulationStatus] = mapped_column(
        SQLEnum(SimulationStatus),
        default=SimulationStatus.PENDING
    )
    
    # Configuration
    tick_rate: Mapped[float] = mapped_column(Float, default=1.0)
    max_ticks: Mapped[int] = mapped_column(Integer, default=1000)
    current_tick: Mapped[int] = mapped_column(Integer, default=0)
    config: Mapped[Dict[str, Any]] = mapped_column(JSON, default_factory=dict)
    
    # Progress
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True, default=None)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True, default=None)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True, default=None)
    
    # Results
    results: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True, default=None)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True, default=None)
    
    # Relationships
    owner: Mapped["User"] = relationship(back_populates="simulations", init=False)
    world: Mapped["World"] = relationship(back_populates="simulations", init=False)
    agents: Mapped[List["Agent"]] = relationship(
        back_populates="simulation",
        lazy="selectin",
        cascade="all, delete-orphan",
        init=False,
        default_factory=list
    )
    events: Mapped[List["SimulationEvent"]] = relationship(
        back_populates="simulation",
        lazy="selectin",
        cascade="all, delete-orphan",
        init=False,
        default_factory=list
    )
    audit_records: Mapped[List["AuditRecord"]] = relationship(
        back_populates="simulation",
        lazy="selectin",
        cascade="all, delete-orphan",
        init=False,
        default_factory=list
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
    
    priority: Mapped[int] = mapped_column(Integer, default=0)
    source_id: Mapped[Optional[UUID]] = mapped_column(ForeignKey("agents.id"), nullable=True, default=None)
    target_id: Mapped[Optional[UUID]] = mapped_column(ForeignKey("agents.id"), nullable=True, default=None)
    data: Mapped[Dict[str, Any]] = mapped_column(JSON, default_factory=dict)
    
    # Relationships
    simulation: Mapped["Simulation"] = relationship(back_populates="events", init=False)


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
    
    cost: Mapped[float] = mapped_column(Float, default=0.0)
    approved: Mapped[bool] = mapped_column(Boolean, default=True)
    target_id: Mapped[Optional[UUID]] = mapped_column(ForeignKey("agents.id"), nullable=True, default=None)
    target_zone_id: Mapped[Optional[UUID]] = mapped_column(ForeignKey("zones.id"), nullable=True, default=None)
    params: Mapped[Dict[str, Any]] = mapped_column(JSON, default_factory=dict)
    outcome: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True, default=None)
    
    # Relationships
    agent: Mapped["Agent"] = relationship(back_populates="actions", init=False)


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
    
    # Decision
    decision_type: Mapped[str] = mapped_column(String(50))
    approved: Mapped[bool] = mapped_column(Boolean, default=True)
    action_id: Mapped[Optional[UUID]] = mapped_column(
        ForeignKey("agent_actions.id"),
        nullable=True,
        default=None
    )
    violations: Mapped[List[Dict[str, Any]]] = mapped_column(JSON, default_factory=list)
    permits: Mapped[List[Dict[str, Any]]] = mapped_column(JSON, default_factory=list)
    
    # Agent state snapshot
    agent_state: Mapped[Dict[str, Any]] = mapped_column(JSON, default_factory=dict)
    
    # Relationships
    simulation: Mapped["Simulation"] = relationship(back_populates="audit_records", init=False)


class Constitution(Base):
    """Constitutional constraints definition."""
    
    __tablename__ = "constitutions"
    
    name: Mapped[str] = mapped_column(String(255))
    
    version: Mapped[str] = mapped_column(String(50), default="1.0.0")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True, default=None)
    rules: Mapped[List[Dict[str, Any]]] = mapped_column(JSON, default_factory=list)
    
    # Relationships
    simulations: Mapped[List["Simulation"]] = relationship(
        back_populates="constitution",
        lazy="selectin",
        init=False,
        default_factory=list
    )


# Add constitution relationship to Simulation
Simulation.constitution_id: Mapped[Optional[UUID]] = mapped_column(
    ForeignKey("constitutions.id"),
    nullable=True,
    default=None
)
Simulation.constitution: Mapped[Optional["Constitution"]] = relationship(
    back_populates="simulations",
    init=False
)
