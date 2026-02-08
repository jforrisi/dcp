import sqlite3

conn = sqlite3.connect('series_tiempo.db')
cursor = conn.cursor()

print("=== TODOS LOS PRODUCTOS ACTIVOS ===")
cursor.execute("""
    SELECT id, nombre, tipo, categoria, pais, activo
    FROM maestro
    WHERE activo = 1
    ORDER BY categoria, nombre
""")
all_products = cursor.fetchall()
print(f"Total productos activos: {len(all_products)}")
for row in all_products:
    print(f"  ID: {row[0]}, Nombre: {row[1][:50]}, Tipo: {row[2]}, Categoria: {row[3]}, Pais: {row[4]}")

print("\n=== PRODUCTOS CON CATEGORIA NO NULA ===")
cursor.execute("""
    SELECT id, nombre, tipo, categoria, pais, activo
    FROM maestro
    WHERE activo = 1
    AND categoria IS NOT NULL 
    AND categoria != ''
    ORDER BY categoria, nombre
""")
cat_not_null = cursor.fetchall()
print(f"Total con categoria no nula: {len(cat_not_null)}")
for row in cat_not_null[:20]:  # Mostrar primeros 20
    print(f"  ID: {row[0]}, Nombre: {row[1][:50]}, Categoria: {row[3]}, Pais: {row[4]}")

print("\n=== PRODUCTOS INTERNOS (Uruguay + Precios) ===")
cursor.execute("""
    SELECT id, nombre, tipo, categoria, pais, activo
    FROM maestro
    WHERE activo = 1
    AND pais = 'Uruguay' 
    AND categoria = 'Precios'
    ORDER BY nombre
""")
internos = cursor.fetchall()
print(f"Total internos: {len(internos)}")
for row in internos:
    print(f"  ID: {row[0]}, Nombre: {row[1][:50]}, Categoria: {row[3]}, Pais: {row[4]}")

print("\n=== QUERY ACTUAL DE PEPUC ===")
cursor.execute("""
    SELECT id, nombre, tipo, categoria, pais, activo
    FROM maestro
    WHERE activo = 1
    AND (
        (categoria IS NOT NULL AND categoria != '')
        OR (pais = 'Uruguay' AND categoria = 'Precios')
    )
    ORDER BY nombre
""")
pepuc_products = cursor.fetchall()
print(f"Total productos PEPUC: {len(pepuc_products)}")
for row in pepuc_products[:30]:  # Mostrar primeros 30
    print(f"  ID: {row[0]}, Nombre: {row[1][:50]}, Categoria: {row[3]}, Pais: {row[4]}")

print("\n=== VALORES ÚNICOS DE CATEGORIA ===")
cursor.execute("""
    SELECT DISTINCT categoria, COUNT(*) as count
    FROM maestro
    WHERE activo = 1
    GROUP BY categoria
    ORDER BY count DESC
""")
categorias = cursor.fetchall()
print("Categorías y cantidad de productos:")
for row in categorias:
    print(f"  '{row[0]}': {row[1]} productos")

print("\n=== PRODUCTOS QUE NO APARECEN EN PEPUC ===")
cursor.execute("""
    SELECT id, nombre, tipo, categoria, pais, activo
    FROM maestro
    WHERE activo = 1
    AND NOT (
        (categoria IS NOT NULL AND categoria != '')
        OR (pais = 'Uruguay' AND categoria = 'Precios')
    )
    ORDER BY nombre
""")
missing = cursor.fetchall()
print(f"Total productos que NO aparecen: {len(missing)}")
for row in missing:
    print(f"  ID: {row[0]}, Nombre: {row[1][:50]}, Tipo: {row[2]}, Categoria: '{row[3]}', Pais: '{row[4]}'")

conn.close()
