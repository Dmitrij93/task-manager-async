import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.models import Base

# Используем TestSettings для интеграционных тестов
from test_config import get_integration_test_settings

# Получаем настройки для интеграционных тестов
integration_settings = get_integration_test_settings()


@pytest_asyncio.fixture(scope="function")  # Изменено с "module" на "function"
async def engine():
    """Создает движок базы данных для каждого теста."""
    # Используем URL из TestSettings
    engine = create_async_engine(
        integration_settings.database_url,
        echo=False,
        pool_size=5,
        max_overflow=10,
    )
    # Создаем таблицы перед каждым тестом
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    # Удаляем таблицы после каждого теста
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def db_session(engine):
    """Создает сессию для каждого теста."""
    async_session_maker = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    async with async_session_maker() as session:
        yield session
        # Откатываем транзакцию, если она не была завершена
        if session.in_transaction():
            await session.rollback()


@pytest_asyncio.fixture(scope="function")
async def client(db_session):
    """Асинхронный клиент для тестирования API с подменой зависимостей."""
    from app.api.v1.tasks import get_rabbitmq  # Импортируем функцию get_rabbitmq
    from app.core.database import get_db
    from app.main import app
    from app.core.rabbitmq import RabbitMQ  # Импортируем класс RabbitMQ

    # Переопределяем зависимость get_db для использования тестовой сессии
    async def override_get_db():
        try:
            yield db_session
        finally:
            pass  # Сессия управляется фикстурой db_session

    # Переопределяем зависимость get_rabbitmq для использования нового экземпляра
    async def override_get_rabbitmq():
        # Используем URL из TestSettings для интеграционных тестов
        rabbitmq_instance = RabbitMQ(rabbitmq_url=integration_settings.rabbitmq_url)
        try:
            yield rabbitmq_instance
        finally:
            await rabbitmq_instance.close()

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_rabbitmq] = override_get_rabbitmq

    from httpx import AsyncClient

    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()
