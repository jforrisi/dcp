# -*- coding: utf-8 -*-
"""
Script: nxr_bra
---------------
Actualiza la base de datos con la serie de tipo de cambio USD/BRL del Banco Central de Brasil (BCB).

1) Extraer datos desde API del BCB.
2) Completar días faltantes (forward fill).
3) Validar fechas.
4) Actualizar automáticamente la base de datos.
"""

from datetime import datetime

import pandas as pd
import requests
from _helpers import (
    validar_fechas_solo_nulas,
    insertar_en_bd_unificado
)


# Configuración de base de datos
DB_NAME = "series_tiempo.db"

# Configuración de IDs (desde maestro_database.xlsx Sheet1_old)
ID_VARIABLE = 20  # Configurar cuando esté en maestro_database.xlsx
ID_PAIS = 76  # Brasil)


def extraer_bcb_brasil(fecha_inicio=None, fecha_fin=None):
    """
    Extrae datos de tipo de cambio del Banco Central de Brasil (BCB).
    
    Args:
        fecha_inicio: Fecha de inicio en formato MM-DD-YYYY (por defecto: 01-01-2010)
        fecha_fin: Fecha de fin en formato MM-DD-YYYY (por defecto: hoy)
        
    Returns:
        DataFrame con columnas: Fecha, Tipo_Cambio (promedio de compra y venta)
    """
    try:
        # Fechas por defecto
        if fecha_inicio is None:
            fecha_inicio = "01-01-2010"  # MM-DD-YYYY - desde 2010 como solicitado
        if fecha_fin is None:
            fecha_fin = datetime.today().strftime("%m-%d-%Y")
        
        # Endpoint oficial BCB (PTAX)
        url = (
            "https://olinda.bcb.gov.br/olinda/servico/PTAX/versao/v1/odata/"
            "CotacaoDolarPeriodo(dataInicial=@dataInicial,dataFinalCotacao=@dataFinalCotacao)?"
            f"@dataInicial='{fecha_inicio}'"
            f"&@dataFinalCotacao='{fecha_fin}'"
            "&$format=json"
        )
        
        # Request
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        data = response.json()["value"]
        
        if not data:
            print("No se encontraron datos en el rango de fechas especificado")
            return None
        
        # DataFrame
        df = pd.DataFrame(data)
        
        # Crear DataFrame con las columnas necesarias
        datos = pd.DataFrame({
            'Fecha': pd.to_datetime(df["dataHoraCotacao"]).dt.date,
            'Compra': df["cotacaoCompra"],
            'Venta': df["cotacaoVenda"]
        })
        
        # Limpiar datos: eliminar filas vacías o con NaN en fecha
        datos = datos.dropna(subset=['Fecha'])
        
        # Convertir fecha a datetime
        datos['Fecha'] = pd.to_datetime(datos['Fecha'])
        
        # Convertir compra y venta a numérico
        datos['Compra'] = pd.to_numeric(datos['Compra'], errors='coerce')
        datos['Venta'] = pd.to_numeric(datos['Venta'], errors='coerce')
        
        # Calcular promedio de compra y venta
        datos['Tipo_Cambio'] = (datos['Compra'] + datos['Venta']) / 2
        
        # Seleccionar solo Fecha y Tipo_Cambio
        tc_brasil = datos[['Fecha', 'Tipo_Cambio']].copy()
        
        # Eliminar filas donde Tipo_Cambio es NaN
        tc_brasil = tc_brasil.dropna(subset=['Tipo_Cambio'])
        
        # Agrupar por fecha y promediar (por si hay duplicados)
        tc_brasil = tc_brasil.groupby('Fecha')['Tipo_Cambio'].mean().reset_index()
        
        # Ordenar por fecha (más reciente primero)
        tc_brasil = tc_brasil.sort_values('Fecha', ascending=False).reset_index(drop=True)
        
        return tc_brasil
        
    except Exception as e:
        print(f"Error al procesar los datos: {e}")
        import traceback
        traceback.print_exc()
        return None

def completar_dias_faltantes(df: pd.DataFrame, columna_fecha: str = 'Fecha', columna_valor: str = 'Tipo_Cambio') -> pd.DataFrame:
    """
    Completa días faltantes en una serie diaria usando forward fill.
    """
    print("\n[INFO] Completando días faltantes en serie diaria...")
    
    df = df.copy()
    df[columna_fecha] = pd.to_datetime(df[columna_fecha])
    df = df.sort_values(columna_fecha).reset_index(drop=True)
    
    fecha_min = df[columna_fecha].min()
    fecha_max = df[columna_fecha].max()
    
    rango_completo = pd.date_range(start=fecha_min, end=fecha_max, freq='D')
    df_completo = pd.DataFrame({columna_fecha: rango_completo})
    
    df_completo = df_completo.merge(
        df[[columna_fecha, columna_valor]], 
        on=columna_fecha, 
        how='left'
    )
    
    df_completo[columna_valor] = df_completo[columna_valor].ffill()
    
    dias_originales = len(df)
    dias_completados = len(df_completo)
    dias_agregados = dias_completados - dias_originales
    
    if dias_agregados > 0:
        print(f"[INFO] Se completaron {dias_agregados} días faltantes (de {dias_originales} a {dias_completados} días)")
        print(f"   Rango: {fecha_min.strftime('%d/%m/%Y')} a {fecha_max.strftime('%d/%m/%Y')}")
    else:
        print(f"[OK] No había días faltantes ({dias_originales} días en el rango)")
    
    return df_completo

def main():
    print("=" * 60)
    print("ACTUALIZACION DE DATOS: TIPO DE CAMBIO USD/BRL (BRASIL)")
    print("=" * 60)
    
    # Extraer datos desde API del BCB (desde 2010)
    print("\n[INFO] Extrayendo datos del Banco Central de Brasil (desde 2010)...")
    df = extraer_bcb_brasil(fecha_inicio="01-01-2010", fecha_fin=None)
    
    if df is None or df.empty:
        print("[ERROR] No se pudieron extraer los datos")
        return
    
    # Mostrar primeros y últimos datos
    print("\n[INFO] Datos de la serie cruda:")
    print("\nPrimeros datos:")
    print(df.head())
    print("\nÚltimos datos:")
    print(df.tail())
    
    # COMPLETAR DÍAS FALTANTES (OBLIGATORIO para series diarias según README)
    df = completar_dias_faltantes(df, columna_fecha='Fecha', columna_valor='Tipo_Cambio')
    
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
    insertar_en_bd_unificado(ID_VARIABLE, ID_PAIS, df, DB_NAME)

if __name__ == "__main__":
    main()
