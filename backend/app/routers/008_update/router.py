"""Router for database update automation endpoints."""
from flask import Blueprint, jsonify, request, send_file
from ...middleware import admin_session_required
import subprocess
import os
import sys
from pathlib import Path
import threading
from datetime import datetime

bp = Blueprint('update', __name__)

# Variable global para evitar ejecuciones simultáneas
update_in_progress = False
update_process = None  # Referencia al subprocess para poder cancelarlo
update_cancelled = False  # True si el usuario canceló (para no sobrescribir status)
update_status = {
    'running': False,
    'started_at': None,
    'completed_at': None,
    'returncode': None,
    'output': None,
    'error': None,
    'log_file': None,
    'progress': [],
    'elapsed_seconds': None,
}

# Estado de scripts individuales
single_script_status = {}
single_script_in_progress = {}

# Directorio para logs de actualización
LOGS_DIR = Path(__file__).parent.parent.parent.parent.parent / "update" / "logs"
LOGS_DIR.mkdir(parents=True, exist_ok=True)


@bp.route('/update/run', methods=['POST'])
@admin_session_required
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
        global update_in_progress, update_status, update_process, update_cancelled
        update_in_progress = True
        update_process = None
        update_cancelled = False
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
            
            # Determinar Python path - usar el mismo Python que ejecuta el servidor
            # En Anaconda en Windows, sys.executable puede no ser directamente ejecutable
            # Intentar obtener el python.exe real
            python_path_str = sys.executable
            
            # Si es un .exe de Anaconda, buscar python.exe en el mismo directorio
            if python_path_str.lower().endswith('.exe') and not python_path_str.lower().endswith('python.exe'):
                python_dir = os.path.dirname(python_path_str)
                python_exe = os.path.join(python_dir, 'python.exe')
                if os.path.exists(python_exe):
                    python_path_str = python_exe
            
            # Log de debugging
            print(f"[DEBUG] Python path: {python_path_str}")
            print(f"[DEBUG] Python exists: {os.path.exists(python_path_str)}")
            print(f"[DEBUG] Script path: {script_path}")
            print(f"[DEBUG] Script exists: {script_path.exists()}")
            print(f"[DEBUG] Project root: {project_root}")
            
            # Validar que el ejecutable existe
            if not os.path.exists(python_path_str):
                error_msg = f'Python executable not found: {python_path_str}'
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
            
            # Validar que el script existe
            script_path_str = str(script_path)
            if not os.path.exists(script_path_str):
                error_msg = f'Script not found: {script_path_str}'
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
            
            print(f"[DEBUG] About to execute: [{python_path_str}, {script_path_str}]")
            print(f"[DEBUG] Working directory: {project_root}")
            
            try:
                # Ejecutar script y capturar output en tiempo real
                process = subprocess.Popen(
                    [python_path_str, script_path_str],
                    cwd=str(project_root),
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    bufsize=1,
                    universal_newlines=True
                )
                update_process = process
            except FileNotFoundError as e:
                error_msg = f'Failed to execute subprocess: {e}\nPython: {python_path_str}\nScript: {script_path_str}'
                print(f"[ERROR] {error_msg}")
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
            
            # Escribir output en tiempo real al archivo y al status (con timestamps)
            PROGRESS_LINES = 25  # Más líneas para debug
            output_lines = []
            with open(log_file, 'w', encoding='utf-8') as f:
                f.write(f"=== ACTUALIZACIÓN DE BASE DE DATOS ===\n")
                f.write(f"Inicio: {update_status['started_at']}\n")
                f.write("=" * 80 + "\n\n")
                
                for line in process.stdout:
                    ts = datetime.now().strftime('%H:%M:%S')
                    line_with_ts = f"[{ts}] {line}"
                    output_lines.append(line_with_ts)
                    f.write(line)
                    f.flush()
                    
                    # Mantener últimas 200 líneas en memoria para progress
                    if len(output_lines) > 200:
                        output_lines.pop(0)
                    
                    # Actualizar progress con las últimas N líneas
                    update_status['progress'] = output_lines[-PROGRESS_LINES:]
                    # Tiempo transcurrido
                    start = datetime.fromisoformat(update_status['started_at'])
                    update_status['elapsed_seconds'] = int((datetime.now() - start).total_seconds())
            
            process.wait()
            
            # No sobrescribir si el usuario canceló (el cancel handler ya actualizó el status)
            if update_cancelled:
                return
            
            # Leer el archivo completo para el output
            with open(log_file, 'r', encoding='utf-8') as f:
                full_output = f.read()
            
            start = datetime.fromisoformat(update_status['started_at'])
            elapsed = int((datetime.now() - start).total_seconds())
            update_status.update({
                'running': False,
                'completed_at': datetime.now().isoformat(),
                'returncode': process.returncode,
                'output': full_output[-50000:] if len(full_output) > 50000 else full_output,
                'error': None if process.returncode == 0 else f'Script exited with code {process.returncode}',
                'elapsed_seconds': elapsed,
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
            # Si fue cancelado por el usuario, no sobrescribir el status
            if update_cancelled:
                pass
            else:
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
            update_process = None
    
    thread = threading.Thread(target=run_script, daemon=True)
    thread.start()
    
    return jsonify({
        'status': 'started',
        'message': 'Update script started in background',
        'started_at': update_status['started_at'],
        'log_file': update_status['log_file']
    })


@bp.route('/update/cancel', methods=['POST'])
@admin_session_required
def cancel_update():
    """Cancela la actualización en curso si hay una."""
    global update_in_progress, update_process, update_status, update_cancelled
    if not update_in_progress or update_process is None:
        return jsonify({
            'status': 'nothing_to_cancel',
            'message': 'No hay actualización en curso'
        }), 200
    try:
        update_cancelled = True
        update_process.terminate()
        # Dar tiempo a que termine
        try:
            update_process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            update_process.kill()
        update_status.update({
            'running': False,
            'completed_at': datetime.now().isoformat(),
            'returncode': -9,
            'error': 'Actualización cancelada por el usuario',
            'elapsed_seconds': int((datetime.now() - datetime.fromisoformat(update_status['started_at'])).total_seconds()) if update_status.get('started_at') else None
        })
        update_process = None
        update_in_progress = False
        return jsonify({
            'status': 'cancelled',
            'message': 'Actualización cancelada correctamente'
        })
    except Exception as e:
        return jsonify({
            'error': f'Error al cancelar: {str(e)}'
        }), 500


@bp.route('/update/status', methods=['GET'])
@admin_session_required
def get_update_status():
    """Obtiene el estado de la última ejecución."""
    status = dict(update_status)
    if status.get('running') and status.get('started_at'):
        start = datetime.fromisoformat(status['started_at'])
        status['elapsed_seconds'] = int((datetime.now() - start).total_seconds())
    return jsonify(status)


@bp.route('/update/logs', methods=['GET'])
@admin_session_required
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
@admin_session_required
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


@bp.route('/update/run-single/<script_name>', methods=['POST'])
@admin_session_required
def run_single_script(script_name):
    """Ejecuta un script individual de descarga."""
    global single_script_in_progress, single_script_status
    
    allowed_scripts = [
        'curva_pesos_uyu_temp',
        'curva_pesos_uyu_ui_temp',
        'dolar_bevsa_uyu',
        'ipc_colombia',
        'ipc_paraguay'
    ]
    
    if script_name not in allowed_scripts:
        return jsonify({'error': f'Script no permitido: {script_name}'}), 400
    
    if single_script_in_progress.get(script_name, False):
        return jsonify({
            'error': f'Script {script_name} ya está en ejecución',
            'status': single_script_status.get(script_name, {})
        }), 409
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    log_file = LOGS_DIR / f"{script_name}_{timestamp}.log"
    
    # Inicializar estado antes de iniciar el thread
    single_script_in_progress[script_name] = True
    started_at = datetime.now().isoformat()
    single_script_status[script_name] = {
        'running': True,
        'started_at': started_at,
        'completed_at': None,
        'returncode': None,
        'output': None,
        'error': None,
        'log_file': str(log_file.name)
    }
    
    def run_script():
        global single_script_in_progress, single_script_status
        
        try:
            project_root = Path(__file__).parent.parent.parent.parent.parent
            script_path = project_root / 'update' / 'run_single.py'
            
            if not script_path.exists():
                error_msg = f'Script runner no encontrado: {script_path}'
                single_script_status[script_name].update({
                    'running': False,
                    'completed_at': datetime.now().isoformat(),
                    'returncode': -1,
                    'error': error_msg
                })
                with open(log_file, 'w', encoding='utf-8') as f:
                    f.write(f"ERROR: {error_msg}\n")
                single_script_in_progress[script_name] = False
                return
            
            if os.getenv('RAILWAY_ENVIRONMENT') or os.getenv('RAILWAY') or os.getenv('AZURE_ENVIRONMENT'):
                python_path = project_root / 'backend' / 'venv' / 'bin' / 'python'
                if not python_path.exists():
                    python_path = 'python3'
            else:
                python_path = 'python3'
            
            process = subprocess.Popen(
                [str(python_path), str(script_path), script_name],
                cwd=str(project_root),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                universal_newlines=True
            )
            
            output_lines = []
            with open(log_file, 'w', encoding='utf-8') as f:
                f.write(f"=== EJECUCIÓN DE SCRIPT INDIVIDUAL ===\n")
                f.write(f"Script: {script_name}\n")
                f.write(f"Inicio: {single_script_status[script_name]['started_at']}\n")
                f.write("=" * 80 + "\n\n")
                
                for line in process.stdout:
                    output_lines.append(line)
                    f.write(line)
                    f.flush()
                    
                    if len(output_lines) > 100:
                        output_lines.pop(0)
                    
                    single_script_status[script_name]['progress'] = output_lines[-10:]
            
            process.wait()
            
            with open(log_file, 'r', encoding='utf-8') as f:
                full_output = f.read()
            
            single_script_status[script_name].update({
                'running': False,
                'completed_at': datetime.now().isoformat(),
                'returncode': process.returncode,
                'output': full_output[-50000:] if len(full_output) > 50000 else full_output,
                'error': None if process.returncode == 0 else f'Script exited with code {process.returncode}'
            })
            
        except subprocess.TimeoutExpired:
            error_msg = 'Timeout: Script tomó más de 3 horas'
            single_script_status[script_name].update({
                'running': False,
                'completed_at': datetime.now().isoformat(),
                'returncode': -1,
                'error': error_msg
            })
            with open(log_file, 'a', encoding='utf-8') as f:
                f.write(f"\n\nERROR: {error_msg}\n")
        except Exception as e:
            error_msg = str(e)
            single_script_status[script_name].update({
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
            single_script_in_progress[script_name] = False
    
    thread = threading.Thread(target=run_script, daemon=True)
    thread.start()
    
    return jsonify({
        'status': 'started',
        'message': f'Script {script_name} iniciado en background',
        'started_at': started_at,
        'log_file': str(log_file.name)
    })


@bp.route('/update/status-single/<script_name>', methods=['GET'])
@admin_session_required
def get_single_script_status(script_name):
    """Obtiene el estado de un script individual."""
    if script_name not in single_script_status:
        return jsonify({'error': f'Script {script_name} no encontrado'}), 404
    
    return jsonify(single_script_status[script_name])
