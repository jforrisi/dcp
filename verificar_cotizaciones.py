"""Script para verificar las condiciones de cotizaciones en la base de datos."""
import sqlite3

conn = sqlite3.connect('series_tiempo.db')
cursor = conn.cursor()

# IDs a verificar
ids = [6, 22, 23]

print("=" * 80)
print("VERIFICACIÓN DE COTIZACIONES EN LA BASE DE DATOS")
print("=" * 80)
print()

for product_id in ids:
    print(f"\n{'='*80}")
    print(f"ID: {product_id}")
    print(f"{'='*80}")
    
    # Consultar el maestro
    cursor.execute("""
        SELECT id, nombre, tipo, fuente, periodicidad, unidad, categoria, activo
        FROM maestro
        WHERE id = ?
    """, (product_id,))
    
    row = cursor.fetchone()
    if row:
        print(f"Nombre: {row[1]}")
        print(f"Tipo: {row[2]} (M = Macro)")
        print(f"Fuente: {row[3]}")
        print(f"Periodicidad: {row[4]} (D = Diario)")
        print(f"Unidad: {row[5]}")
        print(f"Categoría: {row[6]}")
        print(f"Activo: {row[7]}")
        
        # Verificar condiciones
        print("\n--- Verificación de condiciones ---")
        tipo_ok = row[2] == 'M'
        activo_ok = row[7] == 1
        periodicidad_ok = row[4] == 'D'
        categoria_ok = row[6] and ('Tipo de cambio' in row[6] or 'tipo de cambio' in row[6])
        id_ok = product_id in [6, 22, 23]
        
        print(f"tipo = 'M': {tipo_ok} {'✓' if tipo_ok else '✗'}")
        print(f"activo = 1: {activo_ok} {'✓' if activo_ok else '✗'}")
        print(f"periodicidad = 'D': {periodicidad_ok} {'✓' if periodicidad_ok else '✗'}")
        print(f"categoria LIKE '%Tipo de cambio%': {categoria_ok} {'✓' if categoria_ok else '✗'}")
        print(f"id IN (6, 22, 23): {id_ok} {'✓' if id_ok else '✗'}")
        
        # Verificar si cumple todas las condiciones del query
        cumple_condiciones = tipo_ok and activo_ok and periodicidad_ok and (categoria_ok or id_ok)
        print(f"\n¿Cumple condiciones del query?: {cumple_condiciones} {'✓' if cumple_condiciones else '✗'}")
        
        # Contar registros de precios
        cursor.execute("""
            SELECT COUNT(*) 
            FROM maestro_precios 
            WHERE maestro_id = ?
        """, (product_id,))
        count = cursor.fetchone()[0]
        print(f"\nRegistros en maestro_precios: {count}")
        
        if count > 0:
            # Mostrar primer y último registro
            cursor.execute("""
                SELECT fecha, valor 
                FROM maestro_precios 
                WHERE maestro_id = ? 
                ORDER BY fecha ASC 
                LIMIT 1
            """, (product_id,))
            first = cursor.fetchone()
            if first:
                print(f"Primer registro: {first[0]} = {first[1]}")
            
            cursor.execute("""
                SELECT fecha, valor 
                FROM maestro_precios 
                WHERE maestro_id = ? 
                ORDER BY fecha DESC 
                LIMIT 1
            """, (product_id,))
            last = cursor.fetchone()
            if last:
                print(f"Último registro: {last[0]} = {last[1]}")
    else:
        print(f"❌ ERROR: No se encontró el ID {product_id} en la tabla maestro")

print("\n" + "=" * 80)
print("VERIFICACIÓN COMPLETA")
print("=" * 80)

conn.close()
