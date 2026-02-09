# -*- coding: utf-8 -*-
"""
Script: tasa_pm_multipais_incremental
--------------------------------------
Actualización incremental de datos de Tasa de Política Monetaria (PM) para múltiples países
desde el Banco Central de Chile (BCCH), usando su API oficial (bcchapi).

Este script:
1. Extrae datos de los últimos 30 días desde el BCCH
2. Inserta/actualiza los datos en maestro_precios usando INSERT OR REPLACE
   (reemplaza datos existentes para las mismas fechas)

Países incluidos:
- Alemania, Argentina, Australia, Brasil, Canadá, Chile, China, Colombia,
  Estados Unidos, Filipinas, Francia, India, Indonesia, Japón, Malasia,
  México, Nueva Zelanda, Perú, Polonia, Reino Unido, República Checa,
  Rusia, Tailandia, Turquía, Zona Euro
"""

import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd
from bcchapi import Siete

# Asegurar que podemos importar _helpers y db
script_dir = Path(__file__).parent
base_dir = Path(__file__).parent.parent.parent
if str(base_dir) not in sys.path:
    sys.path.insert(0, str(base_dir))

from db.connection import execute_query_single, execute_update
from _helpers import validar_fechas_solo_nulas

# Credenciales del BCCH (desde 017_ipc_multipais.py)
BCCH_USER = "joaquin.forrisi@gmail.com"
BCCH_PASSWORD = "Joaquin.13"

# Configuración de países y códigos BCCH
PAISES_CONFIG = [
    {"nombre": "Alemania", "codigo": "F019.TPM.TIN.GE.D", "id_pais": 276},
    {"nombre": "Argentina", "codigo": "F019.TPM.TIN.ARG.D", "id_pais": 32},
    {"nombre": "Australia", "codigo": "F019.TPM.TIN.AU.D", "id_pais": 36},
    {"nombre": "Brasil", "codigo": "F019.TPM.TIN.BRA.D", "id_pais": 76},
    {"nombre": "Canadá", "codigo": "F019.TPM.TIN.CA.D", "id_pais": 124},
    {"nombre": "Chile", "codigo": "F022.TPM.TIN.D001.NO.Z.D", "id_pais": 152},
    {"nombre": "China", "codigo": "F019.TPM.TIN.CHN.D", "id_pais": 156},
    {"nombre": "Colombia", "codigo": "F019.TPM.TIN.COL.D", "id_pais": 170},
    {"nombre": "Estados Unidos", "codigo": "F019.TPM.TIN.10.D", "id_pais": 840},
    {"nombre": "Filipinas", "codigo": "F019.TPM.TIN.PH.D", "id_pais": 608},
    {"nombre": "Francia", "codigo": "F019.TPM.TIN.FR.D", "id_pais": 250},
    {"nombre": "India", "codigo": "F019.TPM.TIN.IN.D", "id_pais": 356},
    {"nombre": "Indonesia", "codigo": "F019.TPM.TIN.ID.D", "id_pais": 360},
    {"nombre": "Japón", "codigo": "F019.TPM.TIN.30.D", "id_pais": 392},
    {"nombre": "Malasia", "codigo": "F019.TPM.TIN.MAL.D", "id_pais": 458},
    {"nombre": "México", "codigo": "F019.TPM.TIN.MEX.D", "id_pais": 484},
    {"nombre": "Nueva Zelanda", "codigo": "F019.TPM.TIN.NZ.D", "id_pais": 554},
    {"nombre": "Perú", "codigo": "F019.TPM.TIN.PER.D", "id_pais": 604},
    {"nombre": "Polonia", "codigo": "F019.TPM.TIN.POL.D", "id_pais": 616},
    {"nombre": "Reino Unido", "codigo": "F019.TPM.TIN.UK.D", "id_pais": 826},
    {"nombre": "República Checa", "codigo": "F019.TPM.TIN.RCH.D", "id_pais": 203},
    {"nombre": "Rusia", "codigo": "F019.TPM.TIN.RUS.D", "id_pais": 643},
    {"nombre": "Tailandia", "codigo": "F019.TPM.TIN.TAI.D", "id_pais": 764},
    {"nombre": "Turquía", "codigo": "F019.TPM.TIN.TUR.D", "id_pais": 792},
    {"nombre": "Zona Euro", "codigo": "F019.TPM.TIN.20.D", "id_pais": 1000},
]

ID_VARIABLE = 52  # Tasa de PM
DIAS_ATRAS = 30  # Días hacia atrás para actualizar


def extraer_tasa_pm_bcch(codigo_serie: str, nombre_pais: str, fecha_inicio: str, fecha_fin: str):
    """
    Extrae datos de Tasa PM desde el BCCH usando bcchapi.
    
    Args:
        codigo_serie: Código de serie del BCCH
        nombre_pais: Nombre del país para logging
        fecha_inicio: Fecha de inicio en formato YYYY-MM-DD
        fecha_fin: Fecha de fin en formato YYYY-MM-DD
        
    Returns:
        DataFrame con columnas: Fecha, Tasa_PM
    """
    print(f"\n[INFO] Extrayendo Tasa PM de {nombre_pais}...")
    print(f"   Código de serie: {codigo_serie}")
    print(f"   Rango solicitado: {fecha_inicio} a {fecha_fin}")
    
    try:
        # Inicializar conexión con BCCH
        siete = Siete(BCCH_USER, BCCH_PASSWORD)
        
        # Obtener datos (diarios)
        df = siete.cuadro(
            series=[codigo_serie],
            nombres=["tasa_pm"],
            desde=fecha_inicio,
            hasta=fecha_fin
        )
        
        if df is None or df.empty:
            print(f"[WARN] No se obtuvieron datos del BCCH para {nombre_pais}")
            return None
        
        print(f"[OK] Se obtuvieron {len(df)} registros del BCCH")
        
        # Preparar DataFrame estándar
        df = df.reset_index()
        
        # Identificar columna de fecha y valor
        if 'index' in df.columns:
            df.rename(columns={'index': 'Fecha'}, inplace=True)
        elif 'Fecha' not in df.columns and len(df.columns) > 0:
            df.columns = ['Fecha'] + list(df.columns[1:])
        
        # Identificar columna de valor
        if 'tasa_pm' in df.columns:
            df['Tasa_PM'] = df['tasa_pm']
        elif len(df.columns) >= 2:
            df['Tasa_PM'] = df.iloc[:, 1]
        
        # Asegurar que tenemos las columnas necesarias
        if 'Fecha' not in df.columns or 'Tasa_PM' not in df.columns:
            print(f"[ERROR] No se pudo identificar las columnas Fecha y Tasa_PM")
            print(f"[DEBUG] Columnas disponibles: {list(df.columns)}")
            return None
        
        # Seleccionar solo las columnas necesarias
        df = df[['Fecha', 'Tasa_PM']].copy()
        
        # Convertir fecha a datetime
        df['Fecha'] = pd.to_datetime(df['Fecha'], errors='coerce')
        df = df.dropna(subset=['Fecha'])
        
        # Convertir valor a numérico y filtrar valores inválidos
        df['Tasa_PM'] = pd.to_numeric(df['Tasa_PM'], errors='coerce')
        df = df.dropna(subset=['Tasa_PM'])
        
        # Eliminar duplicados por fecha (mantener el último)
        df = df.drop_duplicates(subset='Fecha', keep='last')
        
        # Ordenar por fecha
        df = df.sort_values('Fecha').reset_index(drop=True)
        
        print(f"[OK] Se procesaron {len(df)} registros válidos")
        if len(df) > 0:
            print(f"   Rango: {df['Fecha'].min().strftime('%d/%m/%Y')} a {df['Fecha'].max().strftime('%d/%m/%Y')}")
        
        return df
        
    except Exception as e:
        print(f"[ERROR] Error al obtener datos del BCCH para {nombre_pais}: {e}")
        import traceback
        traceback.print_exc()
        return None


def insertar_con_replace(id_variable: int, id_pais: int, df: pd.DataFrame):
    """
    Inserta datos en maestro_precios (insert o update según exista).
    
    Args:
        id_variable: ID de la variable
        id_pais: ID del país
        df: DataFrame con columnas FECHA y VALOR
    """
    print(f"\n[INFO] Actualizando base de datos para id_variable={id_variable}, id_pais={id_pais}...")

    # Verificar que existe registro en maestro
    row = execute_query_single(
        "SELECT id_variable, id_pais FROM maestro WHERE id_variable = ? AND id_pais = ?",
        (id_variable, id_pais),
    )
    if not row:
        print(f"[ERROR] No existe registro en 'maestro' para id_variable={id_variable}, id_pais={id_pais}.")
        return False

    registros_insertados = 0
    registros_actualizados = 0

    try:
        for _, row in df.iterrows():
            fecha = row["FECHA"]
            valor = row["VALOR"]
            fecha_str = fecha.strftime("%Y-%m-%d") if hasattr(fecha, "strftime") else str(fecha)

            existe = execute_query_single(
                "SELECT id FROM maestro_precios WHERE id_variable = ? AND id_pais = ? AND fecha = ?",
                (id_variable, id_pais, fecha_str),
            )

            if existe:
                success, error, _ = execute_update(
                    "UPDATE maestro_precios SET valor = ? WHERE id_variable = ? AND id_pais = ? AND fecha = ?",
                    (valor, id_variable, id_pais, fecha_str),
                )
                if success:
                    registros_actualizados += 1
            else:
                success, error, _ = execute_update(
                    "INSERT INTO maestro_precios (id_variable, id_pais, fecha, valor) VALUES (?, ?, ?, ?)",
                    (id_variable, id_pais, fecha_str, valor),
                )
                if success:
                    registros_insertados += 1

        print(f"[OK] Insertados: {registros_insertados}, Actualizados: {registros_actualizados}")
        return True

    except Exception as e:
        print(f"[ERROR] Error al insertar datos: {e}")
        import traceback
        traceback.print_exc()
        return False


def procesar_pais(pais_config: dict, fecha_inicio: str, fecha_fin: str) -> bool:
    """
    Procesa un país completo: extracción, validación e inserción.
    Retorna True si fue exitoso, False en caso contrario.
    """
    print("\n" + "=" * 60)
    print(f"PROCESANDO: {pais_config['nombre']}")
    print("=" * 60)
    
    try:
        id_pais = pais_config["id_pais"]
        
        # Extraer datos
        df = extraer_tasa_pm_bcch(
            codigo_serie=pais_config["codigo"],
            nombre_pais=pais_config["nombre"],
            fecha_inicio=fecha_inicio,
            fecha_fin=fecha_fin
        )
        
        if df is None or df.empty:
            print(f"[WARN] No se pudieron extraer datos para {pais_config['nombre']}")
            return False
        
        # Renombrar columnas
        df = df.rename(columns={'Fecha': 'FECHA', 'Tasa_PM': 'VALOR'})
        
        # Validar fechas
        df = validar_fechas_solo_nulas(df)
        
        if df.empty:
            print(f"[WARN] No hay datos válidos después de validación para {pais_config['nombre']}")
            return False
        
        # Insertar en BD usando INSERT OR REPLACE
        exito = insertar_con_replace(ID_VARIABLE, id_pais, df)
        
        return exito
        
    except Exception as e:
        print(f"[ERROR] Error procesando {pais_config['nombre']}: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    print("=" * 60)
    print("ACTUALIZACIÓN INCREMENTAL: TASA PM MULTIPAIES")
    print("=" * 60)
    
    # Calcular rango de fechas (últimos 30 días)
    fecha_fin = datetime.today()
    fecha_inicio = fecha_fin - timedelta(days=DIAS_ATRAS)
    
    fecha_inicio_str = fecha_inicio.strftime("%Y-%m-%d")
    fecha_fin_str = fecha_fin.strftime("%Y-%m-%d")
    
    print(f"\n[INFO] Rango de actualización: {fecha_inicio_str} a {fecha_fin_str}")
    print(f"[INFO] Actualizando últimos {DIAS_ATRAS} días para {len(PAISES_CONFIG)} países\n")
    
    # Procesar cada país
    resultados = {}
    for pais_config in PAISES_CONFIG:
        exito = procesar_pais(pais_config, fecha_inicio_str, fecha_fin_str)
        resultados[pais_config["nombre"]] = exito
    
    # Resumen final
    print("\n" + "=" * 60)
    print("RESUMEN FINAL")
    print("=" * 60)
    
    exitosos = sum(1 for exito in resultados.values() if exito)
    fallidos = len(resultados) - exitosos
    
    print(f"\nPaíses procesados exitosamente: {exitosos}")
    print(f"Países con errores o sin datos: {fallidos}")
    
    if fallidos > 0:
        print("\nPaíses con problemas:")
        for nombre, exito in resultados.items():
            if not exito:
                print(f"  - {nombre}")
    
    print("\n" + "=" * 60)


if __name__ == "__main__":
    main()
