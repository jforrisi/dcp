"""Verificar todas las cotizaciones en la base de datos."""
import sqlite3
from datetime import datetime

conn = sqlite3.connect('series_tiempo.db')
cursor = conn.cursor()

print("=" * 80)
print("VERIFICACIÓN DE COTIZACIONES EN LA BASE DE DATOS")
print("=" * 80)

# Obtener todas las cotizaciones (tipo='M', periodicidad='D', es_cotizacion=1)
cursor.execute("""
    SELECT id, nombre, tipo, periodicidad, activo, es_cotizacion, moneda, fuente
    FROM maestro
    WHERE tipo = 'M' 
    AND periodicidad = 'D'
    AND es_cotizacion = 1
    ORDER BY id
""")

cotizaciones = cursor.fetchall()

print(f"\nTotal de cotizaciones marcadas (es_cotizacion=1): {len(cotizaciones)}")
print("=" * 80)

for row in cotizaciones:
    product_id = row[0]
    nombre = row[1]
    tipo = row[2]
    periodicidad = row[3]
    activo = row[4]
    es_cotizacion = row[5]
    moneda = row[6] if len(row) > 6 else None
    fuente = row[7] if len(row) > 7 else None
    
    print(f"\nID {product_id}: {nombre}")
    print(f"  Tipo: {tipo}, Periodicidad: {periodicidad}")
    print(f"  Activo: {activo}, es_cotizacion: {es_cotizacion}")
    if moneda:
        print(f"  Moneda: {moneda}")
    if fuente:
        print(f"  Fuente: {fuente}")
    
    # Verificar datos en maestro_precios
    cursor.execute("SELECT COUNT(*) FROM maestro_precios WHERE maestro_id = ?", (product_id,))
    count = cursor.fetchone()[0]
    
    if count > 0:
        cursor.execute("""
            SELECT MIN(fecha) as primera, MAX(fecha) as ultima, COUNT(*) as total
            FROM maestro_precios 
            WHERE maestro_id = ?
        """, (product_id,))
        fecha_info = cursor.fetchone()
        print(f"  ✓ Datos: {fecha_info[2]} registros")
        print(f"  ✓ Rango: {fecha_info[0]} a {fecha_info[1]}")
        
        # Mostrar algunos valores recientes
        cursor.execute("""
            SELECT fecha, valor 
            FROM maestro_precios 
            WHERE maestro_id = ? 
            ORDER BY fecha DESC 
            LIMIT 3
        """, (product_id,))
        recent = cursor.fetchall()
        print(f"  Últimos 3 valores:")
        for f, v in recent:
            print(f"    {f}: {v}")
    else:
        print(f"  ❌ Sin datos en maestro_precios")

# Verificar también todas las que tienen tipo='M' y periodicidad='D' aunque no tengan es_cotizacion=1
print("\n" + "=" * 80)
print("OTRAS SERIES QUE PODRÍAN SER COTIZACIONES")
print("(tipo='M' y periodicidad='D' pero es_cotizacion != 1)")
print("=" * 80)

cursor.execute("""
    SELECT id, nombre, tipo, periodicidad, activo, es_cotizacion
    FROM maestro
    WHERE tipo = 'M' 
    AND periodicidad = 'D'
    AND (es_cotizacion != 1 OR es_cotizacion IS NULL)
    ORDER BY id
""")

otras = cursor.fetchall()

if otras:
    print(f"\nTotal: {len(otras)}")
    for row in otras:
        product_id = row[0]
        nombre = row[1]
        activo = row[4]
        es_cotizacion = row[5]
        
        cursor.execute("SELECT COUNT(*) FROM maestro_precios WHERE maestro_id = ?", (product_id,))
        count = cursor.fetchone()[0]
        
        status = "✓" if count > 0 else "❌"
        print(f"  {status} ID {product_id}: {nombre[:60]}... | activo={activo} | es_cotizacion={es_cotizacion} | registros={count}")
else:
    print("\nNo hay otras series con estas características")

conn.close()
print("\n" + "=" * 80)
print("VERIFICACIÓN COMPLETA")
print("=" * 80)
