@echo off
setlocal

REM Запуск интеграционных тестов внутри Docker
REM Этот скрипт должен запускаться на хосте Windows

echo Building test environment...

REM Запускаем контейнеры для тестов
docker-compose -f docker-compose.test.yml up -d --build

REM Ждем, пока контейнеры будут готовы
echo Waiting for services to be ready...
sleep 30

REM Запускаем тесты внутри контейнера app
echo Running integration tests...
docker-compose -f docker-compose.test.yml exec -T app pytest tests/integration -v

REM Останавливаем контейнеры
echo Stopping test environment...
docker-compose -f docker-compose.test.yml down

echo Integration tests completed.
endlocal