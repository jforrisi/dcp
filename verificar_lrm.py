import pandas as pd

xl = pd.ExcelFile('data_raw/instrumentos_emitidos_bcu_y_gobierno_central.xlsx')
print('Hojas:', xl.sheet_names)

df = pd.read_excel(xl, sheet_name='LRM', skiprows=9, header=None, nrows=10)
print(f'\nHoja LRM: {len(df)} filas, {len(df.columns)} columnas')
print('\nPrimeras 10 filas:')
print(df.to_string())

print('\n\nVerificando columnas V, Z, AA:')
if len(df.columns) > 21:
    print(f'Columna V (21): {df.iloc[0, 21]}')
if len(df.columns) > 25:
    print(f'Columna Z (25): {df.iloc[0, 25]}')
if len(df.columns) > 26:
    print(f'Columna AA (26): {df.iloc[0, 26]}')
