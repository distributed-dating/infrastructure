#!/usr/bin/env python3
"""
JWT Authentication validator для nginx auth_request модуля.

Этот скрипт проверяет JWT токены из заголовка Authorization и возвращает
HTTP 200 если токен валиден, или HTTP 401/403 если не валиден.
"""

import os
import sys
import json
import base64
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse, parse_qs

try:
    import jwt
    JWT_LIBRARY_AVAILABLE = True
except ImportError:
    JWT_LIBRARY_AVAILABLE = False
    print("Warning: PyJWT library not found. Install with: pip install PyJWT", file=sys.stderr)


class JWTValidatorHandler(BaseHTTPRequestHandler):
    """HTTP обработчик для проверки JWT токенов."""
    
    def log_message(self, format, *args):
        # Отключаем стандартное логирование
        pass
    
    def do_GET(self):
        """Обработка GET запроса от nginx auth_request."""
        # Получаем Authorization header из запроса
        auth_header = self.headers.get('Authorization', '')
        
        if not auth_header:
            self.send_response(401)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({
                'error': 'Missing Authorization header'
            }).encode())
            return
        
        # Извлекаем токен из заголовка "Bearer <token>"
        if not auth_header.startswith('Bearer '):
            self.send_response(401)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({
                'error': 'Invalid Authorization header format. Expected: Bearer <token>'
            }).encode())
            return
        
        token = auth_header[7:]  # Убираем "Bearer "
        
        # Валидация токена
        valid, error = self.validate_jwt(token)
        
        if not valid:
            self.send_response(401)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({
                'error': 'Invalid JWT token',
                'reason': error
            }).encode())
            return
        
        # Токен валиден - возвращаем 200
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps({'status': 'valid'}).encode())
    
    def validate_jwt(self, token):
        """
        Валидация JWT токена.
        
        Returns:
            tuple: (is_valid, error_message)
        """
        if not token or token == "":
            return False, "Empty token"
        
        # Базовая проверка формата (три части, разделенные точками)
        parts = token.split('.')
        if len(parts) != 3:
            return False, "Invalid JWT format"
        
        # Если доступна библиотека PyJWT, используем полную проверку
        if JWT_LIBRARY_AVAILABLE:
            return self.validate_jwt_with_library(token)
        
        # Иначе - только базовая проверка формата
        return True, None
    
    def validate_jwt_with_library(self, token):
        """
        Полная валидация JWT с использованием PyJWT библиотеки.
        
        Returns:
            tuple: (is_valid, error_message)
        """
        try:
            # Получаем секрет из переменной окружения
            secret = os.environ.get('JWT_SECRET', '')
            algorithm = os.environ.get('JWT_ALGORITHM', 'HS256')
            
            if not secret:
                # Если секрет не задан, только проверяем формат
                return True, None
            
            # Декодируем и проверяем токен
            payload = jwt.decode(
                token,
                secret,
                algorithms=[algorithm],
                options={
                    "verify_signature": True,
                    "verify_exp": True,
                    "verify_iat": True,
                }
            )
            
            return True, None
            
        except jwt.ExpiredSignatureError:
            return False, "Token expired"
        except jwt.InvalidTokenError as e:
            return False, f"Invalid token: {str(e)}"
        except Exception as e:
            return False, f"Validation error: {str(e)}"


def main():
    """Запуск HTTP сервера для проверки JWT."""
    port = int(os.environ.get('JWT_VALIDATOR_PORT', '9090'))
    server_address = ('', port)
    
    httpd = HTTPServer(server_address, JWTValidatorHandler)
    
    print(f"JWT Validator starting on port {port}", file=sys.stderr)
    
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down JWT Validator", file=sys.stderr)
        httpd.shutdown()


if __name__ == '__main__':
    main()
