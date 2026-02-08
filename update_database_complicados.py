"""
Script de Actualización Automática de Base de Datos - SCRIPTS COMPLICADOS
==========================================================================
Ejecuta automáticamente scripts que requieren procesamiento especial o tardan mucho:
- servicios_no_tradicionales.py (calcula promedios desde otras series)

Estos scripts se ejecutan por separado porque:
- Requieren que otros scripts ya hayan terminado
- Tardan mucho tiempo en procesar
- Hacen consultas complejas a la base de datos

Genera un reporte en update_database_complicados.txt con errores y resumen.
"""

import subprocess
import sys
import traceback
from pathlib import Path
import time
from datetime import datetime
from typing import List, Tuple, Dict
import os


# Configuración
REPORTE_FILE = "update_database_complicados.txt"
TIMEOUT_SCRIPT = 7200  # 2 horas máximo por script (más tiempo para scripts complicados)


def descubrir_scripts_complicados() -> Dict[str, List[Path]]:
    """
    Descubre automáticamente scripts complicados que requieren procesamiento especial.
    
    Returns:
        Dict con categorías como keys, cada una con lista de Paths
    """
    scripts = {
        'precios_servicios': []
    }
    
    # Scripts complicados de precios/servicios/update
    scripts_complicados = ['servicios_no_tradicionales.py']
    precios_servicios_dir = Path("precios/update/servicios")
    if precios_servicios_dir.exists():
        for script_file in precios_servicios_dir.glob("*.py"):
            if script_file.name != "__init__.py" and not script_file.name.startswith("_"):
                # Solo incluir scripts complicados
                if script_file.name in scripts_complicados:
                    scripts['precios_servicios'].append(script_file)
    
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
        # Ejecutar el script como subprocess
        proceso = subprocess.Popen(
            [sys.executable, str(ruta_script)],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,  # Combinar stderr con stdout
            text=True,
            bufsize=1,
            universal_newlines=True
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


def generar_reporte(resultados: Dict, tiempo_total: float) -> str:
    """
    Genera el contenido del reporte en formato texto.
    
    Args:
        resultados: Dict con 'exitosos' y 'fallidos'
        tiempo_total: Tiempo total de ejecución
        
    Returns:
        String con el contenido del reporte
    """
    reporte = []
    reporte.append("=" * 80)
    reporte.append("REPORTE DE ACTUALIZACIÓN DE BASE DE DATOS - SCRIPTS COMPLICADOS")
    reporte.append("=" * 80)
    reporte.append(f"Fecha/Hora de ejecución: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    reporte.append("")
    reporte.append("NOTA: Estos scripts requieren procesamiento especial y tardan más tiempo.")
    reporte.append("")
    
    # Resumen general
    total_scripts = len(resultados['exitosos']) + len(resultados['fallidos'])
    reporte.append("RESUMEN GENERAL")
    reporte.append("-" * 80)
    reporte.append(f"Total de scripts ejecutados: {total_scripts}")
    reporte.append(f"Exitosos: {len(resultados['exitosos'])}")
    reporte.append(f"Fallidos: {len(resultados['fallidos'])}")
    reporte.append(f"Tiempo total: {tiempo_total:.2f} segundos ({tiempo_total/60:.2f} minutos)")
    reporte.append("")
    
    # Scripts exitosos
    if resultados['exitosos']:
        reporte.append("SCRIPTS EJECUTADOS EXITOSAMENTE")
        reporte.append("-" * 80)
        for res in resultados['exitosos']:
            categoria = res['categoria']
            script = res['script']
            tiempo = res['tiempo']
            reporte.append(f"  ✅ {categoria}/{script} ({tiempo:.2f}s)")
        reporte.append("")
    
    # Scripts con errores
    if resultados['fallidos']:
        reporte.append("=" * 80)
        reporte.append("ERRORES DETECTADOS")
        reporte.append("=" * 80)
        reporte.append("")
        
        for i, res in enumerate(resultados['fallidos'], 1):
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
    else:
        reporte.append("=" * 80)
        reporte.append("NO SE DETECTARON ERRORES")
        reporte.append("=" * 80)
        reporte.append("Todos los scripts se ejecutaron exitosamente.")
        reporte.append("")
    
    reporte.append("=" * 80)
    reporte.append(f"Fin del reporte - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    reporte.append("=" * 80)
    
    return "\n".join(reporte)


def ejecutar_scripts_complicados() -> None:
    """
    Ejecuta todos los scripts complicados automáticamente.
    Genera reporte en update_database_complicados.txt
    """
    print("=" * 80)
    print("ACTUALIZACIÓN AUTOMÁTICA DE BASE DE DATOS - SCRIPTS COMPLICADOS")
    print("=" * 80)
    print(f"Fecha/Hora: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("Modo: AUTOMÁTICO (sin confirmaciones manuales)")
    print("NOTA: Estos scripts requieren procesamiento especial y tardan más tiempo.")
    print()
    
    # Descubrir scripts complicados
    todos_scripts = descubrir_scripts_complicados()
    
    # Preparar lista de scripts a ejecutar
    scripts_a_ejecutar = []
    
    for categoria, scripts in todos_scripts.items():
        for script in scripts:
            scripts_a_ejecutar.append((categoria, script))
    
    if not scripts_a_ejecutar:
        print("[INFO] No se encontraron scripts complicados para ejecutar.")
        print("       (Esto es normal si no hay scripts marcados como complicados)")
        return
    
    print(f"Scripts complicados detectados: {len(scripts_a_ejecutar)}")
    print("-" * 80)
    for categoria, script in scripts_a_ejecutar:
        print(f"  - {categoria}/{script.name}")
    print()
    print("[INFO] Estos scripts se ejecutarán con timeout de 2 horas cada uno.")
    print()
    
    # Ejecutar cada script
    resultados = {
        'exitosos': [],
        'fallidos': []
    }
    
    inicio_total = time.time()
    
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
            print(f"[OK] {nombre_script} - Tiempo: {tiempo:.2f}s ({tiempo/60:.2f} minutos)")
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
    
    tiempo_total = time.time() - inicio_total
    
    # Generar y guardar reporte
    reporte = generar_reporte(resultados, tiempo_total)
    
    # Guardar reporte en archivo
    reporte_path = Path(REPORTE_FILE)
    with open(reporte_path, 'w', encoding='utf-8') as f:
        f.write(reporte)
    
    print("=" * 80)
    print("EJECUCIÓN COMPLETADA")
    print("=" * 80)
    print(f"Reporte guardado en: {reporte_path.absolute()}")
    print()
    print("RESUMEN:")
    print(f"  Total: {len(scripts_a_ejecutar)}")
    print(f"  Exitosos: {len(resultados['exitosos'])}")
    print(f"  Fallidos: {len(resultados['fallidos'])}")
    print(f"  Tiempo total: {tiempo_total:.2f}s ({tiempo_total/60:.2f} minutos)")
    print()
    
    # Mostrar errores en consola también
    if resultados['fallidos']:
        print("ERRORES DETECTADOS:")
        for res in resultados['fallidos']:
            print(f"  ❌ {res['categoria']}/{res['script']}")
        print()
        print(f"Ver detalles en: {reporte_path.absolute()}")
    
    # Retornar código de salida apropiado
    if resultados['fallidos']:
        sys.exit(1)  # Hay errores
    else:
        sys.exit(0)  # Todo OK


if __name__ == "__main__":
    ejecutar_scripts_complicados()
