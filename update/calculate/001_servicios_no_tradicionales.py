"""
Script: servicios_no_tradicionales
-----------------------------------
Calcula y actualiza la base de datos con la serie "Servicios no tradicionales - sin software"
como promedio mensual de las series:
- Ingeniería (id_variable=8, id_pais=999)
- Arquitectura (id_variable=1, id_pais=999)
- Contabilidad (id_variable=5, id_pais=999)
- Bookkeeping (id_variable=3, id_pais=999)

1) Leer las 4 series desde maestro_precios.
2) Calcular promedio mensual por fecha.
3) Validar fechas.
4) Actualizar automáticamente la base de datos.
"""

import sys
import os
from pathlib import Path
import sqlite3
from datetime import datetime
from dateutil.relativedelta import relativedelta

import pandas as pd

# Agregar el directorio padre al path para importar _helpers
SCRIPT_DIR = Path(__file__).parent.absolute()
PROJECT_ROOT = SCRIPT_DIR.parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "update" / "direct"))

from _helpers import (
    validar_fechas_solo_nulas,
    insertar_en_bd_unificado
)


# Configuración de base de datos
DB_NAME = "series_tiempo.db"

# IDs de las series fuente (id_variable, id_pais)
# Todas las series fuente tienen id_pais=999 (Economía internacional)
SERIES_FUENTE = [
    (8, 999),   # Ingeniería
    (1, 999),   # Arquitectura
    (5, 999),   # Contabilidad (CPA)
    (3, 999),   # Bookkeeping / payroll
]

# Configuración de la serie destino
ID_VARIABLE = 16  # Servicios no tradicionales - sin software (desde maestro_database.xlsx Sheet1_old)
ID_PAIS = 999  # Economía internacional_database.xlsx Sheet1_old)


def leer_series_fuente():
    """
    Lee las 4 series fuente desde maestro_precios.
    Solo lee los últimos 24 meses para optimizar el rendimiento.
    Retorna un DataFrame con fecha y valores de cada serie.
    """
    print("\n[INFO] Leyendo series fuente desde la base de datos...")
    print(f"   Series: {SERIES_FUENTE}")
    print("   [OPTIMIZACIÓN] Solo se leerán los últimos 24 meses")
    
    # Calcular fecha límite (últimos 24 meses)
    fecha_limite = datetime.now() - relativedelta(months=24)
    fecha_limite_str = fecha_limite.strftime('%Y-%m-%d')
    
    print(f"   Fecha límite: {fecha_limite_str} (últimos 24 meses)")
    
    conn = sqlite3.connect(DB_NAME)
    
    # Leer todas las series fuente (solo últimos 24 meses)
    dfs = []
    for id_variable, id_pais in SERIES_FUENTE:
        query = """
            SELECT fecha, valor
            FROM maestro_precios
            WHERE id_variable = ? AND id_pais = ? AND fecha >= ?
            ORDER BY fecha ASC
        """
        df = pd.read_sql_query(query, conn, params=(id_variable, id_pais, fecha_limite_str))
        if len(df) == 0:
            print(f"[WARN] Serie id_variable={id_variable}, id_pais={id_pais} no tiene datos en los últimos 24 meses")
            continue
        
        df['fecha'] = pd.to_datetime(df['fecha'])
        df = df.rename(columns={'valor': f'valor_{id_variable}'})
        dfs.append(df)
        print(f"[OK] Serie id_variable={id_variable}, id_pais={id_pais}: {len(df)} registros (últimos 24 meses)")
    
    conn.close()
    
    if not dfs:
        raise ValueError("No se encontraron datos en ninguna serie fuente (últimos 24 meses)")
    
    # Combinar todas las series por fecha
    df_combinado = dfs[0]
    for df in dfs[1:]:
        df_combinado = pd.merge(df_combinado, df, on='fecha', how='outer')
    
    # Ordenar por fecha
    df_combinado = df_combinado.sort_values('fecha').reset_index(drop=True)
    
    print(f"[OK] Series combinadas: {len(df_combinado)} fechas únicas (últimos 24 meses)")
    return df_combinado


def calcular_promedio_mensual(df_combinado: pd.DataFrame) -> pd.DataFrame:
    """
    Calcula el promedio mensual de las 4 series fuente.
    Solo incluye fechas donde hay al menos una serie disponible.
    """
    print("\n[INFO] Calculando promedio mensual...")
    
    # Obtener columnas de valores
    columnas_valores = [col for col in df_combinado.columns if col.startswith('valor_')]
    
    if not columnas_valores:
        raise ValueError("No se encontraron columnas de valores")
    
    # Calcular promedio de las columnas disponibles (ignorando NaN)
    df_combinado['promedio'] = df_combinado[columnas_valores].mean(axis=1, skipna=True)
    
    # Filtrar solo filas donde hay al menos un valor
    df_resultado = df_combinado[df_combinado['promedio'].notna()].copy()
    
    # Seleccionar solo fecha y promedio
    df_resultado = df_resultado[['fecha', 'promedio']].copy()
    df_resultado = df_resultado.rename(columns={'promedio': 'valor', 'fecha': 'FECHA'})
    df_resultado = df_resultado.rename(columns={'valor': 'VALOR'})
    
    # Mostrar estadísticas de cobertura
    print(f"[INFO] Cobertura por serie:")
    for col in columnas_valores:
        id_variable = col.replace('valor_', '')
        count = df_combinado[col].notna().sum()
        print(f"   Serie id_variable={id_variable}: {count} valores disponibles")
    
    print(f"[OK] Promedio calculado: {len(df_resultado)} registros")
    return df_resultado[['FECHA', 'VALOR']]


def main():
    print("=" * 60)
    print("ACTUALIZACION DE DATOS: SERVICIOS NO TRADICIONALES - SIN SOFTWARE")
    print("=" * 60)
    print("Calcula el promedio mensual de las series:")
    print("  - Ingeniería (id_variable=8, id_pais=999)")
    print("  - Arquitectura (id_variable=1, id_pais=999)")
    print("  - Contabilidad (id_variable=5, id_pais=999)")
    print("  - Bookkeeping (id_variable=3, id_pais=999)")
    
    # Leer series fuente
    df_combinado = leer_series_fuente()
    
    # Calcular promedio mensual
    df_promedio = calcular_promedio_mensual(df_combinado)
    
    # Mostrar primeros y últimos datos
    print("\n[INFO] Datos del promedio calculado:")
    print("\nPrimeros datos:")
    print(df_promedio.head())
    print("\nÚltimos datos:")
    print(df_promedio.tail())
    
    # Validar fechas
    df_promedio = validar_fechas_solo_nulas(df_promedio)

    # Verificar que ID_VARIABLE e ID_PAIS están configurados
    if ID_VARIABLE is None or ID_PAIS is None:
        print("\n[ERROR] ID_VARIABLE e ID_PAIS deben estar configurados en el script.")
        print("   Consulta maestro_database.xlsx o la base de datos para obtener los valores correctos.")
        return

    print("\n[INFO] Actualizando base de datos...")
    insertar_en_bd_unificado(ID_VARIABLE, ID_PAIS, df_promedio, DB_NAME)


if __name__ == "__main__":
    main()
