"""
Probar el endpoint de inflacion dolares con la query corregida
"""
import sys
sys.path.insert(0, 'backend')

from app.database import execute_query, execute_query_single

print("="*80)
print("PRUEBA ENDPOINT INFLACION DOLARES (QUERY CORREGIDA)")
print("="*80)
print()

# 1. Obtener cotizaciones
print("1. COTIZACIONES:")
query_cot = """
    SELECT id, nombre, pais, fuente, unidad
    FROM maestro
    WHERE es_cotizacion = 1
    AND periodicidad = 'D'
    AND (activo = 1 OR CAST(activo AS INTEGER) = 1)
    AND pais IS NOT NULL
    ORDER BY pais, nombre
"""
cotizaciones = execute_query(query_cot)
print(f"Total: {len(cotizaciones)}")
for cot in cotizaciones[:5]:
    print(f"  ID {cot.get('id')}: {cot.get('nombre')[:40]} - pais: '{cot.get('pais')}'")

print()
print("="*80)
print()

# 2. Para cada cotización, verificar si tiene IPC (con query corregida)
print("2. VERIFICANDO IPC PARA CADA COTIZACION:")
results = []
for cot in cotizaciones:
    pais = cot.get('pais', '')
    if not pais:
        continue
    
    # Query corregida (sin filtro de tipo)
    query_ipc = """
        SELECT COUNT(*) as count
        FROM maestro ipc
        WHERE ipc.periodicidad = 'M'
        AND (
            ipc.nombre LIKE '%IPC%' OR ipc.nombre LIKE '%índice de precios%' OR ipc.nombre LIKE '%indice de precios%'
            OR ipc.categoria LIKE '%IPC%' OR ipc.categoria LIKE '%inflación%' OR ipc.categoria LIKE '%inflacion%'
        )
        AND (ipc.pais = ? OR ipc.pais LIKE '%' || ? || '%')
        AND (ipc.activo = 1 OR CAST(ipc.activo AS INTEGER) = 1)
    """
    ipc_result = execute_query_single(query_ipc, (pais, pais))
    
    # También buscar IPC exacto
    query_ipc_exact = """
        SELECT id, nombre, pais
        FROM maestro ipc
        WHERE ipc.periodicidad = 'M'
        AND (
            ipc.nombre LIKE '%IPC%' OR ipc.nombre LIKE '%índice de precios%' OR ipc.nombre LIKE '%indice de precios%'
        )
        AND (ipc.pais = ? OR ipc.pais LIKE '%' || ? || '%')
        AND (ipc.activo = 1 OR CAST(ipc.activo AS INTEGER) = 1)
        LIMIT 1
    """
    ipc_exact = execute_query_single(query_ipc_exact, (pais, pais))
    
    if ipc_result and ipc_result.get('count', 0) > 0:
        results.append(cot)
        print(f"  [OK] {pais}: Tiene IPC (ID {ipc_exact.get('id') if ipc_exact else 'N/A'})")
    else:
        print(f"  [NO] {pais}: NO tiene IPC")

print()
print("="*80)
print()
print(f"3. PAISES CON COTIZACION E IPC: {len(results)}")
for r in results:
    print(f"  - {r.get('pais')} (ID {r.get('id')})")

print()
print("="*80)
print()

# 4. Verificar coincidencia de nombres de países
print("4. VERIFICANDO COINCIDENCIA DE NOMBRES:")
print("Cotizaciones con nombres especiales:")
for cot in cotizaciones:
    pais_cot = cot.get('pais', '')
    if '(' in pais_cot or 'oficial' in pais_cot.lower() or 'ccl' in pais_cot.lower():
        # Extraer el país base
        pais_base = pais_cot.split('(')[0].strip()
        print(f"  '{pais_cot}' -> país base: '{pais_base}'")
        
        # Buscar IPC con país base
        query_ipc_base = """
            SELECT id, nombre, pais
            FROM maestro ipc
            WHERE ipc.periodicidad = 'M'
            AND ipc.nombre LIKE '%IPC%'
            AND (ipc.pais = ? OR ipc.pais LIKE ?)
            AND (ipc.activo = 1 OR CAST(ipc.activo AS INTEGER) = 1)
            LIMIT 1
        """
        ipc_base = execute_query_single(query_ipc_base, (pais_base, f'%{pais_base}%'))
        if ipc_base:
            print(f"    -> Encontrado IPC: ID {ipc_base.get('id')}, pais: '{ipc_base.get('pais')}'")

print()
print("="*80)
print("FIN")
print("="*80)
