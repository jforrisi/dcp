# -*- coding: utf-8 -*-
"""
Script: nxr_peru
----------------
Actualiza la base de datos con la serie de tipo de cambio USD/PEN del Banco Central 
de Reserva del Perú (BCRP), usando su API oficial.

1) Extraer datos desde API del BCRP (desde el primer dato disponible).
2) Parsear fechas y filtrar valores no numéricos.
3) Completar días faltantes (forward fill).
4) Validar fechas.
5) Actualizar automáticamente la base de datos.
"""

import re
from datetime import datetime

import pandas as pd
import requests
from _helpers import (
    completar_dias_faltantes,
    validar_fechas_solo_nulas,
    insertar_en_bd_unificado
)


# Configuración de base de datos
# Código de serie del BCRP para TC Interbancario (Venta)
CODIGO_SERIE_BCRP = "PD04638PD"

# Base URL de la API del BCRP
BASE_URL_API = "https://estadisticas.bcrp.gob.pe/estadisticas/series/api"

# Configuración de IDs (desde maestro_database.xlsx Sheet1_old)
ID_VARIABLE = 20  # Tipo de cambio USD
ID_PAIS = 604  # Perú

# Mapeo de meses en español (por si acaso vienen en formato "02Ene97")
MESES_BCRP = {
    'Ene': '01', 'Feb': '02', 'Mar': '03', 'Abr': '04',
    'May': '05', 'Jun': '06', 'Jul': '07', 'Ago': '08',
    'Set': '09', 'Oct': '10', 'Nov': '11', 'Dic': '12'
}

def parsear_fecha_bcrp(fecha_str: str) -> datetime:
    """
    Parsea fecha en formato BCRP "02Ene97" a datetime.
    """
    patron = r'(\d{2})(Ene|Feb|Mar|Abr|May|Jun|Jul|Ago|Set|Oct|Nov|Dic)(\d{2})'
    match = re.match(patron, fecha_str)
    
    if not match:
        raise ValueError(f"No se pudo parsear la fecha: {fecha_str}")
    
    dia = int(match.group(1))
    mes_str = match.group(2)
    año_2digitos = int(match.group(3))
    
    # Convertir año de 2 dígitos a 4 dígitos
    if año_2digitos <= 50:
        año = 2000 + año_2digitos
    else:
        año = 1900 + año_2digitos
    
    mes = int(MESES_BCRP[mes_str])
    
    return datetime(año, mes, dia)

def extraer_bcrp_peru():
    """
    Extrae datos de tipo de cambio del BCRP usando su API.
    Obtiene todos los datos disponibles desde el inicio de la serie.
    
    Returns:
        DataFrame con columnas: Fecha, Tipo_Cambio
    """
    print(f"[INFO] Extrayendo datos desde API del BCRP...")
    print(f"   Código de serie: {CODIGO_SERIE_BCRP}")
    
    try:
        # Obtener todos los datos históricos desde el inicio (1997-01-02 según la documentación)
        fecha_inicio = "1997-01-02"  # Primer dato disponible según la documentación
        fecha_fin = datetime.today().strftime("%Y-%m-%d")  # Hasta hoy
        
        url = f"{BASE_URL_API}/{CODIGO_SERIE_BCRP}/json/{fecha_inicio}/{fecha_fin}/esp"
        
        print(f"   URL: {url}")
        print(f"   Rango solicitado: {fecha_inicio} a {fecha_fin}")
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'application/json'
        }
        
        response = requests.get(url, headers=headers, timeout=60)
        response.raise_for_status()
        
        # Parsear JSON
        data = response.json()
        
        datos = []
        
        # Estructura real del BCRP: {"periods": [{"name": "08.Set.25", "values": ["3.516"]}, ...]}
        if isinstance(data, dict) and "periods" in data:
            periods = data.get("periods", [])
            
            for period_item in periods:
                if not isinstance(period_item, dict):
                    continue
                
                # Obtener nombre de periodo (fecha) y valores
                periodo_name = period_item.get("name", "")
                period_values = period_item.get("values", [])
                
                # Tomar el primer valor (puede haber múltiples series)
                if not period_values or len(period_values) == 0:
                    continue
                
                valor_str = period_values[0]  # Primer valor de la lista
                
                # Filtrar valores "n.d." o no numéricos
                if valor_str in ['n.d.', 'nan', '', '-', 'N/A', 'N.D.', None]:
                    continue
                
                try:
                    # Parsear fecha: formato "08.Set.25" (día.mes.año)
                    fecha = None
                    
                    # Intentar parsear formato "08.Set.25" o "08Ene97"
                    if re.match(r'\d{2}\.[A-Za-z]{3}\.\d{2}', periodo_name):
                        # Formato "08.Set.25" -> "08/Set/2025"
                        partes = periodo_name.split('.')
                        dia = int(partes[0])
                        mes_str = partes[1].capitalize()  # Asegurar primera letra mayúscula
                        año_2digitos = int(partes[2])
                        
                        # Convertir año de 2 dígitos a 4 dígitos
                        if año_2digitos <= 50:
                            año = 2000 + año_2digitos
                        else:
                            año = 1900 + año_2digitos
                        
                        # Convertir mes (normalizar a formato sin punto)
                        mes_str_normalizado = mes_str.replace('.', '')
                        mes = int(MESES_BCRP.get(mes_str_normalizado, '01'))
                        fecha = datetime(año, mes, dia)
                    
                    elif re.match(r'\d{2}[A-Za-z]{3}\d{2}', periodo_name):
                        # Formato "08Ene97"
                        fecha = parsear_fecha_bcrp(periodo_name)
                    else:
                        # Intentar parsear como fecha estándar
                        fecha = pd.to_datetime(periodo_name, errors='coerce')
                        if pd.isna(fecha):
                            continue
                    
                    # Convertir valor a numérico
                    valor_limpio = str(valor_str).replace(',', '').replace(' ', '')
                    valor_num = float(valor_limpio)
                    
                    datos.append({
                        'Fecha': fecha,
                        'Tipo_Cambio': valor_num
                    })
                except (ValueError, TypeError, KeyError) as e:
                    print(f"[WARN] Error procesando periodo '{periodo_name}', valor '{valor_str}': {e}")
                    continue
        
        if not datos:
            print("[ERROR] No se encontraron datos válidos en la respuesta de la API")
            return None
        
        df = pd.DataFrame(datos)
        
        # Eliminar duplicados por fecha (mantener el último)
        df = df.drop_duplicates(subset='Fecha', keep='last')
        
        # Ordenar por fecha
        df = df.sort_values('Fecha').reset_index(drop=True)
        
        print(f"[OK] Se extrajeron {len(df)} registros")
        if len(df) > 0:
            print(f"   Rango: {df['Fecha'].min().strftime('%d/%m/%Y')} a {df['Fecha'].max().strftime('%d/%m/%Y')}")
        
        return df
        
    except requests.RequestException as e:
        print(f"[ERROR] Error al obtener datos del BCRP: {e}")
        return None
    except Exception as e:
        print(f"[ERROR] Error inesperado: {e}")
        import traceback
        traceback.print_exc()
        return None

def main():
    print("=" * 60)
    print("ACTUALIZACION DE DATOS: TIPO DE CAMBIO USD/PEN (PERÚ)")
    print("=" * 60)
    
    # Extraer datos desde API del BCRP
    print("\n[INFO] Extrayendo datos del Banco Central de Reserva del Perú...")
    df = extraer_bcrp_peru()
    
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
