"""
Script para verificar si existe una columna 'grupo' en la tabla maestro
"""
import sys
sys.path.insert(0, 'backend')

from app.database import execute_query

print("="*80)
print("VERIFICACIÓN DE COLUMNA 'grupo' EN TABLA maestro")
print("="*80)
print()

# Verificar estructura de la tabla
print("1. ESTRUCTURA DE LA TABLA maestro:")
try:
    # SQLite no tiene INFORMATION_SCHEMA, usar PRAGMA
    import sqlite3
    conn = sqlite3.connect('series_tiempo.db')
    cursor = conn.cursor()
    cursor.execute("PRAGMA table_info(maestro)")
    columns = cursor.fetchall()
    print("Columnas encontradas:")
    for col in columns:
        print(f"  - {col[1]} ({col[2]})")
    conn.close()
except Exception as e:
    print(f"Error: {e}")

print()
print("="*80)
print()

# Intentar seleccionar la columna grupo si existe
print("2. INTENTANDO SELECCIONAR COLUMNA 'grupo':")
try:
    query = "SELECT id, nombre, tipo, categoria, grupo FROM maestro LIMIT 5"
    results = execute_query(query)
    print("✓ La columna 'grupo' EXISTE")
    print("Primeros 5 registros con grupo:")
    for r in results:
        print(f"  ID {r.get('id')}: {r.get('nombre')[:40]} - grupo: '{r.get('grupo')}' - categoria: '{r.get('categoria')}'")
except Exception as e:
    print(f"✗ La columna 'grupo' NO EXISTE o hay error: {e}")
    print()
    print("Verificando productos con categoria='Precios':")
    query2 = "SELECT id, nombre, tipo, categoria, pais FROM maestro WHERE categoria = 'Precios'"
    results2 = execute_query(query2)
    print(f"Total productos con categoria='Precios': {len(results2)}")
    for r in results2:
        print(f"  ID {r.get('id')}: {r.get('nombre')[:40]} - tipo: {r.get('tipo')} - pais: {r.get('pais')}")

print()
print("="*80)
print()

# Verificar si hay productos con pais='Uruguay' y categoria='Precios'
print("3. PRODUCTOS CON pais='Uruguay' AND categoria='Precios':")
try:
    query3 = "SELECT id, nombre, tipo, categoria, pais FROM maestro WHERE pais = 'Uruguay' AND categoria = 'Precios'"
    results3 = execute_query(query3)
    print(f"Total: {len(results3)} productos")
    for r in results3:
        print(f"  ID {r.get('id')}: {r.get('nombre')[:50]} (tipo: {r.get('tipo')}, categoria: {r.get('categoria')}, pais: {r.get('pais')})")
except Exception as e:
    print(f"Error: {e}")

print()
print("="*80)
print()

# Si existe grupo, verificar productos con grupo='Precios'
print("4. INTENTANDO BUSCAR CON grupo='Precios':")
try:
    query4 = "SELECT id, nombre, tipo, categoria, pais, grupo FROM maestro WHERE grupo = 'Precios'"
    results4 = execute_query(query4)
    print(f"Total productos con grupo='Precios': {len(results4)}")
    for r in results4:
        print(f"  ID {r.get('id')}: {r.get('nombre')[:50]} (tipo: {r.get('tipo')}, categoria: {r.get('categoria')}, grupo: {r.get('grupo')}, pais: {r.get('pais')})")
except Exception as e:
    print(f"Error o columna grupo no existe: {e}")

print()
print("="*80)
print("FIN")
print("="*80)
