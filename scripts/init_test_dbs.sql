-- Создание тестовых баз данных при запуске PostgreSQL контейнера

-- База для unit-тестов (быстрые, изолированные тесты)
CREATE DATABASE unit_test_db 
    WITH OWNER = test_user 
    ENCODING = 'UTF8';

-- База для интеграционных тестов (полные сценарии)
CREATE DATABASE integration_test_db 
    WITH OWNER = test_user 
    ENCODING = 'UTF8';

-- Подключаемся к каждой БД и выдаём права
\c unit_test_db;
GRANT ALL PRIVILEGES ON DATABASE unit_test_db TO test_user;
GRANT ALL PRIVILEGES ON SCHEMA public TO test_user;

\c integration_test_db;
GRANT ALL PRIVILEGES ON DATABASE integration_test_db TO test_user;
GRANT ALL PRIVILEGES ON SCHEMA public TO test_user;