"""
Script para convertir la columna fecha de texto a formato datetime
en el archivo curva_pesos_uyu.xlsx
"""

import pandas as pd
from datetime import datetime
import os

# Rutas
archivo_original = "curva_pesos_uyu.xlsx"
archivo_nuevo = "curva_pesos_uyu_fechas.xlsx"
directorio = os.path.dirname(os.path.abspath(__file__))

ruta_original = os.path.join(directorio, archivo_original)
ruta_nuevo = os.path.join(directorio, archivo_nuevo)

print(f"[INFO] Leyendo archivo: {ruta_original}")

# Leer el archivo Excel
df = pd.read_excel(ruta_original)

print(f"[INFO] Archivo leído: {len(df)} filas, {len(df.columns)} columnas")
print(f"[INFO] Primera columna: {df.columns[0]}")
print(f"[INFO] Primeros valores de fecha (antes):")
print(df.iloc[:5, 0])

# Convertir la primera columna (fecha) de texto a datetime
# Formato: "Sep 15 2017" -> datetime
print(f"\n[INFO] Convirtiendo fechas de texto a datetime...")
columna_fecha = df.columns[0]
df[columna_fecha] = pd.to_datetime(df[columna_fecha], format='%b %d %Y', errors='coerce')

print(f"[INFO] Primeros valores de fecha (después):")
print(df[columna_fecha].head())
print(f"[INFO] Tipo de dato de la columna fecha: {df[columna_fecha].dtype}")

# Verificar si hay fechas que no se pudieron convertir
fechas_nulas = df[columna_fecha].isna().sum()
if fechas_nulas > 0:
    print(f"[WARN] {fechas_nulas} fechas no se pudieron convertir")
    print(df[df[columna_fecha].isna()].head())

# Dividir todos los valores numéricos (excepto fecha) entre 100000
print(f"\n[INFO] Dividiendo todos los valores numéricos entre 100000...")

# Obtener todas las columnas excepto la de fecha
columnas_a_dividir = [col for col in df.columns if col != columna_fecha]
print(f"[INFO] Columnas a dividir: {len(columnas_a_dividir)}")
print(f"[INFO] Columnas: {columnas_a_dividir[:5]}...")  # Mostrar primeras 5

# Convertir a numérico y dividir cada columna entre 100000
for col in columnas_a_dividir:
    print(f"[INFO] Procesando columna '{col}'...")
    # Convertir a numérico (manejar errores con coerce)
    df[col] = pd.to_numeric(df[col], errors='coerce')
    # Dividir entre 100000
    df[col] = df[col] / 100000

print(f"[INFO] Primeros valores después de dividir:")
print(df.head())

# Guardar el nuevo archivo con formato de fecha
print(f"\n[INFO] Guardando nuevo archivo: {ruta_nuevo}")
with pd.ExcelWriter(ruta_nuevo, engine='openpyxl') as writer:
    df.to_excel(writer, index=False, sheet_name='Sheet1')
    
    # Obtener la hoja para formatear la columna de fecha
    worksheet = writer.sheets['Sheet1']
    
    # Aplicar formato de fecha a la primera columna (columna A)
    from openpyxl.styles import NamedStyle
    from openpyxl.utils import get_column_letter
    
    # Formato de fecha estándar
    date_style = NamedStyle(name='date_style', number_format='YYYY-MM-DD')
    
    # Aplicar formato a todas las celdas de la columna A (excepto encabezado)
    for row in range(2, len(df) + 2):  # Empezar en fila 2 (después del encabezado)
        cell = worksheet[f'A{row}']
        cell.number_format = 'YYYY-MM-DD'

print(f"[OK] Archivo guardado exitosamente: {ruta_nuevo}")
print(f"[INFO] Total de filas procesadas: {len(df)}")
