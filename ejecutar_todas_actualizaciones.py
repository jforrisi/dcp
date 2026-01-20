"""
Script Ejecutor de Todas las Actualizaciones
============================================
Ejecuta automáticamente todos los scripts de actualización de datos
en precios/update/productos/ y macro/update/
"""

import subprocess
import sys
import traceback
from pathlib import Path
import time
from datetime import datetime
from typing import List, Tuple, Dict
import io


def descubrir_scripts() -> Dict[str, List[Path]]:
    """
    Descubre automáticamente todos los scripts de actualización.
    
    Returns:
        Dict con 'precios' y 'macro' como keys, cada uno con lista de Paths
    """
    scripts = {
        'precios': [],
        'macro': []
    }
    
    # Scripts de precios
    precios_dir = Path("precios/update/productos")
    if precios_dir.exists():
        for script_file in precios_dir.glob("*.py"):
            if script_file.name != "__init__.py" and not script_file.name.startswith("_"):
                scripts['precios'].append(script_file)
    
    # Scripts de macro
    macro_dir = Path("macro/update")
    if macro_dir.exists():
        for script_file in macro_dir.glob("*.py"):
            if script_file.name != "__init__.py" and not script_file.name.startswith("_"):
                scripts['macro'].append(script_file)
    
    # Ordenar por nombre para ejecución consistente
    scripts['precios'].sort(key=lambda x: x.name)
    scripts['macro'].sort(key=lambda x: x.name)
    
    return scripts


def ejecutar_script(ruta_script: Path) -> Tuple[bool, str, float]:
    """
    Ejecuta un script de actualización usando subprocess.
    Lee la salida línea por línea y responde automáticamente a confirmaciones.
    Captura stderr para mostrar errores detallados.
    
    Args:
        ruta_script: Path al script a ejecutar
        
    Returns:
        Tuple (exitoso, mensaje, tiempo_ejecucion)
    """
    inicio = time.time()
    nombre_script = ruta_script.name
    
    try:
        # Ejecutar el script como subprocess
        proceso = subprocess.Popen(
            [sys.executable, str(ruta_script)],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,  # Capturar para leer línea por línea
            stderr=subprocess.PIPE,  # Capturar stderr para análisis
            text=True,
            bufsize=1
        )
        
        # Leer stdout línea por línea y responder a confirmaciones
        import threading
        import queue
        
        output_queue = queue.Queue()
        error_output = []
        
        def leer_stdout():
            """Lee stdout y lo pone en la cola, también lo imprime"""
            try:
                for linea in proceso.stdout:
                    output_queue.put(('stdout', linea))
                    print(linea, end='', flush=True)  # Mostrar en tiempo real
            except:
                pass
        
        def leer_stderr():
            """Lee stderr y lo guarda"""
            try:
                for linea in proceso.stderr:
                    error_output.append(linea)
            except:
                pass
        
        # Iniciar hilos para leer stdout y stderr
        thread_stdout = threading.Thread(target=leer_stdout, daemon=True)
        thread_stderr = threading.Thread(target=leer_stderr, daemon=True)
        thread_stdout.start()
        thread_stderr.start()
        
        # Procesar salida y responder a confirmaciones
        prompts_confirmacion = [
            "¿Confirmás que los datos son correctos",
            "¿Confirmás que querés cambiar a Selenium",
            "¿Desea",
            "¿Está seguro",
            "(sí/no):",
            "(yes/no):"
        ]
        
        respuestas_enviadas = 0
        max_respuestas = 20
        
        while proceso.poll() is None or not output_queue.empty():
            try:
                tipo, linea = output_queue.get(timeout=0.1)
                # Si detectamos un prompt de confirmación, enviar "sí"
                if any(prompt.lower() in linea.lower() for prompt in prompts_confirmacion):
                    if respuestas_enviadas < max_respuestas:
                        proceso.stdin.write("sí\n")
                        proceso.stdin.flush()
                        respuestas_enviadas += 1
            except queue.Empty:
                continue
            except:
                break
        
        # Cerrar stdin
        try:
            proceso.stdin.close()
        except:
            pass
        
        # Esperar a que termine
        proceso.wait(timeout=3600)
        
        # Esperar a que terminen los hilos de lectura
        thread_stdout.join(timeout=1)
        thread_stderr.join(timeout=1)
        
        tiempo = time.time() - inicio
        stderr_text = ''.join(error_output) if error_output else ""
        
        # Verificar código de salida
        if proceso.returncode == 0:
            return True, f"Ejecutado exitosamente", tiempo
        else:
            # Incluir stderr en el mensaje de error si está disponible
            error_msg = f"Error: El script terminó con código {proceso.returncode}"
            if stderr_text:
                # Mostrar últimas líneas del error
                error_lines = stderr_text.strip().split('\n')
                if len(error_lines) > 15:
                    error_msg += f"\nÚltimas 15 líneas del error:\n" + "\n".join(error_lines[-15:])
                else:
                    error_msg += f"\nError completo:\n{stderr_text}"
            return False, error_msg, tiempo
            
    except subprocess.TimeoutExpired:
        proceso.kill()
        tiempo = time.time() - inicio
        return False, f"Timeout: El script tardó más de 1 hora", tiempo
    except KeyboardInterrupt:
        if 'proceso' in locals():
            proceso.kill()
        tiempo = time.time() - inicio
        return False, f"Interrumpido por el usuario", tiempo
    except Exception as e:
        tiempo = time.time() - inicio
        error_msg = f"Error: {str(e)}"
        error_traceback = traceback.format_exc()
        return False, f"{error_msg}\n{error_traceback}", tiempo


def ejecutar_todas_actualizaciones(
    solo_precios: bool = False,
    solo_macro: bool = False,
    scripts_especificos: List[str] = None
) -> None:
    """
    Ejecuta todos los scripts de actualización.
    
    Args:
        solo_precios: Si True, solo ejecuta scripts de precios
        solo_macro: Si True, solo ejecuta scripts de macro
        scripts_especificos: Lista de nombres de scripts a ejecutar (opcional)
    """
    print("=" * 80)
    print("EJECUTOR DE ACTUALIZACIONES")
    print("=" * 80)
    print(f"Fecha/Hora: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Descubrir scripts
    todos_scripts = descubrir_scripts()
    
    # Filtrar según opciones
    scripts_a_ejecutar = []
    
    if scripts_especificos:
        # Ejecutar solo scripts específicos
        for categoria, scripts in todos_scripts.items():
            for script in scripts:
                if script.name in scripts_especificos:
                    scripts_a_ejecutar.append((categoria, script))
    else:
        # Ejecutar todos según filtros
        if not solo_macro:
            for script in todos_scripts['precios']:
                scripts_a_ejecutar.append(('precios', script))
        
        if not solo_precios:
            for script in todos_scripts['macro']:
                scripts_a_ejecutar.append(('macro', script))
    
    if not scripts_a_ejecutar:
        print("[WARN] No se encontraron scripts para ejecutar.")
        return
    
    print(f"Scripts a ejecutar: {len(scripts_a_ejecutar)}")
    print("-" * 80)
    print()
    
    # Ejecutar cada script
    resultados = {
        'exitosos': [],
        'fallidos': [],
        'total_tiempo': 0.0
    }
    
    inicio_total = time.time()
    
    for i, (categoria, script_path) in enumerate(scripts_a_ejecutar, 1):
        nombre_script = script_path.name
        print(f"[{i}/{len(scripts_a_ejecutar)}] Ejecutando: {categoria}/{nombre_script}")
        print("-" * 80)
        
        exitoso, mensaje, tiempo = ejecutar_script(script_path)
        
        if exitoso:
            resultados['exitosos'].append({
                'categoria': categoria,
                'script': nombre_script,
                'tiempo': tiempo,
                'mensaje': mensaje
            })
            print(f"[OK] {nombre_script} - Tiempo: {tiempo:.2f}s")
        else:
            resultados['fallidos'].append({
                'categoria': categoria,
                'script': nombre_script,
                'tiempo': tiempo,
                'error': mensaje
            })
            print(f"[ERROR] {nombre_script}")
            print(f"  {mensaje}")
        
        print()
    
    tiempo_total = time.time() - inicio_total
    resultados['total_tiempo'] = tiempo_total
    
    # Mostrar resumen
    print("=" * 80)
    print("RESUMEN DE EJECUCIÓN")
    print("=" * 80)
    print(f"Total de scripts ejecutados: {len(scripts_a_ejecutar)}")
    print(f"Exitosos: {len(resultados['exitosos'])}")
    print(f"Fallidos: {len(resultados['fallidos'])}")
    print(f"Tiempo total: {tiempo_total:.2f}s")
    print()
    
    if resultados['exitosos']:
        print("SCRIPTS EXITOSOS:")
        print("-" * 80)
        for res in resultados['exitosos']:
            print(f"  ✅ {res['categoria']}/{res['script']} ({res['tiempo']:.2f}s)")
        print()
    
    if resultados['fallidos']:
        print("SCRIPTS CON ERRORES:")
        print("-" * 80)
        for res in resultados['fallidos']:
            print(f"  ❌ {res['categoria']}/{res['script']} ({res['tiempo']:.2f}s)")
            # Mostrar solo primera línea del error para no saturar
            error_linea1 = res['error'].split('\n')[0]
            print(f"     {error_linea1}")
        print()
    
    print("=" * 80)


def main():
    """Función principal con opciones de línea de comandos."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Ejecuta todos los scripts de actualización de datos'
    )
    parser.add_argument(
        '--solo-precios',
        action='store_true',
        help='Ejecutar solo scripts de precios/update/productos'
    )
    parser.add_argument(
        '--solo-macro',
        action='store_true',
        help='Ejecutar solo scripts de macro/update'
    )
    parser.add_argument(
        '--scripts',
        nargs='+',
        help='Ejecutar solo scripts específicos (por nombre de archivo)'
    )
    
    args = parser.parse_args()
    
    ejecutar_todas_actualizaciones(
        solo_precios=args.solo_precios,
        solo_macro=args.solo_macro,
        scripts_especificos=args.scripts
    )


if __name__ == "__main__":
    main()
