"""
Script para actualizar los ID_VARIABLE e ID_PAIS en todos los scripts de macro
basándose en maestro_database.xlsx
"""

import pandas as pd
import re
import os

# Leer Excel
df = pd.read_excel('maestro_database.xlsx', sheet_name='Sheet1_old')

# Mapeo de scripts a búsquedas
MAPEO_SCRIPTS = {
    'ipc.py': {'nombre': 'IPC', 'id_region': 12},  # IPC Uruguay
    'tipo_cambio_usd.py': {'nombre': 'USD/LC', 'id_region': 12},  # USD/UYU
    'tipo_cambio_eur.py': {'nombre': 'EUR/LC', 'id_region': 12},  # EUR/UYU
    'salario_real.py': {'nombre': 'Salario', 'id_region': 12},  # Salario Real Uruguay
    'combustibles_miem.py': {'nombre': 'Gasoil', 'id_region': 12},  # Gasoil Uruguay
    'ipc_paraguay.py': {'nombre': 'IPC', 'id_region': None},  # IPC Paraguay - buscar por país
    'nxr_chile.py': {'nombre': 'Tipo.*cambio.*Chile|Chile.*tipo.*cambio', 'id_region': None},  # TC Chile
    'nxr_bra.py': {'nombre': 'Tipo.*cambio.*Brasil|Brasil.*tipo.*cambio', 'id_region': None},  # TC Brasil
    'nxr_peru.py': {'nombre': 'Tipo.*cambio.*Peru|Peru.*tipo.*cambio', 'id_region': None},  # TC Perú
    'nxr_argy.py': {'nombre': 'Tipo.*cambio.*Argentina|Argentina.*tipo.*cambio', 'id_region': None},  # TC Argentina
    'nxr_argy_cargar_historico.py': {'nombre': 'Tipo.*cambio.*Argentina|Argentina.*tipo.*cambio', 'id_region': None},  # TC Argentina
}

# Buscar valores
resultados = {}
for script, criterio in MAPEO_SCRIPTS.items():
    nombre_patron = criterio['nombre']
    id_region = criterio.get('id_region')
    
    # Buscar por nombre
    mask = df['nombre'].str.contains(nombre_patron, case=False, na=False, regex=True)
    if id_region is not None:
        mask = mask & (df['id_region'] == id_region)
    
    matches = df[mask]
    
    if not matches.empty:
        # Tomar el primero
        row = matches.iloc[0]
        resultados[script] = {
            'id_variable': int(row['id_nombre_variable']),
            'id_pais': int(row['id_region']),
            'nombre': row['nombre']
        }
        print(f"{script}: id_variable={row['id_nombre_variable']}, id_pais={row['id_region']}, nombre={row['nombre']}")
    else:
        print(f"{script}: NO ENCONTRADO")
        resultados[script] = None

# Mostrar todos los resultados
print("\n" + "="*60)
print("RESUMEN DE BÚSQUEDA")
print("="*60)
for script, resultado in resultados.items():
    if resultado:
        print(f"{script:40} -> id_variable={resultado['id_variable']:3}, id_pais={resultado['id_pais']:3} ({resultado['nombre'][:40]})")
    else:
        print(f"{script:40} -> NO ENCONTRADO")
