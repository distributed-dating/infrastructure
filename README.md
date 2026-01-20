# Infrastructure

Локальная инфраструктура для микросервисной архитектуры.

## Сервисы

| Сервис | Описание |
|--------|----------|
| nginx | API Gateway с балансировкой нагрузки, rate limiting и JWT аутентификацией |
| JWT Validator (Python) | Микросервис для проверки JWT токенов |
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

## API Gateway (nginx)

**URL:** http://localhost

nginx работает как API Gateway, обеспечивая балансировку нагрузки, rate limiting и JWT аутентификацию для всех API запросов.

### Endpoints

| Endpoint | Описание | Аутентификация |
|----------|----------|----------------|
| `GET /health` | Health check | Не требуется |
| `POST /api/v1/auth` | Аутентификация (получение JWT токена) | Не требуется |
| `/api/v1/users/*` | API user_service | JWT токен (Bearer) |
| `/api/v1/profiles/*` | API profile_service | JWT токен (Bearer) |

### JWT Аутентификация

Все защищенные endpoints требуют JWT токен в заголовке `Authorization`:
```
Authorization: Bearer <token>
```

Токен проверяется через Python микросервис `jwt_validator`, который использует библиотеку PyJWT для проверки подписи и expiration токена. Сервис работает на порту 9090 и вызывается nginx через `auth_request` модуль.

### Rate Limiting

Применяются следующие лимиты:
- **Глобальный лимит**: 10 запросов/сек на IP (по умолчанию)
- **user_service**: 20 запросов/сек на IP
- **profile_service**: 20 запросов/сек на IP
- **auth endpoint**: 5 запросов/сек на IP

При превышении лимита возвращается HTTP 429 (Too Many Requests).

### Балансировка нагрузки

API Gateway распределяет запросы между инстансами сервисов через upstream блоки:
- `user_service`: порт 8001
- `profile_service`: порт 8002

Можно добавить несколько инстансов для балансировки, отредактировав `nginx/conf.d/upstreams.conf`.

### Конфигурация

Конфигурационные файлы находятся в директории `nginx/`:
- `nginx/nginx.conf` - основная конфигурация
- `nginx/conf.d/api.conf` - маршрутизация API
- `nginx/conf.d/upstreams.conf` - upstream серверы
- `nginx/conf.d/rate-limit.conf` - настройки rate limiting
- `nginx/conf.d/jwt-auth.conf` - конфигурация auth_request для JWT

Python сервис для проверки JWT:
- `nginx/auth/jwt_validator.py` - Python скрипт для проверки JWT токенов
- `nginx/auth/Dockerfile` - Dockerfile для JWT validator сервиса
- `nginx/auth/requirements.txt` - Python зависимости (PyJWT)

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

# Nginx API Gateway
USER_SERVICE_PORT=8001
PROFILE_SERVICE_PORT=8002

# JWT Configuration
JWT_SECRET=your-secret-key-here
JWT_ALGORITHM=HS256

# Rate Limiting
RATE_LIMIT_GLOBAL=10r/s
RATE_LIMIT_USER_SERVICE=20r/s
RATE_LIMIT_PROFILE_SERVICE=20r/s
RATE_LIMIT_AUTH=5r/s
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
