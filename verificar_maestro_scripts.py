"""Script temporal para verificar correspondencia entre scripts y BD"""
import sqlite3
import pandas as pd
import re
import os
from pathlib import Path

DB_NAME = "series_tiempo.db"

# Diccionario con todos los scripts y sus datos MAESTRO
scripts_maestro = {}

# Leer scripts de precios/update/productos
productos_dir = Path("precios/update/productos")
if productos_dir.exists():
    for script_file in productos_dir.glob("*.py"):
        try:
            with open(script_file, 'r', encoding='utf-8') as f:
                content = f.read()
                # Buscar MAESTRO_* = { ... }
                match = re.search(r'MAESTRO_\w+\s*=\s*\{([^}]+)\}', content, re.DOTALL)
                if match:
                    dict_str = match.group(0)
                    # Extraer id y nombre
                    id_match = re.search(r'"id":\s*(\d+)', dict_str)
                    nombre_match = re.search(r'"nombre":\s*"([^"]+)"', dict_str)
                    if id_match and nombre_match:
                        script_id = int(id_match.group(1))
                        script_nombre = nombre_match.group(1)
                        scripts_maestro[script_file.name] = {
                            'id': script_id,
                            'nombre': script_nombre,
                            'path': str(script_file)
                        }
        except Exception as e:
            print(f"Error leyendo {script_file}: {e}")

# Leer scripts de macro/update
macro_dir = Path("macro/update")
if macro_dir.exists():
    for script_file in macro_dir.glob("*.py"):
        if script_file.name == "__init__.py":
            continue
        try:
            with open(script_file, 'r', encoding='utf-8') as f:
                content = f.read()
                # Buscar MAESTRO_* = { ... }
                match = re.search(r'MAESTRO_\w+\s*=\s*\{([^}]+)\}', content, re.DOTALL)
                if match:
                    dict_str = match.group(0)
                    # Extraer id y nombre
                    id_match = re.search(r'"id":\s*(\d+)', dict_str)
                    nombre_match = re.search(r'"nombre":\s*"([^"]+)"', dict_str)
                    if id_match and nombre_match:
                        script_id = int(id_match.group(1))
                        script_nombre = nombre_match.group(1)
                        scripts_maestro[script_file.name] = {
                            'id': script_id,
                            'nombre': script_nombre,
                            'path': str(script_file)
                        }
        except Exception as e:
            print(f"Error leyendo {script_file}: {e}")

# Leer base de datos
conn = sqlite3.connect(DB_NAME)
df_maestro = pd.read_sql_query("SELECT id, nombre FROM maestro ORDER BY id", conn)
conn.close()

print("=" * 80)
print("VERIFICACION: SCRIPTS vs BASE DE DATOS")
print("=" * 80)

print(f"\nScripts encontrados: {len(scripts_maestro)}")
print(f"Registros en BD: {len(df_maestro)}")

# Crear diccionario de BD
bd_dict = {}
for _, row in df_maestro.iterrows():
    bd_dict[row['id']] = row['nombre']

print("\n" + "=" * 80)
print("COMPARACION POR ID:")
print("=" * 80)

problemas = []
ids_duplicados_scripts = {}

# Verificar IDs duplicados en scripts
ids_en_scripts = {}
for script_name, data in scripts_maestro.items():
    script_id = data['id']
    if script_id in ids_en_scripts:
        if script_id not in ids_duplicados_scripts:
            ids_duplicados_scripts[script_id] = []
        ids_duplicados_scripts[script_id].append(ids_en_scripts[script_id])
        ids_duplicados_scripts[script_id].append(script_name)
    else:
        ids_en_scripts[script_id] = script_name

if ids_duplicados_scripts:
    print("\n[ERROR] IDs DUPLICADOS EN SCRIPTS:")
    for dup_id, scripts in ids_duplicados_scripts.items():
        print(f"  ID {dup_id} usado en: {', '.join(scripts)}")
        problemas.append(f"ID {dup_id} duplicado en scripts")

# Comparar cada script con BD
print("\n" + "-" * 80)
print("DETALLE POR SCRIPT:")
print("-" * 80)

for script_name, data in sorted(scripts_maestro.items(), key=lambda x: x[1]['id']):
    script_id = data['id']
    script_nombre = data['nombre']
    
    if script_id in bd_dict:
        bd_nombre = bd_dict[script_id]
        if script_nombre.strip() == bd_nombre.strip():
            print(f"\n[OK] {script_name} (ID {script_id})")
            print(f"     Script: {script_nombre}")
            print(f"     BD:     {bd_nombre}")
        else:
            print(f"\n[ERROR] {script_name} (ID {script_id}) - NOMBRES NO COINCIDEN")
            print(f"     Script: {script_nombre}")
            print(f"     BD:     {bd_nombre}")
            problemas.append(f"ID {script_id}: nombres no coinciden")
    else:
        print(f"\n[ERROR] {script_name} (ID {script_id}) - NO EXISTE EN BD")
        print(f"     Script: {script_nombre}")
        problemas.append(f"ID {script_id}: no existe en BD")

# Verificar IDs en BD que no tienen script
print("\n" + "-" * 80)
print("IDS EN BD SIN SCRIPT CORRESPONDIENTE:")
print("-" * 80)

ids_en_scripts_set = set(ids_en_scripts.keys())
ids_en_bd = set(bd_dict.keys())
ids_sin_script = ids_en_bd - ids_en_scripts_set

if ids_sin_script:
    for bd_id in sorted(ids_sin_script):
        print(f"\n[WARN] ID {bd_id} en BD sin script:")
        print(f"     Nombre BD: {bd_dict[bd_id]}")
else:
    print("\n[OK] Todos los IDs en BD tienen script correspondiente")

# Resumen
print("\n" + "=" * 80)
print("RESUMEN:")
print("=" * 80)

if problemas:
    print(f"\n[ERROR] Se encontraron {len(problemas)} problema(s):")
    for i, problema in enumerate(problemas, 1):
        print(f"  {i}. {problema}")
else:
    print("\n[OK] No se encontraron problemas. Todo está sincronizado correctamente.")

print("\n" + "=" * 80)
