"""
Script para limpiar todos los datos de precios y regenerarlos
"""
import sqlite3
from pathlib import Path
import subprocess
import sys

DB_PATH = Path(__file__).parent / "series_tiempo.db"

def limpiar_datos_precios():
    """Elimina todos los registros de maestro_precios"""
    print("=" * 80)
    print("LIMPIANDO DATOS DE PRECIOS")
    print("=" * 80)
    
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()
    
    # Contar registros antes de eliminar
    cursor.execute("SELECT COUNT(*) FROM maestro_precios")
    count_antes = cursor.fetchone()[0]
    print(f"Registros en maestro_precios antes: {count_antes}")
    
    # Eliminar todos los registros
    cursor.execute("DELETE FROM maestro_precios")
    conn.commit()
    
    # Verificar que se eliminaron
    cursor.execute("SELECT COUNT(*) FROM maestro_precios")
    count_despues = cursor.fetchone()[0]
    print(f"Registros en maestro_precios después: {count_despues}")
    
    # Verificar que maestro se mantiene intacto
    cursor.execute("SELECT COUNT(*) FROM maestro")
    count_maestro = cursor.fetchone()[0]
    print(f"Registros en maestro (se mantienen): {count_maestro}")
    
    conn.close()
    
    print(f"\n[OK] Datos de precios eliminados correctamente")
    print(f"  - Eliminados: {count_antes} registros")
    print(f"  - Mantenidos: {count_maestro} registros en maestro")
    print()

def ejecutar_actualizaciones():
    """Ejecuta el script de actualizaciones"""
    print("=" * 80)
    print("EJECUTANDO SCRIPT DE ACTUALIZACIONES")
    print("=" * 80)
    print()
    
    script_path = Path(__file__).parent / "ejecutar_todas_actualizaciones.py"
    
    if not script_path.exists():
        print(f"ERROR: No se encuentra el script {script_path}")
        return False
    
    try:
        # Ejecutar el script
        resultado = subprocess.run(
            [sys.executable, str(script_path)],
            cwd=str(script_path.parent),
            capture_output=False,
            text=True
        )
        
        if resultado.returncode == 0:
            print("\n[OK] Script de actualizaciones ejecutado correctamente")
            return True
        else:
            print(f"\n[ERROR] El script termino con codigo de error: {resultado.returncode}")
            return False
            
    except Exception as e:
        print(f"\n[ERROR] Error al ejecutar el script: {e}")
        return False

if __name__ == "__main__":
    print("\n" + "=" * 80)
    print("PROCESO DE LIMPIEZA Y REGENERACIÓN DE DATOS")
    print("=" * 80)
    print()
    
    # Paso 1: Limpiar datos
    limpiar_datos_precios()
    
    # Paso 2: Ejecutar actualizaciones automáticamente
    print("\n" + "=" * 80)
    print("Ejecutando script de actualizaciones automaticamente...")
    print("=" * 80)
    ejecutar_actualizaciones()
    
    print("\n" + "=" * 80)
    print("PROCESO COMPLETADO")
    print("=" * 80)
