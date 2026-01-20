FROM python:3.11-slim

WORKDIR /app

# Копируем requirements и устанавливаем зависимости
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копируем скрипт
COPY jwt_validator.py .

# Запускаем сервис
CMD ["python", "jwt_validator.py"]
