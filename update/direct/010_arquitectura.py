"""
Script: arquitectura
--------------------
Actualiza la base de datos con la serie PPI (Producer Price Index) 
para Architectural Services (NAICS 541310) del BLS,
siguiendo el flujo del README:

1) Obtener datos desde la API de BLS v2 (sin registro requerido).
2) Validar fechas.
3) Generar Excel de prueba.
4) Actualizar automáticamente la base de datos.

Serie BLS: PCU541310541310
Descripción: Producer Price Index for Architectural Services
Base: Dec 2000 = 100
Periodicidad: Mensual (M)

NOTA: Usa API v2 sin registro (funciona para rangos de hasta 10 años).
Para obtener datos desde 2010, se hacen múltiples consultas si es necesario.
"""

import os
import sqlite3
import sys
from datetime import datetime

import pandas as pd
import requests

# Configuración de origen de datos
BLS_API_URL_V2 = "https://api.bls.gov/publicAPI/v2/timeseries/data/"
BLS_API_KEY = "f13f1d4aa9b947ca80fa0d8d063ac94f"  # API Key para aumentar límite a 500 consultas/día
BLS_SERIES_ID = "PCU541310541310"
BLS_START_YEAR = 2010
BLS_END_YEAR = datetime.now().year

# Configuración de base de datos
DB_NAME = "series_tiempo.db"
ID_VARIABLE = 1  # id_variable para "Arquitectura" (desde tabla variables)
ID_PAIS = 999  # id_pais (Uruguay, desde tabla pais_grupo)


def obtener_datos_bls_v2():
    """
    Obtiene datos desde la API de BLS v2 con API key y retorna DataFrame con columna FECHA.
    Con API key, el límite diario aumenta de 25 a 500 consultas.
    Retorna DataFrame con columnas: FECHA, VALOR (fechas ya validadas).
    Obtiene datos desde enero 2010 hasta el último disponible.
    """
    print("\n[INFO] Obteniendo datos desde la API de BLS v2 (con API key)...")
    print(f"   Serie: {BLS_SERIES_ID}")
    print(f"   Rango deseado: Enero {BLS_START_YEAR} - {BLS_END_YEAR}")
    
    # Con API key, la API v2 permite hasta 20 años por consulta
    # Dividir en chunks de 20 años si es necesario
    todos_registros = []
    
    año_inicio = BLS_START_YEAR
    while año_inicio <= BLS_END_YEAR:
        año_fin = min(año_inicio + 19, BLS_END_YEAR)  # Máximo 20 años (inclusive)
        
        print(f"\n[INFO] Consultando años {año_inicio} - {año_fin}...")
        
        # Preparar request a la API v2 (POST request) con API key
        payload = {
            "seriesid": [BLS_SERIES_ID],
            "startyear": str(año_inicio),
            "endyear": str(año_fin),
            "registrationkey": BLS_API_KEY
        }
        
        try:
            response = requests.post(
                BLS_API_URL_V2,
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=30
            )
            response.raise_for_status()
            
            data = response.json()
            
            # Verificar si hay errores en la respuesta
            if data.get("status") != "REQUEST_SUCCEEDED":
                error_msg = data.get("message", ["Error desconocido"])
                raise ValueError(f"Error en API BLS: {error_msg}")
            
            # Extraer datos de la serie
            series_data = data.get("Results", {}).get("series", [])
            if not series_data:
                print(f"[WARN] No se encontraron datos para años {año_inicio} - {año_fin}")
                año_inicio = año_fin + 1
                continue
            
            # Procesar los datos
            for serie in series_data:
                for dato in serie.get("data", []):
                    año = int(dato.get("year"))
                    periodo = dato.get("period")  # Formato: M01, M02, ..., M12
                    valor_str = dato.get("value")
                    
                    # Parsear periodo (M01 -> 1, M02 -> 2, etc.)
                    if periodo and periodo.startswith("M"):
                        mes = int(periodo[1:])
                        if 1 <= mes <= 12:
                            # Convertir valor a float
                            try:
                                valor = float(valor_str) if valor_str != "" else None
                                if valor is not None:
                                    # Filtrar: solo desde enero 2010 en adelante
                                    if año > BLS_START_YEAR or (año == BLS_START_YEAR and mes >= 1):
                                        todos_registros.append({
                                            "AÑO": año,
                                            "MES": mes,
                                            "VALOR": valor
                                        })
                            except (ValueError, TypeError):
                                continue
            
            print(f"[OK] Obtenidos datos para años {año_inicio} - {año_fin}")
            
            # Avanzar al siguiente chunk
            año_inicio = año_fin + 1
            
        except requests.exceptions.RequestException as e:
            raise Exception(f"Error al conectar con la API de BLS: {e}")
        except Exception as e:
            raise Exception(f"Error al procesar datos de la API: {e}")
    
    if not todos_registros:
        raise ValueError("No se pudieron extraer datos válidos de la API")
    
    df = pd.DataFrame(todos_registros)
    # Eliminar duplicados por si acaso (puede haber solapamiento)
    df = df.drop_duplicates(subset=["AÑO", "MES"])
    # Filtrar explícitamente desde enero 2010
    df = df[(df["AÑO"] > BLS_START_YEAR) | ((df["AÑO"] == BLS_START_YEAR) & (df["MES"] >= 1))]
    # Ordenar por año y mes
    df = df.sort_values(["AÑO", "MES"]).reset_index(drop=True)
    
    print(f"\n[OK] Total obtenidos: {len(df)} registros válidos desde Enero {BLS_START_YEAR}")
    
    # ===== UNIFICADO: Combinar año y mes para crear fechas =====
    print("\n[INFO] Combinando año y mes para crear fechas...")
    fechas = []
    fechas_invalidas = []
    
    for idx, row in df.iterrows():
        año = row["AÑO"]
        mes = row["MES"]
        
        try:
            año_int = int(año)
            mes_int = int(mes)
            
            if not (1900 <= año_int <= 2100):
                fechas_invalidas.append((idx, año, mes, "Año fuera de rango"))
                continue
            
            if not (1 <= mes_int <= 12):
                fechas_invalidas.append((idx, año, mes, "Mes fuera de rango (1-12)"))
                continue
            
            # Crear fecha (primer día del mes)
            fecha = pd.Timestamp(year=año_int, month=mes_int, day=1)
            fechas.append(fecha)
            
        except Exception as exc:
            fechas_invalidas.append((idx, año, mes, str(exc)))
    
    if fechas_invalidas:
        print(f"[ERROR] Se encontraron {len(fechas_invalidas)} fechas inválidas:")
        for idx, año, mes, motivo in fechas_invalidas[:10]:
            print(f"   Fila {idx}: Año={año}, Mes={mes} - {motivo}")
        if len(fechas_invalidas) > 10:
            print(f"   ... y {len(fechas_invalidas) - 10} más")
        raise ValueError("Hay fechas inválidas. No se puede continuar.")
    
    df["FECHA"] = fechas
    print(f"[OK] {len(fechas)} fechas creadas correctamente")
    
    # ===== UNIFICADO: Validar fechas =====
    print("\n[INFO] Validando fechas...")
    fechas_nulas = df["FECHA"].isna().sum()
    
    if fechas_nulas > 0:
        print(f"[ERROR] Se encontraron {fechas_nulas} fechas nulas")
        raise ValueError("Hay fechas nulas. No se puede continuar.")
    
    # Verificar que la primera fecha sea enero 2010
    primera_fecha = df["FECHA"].min()
    if primera_fecha.year != BLS_START_YEAR or primera_fecha.month != 1:
        print(f"[WARN] La primera fecha es {primera_fecha}, se esperaba Enero {BLS_START_YEAR}")
    
    print(f"[OK] Todas las {len(df)} fechas son válidas")
    print(f"   Rango: {df['FECHA'].min()} a {df['FECHA'].max()}")
    
    # Retornar solo columnas necesarias: FECHA y VALOR
    df = df[["FECHA", "VALOR"]].copy()
    return df


def preparar_datos_maestro_precios(df_ppi: pd.DataFrame, id_variable: int, id_pais: int) -> pd.DataFrame:
    """Prepara el DataFrame para maestro_precios."""
    df_precios = df_ppi.copy()
    df_precios["id_variable"] = id_variable
    df_precios["id_pais"] = id_pais
    df_precios = df_precios[["id_variable", "id_pais", "FECHA", "VALOR"]]
    df_precios.columns = ["id_variable", "id_pais", "fecha", "valor"]
    
    # Asegurar que valor sea numérico
    df_precios["valor"] = pd.to_numeric(df_precios["valor"], errors="coerce")
    
    # Eliminar filas con valor nulo
    df_precios = df_precios.dropna(subset=["valor"])
    return df_precios


def insertar_en_bd(id_variable: int, id_pais: int, df_precios: pd.DataFrame) -> None:
    """Inserta los datos en la base de datos SQLite.
    
    Args:
        id_variable: ID de la variable (FK a tabla variables)
        id_pais: ID del país (FK a tabla pais_grupo)
        df_precios: DataFrame con columnas FECHA y VALOR (o ya con id_variable, id_pais, fecha, valor)
    """
    print("\n[INFO] Insertando datos en la base de datos...")
    print(f"[INFO] Usando id_variable={id_variable}, id_pais={id_pais}")

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    try:
        # Verificar que id_variable e id_pais existen en sus tablas de referencia
        cursor.execute("SELECT id_variable FROM variables WHERE id_variable = ?", (id_variable,))
        if not cursor.fetchone():
            print(f"[ERROR] id_variable={id_variable} no existe en la tabla 'variables'.")
            return
        
        cursor.execute("SELECT id_pais FROM pais_grupo WHERE id_pais = ?", (id_pais,))
        if not cursor.fetchone():
            print(f"[ERROR] id_pais={id_pais} no existe en la tabla 'pais_grupo'.")
            return

        # Preparar datos con FKs si no están ya preparados
        if "id_variable" not in df_precios.columns or "id_pais" not in df_precios.columns:
            df_precios = preparar_datos_maestro_precios(df_precios, id_variable, id_pais)

        # Eliminar registros existentes para esta id_variable y id_pais para evitar duplicados
        cursor.execute(
            """
            DELETE FROM maestro_precios WHERE id_variable = ? AND id_pais = ?
            """,
            (id_variable, id_pais)
        )
        registros_eliminados = cursor.rowcount
        if registros_eliminados > 0:
            print(f"[INFO] Se eliminaron {registros_eliminados} registros antiguos de 'maestro_precios' para id_variable={id_variable}, id_pais={id_pais}")

        # Insertar todos los precios nuevos
        if not df_precios.empty:
            print(f"[INFO] Insertando {len(df_precios)} registros en 'maestro_precios'...")
            df_precios.to_sql("maestro_precios", conn, if_exists="append", index=False)
            print(f"[OK] Insertados {len(df_precios)} registro(s) en tabla 'maestro_precios'")
        else:
            print(f"[WARN] No hay datos para insertar en maestro_precios")

        conn.commit()
        print(f"\n[OK] Datos insertados exitosamente en '{DB_NAME}'")
    except Exception as exc:
        conn.rollback()
        print(f"[ERROR] Error al insertar datos: {exc}")
        raise
    finally:
        conn.close()


def main():
    print("=" * 60)
    print("ACTUALIZACION DE DATOS: ARQUITECTURA (BLS)")
    print("=" * 60)

    # Obtener datos desde API (ya con FECHA creada y validada)
    df_precios = obtener_datos_bls_v2()
    
    # Mostrar primeros y últimos datos
    print("\n[INFO] Datos obtenidos:")
    print("\nPrimeros datos:")
    print(df_precios.head())
    print("\nÚltimos datos:")
    print(df_precios.tail())

    # Insertar en base de datos
    if ID_VARIABLE is None or ID_PAIS is None:
        print("\n[ERROR] ID_VARIABLE e ID_PAIS deben estar configurados en el script.")
        print("   Consulta maestro_database.xlsx o la base de datos para obtener los valores correctos.")
        return
    
    print("\n[INFO] Actualizando base de datos...")
    insertar_en_bd(ID_VARIABLE, ID_PAIS, df_precios)


if __name__ == "__main__":
    main()
