"""Verificación completa de todas las cotizaciones."""
import sqlite3

conn = sqlite3.connect('series_tiempo.db')
cursor = conn.cursor()

print("=" * 80)
print("VERIFICACIÓN COMPLETA DE COTIZACIONES")
print("=" * 80)

# Verificar que la columna es_cotizacion existe
try:
    cursor.execute("SELECT es_cotizacion FROM maestro LIMIT 1")
    print("✓ Columna es_cotizacion existe")
except sqlite3.OperationalError:
    print("❌ Columna es_cotizacion NO existe - ejecuta agregar_es_cotizacion.py")
    conn.close()
    exit(1)

# Obtener todas las cotizaciones
cursor.execute("""
    SELECT id, nombre, tipo, periodicidad, activo, es_cotizacion
    FROM maestro
    WHERE es_cotizacion = 1
    ORDER BY id
""")

cotizaciones = cursor.fetchall()

print(f"\nCotizaciones marcadas (es_cotizacion = 1): {len(cotizaciones)}")
print("-" * 80)

for row in cotizaciones:
    product_id = row[0]
    nombre = row[1]
    tipo = row[2]
    periodicidad = row[3]
    activo = row[4]
    es_cotizacion = row[5]
    
    print(f"\nID {product_id}: {nombre[:60]}")
    print(f"  Tipo: {tipo}, Periodicidad: {periodicidad}, Activo: {activo}, es_cotizacion: {es_cotizacion}")
    
    # Verificar datos
    cursor.execute("SELECT COUNT(*) FROM maestro_precios WHERE maestro_id = ?", (product_id,))
    count = cursor.fetchone()[0]
    
    if count > 0:
        cursor.execute("""
            SELECT MIN(fecha) as primera, MAX(fecha) as ultima
            FROM maestro_precios 
            WHERE maestro_id = ?
        """, (product_id,))
        fecha_range = cursor.fetchone()
        print(f"  ✓ Datos: {count} registros ({fecha_range[0]} a {fecha_range[1]})")
    else:
        print(f"  ❌ Sin datos en maestro_precios")
        if product_id == 25:
            print(f"     → Ejecuta: python macro/update/nxr_chile.py (después de instalar bcchapi)")

# Verificar IDs esperados
ids_esperados = [6, 22, 23, 24, 25]
print("\n" + "=" * 80)
print("VERIFICACIÓN DE IDs ESPERADOS")
print("=" * 80)

for product_id in ids_esperados:
    cursor.execute("""
        SELECT id, nombre, es_cotizacion
        FROM maestro
        WHERE id = ?
    """, (product_id,))
    
    row = cursor.fetchone()
    if row:
        status = "✓" if row[2] == 1 else "⚠ (es_cotizacion = 0)"
        print(f"  ID {product_id}: {row[1][:50]}... {status}")
    else:
        print(f"  ❌ ID {product_id}: NO EXISTE en maestro")

conn.close()
print("\n" + "=" * 80)
print("FIN DE VERIFICACIÓN")
print("=" * 80)
