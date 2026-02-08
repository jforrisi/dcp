"""Flask application main file."""
import os
from flask import Flask, send_from_directory, send_file
from flask_cors import CORS
from pathlib import Path
from .routers import ticker, prices, dcp, cotizaciones, inflacion_dolares, yield_curve, data_export, licitaciones_lrm, update

# Create Flask app
static_folder = Path(__file__).parent / 'static'
app = Flask(__name__, static_folder=str(static_folder), static_url_path='/static')

# Configure CORS
CORS(app, resources={r"/*": {"origins": "*"}})

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

# Register admin blueprint only if not in Railway
if not os.getenv('RAILWAY_ENVIRONMENT'):
    try:
        from .routers.admin import bp as admin_bp
        app.register_blueprint(admin_bp)
    except ImportError:
        # Admin routes not available
        pass

# Serve admin panel (must be before catch-all route)
@app.route('/admin')
@app.route('/admin/<path:path>')
def serve_admin(path=''):
    """Serve admin panel frontend (only available locally)."""
    if os.getenv('RAILWAY_ENVIRONMENT'):
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
