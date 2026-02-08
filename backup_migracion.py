"""
Script de backup antes de migración de estructura maestro.
Copia la base de datos y archivos críticos a la carpeta backup/.
"""

import os
import shutil
from datetime import datetime

# Archivos a respaldar
ARCHIVOS_BACKUP = [
    "series_tiempo.db",
    "backend/app/routers/dcp.py",
    "backend/app/routers/prices.py",
    "backend/app/routers/cotizaciones.py",
    "0_README"
]

BACKUP_DIR = "backup"
TIMESTAMP = datetime.now().strftime("%Y%m%d_%H%M%S")


def crear_backup():
    """Crea backup de BD y archivos críticos."""
    print("=" * 80)
    print("CREANDO BACKUP ANTES DE MIGRACION")
    print("=" * 80)
    
    # Crear carpeta backup si no existe
    if not os.path.exists(BACKUP_DIR):
        os.makedirs(BACKUP_DIR)
        print(f"[OK] Carpeta '{BACKUP_DIR}' creada")
    
    # Backup de base de datos
    db_original = "series_tiempo.db"
    if os.path.exists(db_original):
        db_backup = os.path.join(BACKUP_DIR, f"series_tiempo_backup_{TIMESTAMP}.db")
        shutil.copy2(db_original, db_backup)
        print(f"[OK] Base de datos respaldada: {db_backup}")
    else:
        print(f"[WARN] No se encontró {db_original}")
    
    # Backup de archivos Python y README
    for archivo in ARCHIVOS_BACKUP:
        if archivo == "series_tiempo.db":
            continue  # Ya se respaldó arriba
        
        if os.path.exists(archivo):
            # Crear estructura de carpetas en backup si es necesario
            backup_path = os.path.join(BACKUP_DIR, archivo)
            backup_dir = os.path.dirname(backup_path)
            if backup_dir and not os.path.exists(backup_dir):
                os.makedirs(backup_dir)
            
            shutil.copy2(archivo, backup_path + ".backup")
            print(f"[OK] Archivo respaldado: {archivo} -> {backup_path}.backup")
        else:
            print(f"[WARN] No se encontró {archivo}")
    
    print("\n" + "=" * 80)
    print("BACKUP COMPLETADO")
    print(f"Timestamp: {TIMESTAMP}")
    print("=" * 80)


if __name__ == "__main__":
    crear_backup()
