from typing import AsyncGenerator, Optional, cast

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import settings
from app.models import Base

# Глобальные переменные для отложенной инициализации
_engine: Optional[AsyncEngine] = None
_AsyncSessionLocal: Optional[async_sessionmaker] = None


def get_engine() -> AsyncEngine:
    """Возвращает экземпляр движка базы данных (создает при первом вызове)."""
    global _engine
    if _engine is None:
        _engine = create_async_engine(
            settings.database_url,
            echo=settings.debug,
            pool_size=20,
            max_overflow=30,
            pool_pre_ping=True,
            pool_recycle=3600,
        )
    return _engine


def get_sessionmaker() -> async_sessionmaker:
    """Возвращает фабрику сессий (создает при первом вызове)."""
    global _AsyncSessionLocal
    if _AsyncSessionLocal is None:
        engine = get_engine()
        _AsyncSessionLocal = async_sessionmaker(
            engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )
    return _AsyncSessionLocal


# Для обратной совместимости в коде приложения используем псевдонимы
engine = get_engine()
AsyncSessionLocal: async_sessionmaker = get_sessionmaker()


async def create_tables() -> None:
    """Создание всех таблиц в базе данных"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def drop_tables() -> None:
    """Удаление всех таблиц (для тестов)"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency для получения сессии базы данных в FastAPI endpoints
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


# Для тестов - получение сессии без dependency injection
async def get_test_db_session() -> AsyncSession:
    """Получение сессии БД для тестов"""
    return cast(AsyncSession, AsyncSessionLocal())
