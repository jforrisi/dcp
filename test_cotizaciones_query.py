"""Script para probar el query de cotizaciones."""
import sqlite3

conn = sqlite3.connect('series_tiempo.db')
cursor = conn.cursor()

# Query exacto del backend
query = """
    SELECT id, nombre, fuente, unidad, categoria, periodicidad, activo
    FROM maestro
    WHERE tipo = 'M' 
    AND (activo = 1 OR CAST(activo AS INTEGER) = 1)
    AND periodicidad = 'D'
    AND (
        id IN (6, 22, 23)
        OR categoria LIKE '%Tipo de cambio%' 
        OR categoria LIKE '%tipo de cambio%'
        OR nombre LIKE '%USD/UYU%'
        OR nombre LIKE '%USD/ARS%'
        OR nombre LIKE '%USD/BRL%'
    )
    ORDER BY nombre
"""

print("=" * 80)
print("RESULTADOS DEL QUERY DE COTIZACIONES")
print("=" * 80)
print()

cursor.execute(query)
results = cursor.fetchall()

if results:
    for row in results:
        print(f"ID: {row[0]}")
        print(f"Nombre: {row[1]}")
        print(f"Fuente: {row[2]}")
        print(f"Unidad: {row[3]}")
        print(f"Categoría: {row[4]}")
        print(f"Periodicidad: {row[5]}")
        print(f"Activo: {row[6]} (tipo: {type(row[6]).__name__})")
        print("-" * 80)
else:
    print("❌ No se encontraron resultados")

print(f"\nTotal encontrados: {len(results)}")

# Verificar específicamente Uruguay
print("\n" + "=" * 80)
print("VERIFICACIÓN ESPECÍFICA DE URUGUAY (ID 6)")
print("=" * 80)
cursor.execute("SELECT id, nombre, tipo, activo, periodicidad, categoria FROM maestro WHERE id = 6")
uruguay = cursor.fetchone()
if uruguay:
    print(f"ID: {uruguay[0]}")
    print(f"Nombre: {uruguay[1]}")
    print(f"Tipo: {uruguay[2]}")
    print(f"Activo: {uruguay[3]} (tipo: {type(uruguay[3]).__name__})")
    print(f"Periodicidad: {uruguay[4]}")
    print(f"Categoría: {uruguay[5]}")
    print()
    print("Verificación de condiciones:")
    print(f"  tipo = 'M': {uruguay[2] == 'M'}")
    print(f"  activo = 1: {uruguay[3] == 1}")
    print(f"  CAST(activo AS INTEGER) = 1: {bool(cursor.execute('SELECT CAST(? AS INTEGER)', (uruguay[3],)).fetchone()[0] == 1)}")
    print(f"  periodicidad = 'D': {uruguay[4] == 'D'}")
    print(f"  id IN (6, 22, 23): {uruguay[0] in [6, 22, 23]}")
    print(f"  nombre LIKE '%USD/UYU%': {'USD/UYU' in uruguay[1]}")
else:
    print("❌ Uruguay (ID 6) no encontrado en la base de datos")

conn.close()
