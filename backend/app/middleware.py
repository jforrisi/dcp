"""Middleware for admin panel security."""
from functools import wraps
from flask import request, jsonify
import os


def admin_only(f):
    """
    Decorator that only allows access from localhost.
    Blocks access if RAILWAY_ENVIRONMENT is set (production).
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # En producción (Railway), deshabilitar completamente
        if os.getenv('RAILWAY_ENVIRONMENT'):
            return jsonify({'error': 'Admin panel not available in production'}), 403
        
        # Solo permitir desde localhost
        remote_addr = request.remote_addr
        allowed_hosts = ['127.0.0.1', 'localhost', '::1']
        
        # También verificar el header X-Forwarded-For si está presente (para proxies locales)
        if remote_addr not in allowed_hosts:
            # Verificar si viene de un proxy local
            forwarded_for = request.headers.get('X-Forwarded-For', '')
            if forwarded_for:
                # Tomar la primera IP de la cadena
                first_ip = forwarded_for.split(',')[0].strip()
                if first_ip not in allowed_hosts:
                    return jsonify({'error': 'Admin access only from localhost'}), 403
            else:
                return jsonify({'error': 'Admin access only from localhost'}), 403
        
        return f(*args, **kwargs)
    return decorated_function
