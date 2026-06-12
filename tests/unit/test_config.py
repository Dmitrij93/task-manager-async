import pytest

from app.core.config import Settings


class TestSettings:
    def test_database_url_format(self, monkeypatch):
        """Проверяет формат URL базы данных."""
        # Устанавливаем переменные окружения
        monkeypatch.setenv("DB_USER", "testuser")
        monkeypatch.setenv("DB_PASSWORD", "testpass")
        monkeypatch.setenv("DB_HOST", "localhost")
        monkeypatch.setenv("DB_PORT", "5432")
        monkeypatch.setenv("DB_NAME", "testdb")

        # Создаем экземпляр настроек
        settings = Settings()

        # Проверяем формирование URL
        expected_url = "postgresql+asyncpg://testuser:testpass@localhost:5432/testdb"
        assert settings.database_url == expected_url

    def test_rabbitmq_url_format(self, monkeypatch):
        """Проверяет формат URL RabbitMQ."""
        monkeypatch.setenv("RABBITMQ_USER", "guest")
        monkeypatch.setenv("RABBITMQ_PASSWORD", "guest")
        monkeypatch.setenv("RABBITMQ_HOST", "localhost")
        monkeypatch.setenv("RABBITMQ_PORT", "5672")

        settings = Settings()

        expected_url = "amqp://guest:guest@localhost:5672/"
        assert settings.rabbitmq_url == expected_url

    def test_effective_credentials_for_test_env(self, monkeypatch):
        """Проверяет, что для тестового окружения используются
        тестовые учетные данные.
        """
        monkeypatch.setenv("ENVIRONMENT", "test")

        settings = Settings()

        # В тестовом окружении должны использоваться фиксированные значения
        assert settings.effective_db_user == "test_user"
        assert settings.effective_db_password == "test_password"
        assert settings.effective_rabbitmq_user == "test_rabbit_user"
        assert settings.effective_rabbitmq_password == "test_rabbit_password"
        assert settings.effective_secret_key == "test-secret-key-not-secure"

    def test_missing_required_env_var(self, monkeypatch):
        """Проверяет, что при отсутствии обязательной переменной
        выбрасывается ошибка.
        """
        # Устанавливаем окружение в development,
        # чтобы сработала проверка обязательных полей
        monkeypatch.setenv("ENVIRONMENT", "development")
        # Устанавливаем DB_USER в пустую строку
        # (это эквивалентно отсутствию для pydantic)
        monkeypatch.setenv("DB_USER", "")

        with pytest.raises(ValueError, match="DB_USER обязателен"):
            settings = Settings()
            _ = settings.effective_db_user
