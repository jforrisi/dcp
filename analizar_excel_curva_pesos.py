"""Script para analizar la estructura del Excel de curva de pesos"""

import pandas as pd
import os

archivo = "update/historicos/curva_pesos_uyu_fechas.xlsx"

if not os.path.exists(archivo):
    # Intentar con el original
    archivo = "update/historicos/curva_pesos_uyu.xlsx"

if not os.path.exists(archivo):
    print(f"[ERROR] No se encontró el archivo Excel")
    exit(1)

print(f"[INFO] Leyendo: {archivo}")
df = pd.read_excel(archivo)

print("\n" + "=" * 80)
print("ESTRUCTURA DEL EXCEL")
print("=" * 80)
print(f"Filas: {len(df)}")
print(f"Columnas: {len(df.columns)}")
print(f"\nNombres de columnas:")
for i, col in enumerate(df.columns):
    print(f"  {i}: {col}")

print(f"\nPrimeras 5 filas:")
print(df.head())

print(f"\nÚltimas 5 filas:")
print(df.tail())

print(f"\nTipos de datos:")
print(df.dtypes)

print(f"\nRango de fechas:")
print(f"  Primera fecha: {df.iloc[:, 0].min()}")
print(f"  Última fecha: {df.iloc[:, 0].max()}")

print(f"\nValores de ejemplo (primera fila):")
for col in df.columns:
    print(f"  {col}: {df.iloc[0][col]}")
