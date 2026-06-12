import asyncio
import json
import traceback  # Добавлен импорт
import uuid

from crud import task_crud
from database import AsyncSessionLocal
from models import TaskStatus
from rabbitmq import QUEUE_NAME, rabbitmq


async def process_one(task_id: uuid.UUID) -> None:
    async with AsyncSessionLocal() as db:
        task = await task_crud.get_by_id(db, task_id)
        if task is None:
            return

        # Если задача уже была отменена — ничего не делаем
        if task.status == TaskStatus.CANCELLED:
            return

        # Устанавливаем статус "В процессе"
        await task_crud.update_status(db, task_id, TaskStatus.IN_PROGRESS)

    try:
        async with AsyncSessionLocal() as db:
            # Успешное завершение
            await task_crud.update_status(
                db,
                task_id,
                TaskStatus.COMPLETED,
                result="выполнено мгновенно",
            )
    except Exception as e:
        # Обработка ошибок и установка статуса FAILED
        async with AsyncSessionLocal() as db:
            await task_crud.update_status(
                db,
                task_id,
                TaskStatus.FAILED,
                error_message=str(e),
                error_details=traceback.format_exc(),
            )


async def main() -> None:
    await rabbitmq.connect()

    # Создаём отдельный канал для потребления
    connection = rabbitmq._connection
    assert connection is not None
    channel = await connection.channel()

    # Устанавливаем prefetch_count=1 для равномерного распределения задач
    # Это гарантирует, что воркер не заберет слишком много сообщений сразу
    await channel.set_qos(prefetch_count=1)

    queue = await channel.declare_queue(
        QUEUE_NAME,
        durable=True,
        arguments={"x-max-priority": 10},
    )

    async with queue.iterator() as queue_iter:
        async for message in queue_iter:
            async with message.process(requeue=True):
                try:
                    payload = json.loads(message.body.decode("utf-8"))
                    task_id = uuid.UUID(payload["task_id"])
                    await process_one(task_id)
                except Exception as e:
                    print(f"Critical error processing message: {e}")


if __name__ == "__main__":
    asyncio.run(main())

