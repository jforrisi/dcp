"""
Buscar IPC de forma alternativa
"""
import sys
sys.path.insert(0, 'backend')

from app.database import execute_query

print("="*80)
print("BUSCANDO IPC DE FORMA ALTERNATIVA")
print("="*80)
print()

# Buscar cualquier producto que contenga IPC en el nombre
print("1. PRODUCTOS QUE CONTIENEN 'IPC' EN EL NOMBRE:")
query1 = """
    SELECT id, nombre, pais, tipo, categoria, periodicidad, activo
    FROM maestro
    WHERE nombre LIKE '%IPC%' OR nombre LIKE '%índice de precios%' OR nombre LIKE '%indice de precios%'
    ORDER BY nombre
"""
ipc_nombre = execute_query(query1)
print(f"Total: {len(ipc_nombre)}")
for p in ipc_nombre:
    print(f"  ID {p.get('id')}: {p.get('nombre')[:60]} - pais: {p.get('pais')}, tipo: {p.get('tipo')}, categoria: {p.get('categoria')}, periodicidad: {p.get('periodicidad')}")

print()
print("="*80)
print()

# Buscar por categoria
print("2. PRODUCTOS QUE CONTIENEN 'IPC' EN CATEGORIA:")
query2 = """
    SELECT id, nombre, pais, tipo, categoria, periodicidad, activo
    FROM maestro
    WHERE categoria LIKE '%IPC%' OR categoria LIKE '%inflación%' OR categoria LIKE '%inflacion%'
    ORDER BY nombre
"""
ipc_cat = execute_query(query2)
print(f"Total: {len(ipc_cat)}")
for p in ipc_cat:
    print(f"  ID {p.get('id')}: {p.get('nombre')[:60]} - pais: {p.get('pais')}, tipo: {p.get('tipo')}, categoria: {p.get('categoria')}, periodicidad: {p.get('periodicidad')}")

print()
print("="*80)
print()

# Ver todos los productos con periodicidad = 'M'
print("3. TODOS LOS PRODUCTOS CON periodicidad = 'M':")
query3 = """
    SELECT id, nombre, pais, tipo, categoria, periodicidad, activo
    FROM maestro
    WHERE periodicidad = 'M'
    AND (activo = 1 OR CAST(activo AS INTEGER) = 1)
    ORDER BY nombre
"""
periodicidad_m = execute_query(query3)
print(f"Total: {len(periodicidad_m)}")
for p in periodicidad_m:
    print(f"  ID {p.get('id')}: {p.get('nombre')[:60]} - pais: {p.get('pais')}, tipo: {p.get('tipo')}, categoria: {p.get('categoria')}")

print()
print("="*80)
print()

# Ver todos los productos activos
print("4. TODOS LOS PRODUCTOS ACTIVOS (primeros 20):")
query4 = """
    SELECT id, nombre, pais, tipo, categoria, periodicidad, activo
    FROM maestro
    WHERE activo = 1 OR CAST(activo AS INTEGER) = 1
    ORDER BY id
    LIMIT 20
"""
todos = execute_query(query4)
print(f"Total (mostrando primeros 20): {len(todos)}")
for p in todos:
    print(f"  ID {p.get('id')}: {p.get('nombre')[:60]} - pais: {p.get('pais')}, tipo: {p.get('tipo')}, categoria: {p.get('categoria')}, periodicidad: {p.get('periodicidad')}")

print()
print("="*80)
print("FIN")
print("="*80)
