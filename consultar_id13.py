import sqlite3

conn = sqlite3.connect('series_tiempo.db')
cursor = conn.cursor()

# Información del maestro
cursor.execute('SELECT id, nombre, tipo, fuente, periodicidad, unidad, categoria FROM maestro WHERE id = 13')
row = cursor.fetchone()
print('INFORMACION DEL PRODUCTO ID 13:')
print('=' * 60)
print(f'ID: {row[0]}')
print(f'Nombre: {row[1]}')
print(f'Tipo: {row[2]} (S = Servicio)')
print(f'Fuente: {row[3]}')
print(f'Periodicidad: {row[4]} (M = Mensual)')
print(f'Unidad: {row[5]}')
print(f'Categoria: {row[6]}')
print()

# Datos de precios
cursor.execute('SELECT fecha, valor FROM maestro_precios WHERE maestro_id = 13 ORDER BY fecha')
rows = cursor.fetchall()
print(f'DATOS DE PRECIOS:')
print('=' * 60)
print(f'Total de registros: {len(rows)}')
print()
print('Primeros 5 registros:')
for r in rows[:5]:
    print(f'  {r[0]}: {r[1]:.2f}')
print()
print('Ultimos 5 registros:')
for r in rows[-5:]:
    print(f'  {r[0]}: {r[1]:.2f}')

conn.close()
