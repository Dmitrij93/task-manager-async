# Система управления задачами

Асинхронный сервис для управления задачами с использованием FastAPI, PostgreSQL и RabbitMQ.

## Структура проекта

```text
.
├── app/                    # Основной код приложения
│   ├── api/
│   │   └── v1/
│   │       └── tasks.py    # API endpoints
│   ├── core/
│   │   ├── config.py       # Конфигурация
│   │   ├── database.py     # Подключение к БД
│   │   └── rabbitmq.py     # Подключение к RabbitMQ
│   ├── models.py           # Модели SQLAlchemy
│   ├── schemas.py          # Pydantic схемы
│   ├── crud.py             # CRUD операции
│   ├── main.py             # FastAPI приложение
│   └── worker.py           # Обработчик задач
├── tests/                  # Тесты
├── alembic/                # Миграции
├── scripts/                # Скрипты
├── docker/                 # Docker конфигурация
├── .env                    # Переменные окружения
└── requirements.txt        # Зависимости
```

## Запуск проекта

### 1. Настройка окружения

Создайте файл `.env` в корне проекта со следующими переменными:

```env
# Приложение
ENVIRONMENT=development
DEBUG=True
SECRET_KEY=your_secret_key

# База данных
DB_USER=postgres
DB_PASSWORD=postgres
DB_HOST=localhost
DB_PORT=5432
DB_NAME=tasks_db

# RabbitMQ
RABBITMQ_USER=guest
RABBITMQ_PASSWORD=guest
RABBITMQ_HOST=localhost
RABBITMQ_PORT=5672
```

### 2. Запуск с Docker Compose (рекомендуется)

```bash
docker-compose up -d
```

Приложение будет доступно по адресу: `http://localhost:8000`

### 3. Запуск вручную (без Docker)

1. Установите зависимости:
```bash
pip install -r requirements.txt
```

2. Запустите базу данных и RabbitMQ (например, через Docker):
```bash
docker run -d --name postgres -p 5432:5432 -e POSTGRES_PASSWORD=postgres postgres:16-alpine
docker run -d --name rabbitmq -p 5672:5672 -p 15672:15672 rabbitmq:3-management
```

3. Примените миграции:
```bash
alembic upgrade head
```

4. Запустите приложение:
```bash
uvicorn app.main:app --reload
```

5. Запустите воркер (обработчик задач):
```bash
python -m app.worker
```

## Статический анализ и форматирование

### Форматирование кода (Black)
```bash
black .
```

### Проверка форматирования (Black)
```bash
black --check .
```

### Линтинг (Flake8)
```bash
flake8 .
```

### Проверка типов (Mypy)
```bash
mypy .
```

## Нагрузочное тестирование

Для тестирования производительности API можно использовать скрипт `scripts/generate_tasks.py`.

### Запуск скрипта в Docker (рекомендуется)

Для запуска скрипта нагрузочного тестирования необходимо, чтобы сервисы базы данных и RabbitMQ были запущены, а также были применены миграции к тестовой базе данных.

```bash
# 1. Запустите основные сервисы (PostgreSQL, RabbitMQ) и контейнер app в фоновом режиме
docker-compose -f docker-compose.test.yml up -d

# 2. Примените миграции к тестовой базе данных
docker-compose -f docker-compose.test.yml exec app alembic upgrade head

# 3. Запустите скрипт генерации задач внутри контейнера app
# Важно: добавляем PYTHONPATH=/app, чтобы Python мог найти модули проекта
docker-compose -f docker-compose.test.yml exec app sh -c "PYTHONPATH=/app python scripts/generate_tasks.py --count 1000 --concurrency 10"
```

### Запуск скрипта локально

```bash
# Убедитесь, что переменные окружения (.env) настроены и сервисы запущены
# Примените миграции
alembic upgrade head

# Запустите скрипт
$env:PYTHONPATH = '.'
python scripts/generate_tasks.py --count 1000 --concurrency 10
```

### Параметры
- `--count`: Количество задач для создания (по умолчанию: 100)
- `--concurrency`: Количество одновременных запросов (по умолчанию: 5)
- `--api-url`: URL API (по умолчанию: http://localhost:8000)

### Пример (Docker)
```bash
docker-compose -f docker-compose.test.yml exec app sh -c "PYTHONPATH=/app python scripts/generate_tasks.py --count 500 --concurrency 20"
```

Скрипт создаст указанное количество задач в базе данных и отправит их в очередь RabbitMQ.

## Масштабирование воркеров

Для увеличения пропускной способности очереди задач можно запустить несколько экземпляров воркера.

### В Docker Compose (тестовая среда)

```bash
# Запустить 3 воркера вместо одного
docker-compose -f docker-compose.test.yml up --scale worker=3 -d
```

### В Docker Compose (продакшен)

```bash
# Запустить 3 воркера вместо одного
docker-compose up --scale worker=3 -d
```

### Мониторинг очереди RabbitMQ

RabbitMQ предоставляет веб-интерфейс для мониторинга:
- **Продакшен**: `http://localhost:15672` (логин/пароль: guest/guest)
- **Тестовая среда**: `http://localhost:15673` (логин/пароль: test_rabbit_user/test_rabbit_password)

В веб-интерфейсе можно просмотреть:
- Количество сообщений в очереди
- Скорость обработки
- Количество активных потребителей (воркеров)

### Настройка производительности воркера

В `app/worker.py` установлен `prefetch_count=1`, что гарантирует равномерное распределение задач между воркерами. Каждый воркер будет обрабатывать только одну задачу одновременно.

Если задачи выполняются быстро, можно увеличить `prefetch_count` для повышения пропускной способности (но это может привести к неравномерной нагрузке).
