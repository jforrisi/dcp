"""Router for database update automation endpoints."""
from flask import Blueprint, jsonify, request, send_file
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
    'error': None,
    'log_file': None
}

# Directorio para logs de actualización
LOGS_DIR = Path(__file__).parent.parent.parent.parent.parent / "update" / "logs"
LOGS_DIR.mkdir(parents=True, exist_ok=True)


@bp.route('/update/run', methods=['POST'])
def run_update():
    """
    Ejecuta update/update_database.py y guarda el log con timestamp.
    """
    global update_in_progress, update_status
    
    # Evitar ejecuciones simultáneas
    if update_in_progress:
        return jsonify({
            'error': 'Update already in progress',
            'status': update_status
        }), 409
    
    # Crear nombre de archivo de log con timestamp
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    log_file = LOGS_DIR / f"update_{timestamp}.txt"
    
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
            'error': None,
            'log_file': str(log_file.name),
            'progress': []
        }
        
        try:
            # Obtener el directorio raíz del proyecto
            project_root = Path(__file__).parent.parent.parent.parent.parent
            
            # Ruta al script update/update_database.py
            script_path = project_root / 'update' / 'update_database.py'
            
            if not script_path.exists():
                error_msg = f'Script not found: {script_path}'
                update_status.update({
                    'running': False,
                    'completed_at': datetime.now().isoformat(),
                    'returncode': -1,
                    'error': error_msg
                })
                with open(log_file, 'w', encoding='utf-8') as f:
                    f.write(f"ERROR: {error_msg}\n")
                update_in_progress = False
                return
            
            # Determinar Python path
            if os.getenv('RAILWAY_ENVIRONMENT') or os.getenv('RAILWAY'):
                python_path = project_root / 'backend' / 'venv' / 'bin' / 'python'
                if not python_path.exists():
                    python_path = 'python3'
            else:
                python_path = 'python3'
            
            # Ejecutar script y capturar output en tiempo real
            process = subprocess.Popen(
                [str(python_path), str(script_path)],
                cwd=str(project_root),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                universal_newlines=True
            )
            
            # Escribir output en tiempo real al archivo y al status
            output_lines = []
            with open(log_file, 'w', encoding='utf-8') as f:
                f.write(f"=== ACTUALIZACIÓN DE BASE DE DATOS ===\n")
                f.write(f"Inicio: {update_status['started_at']}\n")
                f.write("=" * 80 + "\n\n")
                
                for line in process.stdout:
                    output_lines.append(line)
                    f.write(line)
                    f.flush()
                    
                    # Mantener solo las últimas 100 líneas en memoria
                    if len(output_lines) > 100:
                        output_lines.pop(0)
                    
                    # Actualizar progress con las últimas 5 líneas
                    update_status['progress'] = output_lines[-5:]
            
            process.wait()
            
            # Leer el archivo completo para el output
            with open(log_file, 'r', encoding='utf-8') as f:
                full_output = f.read()
            
            update_status.update({
                'running': False,
                'completed_at': datetime.now().isoformat(),
                'returncode': process.returncode,
                'output': full_output[-50000:] if len(full_output) > 50000 else full_output,  # Últimos 50KB
                'error': None if process.returncode == 0 else f'Script exited with code {process.returncode}'
            })
            
        except subprocess.TimeoutExpired:
            error_msg = 'Timeout: Script took more than 3 hours'
            update_status.update({
                'running': False,
                'completed_at': datetime.now().isoformat(),
                'returncode': -1,
                'error': error_msg
            })
            with open(log_file, 'a', encoding='utf-8') as f:
                f.write(f"\n\nERROR: {error_msg}\n")
        except Exception as e:
            error_msg = str(e)
            update_status.update({
                'running': False,
                'completed_at': datetime.now().isoformat(),
                'returncode': -1,
                'error': error_msg
            })
            with open(log_file, 'a', encoding='utf-8') as f:
                f.write(f"\n\nERROR: {error_msg}\n")
                import traceback
                f.write(traceback.format_exc())
        finally:
            update_in_progress = False
    
    thread = threading.Thread(target=run_script, daemon=True)
    thread.start()
    
    return jsonify({
        'status': 'started',
        'message': 'Update script started in background',
        'started_at': update_status['started_at'],
        'log_file': update_status['log_file']
    })


@bp.route('/update/status', methods=['GET'])
def get_update_status():
    """Obtiene el estado de la última ejecución."""
    return jsonify(update_status)


@bp.route('/update/logs', methods=['GET'])
def list_logs():
    """Lista los últimos 5 archivos de log."""
    try:
        log_files = sorted(LOGS_DIR.glob("update_*.txt"), key=os.path.getmtime, reverse=True)[:5]
        logs = []
        for log_file in log_files:
            stat = log_file.stat()
            logs.append({
                'filename': log_file.name,
                'size': stat.st_size,
                'modified': datetime.fromtimestamp(stat.st_mtime).isoformat(),
                'date': datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d %H:%M:%S')
            })
        return jsonify(logs)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@bp.route('/update/logs/<filename>', methods=['GET'])
def download_log(filename):
    """Descarga un archivo de log específico."""
    try:
        # Validar que el archivo existe y está en el directorio de logs
        log_file = LOGS_DIR / filename
        if not log_file.exists() or not str(log_file).startswith(str(LOGS_DIR)):
            return jsonify({'error': 'File not found'}), 404
        
        return send_file(
            str(log_file),
            mimetype='text/plain',
            as_attachment=True,
            download_name=filename
        )
    except Exception as e:
        return jsonify({'error': str(e)}), 500
