"""Actualizar tabla maestro desde Excel maestro_completo.xlsx"""
import sqlite3
import pandas as pd
from pathlib import Path

EXCEL_FILE = "maestro_completo.xlsx"
DB_NAME = "series_tiempo.db"

print("=" * 80)
print("ACTUALIZACIÓN DE MAESTRO DESDE EXCEL")
print("=" * 80)

# Verificar que existe el Excel
if not Path(EXCEL_FILE).exists():
    print(f"\n❌ Error: No se encuentra el archivo {EXCEL_FILE}")
    exit(1)

# Leer Excel
print(f"\n[INFO] Leyendo {EXCEL_FILE}...")
df = pd.read_excel(EXCEL_FILE, sheet_name='maestro')

print(f"✓ Leídos {len(df)} registros")
print(f"Columnas: {list(df.columns)}")

# Conectar a la base de datos
conn = sqlite3.connect(DB_NAME)
cursor = conn.cursor()

# Verificar estructura de la tabla
cursor.execute("PRAGMA table_info(maestro)")
columns_info = cursor.fetchall()
existing_columns = [col[1] for col in columns_info]
print(f"\nColumnas en la tabla maestro: {existing_columns}")

# Asegurar que existe la columna es_cotizacion
if 'es_cotizacion' not in existing_columns:
    print("\n[INFO] Agregando columna es_cotizacion...")
    try:
        cursor.execute("ALTER TABLE maestro ADD COLUMN es_cotizacion INTEGER DEFAULT 0")
        conn.commit()
        print("✓ Columna es_cotizacion agregada")
    except sqlite3.OperationalError as e:
        if "duplicate column" not in str(e).lower():
            raise

# Normalizar valores de activo y es_cotizacion
def normalize_bool(value):
    """Convierte diferentes formatos de boolean a 1 o 0"""
    if pd.isna(value):
        return 0
    if isinstance(value, bool):
        return 1 if value else 0
    if isinstance(value, (int, float)):
        return 1 if value == 1 or value == True else 0
    if isinstance(value, str):
        if value.lower() in ['true', '1', 'yes', 'si', 'sí']:
            return 1
        return 0
    return 0

# Preparar datos para actualización
print("\n[INFO] Preparando datos...")
updated_count = 0
inserted_count = 0

for idx, row in df.iterrows():
    # Obtener valores, manejando NaN
    id_val = int(row['id']) if pd.notna(row['id']) else None
    if id_val is None:
        print(f"⚠ Fila {idx+1}: ID nulo, saltando...")
        continue
    
    nombre = str(row['nombre']) if pd.notna(row['nombre']) else ''
    tipo = str(row['tipo']) if pd.notna(row['tipo']) else 'P'
    fuente = str(row['fuente']) if pd.notna(row['fuente']) else ''
    periodicidad = str(row['periodicidad']) if pd.notna(row['periodicidad']) else 'M'
    unidad = str(row['unidad']) if pd.notna(row['unidad']) else None
    categoria = str(row['categoria']) if pd.notna(row['categoria']) else None
    activo = normalize_bool(row.get('activo', 1))
    moneda = str(row['moneda']).lower() if pd.notna(row.get('moneda')) else None
    nominal_real = str(row['nominal_real']) if pd.notna(row.get('nominal_real')) else None
    es_cotizacion = normalize_bool(row.get('es_cotizacion', 0))
    
    # Verificar si existe
    cursor.execute("SELECT id FROM maestro WHERE id = ?", (id_val,))
    exists = cursor.fetchone()
    
    if exists:
        # Actualizar
        update_query = """
            UPDATE maestro 
            SET nombre = ?, tipo = ?, fuente = ?, periodicidad = ?, 
                unidad = ?, categoria = ?, activo = ?, 
                moneda = ?, nominal_real = ?, es_cotizacion = ?
            WHERE id = ?
        """
        cursor.execute(update_query, (
            nombre, tipo, fuente, periodicidad, unidad, categoria, 
            activo, moneda, nominal_real, es_cotizacion, id_val
        ))
        updated_count += 1
    else:
        # Insertar
        insert_query = """
            INSERT INTO maestro 
            (id, nombre, tipo, fuente, periodicidad, unidad, categoria, activo, moneda, nominal_real, es_cotizacion)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        cursor.execute(insert_query, (
            id_val, nombre, tipo, fuente, periodicidad, unidad, categoria,
            activo, moneda, nominal_real, es_cotizacion
        ))
        inserted_count += 1

conn.commit()

print(f"\n✓ Actualizados: {updated_count} registros")
print(f"✓ Insertados: {inserted_count} registros")

# Verificar cotizaciones
print("\n" + "=" * 80)
print("VERIFICACIÓN DE COTIZACIONES")
print("=" * 80)

cursor.execute("""
    SELECT id, nombre, tipo, periodicidad, activo, es_cotizacion
    FROM maestro
    WHERE es_cotizacion = 1
    ORDER BY id
""")

cotizaciones = cursor.fetchall()
print(f"\nCotizaciones encontradas: {len(cotizaciones)}")
for row in cotizaciones:
    print(f"  ID {row[0]}: {row[1][:50]}... | tipo={row[2]} | periodicidad={row[3]} | activo={row[4]} | es_cotizacion={row[5]}")

# Verificar que cumplen los criterios del endpoint
print("\n" + "=" * 80)
print("COTIZACIONES QUE CUMPLEN CRITERIOS DEL ENDPOINT")
print("=" * 80)
print("(tipo='M' AND periodicidad='D' AND es_cotizacion=1 AND activo=1)")

cursor.execute("""
    SELECT id, nombre, tipo, periodicidad, activo, es_cotizacion
    FROM maestro
    WHERE tipo = 'M' 
    AND periodicidad = 'D'
    AND es_cotizacion = 1
    AND (activo = 1 OR CAST(activo AS INTEGER) = 1)
    ORDER BY nombre
""")

valid_cotizaciones = cursor.fetchall()
print(f"\nTotal: {len(valid_cotizaciones)}")
for row in valid_cotizaciones:
    print(f"  ID {row[0]}: {row[1][:60]}...")

conn.close()

print("\n" + "=" * 80)
print("ACTUALIZACIÓN COMPLETA")
print("=" * 80)
print("\n✓ Reinicia el servidor para aplicar los cambios:")
print("  python backend/run.py")
