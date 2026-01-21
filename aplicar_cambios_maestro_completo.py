"""
Script para aplicar cambios del archivo maestro_completo.xlsx a la base de datos
"""
import sqlite3
import pandas as pd
import os

DB_NAME = "series_tiempo.db"
EXCEL_NAME = "maestro_completo.xlsx"

print("=" * 60)
print("APLICANDO CAMBIOS DESDE maestro_completo.xlsx")
print("=" * 60)

# Verificar que el archivo existe
if not os.path.exists(EXCEL_NAME):
    print(f"[ERROR] No se encuentra el archivo: {EXCEL_NAME}")
    exit(1)

# Leer el Excel
print(f"\n[INFO] Leyendo archivo: {EXCEL_NAME}")
df_excel = pd.read_excel(EXCEL_NAME, engine="openpyxl")
print(f"[OK] Leídos {len(df_excel)} registros del Excel")

# Mostrar columnas del Excel
print(f"\n[INFO] Columnas en el Excel:")
for col in df_excel.columns:
    print(f"   - {col}")

# Conectar a la base de datos
conn = sqlite3.connect(DB_NAME)
cursor = conn.cursor()

# Obtener estructura actual de la tabla maestro
cursor.execute("PRAGMA table_info(maestro)")
columnas_bd = {col[1]: col[2] for col in cursor.fetchall()}
print(f"\n[INFO] Columnas actuales en BD: {list(columnas_bd.keys())}")

# Verificar y agregar nuevas columnas si existen en el Excel
nuevas_columnas = []
for col in df_excel.columns:
    if col not in columnas_bd:
        print(f"\n[INFO] Nueva columna detectada: {col}")
        # Determinar el tipo de dato
        tipo_dato = "VARCHAR(500)"
        if df_excel[col].dtype == "int64":
            tipo_dato = "INTEGER"
        elif df_excel[col].dtype == "float64":
            tipo_dato = "REAL"
        elif df_excel[col].dtype == "bool":
            tipo_dato = "BOOLEAN"
        
        try:
            cursor.execute(f"ALTER TABLE maestro ADD COLUMN {col} {tipo_dato}")
            nuevas_columnas.append(col)
            print(f"[OK] Columna '{col}' agregada a la tabla maestro")
        except sqlite3.OperationalError as e:
            print(f"[WARN] No se pudo agregar columna '{col}': {e}")

conn.commit()

# Obtener todas las columnas actualizadas (incluyendo las nuevas)
cursor.execute("PRAGMA table_info(maestro)")
columnas_actuales = [col[1] for col in cursor.fetchall()]
print(f"\n[INFO] Columnas finales en BD: {columnas_actuales}")

# Preparar datos para insertar/actualizar
print(f"\n[INFO] Procesando registros...")

registros_insertados = 0
registros_actualizados = 0
errores = []

for idx, row in df_excel.iterrows():
    try:
        # Obtener el ID
        registro_id = int(row.get("id", row.get("ID", None)))
        if registro_id is None:
            print(f"[WARN] Fila {idx+2}: No se encontró ID, se omite")
            continue
        
        # Verificar si el registro existe
        cursor.execute("SELECT id FROM maestro WHERE id = ?", (registro_id,))
        existe = cursor.fetchone() is not None
        
        # Preparar valores para insertar/actualizar
        valores = {}
        for col in columnas_actuales:
            if col in df_excel.columns:
                valor = row[col]
                # Manejar valores NaN
                if pd.isna(valor):
                    valor = None
                # Convertir booleanos
                elif isinstance(valor, bool):
                    valor = 1 if valor else 0
                elif isinstance(valor, (int, float)) and pd.isna(valor):
                    valor = None
                valores[col] = valor
        
        if existe:
            # Actualizar registro existente
            campos_update = ", ".join([f"{k} = ?" for k in valores.keys()])
            valores_list = list(valores.values()) + [registro_id]
            
            cursor.execute(
                f"UPDATE maestro SET {campos_update} WHERE id = ?",
                valores_list
            )
            registros_actualizados += 1
            print(f"[OK] Actualizado registro ID {registro_id}: {row.get('nombre', 'N/A')}")
        else:
            # Insertar nuevo registro
            campos = ", ".join(valores.keys())
            placeholders = ", ".join(["?"] * len(valores))
            valores_list = list(valores.values())
            
            cursor.execute(
                f"INSERT INTO maestro ({campos}) VALUES ({placeholders})",
                valores_list
            )
            registros_insertados += 1
            print(f"[OK] Insertado nuevo registro ID {registro_id}: {row.get('nombre', 'N/A')}")
    
    except Exception as e:
        error_msg = f"Fila {idx+2} (ID: {row.get('id', 'N/A')}): {str(e)}"
        errores.append(error_msg)
        print(f"[ERROR] {error_msg}")

# Confirmar cambios
conn.commit()

# Mostrar resumen
print("\n" + "=" * 60)
print("RESUMEN DE CAMBIOS")
print("=" * 60)
print(f"Registros actualizados: {registros_actualizados}")
print(f"Registros insertados: {registros_insertados}")
if nuevas_columnas:
    print(f"Columnas nuevas agregadas: {', '.join(nuevas_columnas)}")
if errores:
    print(f"\n[WARN] Errores encontrados: {len(errores)}")
    for error in errores[:5]:
        print(f"   - {error}")
    if len(errores) > 5:
        print(f"   ... y {len(errores) - 5} más")

# Verificar resultado final
cursor.execute("SELECT COUNT(*) FROM maestro")
total_final = cursor.fetchone()[0]
print(f"\nTotal de registros en BD después de cambios: {total_final}")

conn.close()

print("\n[OK] Cambios aplicados exitosamente")
