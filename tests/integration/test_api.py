import pytest


@pytest.mark.asyncio
async def test_create_task(client):
    """Тест создания задачи через API."""
    task_data = {
        "title": "Test Task",
        "description": "Test Description",
        "priority": "HIGH",
    }

    response = await client.post("/api/v1/tasks", json=task_data)

    assert response.status_code == 201
    data = response.json()

    assert "id" in data
    assert data["title"] == "Test Task"
    # Статус меняется на PENDING внутри эндпоинта
    assert data["status"] == "PENDING"
    assert data["priority"] == "HIGH"


@pytest.mark.asyncio
async def test_get_task(client):
    """Тест получения задачи по ID."""

    task_data = {"title": "Task to Get", "description": "Get me", "priority": "MEDIUM"}
    create_response = await client.post("/api/v1/tasks", json=task_data)
    task_id = create_response.json()["id"]

    response = await client.get(f"/api/v1/tasks/{task_id}")

    assert response.status_code == 200
    data = response.json()

    assert data["id"] == task_id
    assert data["title"] == "Task to Get"
    assert data["status"] == "PENDING"


@pytest.mark.asyncio
async def test_list_tasks(client):
    """Тест получения списка задач с фильтрацией и пагинацией."""

    task_1 = {"title": "Task 1", "description": "First", "priority": "HIGH"}
    task_2 = {"title": "Task 2", "description": "Second", "priority": "MEDIUM"}
    task_3 = {"title": "Task 3", "description": "Third", "priority": "LOW"}

    await client.post("/api/v1/tasks", json=task_1)
    await client.post("/api/v1/tasks", json=task_2)
    await client.post("/api/v1/tasks", json=task_3)

    # Тест пагинации
    response = await client.get("/api/v1/tasks", params={"page": 1, "size": 2})
    assert response.status_code == 200
    data = response.json()
    assert len(data["tasks"]) == 2
    assert data["total"] >= 3
    assert data["page"] == 1
    assert data["size"] == 2

    # Тест фильтрации по статусу
    response = await client.get("/api/v1/tasks", params={"status": "PENDING"})
    assert response.status_code == 200
    data = response.json()
    for task in data["tasks"]:
        assert task["status"] == "PENDING"

    # Тест фильтрации по приоритету
    response = await client.get("/api/v1/tasks", params={"priority": "HIGH"})
    assert response.status_code == 200
    data = response.json()
    # Проверяем, что хотя бы одна задача с HIGH приоритетом есть (Task 1)
    high_priority_tasks = [t for t in data["tasks"] if t["priority"] == "HIGH"]
    assert len(high_priority_tasks) > 0

    # Тест фильтрации по названию
    response = await client.get("/api/v1/tasks", params={"title_contains": "Task 1"})
    assert response.status_code == 200
    data = response.json()
    assert len(data["tasks"]) > 0
    assert "Task 1" in data["tasks"][0]["title"]


@pytest.mark.asyncio
async def test_cancel_task(client):
    """Тест отмены задачи."""
    # Создаем задачу
    task_data = {
        "title": "Task to Cancel",
        "description": "Will be cancelled",
        "priority": "MEDIUM",
    }
    create_response = await client.post("/api/v1/tasks", json=task_data)
    task_id = create_response.json()["id"]

    # Отменяем задачу
    response = await client.delete(f"/api/v1/tasks/{task_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "CANCELLED"

    # Проверяем, что задача действительно отменена
    get_response = await client.get(f"/api/v1/tasks/{task_id}")
    assert get_response.status_code == 200
    assert get_response.json()["status"] == "CANCELLED"

    # Попытка отменить уже отмененную задачу (или завершенную) - вернет 409
    cancel_again_response = await client.delete(f"/api/v1/tasks/{task_id}")
    assert cancel_again_response.status_code == 409


@pytest.mark.asyncio
async def test_get_task_status(client):
    """Тест получения статуса задачи."""
    # Создаем задачу
    task_data = {
        "title": "Task for Status",
        "description": "Check status",
        "priority": "LOW",
    }
    create_response = await client.post("/api/v1/tasks", json=task_data)
    task_id = create_response.json()["id"]

    # Получаем статус
    response = await client.get(f"/api/v1/tasks/{task_id}/status")
    assert response.status_code == 200
    data = response.json()

    assert data["id"] == task_id
    assert data["status"] == "PENDING"
    assert "created_at" in data
