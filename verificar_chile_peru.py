"""Script para verificar datos de Chile y Perú."""
import sqlite3

conn = sqlite3.connect('series_tiempo.db')
cursor = conn.cursor()

# Buscar Chile y Perú en el maestro
print("=" * 80)
print("BÚSQUEDA DE CHILE Y PERÚ EN MAESTRO")
print("=" * 80)

cursor.execute("""
    SELECT id, nombre, tipo, periodicidad, activo, es_cotizacion
    FROM maestro
    WHERE nombre LIKE '%Chile%' OR nombre LIKE '%Perú%' OR nombre LIKE '%Peru%'
       OR nombre LIKE '%CLP%' OR nombre LIKE '%PEN%'
    ORDER BY id
""")

results = cursor.fetchall()

if results:
    print(f"\nSe encontraron {len(results)} registros:")
    for row in results:
        print(f"\n  ID: {row[0]}")
        print(f"  Nombre: {row[1]}")
        print(f"  Tipo: {row[2]}")
        print(f"  Periodicidad: {row[3]}")
        print(f"  Activo: {row[4]} (tipo: {type(row[4]).__name__})")
        print(f"  es_cotizacion: {row[5] if len(row) > 5 else 'N/A'}")
        
        # Verificar datos en maestro_precios
        cursor.execute("SELECT COUNT(*) FROM maestro_precios WHERE maestro_id = ?", (row[0],))
        count = cursor.fetchone()[0]
        print(f"  Registros en maestro_precios: {count}")
        
        if count > 0:
            cursor.execute("""
                SELECT MIN(fecha) as primera, MAX(fecha) as ultima
                FROM maestro_precios 
                WHERE maestro_id = ?
            """, (row[0],))
            fecha_range = cursor.fetchone()
            print(f"  Rango de fechas: {fecha_range[0]} a {fecha_range[1]}")
            
            # Mostrar algunos valores recientes
            cursor.execute("""
                SELECT fecha, valor 
                FROM maestro_precios 
                WHERE maestro_id = ? 
                ORDER BY fecha DESC 
                LIMIT 5
            """, (row[0],))
            recent = cursor.fetchall()
            print(f"  Últimos 5 valores:")
            for f, v in recent:
                print(f"    {f}: {v}")
else:
    print("\n❌ No se encontraron registros para Chile o Perú")

# Verificar también IDs 24 y 25 específicamente
print("\n" + "=" * 80)
print("VERIFICACIÓN ESPECÍFICA DE IDs 24 Y 25")
print("=" * 80)

for product_id in [24, 25]:
    cursor.execute("""
        SELECT id, nombre, tipo, periodicidad, activo, es_cotizacion
        FROM maestro
        WHERE id = ?
    """, (product_id,))
    
    row = cursor.fetchone()
    if row:
        print(f"\n  ID {product_id}: {row[1]}")
        print(f"    Tipo: {row[2]}, Periodicidad: {row[3]}")
        print(f"    Activo: {row[4]}, es_cotizacion: {row[5] if len(row) > 5 else 'N/A'}")
        
        cursor.execute("SELECT COUNT(*) FROM maestro_precios WHERE maestro_id = ?", (product_id,))
        count = cursor.fetchone()[0]
        print(f"    Registros: {count}")
    else:
        print(f"\n  ❌ ID {product_id} no encontrado")

conn.close()
print("\n" + "=" * 80)
print("VERIFICACIÓN COMPLETA")
print("=" * 80)
