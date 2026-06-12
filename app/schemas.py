"""
Pydantic схемы для валидации данных API.
"""

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from app.models import TaskPriority, TaskStatus


class TaskBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    priority: TaskPriority = TaskPriority.MEDIUM


class TaskCreate(TaskBase):
    """Тело запроса для POST /api/v1/tasks"""


class TaskResponse(TaskBase):
    """Ответ для GET /api/v1/tasks/{task_id} и POST /api/v1/tasks"""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    status: TaskStatus

    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    result: Optional[str] = None
    error_message: Optional[str] = None
    error_details: Optional[str] = None


class TaskStatusResponse(BaseModel):
    """Ответ для GET /api/v1/tasks/{task_id}/status"""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    status: TaskStatus
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


class TaskListResponse(BaseModel):
    """Ответ для GET /api/v1/tasks (пагинация + фильтры)"""

    tasks: list[TaskResponse]
    total: int
    page: int
    size: int
    pages: int


class TaskFilters(BaseModel):
    status: Optional[TaskStatus] = None
    priority: Optional[TaskPriority] = None
    title_contains: Optional[str] = None


class ErrorResponse(BaseModel):
    error: str
    message: str
    details: Optional[str] = None
