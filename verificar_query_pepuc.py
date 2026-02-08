"""
Script para verificar qué devuelve la query de PEPUC
"""
import sys
sys.path.insert(0, 'backend')

from app.database import execute_query

print("="*80)
print("VERIFICACIÓN DE QUERY PEPUC")
print("="*80)
print()

# Query actual de PEPUC
query = """
    SELECT id, nombre, tipo, unidad, categoria, fuente, periodicidad, activo, pais
    FROM maestro
    WHERE activo = 1
    AND (
        tipo IN ('P', 'S')
        OR (pais = 'Uruguay' AND categoria = 'Precios')
    )
    ORDER BY nombre
"""

print("QUERY EJECUTADA:")
print(query)
print()
print("="*80)
print()

# Ejecutar query
results = execute_query(query)

print(f"TOTAL DE PRODUCTOS ENCONTRADOS: {len(results)}")
print()
print("="*80)
print()

# Mostrar las primeras 5 columnas de los resultados
if len(results) > 0:
    print("PRIMERAS 5 COLUMNAS DE LOS RESULTADOS:")
    print(f"{'ID':<6} {'Nombre':<50} {'Tipo':<6} {'Unidad':<15} {'Categoria':<30}")
    print(f"{'-'*6} {'-'*50} {'-'*6} {'-'*15} {'-'*30}")
    
    for i, r in enumerate(results):
        id_val = str(r.get('id', ''))[:6]
        nombre_val = str(r.get('nombre', ''))[:50]
        tipo_val = str(r.get('tipo', ''))[:6]
        unidad_val = str(r.get('unidad', ''))[:15]
        categoria_val = str(r.get('categoria', 'NULL'))[:30]
        print(f"{id_val:<6} {nombre_val:<50} {tipo_val:<6} {unidad_val:<15} {categoria_val:<30}")
    
    print()
    print("="*80)
    print()
    
    # Resumen por categoría
    categorias_unicas = {}
    for r in results:
        cat = r.get('categoria', 'NULL')
        categorias_unicas[cat] = categorias_unicas.get(cat, 0) + 1
    
    print("RESUMEN POR CATEGORÍA:")
    for cat, count in sorted(categorias_unicas.items()):
        print(f"  '{cat}': {count} productos")
    
    print()
    print("="*80)
    print()
    
    # Resumen por tipo
    tipos_unicos = {}
    for r in results:
        tipo = r.get('tipo', 'NULL')
        tipos_unicos[tipo] = tipos_unicos.get(tipo, 0) + 1
    
    print("RESUMEN POR TIPO:")
    for tipo, count in sorted(tipos_unicos.items(), key=lambda x: (x[0] is None, str(x[0]) if x[0] is not None else '')):
        tipo_str = str(tipo) if tipo is not None else 'None'
        print(f"  '{tipo_str}': {count} productos")
    
    print()
    print("="*80)
    print()
    
    # Verificar productos internos (Uruguay + Precios)
    internos = [r for r in results if r.get('pais') == 'Uruguay' and r.get('categoria') == 'Precios']
    print(f"PRODUCTOS INTERNOS (pais='Uruguay' AND categoria='Precios'): {len(internos)}")
    if len(internos) > 0:
        for r in internos:
            print(f"  ID {r.get('id')}: {r.get('nombre')[:60]} (pais: {r.get('pais')}, categoria: {r.get('categoria')}, tipo: {r.get('tipo')})")
    else:
        print("  No se encontraron productos internos con esta condición")
        print()
        print("  Verificando productos con categoria='Precios':")
        precios = [r for r in results if r.get('categoria') == 'Precios']
        for r in precios:
            print(f"    ID {r.get('id')}: {r.get('nombre')[:60]} (pais: {r.get('pais')}, tipo: {r.get('tipo')})")
    
    print()
    print("="*80)
    print()
    
    # Verificar productos que cumplen tipo IN ('P', 'S')
    productos_servicios = [r for r in results if r.get('tipo') in ('P', 'S')]
    print(f"PRODUCTOS Y SERVICIOS (tipo IN ('P', 'S')): {len(productos_servicios)}")
    
    print()
    print("="*80)
    print()
    
    # Verificar si hay productos que NO cumplen ninguna condición
    print("VERIFICACIÓN DE CONDICIONES:")
    print(f"  Total resultados: {len(results)}")
    print(f"  Productos/Servicios (tipo P/S): {len(productos_servicios)}")
    print(f"  Internos (Uruguay + Precios): {len(internos)}")
    print(f"  Suma: {len(productos_servicios) + len(internos)}")
    
    # Productos que cumplen ambas condiciones
    ambos = [r for r in results if r.get('tipo') in ('P', 'S') and r.get('pais') == 'Uruguay' and r.get('categoria') == 'Precios']
    print(f"  Que cumplen AMBAS condiciones: {len(ambos)}")
    
    print()
    print("="*80)
    print()
    
    # Mostrar algunos ejemplos de cada tipo
    print("EJEMPLOS:")
    print()
    
    # Ejemplo de producto (tipo P)
    productos_p = [r for r in results if r.get('tipo') == 'P']
    if len(productos_p) > 0:
        print(f"Producto (tipo P) - ejemplo:")
        r = productos_p[0]
        print(f"  ID: {r.get('id')}, Nombre: {r.get('nombre')}, Categoria: {r.get('categoria')}, Pais: {r.get('pais')}")
    
    # Ejemplo de servicio (tipo S)
    servicios_s = [r for r in results if r.get('tipo') == 'S']
    if len(servicios_s) > 0:
        print(f"Servicio (tipo S) - ejemplo:")
        r = servicios_s[0]
        print(f"  ID: {r.get('id')}, Nombre: {r.get('nombre')}, Categoria: {r.get('categoria')}, Pais: {r.get('pais')}")
    
    # Ejemplo de interno
    if len(internos) > 0:
        print(f"Interno (Uruguay + Precios) - ejemplo:")
        r = internos[0]
        print(f"  ID: {r.get('id')}, Nombre: {r.get('nombre')}, Tipo: {r.get('tipo')}, Categoria: {r.get('categoria')}, Pais: {r.get('pais')}")
    
else:
    print("NO SE ENCONTRARON PRODUCTOS")
    print()
    print("Verificando qué productos activos hay en total...")
    query_todos = """
        SELECT id, nombre, tipo, categoria, pais, activo
        FROM maestro
        WHERE activo = 1
        ORDER BY tipo, nombre
        LIMIT 20
    """
    todos = execute_query(query_todos)
    print(f"Total productos activos: {len(todos)}")
    print("Primeros 20 productos activos:")
    for r in todos:
        print(f"  ID {r.get('id')}: {r.get('nombre')[:50]} (tipo: {r.get('tipo')}, categoria: {r.get('categoria')}, pais: {r.get('pais')})")

print()
print("="*80)
print("FIN DEL REPORTE")
print("="*80)
