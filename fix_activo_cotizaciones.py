"""Script para corregir el campo activo de Argentina y Brasil."""
import sqlite3

conn = sqlite3.connect('series_tiempo.db')
cursor = conn.cursor()

# Actualizar activo para Argentina (ID 22) y Brasil (ID 23)
cursor.execute("UPDATE maestro SET activo = 1 WHERE id = 22")
cursor.execute("UPDATE maestro SET activo = 1 WHERE id = 23")

conn.commit()

# Verificar los cambios
cursor.execute("SELECT id, nombre, activo FROM maestro WHERE id IN (22, 23)")
rows = cursor.fetchall()

print("Valores actualizados:")
for row in rows:
    print(f"ID {row[0]}: {row[1]} - activo = {row[2]}")

conn.close()
print("\n✓ Actualización completada")
