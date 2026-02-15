"""
Script de Actualización Automática de Base de Datos
===================================================
Ejecuta automáticamente todos los scripts de actualización en el orden correcto:
1. FASE 1: Descargar Excels (update/download/)
2. FASE 2: Actualizar BD (update/direct/ y update/calculate/)

Genera un reporte en update_database.txt con errores y resumen.
Diseñado para ejecutarse automáticamente (cron/task scheduler/Azure/GitHub Actions).
"""

import subprocess
import sys
import traceback
from pathlib import Path
import time
from datetime import datetime
from typing import List, Tuple, Dict
import os

# Detectar la raíz del proyecto (directorio padre de update/)
SCRIPT_DIR = Path(__file__).parent.absolute()
PROJECT_ROOT = SCRIPT_DIR.parent  # Raíz del proyecto

# Configuración
REPORTE_FILE = PROJECT_ROOT / "update_database.txt"
TIMEOUT_SCRIPT = 3600  # 1 hora máximo por script


def descubrir_scripts_download() -> Dict[str, List[Path]]:
    """
    Descubre automáticamente todos los scripts de descarga.
    
    Returns:
        Dict con categorías como keys, cada una con lista de Paths
    """
    scripts = {
        'download': []
    }
    
    # Scripts de update/download/ (relativo a raíz del proyecto)
    download_dir = PROJECT_ROOT / "update" / "download"
    if download_dir.exists():
        for script_file in download_dir.glob("*.py"):
            if script_file.name != "__init__.py" and not script_file.name.startswith("_"):
                scripts['download'].append(script_file)
    
    # Ordenar por nombre para ejecución consistente
    scripts['download'].sort(key=lambda x: x.name)
    
    return scripts


def descubrir_scripts_update() -> Dict[str, List[Path]]:
    """
    Descubre automáticamente todos los scripts de actualización.
    
    Returns:
        Dict con categorías como keys, cada una con lista de Paths
        Orden: 'direct' primero, luego 'calculate'
    """
    scripts = {
        'direct': [],      # Scripts que obtienen datos de fuentes externas
        'calculate': []    # Scripts que calculan a partir de otros datos
    }
    
    # Scripts de update/direct/ (relativo a raíz del proyecto)
    direct_dir = PROJECT_ROOT / "update" / "direct"
    if direct_dir.exists():
        for script_file in sorted(direct_dir.glob("*.py")):
            if script_file.name != "__init__.py" and not script_file.name.startswith("_"):
                # Incluir todos los scripts (incluyendo 019_nxr_argy_cargar_historico.py que ahora hace todo)
                scripts['direct'].append(script_file)
    
    # Scripts de update/calculate/ (scripts que se alimentan de otros)
    calculate_dir = PROJECT_ROOT / "update" / "calculate"
    if calculate_dir.exists():
        for script_file in sorted(calculate_dir.glob("*.py")):
            if script_file.name != "__init__.py" and not script_file.name.startswith("_"):
                scripts['calculate'].append(script_file)
    
    # Ordenar por nombre para ejecución consistente
    for categoria in scripts:
        scripts[categoria].sort(key=lambda x: x.name)
    
    return scripts


def ejecutar_script(ruta_script: Path, modo_automatico: bool = True) -> Tuple[bool, str, float, str]:
    """
    Ejecuta un script usando subprocess.
    En modo automático, responde automáticamente "sí" a todas las confirmaciones.
    
    Args:
        ruta_script: Path al script a ejecutar
        modo_automatico: Si True, responde automáticamente a confirmaciones
        
    Returns:
        Tuple (exitoso, mensaje, tiempo_ejecucion, output_completo)
    """
    inicio = time.time()
    nombre_script = ruta_script.name
    output_completo = []
    
    try:
        # Cambiar al directorio del proyecto para que los scripts funcionen correctamente
        cwd_original = os.getcwd()
        os.chdir(PROJECT_ROOT)
        
        try:
            # Ejecutar el script como subprocess
            proceso = subprocess.Popen(
                [sys.executable, str(ruta_script)],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,  # Combinar stderr con stdout
                text=True,
                bufsize=1,
                universal_newlines=True,
                cwd=PROJECT_ROOT
            )
            
            # Leer output línea por línea
            import threading
            import queue
            
            output_queue = queue.Queue()
            
            def leer_output():
                """Lee stdout/stderr y lo pone en la cola"""
                try:
                    for linea in proceso.stdout:
                        output_queue.put(linea)
                        output_completo.append(linea)
                except:
                    pass
            
            thread_output = threading.Thread(target=leer_output, daemon=True)
            thread_output.start()
            
            # Procesar output y responder a confirmaciones si está en modo automático
            prompts_confirmacion = [
                "¿confirmás que los datos son correctos",
                "¿confirmás que querés cambiar a selenium",
                "¿confirmás la inserción",
                "¿desea",
                "¿está seguro",
                "(sí/no):",
                "(yes/no):",
                "confirmar",
                "¿confirmas"
            ]
            
            respuestas_enviadas = 0
            max_respuestas = 30
            
            while proceso.poll() is None or not output_queue.empty():
                try:
                    linea = output_queue.get(timeout=0.1)
                    
                    # Si detectamos un prompt de confirmación y estamos en modo automático
                    if modo_automatico:
                        linea_lower = linea.lower()
                        if any(prompt in linea_lower for prompt in prompts_confirmacion):
                            if respuestas_enviadas < max_respuestas:
                                try:
                                    proceso.stdin.write("sí\n")
                                    proceso.stdin.flush()
                                    respuestas_enviadas += 1
                                except:
                                    pass
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
            try:
                proceso.wait(timeout=TIMEOUT_SCRIPT)
            except subprocess.TimeoutExpired:
                proceso.kill()
                tiempo = time.time() - inicio
                return False, f"Timeout: El script tardó más de {TIMEOUT_SCRIPT}s", tiempo, ''.join(output_completo)
            
            # Esperar a que termine el hilo
            thread_output.join(timeout=2)
            
            tiempo = time.time() - inicio
            output_text = ''.join(output_completo)
            
            # Verificar código de salida
            if proceso.returncode == 0:
                return True, "Ejecutado exitosamente", tiempo, output_text
            else:
                # Extraer mensaje de error relevante
                error_lines = output_text.strip().split('\n')
                error_msg = f"Error: El script terminó con código {proceso.returncode}"
                
                # Buscar líneas de error relevantes
                error_relevant = []
                for i, line in enumerate(error_lines):
                    if any(keyword in line.lower() for keyword in ['error', 'exception', 'traceback', 'failed', 'fallo']):
                        # Incluir contexto (líneas antes y después)
                        start = max(0, i - 2)
                        end = min(len(error_lines), i + 5)
                        error_relevant.extend(error_lines[start:end])
                
                if error_relevant:
                    error_msg += "\n" + "\n".join(error_relevant[-20:])  # Últimas 20 líneas relevantes
                elif len(error_lines) > 10:
                    error_msg += "\n" + "\n".join(error_lines[-10:])  # Últimas 10 líneas
                
                return False, error_msg, tiempo, output_text
        finally:
            # Restaurar directorio original
            os.chdir(cwd_original)
            
    except KeyboardInterrupt:
        if 'proceso' in locals():
            proceso.kill()
        tiempo = time.time() - inicio
        return False, "Interrumpido por el usuario", tiempo, ''.join(output_completo)
    except Exception as e:
        tiempo = time.time() - inicio
        error_msg = f"Error al ejecutar script: {str(e)}"
        error_traceback = traceback.format_exc()
        return False, f"{error_msg}\n{error_traceback}", tiempo, ''.join(output_completo)


def generar_reporte(resultados_fase1: Dict, resultados_fase2: Dict, tiempo_total: float) -> str:
    """
    Genera el contenido del reporte en formato texto.
    
    Args:
        resultados_fase1: Dict con 'exitosos' y 'fallidos' de FASE 1
        resultados_fase2: Dict con 'exitosos' y 'fallidos' de FASE 2
        tiempo_total: Tiempo total de ejecución
        
    Returns:
        String con el contenido del reporte
    """
    reporte = []
    reporte.append("=" * 80)
    reporte.append("REPORTE DE ACTUALIZACIÓN DE BASE DE DATOS")
    reporte.append("=" * 80)
    reporte.append(f"Fecha/Hora de ejecución: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    reporte.append("")
    
    # Resumen general
    total_fase1 = len(resultados_fase1['exitosos']) + len(resultados_fase1['fallidos'])
    total_fase2 = len(resultados_fase2['exitosos']) + len(resultados_fase2['fallidos'])
    total_scripts = total_fase1 + total_fase2
    
    reporte.append("RESUMEN GENERAL")
    reporte.append("-" * 80)
    reporte.append(f"Total de scripts ejecutados: {total_scripts}")
    reporte.append(f"  - FASE 1 (Descargas): {total_fase1}")
    reporte.append(f"  - FASE 2 (Actualizaciones): {total_fase2}")
    reporte.append("")
    reporte.append(f"Exitosos: {len(resultados_fase1['exitosos']) + len(resultados_fase2['exitosos'])}")
    reporte.append(f"  - FASE 1: {len(resultados_fase1['exitosos'])}")
    reporte.append(f"  - FASE 2: {len(resultados_fase2['exitosos'])}")
    reporte.append("")
    reporte.append(f"Fallidos: {len(resultados_fase1['fallidos']) + len(resultados_fase2['fallidos'])}")
    reporte.append(f"  - FASE 1: {len(resultados_fase1['fallidos'])}")
    reporte.append(f"  - FASE 2: {len(resultados_fase2['fallidos'])}")
    reporte.append("")
    reporte.append(f"Tiempo total: {tiempo_total:.2f} segundos ({tiempo_total/60:.2f} minutos)")
    reporte.append("")
    
    # FASE 1: Scripts exitosos
    if resultados_fase1['exitosos']:
        reporte.append("FASE 1 - SCRIPTS DE DESCARGA EJECUTADOS EXITOSAMENTE")
        reporte.append("-" * 80)
        for res in resultados_fase1['exitosos']:
            categoria = res['categoria']
            script = res['script']
            tiempo = res['tiempo']
            reporte.append(f"  [OK] {categoria}/{script} ({tiempo:.2f}s)")
        reporte.append("")
    
    # FASE 2: Scripts exitosos
    if resultados_fase2['exitosos']:
        reporte.append("FASE 2 - SCRIPTS DE ACTUALIZACIÓN EJECUTADOS EXITOSAMENTE")
        reporte.append("-" * 80)
        for res in resultados_fase2['exitosos']:
            categoria = res['categoria']
            script = res['script']
            tiempo = res['tiempo']
            reporte.append(f"  [OK] {categoria}/{script} ({tiempo:.2f}s)")
        reporte.append("")
    
    # Errores FASE 1
    if resultados_fase1['fallidos']:
        reporte.append("=" * 80)
        reporte.append("ERRORES EN FASE 1 (DESCARGAS)")
        reporte.append("=" * 80)
        reporte.append("")
        
        for i, res in enumerate(resultados_fase1['fallidos'], 1):
            categoria = res['categoria']
            script = res['script']
            tiempo = res['tiempo']
            error = res['error']
            
            reporte.append(f"ERROR #{i}: {categoria}/{script}")
            reporte.append("-" * 80)
            reporte.append(f"Tiempo de ejecución: {tiempo:.2f}s")
            reporte.append("")
            reporte.append("Detalle del error:")
            reporte.append(error)
            reporte.append("")
            reporte.append("=" * 80)
            reporte.append("")
    
    # Errores FASE 2
    if resultados_fase2['fallidos']:
        reporte.append("=" * 80)
        reporte.append("ERRORES EN FASE 2 (ACTUALIZACIONES)")
        reporte.append("=" * 80)
        reporte.append("")
        
        for i, res in enumerate(resultados_fase2['fallidos'], 1):
            categoria = res['categoria']
            script = res['script']
            tiempo = res['tiempo']
            error = res['error']
            
            reporte.append(f"ERROR #{i}: {categoria}/{script}")
            reporte.append("-" * 80)
            reporte.append(f"Tiempo de ejecución: {tiempo:.2f}s")
            reporte.append("")
            reporte.append("Detalle del error:")
            reporte.append(error)
            reporte.append("")
            reporte.append("=" * 80)
            reporte.append("")
    
    # Resumen final
    total_errores = len(resultados_fase1['fallidos']) + len(resultados_fase2['fallidos'])
    if total_errores == 0:
        reporte.append("=" * 80)
        reporte.append("NO SE DETECTARON ERRORES")
        reporte.append("=" * 80)
        reporte.append("Todos los scripts se ejecutaron exitosamente.")
        reporte.append("")
    
    reporte.append("=" * 80)
    reporte.append(f"Fin del reporte - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    reporte.append("=" * 80)
    
    return "\n".join(reporte)


def ejecutar_fase_descargas() -> Dict:
    """
    Ejecuta FASE 1: Todos los scripts de descarga.
    
    Returns:
        Dict con 'exitosos' y 'fallidos'
    """
    print("=" * 80)
    print("FASE 1: DESCARGAR ARCHIVOS EXCEL")
    print("=" * 80)
    print()
    
    # Descubrir scripts de descarga
    todos_scripts = descubrir_scripts_download()
    
    # Preparar lista de scripts a ejecutar
    scripts_a_ejecutar = []
    
    for categoria, scripts in todos_scripts.items():
        for script in scripts:
            scripts_a_ejecutar.append((categoria, script))
    
    if not scripts_a_ejecutar:
        print("[INFO] No se encontraron scripts de descarga.")
        return {'exitosos': [], 'fallidos': []}
    
    print(f"Scripts de descarga detectados: {len(scripts_a_ejecutar)}")
    print("-" * 80)
    for categoria, script in scripts_a_ejecutar:
        print(f"  - {categoria}/{script.name}")
    print()
    
    # Ejecutar cada script
    resultados = {
        'exitosos': [],
        'fallidos': []
    }
    
    for i, (categoria, script_path) in enumerate(scripts_a_ejecutar, 1):
        nombre_script = script_path.name
        print(f"[{i}/{len(scripts_a_ejecutar)}] Ejecutando: {categoria}/{nombre_script}")
        print("-" * 80)
        
        exitoso, mensaje, tiempo, output = ejecutar_script(script_path, modo_automatico=True)
        
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
            print(f"  {mensaje[:200]}...")  # Primeros 200 caracteres
        
        print()
    
    return resultados


def ejecutar_fase_actualizaciones() -> Dict:
    """
    Ejecuta FASE 2: Todos los scripts de actualización.
    Orden: primero todos los de 'direct', luego todos los de 'calculate'
    
    Returns:
        Dict con 'exitosos' y 'fallidos'
    """
    print("=" * 80)
    print("FASE 2: ACTUALIZAR BASE DE DATOS")
    print("=" * 80)
    print()
    
    # Descubrir scripts de actualización
    todos_scripts = descubrir_scripts_update()
    
    # Preparar lista de scripts a ejecutar EN ORDEN:
    # 1. Primero todos los de 'direct'
    # 2. Luego todos los de 'calculate'
    scripts_a_ejecutar = []
    
    # Orden explícito: direct primero, calculate después
    orden_categorias = ['direct', 'calculate']
    
    for categoria in orden_categorias:
        if categoria in todos_scripts:
            for script in todos_scripts[categoria]:
                scripts_a_ejecutar.append((categoria, script))
    
    if not scripts_a_ejecutar:
        print("[WARN] No se encontraron scripts de actualización.")
        return {'exitosos': [], 'fallidos': []}
    
    print(f"Scripts de actualización detectados: {len(scripts_a_ejecutar)}")
    print("-" * 80)
    print("Orden de ejecución:")
    cat_actual = None
    for categoria, script in scripts_a_ejecutar:
        if categoria != cat_actual:
            cat_actual = categoria
            etiqueta = "DIRECT (fuentes externas)" if categoria == 'direct' else "CALCULATE (cálculos derivados)"
            num = 1 if categoria == 'direct' else 2
            print(f"  {num}. {etiqueta}:")
        print(f"     - {script.name}")
    print()
    
    # Ejecutar cada script
    resultados = {
        'exitosos': [],
        'fallidos': []
    }
    
    for i, (categoria, script_path) in enumerate(scripts_a_ejecutar, 1):
        nombre_script = script_path.name
        tipo = "DIRECT" if categoria == 'direct' else "CALCULATE"
        print(f"[{i}/{len(scripts_a_ejecutar)}] [{tipo}] Ejecutando: {nombre_script}")
        print("-" * 80)
        
        exitoso, mensaje, tiempo, output = ejecutar_script(script_path, modo_automatico=True)
        
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
            print(f"  {mensaje[:200]}...")  # Primeros 200 caracteres
        
        print()
    
    return resultados


def ejecutar_todas_actualizaciones() -> None:
    """
    Ejecuta todas las actualizaciones automáticamente en dos fases.
    Genera reporte en update_database.txt en la raíz del proyecto
    """
    print("=" * 80)
    print("ACTUALIZACIÓN AUTOMÁTICA DE BASE DE DATOS")
    print("=" * 80)
    print(f"Fecha/Hora: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("Modo: AUTOMÁTICO (sin confirmaciones manuales)")
    print()
    
    inicio_total = time.time()
    
    # FASE 1: Descargar archivos
    resultados_fase1 = ejecutar_fase_descargas()
    
    print()
    print("=" * 80)
    print("FASE 1 COMPLETADA")
    print("=" * 80)
    print(f"Exitosos: {len(resultados_fase1['exitosos'])}")
    print(f"Fallidos: {len(resultados_fase1['fallidos'])}")
    print()
    
    # FASE 2: Actualizar base de datos
    resultados_fase2 = ejecutar_fase_actualizaciones()
    
    tiempo_total = time.time() - inicio_total
    
    # Generar y guardar reporte
    reporte = generar_reporte(resultados_fase1, resultados_fase2, tiempo_total)
    
    # Guardar reporte en archivo (en la raíz del proyecto)
    with open(REPORTE_FILE, 'w', encoding='utf-8') as f:
        f.write(reporte)
    
    print("=" * 80)
    print("EJECUCIÓN COMPLETADA")
    print("=" * 80)
    print(f"Reporte guardado en: {REPORTE_FILE.absolute()}")
    print()
    print("RESUMEN:")
    print(f"  FASE 1 (Descargas):")
    print(f"    Exitosos: {len(resultados_fase1['exitosos'])}")
    print(f"    Fallidos: {len(resultados_fase1['fallidos'])}")
    print(f"  FASE 2 (Actualizaciones):")
    print(f"    Exitosos: {len(resultados_fase2['exitosos'])}")
    print(f"    Fallidos: {len(resultados_fase2['fallidos'])}")
    print(f"  Tiempo total: {tiempo_total:.2f}s ({tiempo_total/60:.2f} minutos)")
    print()
    
    # Mostrar errores en consola también
    total_errores = len(resultados_fase1['fallidos']) + len(resultados_fase2['fallidos'])
    if total_errores > 0:
        print("ERRORES DETECTADOS:")
        if resultados_fase1['fallidos']:
            print("  FASE 1:")
            for res in resultados_fase1['fallidos']:
                print(f"    [ERROR] {res['categoria']}/{res['script']}")
        if resultados_fase2['fallidos']:
            print("  FASE 2:")
            for res in resultados_fase2['fallidos']:
                print(f"    [ERROR] {res['categoria']}/{res['script']}")
        print()
        print(f"Ver detalles en: {REPORTE_FILE.absolute()}")
    
    # Siempre salir con 0 para no fallar el pipeline (cron/CI); el reporte lista los fallidos
    sys.exit(0)


if __name__ == "__main__":
    ejecutar_todas_actualizaciones()
