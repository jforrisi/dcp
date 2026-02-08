"""Router for database update automation endpoints."""
from flask import Blueprint, jsonify, request
import subprocess
import os
from pathlib import Path
import threading
from datetime import datetime

bp = Blueprint('update', __name__)

# Variable global para evitar ejecuciones simultáneas
update_in_progress = False
update_status = {
    'running': False,
    'started_at': None,
    'completed_at': None,
    'returncode': None,
    'output': None,
    'error': None
}


@bp.route('/update/run', methods=['POST'])
def run_update():
    """
    Ejecuta update_database.py desde Railway.
    Requiere token secreto para autenticación.
    """
    global update_in_progress, update_status
    
    # Verificar token secreto
    token = request.headers.get('Authorization') or (request.json.get('token') if request.json else None)
    expected_token = os.getenv('UPDATE_TOKEN')
    
    if not expected_token:
        return jsonify({'error': 'UPDATE_TOKEN not configured'}), 500
    
    # Remover "Bearer " si está presente
    if token and token.startswith('Bearer '):
        token = token[7:]
    
    if token != expected_token:
        return jsonify({'error': 'Unauthorized'}), 401
    
    # Evitar ejecuciones simultáneas
    if update_in_progress:
        return jsonify({
            'error': 'Update already in progress',
            'status': update_status
        }), 409
    
    # Ejecutar en thread separado para no bloquear
    def run_script():
        global update_in_progress, update_status
        update_in_progress = True
        update_status = {
            'running': True,
            'started_at': datetime.now().isoformat(),
            'completed_at': None,
            'returncode': None,
            'output': None,
            'error': None
        }
        
        try:
            # Obtener el directorio raíz del proyecto
            # Desde backend/app/routers/008_update/router.py -> raíz
            project_root = Path(__file__).parent.parent.parent.parent.parent
            
            # Ruta al script update_database.py
            script_path = project_root / 'update_database.py'
            
            if not script_path.exists():
                update_status = {
                    'running': False,
                    'started_at': update_status['started_at'],
                    'completed_at': datetime.now().isoformat(),
                    'returncode': -1,
                    'error': f'Script not found: {script_path}'
                }
                update_in_progress = False
                return
            
            # Usar el Python del venv si está en Railway
            if os.getenv('RAILWAY_ENVIRONMENT') or os.getenv('RAILWAY'):
                python_path = project_root / 'backend' / 'venv' / 'bin' / 'python'
                if not python_path.exists():
                    python_path = 'python3'
            else:
                python_path = 'python3'
            
            result = subprocess.run(
                [str(python_path), str(script_path)],
                cwd=str(project_root),
                capture_output=True,
                text=True,
                timeout=10800  # 3 horas máximo
            )
            
            update_status = {
                'running': False,
                'started_at': update_status['started_at'],
                'completed_at': datetime.now().isoformat(),
                'returncode': result.returncode,
                'output': result.stdout[-10000:] if result.stdout else None,  # Últimos 10KB
                'error': result.stderr[-5000:] if result.stderr else None
            }
        except subprocess.TimeoutExpired:
            update_status = {
                'running': False,
                'started_at': update_status['started_at'],
                'completed_at': datetime.now().isoformat(),
                'returncode': -1,
                'error': 'Timeout: Script took more than 3 hours'
            }
        except Exception as e:
            update_status = {
                'running': False,
                'started_at': update_status['started_at'],
                'completed_at': datetime.now().isoformat(),
                'returncode': -1,
                'error': str(e)
            }
        finally:
            update_in_progress = False
    
    thread = threading.Thread(target=run_script, daemon=True)
    thread.start()
    
    return jsonify({
        'status': 'started',
        'message': 'Update script started in background',
        'started_at': update_status['started_at']
    })


@bp.route('/update/status', methods=['GET'])
def get_update_status():
    """Obtiene el estado de la última ejecución."""
    return jsonify(update_status)
