from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.pool import NullPool
from typing import AsyncGenerator, Any
import os

from app.config import settings
from app.models import *  # noqa: F401, F403
from app.models.base import Base

# Create async database engine
engine = create_async_engine(
    settings.DATABASE_URI,
    echo=settings.DEBUG,
    pool_pre_ping=True,
    poolclass=NullPool if settings.TESTING else None,
    pool_size=20 if not settings.TESTING else 5,
    max_overflow=10 if not settings.TESTING else 0,
)

# Create async session factory
async_session_factory = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)

# Dependency to get DB session
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency that provides a database session."""
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception as e:
            await session.rollback()
            raise e
        finally:
            await session.close()

# For synchronous operations (Alembic needs this)
SyncSessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine.sync_engine if hasattr(engine, 'sync_engine') else None,
    future=True
)

def get_sync_db() -> Any:
    """Get a synchronous database session for Alembic."""
    db = SyncSessionLocal()
    try:
        yield db
    finally:
        db.close()