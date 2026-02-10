"""Middleware for admin panel security."""
from functools import wraps
from flask import request, jsonify, session
import os

# Credenciales hardcodeadas para admin
ADMIN_USER = 'joaquin'
ADMIN_PASS = 'joaquin13'


def _is_localhost_or_local_network():
    """Verifica si la petición viene de localhost o red local (desarrollo)."""
    remote_addr = request.remote_addr or ''
    # Localhost
    if remote_addr in ('127.0.0.1', 'localhost', '::1'):
        return True
    # Red local típica (172.16.x.x - 172.31.x.x, 192.168.x.x, 10.x.x.x, 172.20.x.x)
    if remote_addr.startswith(('172.', '192.168.', '10.')):
        return True
    forwarded_for = request.headers.get('X-Forwarded-For', '')
    if forwarded_for:
        first_ip = forwarded_for.split(',')[0].strip()
        if first_ip in ('127.0.0.1', 'localhost', '::1'):
            return True
        if first_ip.startswith(('172.', '192.168.', '10.')):
            return True
    return False


def admin_only(f):
    """
    Decorator that only allows access from localhost.
    Blocks access if production env is set (Azure/Railway).
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if os.getenv('RAILWAY_ENVIRONMENT') or os.getenv('AZURE_ENVIRONMENT'):
            return jsonify({'error': 'Admin panel not available in production'}), 403
        if not _is_localhost_or_local_network():
            return jsonify({'error': 'Admin access only from localhost'}), 403
        return f(*args, **kwargs)
    return decorated_function


def _is_admin_authenticated():
    """Verifica sesión o token Bearer (evita dependencia de cookies bloqueadas por Tracking Prevention)."""
    if session.get('admin_logged_in'):
        return True
    auth = request.headers.get('Authorization', '')
    if auth.startswith('Bearer '):
        from . import admin_tokens
        return admin_tokens.has_token(auth[7:].strip())
    return False


def admin_session_required(f):
    """
    Decorator that requires admin login (session o token Bearer) + localhost.
    Use for admin API routes and update routes.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if os.getenv('RAILWAY_ENVIRONMENT') or os.getenv('AZURE_ENVIRONMENT'):
            return jsonify({'error': 'Admin panel not available in production'}), 403
        if not _is_localhost_or_local_network():
            return jsonify({'error': 'Admin access only from localhost'}), 403
        if not _is_admin_authenticated():
            return jsonify({'error': 'Login required'}), 401
        return f(*args, **kwargs)
    return decorated_function
