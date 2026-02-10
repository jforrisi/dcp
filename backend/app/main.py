"""Flask application main file."""
import os
import sys
from pathlib import Path

# Agregar raíz del proyecto al path (para módulo db)
_project_root = Path(__file__).resolve().parent.parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from flask import Flask, send_from_directory, send_file, request, jsonify, session
from flask_cors import CORS
from pathlib import Path
from .routers import ticker, prices, dcp, cotizaciones, inflacion_dolares, yield_curve, data_export, licitaciones_lrm, update

# Create Flask app
static_folder = Path(__file__).parent / 'static'
app = Flask(__name__, static_folder=str(static_folder), static_url_path='/static')
app.secret_key = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')

# Configure CORS (supports_credentials requiere orígenes explícitos, no "*")
_ports = [5000, 8000, 3000]
_cors_origins = [f"http://localhost:{p}" for p in _ports] + [f"http://127.0.0.1:{p}" for p in _ports]
# Permitir acceso desde IP local (172.20.10.14 en tu red)
_cors_origins.extend([f"http://172.20.10.14:{p}" for p in _ports])
CORS(app, resources={
    r"/api/*": {
        "origins": _cors_origins,
        "supports_credentials": True,
        "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization"],
    },
    r"/*": {"origins": "*"},
})

# Rutas de auth ANTES de blueprints (prioridad máxima)
def _is_admin_authenticated():
    """Verifica sesión o token Bearer (evita dependencia de cookies)."""
    if session.get('admin_logged_in'):
        return True
    auth = request.headers.get('Authorization', '')
    if auth.startswith('Bearer '):
        token = auth[7:].strip()
        from . import admin_tokens
        return admin_tokens.has_token(token)
    return False

try:
    import uuid
    from . import admin_tokens
    from .middleware import admin_only, ADMIN_USER, ADMIN_PASS

    @app.route('/api/admin/ping', methods=['GET'], strict_slashes=False)
    def admin_ping():
        """Diagnóstico: retorna OK si las rutas admin están activas (sin auth)."""
        return jsonify({'ok': True, 'msg': 'Admin routes active'})

    @app.route('/api/admin/check', methods=['GET', 'OPTIONS'], strict_slashes=False)
    @admin_only
    def admin_check():
        if request.method == 'OPTIONS':
            return '', 204
        if _is_admin_authenticated():
            return jsonify({'logged_in': True})
        return jsonify({'logged_in': False}), 401

    @app.route('/api/admin/login', methods=['POST', 'OPTIONS'], strict_slashes=False)
    @admin_only
    def admin_login():
        if request.method == 'OPTIONS':
            return '', 204
        data = request.get_json() or {}
        user = data.get('user', '').strip()
        password = data.get('password', '')
        if user == ADMIN_USER and password == ADMIN_PASS:
            session['admin_logged_in'] = True
            token = str(uuid.uuid4())
            admin_tokens.add_token(token)
            return jsonify({'success': True, 'token': token})
        return jsonify({'error': 'Usuario o contraseña incorrectos'}), 401

    @app.route('/api/admin/logout', methods=['POST', 'OPTIONS'], strict_slashes=False)
    @admin_only
    def admin_logout():
        if request.method == 'OPTIONS':
            return '', 204
        session.pop('admin_logged_in', None)
        auth = request.headers.get('Authorization', '')
        if auth.startswith('Bearer '):
            admin_tokens.remove_token(auth[7:].strip())
        return jsonify({'success': True})
except ImportError:
    pass

# Register blueprints
app.register_blueprint(ticker.ticker, url_prefix='')
app.register_blueprint(data_export, url_prefix='/api')
app.register_blueprint(prices.bp, url_prefix='/api')
app.register_blueprint(dcp.bp, url_prefix='/api')
app.register_blueprint(cotizaciones.bp, url_prefix='/api')
app.register_blueprint(inflacion_dolares.bp, url_prefix='/api')
app.register_blueprint(yield_curve.bp, url_prefix='/api')
app.register_blueprint(licitaciones_lrm.bp, url_prefix='/api')
app.register_blueprint(update.bp, url_prefix='/api')

# Register admin blueprint only if not in production (Azure/Railway)
if not (os.getenv('RAILWAY_ENVIRONMENT') or os.getenv('AZURE_ENVIRONMENT')):
    try:
        from .routers.admin import bp as admin_bp
        app.register_blueprint(admin_bp)
    except ImportError:
        pass

# Serve admin panel (must be before catch-all route)
@app.route('/admin')
@app.route('/admin/<path:path>')
def serve_admin(path=''):
    """Serve admin panel frontend (only available locally)."""
    if os.getenv('RAILWAY_ENVIRONMENT') or os.getenv('AZURE_ENVIRONMENT'):
        return {"error": "Admin panel not available in production"}, 404
    
    # If it's a request for a static file, serve it
    if path and path != '':
        static_file = static_folder / 'admin' / path
        if static_file.exists() and static_file.is_file():
            return send_file(static_file)
    
    # Otherwise, serve index.html
    admin_index = static_folder / 'admin' / 'index.html'
    if admin_index.exists():
        return send_file(admin_index)
    return {"error": "Admin panel not found"}, 404

# Serve static files
@app.route('/')
def index():
    """Serve the main HTML file."""
    index_path = static_folder / 'index.html'
    if index_path.exists():
        return send_file(index_path)
    return {"error": "Frontend not built. Please run build script."}, 404

# Catch-all route for React Router (SPA routing)
# This should only catch routes that haven't been matched by blueprints
# Flask will only reach here if no blueprint route matched
@app.route('/<path:path>')
def serve_spa(path):
    """Serve index.html for all non-API routes (React Router)."""
    # Don't interfere with API routes or admin routes - these should be handled by blueprints
    # If we reach here for api/ or admin/, it means the route doesn't exist
    if path.startswith('api/') or path.startswith('admin/'):
        return {"error": "Not found"}, 404
    
    # Check if it's a static file request
    static_file = static_folder / path
    if static_file.exists() and static_file.is_file():
        return send_file(static_file)
    
    # Otherwise, serve index.html for React Router
    index_path = static_folder / 'index.html'
    if index_path.exists():
        return send_file(index_path)
    return {"error": "Frontend not built. Please run build script."}, 404

@app.route('/health')
def health_check():
    """Health check endpoint."""
    return {"status": "ok"}
