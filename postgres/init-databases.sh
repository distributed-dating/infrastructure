#!/bin/bash
set -e

# Создание дополнительных баз данных при первом запуске PostgreSQL
# Скрипт выполняется от имени суперпользователя POSTGRES_USER

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "postgres" <<-EOSQL
    -- Создаём пользователя и базу данных для user_service
    CREATE USER ${USER_SERVICE_DB_USER} WITH PASSWORD '${USER_SERVICE_DB_PASSWORD}';
    CREATE DATABASE ${USER_SERVICE_DB_NAME} OWNER ${USER_SERVICE_DB_USER};
    GRANT ALL PRIVILEGES ON DATABASE ${USER_SERVICE_DB_NAME} TO ${USER_SERVICE_DB_USER};

    -- Создаём пользователя и базу данных для profile_service
    CREATE USER ${PROFILE_SERVICE_DB_USER} WITH PASSWORD '${PROFILE_SERVICE_DB_PASSWORD}';
    CREATE DATABASE ${PROFILE_SERVICE_DB_NAME} OWNER ${PROFILE_SERVICE_DB_USER};
    GRANT ALL PRIVILEGES ON DATABASE ${PROFILE_SERVICE_DB_NAME} TO ${PROFILE_SERVICE_DB_USER};
EOSQL

echo "Базы данных ${USER_SERVICE_DB_NAME} и ${PROFILE_SERVICE_DB_NAME} успешно созданы"
