import sqlite3

DB_PATH = "series_tiempo.db"

conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()

# 1) Poner TODOS los productos / servicios de exportación como nominales ('n')
cur.execute("""
    UPDATE maestro
    SET nominal_real = 'n'
    WHERE tipo IN ('P','S') AND activo = 1
""")

# 2) Asegurar que Salario real (id 19) quede como 'r'
cur.execute("""
    UPDATE maestro
    SET nominal_real = 'r'
    WHERE id = 19
""")

conn.commit()

# 3) Verificar (opcional: imprime el rango 1–20)
cur.execute("""
    SELECT id, nombre, moneda, nominal_real
    FROM maestro
    WHERE id BETWEEN 1 AND 20
    ORDER BY id
""")
for row in cur.fetchall():
    print(row)

conn.close()
print("Listo: nominal_real actualizado.")