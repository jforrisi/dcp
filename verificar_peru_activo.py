"""Verificar estado de Perú (ID 24) en la base de datos."""
import sqlite3

conn = sqlite3.connect('series_tiempo.db')
cursor = conn.cursor()

print("=" * 80)
print("VERIFICACIÓN DE PERÚ (ID 24)")
print("=" * 80)

# Verificar registro en maestro
cursor.execute("""
    SELECT id, nombre, tipo, periodicidad, activo, es_cotizacion
    FROM maestro
    WHERE id = 24
""")

row = cursor.fetchone()
if row:
    print(f"\nRegistro en maestro:")
    print(f"  ID: {row[0]}")
    print(f"  Nombre: {row[1]}")
    print(f"  Tipo: {row[2]}")
    print(f"  Periodicidad: {row[3]}")
    print(f"  Activo: {row[4]} (tipo: {type(row[4]).__name__})")
    print(f"  es_cotizacion: {row[5] if len(row) > 5 and row[5] is not None else 'NULL'}")
    
    # Verificar si activo es 1 o True
    activo_value = row[4]
    if activo_value == 1 or activo_value == True or (isinstance(activo_value, bytes) and activo_value == b'\x01'):
        print(f"\n✓ activo está correcto (1/True)")
    else:
        print(f"\n❌ PROBLEMA: activo = {activo_value} (debería ser 1)")
        print(f"   → Necesitas actualizar: UPDATE maestro SET activo = 1 WHERE id = 24")
else:
    print("\n❌ ID 24 no encontrado en maestro")

# Verificar datos
cursor.execute("SELECT COUNT(*) FROM maestro_precios WHERE maestro_id = 24")
count = cursor.fetchone()[0]
print(f"\nRegistros en maestro_precios: {count}")

if count > 0:
    cursor.execute("""
        SELECT MIN(fecha) as primera, MAX(fecha) as ultima
        FROM maestro_precios 
        WHERE maestro_id = 24
    """)
    fecha_range = cursor.fetchone()
    print(f"Rango de fechas: {fecha_range[0]} a {fecha_range[1]}")

# Probar el query que usa el endpoint
print("\n" + "=" * 80)
print("PRUEBA DEL QUERY DEL ENDPOINT")
print("=" * 80)

query = """
    SELECT id, nombre, fuente, unidad, categoria
    FROM maestro
    WHERE id IN (24) AND activo = 1
"""

cursor.execute(query)
results = cursor.fetchall()

if results:
    print(f"✓ Query devuelve {len(results)} resultado(s):")
    for r in results:
        print(f"  ID {r[0]}: {r[1][:50]}...")
else:
    print("❌ Query NO devuelve resultados")
    print("\nProbando con CAST(activo AS INTEGER):")
    query2 = """
        SELECT id, nombre, fuente, unidad, categoria
        FROM maestro
        WHERE id IN (24) AND (activo = 1 OR CAST(activo AS INTEGER) = 1)
    """
    cursor.execute(query2)
    results2 = cursor.fetchall()
    if results2:
        print(f"✓ Con CAST funciona: {len(results2)} resultado(s)")
    else:
        print("❌ Tampoco funciona con CAST")

conn.close()
