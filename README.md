# Infrastructure

Локальная инфраструктура для микросервисной архитектуры.

## Сервисы

| Сервис | Описание | Порт |
|--------|----------|------|
| nginx | API Gateway с балансировкой нагрузки, rate limiting и JWT аутентификацией | 8080 |
| JWT Validator (Python) | Микросервис для проверки JWT токенов | 9090 (внутренний) |
| PostgreSQL 17 | Базы данных для user_service и profile_service | 5432 |
| RabbitMQ  | Брокер сообщений (AMQP) | 5672 |
| RabbitMQ Management | Web UI для управления RabbitMQ | 15672 |

## Быстрый старт

```bash
# 1. Создать файл .env из примера и заполнить переменные
cp env-example.txt .env
# Отредактируй .env и заполни необходимые значения

# 2. Запустить инфраструктуру
docker-compose up -d

# 3. Проверить статус
docker-compose ps

# 4. Проверить логи (опционально)
docker-compose logs -f
```

## API Gateway (nginx)

**URL:** http://localhost:8080

nginx работает как API Gateway, обеспечивая балансировку нагрузки, rate limiting и JWT аутентификацию для всех API запросов.

### Endpoints

| Endpoint | Описание | Аутентификация |
|----------|----------|----------------|
| `GET /health` | Health check | Не требуется |
| `POST /api/v1/auth` | Аутентификация (получение JWT токена) | Не требуется |
| `/api/v1/users/*` | API auth_service | JWT токен (Bearer) |

### JWT Аутентификация

Все защищенные endpoints требуют JWT токен в заголовке `Authorization`:
```
Authorization: Bearer <token>
```

Токен проверяется через Python микросервис `jwt_validator`, который использует библиотеку PyJWT для проверки подписи и expiration токена. Сервис работает на порту 9090 и вызывается nginx через `auth_request` модуль.

### Rate Limiting

Применяются следующие лимиты:
- **Глобальный лимит**: 10 запросов/сек на IP (по умолчанию)
- **auth_service**: 20 запросов/сек на IP
- **auth endpoint** (`/api/v1/auth`): 5 запросов/сек на IP

При превышении лимита возвращается HTTP 429 (Too Many Requests).

### Балансировка нагрузки

API Gateway распределяет запросы между инстансами сервисов через upstream блоки:
- `auth_service`: `host.docker.internal:8000` (внешний сервис, должен работать на хосте)

**Важно:** Убедись, что `auth_service` запущен на хосте на порту 8000, так как nginx использует `host.docker.internal` для доступа к сервисам вне Docker.

Можно добавить несколько инстансов для балансировки, отредактировав `nginx/conf.d/upstreams.conf`.

### Конфигурация

Конфигурационные файлы находятся в директории `nginx/`:
- `nginx/nginx.conf` - основная конфигурация
- `nginx/conf.d/api.conf` - маршрутизация API (включая JWT аутентификацию через `auth_request`)
- `nginx/conf.d/upstreams.conf` - upstream серверы для балансировки нагрузки
- `nginx/conf.d/rate-limit.conf` - настройки rate limiting

Python сервис для проверки JWT:
- `nginx/auth/jwt_validator.py` - Python скрипт для проверки JWT токенов
- `nginx/auth/Dockerfile` - Dockerfile для JWT validator сервиса
- `nginx/auth/pyproject.toml` и `nginx/auth/requirements.txt` - Python зависимости (PyJWT)

## Базы данных PostgreSQL

| База данных | Пользователь | Назначение |
|-------------|--------------|------------|
| `user_db` | `user_service` | Данные пользователей |
| `profile_db` | `profile_service` | Профили пользователей |

Подключение:
```bash
# user_db
psql -h localhost -p 5432 -U user_service -d user_db

# profile_db
psql -h localhost -p 5432 -U profile_service -d profile_db
```

Пароли указываются при запросе или через переменную окружения `PGPASSWORD`.

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

Создай файл `.env` из `env-example.txt` и заполни необходимые переменные. Для управления переменными окружения можно использовать [direnv](https://direnv.net/) с файлом `.envrc`.

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
# Порт nginx: 8080 (внешний) -> 80 (внутренний)

# JWT Configuration
JWT_VALIDATOR_PORT=9090
JWT_SECRET=your-secret-key-here
JWT_ALGORITHM=HS256

# Rate Limiting
# Примечание: nginx не поддерживает переменные окружения в limit_req_zone.
# Для изменения лимитов отредактируйте файл nginx/conf.d/rate-limit.conf
RATE_LIMIT_GLOBAL=10r/s
RATE_LIMIT_AUTH_SERVICE=20r/s
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
