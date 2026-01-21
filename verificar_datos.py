import sqlite3
from pathlib import Path

conn = sqlite3.connect('series_tiempo.db')
cursor = conn.cursor()

cursor.execute('SELECT COUNT(*) FROM maestro_precios')
count = cursor.fetchone()[0]

cursor.execute('SELECT COUNT(*) FROM maestro')
count_maestro = cursor.fetchone()[0]

print(f'Registros en maestro_precios: {count}')
print(f'Registros en maestro: {count_maestro}')

cursor.execute('SELECT maestro_id, COUNT(*) as cnt FROM maestro_precios GROUP BY maestro_id ORDER BY maestro_id')
print('\nRegistros por producto:')
for row in cursor.fetchall():
    print(f'  ID {row[0]}: {row[1]} registros')

conn.close()
