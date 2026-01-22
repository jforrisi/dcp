"""Activar todas las cotizaciones (activo = 1)."""
import sqlite3

conn = sqlite3.connect('series_tiempo.db')
cursor = conn.cursor()

print("=" * 80)
print("ACTIVAR TODAS LAS COTIZACIONES")
print("=" * 80)

# Primero, verificar cuántas hay
cursor.execute("""
    SELECT COUNT(*) 
    FROM maestro
    WHERE tipo = 'M' 
    AND periodicidad = 'D'
    AND es_cotizacion = 1
""")
total = cursor.fetchone()[0]
print(f"\nTotal de cotizaciones encontradas: {total}")

# Listar antes de actualizar
cursor.execute("""
    SELECT id, nombre, activo
    FROM maestro
    WHERE tipo = 'M' 
    AND periodicidad = 'D'
    AND es_cotizacion = 1
    ORDER BY id
""")
cotizaciones = cursor.fetchall()

print("\nEstado ANTES de actualizar:")
print("-" * 80)
for row in cotizaciones:
    product_id = row[0]
    nombre = row[1]
    activo_actual = row[2]
    print(f"  ID {product_id}: {nombre[:50]}... | activo = {activo_actual}")

# Actualizar todas a activo = 1
cursor.execute("""
    UPDATE maestro
    SET activo = 1
    WHERE tipo = 'M' 
    AND periodicidad = 'D'
    AND es_cotizacion = 1
""")
affected = cursor.rowcount
conn.commit()

print(f"\n✓ Actualizadas {affected} cotizaciones a activo = 1")

# Verificar después de actualizar
cursor.execute("""
    SELECT id, nombre, activo
    FROM maestro
    WHERE tipo = 'M' 
    AND periodicidad = 'D'
    AND es_cotizacion = 1
    ORDER BY id
""")
cotizaciones_after = cursor.fetchall()

print("\nEstado DESPUÉS de actualizar:")
print("-" * 80)
for row in cotizaciones_after:
    product_id = row[0]
    nombre = row[1]
    activo_nuevo = row[2]
    status = "✓" if activo_nuevo == 1 else "❌"
    print(f"  {status} ID {product_id}: {nombre[:50]}... | activo = {activo_nuevo}")

# Verificar que todas quedaron en 1
cursor.execute("""
    SELECT COUNT(*) 
    FROM maestro
    WHERE tipo = 'M' 
    AND periodicidad = 'D'
    AND es_cotizacion = 1
    AND activo = 1
""")
total_activas = cursor.fetchone()[0]

print(f"\n✓ Total de cotizaciones activas: {total_activas} de {total}")

conn.close()
print("\n" + "=" * 80)
print("PROCESO COMPLETADO")
print("=" * 80)
