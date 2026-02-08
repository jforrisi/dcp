# -*- coding: utf-8 -*-
"""
Script: tasa_pm_multipais_inicial
----------------------------------
Carga inicial de datos de Tasa de Política Monetaria (PM) para múltiples países
desde el Banco Central de Chile (BCCH), usando su API oficial (bcchapi).

Este script:
1. Crea registros en maestro para id_variable=52 con periodicidad diaria
2. Carga datos históricos desde 2010-01-01 hasta hoy
3. Inserta los datos en maestro_precios

Países incluidos:
- Alemania, Argentina, Australia, Brasil, Canadá, Chile, China, Colombia,
  Estados Unidos, Filipinas, Francia, India, Indonesia, Japón, Malasia,
  México, Nueva Zelanda, Perú, Polonia, Reino Unido, República Checa,
  Rusia, Tailandia, Turquía, Zona Euro
"""

import os
import sys
import sqlite3
from datetime import datetime
from pathlib import Path

import pandas as pd
from bcchapi import Siete

# Asegurar que podemos importar _helpers
script_dir = Path(__file__).parent
if str(script_dir) not in sys.path:
    sys.path.insert(0, str(script_dir))

from _helpers import (
    validar_fechas_solo_nulas,
    insertar_en_bd_unificado
)

# Configuración de base de datos
DB_NAME = "series_tiempo.db"

# Credenciales del BCCH (desde 017_ipc_multipais.py)
BCCH_USER = "joaquin.forrisi@gmail.com"
BCCH_PASSWORD = "Joaquin.13"

# Configuración de países y códigos BCCH
# id_pais obtenidos de la base de datos
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
PERIODICIDAD = "D"  # Diaria
FUENTE = "BCCH"


def obtener_id_pais_por_nombre(conn, nombre_pais: str) -> int:
    """Busca el id_pais por nombre en la tabla pais_grupo."""
    cursor = conn.cursor()
    # Buscar por nombre (case insensitive, parcial)
    cursor.execute("""
        SELECT id_pais FROM pais_grupo 
        WHERE nombre_pais_grupo LIKE ? 
        LIMIT 1
    """, (f"%{nombre_pais}%",))
    result = cursor.fetchone()
    if result:
        return result[0]
    return None


def crear_registros_maestro():
    """Crea registros en maestro para todos los países configurados."""
    print("\n" + "=" * 60)
    print("CREANDO REGISTROS EN MAESTRO")
    print("=" * 60)
    
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    registros_creados = 0
    registros_omitidos = 0
    errores = []
    
    for pais_config in PAISES_CONFIG:
        nombre_pais = pais_config["nombre"]
        id_pais = pais_config["id_pais"]
        
        # Si no tiene id_pais, intentar buscarlo por nombre
        if id_pais is None:
            id_pais = obtener_id_pais_por_nombre(conn, nombre_pais)
            if id_pais is None:
                print(f"[ERROR] No se encontró id_pais para {nombre_pais}")
                errores.append(nombre_pais)
                continue
            print(f"[INFO] {nombre_pais}: id_pais encontrado = {id_pais}")
        
        # Verificar si ya existe
        cursor.execute("""
            SELECT id_variable, id_pais FROM maestro 
            WHERE id_variable = ? AND id_pais = ?
        """, (ID_VARIABLE, id_pais))
        if cursor.fetchone():
            print(f"[SKIP] Registro maestro ya existe: {nombre_pais} (id_pais={id_pais})")
            registros_omitidos += 1
            continue
        
        # Crear registro maestro
        try:
            cursor.execute("""
                INSERT INTO maestro (
                    id_variable, id_pais, periodicidad, fuente, activo
                ) VALUES (?, ?, ?, ?, ?)
            """, (ID_VARIABLE, id_pais, PERIODICIDAD, FUENTE, 1))
            print(f"[OK] Registro maestro creado: {nombre_pais} (id_pais={id_pais})")
            registros_creados += 1
        except sqlite3.IntegrityError as e:
            print(f"[ERROR] Error al crear registro maestro para {nombre_pais}: {e}")
            errores.append(nombre_pais)
            registros_omitidos += 1
    
    conn.commit()
    conn.close()
    
    print(f"\n[RESUMEN MAESTRO]")
    print(f"  Registros creados: {registros_creados}")
    print(f"  Registros omitidos: {registros_omitidos}")
    if errores:
        print(f"  Países con errores: {', '.join(errores)}")
    
    return registros_creados > 0


def extraer_tasa_pm_bcch(codigo_serie: str, nombre_pais: str, fecha_inicio: str = "2010-01-01", fecha_fin: str = None):
    """
    Extrae datos de Tasa PM desde el BCCH usando bcchapi.
    
    Args:
        codigo_serie: Código de serie del BCCH
        nombre_pais: Nombre del país para logging
        fecha_inicio: Fecha de inicio en formato YYYY-MM-DD
        fecha_fin: Fecha de fin en formato YYYY-MM-DD (por defecto: hoy)
        
    Returns:
        DataFrame con columnas: Fecha, Tasa_PM
    """
    print(f"\n[INFO] Extrayendo Tasa PM de {nombre_pais}...")
    print(f"   Código de serie: {codigo_serie}")
    
    if fecha_fin is None:
        fecha_fin = datetime.today().strftime("%Y-%m-%d")
    
    try:
        # Inicializar conexión con BCCH
        siete = Siete(BCCH_USER, BCCH_PASSWORD)
        
        print(f"   Rango solicitado: {fecha_inicio} a {fecha_fin}")
        
        # Obtener datos (diarios)
        df = siete.cuadro(
            series=[codigo_serie],
            nombres=["tasa_pm"],
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


def procesar_pais(pais_config: dict) -> bool:
    """
    Procesa un país completo: extracción, validación e inserción.
    Retorna True si fue exitoso, False en caso contrario.
    """
    print("\n" + "=" * 60)
    print(f"PROCESANDO: {pais_config['nombre']}")
    print("=" * 60)
    
    try:
        conn = sqlite3.connect(DB_NAME)
        id_pais = pais_config["id_pais"]
        
        # Si no tiene id_pais, intentar buscarlo por nombre
        if id_pais is None:
            id_pais = obtener_id_pais_por_nombre(conn, pais_config["nombre"])
            if id_pais is None:
                print(f"[ERROR] No se encontró id_pais para {pais_config['nombre']}")
                conn.close()
                return False
        
        conn.close()
        
        # Extraer datos
        df = extraer_tasa_pm_bcch(
            codigo_serie=pais_config["codigo"],
            nombre_pais=pais_config["nombre"],
            fecha_inicio="2010-01-01",
            fecha_fin=None
        )
        
        if df is None or df.empty:
            print(f"[ERROR] No se pudieron extraer datos para {pais_config['nombre']}")
            return False
        
        # Renombrar columnas para el helper
        df = df.rename(columns={'Fecha': 'FECHA', 'Tasa_PM': 'VALOR'})
        
        # Validar fechas
        df = validar_fechas_solo_nulas(df)
        
        # Insertar en BD usando helper unificado
        print(f"\n[INFO] Actualizando base de datos para {pais_config['nombre']}...")
        insertar_en_bd_unificado(
            ID_VARIABLE,
            id_pais,
            df,
            DB_NAME
        )
        
        return True
        
    except Exception as e:
        print(f"[ERROR] Error procesando {pais_config['nombre']}: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    print("=" * 60)
    print("CARGA INICIAL: TASA PM MULTIPAIES")
    print("=" * 60)
    
    # Paso 1: Crear registros en maestro
    crear_registros_maestro()
    
    # Paso 2: Procesar cada país
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
