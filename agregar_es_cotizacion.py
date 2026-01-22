"""Script para agregar columna es_cotizacion y actualizar registros."""
import sqlite3

conn = sqlite3.connect('series_tiempo.db')
cursor = conn.cursor()

# 1. Agregar columna es_cotizacion (si no existe)
try:
    cursor.execute("ALTER TABLE maestro ADD COLUMN es_cotizacion INTEGER DEFAULT 0")
    print("✓ Columna es_cotizacion agregada")
except sqlite3.OperationalError as e:
    if "duplicate column" in str(e).lower() or "already exists" in str(e).lower():
        print("⚠ Columna es_cotizacion ya existe")
    else:
        raise

# 2. Actualizar IDs 6, 22, 23, 24, 25
ids_cotizaciones = [6, 22, 23, 24, 25]
for product_id in ids_cotizaciones:
    cursor.execute("UPDATE maestro SET es_cotizacion = 1 WHERE id = ?", (product_id,))
    affected = cursor.rowcount
    if affected > 0:
        print(f"✓ ID {product_id} actualizado a es_cotizacion = 1")
    else:
        print(f"⚠ ID {product_id} no encontrado en la base de datos")

conn.commit()

# 3. Verificar
cursor.execute("""
    SELECT id, nombre, es_cotizacion 
    FROM maestro 
    WHERE id IN (6, 22, 23, 24, 25)
    ORDER BY id
""")
results = cursor.fetchall()
print("\nVerificación:")
for row in results:
    nombre_corto = row[1][:60] + "..." if len(row[1]) > 60 else row[1]
    print(f"  ID {row[0]}: {nombre_corto} | es_cotizacion = {row[2]}")

conn.close()
print("\n✓ Proceso completado")
