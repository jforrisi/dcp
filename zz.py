import sqlite3

conn = sqlite3.connect("series_tiempo.db")
cur = conn.cursor()

cur.execute("""
    SELECT id, nombre, moneda, nominal_real
    FROM maestro
    WHERE tipo IN ('P','S')
      AND activo = 1
      AND (nominal_real IS NULL OR LOWER(nominal_real) <> 'n')
    ORDER BY id
""")

for row in cur.fetchall():
    print(row)

conn.close()