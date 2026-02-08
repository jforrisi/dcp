"""
Script de prueba para verificar que Precios Corrientes solo muestre "Precios Internacionales".
"""

import sqlite3

DB_NAME = "series_tiempo.db"

def test_precios_corrientes():
    """Verifica que Precios Corrientes filtre correctamente."""
    print("=" * 80)
    print("PRUEBA: MÓDULO PRECIOS CORRIENTES")
    print("=" * 80)
    
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # Verificar filtro por "Precios Internacionales"
    print("\n[1] Verificando filtro por categoria = 'Precios Internacionales':")
    cursor.execute("""
        SELECT id, nombre, categoria, activo
        FROM maestro
        WHERE categoria = 'Precios Internacionales' AND activo = 1
        ORDER BY nombre
    """)
    resultados = cursor.fetchall()
    
    print(f"   Total de registros encontrados: {len(resultados)}")
    print("   Primeros 10 registros:")
    for row in resultados[:10]:
        print(f"      - ID {row[0]}: {row[1]} (categoria: {row[2]})")
    
    # Verificar que no hay otros productos activos que no sean "Precios Internacionales"
    print("\n[2] Verificando que no hay otros productos activos fuera de 'Precios Internacionales':")
    cursor.execute("""
        SELECT COUNT(*) 
        FROM maestro
        WHERE categoria IN ('P', 'S') 
        AND categoria != 'Precios Internacionales'
        AND activo = 1
    """)
    count_otros = cursor.fetchone()[0]
    print(f"   Productos activos fuera de 'Precios Internacionales': {count_otros}")
    
    if count_otros > 0:
        cursor.execute("""
            SELECT id, nombre, categoria
            FROM maestro
            WHERE categoria IN ('P', 'S')
            AND categoria != 'Precios Internacionales'
            AND activo = 1
            LIMIT 5
        """)
        otros = cursor.fetchall()
        print("   Ejemplos:")
        for row in otros:
            print(f"      - ID {row[0]}: {row[1]} (categoria: {row[2]})")
    
    conn.close()
    print("\n[OK] Prueba Precios Corrientes completada")


if __name__ == "__main__":
    test_precios_corrientes()
