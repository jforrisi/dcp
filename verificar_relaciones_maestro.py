import pandas as pd

maestro = pd.read_excel('maestro_database.xlsx', sheet_name='maestro')
variables = pd.read_excel('maestro_database.xlsx', sheet_name='variables')
sheet1 = pd.read_excel('maestro_database.xlsx', sheet_name='Sheet1_old')

print("=== VERIFICACIÓN DE RELACIONES ===")
print(f"\nMaestro tiene {len(maestro)} registros")
print(f"Variables tiene {len(variables)} registros")
print(f"Sheet1_old tiene {len(sheet1)} registros")

print("\n=== EJEMPLO DE Sheet1_old (estructura completa) ===")
print(sheet1[['id', 'nombre', 'id_nombre_variable', 'id_region', 'pais/region', 'moneda', 'nominal_real']].head(10).to_string())

print("\n=== RELACIÓN: id_nombre_variable ===")
print("En maestro (tipo numérico):")
print(maestro['id_nombre_variable'].head(10).tolist())
print("\nEn variables:")
print("  - id_variable (PK numérico):")
print(variables['id_variable'].head(10).tolist())
print("  - id_nombre_variable (nombre texto):")
print(variables['id_nombre_variable'].head(10).tolist())

print("\n=== VERIFICANDO RELACIÓN CORRECTA ===")
print("\nEjemplo: id_nombre_variable=12 en Sheet1_old:")
ejemplo = sheet1[sheet1['id_nombre_variable']==12]
if len(ejemplo) > 0:
    print(ejemplo[['id', 'nombre', 'id_nombre_variable']].to_string())
    
print("\nBuscando id_variable=12 en variables:")
var_12 = variables[variables['id_variable']==12]
if len(var_12) > 0:
    print(var_12[['id_variable', 'id_nombre_variable', 'moneda']].to_string())
else:
    print("No encontrado id_variable=12")
    
print("\n=== MAPEO COMPLETO ===")
print("Verificando si maestro.id_nombre_variable -> variables.id_variable:")
merged = maestro.merge(variables, left_on='id_nombre_variable', right_on='id_variable', how='left')
print(f"Registros con match: {merged['id_variable'].notna().sum()} de {len(merged)}")
print("\nEjemplo de merge exitoso:")
merged_exitoso = merged[merged['id_variable'].notna()].head(5)
cols = [c for c in merged_exitoso.columns if c in ['id_nombre_variable_x', 'id_variable', 'id_nombre_variable_y', 'moneda', 'nominal_o_real', 'id_region']]
print(merged_exitoso[cols].to_string())

print("\n=== CONCLUSIÓN ===")
print("La relación correcta es:")
print("  maestro.id_nombre_variable (numérico) -> variables.id_variable (numérico)")
print("  variables.id_nombre_variable es el NOMBRE descriptivo de la variable")
