# -*- coding: utf-8 -*-
"""
Script: nxr_chile
----------------
Actualiza la base de datos con la serie de tipo de cambio USD/CLP del Banco Central 
de Chile (BCCH), usando su API oficial (bcchapi).

1) Extraer datos desde API del BCCH usando bcchapi (desde 2010-01-01).
2) Filtrar valores no numéricos.
3) Completar días faltantes (forward fill).
4) Validar fechas.
5) Actualizar automáticamente la base de datos.
"""

from datetime import datetime

import pandas as pd
from bcchapi import Siete
from _helpers import (
    completar_dias_faltantes,
    validar_fechas_solo_nulas,
    insertar_en_bd_unificado
)


# Configuración de base de datos
# Credenciales del BCCH
BCCH_USER = "joaquin.forrisi@gmail.com"
BCCH_PASSWORD = "Joaquin.13"

# Código de serie del BCCH para Dólar Observado (puede variar, se busca automáticamente)
CODIGO_SERIE_BCCH = None  # Se buscará automáticamente

# Configuración de IDs (desde maestro_database.xlsx Sheet1_old)
ID_VARIABLE = 20  # Configurar cuando esté en maestro_database.xlsx
ID_PAIS = 152  # Chile)


def buscar_codigo_serie(siete: Siete):
    """
    Busca el código de serie para el Dólar Observado en el BCCH.
    
    Returns:
        Código de serie (str) o None si no se encuentra
    """
    print("[INFO] Buscando código de serie para 'Dólar Observado'...")
    
    try:
        df_busqueda = siete.buscar("Dólar Observado")
        
        if df_busqueda is None or df_busqueda.empty:
            print("[WARN] No se encontraron series con 'Dólar Observado'")
            # Intentar otras búsquedas
            df_busqueda = siete.buscar("dolar")
            if df_busqueda is None or df_busqueda.empty:
                return None
        
        print(f"[INFO] Se encontraron {len(df_busqueda)} series:")
        print(df_busqueda.head())
        
        # Buscar la serie diaria (frecuencia 'D' o 'DAILY')
        serie_diaria = None
        
        for idx, row in df_busqueda.iterrows():
            if isinstance(row, pd.Series):
                codigo = str(row.get('seriesId', row.get('codigo', row.iloc[0] if len(row) > 0 else '')))
                frecuencia = str(row.get('frequencyCode', row.get('frecuencia', row.iloc[-1] if len(row) > 1 else '')))
            else:
                codigo = str(row.get('seriesId', '')) if hasattr(row, 'get') else (str(row[0]) if len(row) > 0 else '')
                frecuencia = str(row.get('frequencyCode', '')) if hasattr(row, 'get') else (str(row[-1]) if len(row) > 1 else '')
            
            if frecuencia.upper() in ['DAILY', 'D', 'DIARIA', 'DIARIO']:
                if 'TCO' in codigo.upper() or 'DOLAR' in codigo.upper():
                    print(f"[OK] Código diario encontrado: {codigo}")
                    return codigo
                elif serie_diaria is None:
                    serie_diaria = codigo
        
        if serie_diaria:
            print(f"[INFO] Usando serie diaria encontrada: {serie_diaria}")
            return serie_diaria
        
        for idx, row in df_busqueda.iterrows():
            if isinstance(row, pd.Series):
                codigo = str(row.get('seriesId', row.get('codigo', row.iloc[0] if len(row) > 0 else '')))
            else:
                codigo = str(row.get('seriesId', '')) if hasattr(row, 'get') else (str(row[0]) if len(row) > 0 else '')
            
            if 'TCO' in codigo.upper():
                print(f"[INFO] Usando serie con TCO: {codigo}")
                return codigo
        
        if len(df_busqueda) > 0:
            primer_row = df_busqueda.iloc[0]
            if isinstance(primer_row, pd.Series):
                primer_codigo = str(primer_row.get('seriesId', primer_row.get('codigo', primer_row.iloc[0] if len(primer_row) > 0 else '')))
            else:
                primer_codigo = str(primer_row.get('seriesId', '')) if hasattr(primer_row, 'get') else (str(primer_row[0]) if len(primer_row) > 0 else '')
            print(f"[WARN] Usando primer código encontrado (puede no ser diario): {primer_codigo}")
            return primer_codigo
        
        return None
        
    except Exception as e:
        print(f"[ERROR] Error al buscar código de serie: {e}")
        import traceback
        traceback.print_exc()
        return None

def extraer_bcch_chile(fecha_inicio="2010-01-01", fecha_fin=None):
    """
    Extrae datos de tipo de cambio del Banco Central de Chile usando bcchapi.
    
    Args:
        fecha_inicio: Fecha de inicio en formato YYYY-MM-DD (por defecto: 2010-01-01)
        fecha_fin: Fecha de fin en formato YYYY-MM-DD (por defecto: hoy)
        
    Returns:
        DataFrame con columnas: Fecha, Tipo_Cambio
    """
    print(f"[INFO] Extrayendo datos desde API del BCCH...")
    
    if fecha_fin is None:
        fecha_fin = datetime.today().strftime("%Y-%m-%d")
    
    try:
        # Inicializar conexión con BCCH
        print(f"[INFO] Conectando al BCCH con usuario: {BCCH_USER}")
        siete = Siete(BCCH_USER, BCCH_PASSWORD)
        
        # Buscar código de serie si no está definido
        codigo_serie = CODIGO_SERIE_BCCH
        if codigo_serie is None:
            codigo_serie = buscar_codigo_serie(siete)
            if codigo_serie is None:
                print("[WARN] No se pudo encontrar el código de serie automáticamente")
                print("[INFO] Intentando con código común: F032.TCO.PRE.Z.D")
                codigo_serie = "F032.TCO.PRE.Z.D"
        
        print(f"[INFO] Usando código de serie: {codigo_serie}")
        print(f"[INFO] Rango solicitado: {fecha_inicio} a {fecha_fin}")
        
        # Obtener datos
        df = siete.cuadro(
            series=[codigo_serie],
            nombres=["dolar_observado"],
            desde=fecha_inicio,
            hasta=fecha_fin
        )
        
        if df is None or df.empty:
            print("[ERROR] No se obtuvieron datos del BCCH")
            return None
        
        print(f"[OK] Se obtuvieron {len(df)} registros del BCCH")
        
        # Preparar DataFrame estándar
        if 'dolar_observado' in df.columns:
            if df.index.name and 'fecha' in str(df.index.name).lower():
                df['Fecha'] = df.index
            elif 'Fecha' not in df.columns:
                df = df.reset_index()
                if 'index' in df.columns:
                    df.rename(columns={'index': 'Fecha'}, inplace=True)
            
            df['Tipo_Cambio'] = df['dolar_observado']
        
        elif len(df.columns) == 1:
            df = df.reset_index()
            df.columns = ['Fecha', 'Tipo_Cambio']
        
        else:
            df = df.reset_index()
            if len(df.columns) >= 2:
                df.columns = ['Fecha'] + list(df.columns[1:])
                df['Tipo_Cambio'] = df.iloc[:, 1]
        
        if 'Fecha' not in df.columns or 'Tipo_Cambio' not in df.columns:
            print(f"[ERROR] No se pudo identificar las columnas Fecha y Tipo_Cambio")
            print(f"[DEBUG] Columnas disponibles: {list(df.columns)}")
            return None
        
        df = df[['Fecha', 'Tipo_Cambio']].copy()
        
        # Convertir fecha a datetime
        df['Fecha'] = pd.to_datetime(df['Fecha'], errors='coerce')
        df = df.dropna(subset=['Fecha'])
        
        # Convertir valor a numérico y filtrar valores inválidos
        df['Tipo_Cambio'] = pd.to_numeric(df['Tipo_Cambio'], errors='coerce')
        df = df.dropna(subset=['Tipo_Cambio'])
        
        # Eliminar duplicados por fecha (mantener el último)
        df = df.drop_duplicates(subset='Fecha', keep='last')
        
        # Ordenar por fecha
        df = df.sort_values('Fecha').reset_index(drop=True)
        
        print(f"[OK] Se procesaron {len(df)} registros válidos")
        if len(df) > 0:
            print(f"   Rango: {df['Fecha'].min().strftime('%d/%m/%Y')} a {df['Fecha'].max().strftime('%d/%m/%Y')}")
        
        return df
        
    except Exception as e:
        print(f"[ERROR] Error al obtener datos del BCCH: {e}")
        import traceback
        traceback.print_exc()
        return None

def main():
    print("=" * 60)
    print("ACTUALIZACION DE DATOS: TIPO DE CAMBIO USD/CLP (CHILE)")
    print("=" * 60)
    
    # Extraer datos desde API del BCCH (desde 2010-01-01)
    print("\n[INFO] Extrayendo datos del Banco Central de Chile (API)...")
    df = extraer_bcch_chile(fecha_inicio="2010-01-01", fecha_fin=None)
    
    if df is None or df.empty:
        print("[ERROR] No se pudieron extraer los datos")
        return
    
    # Mostrar primeros y últimos datos
    print("\n[INFO] Datos de la serie cruda:")
    print("\nPrimeros datos:")
    print(df.head())
    print("\nÚltimos datos:")
    print(df.tail())
    
    # COMPLETAR DÍAS FALTANTES y solo lunes a viernes
    df = completar_dias_faltantes(
        df, columna_fecha='Fecha', columna_valor='Tipo_Cambio', solo_lunes_a_viernes=True
    )
    
    # Renombrar columnas para el helper
    df = df.rename(columns={'Fecha': 'FECHA', 'Tipo_Cambio': 'VALOR'})
    
    # Validar fechas
    df = validar_fechas_solo_nulas(df)
    
    # Verificar que ID_VARIABLE e ID_PAIS están configurados
    if ID_VARIABLE is None or ID_PAIS is None:
        print("\n[ERROR] ID_VARIABLE e ID_PAIS deben estar configurados en el script.")
        print("   Consulta maestro_database.xlsx o la base de datos para obtener los valores correctos.")
        return
    
    print("\n[INFO] Actualizando base de datos...")
    insertar_en_bd_unificado(ID_VARIABLE, ID_PAIS, df)

if __name__ == "__main__":
    main()
