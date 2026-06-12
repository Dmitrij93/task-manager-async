#!/bin/bash

# Запуск интеграционных тестов внутри Docker
# Этот скрипт должен запускаться на хосте

set -e

echo "Building test environment..."

# Запускаем контейнеры для тестов
docker-compose -f docker-compose.test.yml up -d --build

# Ждем, пока контейнеры будут готовы
echo "Waiting for services to be ready..."
sleep 30

# Запускаем тесты внутри контейнера app
echo "Running integration tests..."
docker-compose -f docker-compose.test.yml exec -T app pytest tests/integration -v

# Останавливаем контейнеры
echo "Stopping test environment..."
docker-compose -f docker-compose.test.yml down

echo "Integration tests completed."