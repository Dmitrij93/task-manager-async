import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.models import TaskStatus

# Change import to match worker.py
from app.worker import process_one


@pytest.mark.asyncio
async def test_process_task_success():
    """Тест успешной обработки задачи воркером."""
    task_id = uuid.uuid4()

    # Мокаем зависимости
    mock_task = MagicMock()
    mock_task.id = task_id
    mock_task.status = TaskStatus.PENDING
    mock_task.priority = "MEDIUM"

    # Настройка мока для task_crud
    with patch("app.worker.task_crud") as mock_crud:
        # Используем AsyncMock для асинхронных методов
        mock_crud.get_by_id = AsyncMock(return_value=mock_task)
        mock_crud.update_status = AsyncMock(return_value=mock_task)

        # Мокаем AsyncSessionLocal
        with patch("app.worker.AsyncSessionLocal") as mock_session_local:
            # Настройка мока сессии как контекстного менеджера
            mock_session_local.return_value.__aenter__.return_value = AsyncMock()
            mock_session_local.return_value.__aexit__.return_value = None

            await process_one(task_id)

        # Проверяем, что статус задачи был обновлен
        # Первый вызов - установка IN_PROGRESS
        mock_crud.update_status.assert_any_call(
            mock_session_local.return_value.__aenter__.return_value,
            task_id,
            TaskStatus.IN_PROGRESS,
        )
        # Второй вызов - установка COMPLETED
        mock_crud.update_status.assert_any_call(
            mock_session_local.return_value.__aenter__.return_value,
            task_id,
            TaskStatus.COMPLETED,
            result="выполнено мгновенно",
        )


@pytest.mark.asyncio
async def test_process_task_not_found():
    """Тест обработки несуществующей задачи."""
    task_id = uuid.uuid4()

    with patch("app.worker.task_crud") as mock_crud:
        # Используем AsyncMock для асинхронных методов
        mock_crud.get_by_id = AsyncMock(return_value=None)

        with patch("app.worker.AsyncSessionLocal") as mock_session_local:
            mock_session_local.return_value.__aenter__.return_value = AsyncMock()
            mock_session_local.return_value.__aexit__.return_value = None

            await process_one(task_id)

        # Проверяем, что статус задачи не обновлялся (так как задача не найдена)
        mock_crud.update_status.assert_not_called()
