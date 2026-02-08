"""
Script para diagnosticar por qué no hay datos en Inflación en Dólares
"""
import sys
sys.path.insert(0, 'backend')

from app.database import execute_query

print("="*80)
print("DIAGNOSTICO: INFLACION EN DOLARES")
print("="*80)
print()

# 1. Verificar cotizaciones (es_cotizacion = 1)
print("1. COTIZACIONES (es_cotizacion = 1, periodicidad = 'D'):")
query_cot = """
    SELECT id, nombre, pais, tipo, categoria, periodicidad, activo, es_cotizacion
    FROM maestro
    WHERE es_cotizacion = 1
    AND periodicidad = 'D'
    AND (activo = 1 OR CAST(activo AS INTEGER) = 1)
    AND pais IS NOT NULL
    ORDER BY pais, nombre
"""
cotizaciones = execute_query(query_cot)
print(f"Total cotizaciones encontradas: {len(cotizaciones)}")
for cot in cotizaciones[:10]:
    print(f"  ID {cot.get('id')}: {cot.get('nombre')[:50]} - pais: {cot.get('pais')}, tipo: {cot.get('tipo')}, categoria: {cot.get('categoria')}")

print()
print("="*80)
print()

# 2. Verificar IPC (tipo = 'M', periodicidad = 'M', nombre/categoria contiene IPC)
print("2. IPC DISPONIBLES (tipo = 'M', periodicidad = 'M', contiene IPC):")
query_ipc = """
    SELECT id, nombre, pais, tipo, categoria, periodicidad, activo
    FROM maestro
    WHERE tipo = 'M'
    AND periodicidad = 'M'
    AND (
        nombre LIKE '%IPC%' OR nombre LIKE '%índice de precios%' OR nombre LIKE '%indice de precios%'
        OR categoria LIKE '%IPC%' OR categoria LIKE '%inflación%' OR categoria LIKE '%inflacion%'
    )
    AND (activo = 1 OR CAST(activo AS INTEGER) = 1)
    ORDER BY pais, nombre
"""
ipcs = execute_query(query_ipc)
print(f"Total IPC encontrados: {len(ipcs)}")
for ipc in ipcs:
    print(f"  ID {ipc.get('id')}: {ipc.get('nombre')[:50]} - pais: {ipc.get('pais')}, categoria: {ipc.get('categoria')}")

print()
print("="*80)
print()

# 3. Verificar qué países tienen tanto cotización como IPC
print("3. PAISES CON COTIZACION E IPC:")
paises_cot = set(cot.get('pais') for cot in cotizaciones if cot.get('pais'))
paises_ipc = set(ipc.get('pais') for ipc in ipcs if ipc.get('pais'))

paises_completos = paises_cot.intersection(paises_ipc)
print(f"Paises con cotizacion: {sorted(paises_cot)}")
print(f"Paises con IPC: {sorted(paises_ipc)}")
print(f"Paises con AMBOS: {sorted(paises_completos)}")

print()
print("="*80)
print()

# 4. Verificar estructura de la tabla maestro
print("4. ESTRUCTURA DE COLUMNAS EN maestro:")
query_structure = "PRAGMA table_info(maestro)"
import sqlite3
conn = sqlite3.connect('series_tiempo.db')
cursor = conn.cursor()
cursor.execute(query_structure)
columns = cursor.fetchall()
print("Columnas:")
for col in columns:
    print(f"  - {col[1]} ({col[2]})")
conn.close()

print()
print("="*80)
print()

# 5. Verificar todos los productos con tipo = 'M'
print("5. TODOS LOS PRODUCTOS CON tipo = 'M':")
query_tipo_m = """
    SELECT id, nombre, pais, tipo, categoria, periodicidad, activo
    FROM maestro
    WHERE tipo = 'M'
    AND (activo = 1 OR CAST(activo AS INTEGER) = 1)
    ORDER BY pais, nombre
"""
tipo_m = execute_query(query_tipo_m)
print(f"Total productos tipo M: {len(tipo_m)}")
for p in tipo_m[:15]:
    print(f"  ID {p.get('id')}: {p.get('nombre')[:50]} - pais: {p.get('pais')}, categoria: {p.get('categoria')}, periodicidad: {p.get('periodicidad')}")

print()
print("="*80)
print("FIN")
print("="*80)
