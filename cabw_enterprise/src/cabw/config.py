"""Configuration management for CABW Enterprise."""

from functools import lru_cache
from typing import List, Optional

from pydantic import Field, PostgresDsn, RedisDsn, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class DatabaseSettings(BaseSettings):
    """Database configuration."""
    
    model_config = SettingsConfigDict(env_prefix="DB_")
    
    url: Optional[PostgresDsn] = Field(
        default="postgresql+asyncpg://cabw:cabw@localhost:5432/cabw",
        description="Database connection URL"
    )
    pool_size: int = Field(default=10, ge=1, le=100)
    max_overflow: int = Field(default=20, ge=0, le=100)
    pool_timeout: int = Field(default=30, ge=1, le=300)
    echo: bool = Field(default=False)
    
    @field_validator("url", mode="before")
    @classmethod
    def validate_url(cls, v: Optional[str]) -> Optional[str]:
        """Validate and convert database URL."""
        if v is None:
            return "postgresql+asyncpg://cabw:cabw@localhost:5432/cabw"
        return str(v)


class RedisSettings(BaseSettings):
    """Redis configuration."""
    
    model_config = SettingsConfigDict(env_prefix="REDIS_")
    
    url: RedisDsn = Field(
        default="redis://localhost:6379/0",
        description="Redis connection URL"
    )
    password: Optional[str] = Field(default=None)
    socket_timeout: int = Field(default=5, ge=1, le=60)
    socket_connect_timeout: int = Field(default=5, ge=1, le=60)
    retry_on_timeout: bool = Field(default=True)
    health_check_interval: int = Field(default=30, ge=1, le=300)


class APISettings(BaseSettings):
    """API server configuration."""
    
    model_config = SettingsConfigDict(env_prefix="API_")
    
    host: str = Field(default="0.0.0.0")
    port: int = Field(default=8000, ge=1, le=65535)
    workers: int = Field(default=4, ge=1, le=32)
    reload: bool = Field(default=False)
    log_level: str = Field(default="info", pattern=r"^(debug|info|warning|error|critical)$")
    cors_origins: List[str] = Field(default=["*"])
    cors_allow_credentials: bool = Field(default=True)
    cors_allow_methods: List[str] = Field(default=["*"])
    cors_allow_headers: List[str] = Field(default=["*"])
    request_timeout: int = Field(default=30, ge=1, le=300)
    max_request_size: int = Field(default=10 * 1024 * 1024, ge=1024)  # 10MB


class AuthSettings(BaseSettings):
    """Authentication configuration."""
    
    model_config = SettingsConfigDict(env_prefix="AUTH_")
    
    secret_key: str = Field(
        default="your-secret-key-change-in-production",
        min_length=32
    )
    algorithm: str = Field(default="HS256")
    access_token_expire_minutes: int = Field(default=30, ge=1, le=1440)
    refresh_token_expire_days: int = Field(default=7, ge=1, le=365)
    password_hash_algorithm: str = Field(default="bcrypt")
    password_min_length: int = Field(default=8, ge=4, le=128)
    max_login_attempts: int = Field(default=5, ge=1, le=20)
    login_lockout_minutes: int = Field(default=15, ge=1, le=1440)


class SimulationSettings(BaseSettings):
    """Simulation engine configuration."""
    
    model_config = SettingsConfigDict(env_prefix="SIM_")
    
    tick_rate: float = Field(default=1.0, ge=0.1, le=60.0)
    max_ticks: int = Field(default=10000, ge=100, le=1000000)
    max_agents: int = Field(default=1000, ge=10, le=100000)
    max_zones: int = Field(default=10000, ge=10, le=1000000)
    enable_governance: bool = Field(default=True)
    enable_audit: bool = Field(default=True)
    audit_retention_days: int = Field(default=90, ge=1, le=3650)
    memory_decay_interval: int = Field(default=10, ge=1, le=1000)
    relationship_decay_interval: int = Field(default=50, ge=1, le=10000)
    batch_size: int = Field(default=100, ge=10, le=10000)


class CelerySettings(BaseSettings):
    """Celery worker configuration."""
    
    model_config = SettingsConfigDict(env_prefix="CELERY_")
    
    broker_url: str = Field(default="redis://localhost:6379/1")
    result_backend: str = Field(default="redis://localhost:6379/2")
    task_serializer: str = Field(default="msgpack")
    accept_content: List[str] = Field(default=["msgpack", "json"])
    result_serializer: str = Field(default="msgpack")
    timezone: str = Field(default="UTC")
    enable_utc: bool = Field(default=True)
    task_track_started: bool = Field(default=True)
    task_time_limit: int = Field(default=3600, ge=60, le=86400)
    worker_prefetch_multiplier: int = Field(default=4, ge=1, le=20)
    worker_max_tasks_per_child: int = Field(default=1000, ge=100, le=10000)


class MonitoringSettings(BaseSettings):
    """Monitoring and observability configuration."""
    
    model_config = SettingsConfigDict(env_prefix="MONITORING_")
    
    enabled: bool = Field(default=True)
    metrics_port: int = Field(default=9090, ge=1, le=65535)
    metrics_path: str = Field(default="/metrics")
    tracing_enabled: bool = Field(default=True)
    jaeger_endpoint: Optional[str] = Field(default=None)
    log_level: str = Field(default="INFO", pattern=r"^(DEBUG|INFO|WARNING|ERROR|CRITICAL)$")
    log_format: str = Field(default="json", pattern=r"^(json|text)$")
    enable_access_log: bool = Field(default=True)


class Settings(BaseSettings):
    """Main application settings."""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )
    
    # Application
    app_name: str = Field(default="CABW Enterprise")
    app_version: str = Field(default="3.0.0")
    debug: bool = Field(default=False)
    environment: str = Field(default="development", pattern=r"^(development|staging|production|test)$")
    
    # Sub-configurations
    database: DatabaseSettings = Field(default_factory=DatabaseSettings)
    redis: RedisSettings = Field(default_factory=RedisSettings)
    api: APISettings = Field(default_factory=APISettings)
    auth: AuthSettings = Field(default_factory=AuthSettings)
    simulation: SimulationSettings = Field(default_factory=SimulationSettings)
    celery: CelerySettings = Field(default_factory=CelerySettings)
    monitoring: MonitoringSettings = Field(default_factory=MonitoringSettings)
    
    @property
    def is_development(self) -> bool:
        """Check if running in development mode."""
        return self.environment == "development"
    
    @property
    def is_production(self) -> bool:
        """Check if running in production mode."""
        return self.environment == "production"
    
    @property
    def is_test(self) -> bool:
        """Check if running in test mode."""
        return self.environment == "test"


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


# Global settings instance
settings = get_settings()
