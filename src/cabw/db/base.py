"""Database base models and utilities."""

from collections.abc import AsyncGenerator
from datetime import datetime
from typing import Any, TypeVar
from uuid import UUID, uuid4

from sqlalchemy import MetaData
from sqlalchemy.ext.asyncio import (
    AsyncAttrs,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    MappedAsDataclass,
    declared_attr,
    mapped_column,
)

from cabw.config import settings

# Naming convention for constraints
convention = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}

metadata = MetaData(naming_convention=convention)


class Base(DeclarativeBase, AsyncAttrs, MappedAsDataclass):
    """Base class for all database models."""

    metadata = metadata

    # Common columns for all tables
    id: Mapped[UUID] = mapped_column(
        primary_key=True,
        default_factory=uuid4,
        sort_order=-100
    )
    created_at: Mapped[datetime] = mapped_column(
        default_factory=datetime.utcnow,
        sort_order=-99
    )
    updated_at: Mapped[datetime] = mapped_column(
        default_factory=datetime.utcnow,
        onupdate=datetime.utcnow,
        sort_order=-98
    )

    @declared_attr.directive
    def __tablename__(self) -> str:
        """Generate table name from class name."""
        return self.__name__.lower()

    def to_dict(self, exclude: list[str] | None = None) -> dict[str, Any]:
        """Convert model to dictionary."""
        exclude = exclude or []
        result = {}
        for column in self.__table__.columns:
            if column.name not in exclude:
                value = getattr(self, column.name)
                if isinstance(value, UUID):
                    value = str(value)
                elif isinstance(value, datetime):
                    value = value.isoformat()
                result[column.name] = value
        return result


# Type variable for generic queries
T = TypeVar("T", bound=Base)


class DatabaseManager:
    """Database connection manager."""

    def __init__(self) -> None:
        """Initialize database manager."""
        self.engine = create_async_engine(
            str(settings.database.url),
            pool_size=settings.database.pool_size,
            max_overflow=settings.database.max_overflow,
            pool_timeout=settings.database.pool_timeout,
            echo=settings.database.echo,
        )
        self.async_session = async_sessionmaker(
            self.engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autocommit=False,
            autoflush=False,
        )

    async def get_session(self) -> AsyncGenerator[AsyncSession, None]:
        """Get database session."""
        async with self.async_session() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()

    async def create_tables(self) -> None:
        """Create all database tables."""
        async with self.engine.begin() as conn:
            await conn.run_sync(metadata.create_all)

    async def drop_tables(self) -> None:
        """Drop all database tables."""
        async with self.engine.begin() as conn:
            await conn.run_sync(metadata.drop_all)

    async def close(self) -> None:
        """Close database connections."""
        await self.engine.dispose()


# Global database manager instance
db_manager = DatabaseManager()
