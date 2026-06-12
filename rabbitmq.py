from __future__ import annotations

import json
import uuid
from typing import Any, Optional

import aio_pika

from config import settings as default_settings
from models import TaskPriority

QUEUE_NAME = "tasks"
MAX_PRIORITY = 10


def priority_to_int(priority: TaskPriority) -> int:
    # RabbitMQ ожидает целочисленный приоритет в диапазоне [0..x-max-priority]
    return {
        TaskPriority.LOW: 1,
        TaskPriority.MEDIUM: 5,
        TaskPriority.HIGH: 9,
    }[priority]


class RabbitMQ:
    def __init__(self, rabbitmq_url: Optional[str] = None) -> None:
        self._connection: Any = None
        self._channel: Any = None
        self._queue: Any = None
        # Если URL не передан, используем URL из настроек по умолчанию
        self.rabbitmq_url = rabbitmq_url or default_settings.rabbitmq_url

    async def connect(self) -> None:
        if self._connection and not self._connection.is_closed:
            return

        self._connection = await aio_pika.connect_robust(self.rabbitmq_url)
        self._channel = await self._connection.channel()

        # Убеждаемся, что очередь существует и поддерживает приоритеты
        assert self._channel is not None
        self._queue = await self._channel.declare_queue(
            QUEUE_NAME,
            durable=True,
            arguments={"x-max-priority": MAX_PRIORITY},
        )

    async def close(self) -> None:
        if self._connection and not self._connection.is_closed:
            await self._connection.close()

        self._connection = None
        self._channel = None
        self._queue = None

    async def publish_task(
        self,
        task_id: uuid.UUID,
        priority: TaskPriority,
    ) -> None:
        await self.connect()

        body = json.dumps({"task_id": str(task_id)}).encode("utf-8")
        message = aio_pika.Message(
            body=body,
            delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
            priority=priority_to_int(priority),
        )

        # Обмен по умолчанию маршрутизирует по routing_key
        await self._channel.default_exchange.publish(message, routing_key=QUEUE_NAME)


rabbitmq = RabbitMQ()
