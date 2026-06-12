from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.database import get_db


class TestDatabase:
    @pytest.mark.asyncio
    async def test_get_db_dependency(self):
        """Тест корректности работы зависимости get_db."""
        # Мокаем AsyncSessionLocal
        mock_session = AsyncMock()
        mock_session.commit = AsyncMock()
        mock_session.rollback = AsyncMock()
        mock_session.close = AsyncMock()

        # Чтобы AsyncSessionLocal работал как async context manager (async with)
        # мы должны настроить __aenter__ и __aexit__
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)

        # __aexit__ должен вызывать close, как это делает реальная сессия
        async def exit_effect(exc_type, exc_val, exc_tb):
            await mock_session.close()
            return None

        mock_session.__aexit__ = AsyncMock(side_effect=exit_effect)

        mock_session_maker = MagicMock(return_value=mock_session)

        with patch("app.core.database.AsyncSessionLocal", mock_session_maker):
            # Получаем генератор
            gen = get_db()
            # Получаем сессию из генератора
            db = await gen.__anext__()

            # Проверяем, что сессия была создана
            mock_session_maker.assert_called_once()
            assert db == mock_session

            # Эмулируем работу с сессией
            await db.commit()

            # Закрываем генератор (вызывает GeneratorExit,
            # который завершает async with и finally блок)
            await gen.aclose()

            # Проверяем, что __aexit__ был вызван
            # (это гарантирует закрытие сессии)
            mock_session.__aexit__.assert_called_once()

            # Также можно проверить, что close был вызван (возможно,
            # дважды, из-за finally блока в get_db)
            # mock_session.close.assert_called()

    def test_engine_creation(self, monkeypatch):
        """Тест создания движка с правильным URL."""
        # Устанавливаем переменные окружения для теста
        monkeypatch.setenv("DB_USER", "user")
        monkeypatch.setenv("DB_PASSWORD", "pass")
        monkeypatch.setenv("DB_HOST", "localhost")
        monkeypatch.setenv("DB_PORT", "5432")
        monkeypatch.setenv("DB_NAME", "test_db")
        # Чтобы избежать использования тестовых учетных данных
        monkeypatch.setenv("ENVIRONMENT", "production")

        # Импортируем Settings здесь, чтобы он подхватил
        # новые переменные окружения
        from app.core.config import Settings

        # Однако, pydantic-settings кэширует конфигурацию,
        # поэтому мы можем создать новый экземпляр
        # Вместо этого, проверим логику формирования URL напрямую

        settings = Settings()
        expected_url = "postgresql+asyncpg://user:pass@localhost:5432/test_db"
        assert settings.database_url == expected_url
