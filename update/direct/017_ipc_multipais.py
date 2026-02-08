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

import re
from datetime import datetime

import pandas as pd
import requests
from bcchapi import Siete
from _helpers import (
    validar_fechas_solo_nulas,
    insertar_en_bd_unificado
)


# Configuración de base de datos
DB_NAME = "series_tiempo.db"

# Credenciales del BCCH
BCCH_USER = "joaquin.forrisi@gmail.com"
BCCH_PASSWORD = "Joaquin.13"

# Token de Banxico (México)
BANXICO_TOKEN = "eb42b7168baa77063b964ad9e2501a29b6c4d7ba9c67d7f417098725555aa1eb"

# Configuración de países
# NOTA: id_variable e id_pais configurados desde maestro_database.xlsx Sheet1_old
PAISES_CONFIG = [
    {
        "api_type": "BCCH",
        "codigo_serie": "F074.IPC.IND.Z.EP23.C.M",
        "id_variable": 9,  # IPC
        "id_pais": 152,  # Chile
        "nombre": "IPC - Chile",
        "es_inflacion_mensual": False  # Ya es índice
    },
    {
        "api_type": "BCB",
        "codigo_serie": "433",
        "id_variable": 9,  # IPC
        "id_pais": 76,  # Brasil
        "nombre": "IPC - Brasil (IPCA)",
        "es_inflacion_mensual": True  # Es inflación mensual, necesita conversión
    },
    {
        "api_type": "BANXICO",
        "codigo_serie": "SP1",
        "id_variable": 9,  # IPC
        "id_pais": 484,  # México (id_pais=484 en tabla pais_grupo de la base de datos)
        "nombre": "IPC - México (INPC)",
        "es_inflacion_mensual": False  # Ya es índice
    },
    {
        "api_type": "BCRP",
        "codigo_serie": "PN38705PM",
        "id_variable": 9,  # IPC
        "id_pais": 604,  # Perú
        "nombre": "IPC - Perú",
        "es_inflacion_mensual": False  # Ya es índice
    },
]

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
                        # Parsear fecha formato DD/MM/YYYY (Banxico usa formato día/mes/año)
                        # Ejemplo: "01/12/2010" = 1 de diciembre de 2010
                        fecha = pd.to_datetime(fecha_str, format='%d/%m/%Y', errors='coerce')
                        if pd.isna(fecha):
                            # Si falla con el formato específico, intentar auto-detección
                            fecha = pd.to_datetime(fecha_str, errors='coerce')
                        if pd.isna(fecha):
                            continue
                        
                        # Convertir valor a numérico
                        valor_limpio = str(valor_str).replace(',', '').replace(' ', '')
                        valor_num = float(valor_limpio)
                        
                        # Guardar fecha original (sin normalizar) para poder agrupar correctamente
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
        
        # Agrupar por año-mes y tomar el último valor de cada mes
        # Esto es necesario porque Banxico puede devolver múltiples fechas por mes
        # (ej: 01/01/2010, 01/02/2010, etc. todos del mismo mes)
        df['Año'] = df['Fecha'].dt.year
        df['Mes'] = df['Fecha'].dt.month
        
        # Ordenar por fecha y agrupar por año-mes, tomando el último de cada grupo
        df = df.sort_values('Fecha').groupby(['Año', 'Mes'], as_index=False).last()
        
        # Normalizar todas las fechas al primer día del mes (IPC es mensual)
        df['Fecha'] = df['Fecha'].apply(lambda x: x.replace(day=1))
        
        # Eliminar columnas auxiliares
        df = df.drop(columns=['Año', 'Mes'])
        
        # Eliminar duplicados por fecha (mantener el último) - por si acaso
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

def extraer_ipc_peru(fecha_inicio: str = "2010-01-01", fecha_fin: str = None):
    """
    Extrae datos de IPC de Perú desde el Excel del INEI.
    
    Args:
        fecha_inicio: Fecha de inicio en formato YYYY-MM-DD
        fecha_fin: Fecha de fin en formato YYYY-MM-DD (por defecto: hoy)
        
    Returns:
        DataFrame con columnas: Fecha, IPC
    """
    print(f"\n[INFO] Extrayendo IPC de Perú desde Excel del INEI...")
    
    if fecha_fin is None:
        fecha_fin = datetime.today().strftime("%Y-%m-%d")
    
    url_excel = "https://www.inei.gob.pe/media/MenuRecursivo/indices_tematicos/01_indice-precios_al_consumidor-lm_ene26.xlsx"
    nombre_hoja = "Base Dic2021"
    
    print(f"   URL: {url_excel}")
    print(f"   Hoja: {nombre_hoja}")
    print(f"   Rango solicitado: {fecha_inicio} a {fecha_fin}")
    
    # Mapeo de meses en español a números
    meses_map = {
        'Enero': 1, 'Febrero': 2, 'Marzo': 3, 'Abril': 4, 'Mayo': 5, 'Junio': 6,
        'Julio': 7, 'Agosto': 8, 'Setiembre': 9, 'Octubre': 10, 'Noviembre': 11, 'Diciembre': 12,
        # Variantes posibles
        'Ene': 1, 'Feb': 2, 'Mar': 3, 'Abr': 4, 'May': 5, 'Jun': 6,
        'Jul': 7, 'Ago': 8, 'Sep': 9, 'Oct': 10, 'Nov': 11, 'Dic': 12
    }
    
    try:
        # Leer Excel desde URL
        print("[INFO] Cargando Excel desde URL...")
        df = pd.read_excel(
            url_excel,
            sheet_name=nombre_hoja,
            skiprows=4,  # Empezar desde fila 5 (0-indexed = 4)
            usecols=[0, 1, 2],  # Columnas A (año), B (mes), C (índice)
            header=None,
            names=['Año', 'Mes', 'IPC']
        )
        
        print(f"[OK] Datos leídos: {len(df)} filas")
        
        # Eliminar filas completamente vacías
        df = df.dropna(how='all')
        
        # Eliminar filas donde IPC sea nulo o no numérico
        df['IPC'] = pd.to_numeric(df['IPC'], errors='coerce')
        df = df.dropna(subset=['IPC'])
        
        # Completar años vacíos con forward fill (el último año disponible)
        df['Año'] = pd.to_numeric(df['Año'], errors='coerce')
        df['Año'] = df['Año'].ffill()  # Forward fill
        
        # Eliminar filas donde el año sigue siendo nulo (después del forward fill)
        df = df.dropna(subset=['Año'])
        
        # Convertir año a entero
        df['Año'] = df['Año'].astype(int)
        
        # Parsear mes desde español a número
        print("[INFO] Parseando meses...")
        def parsear_mes(mes_str):
            if pd.isna(mes_str):
                return None
            mes_str = str(mes_str).strip()
            # Buscar en el mapeo (case insensitive)
            for mes_nombre, mes_num in meses_map.items():
                if mes_str.lower() == mes_nombre.lower():
                    return mes_num
            # Si no se encuentra, intentar convertir directamente a número
            try:
                return int(float(mes_str))
            except:
                return None
        
        df['Mes_num'] = df['Mes'].apply(parsear_mes)
        
        # Eliminar filas donde no se pudo parsear el mes
        df = df.dropna(subset=['Mes_num'])
        df['Mes_num'] = df['Mes_num'].astype(int)
        
        # Crear columna de fecha (primer día del mes)
        df['Fecha'] = df.apply(lambda row: datetime(int(row['Año']), int(row['Mes_num']), 1), axis=1)
        
        # Seleccionar solo las columnas necesarias
        df = df[['Fecha', 'IPC']].copy()
        
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
        print(f"[ERROR] Error al obtener datos del INEI: {e}")
        import traceback
        traceback.print_exc()
        return None

def convertir_inflacion_a_indice(df: pd.DataFrame, fecha_base: str = "2009-12-01", valor_base: float = 100.0) -> pd.DataFrame:
    """
    Convierte inflación mensual (variación %) a índice base 100.
    
    Ejemplo:
    - Dic-2009 = 100 (base)
    - Ene-2010: inflación 0.75% -> índice = 100 * (1 + 0.0075) = 100.75
    - Feb-2010: inflación 0.78% -> índice = 100.75 * (1 + 0.0078) = 101.5358
    
    Args:
        df: DataFrame con columnas 'Fecha' e 'IPC' (donde IPC es inflación mensual en %)
        fecha_base: Fecha base para el índice (por defecto: dic-2009)
        valor_base: Valor base del índice (por defecto: 100.0)
        
    Returns:
        DataFrame con 'IPC' convertido a índice acumulado base 100
    """
    print(f"\n[INFO] Convirtiendo inflación mensual a índice base {valor_base}...")
    print(f"   Fecha base: {fecha_base}")
    
    df = df.copy()
    df = df.sort_values('Fecha').reset_index(drop=True)
    
    # Convertir fecha_base a datetime
    fecha_base_dt = pd.to_datetime(fecha_base)
    
    # Convertir columna Fecha a datetime si no lo es
    df['Fecha_dt'] = pd.to_datetime(df['Fecha'])
    
    # Encontrar el índice de la fila base (diciembre 2009 o la más cercana anterior)
    indices_base = df[df['Fecha_dt'] <= fecha_base_dt].index
    
    if len(indices_base) == 0:
        # Si no hay datos antes de la fecha base, usar el primer valor como base
        print(f"[WARN] No se encontró fecha base {fecha_base}, usando primer valor como base")
        primer_indice = 0
        valor_inicial = valor_base
    else:
        # Usar el último valor antes o igual a la fecha base
        primer_indice = indices_base[-1]
        valor_inicial = valor_base
        print(f"[INFO] Usando fecha {df.loc[primer_indice, 'Fecha_dt'].strftime('%Y-%m-%d')} como base")
    
    # Crear columna de índice acumulado
    df['IPC_indice'] = None
    
    # Establecer valor base
    df.loc[primer_indice, 'IPC_indice'] = valor_inicial
    
    # Aplicar variación acumulativa desde el siguiente mes hacia adelante
    for i in range(primer_indice + 1, len(df)):
        indice_anterior = df.loc[i - 1, 'IPC_indice']
        inflacion_mensual = df.loc[i, 'IPC']  # Inflación en %
        
        # Calcular nuevo índice: índice_anterior * (1 + inflación/100)
        nuevo_indice = indice_anterior * (1 + inflacion_mensual / 100.0)
        df.loc[i, 'IPC_indice'] = nuevo_indice
    
    # También calcular hacia atrás desde la base si hay datos anteriores
    for i in range(primer_indice - 1, -1, -1):
        indice_siguiente = df.loc[i + 1, 'IPC_indice']
        inflacion_mensual = df.loc[i, 'IPC']  # Inflación en %
        
        # Calcular índice anterior: índice_siguiente / (1 + inflación/100)
        indice_anterior = indice_siguiente / (1 + inflacion_mensual / 100.0)
        df.loc[i, 'IPC_indice'] = indice_anterior
    
    # Reemplazar columna IPC con el índice calculado
    df['IPC'] = df['IPC_indice']
    df = df.drop(columns=['IPC_indice', 'Fecha_dt'])
    
    print(f"[OK] Conversión completada. Rango de índice: {df['IPC'].min():.2f} a {df['IPC'].max():.2f}")
    
    return df

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
        
        # Si es inflación mensual, convertir a índice
        if pais_config.get("es_inflacion_mensual", False):
            df = convertir_inflacion_a_indice(df, fecha_base="2009-12-01", valor_base=100.0)
        
        # Verificar que id_variable e id_pais están configurados
        if pais_config.get("id_variable") is None or pais_config.get("id_pais") is None:
            print(f"[ERROR] {pais_config['nombre']}: id_variable e id_pais deben estar configurados.")
            return False
        
        # Renombrar columnas para el helper
        df = df.rename(columns={'Fecha': 'FECHA', 'IPC': 'VALOR'})
        
        # Validar fechas
        df = validar_fechas_solo_nulas(df)
        
        # Insertar en BD usando helper unificado
        print(f"\n[INFO] Actualizando base de datos para {pais_config['nombre']}...")
        insertar_en_bd_unificado(
            pais_config["id_variable"],
            pais_config["id_pais"],
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
    print("ACTUALIZACION DE DATOS: IPC MULTIPAIES")
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
