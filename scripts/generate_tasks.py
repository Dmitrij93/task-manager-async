from __future__ import annotations


import asyncio
import argparse
import uuid
from datetime import datetime
from argparse import Namespace

from app.core.database import AsyncSessionLocal
from app.models import Task, TaskPriority, TaskStatus
from app.core.rabbitmq import rabbitmq


def parse_args() -> Namespace:
    parser = argparse.ArgumentParser(
        description="Генерация задач для нагрузочного тестирования"
    )
    parser.add_argument(
        "--count", type=int, default=100, help="Количество задач для создания"
    )
    parser.add_argument(
        "--concurrency",
        type=int,
        default=5,
        help="Количество одновременных запросов (не используется в текущей реализации)",
    )
    parser.add_argument(
        "--api-url",
        type=str,
        default="http://localhost:8000",
        help="URL API (не используется в текущей реализации)",
    )
    return parser.parse_args()


async def generate_tasks(count: int = 2000) -> None:
    print(f"Генерация {count} задач...")

    async with AsyncSessionLocal() as db:
        tasks = []
        for i in range(count):
            task_id = uuid.uuid4()
            task = Task(
                id=task_id,  # type: ignore[arg-type]
                title=f"Задача #{i+1}",
                description=f"Тестовая задача {i+1}",
                priority=TaskPriority.MEDIUM,
                status=TaskStatus.PENDING,
                created_at=datetime.utcnow(),
            )
            tasks.append(task)

            # Пакетная вставка в БД
            if len(tasks) >= 1000:
                db.add_all(tasks)
                await db.commit()
                print(f"Добавлено в БД {i+1} задач...")

                # Публикуем задачи в RabbitMQ ПОСЛЕ коммита
                for t in tasks:
                    try:
                        await rabbitmq.publish_task(
                            task_id=uuid.UUID(str(t.id)),
                            priority=t.priority if t.priority else TaskPriority.MEDIUM,
                        )
                    except Exception as e:
                        print(f"Ошибка публикации задачи {t.id}: {e}")
                tasks = []

        # Обработка оставшихся задач
        if tasks:
            db.add_all(tasks)
            await db.commit()
            print(f"Добавлено в БД {len(tasks)} задач...")

            # Публикуем оставшиеся задачи
            for t in tasks:
                try:
                    await rabbitmq.publish_task(
                        task_id=uuid.UUID(str(t.id)),
                        priority=t.priority if t.priority else TaskPriority.MEDIUM,
                    )
                except Exception as e:
                    print(f"Ошибка публикации задачи {t.id}: {e}")

                print(f"Всего создано {count} задач и отправлено в очередь.")


if __name__ == "__main__":
    args = parse_args()
    asyncio.run(generate_tasks(args.count))
