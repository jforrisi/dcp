"""
Script de prueba para verificar que Cotizaciones filtre por nombre USD/LC.
"""

import sqlite3

DB_NAME = "series_tiempo.db"

def test_cotizaciones():
    """Verifica que Cotizaciones filtre correctamente por nombre."""
    print("=" * 80)
    print("PRUEBA: MÓDULO COTIZACIONES")
    print("=" * 80)
    
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # Verificar filtro por nombre LIKE '%USD/LC%'
    print("\n[1] Verificando filtro por nombre LIKE '%USD/LC%':")
    cursor.execute("""
        SELECT id, nombre, pais, periodicidad, activo
        FROM maestro
        WHERE nombre LIKE '%USD/LC%'
        AND periodicidad = 'D'
        AND (activo = 1 OR CAST(activo AS INTEGER) = 1)
        ORDER BY nombre
    """)
    resultados = cursor.fetchall()
    
    print(f"   Total de cotizaciones encontradas: {len(resultados)}")
    print("   Cotizaciones:")
    for row in resultados:
        print(f"      - ID {row[0]}: {row[1]} (País: {row[2]}, Periodicidad: {row[3]})")
    
    # Verificar que no se usan registros con es_cotizacion=1 que no tengan USD/LC
    print("\n[2] Verificando que no hay registros con es_cotizacion=1 sin USD/LC en nombre:")
    cursor.execute("""
        SELECT COUNT(*)
        FROM maestro
        WHERE es_cotizacion = 1
        AND nombre NOT LIKE '%USD/LC%'
        AND activo = 1
    """)
    count_sin_usd_lc = cursor.fetchone()[0]
    print(f"   Registros con es_cotizacion=1 pero sin 'USD/LC' en nombre: {count_sin_usd_lc}")
    
    if count_sin_usd_lc > 0:
        cursor.execute("""
            SELECT id, nombre, es_cotizacion
            FROM maestro
            WHERE es_cotizacion = 1
            AND nombre NOT LIKE '%USD/LC%'
            AND activo = 1
        """)
        otros = cursor.fetchall()
        print("   Ejemplos:")
        for row in otros:
            print(f"      - ID {row[0]}: {row[1]} (es_cotizacion: {row[2]})")
    
    conn.close()
    print("\n[OK] Prueba Cotizaciones completada")


if __name__ == "__main__":
    test_cotizaciones()
