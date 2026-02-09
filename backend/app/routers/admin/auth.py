"""Admin login endpoint."""
from flask import Blueprint, request, jsonify, session
from ...middleware import admin_only, ADMIN_USER, ADMIN_PASS

bp = Blueprint('admin_auth', __name__)


@bp.route('/login', methods=['POST', 'OPTIONS'])
@admin_only
def login():
    """Login con usuario y contraseña. Solo localhost."""
    if request.method == 'OPTIONS':
        return '', 204
    data = request.get_json() or {}
    user = data.get('user', '').strip()
    password = data.get('password', '')
    
    if user == ADMIN_USER and password == ADMIN_PASS:
        session['admin_logged_in'] = True
        return jsonify({'success': True})
    
    return jsonify({'error': 'Usuario o contraseña incorrectos'}), 401


@bp.route('/logout', methods=['POST'])
@admin_only
def logout():
    """Cerrar sesión."""
    session.pop('admin_logged_in', None)
    return jsonify({'success': True})


@bp.route('/check', methods=['GET'])
@admin_only
def check():
    """Verifica si hay sesión activa."""
    if session.get('admin_logged_in'):
        return jsonify({'logged_in': True})
    return jsonify({'logged_in': False}), 401
