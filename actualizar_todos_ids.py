"""
Script para actualizar todos los ID_VARIABLE e ID_PAIS en los scripts de macro
"""

import re
import os

# Mapeo de scripts a IDs (basado en búsquedas en el Excel)
MAPEO_IDS = {
    'macro/update/ipc.py': {'id_variable': 9, 'id_pais': 12},  # IPC Uruguay
    'macro/update/tipo_cambio_usd.py': {'id_variable': 20, 'id_pais': 12},  # USD/LC Uruguay
    'macro/update/tipo_cambio_eur.py': {'id_variable': 6, 'id_pais': 12},  # EUR/LC Uruguay
    'macro/update/salario_real.py': {'id_variable': 15, 'id_pais': 12},  # Salario real Uruguay
    'macro/update/combustibles_miem.py': {'id_variable': 7, 'id_pais': 12},  # Gasoil Uruguay
    'macro/update/ipc_paraguay.py': {'id_variable': 9, 'id_pais': None},  # IPC Paraguay - necesito buscar id_region de Paraguay
    'macro/update/nxr_chile.py': {'id_variable': None, 'id_pais': 4},  # TC Chile - necesito buscar id_variable
    'macro/update/nxr_bra.py': {'id_variable': None, 'id_pais': 3},  # TC Brasil - necesito buscar id_variable
    'macro/update/nxr_peru.py': {'id_variable': None, 'id_pais': 9},  # TC Perú - necesito buscar id_variable
    'macro/update/nxr_argy.py': {'id_variable': None, 'id_pais': None},  # TC Argentina - necesito buscar ambos
    'macro/update/nxr_argy_cargar_historico.py': {'id_variable': None, 'id_pais': None},  # TC Argentina - necesito buscar ambos
}

# Primero, buscar los IDs faltantes
import pandas as pd
df = pd.read_excel('maestro_database.xlsx', sheet_name='Sheet1_old')

# Buscar IPC Paraguay (id_variable=9, pero necesito id_region de Paraguay)
paraguay_ipc = df[(df['id_nombre_variable'] == 9) & (df['pais/region'].str.contains('Paraguay', case=False, na=False))]
if not paraguay_ipc.empty:
    MAPEO_IDS['macro/update/ipc_paraguay.py']['id_pais'] = int(paraguay_ipc.iloc[0]['id_region'])
    print(f"IPC Paraguay: id_variable=9, id_pais={paraguay_ipc.iloc[0]['id_region']}")

# Buscar tipos de cambio de otros países (buscar por id_region y tipo de cambio)
# Chile (id_region=4)
tc_chile = df[(df['id_region'] == 4) & (df['nombre'].str.contains('tipo.*cambio|USD|TC', case=False, na=False, regex=True))]
if not tc_chile.empty:
    MAPEO_IDS['macro/update/nxr_chile.py']['id_variable'] = int(tc_chile.iloc[0]['id_nombre_variable'])
    print(f"TC Chile: id_variable={tc_chile.iloc[0]['id_nombre_variable']}, id_pais=4")

# Brasil (id_region=3)
tc_brasil = df[(df['id_region'] == 3) & (df['nombre'].str.contains('tipo.*cambio|USD|TC', case=False, na=False, regex=True))]
if not tc_brasil.empty:
    MAPEO_IDS['macro/update/nxr_bra.py']['id_variable'] = int(tc_brasil.iloc[0]['id_nombre_variable'])
    print(f"TC Brasil: id_variable={tc_brasil.iloc[0]['id_nombre_variable']}, id_pais=3")

# Perú (id_region=9)
tc_peru = df[(df['id_region'] == 9) & (df['nombre'].str.contains('tipo.*cambio|USD|TC', case=False, na=False, regex=True))]
if not tc_peru.empty:
    MAPEO_IDS['macro/update/nxr_peru.py']['id_variable'] = int(tc_peru.iloc[0]['id_nombre_variable'])
    print(f"TC Perú: id_variable={tc_peru.iloc[0]['id_nombre_variable']}, id_pais=9")

# Argentina - buscar id_region primero
argentina_rows = df[df['pais/region'].str.contains('Argentina', case=False, na=False)]
if not argentina_rows.empty:
    id_region_arg = int(argentina_rows.iloc[0]['id_region'])
    tc_arg = argentina_rows[argentina_rows['nombre'].str.contains('tipo.*cambio|USD|TC', case=False, na=False, regex=True)]
    if not tc_arg.empty:
        MAPEO_IDS['macro/update/nxr_argy.py']['id_variable'] = int(tc_arg.iloc[0]['id_nombre_variable'])
        MAPEO_IDS['macro/update/nxr_argy.py']['id_pais'] = id_region_arg
        MAPEO_IDS['macro/update/nxr_argy_cargar_historico.py']['id_variable'] = int(tc_arg.iloc[0]['id_nombre_variable'])
        MAPEO_IDS['macro/update/nxr_argy_cargar_historico.py']['id_pais'] = id_region_arg
        print(f"TC Argentina: id_variable={tc_arg.iloc[0]['id_nombre_variable']}, id_pais={id_region_arg}")

# Actualizar scripts
print("\n" + "="*60)
print("ACTUALIZANDO SCRIPTS")
print("="*60)

for script_path, ids in MAPEO_IDS.items():
    if not os.path.exists(script_path):
        print(f"[WARN] {script_path} no existe, saltando...")
        continue
    
    if ids['id_variable'] is None or ids['id_pais'] is None:
        print(f"[SKIP] {script_path}: Faltan IDs (id_variable={ids['id_variable']}, id_pais={ids['id_pais']})")
        continue
    
    # Leer archivo
    with open(script_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Reemplazar ID_VARIABLE
    pattern_var = r'ID_VARIABLE\s*=\s*None'
    replacement_var = f"ID_VARIABLE = {ids['id_variable']}"
    content = re.sub(pattern_var, replacement_var, content)
    
    # Reemplazar ID_PAIS
    pattern_pais = r'ID_PAIS\s*=\s*None'
    replacement_pais = f"ID_PAIS = {ids['id_pais']}"
    content = re.sub(pattern_pais, replacement_pais, content)
    
    # Escribir archivo
    with open(script_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"[OK] {script_path}: id_variable={ids['id_variable']}, id_pais={ids['id_pais']}")

print("\n" + "="*60)
print("PROCESO COMPLETADO")
print("="*60)
