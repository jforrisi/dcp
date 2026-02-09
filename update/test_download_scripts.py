"""
Script de Prueba de Scripts de Descarga
========================================
Ejecuta todos los scripts en update/download/ y genera un reporte detallado
con el análisis de qué pasó con cada actualización.
"""

import subprocess
import sys
import traceback
from pathlib import Path
import time
from datetime import datetime
from typing import List, Tuple, Dict
import os

# Detectar la raíz del proyecto
SCRIPT_DIR = Path(__file__).parent.absolute()
PROJECT_ROOT = SCRIPT_DIR.parent
DOWNLOAD_DIR = PROJECT_ROOT / "update" / "download"

# Configuración
TIMEOUT_SCRIPT = 1800  # 30 minutos máximo por script
REPORTE_FILE = PROJECT_ROOT / "test_download_report.txt"


def descubrir_scripts_download() -> List[Path]:
    """
    Descubre automáticamente todos los scripts de descarga.
    
    Returns:
        Lista de Paths a los scripts
    """
    scripts = []
    
    if DOWNLOAD_DIR.exists():
        for script_file in sorted(DOWNLOAD_DIR.glob("*.py")):
            if script_file.name != "__init__.py" and not script_file.name.startswith("_"):
                scripts.append(script_file)
    
    return scripts


def ejecutar_script(ruta_script: Path) -> Tuple[bool, str, float, str, str]:
    """
    Ejecuta un script usando subprocess.
    
    Args:
        ruta_script: Path al script a ejecutar
        
    Returns:
        Tuple (exitoso, mensaje, tiempo_ejecucion, stdout, stderr)
    """
    nombre_script = ruta_script.name
    inicio = time.time()
    
    try:
        # Usar el mismo Python que ejecuta este script
        python_exe = sys.executable
        
        # Ejecutar script
        proceso = subprocess.Popen(
            [python_exe, str(ruta_script)],
            cwd=str(PROJECT_ROOT),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1
        )
        
        try:
            stdout, stderr = proceso.communicate(timeout=TIMEOUT_SCRIPT)
            tiempo_ejecucion = time.time() - inicio
            returncode = proceso.returncode
            
            if returncode == 0:
                return (True, f"✓ Ejecutado exitosamente", tiempo_ejecucion, stdout, stderr)
            else:
                error_msg = f"✗ Error: código de salida {returncode}"
                if stderr:
                    error_msg += f"\n   {stderr[:200]}"
                return (False, error_msg, tiempo_ejecucion, stdout, stderr)
                
        except subprocess.TimeoutExpired:
            proceso.kill()
            tiempo_ejecucion = time.time() - inicio
            return (False, f"✗ Timeout después de {TIMEOUT_SCRIPT}s", tiempo_ejecucion, "", "Timeout")
            
    except Exception as e:
        tiempo_ejecucion = time.time() - inicio
        error_msg = f"✗ Excepción: {str(e)}"
        return (False, error_msg, tiempo_ejecucion, "", str(e))


def analizar_output(stdout: str, stderr: str) -> Dict[str, any]:
    """
    Analiza el output de un script para extraer información relevante.
    
    Returns:
        Dict con información analizada
    """
    analisis = {
        'tiene_errores': False,
        'tiene_warnings': False,
        'lineas_output': len(stdout.splitlines()) if stdout else 0,
        'lineas_error': len(stderr.splitlines()) if stderr else 0,
        'palabras_clave': {
            'error': 0,
            'warning': 0,
            'success': 0,
            'descargado': 0,
            'actualizado': 0
        }
    }
    
    # Analizar stdout
    if stdout:
        stdout_lower = stdout.lower()
        analisis['palabras_clave']['error'] += stdout_lower.count('error')
        analisis['palabras_clave']['warning'] += stdout_lower.count('warning')
        analisis['palabras_clave']['success'] += stdout_lower.count('success')
        analisis['palabras_clave']['descargado'] += stdout_lower.count('descargado')
        analisis['palabras_clave']['actualizado'] += stdout_lower.count('actualizado')
        
        if 'error' in stdout_lower or 'exception' in stdout_lower:
            analisis['tiene_errores'] = True
        if 'warning' in stdout_lower:
            analisis['tiene_warnings'] = True
    
    # Analizar stderr
    if stderr:
        stderr_lower = stderr.lower()
        analisis['palabras_clave']['error'] += stderr_lower.count('error')
        analisis['tiene_errores'] = True
    
    return analisis


def generar_reporte(resultados: List[Dict]) -> str:
    """
    Genera un reporte detallado de los resultados.
    
    Args:
        resultados: Lista de dicts con información de cada script
        
    Returns:
        String con el reporte completo
    """
    reporte = []
    reporte.append("=" * 80)
    reporte.append("REPORTE DE PRUEBA DE SCRIPTS DE DESCARGA")
    reporte.append("=" * 80)
    reporte.append(f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    reporte.append(f"Total de scripts: {len(resultados)}")
    reporte.append("")
    
    # Resumen
    exitosos = sum(1 for r in resultados if r['exitoso'])
    fallidos = len(resultados) - exitosos
    
    reporte.append("RESUMEN")
    reporte.append("-" * 80)
    reporte.append(f"✓ Exitosos: {exitosos}")
    reporte.append(f"✗ Fallidos: {fallidos}")
    reporte.append(f"Tiempo total: {sum(r['tiempo'] for r in resultados):.2f} segundos")
    reporte.append("")
    
    # Detalle por script
    reporte.append("DETALLE POR SCRIPT")
    reporte.append("=" * 80)
    
    for i, resultado in enumerate(resultados, 1):
        nombre = resultado['nombre']
        exitoso = resultado['exitoso']
        mensaje = resultado['mensaje']
        tiempo = resultado['tiempo']
        analisis = resultado['analisis']
        
        reporte.append("")
        reporte.append(f"{i}. {nombre}")
        reporte.append("-" * 80)
        reporte.append(f"Estado: {mensaje}")
        reporte.append(f"Tiempo: {tiempo:.2f} segundos")
        reporte.append("")
        
        # Análisis
        reporte.append("Análisis del output:")
        reporte.append(f"  - Líneas de output: {analisis['lineas_output']}")
        reporte.append(f"  - Líneas de error: {analisis['lineas_error']}")
        reporte.append(f"  - Tiene errores: {'Sí' if analisis['tiene_errores'] else 'No'}")
        reporte.append(f"  - Tiene warnings: {'Sí' if analisis['tiene_warnings'] else 'No'}")
        reporte.append("")
        reporte.append("Palabras clave encontradas:")
        for palabra, cantidad in analisis['palabras_clave'].items():
            if cantidad > 0:
                reporte.append(f"  - '{palabra}': {cantidad}")
        reporte.append("")
        
        # Mostrar últimas líneas del output si hay errores
        if not exitoso and resultado['stdout']:
            reporte.append("Últimas líneas del output:")
            lineas = resultado['stdout'].splitlines()
            for linea in lineas[-10:]:
                reporte.append(f"  {linea}")
            reporte.append("")
        
        if resultado['stderr']:
            reporte.append("Errores (stderr):")
            lineas_error = resultado['stderr'].splitlines()
            for linea in lineas_error[-10:]:
                reporte.append(f"  {linea}")
            reporte.append("")
    
    # Lista de scripts exitosos y fallidos
    reporte.append("")
    reporte.append("=" * 80)
    reporte.append("SCRIPTS EXITOSOS")
    reporte.append("=" * 80)
    for resultado in resultados:
        if resultado['exitoso']:
            reporte.append(f"✓ {resultado['nombre']}")
    
    reporte.append("")
    reporte.append("=" * 80)
    reporte.append("SCRIPTS FALLIDOS")
    reporte.append("=" * 80)
    for resultado in resultados:
        if not resultado['exitoso']:
            reporte.append(f"✗ {resultado['nombre']}: {resultado['mensaje']}")
    
    return "\n".join(reporte)


def main():
    """Función principal."""
    print("=" * 80)
    print("PRUEBA DE SCRIPTS DE DESCARGA")
    print("=" * 80)
    print(f"Inicio: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("")
    
    # Descubrir scripts
    scripts = descubrir_scripts_download()
    
    if not scripts:
        print("No se encontraron scripts en update/download/")
        return
    
    print(f"Se encontraron {len(scripts)} scripts:")
    for script in scripts:
        print(f"  - {script.name}")
    print("")
    
    # Ejecutar cada script
    resultados = []
    
    for i, script in enumerate(scripts, 1):
        print(f"[{i}/{len(scripts)}] Ejecutando {script.name}...")
        
        exitoso, mensaje, tiempo, stdout, stderr = ejecutar_script(script)
        analisis = analizar_output(stdout, stderr)
        
        resultado = {
            'nombre': script.name,
            'exitoso': exitoso,
            'mensaje': mensaje,
            'tiempo': tiempo,
            'stdout': stdout,
            'stderr': stderr,
            'analisis': analisis
        }
        
        resultados.append(resultado)
        
        # Mostrar resultado inmediato
        estado = "✓" if exitoso else "✗"
        print(f"  {estado} {mensaje} ({tiempo:.2f}s)")
        if analisis['tiene_errores']:
            print(f"  ⚠ Tiene errores en el output")
        print("")
    
    # Generar reporte
    reporte = generar_reporte(resultados)
    
    # Guardar reporte en archivo
    with open(REPORTE_FILE, 'w', encoding='utf-8') as f:
        f.write(reporte)
    
    # Mostrar resumen en consola
    print("=" * 80)
    print("RESUMEN FINAL")
    print("=" * 80)
    exitosos = sum(1 for r in resultados if r['exitoso'])
    fallidos = len(resultados) - exitosos
    print(f"✓ Exitosos: {exitosos}")
    print(f"✗ Fallidos: {fallidos}")
    print(f"Tiempo total: {sum(r['tiempo'] for r in resultados):.2f} segundos")
    print("")
    print(f"Reporte completo guardado en: {REPORTE_FILE}")
    print("=" * 80)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nEjecución interrumpida por el usuario.")
        sys.exit(1)
    except Exception as e:
        print(f"\n\nError fatal: {str(e)}")
        traceback.print_exc()
        sys.exit(1)
