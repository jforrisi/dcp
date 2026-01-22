query = """
    SELECT id, nombre, fuente, unidad, categoria, periodicidad
    FROM maestro
    WHERE tipo = 'M' 
    AND periodicidad = 'D'
    AND (
        id IN (6, 22, 23, 24, 25)
        OR (
            (categoria LIKE '%Tipo de cambio%' OR categoria LIKE '%tipo de cambio%')
            AND (activo = 1 OR CAST(activo AS INTEGER) = 1)
        )
    )
    ORDER BY nombre
"""