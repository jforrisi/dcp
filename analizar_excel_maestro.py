import pandas as pd
import sqlite3

# Leer el Excel
excel_path = "maestro_completo.xlsx"
df = pd.read_excel(excel_path)

print("=" * 80)
print("ANÁLISIS DEL EXCEL: maestro_completo.xlsx")
print("=" * 80)

print(f"\n[TOTAL DE REGISTROS]: {len(df)}")
print(f"[COLUMNAS ENCONTRADAS] ({len(df.columns)}):")
for i, col in enumerate(df.columns, 1):
    print(f"   {i}. {col}")

print("\n" + "=" * 80)
print("ESTRUCTURA DE DATOS (Primeras 10 filas):")
print("=" * 80)
print(df.head(10).to_string())

print("\n" + "=" * 80)
print("ANÁLISIS POR COLUMNA:")
print("=" * 80)

# Analizar cada columna
for col in df.columns:
    print(f"\n[COLUMNA]: {col}")
    print(f"   Tipo: {df[col].dtype}")
    print(f"   Valores únicos: {df[col].nunique()}")
    print(f"   Valores nulos: {df[col].isna().sum()}")
    
    if df[col].nunique() <= 20:
        print(f"   Valores: {df[col].unique().tolist()}")
    else:
        print(f"   Primeros valores: {df[col].head(5).tolist()}")

print("\n" + "=" * 80)
print("COMENTARIOS Y RECOMENDACIONES:")
print("=" * 80)

# Verificar columnas críticas
columnas_criticas = ['id', 'nombre', 'tipo', 'categoria', 'periodicidad', 'activo', 'es_cotizacion', 'moneda', 'nominal_real']

print("\n[COLUMNAS CRITICAS]:")
for col in columnas_criticas:
    if col in df.columns:
        print(f"   [OK] {col}: PRESENTE")
    else:
        print(f"   [FALTA] {col}: FALTANTE")

# Verificar si hay columna de país
if 'pais' in df.columns:
    print("\n[COLUMNA 'pais' ENCONTRADA]:")
    print(f"   Valores únicos: {df['pais'].unique().tolist()}")
    print(f"   Valores nulos: {df['pais'].isna().sum()}")
else:
    print("\n[ADVERTENCIA] COLUMNA 'pais' NO ENCONTRADA - Se recomienda agregarla")

# Analizar categorías
if 'categoria' in df.columns:
    print("\n[ANALISIS DE CATEGORIAS]:")
    print(df['categoria'].value_counts().to_string())

# Analizar tipos
if 'tipo' in df.columns:
    print("\n[ANALISIS DE TIPOS]:")
    print(df['tipo'].value_counts().to_string())

# Analizar cotizaciones
if 'es_cotizacion' in df.columns:
    print("\n[COTIZACIONES]:")
    cotizaciones = df[df['es_cotizacion'] == 1]
    print(f"   Total con es_cotizacion=1: {len(cotizaciones)}")
    if len(cotizaciones) > 0:
        print("   Nombres:")
        for idx, row in cotizaciones.head(20).iterrows():
            print(f"      - ID {row.get('id', 'N/A')}: {row.get('nombre', 'N/A')}")

# Buscar patrones USD/LC en nombres
if 'nombre' in df.columns:
    print("\n[BUSQUEDA DE PATRONES EN NOMBRES]:")
    usd_lc = df[df['nombre'].str.contains('USD/LC', case=False, na=False)]
    print(f"   Registros con 'USD/LC' en nombre: {len(usd_lc)}")
    if len(usd_lc) > 0:
        print("   Nombres encontrados:")
        for idx, row in usd_lc.iterrows():
            print(f"      - ID {row.get('id', 'N/A')}: {row.get('nombre', 'N/A')}")

# Analizar productos por categoría "Precios Internacionales"
if 'categoria' in df.columns:
    print("\n[PRODUCTOS CON CATEGORIA 'Precios Internacionales']:")
    precios_int = df[df['categoria'].str.contains('Precios Internacionales', case=False, na=False)]
    print(f"   Total: {len(precios_int)}")
    if len(precios_int) > 0:
        print("   IDs y nombres:")
        for idx, row in precios_int.head(20).iterrows():
            print(f"      - ID {row.get('id', 'N/A')}: {row.get('nombre', 'N/A')}")

# Verificar IPC y TC de Uruguay
if 'nombre' in df.columns:
    print("\n[BUSQUEDA DE IPC Y TC DE URUGUAY]:")
    ipc_uy = df[df['nombre'].str.contains('IPC.*Uruguay|Uruguay.*IPC', case=False, na=False)]
    tc_usd_uy = df[df['nombre'].str.contains('USD.*Uruguay|Uruguay.*USD|Tipo de cambio.*USD.*UYU', case=False, na=False)]
    tc_eur_uy = df[df['nombre'].str.contains('EUR.*Uruguay|Uruguay.*EUR|Tipo de cambio.*EUR.*UYU', case=False, na=False)]
    
    print(f"   IPC Uruguay encontrados: {len(ipc_uy)}")
    for idx, row in ipc_uy.iterrows():
        print(f"      - ID {row.get('id', 'N/A')}: {row.get('nombre', 'N/A')}")
    
    print(f"   TC USD/UYU encontrados: {len(tc_usd_uy)}")
    for idx, row in tc_usd_uy.iterrows():
        print(f"      - ID {row.get('id', 'N/A')}: {row.get('nombre', 'N/A')}")
    
    print(f"   TC EUR/UYU encontrados: {len(tc_eur_uy)}")
    for idx, row in tc_eur_uy.iterrows():
        print(f"      - ID {row.get('id', 'N/A')}: {row.get('nombre', 'N/A')}")

print("\n" + "=" * 80)
print("FIN DEL ANÁLISIS")
print("=" * 80)
