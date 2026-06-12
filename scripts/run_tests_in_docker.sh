#!/bin/bash
# Этот скрипт запускается внутри контейнера app в docker-compose.test.yml
# Устанавливаем PYTHONPATH, чтобы Python видел модули проекта
export PYTHONPATH=/app

# Запускаем pytest для интеграционных тестов
# Используем -v для подробного вывода
exec pytest tests/integration/ -v