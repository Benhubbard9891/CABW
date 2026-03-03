"""Pydantic schemas for API requests and responses."""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field


# Base schemas
class BaseSchema(BaseModel):
    """Base schema with common configuration."""
    model_config = ConfigDict(from_attributes=True)


# User schemas
class UserCreate(BaseSchema):
    """User creation schema."""
    email: EmailStr
    username: str = Field(..., min_length=3, max_length=100)
    password: str = Field(..., min_length=8)
    full_name: str | None = None


class UserResponse(BaseSchema):
    """User response schema."""
    id: UUID
    email: EmailStr
    username: str
    full_name: str | None
    role: str
    is_active: bool
    is_verified: bool
    created_at: datetime
    last_login: datetime | None


class UserUpdate(BaseSchema):
    """User update schema."""
    full_name: str | None = None
    email: EmailStr | None = None


# Token schemas
class Token(BaseSchema):
    """Token response schema."""
    access_token: str
    token_type: str
    expires_in: int


class TokenData(BaseSchema):
    """Token data schema."""
    user_id: str | None = None


# World schemas
class WorldCreate(BaseSchema):
    """World creation schema."""
    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    width: int = Field(default=10, ge=1, le=1000)
    height: int = Field(default=10, ge=1, le=1000)
    config: dict[str, Any] = Field(default_factory=dict)


class WorldResponse(BaseSchema):
    """World response schema."""
    id: UUID
    name: str
    description: str | None
    version: str
    width: int
    height: int
    config: dict[str, Any]
    is_template: bool
    created_at: datetime
    updated_at: datetime


class ZoneResponse(BaseSchema):
    """Zone response schema."""
    id: UUID
    x: int
    y: int
    terrain: str
    cover: float
    visibility: float
    hazard_type: str | None
    hazard_severity: float
    properties: dict[str, Any]


class WorldObjectResponse(BaseSchema):
    """World object response schema."""
    id: UUID
    object_type: str
    name: str | None
    is_interactable: bool
    tags: list[str]
    properties: dict[str, Any]


# Simulation schemas
class SimulationCreate(BaseSchema):
    """Simulation creation schema."""
    world_id: UUID
    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    tick_rate: float | None = Field(default=None, ge=0.1, le=60)
    max_ticks: int | None = Field(default=None, ge=1, le=1000000)
    config: dict[str, Any] = Field(default_factory=dict)


class SimulationUpdate(BaseSchema):
    """Simulation update schema."""
    name: str | None = None
    description: str | None = None
    config: dict[str, Any] | None = None


class SimulationResponse(BaseSchema):
    """Simulation response schema."""
    id: UUID
    name: str
    description: str | None
    status: str
    world_id: UUID
    tick_rate: float
    max_ticks: int
    current_tick: int
    config: dict[str, Any]
    started_at: datetime | None
    completed_at: datetime | None
    created_at: datetime
    updated_at: datetime
    results: dict[str, Any] | None
    error_message: str | None


class SimulationEventResponse(BaseSchema):
    """Simulation event response schema."""
    id: UUID
    tick: int
    event_type: str
    source_id: UUID | None
    target_id: UUID | None
    data: dict[str, Any]
    priority: int
    created_at: datetime


class AgentActionResponse(BaseSchema):
    """Agent action response schema."""
    id: UUID
    tick: int
    action_type: str
    target_id: UUID | None
    target_zone_id: UUID | None
    params: dict[str, Any]
    cost: float
    approved: bool
    outcome: dict[str, Any] | None
    created_at: datetime


# Agent schemas
class AgentCreate(BaseSchema):
    """Agent creation schema."""
    name: str = Field(..., min_length=1, max_length=255)
    agent_type: str = Field(default="npc")
    zone_id: UUID | None = None

    # OCEAN personality
    openness: float = Field(default=0.5, ge=0, le=1)
    conscientiousness: float = Field(default=0.5, ge=0, le=1)
    extraversion: float = Field(default=0.5, ge=0, le=1)
    agreeableness: float = Field(default=0.5, ge=0, le=1)
    neuroticism: float = Field(default=0.5, ge=0, le=1)

    # PAD emotion
    pleasure: float = Field(default=0, ge=-1, le=1)
    arousal: float = Field(default=0, ge=-1, le=1)
    dominance: float = Field(default=0, ge=-1, le=1)


class AgentResponse(BaseSchema):
    """Agent response schema."""
    id: UUID
    name: str
    agent_type: str
    status: str
    zone_id: UUID | None

    # Vitals
    hp: float
    max_hp: float
    stamina: float
    max_stamina: float
    action_points: float

    # OCEAN
    openness: float
    conscientiousness: float
    extraversion: float
    agreeableness: float
    neuroticism: float

    # PAD
    pleasure: float
    arousal: float
    dominance: float

    # State
    inventory: list[str]
    goals: list[str]
    current_goal: str | None

    created_at: datetime
    updated_at: datetime


class AgentUpdate(BaseSchema):
    """Agent update schema."""
    name: str | None = None
    status: str | None = None
    zone_id: UUID | None = None
    hp: float | None = Field(default=None, ge=0, le=1)
    stamina: float | None = Field(default=None, ge=0, le=1)


class MemoryResponse(BaseSchema):
    """Memory response schema."""
    id: UUID
    content: str
    memory_type: str
    emotional_salience: float
    strength: float
    rehearsal_count: int
    participants: list[str]
    is_forgotten: bool
    created_at: datetime


class RelationshipResponse(BaseSchema):
    """Relationship response schema."""
    id: UUID
    agent_a_id: UUID
    agent_b_id: UUID
    affection: float
    trust: float
    familiarity: float
    respect: float
    commitment: float
    betrayal_scar: float
    romantic_interest: bool
    power_dynamic: float
    stage: str
    interaction_count: int
    positive_interactions: int
    negative_interactions: int
    created_at: datetime


# Constitution schemas
class ConstitutionCreate(BaseSchema):
    """Constitution creation schema."""
    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    version: str = Field(default="1.0.0")
    rules: list[dict[str, Any]] = Field(default_factory=list)


class ConstitutionResponse(BaseSchema):
    """Constitution response schema."""
    id: UUID
    name: str
    description: str | None
    version: str
    is_active: bool
    rules: list[dict[str, Any]]
    created_at: datetime
    updated_at: datetime


# Pagination
class PaginatedResponse(BaseSchema):
    """Paginated response schema."""
    items: list[Any]
    total: int
    skip: int
    limit: int
    has_more: bool


# Error schemas
class ErrorResponse(BaseSchema):
    """Error response schema."""
    error: str
    message: str
    details: dict[str, Any] | None = None
