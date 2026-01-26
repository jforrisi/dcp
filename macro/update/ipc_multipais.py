# -*- coding: utf-8 -*-
"""
Script: ipc_multipais
---------------------
Actualiza la base de datos con series de IPC (Índice de Precios al Consumidor) mensual
de múltiples países desde sus APIs oficiales.

Países incluidos:
- Chile (F074.IPC.IND.Z.EP23.C.M) - BCCH API
- Brasil (IPCA código 433) - BCB API
- México (INPC código SP1) - Banxico SIE API
- Perú (PN38705PM) - BCRP HTML (pd.read_html)

1) Extraer datos desde APIs oficiales (desde 2010-01-01).
2) Filtrar valores no numéricos.
3) Validar fechas mensuales.
4) Insertar directamente en SQLite (sin Excel de prueba).
"""

import os
import sqlite3
import sys
from datetime import datetime
import re

import pandas as pd
import requests
from bcchapi import Siete

# Configuración de base de datos
DB_NAME = "series_tiempo.db"

# Credenciales del BCCH
BCCH_USER = "joaquin.forrisi@gmail.com"
BCCH_PASSWORD = "Joaquin.13"

# Token de Banxico (México)
BANXICO_TOKEN = "eb42b7168baa77063b964ad9e2501a29b6c4d7ba9c67d7f417098725555aa1eb"

# Configuración de países
PAISES_CONFIG = [
    {
        "api_type": "BCCH",
        "codigo_serie": "F074.IPC.IND.Z.EP23.C.M",
        "id": 33,
        "nombre": "IPC - Chile",
        "unidad": "Índice",
        "fuente": "BCCH_API"
    },
    {
        "api_type": "BCB",
        "codigo_serie": "433",
        "id": 34,
        "nombre": "IPC - Brasil (IPCA)",
        "unidad": "Índice",
        "fuente": "BCB_API"
    },
    {
        "api_type": "BANXICO",
        "codigo_serie": "SP1",
        "id": 35,
        "nombre": "IPC - México (INPC)",
        "unidad": "Índice",
        "fuente": "BANXICO_API"
    },
    {
        "api_type": "BCRP",
        "codigo_serie": "PN38705PM",
        "id": 36,
        "nombre": "IPC - Perú",
        "unidad": "Índice",
        "fuente": "BCRP_HTML"
    },
]


def crear_base_datos():
    """Crea la base de datos SQLite y las tablas según el esquema del README."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS maestro (
            id INTEGER PRIMARY KEY,
            nombre VARCHAR(255) NOT NULL,
            tipo CHAR(1) NOT NULL CHECK (tipo IN ('P', 'S', 'M')),
            fuente VARCHAR(255) NOT NULL,
            periodicidad CHAR(1) NOT NULL CHECK (periodicidad IN ('D', 'W', 'M')),
            unidad VARCHAR(100),
            categoria VARCHAR(255),
            activo BOOLEAN NOT NULL DEFAULT 1
        )
        """
    )

    # Agregar columnas adicionales si no existen
    try:
        cursor.execute("ALTER TABLE maestro ADD COLUMN es_cotizacion INTEGER DEFAULT 0")
    except sqlite3.OperationalError:
        pass  # Columna ya existe

    try:
        cursor.execute("ALTER TABLE maestro ADD COLUMN nominal_real VARCHAR(1)")
    except sqlite3.OperationalError:
        pass  # Columna ya existe

    try:
        cursor.execute("ALTER TABLE maestro ADD COLUMN moneda VARCHAR(10)")
    except sqlite3.OperationalError:
        pass  # Columna ya existe

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS maestro_precios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            maestro_id INTEGER NOT NULL,
            fecha DATE NOT NULL,
            valor NUMERIC(18, 6) NOT NULL,
            FOREIGN KEY (maestro_id) REFERENCES maestro(id)
        )
        """
    )

    cursor.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_maestro_precios_maestro_id
        ON maestro_precios (maestro_id)
        """
    )
    cursor.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_maestro_precios_fecha
        ON maestro_precios (fecha)
        """
    )
    cursor.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_maestro_precios_maestro_fecha
        ON maestro_precios (maestro_id, fecha)
        """
    )

    conn.commit()
    conn.close()
    print(f"[OK] Base de datos '{DB_NAME}' creada/verificada con exito")


def extraer_ipc_chile(fecha_inicio: str = "2010-01-01", fecha_fin: str = None):
    """
    Extrae datos de IPC de Chile desde el BCCH usando bcchapi.
    
    Args:
        fecha_inicio: Fecha de inicio en formato YYYY-MM-DD
        fecha_fin: Fecha de fin en formato YYYY-MM-DD (por defecto: hoy)
        
    Returns:
        DataFrame con columnas: Fecha, IPC
    """
    print(f"\n[INFO] Extrayendo IPC de Chile desde API del BCCH...")
    
    if fecha_fin is None:
        fecha_fin = datetime.today().strftime("%Y-%m-%d")
    
    try:
        # Inicializar conexión con BCCH
        siete = Siete(BCCH_USER, BCCH_PASSWORD)
        
        codigo_serie = "F074.IPC.IND.Z.EP23.C.M"
        print(f"   Código de serie: {codigo_serie}")
        print(f"   Rango solicitado: {fecha_inicio} a {fecha_fin}")
        
        # Obtener datos (mensuales)
        df = siete.cuadro(
            series=[codigo_serie],
            nombres=["ipc"],
            desde=fecha_inicio,
            hasta=fecha_fin
        )
        
        if df is None or df.empty:
            print("[ERROR] No se obtuvieron datos del BCCH")
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
        if 'ipc' in df.columns:
            df['IPC'] = df['ipc']
        elif len(df.columns) >= 2:
            df['IPC'] = df.iloc[:, 1]
        
        # Asegurar que tenemos las columnas necesarias
        if 'Fecha' not in df.columns or 'IPC' not in df.columns:
            print(f"[ERROR] No se pudo identificar las columnas Fecha e IPC")
            print(f"[DEBUG] Columnas disponibles: {list(df.columns)}")
            return None
        
        # Seleccionar solo las columnas necesarias
        df = df[['Fecha', 'IPC']].copy()
        
        # Convertir fecha a datetime
        df['Fecha'] = pd.to_datetime(df['Fecha'], errors='coerce')
        df = df.dropna(subset=['Fecha'])
        
        # Convertir valor a numérico y filtrar valores inválidos
        df['IPC'] = pd.to_numeric(df['IPC'], errors='coerce')
        df = df.dropna(subset=['IPC'])
        
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


def extraer_ipc_brasil(fecha_inicio: str = "2010-01-01", fecha_fin: str = None):
    """
    Extrae datos de IPCA (IPC) de Brasil desde la API del BCB.
    
    Args:
        fecha_inicio: Fecha de inicio en formato YYYY-MM-DD
        fecha_fin: Fecha de fin en formato YYYY-MM-DD (por defecto: hoy)
        
    Returns:
        DataFrame con columnas: Fecha, IPC
    """
    print(f"\n[INFO] Extrayendo IPCA de Brasil desde API del BCB...")
    
    if fecha_fin is None:
        fecha_fin = datetime.today().strftime("%d/%m/%Y")
    else:
        fecha_fin = datetime.strptime(fecha_fin, "%Y-%m-%d").strftime("%d/%m/%Y")
    
    fecha_inicio_brasil = datetime.strptime(fecha_inicio, "%Y-%m-%d").strftime("%d/%m/%Y")
    
    codigo_serie = "433"  # IPCA
    url = f"https://api.bcb.gov.br/dados/serie/bcdata.sgs.{codigo_serie}/dados?formato=json&dataInicial={fecha_inicio_brasil}&dataFinal={fecha_fin}"
    
    print(f"   Código de serie: {codigo_serie} (IPCA)")
    print(f"   URL: {url}")
    print(f"   Rango solicitado: {fecha_inicio_brasil} a {fecha_fin}")
    
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'application/json'
        }
        
        response = requests.get(url, headers=headers, timeout=60)
        response.raise_for_status()
        
        data = response.json()
        
        if not data or len(data) == 0:
            print("[ERROR] No se obtuvieron datos del BCB")
            return None
        
        datos = []
        for item in data:
            fecha_str = item.get('data', '')
            valor_str = item.get('valor', '')
            
            # Filtrar valores inválidos
            if valor_str in ['n.d.', 'nan', '', '-', 'N/A', 'N.D.', None]:
                continue
            
            try:
                # Parsear fecha formato dd/MM/yyyy
                fecha = pd.to_datetime(fecha_str, format='%d/%m/%Y', errors='coerce')
                if pd.isna(fecha):
                    continue
                
                # Convertir valor a numérico
                valor_limpio = str(valor_str).replace(',', '.').replace(' ', '')
                valor_num = float(valor_limpio)
                
                datos.append({
                    'Fecha': fecha,
                    'IPC': valor_num
                })
            except (ValueError, TypeError) as e:
                print(f"[WARN] Error procesando fecha '{fecha_str}', valor '{valor_str}': {e}")
                continue
        
        if not datos:
            print("[ERROR] No se encontraron datos válidos")
            return None
        
        df = pd.DataFrame(datos)
        
        # Eliminar duplicados por fecha (mantener el último)
        df = df.drop_duplicates(subset='Fecha', keep='last')
        
        # Ordenar por fecha
        df = df.sort_values('Fecha').reset_index(drop=True)
        
        print(f"[OK] Se procesaron {len(df)} registros válidos")
        if len(df) > 0:
            print(f"   Rango: {df['Fecha'].min().strftime('%d/%m/%Y')} a {df['Fecha'].max().strftime('%d/%m/%Y')}")
        
        return df
        
    except requests.RequestException as e:
        print(f"[ERROR] Error al obtener datos del BCB: {e}")
        return None
    except Exception as e:
        print(f"[ERROR] Error inesperado: {e}")
        import traceback
        traceback.print_exc()
        return None


def extraer_ipc_mexico(fecha_inicio: str = "2010-01-01", fecha_fin: str = None):
    """
    Extrae datos de INPC (IPC) de México desde la API de Banxico.
    
    Args:
        fecha_inicio: Fecha de inicio en formato YYYY-MM-DD
        fecha_fin: Fecha de fin en formato YYYY-MM-DD (por defecto: hoy)
        
    Returns:
        DataFrame con columnas: Fecha, IPC
    """
    print(f"\n[INFO] Extrayendo INPC de México desde API de Banxico...")
    
    if fecha_fin is None:
        fecha_fin = datetime.today().strftime("%Y-%m-%d")
    
    codigo_serie = "SP1"  # INPC general
    
    # Para serie histórica, usar endpoint con rango de fechas
    # Formato: /series/{idSerie}/datos/{fechaInicial}/{fechaFinal}
    fecha_inicio_banxico = datetime.strptime(fecha_inicio, "%Y-%m-%d").strftime("%Y-%m-%d")
    fecha_fin_banxico = datetime.strptime(fecha_fin, "%Y-%m-%d").strftime("%Y-%m-%d")
    
    url = f"https://www.banxico.org.mx/SieAPIRest/service/v1/series/{codigo_serie}/datos/{fecha_inicio_banxico}/{fecha_fin_banxico}"
    
    print(f"   Código de serie: {codigo_serie} (INPC)")
    print(f"   URL: {url}")
    print(f"   Rango solicitado: {fecha_inicio_banxico} a {fecha_fin_banxico}")
    
    try:
        headers = {
            'Bmx-Token': BANXICO_TOKEN,
            'Accept': 'application/json',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        response = requests.get(url, headers=headers, timeout=60)
        response.raise_for_status()
        
        data = response.json()
        
        # Estructura de respuesta de Banxico: {"bmx": {"series": [{"idSerie": "SP1", "datos": [...]}]}}
        datos = []
        
        if isinstance(data, dict) and "bmx" in data:
            bmx_data = data["bmx"]
            if "series" in bmx_data and len(bmx_data["series"]) > 0:
                serie_data = bmx_data["series"][0]
                datos_serie = serie_data.get("datos", [])
                
                for item in datos_serie:
                    fecha_str = item.get("fecha", "")
                    valor_str = item.get("dato", "")
                    
                    # Filtrar valores inválidos
                    if valor_str in ['N/E', 'n.d.', 'nan', '', '-', 'N/A', 'N.D.', None]:
                        continue
                    
                    try:
                        # Parsear fecha formato YYYY-MM-DD
                        fecha = pd.to_datetime(fecha_str, errors='coerce')
                        if pd.isna(fecha):
                            continue
                        
                        # Convertir valor a numérico
                        valor_limpio = str(valor_str).replace(',', '').replace(' ', '')
                        valor_num = float(valor_limpio)
                        
                        datos.append({
                            'Fecha': fecha,
                            'IPC': valor_num
                        })
                    except (ValueError, TypeError) as e:
                        print(f"[WARN] Error procesando fecha '{fecha_str}', valor '{valor_str}': {e}")
                        continue
        else:
            print("[ERROR] Estructura de respuesta de la API no reconocida")
            print(f"[DEBUG] Estructura: {type(data)}")
            if isinstance(data, dict):
                print(f"[DEBUG] Keys: {list(data.keys())}")
            return None
        
        if not datos:
            print("[ERROR] No se encontraron datos válidos")
            return None
        
        df = pd.DataFrame(datos)
        
        # Eliminar duplicados por fecha (mantener el último)
        df = df.drop_duplicates(subset='Fecha', keep='last')
        
        # Ordenar por fecha
        df = df.sort_values('Fecha').reset_index(drop=True)
        
        print(f"[OK] Se procesaron {len(df)} registros válidos")
        if len(df) > 0:
            print(f"   Rango: {df['Fecha'].min().strftime('%d/%m/%Y')} a {df['Fecha'].max().strftime('%d/%m/%Y')}")
        
        return df
        
    except requests.RequestException as e:
        print(f"[ERROR] Error al obtener datos de Banxico: {e}")
        return None
    except Exception as e:
        print(f"[ERROR] Error inesperado: {e}")
        import traceback
        traceback.print_exc()
        return None


def parsear_fecha_bcrp_mensual(periodo_str: str):
    """
    Parsea fecha en formato BCRP mensual "2010-1" o "2010-01" a datetime (primer día del mes).
    """
    try:
        # Formato "2010-1" o "2010-01"
        if '-' in periodo_str:
            partes = periodo_str.split('-')
            año = int(partes[0])
            mes = int(partes[1])
            return datetime(año, mes, 1)
        else:
            # Intentar parsear como fecha estándar
            fecha = pd.to_datetime(periodo_str, errors='coerce')
            if not pd.isna(fecha):
                return fecha.replace(day=1)  # Primer día del mes
            raise ValueError(f"No se pudo parsear: {periodo_str}")
    except Exception as e:
        raise ValueError(f"Error parseando fecha BCRP '{periodo_str}': {e}")


def parsear_fecha_bcrp(periodo_str: str):
    """
    Parsea fecha en formato BCRP "Ene91" (mes español + año 2 dígitos) a datetime.
    
    Args:
        periodo_str: String en formato "Ene91", "Feb92", etc.
        
    Returns:
        datetime object con el primer día del mes
    """
    # Mapeo de meses abreviados en español
    meses_map = {
        'Ene': 1, 'Feb': 2, 'Mar': 3, 'Abr': 4, 'May': 5, 'Jun': 6,
        'Jul': 7, 'Ago': 8, 'Sep': 9, 'Oct': 10, 'Nov': 11, 'Dic': 12
    }
    
    # Parsear periodo: "Ene91" -> mes="Ene", año_2digitos=91
    mes_str = periodo_str[:3].capitalize()
    año_2digitos = int(periodo_str[3:])
    
    # Convertir año de 2 dígitos a 4 dígitos
    if año_2digitos <= 50:
        año = 2000 + año_2digitos
    else:
        año = 1900 + año_2digitos
    
    mes = meses_map.get(mes_str)
    if mes is None:
        raise ValueError(f"Mes no reconocido: {mes_str}")
    
    return datetime(año, mes, 1)


def extraer_ipc_peru(fecha_inicio: str = "2010-01-01", fecha_fin: str = None):
    """
    Extrae datos de IPC de Perú desde el BCRP usando pd.read_html().
    
    Args:
        fecha_inicio: Fecha de inicio en formato YYYY-MM-DD
        fecha_fin: Fecha de fin en formato YYYY-MM-DD (por defecto: hoy)
        
    Returns:
        DataFrame con columnas: Fecha, IPC
    """
    print(f"\n[INFO] Extrayendo IPC de Perú desde HTML del BCRP...")
    
    if fecha_fin is None:
        fecha_fin = datetime.today().strftime("%Y-%m-%d")
    
    codigo_serie = "PN38705PM"
    url = f"https://estadisticas.bcrp.gob.pe/estadisticas/series/mensuales/resultados/{codigo_serie}/html"
    
    print(f"   Código de serie: {codigo_serie}")
    print(f"   URL: {url}")
    print(f"   Rango solicitado: {fecha_inicio} a {fecha_fin}")
    
    try:
        # Cargar la tabla de la web del BCRP usando pd.read_html()
        print("[INFO] Cargando tabla desde la URL...")
        tables = pd.read_html(url)
        
        if not tables or len(tables) < 2:
            print("[ERROR] No se encontraron tablas en la página")
            return None
        
        # Extraer la tabla correcta (índice 1 según el ejemplo del usuario)
        df = tables[1].copy()
        
        print(f"[DEBUG] Tabla extraída con {len(df)} filas y {len(df.columns)} columnas")
        print(f"[DEBUG] Primeras filas:\n{df.head()}")
        
        # Renombrar columnas para facilitar el análisis
        if len(df.columns) >= 2:
            df.columns = ['Fecha', 'IPC']
        else:
            print(f"[ERROR] La tabla no tiene el formato esperado. Columnas: {list(df.columns)}")
            return None
        
        # Parsear fechas en formato "Ene91" (mes español + año 2 dígitos)
        print("[INFO] Parseando fechas...")
        df['Fecha'] = df['Fecha'].apply(lambda x: parsear_fecha_bcrp(str(x)) if pd.notna(x) else None)
        
        # Convertir columna 'IPC' a numérica
        df['IPC'] = pd.to_numeric(df['IPC'], errors='coerce')
        
        # Eliminar filas inválidas
        df = df.dropna()
        
        # Eliminar duplicados por fecha (mantener el último)
        df = df.drop_duplicates(subset='Fecha', keep='last')
        
        # Ordenar por fecha
        df = df.sort_values('Fecha').reset_index(drop=True)
        
        # Filtrar por rango de fechas solicitado
        fecha_inicio_dt = datetime.strptime(fecha_inicio, "%Y-%m-%d")
        fecha_fin_dt = datetime.strptime(fecha_fin, "%Y-%m-%d")
        df = df[
            (df['Fecha'] >= fecha_inicio_dt) & 
            (df['Fecha'] <= fecha_fin_dt)
        ]
        
        print(f"[OK] Se procesaron {len(df)} registros válidos")
        if len(df) > 0:
            print(f"   Rango: {df['Fecha'].min().strftime('%d/%m/%Y')} a {df['Fecha'].max().strftime('%d/%m/%Y')}")
        
        return df
        
    except Exception as e:
        print(f"[ERROR] Error al obtener datos del BCRP: {e}")
        import traceback
        traceback.print_exc()
        return None


def validar_fechas(df: pd.DataFrame) -> pd.DataFrame:
    """Valida que todas las fechas sean válidas (OBLIGATORIO según README)."""
    if df is None or df.empty:
        return df
    
    print("\n[INFO] Validando fechas...")

    fechas_invalidas = []
    fechas_validas = []

    for idx, fecha in enumerate(df["Fecha"]):
        try:
            if pd.isna(fecha):
                fechas_invalidas.append((idx, fecha, "Fecha nula"))
            else:
                fecha_parseada = pd.to_datetime(fecha, errors="coerce")
                if pd.isna(fecha_parseada):
                    fechas_invalidas.append((idx, fecha, "No se pudo parsear"))
                else:
                    fechas_validas.append(fecha_parseada)
        except Exception as exc:
            fechas_invalidas.append((idx, fecha, str(exc)))

    if fechas_invalidas:
        print(f"[ERROR] Se encontraron {len(fechas_invalidas)} fechas invalidas:")
        for idx, fecha, motivo in fechas_invalidas[:10]:
            print(f"   Fila {idx}: {fecha} - {motivo}")
        if len(fechas_invalidas) > 10:
            print(f"   ... y {len(fechas_invalidas) - 10} mas")
        raise ValueError("Hay fechas invalidas. No se puede continuar.")

    df["Fecha"] = pd.to_datetime(df["Fecha"])
    print(f"[OK] Todas las {len(fechas_validas)} fechas son validas")
    print(f"   Rango: {df['Fecha'].min()} a {df['Fecha'].max()}")
    return df


def preparar_datos_maestro_precios(df_ipc: pd.DataFrame, maestro_id: int) -> pd.DataFrame:
    """Prepara el DataFrame para maestro_precios."""
    if df_ipc is None or df_ipc.empty:
        return pd.DataFrame(columns=["maestro_id", "fecha", "valor"])
    
    df_precios = df_ipc.copy()
    df_precios["maestro_id"] = maestro_id
    df_precios = df_precios[["maestro_id", "Fecha", "IPC"]]
    df_precios.columns = ["maestro_id", "fecha", "valor"]
    
    df_precios["valor"] = pd.to_numeric(df_precios["valor"], errors="coerce")
    df_precios = df_precios.dropna(subset=["valor"])
    return df_precios


def insertar_en_bd(pais_config: dict, df_maestro: pd.DataFrame, df_precios: pd.DataFrame) -> bool:
    """
    Inserta los datos en la base de datos SQLite.
    Retorna True si fue exitoso, False en caso contrario.
    """
    print("\n[INFO] Insertando datos en la base de datos...")

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    try:
        maestro_id = int(df_maestro.iloc[0]["id"])
        maestro_row = df_maestro.iloc[0]
        
        # Insertar en maestro (con campos adicionales)
        cursor.execute(
            """
            INSERT OR REPLACE INTO maestro 
            (id, nombre, tipo, fuente, periodicidad, unidad, categoria, activo, es_cotizacion, nominal_real)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                maestro_id,
                maestro_row["nombre"],
                maestro_row["tipo"],
                maestro_row["fuente"],
                maestro_row["periodicidad"],
                maestro_row["unidad"],
                maestro_row["categoria"],
                maestro_row["activo"],
                0,  # es_cotizacion = 0 (no es cotización)
                "N",  # nominal_real = "N" (nominal)
            )
        )
        
        print(f"[OK] Insertado/actualizado registro en tabla 'maestro' (id={maestro_id})")

        # Eliminar registros existentes para este maestro_id
        cursor.execute(
            """
            DELETE FROM maestro_precios WHERE maestro_id = ?
            """,
            (maestro_id,)
        )
        registros_eliminados = cursor.rowcount
        if registros_eliminados > 0:
            print(f"[INFO] Se eliminaron {registros_eliminados} registros antiguos de 'maestro_precios'")

        # Insertar todos los precios nuevos
        if len(df_precios) > 0:
            print(f"[INFO] Insertando {len(df_precios)} registros en 'maestro_precios'...")
            df_precios.to_sql("maestro_precios", conn, if_exists="append", index=False)
            print(f"[OK] Insertados {len(df_precios)} registro(s) en tabla 'maestro_precios'")
        else:
            print(f"[WARN] No hay datos para insertar")
            return False

        conn.commit()
        print(f"\n[OK] Datos insertados exitosamente en '{DB_NAME}'")
        return True
    except Exception as exc:
        conn.rollback()
        print(f"[ERROR] Error al insertar datos: {exc}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        conn.close()


def procesar_pais(pais_config: dict) -> bool:
    """
    Procesa un país completo: extracción, validación e inserción.
    Retorna True si fue exitoso, False en caso contrario.
    """
    print("\n" + "=" * 60)
    print(f"PROCESANDO: {pais_config['nombre']}")
    print("=" * 60)
    
    try:
        # Extraer datos según el tipo de API
        df = None
        fecha_inicio = "2010-01-01"
        fecha_fin = None
        
        if pais_config["api_type"] == "BCCH":
            df = extraer_ipc_chile(fecha_inicio=fecha_inicio, fecha_fin=fecha_fin)
        elif pais_config["api_type"] == "BCB":
            df = extraer_ipc_brasil(fecha_inicio=fecha_inicio, fecha_fin=fecha_fin)
        elif pais_config["api_type"] == "BANXICO":
            df = extraer_ipc_mexico(fecha_inicio=fecha_inicio, fecha_fin=fecha_fin)
        elif pais_config["api_type"] == "BCRP":
            df = extraer_ipc_peru(fecha_inicio=fecha_inicio, fecha_fin=fecha_fin)
        else:
            print(f"[ERROR] Tipo de API no reconocido: {pais_config['api_type']}")
            return False
        
        if df is None or df.empty:
            print(f"[ERROR] No se pudieron extraer datos para {pais_config['nombre']}")
            return False
        
        # Validar fechas
        df = validar_fechas(df)
        
        # Preparar datos para inserción
        df_maestro = pd.DataFrame([{
            "id": pais_config["id"],
            "nombre": pais_config["nombre"],
            "tipo": "M",
            "fuente": pais_config["fuente"],
            "periodicidad": "M",  # Mensual
            "unidad": pais_config["unidad"],
            "categoria": "Macro - IPC",
            "activo": True
        }])
        
        df_precios = preparar_datos_maestro_precios(df, pais_config["id"])
        
        # Insertar en BD
        return insertar_en_bd(pais_config, df_maestro, df_precios)
        
    except Exception as e:
        print(f"[ERROR] Error procesando {pais_config['nombre']}: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    print("=" * 60)
    print("ACTUALIZACION DE DATOS: IPC MULTIPAIES")
    print("=" * 60)
    
    crear_base_datos()
    
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
