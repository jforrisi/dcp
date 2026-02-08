"""Router for database update automation endpoints."""
from flask import Blueprint, jsonify, request, send_file
import subprocess
import os
import sys
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

# Estado de scripts individuales
single_script_status = {}
single_script_in_progress = {}

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


@bp.route('/update/run-single/<script_name>', methods=['POST'])
def run_single_script(script_name):
    """Ejecuta un script individual de descarga."""
    global single_script_in_progress, single_script_status
    
    allowed_scripts = [
        'curva_pesos_uyu_temp',
        'curva_pesos_uyu_ui_temp',
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
    
    def run_script():
        global single_script_in_progress, single_script_status
        
        single_script_in_progress[script_name] = True
        single_script_status[script_name] = {
            'running': True,
            'started_at': datetime.now().isoformat(),
            'completed_at': None,
            'returncode': None,
            'output': None,
            'error': None,
            'log_file': str(log_file.name)
        }
        
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
            
            if os.getenv('RAILWAY_ENVIRONMENT') or os.getenv('RAILWAY'):
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
        'started_at': single_script_status[script_name]['started_at'],
        'log_file': single_script_status[script_name]['log_file']
    })


@bp.route('/update/status-single/<script_name>', methods=['GET'])
def get_single_script_status(script_name):
    """Obtiene el estado de un script individual."""
    if script_name not in single_script_status:
        return jsonify({'error': f'Script {script_name} no encontrado'}), 404
    
    return jsonify(single_script_status[script_name])
