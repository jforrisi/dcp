"""
Script para verificar y exportar IPC de Brasil, Chile y Perú a Excel
"""
import sqlite3
import pandas as pd
from pathlib import Path

DB_NAME = "series_tiempo.db"
EXCEL_OUTPUT = "ipc_brasil_chile_peru.xlsx"

# IDs de las series
ID_BRASIL = 34
ID_CHILE = 33
ID_PERU = 36

def obtener_datos_ipc():
    """Obtiene datos de IPC de Brasil, Chile y Perú desde la BD"""
    conn = sqlite3.connect(DB_NAME)
    
    # Obtener datos de cada país
    query = """
        SELECT fecha, valor
        FROM maestro_precios
        WHERE maestro_id = ?
        ORDER BY fecha ASC
    """
    
    df_brasil = pd.read_sql_query(query, conn, params=(ID_BRASIL,))
    df_chile = pd.read_sql_query(query, conn, params=(ID_CHILE,))
    df_peru = pd.read_sql_query(query, conn, params=(ID_PERU,))
    
    conn.close()
    
    # Preparar DataFrames
    df_brasil['fecha'] = pd.to_datetime(df_brasil['fecha'])
    df_chile['fecha'] = pd.to_datetime(df_chile['fecha'])
    df_peru['fecha'] = pd.to_datetime(df_peru['fecha'])
    
    # Renombrar columnas de valor
    df_brasil = df_brasil.rename(columns={'valor': 'Brasil'})
    df_chile = df_chile.rename(columns={'valor': 'Chile'})
    df_peru = df_peru.rename(columns={'valor': 'Perú'})
    
    # Combinar por fecha (outer join para incluir todas las fechas)
    df_combinado = df_brasil[['fecha', 'Brasil']].merge(
        df_chile[['fecha', 'Chile']], 
        on='fecha', 
        how='outer'
    ).merge(
        df_peru[['fecha', 'Perú']], 
        on='fecha', 
        how='outer'
    )
    
    # Ordenar por fecha
    df_combinado = df_combinado.sort_values('fecha').reset_index(drop=True)
    
    # Formatear fecha para Excel
    df_combinado['Fecha'] = df_combinado['fecha'].dt.strftime('%Y-%m-%d')
    
    # Seleccionar columnas en el orden solicitado: Fecha, Brasil, Chile, Perú
    df_final = df_combinado[['Fecha', 'Brasil', 'Chile', 'Perú']].copy()
    
    return df_final

def main():
    print("=" * 60)
    print("EXPORTANDO IPC: BRASIL, CHILE Y PERÚ")
    print("=" * 60)
    
    df = obtener_datos_ipc()
    
    print(f"\n[INFO] Total de registros: {len(df)}")
    print(f"\nPrimeros 10 registros:")
    print(df.head(10).to_string(index=False))
    print(f"\nÚltimos 10 registros:")
    print(df.tail(10).to_string(index=False))
    
    # Exportar a Excel
    excel_path = Path(EXCEL_OUTPUT)
    df.to_excel(excel_path, index=False, sheet_name='IPC Multipaís')
    
    print(f"\n[OK] Excel exportado: {excel_path.absolute()}")
    print(f"   Columnas: Fecha, Brasil, Chile, Perú")
    print(f"   Total de filas: {len(df)}")

if __name__ == "__main__":
    main()
