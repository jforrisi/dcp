"""Diagnóstico de datos para Chile (ID 25) y Perú (ID 24)."""
import sqlite3
from datetime import date

conn = sqlite3.connect('series_tiempo.db')
cursor = conn.cursor()

print("=" * 80)
print("DIAGNÓSTICO: CHILE (ID 25) Y PERÚ (ID 24)")
print("=" * 80)

for product_id, country in [(24, "Perú"), (25, "Chile")]:
    print(f"\n{'='*80}")
    print(f"{country} (ID {product_id})")
    print(f"{'='*80}")
    
    # Verificar en maestro
    cursor.execute("""
        SELECT id, nombre, tipo, periodicidad, activo, es_cotizacion
        FROM maestro
        WHERE id = ?
    """, (product_id,))
    
    maestro_row = cursor.fetchone()
    if maestro_row:
        print(f"✓ Encontrado en maestro:")
        print(f"  Nombre: {maestro_row[1]}")
        print(f"  Tipo: {maestro_row[2]}")
        print(f"  Periodicidad: {maestro_row[3]}")
        print(f"  Activo: {maestro_row[4]} (tipo: {type(maestro_row[4]).__name__})")
        print(f"  es_cotizacion: {maestro_row[5] if len(maestro_row) > 5 and maestro_row[5] is not None else 'NULL'}")
    else:
        print(f"❌ NO encontrado en maestro")
        continue
    
    # Verificar datos en maestro_precios
    cursor.execute("SELECT COUNT(*) FROM maestro_precios WHERE maestro_id = ?", (product_id,))
    total_count = cursor.fetchone()[0]
    print(f"\n  Total de registros en maestro_precios: {total_count}")
    
    if total_count == 0:
        print(f"  ❌ PROBLEMA: No hay datos en maestro_precios")
        print(f"  → Necesitas ejecutar el script de actualización:")
        if product_id == 24:
            print(f"     python macro/update/nxr_peru.py")
        else:
            print(f"     python macro/update/nxr_chile.py")
    else:
        # Mostrar rango de fechas
        cursor.execute("""
            SELECT MIN(fecha) as primera, MAX(fecha) as ultima, COUNT(*) as total
            FROM maestro_precios 
            WHERE maestro_id = ?
        """, (product_id,))
        fecha_info = cursor.fetchone()
        print(f"  ✓ Rango de fechas: {fecha_info[0]} a {fecha_info[1]}")
        print(f"  ✓ Total de registros: {fecha_info[2]}")
        
        # Mostrar algunos valores recientes
        cursor.execute("""
            SELECT fecha, valor 
            FROM maestro_precios 
            WHERE maestro_id = ? 
            ORDER BY fecha DESC 
            LIMIT 5
        """, (product_id,))
        recent = cursor.fetchall()
        print(f"  Últimos 5 valores:")
        for f, v in recent:
            print(f"    {f}: {v}")
        
        # Verificar si hay datos en un rango reciente (últimos 6 meses)
        from datetime import datetime, timedelta
        fecha_hasta = date.today()
        fecha_desde = fecha_hasta - timedelta(days=180)
        
        cursor.execute("""
            SELECT COUNT(*) 
            FROM maestro_precios 
            WHERE maestro_id = ? 
            AND fecha >= ? AND fecha <= ?
        """, (product_id, fecha_desde.isoformat(), fecha_hasta.isoformat()))
        recent_count = cursor.fetchone()[0]
        print(f"\n  Registros en últimos 6 meses ({fecha_desde} a {fecha_hasta}): {recent_count}")
        if recent_count == 0:
            print(f"  ⚠ ADVERTENCIA: No hay datos recientes")

conn.close()
print("\n" + "=" * 80)
print("FIN DEL DIAGNÓSTICO")
print("=" * 80)
