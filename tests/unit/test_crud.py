import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest
import sqlalchemy as sa

from app.crud import task_crud
from app.models import Task, TaskPriority, TaskStatus
from app.schemas import TaskCreate, TaskFilters


@pytest.fixture
def mock_session():
    """Создает мок асинхронной сессии базы данных."""
    session = AsyncMock()
    session.execute = AsyncMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()
    session.rollback = AsyncMock()
    session.close = AsyncMock()
    session.add = MagicMock()
    return session


@pytest.mark.asyncio
async def test_create_task(mock_session):
    """Тест создания задачи через CRUD."""

    task_data = TaskCreate(
        title="Test Task", description="Test Description", priority=TaskPriority.HIGH
    )

    # Мокаем возвращаемый объект Task (который вернет refresh)
    mock_task = MagicMock(spec=Task)
    mock_task.id = uuid.uuid4()
    mock_task.title = task_data.title
    mock_task.description = task_data.description
    mock_task.priority = task_data.priority
    mock_task.status = TaskStatus.NEW

    # Настройка мока сессии
    mock_session.refresh.return_value = mock_task

    result = await task_crud.create(mock_session, task_data)

    # Проверяем, что задача создана с правильными полями
    assert result.title == "Test Task"
    assert result.description == "Test Description"
    assert result.priority == TaskPriority.HIGH
    assert result.status == TaskStatus.NEW

    # Проверяем, что сессия использовалась правильно
    mock_session.add.assert_called_once()
    mock_session.commit.assert_called_once()
    mock_session.refresh.assert_called_once()


@pytest.mark.asyncio
async def test_get_by_id(mock_session):
    """Тест получения задачи по ID."""
    task_id = uuid.uuid4()

    # Мокаем задачу
    mock_task = MagicMock(spec=Task)
    mock_task.id = task_id
    mock_task.title = "Test Task"

    # Мокаем результат выполнения запроса
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_task
    mock_session.execute.return_value = mock_result

    result = await task_crud.get_by_id(mock_session, task_id)

    # Проверяем, что задача найдена
    assert result == mock_task

    # Проверяем, что execute был вызван с правильным запросом
    mock_session.execute.assert_called_once()
    call_args = mock_session.execute.call_args[0]
    query = call_args[0]
    assert isinstance(query, sa.sql.selectable.Select)


@pytest.mark.asyncio
async def test_get_list_with_filters(mock_session):
    """Тест получения списка задач с фильтрацией."""
    # Мокаем задачи
    mock_task1 = MagicMock(spec=Task)
    mock_task1.id = uuid.uuid4()
    mock_task1.title = "Task 1"
    mock_task1.status = TaskStatus.PENDING
    mock_task1.priority = TaskPriority.HIGH

    mock_task2 = MagicMock(spec=Task)
    mock_task2.id = uuid.uuid4()
    mock_task2.title = "Task 2"
    mock_task2.status = TaskStatus.PENDING
    mock_task2.priority = TaskPriority.MEDIUM

    # Мокаем результаты выполнения запросов
    mock_tasks_result = MagicMock()
    mock_tasks_result.scalars.return_value.all.return_value = [mock_task1, mock_task2]

    mock_count_result = MagicMock()
    mock_count_result.scalar.return_value = 2

    # Настройка мока сессии
    mock_session.execute.side_effect = [mock_tasks_result, mock_count_result]

    # Создаем фильтры
    filters = TaskFilters(
        status=TaskStatus.PENDING, priority=TaskPriority.HIGH, title_contains="Task"
    )

    tasks, total = await task_crud.get_list(
        mock_session, filters=filters, page=1, size=10
    )

    assert len(tasks) == 2
    assert total == 2
    assert tasks[0].title == "Task 1"
    assert tasks[1].title == "Task 2"

    # Проверяем, что execute был вызван дважды (для задач и для подсчета)
    assert mock_session.execute.call_count == 2


@pytest.mark.asyncio
async def test_update_status(mock_session):
    """Тест обновления статуса задачи."""
    task_id = uuid.uuid4()
    new_status = TaskStatus.IN_PROGRESS

    # Мокаем обновленную задачу
    mock_updated_task = MagicMock(spec=Task)
    mock_updated_task.id = task_id
    mock_updated_task.status = new_status

    # Мокаем результат выполнения запроса
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_updated_task
    mock_session.execute.return_value = mock_result

    result = await task_crud.update_status(mock_session, task_id, new_status)
    assert result == mock_updated_task

    # Проверяем, что execute был вызван
    mock_session.execute.assert_called_once()

    # Проверяем, что commit был вызван
    mock_session.commit.assert_called_once()


@pytest.mark.asyncio
async def test_cancel_task(mock_session):
    """Тест отмены задачи."""
    task_id = uuid.uuid4()

    # Мокаем обновленную задачу
    mock_updated_task = MagicMock(spec=Task)
    mock_updated_task.id = task_id
    mock_updated_task.status = TaskStatus.CANCELLED

    # Мокаем результат выполнения запроса
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_updated_task
    mock_session.execute.return_value = mock_result

    result = await task_crud.cancel(mock_session, task_id)
    assert result == mock_updated_task
    assert result.status == TaskStatus.CANCELLED

    # Проверяем, что update_status был вызван с правильным статусом
    mock_session.execute.assert_called_once()
    mock_session.commit.assert_called_once()
