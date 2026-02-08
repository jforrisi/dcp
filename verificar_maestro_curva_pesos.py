"""Script rápido para verificar los registros creados en maestro"""

import sqlite3

conn = sqlite3.connect('series_tiempo.db')
cursor = conn.cursor()

cursor.execute("""
    SELECT m.id, m.nombre, m.id_variable, m.id_pais, m.fuente, m.periodicidad, m.tipo, m.activo, 
           v.id_nombre_variable
    FROM maestro m
    LEFT JOIN variables v ON m.id_variable = v.id_variable
    WHERE m.id_variable BETWEEN 37 AND 51 AND m.id_pais = 858
    ORDER BY m.id_variable
""")

rows = cursor.fetchall()

print("=" * 100)
print("REGISTROS EN MAESTRO - CURVA DE PESOS (Uruguay)")
print("=" * 100)
print(f"{'ID':<5} {'Nombre':<15} {'id_var':<8} {'id_pais':<8} {'Fuente':<10} {'Period':<8} {'Tipo':<5} {'Activo':<7} {'Variable'}")
print("-" * 100)

for r in rows:
    print(f"{r[0]:<5} {str(r[1]):<15} {r[2]:<8} {r[3]:<8} {str(r[4]):<10} {str(r[5]):<8} {str(r[6]):<5} {r[7]:<7} {r[8]}")

print("-" * 100)
print(f"Total: {len(rows)} registros")
print("=" * 100)

conn.close()
