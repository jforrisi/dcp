"""
Script para probar el endpoint /dcp/products
"""
import sys
sys.path.insert(0, 'backend')

from app.database import execute_query

print("="*80)
print("PRUEBA DEL ENDPOINT /dcp/products")
print("="*80)
print()

# Query que usa el endpoint
query = """
    SELECT id, nombre, tipo, unidad, categoria, fuente, periodicidad, activo, pais
    FROM maestro
    WHERE activo = 1
    AND categoria IN ('P', 'S', 'I')
    ORDER BY nombre
"""

results = execute_query(query)

print(f"Total productos encontrados: {len(results)}")
print()

if len(results) > 0:
    print("PRIMEROS 10 PRODUCTOS:")
    print(f"{'ID':<5} {'Nombre':<50} {'Categoria':<10} {'Tipo':<5}")
    print("-" * 80)
    for r in results[:10]:
        id_val = str(r.get('id', ''))[:5]
        nombre_val = str(r.get('nombre', ''))[:50]
        categoria_val = str(r.get('categoria', 'NULL'))[:10]
        tipo_val = str(r.get('tipo', 'NULL'))[:5]
        print(f"{id_val:<5} {nombre_val:<50} {categoria_val:<10} {tipo_val:<5}")
    
    print()
    print("RESUMEN POR CATEGORIA:")
    categorias = {}
    for r in results:
        cat = r.get('categoria', 'NULL')
        categorias[cat] = categorias.get(cat, 0) + 1
    for cat, count in sorted(categorias.items()):
        print(f"  '{cat}': {count} productos")
else:
    print("NO SE ENCONTRARON PRODUCTOS")
    print()
    print("Verificando productos activos sin filtro de categoria:")
    query_all = "SELECT id, nombre, categoria, activo FROM maestro WHERE activo = 1 LIMIT 10"
    all_results = execute_query(query_all)
    print(f"Total productos activos: {len(all_results)}")
    for r in all_results:
        print(f"  ID {r.get('id')}: {r.get('nombre')[:50]} - categoria: {r.get('categoria')}")

print()
print("="*80)
print("FIN")
print("="*80)
