"""
Script para verificar cómo se llama la columna categoria en la tabla maestro
"""
import sys
sys.path.insert(0, 'backend')

from app.database import execute_query
import sqlite3

print("="*80)
print("VERIFICACION DE COLUMNA CATEGORIA EN TABLA maestro")
print("="*80)
print()

# Conectar directamente para ver estructura
conn = sqlite3.connect('series_tiempo.db')
cursor = conn.cursor()

# Obtener estructura de la tabla
cursor.execute("PRAGMA table_info(maestro)")
columns = cursor.fetchall()

print("ESTRUCTURA DE LA TABLA maestro:")
print(f"{'Nombre':<20} {'Tipo':<15} {'Not Null':<10} {'Default':<10} {'PK':<5}")
print("-" * 80)
for col in columns:
    cid, name, col_type, not_null, default, pk = col
    print(f"{name:<20} {col_type:<15} {bool(not_null):<10} {str(default):<10} {bool(pk):<5}")

print()
print("="*80)
print()

# Buscar columnas que contengan "categoria" o "categoria" (case insensitive)
print("COLUMNAS RELACIONADAS CON 'categoria':")
categoria_cols = [col[1] for col in columns if 'categoria' in col[1].lower() or 'categoria' in col[1].lower()]
if categoria_cols:
    for col_name in categoria_cols:
        print(f"  - {col_name}")
else:
    print("  No se encontraron columnas con 'categoria'")

print()
print("="*80)
print()

# Ver algunos valores de la columna categoria (si existe)
if 'categoria' in [col[1] for col in columns]:
    print("VALORES UNICOS EN COLUMNA 'categoria':")
    cursor.execute("SELECT DISTINCT categoria FROM maestro WHERE categoria IS NOT NULL ORDER BY categoria")
    valores = cursor.fetchall()
    for val in valores:
        print(f"  - '{val[0]}'")
    
    print()
    print("CONTEO POR CATEGORIA:")
    cursor.execute("SELECT categoria, COUNT(*) as count FROM maestro WHERE categoria IS NOT NULL GROUP BY categoria ORDER BY categoria")
    conteos = cursor.fetchall()
    for cat, count in conteos:
        print(f"  '{cat}': {count} registros")

conn.close()

print()
print("="*80)
print("FIN")
print("="*80)
