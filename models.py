from __future__ import annotations

import uuid
from enum import Enum
from typing import Optional

from sqlalchemy import UUID, Column, DateTime
from sqlalchemy import Enum as SAEnum
from sqlalchemy import String, Text, func
from sqlalchemy.orm import declarative_base

# Базовый класс для всех моделей
Base = declarative_base()


class TaskStatus(str, Enum):
    NEW = "NEW"  # новая задача
    PENDING = "PENDING"  # ожидает обработки
    IN_PROGRESS = "IN_PROGRESS"  # в процессе выполнения
    COMPLETED = "COMPLETED"  # завершено успешно
    FAILED = "FAILED"  # завершено с ошибкой
    CANCELLED = "CANCELLED"  # отменено


class TaskPriority(str, Enum):
    LOW = "LOW"  # низкий приоритет
    MEDIUM = "MEDIUM"  # средний приоритет
    HIGH = "HIGH"  # высокий приоритет


class Task(Base):
    __tablename__ = "tasks"

    # Уникальный идентификатор UUID
    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        comment="Уникальный идентификатор задачи",
    )

    # Основная информация о задаче
    title = Column(String(255), nullable=False, comment="Название задачи")

    description = Column(Text, nullable=True, comment="Описание задачи")

    # Приоритет задачи (LOW, MEDIUM, HIGH)
    priority = Column(
        SAEnum(TaskPriority, name="task_priority"),
        nullable=False,
        default=TaskPriority.MEDIUM,
        comment="Приоритет задачи",
    )

    # Статус задачи (NEW, PENDING, IN_PROGRESS, etc.)
    status = Column(
        SAEnum(TaskStatus, name="task_status"),
        nullable=False,
        default=TaskStatus.NEW,
        comment="Текущий статус задачи",
    )

    # Временные метки
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        comment="Время создания задачи",
    )

    started_at = Column(
        DateTime(timezone=True),
        nullable=True,
        comment="Время начала выполнения задачи",
    )

    completed_at = Column(
        DateTime(timezone=True),
        nullable=True,
        comment="Время завершения задачи",
    )

    # Результат выполнения
    result = Column(
        Text,
        nullable=True,
        comment="Результат выполнения задачи (JSON | text)",
    )

    # Информация об ошибках
    error_message = Column(
        Text,
        nullable=True,
        comment="Сообщение об ошибке (если статус FAILED)",
    )

    error_details = Column(
        Text,
        nullable=True,
        comment="Подробная информация об ошибке (traceback и т. д.)",
    )

    def __repr__(self) -> str:
        return f"<Task(id={self.id}, title='{self.title}', " f"status={self.status})>"

    @property
    def is_completed(self) -> bool:
        return self.status in [
            TaskStatus.COMPLETED,
            TaskStatus.FAILED,
            TaskStatus.CANCELLED,
        ]

    @property
    def is_active(self) -> bool:
        return self.status in [TaskStatus.PENDING, TaskStatus.IN_PROGRESS]

    @property
    def processing_time_seconds(self) -> Optional[float]:
        """Возвращает время обработки в секундах (если задача завершена)"""
        if self.started_at and self.completed_at:
            delta = self.completed_at - self.started_at
            return delta.total_seconds()
        return None
