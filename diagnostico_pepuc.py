"""
Script de diagnóstico para PEPUC - verifica qué productos deberían aparecer
"""
import sys
sys.path.insert(0, 'backend')

from app.database import execute_query

print("=== DIAGNÓSTICO PEPUC ===\n")

# Query actual de PEPUC
print("1. PRODUCTOS CON QUERY ACTUAL DE PEPUC:")
query_actual = """
    SELECT id, nombre, tipo, categoria, pais, activo
    FROM maestro
    WHERE activo = 1
    AND tipo != 'M'
    AND (
        (categoria IS NOT NULL AND categoria != '')
        OR (pais = 'Uruguay' AND categoria = 'Precios')
    )
    ORDER BY categoria, nombre
"""
resultados_actuales = execute_query(query_actual)
print(f"Total: {len(resultados_actuales)} productos\n")

# Agrupar por categoría
categorias_actuales = {}
for r in resultados_actuales:
    cat = r.get('categoria', 'NULL')
    if cat not in categorias_actuales:
        categorias_actuales[cat] = []
    categorias_actuales[cat].append(r)

print("Agrupados por categoría:")
for cat, productos in sorted(categorias_actuales.items()):
    print(f"  {cat}: {len(productos)} productos")
    for p in productos[:3]:  # Mostrar primeros 3
        print(f"    - ID {p['id']}: {p['nombre'][:60]}")

print("\n" + "="*80 + "\n")

# Productos con categoria P o S
print("2. PRODUCTOS CON CATEGORIA = 'P' O 'S':")
query_p_s = """
    SELECT id, nombre, tipo, categoria, pais, activo
    FROM maestro
    WHERE activo = 1
    AND categoria IN ('P', 'S')
    ORDER BY categoria, nombre
"""
resultados_p_s = execute_query(query_p_s)
print(f"Total: {len(resultados_p_s)} productos\n")
for r in resultados_p_s[:10]:
    print(f"  ID {r['id']}: {r['nombre'][:60]} (categoria: {r['categoria']})")

print("\n" + "="*80 + "\n")

# Productos con categoria no nula (sin excluir macros)
print("3. TODOS LOS PRODUCTOS CON CATEGORIA NO NULA (incluyendo macros):")
query_todos_cat = """
    SELECT id, nombre, tipo, categoria, pais, activo
    FROM maestro
    WHERE activo = 1
    AND categoria IS NOT NULL 
    AND categoria != ''
    ORDER BY tipo, categoria, nombre
"""
resultados_todos_cat = execute_query(query_todos_cat)
print(f"Total: {len(resultados_todos_cat)} productos\n")

# Agrupar por tipo y categoría
por_tipo_cat = {}
for r in resultados_todos_cat:
    key = f"{r['tipo']} - {r.get('categoria', 'NULL')}"
    if key not in por_tipo_cat:
        por_tipo_cat[key] = []
    por_tipo_cat[key].append(r)

print("Agrupados por tipo y categoría:")
for key, productos in sorted(por_tipo_cat.items()):
    print(f"  {key}: {len(productos)} productos")

print("\n" + "="*80 + "\n")

# Productos internos (Uruguay + Precios)
print("4. PRODUCTOS INTERNOS (pais='Uruguay' AND categoria='Precios'):")
query_internos = """
    SELECT id, nombre, tipo, categoria, pais, activo
    FROM maestro
    WHERE activo = 1
    AND pais = 'Uruguay' 
    AND categoria = 'Precios'
    ORDER BY nombre
"""
resultados_internos = execute_query(query_internos)
print(f"Total: {len(resultados_internos)} productos\n")
for r in resultados_internos:
    print(f"  ID {r['id']}: {r['nombre'][:60]}")

print("\n" + "="*80 + "\n")

# Comparación: qué productos están en P/S pero no en query actual
print("5. PRODUCTOS CON CATEGORIA='P' O 'S' QUE NO ESTÁN EN QUERY ACTUAL:")
ids_actuales = {r['id'] for r in resultados_actuales}
faltantes = [r for r in resultados_p_s if r['id'] not in ids_actuales]
print(f"Total faltantes: {len(faltantes)}\n")
for r in faltantes:
    print(f"  ID {r['id']}: {r['nombre'][:60]} (categoria: {r['categoria']}, tipo: {r['tipo']})")

print("\n" + "="*80 + "\n")

# Valores únicos de categoria
print("6. VALORES ÚNICOS DE CATEGORIA (activos, excluyendo macros):")
query_categorias = """
    SELECT DISTINCT categoria, COUNT(*) as count
    FROM maestro
    WHERE activo = 1
    AND tipo != 'M'
    AND categoria IS NOT NULL
    AND categoria != ''
    GROUP BY categoria
    ORDER BY count DESC
"""
categorias = execute_query(query_categorias)
print("Categorías y cantidad:")
for r in categorias:
    print(f"  '{r['categoria']}': {r['count']} productos")
