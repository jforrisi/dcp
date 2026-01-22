"""Asegurar que Perú (ID 24) tenga activo = 1."""
import sqlite3

conn = sqlite3.connect('series_tiempo.db')
cursor = conn.cursor()

print("=" * 80)
print("FIX: PERÚ (ID 24) - activo = 1")
print("=" * 80)

# Verificar estado actual
cursor.execute("SELECT id, nombre, activo FROM maestro WHERE id = 24")
row = cursor.fetchone()

if row:
    print(f"\nEstado actual:")
    print(f"  ID: {row[0]}")
    print(f"  Nombre: {row[1]}")
    print(f"  activo: {row[2]} (tipo: {type(row[2]).__name__})")
    
    # Actualizar a 1
    cursor.execute("UPDATE maestro SET activo = 1 WHERE id = 24")
    conn.commit()
    
    # Verificar
    cursor.execute("SELECT id, nombre, activo FROM maestro WHERE id = 24")
    row_after = cursor.fetchone()
    print(f"\nDespués de actualizar:")
    print(f"  activo: {row_after[2]} (tipo: {type(row_after[2]).__name__})")
    print(f"\n✓ Perú (ID 24) actualizado a activo = 1")
else:
    print("\n❌ ID 24 no encontrado en maestro")

conn.close()
print("\n" + "=" * 80)
