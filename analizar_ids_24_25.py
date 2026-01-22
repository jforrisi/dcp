"""Script para analizar IDs 24 y 25 y verificar por qué Uruguay no aparece."""
import sqlite3

conn = sqlite3.connect('series_tiempo.db')
cursor = conn.cursor()

# Analizar IDs 24 y 25
print("=" * 80)
print("ANÁLISIS DE IDs 24 Y 25")
print("=" * 80)
print()

for product_id in [24, 25]:
    print(f"\n{'='*80}")
    print(f"ID: {product_id}")
    print(f"{'='*80}")
    
    cursor.execute("""
        SELECT id, nombre, tipo, fuente, periodicidad, unidad, categoria, activo
        FROM maestro
        WHERE id = ?
    """, (product_id,))
    
    row = cursor.fetchone()
    if row:
        print(f"Nombre: {row[1]}")
        print(f"Tipo: {row[2]}")
        print(f"Fuente: {row[3]}")
        print(f"Periodicidad: {row[4]}")
        print(f"Unidad: {row[5]}")
        print(f"Categoría: {row[6]}")
        print(f"Activo: {row[7]} (tipo: {type(row[7]).__name__})")
        
        # Contar registros
        cursor.execute("SELECT COUNT(*) FROM maestro_precios WHERE maestro_id = ?", (product_id,))
        count = cursor.fetchone()[0]
        print(f"Registros en maestro_precios: {count}")
        
        if count > 0:
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
        print(f"❌ ID {product_id} no encontrado")

# Verificar Uruguay (ID 6) específicamente
print("\n" + "=" * 80)
print("VERIFICACIÓN DE URUGUAY (ID 6)")
print("=" * 80)
cursor.execute("""
    SELECT id, nombre, tipo, fuente, periodicidad, unidad, categoria, activo
    FROM maestro
    WHERE id = 6
""")
uruguay = cursor.fetchone()
if uruguay:
    print(f"Nombre: {uruguay[1]}")
    print(f"Tipo: {uruguay[2]}")
    print(f"Periodicidad: {uruguay[4]}")
    print(f"Categoría: {uruguay[6]}")
    print(f"Activo: {uruguay[7]} (tipo: {type(uruguay[7]).__name__})")
    
    # Probar el query exacto
    print("\n--- Probando query del backend ---")
    test_query = """
        SELECT id, nombre, fuente, unidad, categoria, periodicidad
        FROM maestro
        WHERE tipo = 'M' 
        AND periodicidad = 'D'
        AND (
            id IN (6, 22, 23)
            OR (
                (categoria LIKE '%Tipo de cambio%' OR categoria LIKE '%tipo de cambio%')
                AND (activo = 1 OR CAST(activo AS INTEGER) = 1)
            )
        )
        ORDER BY nombre
    """
    cursor.execute(test_query)
    results = cursor.fetchall()
    print(f"Resultados del query: {len(results)}")
    for r in results:
        print(f"  - ID {r[0]}: {r[1]}")
else:
    print("❌ Uruguay (ID 6) no encontrado")

# Buscar todos los tipos de cambio diarios
print("\n" + "=" * 80)
print("TODOS LOS TIPOS DE CAMBIO DIARIOS EN LA BASE")
print("=" * 80)
cursor.execute("""
    SELECT id, nombre, categoria, activo, periodicidad
    FROM maestro
    WHERE tipo = 'M' 
    AND periodicidad = 'D'
    AND (categoria LIKE '%Tipo de cambio%' OR categoria LIKE '%tipo de cambio%' OR nombre LIKE '%USD/%' OR nombre LIKE '%EUR/%')
    ORDER BY id
""")
all_tc = cursor.fetchall()
print(f"Total encontrados: {len(all_tc)}")
for row in all_tc:
    print(f"  ID {row[0]}: {row[1]} | Categoría: {row[2]} | Activo: {row[3]} | Periodicidad: {row[4]}")

conn.close()
