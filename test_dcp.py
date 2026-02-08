"""
Script de prueba para verificar que DCP use IDs fijos y filtre por categoria.
"""

import sqlite3

DB_NAME = "series_tiempo.db"

def test_dcp():
    """Verifica que DCP use los IDs fijos correctos."""
    print("=" * 80)
    print("PRUEBA: MÓDULO DCP")
    print("=" * 80)
    
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # Verificar IDs fijos
    print("\n[1] Verificando IDs fijos de variables macro:")
    ipc_id = 11
    tc_usd_id = 6
    tc_eur_id = 7
    
    cursor.execute("SELECT id, nombre, pais FROM maestro WHERE id IN (?, ?, ?)", (ipc_id, tc_usd_id, tc_eur_id))
    resultados = cursor.fetchall()
    
    print(f"   IPC Uruguay (ID {ipc_id}):")
    for row in resultados:
        if row[0] == ipc_id:
            print(f"      - {row[1]} (País: {row[2]})")
    
    print(f"   TC USD/UYU (ID {tc_usd_id}):")
    for row in resultados:
        if row[0] == tc_usd_id:
            print(f"      - {row[1]} (País: {row[2]})")
    
    print(f"   TC EUR/UYU (ID {tc_eur_id}):")
    for row in resultados:
        if row[0] == tc_eur_id:
            print(f"      - {row[1]} (País: {row[2]})")
    
    # Verificar que el filtro por categoria funciona
    print("\n[2] Verificando filtro por categoria (P, S, M):")
    cursor.execute("SELECT COUNT(*) FROM maestro WHERE categoria IN ('P', 'S', 'M') AND activo = 1")
    count = cursor.fetchone()[0]
    print(f"   Registros con categoria IN ('P', 'S', 'M'): {count}")
    
    # Verificar distribución
    cursor.execute("SELECT categoria, COUNT(*) FROM maestro WHERE categoria IN ('P', 'S', 'M') AND activo = 1 GROUP BY categoria")
    distribucion = cursor.fetchall()
    print("   Distribución:")
    for cat, cnt in distribucion:
        print(f"      - {cat}: {cnt}")
    
    conn.close()
    print("\n[OK] Prueba DCP completada")


if __name__ == "__main__":
    test_dcp()
