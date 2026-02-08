import sqlite3

conn = sqlite3.connect('series_tiempo.db')
cursor = conn.cursor()

print("=== COTIZACIONES ===")
cursor.execute("""
    SELECT id, nombre, pais, tipo, periodicidad, es_cotizacion, activo 
    FROM maestro 
    WHERE tipo='M' AND periodicidad='D' AND es_cotizacion=1
    LIMIT 20
""")
for row in cursor.fetchall():
    print(row)

print("\n=== IPC MENSUAL ===")
cursor.execute("""
    SELECT id, nombre, pais, tipo, periodicidad, categoria
    FROM maestro 
    WHERE tipo='M' AND periodicidad='M' 
    AND (nombre LIKE '%IPC%' OR categoria LIKE '%IPC%')
    LIMIT 20
""")
for row in cursor.fetchall():
    print(row)

print("\n=== QUERY COMPLETA ===")
cursor.execute("""
    SELECT DISTINCT m.id, m.nombre, m.pais, m.fuente, m.unidad
    FROM maestro m
    WHERE m.tipo = 'M' 
    AND m.periodicidad = 'D'
    AND m.es_cotizacion = 1
    AND (m.activo = 1 OR CAST(m.activo AS INTEGER) = 1)
    AND m.pais IS NOT NULL
    AND m.pais IN ('Uruguay', 'Perú', 'Brasil', 'México', 'Chile')
    AND EXISTS (
        SELECT 1 
        FROM maestro ipc
        WHERE ipc.tipo = 'M'
        AND ipc.periodicidad = 'M'
        AND (
            ipc.nombre LIKE '%IPC%' OR ipc.nombre LIKE '%índice de precios%' OR ipc.nombre LIKE '%indice de precios%'
            OR ipc.categoria LIKE '%IPC%' OR ipc.categoria LIKE '%inflación%' OR ipc.categoria LIKE '%inflacion%'
        )
        AND (ipc.pais = m.pais OR ipc.pais LIKE '%' || m.pais || '%')
        AND (ipc.activo = 1 OR CAST(ipc.activo AS INTEGER) = 1)
    )
    ORDER BY m.pais, m.nombre
""")
results = cursor.fetchall()
print(f"Resultados: {len(results)}")
for row in results:
    print(row)

conn.close()
