# Infrastructure

Локальная инфраструктура для микросервисной архитектуры.

## Сервисы

| Сервис | Описание |
|--------|----------|
| PostgreSQL 17 | Базы данных для user_service и profile_service |
| RabbitMQ  | Брокер сообщений (AMQP) |
| RabbitMQ Management | Web UI для управления RabbitMQ |

## Быстрый старт

```bash
# Загрузить переменные окружения
source .envrc

# Запустить инфраструктуру
docker-compose up -d

# Проверить статус
docker-compose ps
```

## Базы данных PostgreSQL

| База данных | Пользователь | Назначение |
|-------------|--------------|------------|
| `user_db` | `user_service` | Данные пользователей |
| `profile_db` | `profile_service` | Профили пользователей |

Подключение:
```bash
# user_db
psql -h localhost -U user_service -d user_db

# profile_db
psql -h localhost -U profile_service -d profile_db
```

## RabbitMQ

**Management UI:** http://localhost:15672
**Логин:** guest / guest

### Exchanges

| Exchange | Тип | Описание |
|----------|-----|----------|
| `auth.events` | direct | События аутентификации |
| `auth.events.dlx` | direct | Dead Letter Exchange |

### Очереди

| Очередь | Описание |
|---------|----------|
| `profile_service.user_events` | События для profile_service |
| `profile_service.user_events.dlq` | Dead Letter Queue |

### События

| Routing Key | Producer | Consumer | Описание |
|-------------|----------|----------|----------|
| `user.created` | user_service | profile_service | Пользователь создан |
| `user.activated` | user_service | profile_service | Пользователь активирован |
| `user.deactivated` | user_service | profile_service | Пользователь деактивирован |

### Архитектура сообщений

```
user_service                         profile_service
     │                                      │
     │  user.created                        │
     │  user.activated      ┌───────────────┤
     │  user.deactivated    │               │
     ▼                      ▼               │
┌─────────────┐    ┌────────────────────┐   │
│ auth.events │───▶│ profile_service.   │───┘
│   (direct)  │    │   user_events      │
└─────────────┘    └────────────────────┘
                            │ reject/nack
                            ▼
                   ┌────────────────────┐
                   │ auth.events.dlx    │
                   └────────────────────┘
                            │
                            ▼
                   ┌────────────────────┐
                   │ profile_service.   │
                   │ user_events.dlq    │
                   └────────────────────┘
```

## Переменные окружения

Скопируй `env-example.txt` в `.env` или используй `.envrc` с [direnv](https://direnv.net/).

```bash
# PostgreSQL
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres

# user_service DB
USER_SERVICE_DB_NAME=user_db
USER_SERVICE_DB_USER=user_service
USER_SERVICE_DB_PASSWORD=user_service_password

# profile_service DB
PROFILE_SERVICE_DB_NAME=profile_db
PROFILE_SERVICE_DB_USER=profile_service
PROFILE_SERVICE_DB_PASSWORD=profile_service_password

# RabbitMQ
RABBITMQ_HOST=localhost
RABBITMQ_PORT=5672
RABBITMQ_USER=guest
RABBITMQ_PASSWORD=guest
RABBITMQ_EXCHANGE=auth.events
```

## Команды

```bash
# Запустить
docker-compose up -d

# Остановить
docker-compose down

# Логи
docker-compose logs -f

# Полная очистка (удаляет данные)
docker-compose down -v
```
