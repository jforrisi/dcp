"""
Script para limpiar automáticamente los scripts de actualización:
- Eliminar funciones crear_base_datos() y sus llamadas
- Eliminar funciones generar_excel_prueba() y sus llamadas
- Eliminar diccionarios MAESTRO_* (pero mantener comentarios sobre ID_VARIABLE e ID_PAIS)
"""
import os
import re
from pathlib import Path


def limpiar_script(archivo_path: str) -> bool:
    """
    Limpia un script individual eliminando funciones y diccionarios obsoletos.
    
    Returns:
        True si se hizo algún cambio, False si no
    """
    with open(archivo_path, 'r', encoding='utf-8') as f:
        contenido = f.read()
    
    contenido_original = contenido
    cambios = False
    
    # 1. Eliminar función crear_base_datos() completa
    patron_crear_bd = re.compile(
        r'def crear_base_datos\(\):.*?print\(f"\[OK\] Base de datos.*?"\)',
        re.DOTALL
    )
    if patron_crear_bd.search(contenido):
        contenido = patron_crear_bd.sub('', contenido)
        cambios = True
    
    # 2. Eliminar llamadas a crear_base_datos()
    contenido = re.sub(r'\s*crear_base_datos\(\)\s*\n', '\n', contenido)
    if contenido != contenido_original:
        cambios = True
        contenido_original = contenido
    
    # 3. Eliminar función generar_excel_prueba() completa
    patron_excel = re.compile(
        r'def generar_excel_prueba\(.*?\):.*?return excel_path',
        re.DOTALL
    )
    if patron_excel.search(contenido):
        contenido = patron_excel.sub('', contenido)
        cambios = True
    
    # 4. Eliminar llamadas a generar_excel_prueba()
    contenido = re.sub(
        r'\s*excel_path\s*=\s*generar_excel_prueba\([^)]+\)\s*\n',
        '',
        contenido
    )
    if contenido != contenido_original:
        cambios = True
        contenido_original = contenido
    
    # 5. Eliminar variable EXCEL_PRUEBA_NAME
    contenido = re.sub(
        r'EXCEL_PRUEBA_NAME\s*=\s*"[^"]+"\s*\n',
        '',
        contenido
    )
    if contenido != contenido_original:
        cambios = True
        contenido_original = contenido
    
    # 6. Eliminar diccionarios MAESTRO_* (pero mantener comentarios)
    patron_maestro = re.compile(
        r'#\s*Datos del maestro.*?\nMAESTRO_\w+\s*=\s*\{[^}]+\}[^\n]*\n',
        re.DOTALL
    )
    if patron_maestro.search(contenido):
        contenido = patron_maestro.sub(
            '# Configuración de base de datos\n# NOTA: ID_VARIABLE e ID_PAIS deben configurarse desde maestro_database.xlsx Sheet1_old\n',
            contenido
        )
        cambios = True
    
    # Limpiar líneas vacías múltiples
    contenido = re.sub(r'\n{3,}', '\n\n', contenido)
    
    if cambios and contenido != contenido_original:
        # Crear backup
        backup_path = archivo_path + '.backup2'
        if not os.path.exists(backup_path):
            with open(backup_path, 'w', encoding='utf-8') as f:
                f.write(contenido_original)
        
        # Escribir cambios
        with open(archivo_path, 'w', encoding='utf-8') as f:
            f.write(contenido)
        
        return True
    
    return False


def main():
    """Limpia todos los scripts de actualización."""
    print("=" * 60)
    print("LIMPIEZA AUTOMÁTICA DE SCRIPTS")
    print("=" * 60)
    
    # Directorios a procesar
    directorios = [
        'precios/update/productos',
        'precios/update/servicios',
        'macro/update'
    ]
    
    scripts_limpiados = []
    scripts_sin_cambios = []
    
    for directorio in directorios:
        if not os.path.exists(directorio):
            print(f"[WARN] Directorio no existe: {directorio}")
            continue
        
        print(f"\n[INFO] Procesando directorio: {directorio}")
        
        for archivo in Path(directorio).glob('*.py'):
            # Saltar backups y helpers
            if archivo.name.startswith('_') or archivo.name.endswith('.backup'):
                continue
            
            print(f"  - {archivo.name}...", end=' ')
            
            if limpiar_script(str(archivo)):
                scripts_limpiados.append(str(archivo))
                print("OK (limpiado)")
            else:
                scripts_sin_cambios.append(str(archivo))
                print("OK (sin cambios necesarios)")
    
    print("\n" + "=" * 60)
    print("RESUMEN")
    print("=" * 60)
    print(f"Scripts limpiados: {len(scripts_limpiados)}")
    print(f"Scripts sin cambios: {len(scripts_sin_cambios)}")
    
    if scripts_limpiados:
        print("\n[INFO] Scripts limpiados (backups creados con extensión .backup2):")
        for script in scripts_limpiados:
            print(f"  - {script}")
    
    print("\n[INFO] NOTA: Este script solo hace limpieza básica.")
    print("[INFO] Debes revisar manualmente cada script para:")
    print("  1. Agregar ID_VARIABLE e ID_PAIS al inicio del script")
    print("  2. Actualizar la función main() para usar insertar_en_bd_unificado")
    print("  3. Usar helpers unificados para validación de fechas")


if __name__ == "__main__":
    main()
