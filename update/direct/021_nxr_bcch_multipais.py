# -*- coding: utf-8 -*-
"""
Script: nxr_bcch_multipais
---------------------------
Actualiza la base de datos con series de tipo de cambio USD de múltiples países
desde el Banco Central de Chile (BCCH), usando su API oficial (bcchapi).

Países incluidos:
- México (F072.MXN.USD.N.O.D)
- Colombia (F072.COP.USD.N.O.D)
- Australia (F072.AUD.USD.N.O.D)
- Nueva Zelanda (F072.NZD.USD.N.O.D)
- Sudáfrica (F072.ZAR.USD.N.O.D)
- Paraguay (F072.PYG.USD.N.O.D)
- Argentina oficial (F072.ARS.USD.N.O.D)

1) Extraer datos desde API del BCCH usando bcchapi (desde 2010-01-01).
2) Filtrar valores no numéricos.
3) Completar días faltantes (forward fill).
4) Validar fechas.
5) Actualizar automáticamente la base de datos.
"""

import os
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd
from bcchapi import Siete

# Asegurar que podemos importar _helpers
script_dir = Path(__file__).parent
if str(script_dir) not in sys.path:
    sys.path.insert(0, str(script_dir))

from _helpers import (
    completar_dias_faltantes,
    validar_fechas_solo_nulas,
    insertar_en_bd_unificado
)


# Configuración de base de datos

# Credenciales del BCCH
BCCH_USER = "joaquin.forrisi@gmail.com"
BCCH_PASSWORD = "Joaquin.13"

# Configuración de países
# NOTA: id_variable e id_pais configurados desde maestro_database.xlsx Sheet1_old
# Si algún país no está en el Excel, configurar manualmente
PAISES_CONFIG = [
    {
        "codigo_serie": "F072.MXN.USD.N.O.D",
        "id_variable": 20,  # Tipo de cambio USD (verificar en maestro_database.xlsx)
        "id_pais": 484,  # México (id_pais=484 en tabla pais_grupo de la base de datos)
        "nombre": "Tipo de cambio USD/MXN (México)",
    },
    {
        "codigo_serie": "F072.COP.USD.N.O.D",
        "id_variable": 20,  # Tipo de cambio USD (verificar en maestro_database.xlsx)
        "id_pais": 170,  # Colombia
        "nombre": "Tipo de cambio USD/COP (Colombia)",
    },
    {
        "codigo_serie": "F072.AUD.USD.N.O.D",
        "id_variable": 20,  # Tipo de cambio USD (verificar en maestro_database.xlsx)
        "id_pais": 36,  # Australia
        "nombre": "Tipo de cambio USD/AUD (Australia)",
    },
    {
        "codigo_serie": "F072.NZD.USD.N.O.D",
        "id_variable": 20,  # Tipo de cambio USD (verificar en maestro_database.xlsx)
        "id_pais": 554,  # Nueva Zelanda
        "nombre": "Tipo de cambio USD/NZD (Nueva Zelanda)",
    },
    {
        "codigo_serie": "F072.ZAR.USD.N.O.D",
        "id_variable": 20,  # Tipo de cambio USD (verificar en maestro_database.xlsx)
        "id_pais": 710,  # Sudáfrica
        "nombre": "Tipo de cambio USD/ZAR (Sudáfrica)",
    },
    {
        "codigo_serie": "F072.PYG.USD.N.O.D",
        "id_variable": 20,  # Tipo de cambio USD (verificar en maestro_database.xlsx)
        "id_pais": 600,  # Paraguay
        "nombre": "Tipo de cambio USD/PYG (Paraguay)",
    },
    {
        "codigo_serie": "F072.ARS.USD.N.O.D",
        "id_variable": 20,  # Tipo de cambio USD Argentina (verificar en maestro_database.xlsx)
        "id_pais": 32,  # Argentina (id_pais=32 en tabla pais_grupo de la base de datos)
        "nombre": "Tipo de cambio USD/ARS (Argentina - Oficial)",
    },
]

def extraer_bcch_pais(codigo_serie: str, nombre_pais: str, fecha_inicio: str = "2010-01-01", fecha_fin: str = None):
    """
    Extrae datos de tipo de cambio de un país desde el BCCH usando bcchapi.
    
    Args:
        codigo_serie: Código de serie del BCCH (ej: "F072.MXN.USD.N.O.D")
        nombre_pais: Nombre del país para logging
        fecha_inicio: Fecha de inicio en formato YYYY-MM-DD
        fecha_fin: Fecha de fin en formato YYYY-MM-DD (por defecto: hoy)
        
    Returns:
        DataFrame con columnas: Fecha, Tipo_Cambio
    """
    print(f"\n[INFO] Extrayendo datos de {nombre_pais}...")
    print(f"   Código de serie: {codigo_serie}")
    
    if fecha_fin is None:
        fecha_fin = datetime.today().strftime("%Y-%m-%d")
    
    try:
        # Inicializar conexión con BCCH
        siete = Siete(BCCH_USER, BCCH_PASSWORD)
        
        print(f"[INFO] Rango solicitado: {fecha_inicio} a {fecha_fin}")
        
        # Obtener datos
        df = siete.cuadro(
            series=[codigo_serie],
            nombres=["tipo_cambio"],
            desde=fecha_inicio,
            hasta=fecha_fin
        )
        
        if df is None or df.empty:
            print(f"[ERROR] No se obtuvieron datos del BCCH para {nombre_pais}")
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
        if 'tipo_cambio' in df.columns:
            df['Tipo_Cambio'] = df['tipo_cambio']
        elif len(df.columns) >= 2:
            df['Tipo_Cambio'] = df.iloc[:, 1]
        
        # Asegurar que tenemos las columnas necesarias
        if 'Fecha' not in df.columns or 'Tipo_Cambio' not in df.columns:
            print(f"[ERROR] No se pudo identificar las columnas Fecha y Tipo_Cambio")
            print(f"[DEBUG] Columnas disponibles: {list(df.columns)}")
            return None
        
        # Seleccionar solo las columnas necesarias
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
        print(f"[ERROR] Error al obtener datos del BCCH para {nombre_pais}: {e}")
        import traceback
        traceback.print_exc()
        return None

def procesar_pais(pais_config: dict) -> bool:
    """
    Procesa un país completo: extrae, valida e inserta datos.
    
    Args:
        pais_config: Diccionario con configuración del país
        
    Returns:
        True si fue exitoso, False en caso contrario
    """
    try:
        # Verificar que id_variable e id_pais están configurados
        if pais_config.get("id_variable") is None or pais_config.get("id_pais") is None:
            print(f"[ERROR] {pais_config['nombre']}: id_variable e id_pais deben estar configurados.")
            return False
        
        # Extraer datos
        df = extraer_bcch_pais(
            codigo_serie=pais_config["codigo_serie"],
            nombre_pais=pais_config["nombre"],
            fecha_inicio="2010-01-01",
            fecha_fin=None
        )
        
        if df is None or df.empty:
            print(f"[ERROR] No se pudieron extraer datos para {pais_config['nombre']}")
            return False
        
        # Completar días faltantes y solo lunes a viernes
        df = completar_dias_faltantes(
            df, columna_fecha='Fecha', columna_valor='Tipo_Cambio', solo_lunes_a_viernes=True
        )
        
        # Renombrar columnas para el helper
        df = df.rename(columns={'Fecha': 'FECHA', 'Tipo_Cambio': 'VALOR'})
        
        # Validar fechas
        df = validar_fechas_solo_nulas(df)
        
        # Insertar en BD usando helper unificado
        print(f"\n[INFO] Actualizando base de datos para {pais_config['nombre']}...")
        insertar_en_bd_unificado(
            pais_config["id_variable"],
            pais_config["id_pais"],
            df
        )
        
        return True
        
    except Exception as e:
        print(f"[ERROR] Error procesando {pais_config['nombre']}: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    print("=" * 60)
    print("ACTUALIZACION DE DATOS: TIPOS DE CAMBIO MULTIPAIES (BCCH)")
    print("=" * 60)
    
    # Procesar cada país
    resultados = {}
    for pais_config in PAISES_CONFIG:
        exito = procesar_pais(pais_config)
        resultados[pais_config["nombre"]] = exito
    
    # Resumen final
    print("\n" + "=" * 60)
    print("RESUMEN FINAL")
    print("=" * 60)
    
    exitosos = sum(1 for exito in resultados.values() if exito)
    fallidos = len(resultados) - exitosos
    
    print(f"\nPaíses procesados exitosamente: {exitosos}")
    print(f"Países con errores: {fallidos}")
    
    if fallidos > 0:
        print("\nPaíses con errores:")
        for nombre, exito in resultados.items():
            if not exito:
                print(f"  - {nombre}")
    
    print("\n" + "=" * 60)

if __name__ == "__main__":
    main()
