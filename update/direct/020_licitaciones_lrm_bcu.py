# -*- coding: utf-8 -*-
"""
Script: licitaciones_lrm_bcu
-----------------------------
Actualiza la base de datos con datos de licitaciones LRM del BCU (Uruguay).

Lee desde Excel: instrumentos_emitidos_bcu_y_gobierno_central.xlsx
Procesa múltiples valores de "Plazo ref." (30, 90, 180, 360)
Para cada plazo, procesa 3 variables:
- Licitación (columna V)
- Adjudicado (columna Z)
- Tasa de corte (columna AA)
"""

import os
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from db.connection import execute_query_single
from _helpers import (
    validar_fechas_solo_nulas,
    insertar_en_bd_unificado
)

# Configuración
DATA_RAW_DIR = "update/historicos"
EXCEL_NAME = "instrumentos_emitidos_bcu_y_gobierno_central.xlsx"
ID_PAIS = 858  # Uruguay

# Configuración por valor de "Plazo ref."
# Mapeo: {plazo_ref: {variable: id_variable}}
PLAZO_CONFIG = {
    30: {
        "Licitación": {"columna": "V", "columna_excel": 21, "id_variable": 33},
        "Adjudicado": {"columna": "Z", "columna_excel": 25, "id_variable": 29},
        "Tasa de corte": {"columna": "AA", "columna_excel": 26, "id_variable": 25}
    },
    90: {
        "Licitación": {"columna": "V", "columna_excel": 21, "id_variable": 34},
        "Adjudicado": {"columna": "Z", "columna_excel": 25, "id_variable": 30},
        "Tasa de corte": {"columna": "AA", "columna_excel": 26, "id_variable": 26}
    },
    180: {
        "Licitación": {"columna": "V", "columna_excel": 21, "id_variable": 35},
        "Adjudicado": {"columna": "Z", "columna_excel": 25, "id_variable": 31},
        "Tasa de corte": {"columna": "AA", "columna_excel": 26, "id_variable": 27}
    },
    360: {
        "Licitación": {"columna": "V", "columna_excel": 21, "id_variable": 36},
        "Adjudicado": {"columna": "Z", "columna_excel": 25, "id_variable": 32},
        "Tasa de corte": {"columna": "AA", "columna_excel": 26, "id_variable": 28}
    }
}


def leer_excel_lrm():
    """
    Lee el Excel desde data_raw y retorna el DataFrame completo.
    
    Returns:
        DataFrame con los datos de la hoja LRM
    """
    base_dir = os.getcwd()
    ruta_excel = os.path.join(base_dir, DATA_RAW_DIR, EXCEL_NAME)
    
    if not os.path.exists(ruta_excel):
        raise FileNotFoundError(
            f"No se encontró el archivo: {ruta_excel}. "
            "Ejecutá primero el script de descarga."
        )
    
    print(f"\n[INFO] Leyendo Excel desde: {ruta_excel}")
    
    # Leer Excel desde la hoja "LRM" con header en fila 10 (skiprows=9)
    df = pd.read_excel(
        ruta_excel,
        sheet_name='LRM',
        skiprows=9,
        header=0,
    )
    
    print(f"[OK] Excel leído: {len(df)} filas, {len(df.columns)} columnas")
    
    return df


def verificar_registro_maestro(id_variable: int, id_pais: int, var_nombre: str, plazo_valor: int):
    """
    Verifica que existe un registro en la tabla maestro.
    
    Args:
        id_variable: ID de la variable
        id_pais: ID del país
        var_nombre: Nombre de la variable (para logging)
        plazo_valor: Valor del plazo (para el nombre)
    
    Returns:
        True si existe, False si no existe
    """
    try:
        row = execute_query_single(
            "SELECT id_variable, id_pais FROM maestro WHERE id_variable = ? AND id_pais = ?",
            (id_variable, id_pais),
        )
        if row:
            return True

        print(f"    [ERROR] No existe registro en 'maestro' para id_variable={id_variable}, id_pais={id_pais}")
        print(f"    [ERROR] Variable: {var_nombre} (plazo {plazo_valor}d)")
        return False
    except Exception as e:
        print(f"    [ERROR] Error al verificar registro en maestro: {e}")
        return False


def procesar_variable(df_plazo: pd.DataFrame, var_config: dict, var_nombre: str, plazo_valor: int):
    """
    Procesa una variable específica y la inserta en la base de datos.
    
    Args:
        df_plazo: DataFrame filtrado por un valor de "Plazo ref."
        var_config: Configuración de la variable (columna, id_variable)
        var_nombre: Nombre de la variable
        plazo_valor: Valor del plazo ref. para logging
        
    Returns:
        Tupla (exito: bool, registros: int)
    """
    print(f"\n  - Procesando: {var_nombre} (id_variable={var_config['id_variable']})")
    
    col_idx = var_config['columna_excel']
    col_name = df_plazo.columns[col_idx]
    
    # Crear DataFrame con fecha y valor
    df_var = pd.DataFrame({
        'FECHA': df_plazo['FECHA'],
        'VALOR': df_plazo[col_name]
    })
    
    # Convertir valor a numérico
    df_var['VALOR'] = pd.to_numeric(df_var['VALOR'], errors='coerce')
    
    # Eliminar filas con valores nulos
    df_var = df_var.dropna(subset=['VALOR'])
    
    if len(df_var) == 0:
        print(f"    [WARN] No hay datos válidos para {var_nombre}")
        return False, 0
    
    # Convertir tasa de corte de decimal a porcentaje (0.07 -> 7)
    if var_nombre == "Tasa de corte":
        df_var['VALOR'] = df_var['VALOR'] * 100
        print(f"    [INFO] Convertido de decimal a porcentaje (multiplicado por 100)")
    
    print(f"    [OK] {len(df_var)} registros válidos")
    
    # Validar fechas
    df_var = validar_fechas_solo_nulas(df_var)
    
    # Verificar que existe registro en maestro
    if not verificar_registro_maestro(
        var_config['id_variable'],
        ID_PAIS,
        var_nombre,
        plazo_valor
    ):
        return False, len(df_var)
    
    # Insertar en BD
    print(f"    [INFO] Insertando en base de datos...")
    try:
        insertar_en_bd_unificado(
            var_config['id_variable'],
            ID_PAIS,
            df_var
        )
        return True, len(df_var)
    except Exception as e:
        print(f"    [ERROR] Error al insertar: {e}")
        return False, len(df_var)


def main():
    print("=" * 60)
    print("ACTUALIZACION DE DATOS: LICITACIONES LRM BCU")
    print("=" * 60)
    
    try:
        # Leer Excel
        df = leer_excel_lrm()
        
        # Identificar columnas
        fecha_col = df.columns[0]  # Columna A
        plazo_col = df.columns[5]  # Columna F (Plazo ref.)
        
        print(f"\n[INFO] Columna de fecha: {fecha_col}")
        print(f"[INFO] Columna de plazo: {plazo_col}")
        
        # Procesar cada valor de plazo
        resultados = {}
        total_registros = 0
        
        for plazo_valor in sorted(PLAZO_CONFIG.keys()):
            print(f"\n{'='*60}")
            print(f"PROCESANDO PLAZO REF. = {plazo_valor}")
            print(f"{'='*60}")
            
            # Filtrar por este valor de plazo
            df_plazo = df[df[plazo_col] == plazo_valor].copy()
            
            print(f"[OK] Registros encontrados: {len(df_plazo)}")
            
            if len(df_plazo) == 0:
                print(f"[WARN] No hay registros para Plazo ref. = {plazo_valor}")
                continue
            
            # Preparar fecha
            df_plazo['FECHA'] = pd.to_datetime(df_plazo[fecha_col], errors='coerce')
            df_plazo = df_plazo.dropna(subset=['FECHA'])
            
            if df_plazo['FECHA'].dtype == "datetime64[ns]":
                df_plazo['FECHA'] = df_plazo['FECHA'].dt.date
            
            print(f"[OK] Fechas procesadas: {len(df_plazo)} registros")
            if len(df_plazo) > 0:
                print(f"   Rango: {df_plazo['FECHA'].min()} a {df_plazo['FECHA'].max()}")
            
            # Procesar cada variable para este plazo
            config_plazo = PLAZO_CONFIG[plazo_valor]
            exito_plazo = {}
            
            for var_nombre, var_config in config_plazo.items():
                exito, registros = procesar_variable(df_plazo, var_config, var_nombre, plazo_valor)
                exito_plazo[var_nombre] = {'exito': exito, 'registros': registros}
                if exito:
                    total_registros += registros
            
            resultados[plazo_valor] = exito_plazo
        
        # Resumen
        print("\n" + "=" * 60)
        print("RESUMEN")
        print("=" * 60)
        
        total_exitosos = 0
        total_fallidos = 0
        
        for plazo_valor, exito_plazo in resultados.items():
            exitosos = sum(1 for info in exito_plazo.values() if info['exito'])
            fallidos = len(exito_plazo) - exitosos
            total_exitosos += exitosos
            total_fallidos += fallidos
            
            print(f"\nPlazo ref. = {plazo_valor}:")
            for var_nombre, info in exito_plazo.items():
                estado = "OK" if info['exito'] else "ERROR"
                registros = info['registros']
                print(f"  [{estado}] {var_nombre} ({registros} registros)")
        
        print(f"\nTotal: {total_exitosos} variables procesadas exitosamente, {total_fallidos} fallidas")
        print(f"Total de registros procesados: {total_registros}")
        
    except Exception as e:
        print(f"\n[ERROR] Error en el proceso: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
