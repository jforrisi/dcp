"""
Script para analizar maestro_database.xlsx y entender cómo integrarlo al sistema
"""
import pandas as pd

# Leer todas las hojas
excel_file = "maestro_database.xlsx"
sheets = pd.read_excel(excel_file, sheet_name=None)

print("=" * 80)
print("ANÁLISIS DE maestro_database.xlsx")
print("=" * 80)

# Analizar cada hoja
for sheet_name, df in sheets.items():
    print(f"\n{'='*80}")
    print(f"HOJA: {sheet_name}")
    print(f"{'='*80}")
    print(f"Filas: {len(df)}")
    print(f"Columnas: {list(df.columns)}")
    print(f"\nPrimeras 5 filas:")
    print(df.head(5).to_string())
    print(f"\nValores únicos por columna:")
    for col in df.columns:
        if df[col].dtype == 'object':
            unique_vals = df[col].dropna().unique()
            if len(unique_vals) <= 10:
                print(f"  {col}: {list(unique_vals)}")
            else:
                print(f"  {col}: {len(unique_vals)} valores únicos (mostrando primeros 5: {list(unique_vals[:5])})")

# Análisis de relaciones
print(f"\n{'='*80}")
print("ANÁLISIS DE RELACIONES ENTRE TABLAS")
print(f"{'='*80}")

maestro = sheets['maestro']
variables = sheets['variables']
pais_grupo = sheets['pais_grupo']
familia = sheets['familia']
sub_familia = sheets['sub_familia']

print(f"\n1. MAESTRO -> VARIABLES (por id_nombre_variable)")
# Convertir id_nombre_variable a string en ambas tablas para el merge
maestro_merge = maestro.copy()
maestro_merge['id_nombre_variable'] = maestro_merge['id_nombre_variable'].astype(str)
variables_merge = variables.copy()
variables_merge['id_nombre_variable'] = variables_merge['id_nombre_variable'].astype(str)
merged = maestro_merge.merge(variables_merge, on='id_nombre_variable', how='left')
print(f"   Registros después del merge: {len(merged)}")
print(f"   Ejemplo:")
if 'id_sub_familia' in merged.columns:
    print(merged.head(3)[['id_nombre_variable', 'id_region', 'id_sub_familia', 'moneda', 'nominal_o_real']].to_string())
else:
    print(merged.head(3).to_string())

print(f"\n2. VARIABLES -> SUB_FAMILIA (por id_sub_familia)")
merged2 = variables.merge(sub_familia, on='id_sub_familia', how='left')
print(f"   Registros después del merge: {len(merged2)}")
print(f"   Ejemplo:")
print(merged2.head(3)[['id_variable', 'id_nombre_variable', 'nombre_sub_familia', 'moneda']].to_string())

print(f"\n3. MAESTRO -> PAIS_GRUPO (por id_region)")
merged3 = maestro.merge(pais_grupo, left_on='id_region', right_on='id_pais_grupo', how='left')
print(f"   Registros después del merge: {len(merged3)}")
print(f"   Ejemplo:")
print(merged3.head(3)[['id_nombre_variable', 'id_region', 'nombre_pais_grupo', 'fuente']].to_string())

# Comparar con estructura actual
print(f"\n{'='*80}")
print("COMPARACIÓN CON ESTRUCTURA ACTUAL (tabla maestro)")
print(f"{'='*80}")

print("\nEstructura actual del sistema:")
print("  - id (PK)")
print("  - nombre")
print("  - tipo (P/S/M)")
print("  - fuente")
print("  - periodicidad (D/W/M)")
print("  - unidad")
print("  - categoria")
print("  - activo")
print("  - moneda (adicional)")
print("  - nominal_real (adicional)")
print("  - es_cotizacion (adicional)")

print("\nNueva estructura (maestro_database.xlsx):")
print("  - id_nombre_variable (FK a variables)")
print("  - id_region (FK a pais_grupo)")
print("  - fuente")
print("  - periodicidad")
print("  - activo")
print("  - link")

print("\nTablas relacionadas:")
print("  - variables: id_variable, id_nombre_variable, id_sub_familia, nominal_o_real, moneda")
print("  - pais_grupo: id_pais_grupo, nombre_pais_grupo")
print("  - familia: id_familia, nombre_familia")
print("  - sub_familia: id_sub_familia, nombre_sub_familia")
print("  - graph: id_graph, nombre_graph, selector")
print("  - filtros_graph_pais: id_graph, id_pais_region")
