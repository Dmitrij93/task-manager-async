import math
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud import task_crud
from app.core.database import get_db
from app.models import Task, TaskPriority, TaskStatus
from app.core.rabbitmq import RabbitMQ, rabbitmq
from app.schemas import (
    TaskCreate,
    TaskFilters,
    TaskListResponse,
    TaskResponse,
    TaskStatusResponse,
)

router = APIRouter(prefix="/api/v1/tasks", tags=["tasks"])


def get_rabbitmq() -> RabbitMQ:
    """Dependency для получения экземпляра RabbitMQ."""
    return rabbitmq


@router.post(
    "",
    response_model=TaskResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Создание задачи",
    description=(
        "Создает новую задачу с указанными параметрами и "
        "публикует ее в RabbitMQ для обработки."
    ),
)
async def create_task(
    payload: TaskCreate,
    db: AsyncSession = Depends(get_db),
    rabbitmq_client: RabbitMQ = Depends(get_rabbitmq),
) -> Task:
    """Создание новой задачи и публикация в RabbitMQ"""
    new_task = await task_crud.create(db, payload)

    task = await task_crud.update_status(
        db, new_task.id, TaskStatus.PENDING  # type: ignore[arg-type]
    )
    if task is None:
        raise HTTPException(status_code=500, detail="Не удалось обновить статус задачи")

    await rabbitmq_client.publish_task(task.id, task.priority)  # type: ignore[arg-type]

    return task


@router.get(
    "",
    response_model=TaskListResponse,
    summary="Список задач",
    description="Получение списка задач с возможностью фильтрации и пагинации.",
)
async def list_tasks(
    db: AsyncSession = Depends(get_db),
    status_: TaskStatus | None = Query(
        default=None,
        alias="status",
        description="Фильтр по статусу задачи",
    ),
    priority: TaskPriority | None = Query(
        default=None,
        description="Фильтр по приоритету",
    ),
    title_contains: str | None = Query(
        default=None,
        description="Поиск по названию задачи",
    ),
    page: int = Query(default=1, ge=1, description="Номер страницы"),
    size: int = Query(
        default=50,
        ge=1,
        le=200,
        description="Количество элементов на странице",
    ),
) -> TaskListResponse:
    """Получение списка задач с фильтрацией и пагинацией"""
    filters = TaskFilters(
        status=status_, priority=priority, title_contains=title_contains
    )
    tasks, total = await task_crud.get_list(db, filters=filters, page=page, size=size)

    pages = math.ceil(total / size) if total else 0

    # Преобразуем ORM модели в Pydantic схемы
    task_responses = [TaskResponse.model_validate(t) for t in tasks]

    return TaskListResponse(
        tasks=task_responses, total=total, page=page, size=size, pages=pages
    )


@router.get(
    "/{task_id}",
    response_model=TaskResponse,
    summary="Детали задачи",
    description=(
        "Получение детальной информации о задаче по ее уникальному идентификатору."
    ),
)
async def get_task(task_id: uuid.UUID, db: AsyncSession = Depends(get_db)) -> Task:
    """Получение детальной информации о задаче по ID"""
    task = await task_crud.get_by_id(db, task_id)
    if task is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Задача не найдена"
        )
    return task


@router.delete(
    "/{task_id}",
    response_model=TaskStatusResponse,
    summary="Отмена задачи",
    description=(
        "Отменяет задачу, если она еще не завершена "
        "(не в статусе COMPLETED, FAILED или CANCELLED)."
    ),
)
async def cancel_task(
    task_id: uuid.UUID, db: AsyncSession = Depends(get_db)
) -> TaskStatusResponse:
    """Отмена задачи"""
    task = await task_crud.get_by_id(db, task_id)
    if task is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Задача не найдена"
        )

    if task.status in (
        TaskStatus.COMPLETED,
        TaskStatus.FAILED,
        TaskStatus.CANCELLED,
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Невозможно отменить задачу в статусе {task.status}",
        )

    updated = await task_crud.cancel(db, task_id)
    if updated is None:
        raise HTTPException(status_code=500, detail="Не удалось отменить задачу")
    return TaskStatusResponse.model_validate(updated)


@router.get(
    "/{task_id}/status",
    response_model=TaskStatusResponse,
    summary="Статус задачи",
    description="Получение текущего статуса задачи по ее уникальному идентификатору.",
)
async def get_task_status(
    task_id: uuid.UUID, db: AsyncSession = Depends(get_db)
) -> TaskStatusResponse:
    """Получение статуса задачи"""
    task = await task_crud.get_by_id(db, task_id)
    if task is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Задача не найдена"
        )

    return TaskStatusResponse.model_validate(task)
