import asyncio
import json
import traceback
import uuid

from app.crud import task_crud
from app.core.database import AsyncSessionLocal
from app.models import TaskStatus
from app.core.rabbitmq import QUEUE_NAME, rabbitmq


async def process_one(task_id: uuid.UUID) -> None:
    async with AsyncSessionLocal() as db:
        task = await task_crud.get_by_id(db, task_id)
        if task is None:
            return

        if task.status == TaskStatus.CANCELLED:
            return

        await task_crud.update_status(db, task_id, TaskStatus.IN_PROGRESS)

    try:
        async with AsyncSessionLocal() as db:
            await task_crud.update_status(
                db,
                task_id,
                TaskStatus.COMPLETED,
                result="выполнено",
            )
    except Exception as e:
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

    connection = rabbitmq._connection
    assert connection is not None
    channel = await connection.channel()

    # Устанавливаем prefetch_count=1 для равномерного распределения задач
    # чтобы воркер не забирал слишком много сообщений сразу
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
                except json.JSONDecodeError as e:
                    print(
                        f"Ошибка декодирования JSON: {e}. "
                        f"Тело сообщения: {message.body}"
                    )
                except KeyError as e:
                    print(
                        f"Отсутствует ключ в сообщении: {e}. "
                        f"Тело сообщения: {message.body}"
                    )
                except Exception as e:
                    print(f"Неизвестная ошибка при обработке задачи {task_id}: {e}")


if __name__ == "__main__":
    asyncio.run(main())
