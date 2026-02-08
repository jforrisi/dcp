"""Verificar el nombre exacto de la columna pais/region."""
import sqlite3

conn = sqlite3.connect('series_tiempo.db')
cursor = conn.cursor()

print("=" * 80)
print("VERIFICACIÓN DE COLUMNA PAIS/REGION")
print("=" * 80)

# Obtener información de las columnas de la tabla maestro
cursor.execute("PRAGMA table_info(maestro)")
columns = cursor.fetchall()

print("\nColumnas en la tabla maestro:")
print("-" * 80)
for col in columns:
    print(f"  {col[1]} (tipo: {col[2]})")

# Buscar columnas que contengan 'pais' o 'region'
print("\nColumnas que contienen 'pais' o 'region':")
print("-" * 80)
for col in columns:
    if 'pais' in col[1].lower() or 'region' in col[1].lower():
        print(f"  ✓ {col[1]} (tipo: {col[2]})")

# Probar diferentes sintaxis para acceder a la columna
print("\nProbando diferentes sintaxis:")
print("-" * 80)

# Probar 1: Sin comillas
try:
    cursor.execute("SELECT COUNT(*) FROM maestro WHERE pais IS NOT NULL")
    count = cursor.fetchone()[0]
    print(f"  ✓ 'pais' (sin comillas): {count} registros")
except Exception as e:
    print(f"  ❌ 'pais' (sin comillas): {str(e)[:50]}")

# Probar 2: Con comillas dobles
try:
    cursor.execute('SELECT COUNT(*) FROM maestro WHERE "pais/region" IS NOT NULL')
    count = cursor.fetchone()[0]
    print(f"  ✓ '\"pais/region\"' (comillas dobles): {count} registros")
except Exception as e:
    print(f"  ❌ '\"pais/region\"' (comillas dobles): {str(e)[:50]}")

# Probar 3: Con corchetes
try:
    cursor.execute("SELECT COUNT(*) FROM maestro WHERE [pais/region] IS NOT NULL")
    count = cursor.fetchone()[0]
    print(f"  ✓ '[pais/region]' (corchetes): {count} registros")
except Exception as e:
    print(f"  ❌ '[pais/region]' (corchetes): {str(e)[:50]}")

# Probar 4: Con backticks
try:
    cursor.execute("SELECT COUNT(*) FROM maestro WHERE `pais/region` IS NOT NULL")
    count = cursor.fetchone()[0]
    print(f"  ✓ '`pais/region`' (backticks): {count} registros")
except Exception as e:
    print(f"  ❌ '`pais/region`' (backticks): {str(e)[:50]}")

# Mostrar algunos valores únicos
print("\nValores únicos en la columna:")
print("-" * 80)
try:
    cursor.execute('SELECT DISTINCT "pais/region" FROM maestro WHERE "pais/region" IS NOT NULL LIMIT 10')
    valores = cursor.fetchall()
    for val in valores:
        print(f"  - {val[0]}")
except Exception as e:
    print(f"  ❌ Error: {str(e)}")
    # Intentar sin comillas
    try:
        cursor.execute("SELECT DISTINCT pais FROM maestro WHERE pais IS NOT NULL LIMIT 10")
        valores = cursor.fetchall()
        for val in valores:
            print(f"  - {val[0]}")
    except Exception as e2:
        print(f"  ❌ También falla sin comillas: {str(e2)[:50]}")

conn.close()
print("\n" + "=" * 80)
