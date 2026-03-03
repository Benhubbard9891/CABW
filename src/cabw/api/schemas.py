"""Pydantic schemas for API requests and responses."""

from datetime import datetime
from typing import Any, Dict, List, Optional
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
    full_name: Optional[str] = None


class UserResponse(BaseSchema):
    """User response schema."""
    id: UUID
    email: EmailStr
    username: str
    full_name: Optional[str]
    role: str
    is_active: bool
    is_verified: bool
    created_at: datetime
    last_login: Optional[datetime]


class UserUpdate(BaseSchema):
    """User update schema."""
    full_name: Optional[str] = None
    email: Optional[EmailStr] = None


# Token schemas
class Token(BaseSchema):
    """Token response schema."""
    access_token: str
    token_type: str
    expires_in: int


class TokenData(BaseSchema):
    """Token data schema."""
    user_id: Optional[str] = None


# World schemas
class WorldCreate(BaseSchema):
    """World creation schema."""
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    width: int = Field(default=10, ge=1, le=1000)
    height: int = Field(default=10, ge=1, le=1000)
    config: Dict[str, Any] = Field(default_factory=dict)


class WorldResponse(BaseSchema):
    """World response schema."""
    id: UUID
    name: str
    description: Optional[str]
    version: str
    width: int
    height: int
    config: Dict[str, Any]
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
    hazard_type: Optional[str]
    hazard_severity: float
    properties: Dict[str, Any]


class WorldObjectResponse(BaseSchema):
    """World object response schema."""
    id: UUID
    object_type: str
    name: Optional[str]
    is_interactable: bool
    tags: List[str]
    properties: Dict[str, Any]


# Simulation schemas
class SimulationCreate(BaseSchema):
    """Simulation creation schema."""
    world_id: UUID
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    tick_rate: Optional[float] = Field(default=None, ge=0.1, le=60)
    max_ticks: Optional[int] = Field(default=None, ge=1, le=1000000)
    config: Dict[str, Any] = Field(default_factory=dict)


class SimulationUpdate(BaseSchema):
    """Simulation update schema."""
    name: Optional[str] = None
    description: Optional[str] = None
    config: Optional[Dict[str, Any]] = None


class SimulationResponse(BaseSchema):
    """Simulation response schema."""
    id: UUID
    name: str
    description: Optional[str]
    status: str
    world_id: UUID
    tick_rate: float
    max_ticks: int
    current_tick: int
    config: Dict[str, Any]
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime
    results: Optional[Dict[str, Any]]
    error_message: Optional[str]


class SimulationEventResponse(BaseSchema):
    """Simulation event response schema."""
    id: UUID
    tick: int
    event_type: str
    source_id: Optional[UUID]
    target_id: Optional[UUID]
    data: Dict[str, Any]
    priority: int
    created_at: datetime


class AgentActionResponse(BaseSchema):
    """Agent action response schema."""
    id: UUID
    tick: int
    action_type: str
    target_id: Optional[UUID]
    target_zone_id: Optional[UUID]
    params: Dict[str, Any]
    cost: float
    approved: bool
    outcome: Optional[Dict[str, Any]]
    created_at: datetime


# Agent schemas
class AgentCreate(BaseSchema):
    """Agent creation schema."""
    name: str = Field(..., min_length=1, max_length=255)
    agent_type: str = Field(default="npc")
    zone_id: Optional[UUID] = None
    
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
    zone_id: Optional[UUID]
    
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
    inventory: List[str]
    goals: List[str]
    current_goal: Optional[str]
    
    created_at: datetime
    updated_at: datetime


class AgentUpdate(BaseSchema):
    """Agent update schema."""
    name: Optional[str] = None
    status: Optional[str] = None
    zone_id: Optional[UUID] = None
    hp: Optional[float] = Field(default=None, ge=0, le=1)
    stamina: Optional[float] = Field(default=None, ge=0, le=1)


class MemoryResponse(BaseSchema):
    """Memory response schema."""
    id: UUID
    content: str
    memory_type: str
    emotional_salience: float
    strength: float
    rehearsal_count: int
    participants: List[str]
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
    description: Optional[str] = None
    version: str = Field(default="1.0.0")
    rules: List[Dict[str, Any]] = Field(default_factory=list)


class ConstitutionResponse(BaseSchema):
    """Constitution response schema."""
    id: UUID
    name: str
    description: Optional[str]
    version: str
    is_active: bool
    rules: List[Dict[str, Any]]
    created_at: datetime
    updated_at: datetime


# Pagination
class PaginatedResponse(BaseSchema):
    """Paginated response schema."""
    items: List[Any]
    total: int
    skip: int
    limit: int
    has_more: bool


# Error schemas
class ErrorResponse(BaseSchema):
    """Error response schema."""
    error: str
    message: str
    details: Optional[Dict[str, Any]] = None
