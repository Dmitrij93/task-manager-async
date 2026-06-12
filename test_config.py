import os
from typing import Any

from app.core.config import Settings
from pydantic import PrivateAttr


class TestSettings(Settings):
    """Настройки для двух типов тестов"""

    _test_type: str = PrivateAttr(default="unit")

    def __init__(self, test_type: str = "unit", **data: Any):
        super().__init__(**data)
        # Устанавливаем приватный атрибут, Pydantic не позволяет делать это напрямую
        object.__setattr__(self, "_test_type", test_type)

        # Перезагружаем конфигурацию с новым ENVIRONMENT перед завершением
        # инициализации родителя для Pydantic V2, чтобы корректно сработала
        # логика свойств
        if test_type == "unit":
            os.environ["ENVIRONMENT"] = "test"
        elif test_type == "integration":
            os.environ["ENVIRONMENT"] = "test_integration"

    @property
    def test_type(self) -> str:
        return self._test_type

    @property
    def database_url(self) -> str:
        """URL базы данных в зависимости от типа теста"""
        if self.test_type == "unit":
            db_host = os.environ.get("DB_HOST", "localhost")
            db_port = os.environ.get("DB_PORT", "5433")
            return (
                f"postgresql+asyncpg://test_user:test_password@"
                f"{db_host}:{db_port}/unit_test_db"
            )
        elif self.test_type == "integration":
            db_host = os.environ.get("DB_HOST", "localhost")
            db_port = os.environ.get("DB_PORT", "5433")
            return (
                f"postgresql+asyncpg://test_user:test_password@"
                f"{db_host}:{db_port}/integration_test_db"
            )
        else:
            return super().database_url

    @property
    def rabbitmq_url(self) -> str:
        """URL RabbitMQ в зависимости от типа теста"""
        if self.test_type == "unit":
            return "memory://"
        elif self.test_type == "integration":
            rabbitmq_host = os.environ.get("RABBITMQ_HOST", "localhost")
            rabbitmq_port = os.environ.get("RABBITMQ_PORT", "5673")
            return (
                f"amqp://test_rabbit_user:test_rabbit_password@"
                f"{rabbitmq_host}:{rabbitmq_port}/"
            )
        else:
            return super().rabbitmq_url


def get_unit_test_settings() -> TestSettings:
    """Настройки для unit-тестов (PostgreSQL с отдельной БД, mock очереди)"""
    return TestSettings(test_type="unit")


def get_integration_test_settings() -> TestSettings:
    """Настройки для интеграционных тестов (PostgreSQL, RabbitMQ)"""
    return TestSettings(test_type="integration")

