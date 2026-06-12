import uuid
from datetime import datetime
from typing import Any, List, Optional, Tuple

from sqlalchemy import asc, desc, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Task, TaskStatus
from app.schemas import TaskCreate, TaskFilters


class TaskCRUD:
    """Class for working with tasks in the database"""

    @staticmethod
    async def create(db: AsyncSession, task_data: TaskCreate) -> Task:
        """Create a new task"""
        task = Task(
            title=task_data.title,
            description=task_data.description,
            priority=task_data.priority,
            status=TaskStatus.NEW,
        )

        db.add(task)
        await db.commit()
        await db.refresh(task)
        return task

    @staticmethod
    async def get_by_id(
        db: AsyncSession,
        task_id: uuid.UUID,
    ) -> Optional[Task]:
        """Get task by ID"""
        query = select(Task).where(Task.id == task_id)
        result = await db.execute(query)
        return result.scalar_one_or_none()

    @staticmethod
    async def get_list(
        db: AsyncSession,
        filters: TaskFilters,
        page: int = 1,
        size: int = 50,
        order_by: str = "created_at",
        order_direction: str = "desc",
    ) -> Tuple[List[Task], int]:
        """
        Get list of tasks with filtering and pagination
        Returns (list_of_tasks, total_count)
        """
        # Base query
        query = select(Task)
        count_query = select(func.count(Task.id))

        # Apply filters
        conditions = []

        if filters.status:
            conditions.append(Task.status == filters.status)

        if filters.priority:
            conditions.append(Task.priority == filters.priority)

        if filters.title_contains:
            conditions.append(Task.title.ilike(f"%{filters.title_contains}%"))

        if conditions:
            query = query.where(*conditions)
            count_query = count_query.where(*conditions)

        # Sorting
        order_column = getattr(Task, order_by, Task.created_at)
        if order_direction.lower() == "asc":
            query = query.order_by(asc(order_column))
        else:
            query = query.order_by(desc(order_column))

        # Pagination
        offset = (page - 1) * size
        query = query.offset(offset).limit(size)

        # Execute queries
        tasks_result = await db.execute(query)
        tasks = tasks_result.scalars().all()

        count_result = await db.execute(count_query)
        total = count_result.scalar()

        if total is None:
            total = 0

        return list(tasks), total

    @staticmethod
    async def update_status(
        db: AsyncSession,
        task_id: uuid.UUID,
        new_status: TaskStatus,
        error_message: Optional[str] = None,
        error_details: Optional[str] = None,
        result: Optional[str] = None,
    ) -> Optional[Task]:
        """Update task status with automatic timestamp updates"""

        # Prepare update data
        update_data: dict[str, Any] = {"status": new_status}

        # Automatically update timestamps
        if new_status == TaskStatus.IN_PROGRESS:
            update_data["started_at"] = datetime.utcnow()

        elif new_status in [
            TaskStatus.COMPLETED,
            TaskStatus.FAILED,
            TaskStatus.CANCELLED,
        ]:
            update_data["completed_at"] = datetime.utcnow()

            if new_status == TaskStatus.COMPLETED and result:
                update_data["result"] = result

            elif new_status == TaskStatus.FAILED:
                if error_message:
                    update_data["error_message"] = error_message
                if error_details:
                    update_data["error_details"] = error_details

        # Execute update
        query = (
            update(Task).where(Task.id == task_id).values(**update_data).returning(Task)
        )
        query_result = await db.execute(query)
        await db.commit()

        return query_result.scalar_one_or_none()

    @staticmethod
    async def cancel(db: AsyncSession, task_id: uuid.UUID) -> Optional[Task]:
        """Cancel a task (DELETE /api/v1/tasks/{task_id})."""
        return await TaskCRUD.update_status(db, task_id, TaskStatus.CANCELLED)


# Instance for use in endpoints
task_crud = TaskCRUD()
