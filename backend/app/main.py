"""Flask application main file."""
from flask import Flask, send_from_directory, send_file
from flask_cors import CORS
from pathlib import Path
from .routers import prices, dcp, cotizaciones

# Create Flask app
static_folder = Path(__file__).parent / 'static'
app = Flask(__name__, static_folder=str(static_folder), static_url_path='/static')

# Configure CORS
CORS(app, resources={r"/*": {"origins": "*"}})

# Register blueprints
app.register_blueprint(prices.bp, url_prefix='/api')
app.register_blueprint(dcp.bp, url_prefix='/api')
app.register_blueprint(cotizaciones.bp, url_prefix='/api')

# Serve static files
@app.route('/')
def index():
    """Serve the main HTML file."""
    index_path = static_folder / 'index.html'
    if index_path.exists():
        return send_file(index_path)
    return {"error": "Frontend not built. Please run build script."}, 404

# Catch-all route for React Router (SPA routing)
@app.route('/<path:path>')
def serve_spa(path):
    """Serve index.html for all non-API routes (React Router)."""
    # Don't interfere with API routes
    if path.startswith('api/'):
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
