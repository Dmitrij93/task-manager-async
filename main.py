import asyncio
from contextlib import asynccontextmanager
from typing import AsyncGenerator

import uvicorn  # noqa: F401
from fastapi import FastAPI

from api.v1.tasks import router as tasks_router
from config import settings
from database import create_tables
from rabbitmq import rabbitmq

# Таймаут подключения к RabbitMQ при старте API
RABBITMQ_CONNECT_TIMEOUT_SECONDS = 3.0


async def try_connect_rabbitmq() -> None:
    """Подключемся к RabbitMQ, не блокируя запуск API.

    /docs должен открываться даже если брокер ещё не поднялся.
    """
    try:
        await asyncio.wait_for(
            rabbitmq.connect(),
            timeout=RABBITMQ_CONNECT_TIMEOUT_SECONDS,
        )
    except Exception as exc:
        # подключаемся лениво при первом publish.
        print(f"RabbitMQ еще не готов: {exc!r}")
        return None


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    await create_tables()

    await try_connect_rabbitmq()

    yield

    await rabbitmq.close()


app = FastAPI(
    title="Система управления задачами",
    description="Асинхронный сервис управления задачами",
    version="1.0.0",
    lifespan=lifespan,
)

app.include_router(tasks_router)


@app.get("/")
async def root() -> dict[str, str]:
    """Корневой эндпоинт для проверки работоспособности"""
    return {"status": "ok", "environment": settings.environment}


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
    )
