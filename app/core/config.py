from __future__ import annotations

from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuration of the application through environment variables (.env)."""

    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=False,
        extra="ignore",
    )

    # App
    environment: str = "development"
    debug: bool = True
    host: str = "0.0.0.0"
    port: int = 8000

    # Database
    db_user: Optional[str] = None
    db_password: Optional[str] = None
    db_host: str = "postgres"
    db_port: int = 5432
    db_name: str = "tasks_db"

    # RabbitMQ
    rabbitmq_user: Optional[str] = None
    rabbitmq_password: Optional[str] = None
    rabbitmq_host: str = "rabbitmq"
    rabbitmq_port: int = 5672

    # Security
    secret_key: Optional[str] = None

    def _require(self, value: Optional[str], env_name: str) -> str:
        if value:
            return value
        raise ValueError(f"{env_name} обязателен for environment: {self.environment}")

    @property
    def effective_db_user(self) -> str:
        return (
            "test_user"
            if self.environment == "test"
            else self._require(self.db_user, "DB_USER")
        )

    @property
    def effective_db_password(self) -> str:
        return (
            "test_password"
            if self.environment == "test"
            else self._require(self.db_password, "DB_PASSWORD")
        )

    @property
    def effective_rabbitmq_user(self) -> str:
        return (
            "test_rabbit_user"
            if self.environment == "test"
            else self._require(self.rabbitmq_user, "RABBITMQ_USER")
        )

    @property
    def effective_rabbitmq_password(self) -> str:
        return (
            "test_rabbit_password"
            if self.environment == "test"
            else self._require(self.rabbitmq_password, "RABBITMQ_PASSWORD")
        )

    @property
    def effective_secret_key(self) -> str:
        return (
            "test-secret-key-not-secure"
            if self.environment == "test"
            else self._require(self.secret_key, "SECRET_KEY")
        )

    @property
    def database_url(self) -> str:
        return (
            f"postgresql+asyncpg://{self.effective_db_user}:"
            f"{self.effective_db_password}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}"
        )

    @property
    def rabbitmq_url(self) -> str:
        if self.environment == "test":
            # For integration tests use localhost:5673
            return (
                f"amqp://{self.effective_rabbitmq_user}:"
                f"{self.effective_rabbitmq_password}@localhost:5673/"
            )
        else:
            return (
                f"amqp://{self.effective_rabbitmq_user}:"
                f"{self.effective_rabbitmq_password}"
                f"@{self.rabbitmq_host}:{self.rabbitmq_port}/"
            )


settings = Settings()
