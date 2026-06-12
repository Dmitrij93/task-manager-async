import math
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from crud import task_crud
from database import get_db
from models import Task, TaskPriority, TaskStatus
from rabbitmq import RabbitMQ, rabbitmq
from schemas import (
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


@router.get("", response_model=TaskListResponse)
async def list_tasks(
    db: AsyncSession = Depends(get_db),
    status_: TaskStatus | None = Query(default=None, alias="status"),
    priority: TaskPriority | None = Query(default=None),
    title_contains: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    size: int = Query(default=50, ge=1, le=200),
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


@router.get("/{task_id}", response_model=TaskResponse)
async def get_task(task_id: uuid.UUID, db: AsyncSession = Depends(get_db)) -> Task:
    """Получение детальной информации о задаче по ID"""
    task = await task_crud.get_by_id(db, task_id)
    if task is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Задача не найдена"
        )
    return task


@router.delete("/{task_id}", response_model=TaskStatusResponse)
async def cancel_task(
    task_id: uuid.UUID, db: AsyncSession = Depends(get_db)
) -> TaskStatusResponse:
    """Отмена задачи (DELETE /api/v1/tasks/{task_id})"""
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


@router.get("/{task_id}/status", response_model=TaskStatusResponse)
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
