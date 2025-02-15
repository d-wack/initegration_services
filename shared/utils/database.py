"""
Database utilities for all services.

This module provides database connection and management utilities
that can be used across all microservices.
"""

import contextlib
from typing import Any, AsyncGenerator, Dict, Optional, Type, TypeVar

from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from shared.utils.logging import get_logger

logger = get_logger(__name__)

# Type variable for ORM models
ModelType = TypeVar("ModelType", bound=DeclarativeBase)


class Database:
    """Database connection manager.

    This class manages database connections and sessions for both
    synchronous and asynchronous database operations.

    Attributes:
        engine: SQLAlchemy engine instance
        async_engine: SQLAlchemy async engine instance
        session_factory: Factory for creating new database sessions
        async_session_factory: Factory for creating new async database sessions
    """

    def __init__(
        self,
        database_url: str,
        echo: bool = False,
        pool_size: int = 5,
        max_overflow: int = 10,
        pool_timeout: int = 30,
    ) -> None:
        """Initialize database connection manager.

        Args:
            database_url: Database connection URL
            echo: Whether to echo SQL statements
            pool_size: Size of the connection pool
            max_overflow: Maximum number of connections to create beyond pool_size
            pool_timeout: Number of seconds to wait before giving up on getting a connection
        """
        self.database_url = database_url
        self.echo = echo
        
        # Create engines based on URL scheme
        if database_url.startswith("sqlite"):
            # SQLite specific configuration
            self.engine = create_engine(
                database_url,
                echo=echo,
                connect_args={"check_same_thread": False},
            )
            self.async_engine = create_async_engine(
                database_url.replace("sqlite:", "sqlite+aiosqlite:"),
                echo=echo,
            )
        else:
            # PostgreSQL/MySQL configuration
            self.engine = create_engine(
                database_url,
                echo=echo,
                pool_size=pool_size,
                max_overflow=max_overflow,
                pool_timeout=pool_timeout,
            )
            self.async_engine = create_async_engine(
                database_url.replace("postgresql:", "postgresql+asyncpg:"),
                echo=echo,
                pool_size=pool_size,
                max_overflow=max_overflow,
                pool_timeout=pool_timeout,
            )

        # Create session factories
        self.session_factory = sessionmaker(
            bind=self.engine,
            autocommit=False,
            autoflush=False,
        )
        self.async_session_factory = async_sessionmaker(
            bind=self.async_engine,
            autocommit=False,
            autoflush=False,
        )

    @contextlib.contextmanager
    def get_session(self) -> Session:
        """Get a database session.

        Yields:
            Session: Database session

        Raises:
            Exception: Any exception that occurs during the session
        """
        session = self.session_factory()
        try:
            yield session
            session.commit()
        except Exception as e:
            logger.exception("Error during database session", error=str(e))
            session.rollback()
            raise
        finally:
            session.close()

    @contextlib.asynccontextmanager
    async def get_async_session(self) -> AsyncGenerator[AsyncSession, None]:
        """Get an async database session.

        Yields:
            AsyncSession: Async database session

        Raises:
            Exception: Any exception that occurs during the session
        """
        session = self.async_session_factory()
        try:
            yield session
            await session.commit()
        except Exception as e:
            logger.exception("Error during async database session", error=str(e))
            await session.rollback()
            raise
        finally:
            await session.close()

    async def create_database(self) -> None:
        """Create all database tables."""
        async with self.async_engine.begin() as conn:
            await conn.run_sync(DeclarativeBase.metadata.create_all)

    async def drop_database(self) -> None:
        """Drop all database tables."""
        async with self.async_engine.begin() as conn:
            await conn.run_sync(DeclarativeBase.metadata.drop_all)


class BaseRepository:
    """Base repository for database operations.

    This class provides basic CRUD operations that can be inherited
    by specific repository implementations.

    Attributes:
        db: Database instance
        model: SQLAlchemy model class
    """

    def __init__(self, db: Database, model: Type[ModelType]) -> None:
        """Initialize repository.

        Args:
            db: Database instance
            model: SQLAlchemy model class
        """
        self.db = db
        self.model = model

    async def create(self, **kwargs: Any) -> ModelType:
        """Create a new record.

        Args:
            **kwargs: Model attributes

        Returns:
            ModelType: Created model instance
        """
        async with self.db.get_async_session() as session:
            instance = self.model(**kwargs)
            session.add(instance)
            await session.commit()
            await session.refresh(instance)
            return instance

    async def get(self, id: Any) -> Optional[ModelType]:
        """Get a record by ID.

        Args:
            id: Record ID

        Returns:
            Optional[ModelType]: Found model instance or None
        """
        async with self.db.get_async_session() as session:
            return await session.get(self.model, id)

    async def update(
        self, id: Any, **kwargs: Any
    ) -> Optional[ModelType]:
        """Update a record.

        Args:
            id: Record ID
            **kwargs: Attributes to update

        Returns:
            Optional[ModelType]: Updated model instance or None
        """
        async with self.db.get_async_session() as session:
            instance = await session.get(self.model, id)
            if instance:
                for key, value in kwargs.items():
                    setattr(instance, key, value)
                await session.commit()
                await session.refresh(instance)
            return instance

    async def delete(self, id: Any) -> bool:
        """Delete a record.

        Args:
            id: Record ID

        Returns:
            bool: True if record was deleted, False otherwise
        """
        async with self.db.get_async_session() as session:
            instance = await session.get(self.model, id)
            if instance:
                await session.delete(instance)
                await session.commit()
                return True
            return False


def get_database(settings: Dict[str, Any]) -> Database:
    """Create a database instance from settings.

    Args:
        settings: Database settings dictionary

    Returns:
        Database: Configured database instance
    """
    return Database(
        database_url=settings["url"],
        echo=settings.get("echo", False),
        pool_size=settings.get("pool_size", 5),
        max_overflow=settings.get("max_overflow", 10),
        pool_timeout=settings.get("pool_timeout", 30),
    ) 