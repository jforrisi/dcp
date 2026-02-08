"""
Script para migrar scripts de actualización de precios a la nueva estructura de maestro.

Este script actualiza automáticamente los scripts que usan la estructura antigua de maestro
para que usen id_variable e id_pais directamente.
"""
import os
import re
from pathlib import Path


def actualizar_script(archivo_path: str) -> bool:
    """
    Actualiza un script individual para usar la nueva estructura.
    
    Returns:
        True si se hizo algún cambio, False si no
    """
    with open(archivo_path, 'r', encoding='utf-8') as f:
        contenido = f.read()
    
    contenido_original = contenido
    cambios = False
    
    # 1. Reemplazar INSERT OR IGNORE INTO maestro con comentario
    patron_insert_maestro = re.compile(
        r'INSERT\s+OR\s+IGNORE\s+INTO\s+maestro\s*\([^)]+\)\s*VALUES\s*\([^)]+\)',
        re.IGNORECASE | re.DOTALL
    )
    if patron_insert_maestro.search(contenido):
        contenido = patron_insert_maestro.sub(
            '# NOTA: La inserción en maestro se eliminó. El registro debe existir en maestro_database.xlsx',
            contenido
        )
        cambios = True
    
    # 2. Reemplazar SELECT id_variable, id_pais FROM maestro WHERE id = ?
    patron_select_fks = re.compile(
        r'SELECT\s+id_variable,\s*id_pais\s+FROM\s+maestro\s+WHERE\s+id\s*=\s*\?',
        re.IGNORECASE
    )
    if patron_select_fks.search(contenido):
        contenido = patron_select_fks.sub(
            '# NOTA: Ya no se obtienen FKs desde maestro usando id. Usar id_variable e id_pais directamente.',
            contenido
        )
        cambios = True
    
    # 3. Buscar y comentar código que usa maestro_id
    # Esto es más complejo, mejor hacerlo manualmente
    
    if cambios and contenido != contenido_original:
        # Crear backup
        backup_path = archivo_path + '.backup'
        with open(backup_path, 'w', encoding='utf-8') as f:
            f.write(contenido_original)
        
        # Escribir cambios
        with open(archivo_path, 'w', encoding='utf-8') as f:
            f.write(contenido)
        
        return True
    
    return False


def main():
    """Actualiza todos los scripts de actualización."""
    print("=" * 60)
    print("MIGRACIÓN DE SCRIPTS DE ACTUALIZACIÓN")
    print("=" * 60)
    
    # Directorios a procesar
    directorios = [
        'precios/update/productos',
        'precios/update/servicios',
        'macro/update'
    ]
    
    scripts_actualizados = []
    scripts_sin_cambios = []
    
    for directorio in directorios:
        if not os.path.exists(directorio):
            print(f"[WARN] Directorio no existe: {directorio}")
            continue
        
        print(f"\n[INFO] Procesando directorio: {directorio}")
        
        for archivo in Path(directorio).glob('*.py'):
            # Saltar helpers y scripts ya actualizados
            if archivo.name.startswith('_') or archivo.name in ['software.py', 'bookkeeping.py']:
                continue
            
            print(f"  - {archivo.name}...", end=' ')
            
            if actualizar_script(str(archivo)):
                scripts_actualizados.append(str(archivo))
                print("OK (actualizado)")
            else:
                scripts_sin_cambios.append(str(archivo))
                print("OK (sin cambios necesarios)")
    
    print("\n" + "=" * 60)
    print("RESUMEN")
    print("=" * 60)
    print(f"Scripts actualizados: {len(scripts_actualizados)}")
    print(f"Scripts sin cambios: {len(scripts_sin_cambios)}")
    
    if scripts_actualizados:
        print("\n[INFO] Scripts actualizados (backups creados con extensión .backup):")
        for script in scripts_actualizados:
            print(f"  - {script}")
    
    print("\n[INFO] NOTA: Este script solo hace cambios automáticos básicos.")
    print("[INFO] Debes revisar manualmente cada script para:")
    print("  1. Agregar ID_VARIABLE e ID_PAIS al inicio del script")
    print("  2. Actualizar la función insertar_en_bd() para usar id_variable e id_pais")
    print("  3. Actualizar la función main() para pasar id_variable e id_pais")


if __name__ == "__main__":
    main()
