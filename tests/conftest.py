def pytest_configure(config):
    """Регистрируем кастомные маркеры"""
    config.addinivalue_line(
        "markers",
        "unit: юнит-тесты (быстрые, изолированные, PostgreSQL с чистой БД)",
    )
    config.addinivalue_line(
        "markers",
        "integration: интеграционные тесты "
        "(медленнее, реальные PostgreSQL + RabbitMQ)",
    )
