"""
Script: expectativas_inflacion_peru_bcrp
-----------------------------------------
Descarga los datos de Expectativas de Inflación a 12 meses desde el BCRP usando su API.
Convierte los datos JSON a Excel y los guarda en update/historicos.
"""

import os
import pandas as pd
import requests
from datetime import datetime, date

# Configuración
SERIE_ID = "PD12912AM"  # Expectativa de Inflación a 12 meses
HISTORICOS_DIR = "update/historicos"
DEST_FILENAME = "expectativas_inflacion_peru.xlsx"

# URL base de la API del BCRP
# Formato: https://estadisticas.bcrp.gob.pe/estadisticas/series/api/{ID_SERIE}/json/{FECHA_INICIO}/{FECHA_FIN}
BCRP_API_BASE = "https://estadisticas.bcrp.gob.pe/estadisticas/series/api"


def asegurar_historicos():
    """Crea la carpeta update/historicos si no existe y devuelve su ruta absoluta."""
    base_dir = os.getcwd()
    historicos_path = os.path.join(base_dir, HISTORICOS_DIR)
    os.makedirs(historicos_path, exist_ok=True)
    return historicos_path


def obtener_fechas_rango():
    """
    Obtiene el rango de fechas para descargar.
    Por defecto, descarga desde 2000-01 hasta el mes actual.
    """
    hoy = datetime.now()
    fecha_fin = hoy.strftime("%Y-%m")
    fecha_inicio = "2000-01"  # Inicio razonable para tener datos históricos
    return fecha_inicio, fecha_fin


def descargar_datos_bcrp(serie_id: str, fecha_inicio: str, fecha_fin: str):
    """
    Descarga los datos de la serie desde la API del BCRP.
    
    Args:
        serie_id: ID de la serie (ej: PD12912AM)
        fecha_inicio: Fecha inicio en formato YYYY-MM
        fecha_fin: Fecha fin en formato YYYY-MM
    
    Returns:
        DataFrame con los datos (fecha, valor)
    """
    url = f"{BCRP_API_BASE}/{serie_id}/json/{fecha_inicio}/{fecha_fin}"
    
    print(f"[INFO] Descargando datos desde la API del BCRP...")
    print(f"[INFO] URL: {url}")
    
    headers = {
        "Accept": "application/json",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        
        data = response.json()
        
        # Verificar que la respuesta tenga la estructura esperada
        if 'periods' not in data:
            raise ValueError("La respuesta de la API no tiene la estructura esperada (falta 'periods')")
        
        # Extraer los datos
        valores = data['periods']
        
        if not valores:
            raise ValueError("No se obtuvieron datos de la API")
        
        # Debug: mostrar estructura de los primeros elementos
        print(f"[DEBUG] Total de períodos: {len(valores)}")
        if len(valores) > 0:
            print(f"[DEBUG] Primer elemento: {valores[0]}")
            print(f"[DEBUG] Estructura de keys: {valores[0].keys() if isinstance(valores[0], dict) else 'No es dict'}")
        
        # Mapeo de meses en español
        meses_es = {
            'ene': 1, 'feb': 2, 'mar': 3, 'abr': 4, 'may': 5, 'jun': 6,
            'jul': 7, 'ago': 8, 'sep': 9, 'oct': 10, 'nov': 11, 'dic': 12
        }
        
        # Convertir a DataFrame
        registros = []
        for item in valores:
            if not isinstance(item, dict):
                continue
            
            # Obtener fecha y valor
            fecha_str = item.get("name", "")
            valores_lista = item.get("values", [])
            
            if not fecha_str or not valores_lista:
                continue
            
            # Extraer el primer valor de la lista (puede haber múltiples valores)
            valor_str = valores_lista[0] if isinstance(valores_lista, list) and len(valores_lista) > 0 else None
            
            if valor_str is None:
                continue
            
            # Parsear fecha en formato "Ene.2002" o similar
            fecha = None
            try:
                fecha_str_clean = str(fecha_str).strip().lower()
                
                # Buscar el patrón: mes. año (ej: "ene.2002")
                if "." in fecha_str_clean:
                    partes = fecha_str_clean.split(".")
                    if len(partes) >= 2:
                        mes_str = partes[0].strip()
                        año_str = partes[1].strip()
                        
                        # Obtener número de mes
                        mes_num = meses_es.get(mes_str[:3], None)  # Primeros 3 caracteres
                        
                        if mes_num and año_str.isdigit():
                            año = int(año_str)
                            # Crear fecha (primer día del mes)
                            fecha = pd.Timestamp(year=año, month=mes_num, day=1)
                else:
                    # Intentar otros formatos
                    fecha = pd.to_datetime(fecha_str, errors='coerce')
            except Exception as e:
                print(f"[WARN] No se pudo parsear la fecha '{fecha_str}': {e}")
                continue
            
            if pd.isna(fecha) or fecha is None:
                continue
            
            # Convertir valor
            try:
                valor_num = float(valor_str)
                # Convertir fecha a date
                fecha_date = fecha.date() if isinstance(fecha, pd.Timestamp) else fecha
                registros.append({
                    "fecha": fecha_date,
                    "valor": valor_num
                })
            except (ValueError, TypeError) as e:
                print(f"[WARN] Valor no numérico ignorado: {valor_str} (tipo: {type(valor_str)})")
                continue
        
        df = pd.DataFrame(registros)
        
        if df.empty:
            raise ValueError("No se generaron registros válidos")
        
        # Ordenar por fecha
        df = df.sort_values('fecha').reset_index(drop=True)
        
        print(f"[OK] Datos descargados: {len(df)} registros")
        print(f"     Rango de fechas: {df['fecha'].min()} a {df['fecha'].max()}")
        
        return df
        
    except requests.exceptions.RequestException as e:
        raise RuntimeError(f"Error al descargar datos de la API: {e}")
    except Exception as e:
        raise RuntimeError(f"Error al procesar los datos: {e}")


def guardar_excel(df: pd.DataFrame, destino: str):
    """
    Guarda el DataFrame como archivo Excel.
    
    Args:
        df: DataFrame con los datos
        destino: Ruta completa del archivo destino
    """
    try:
        # Asegurar que la columna fecha esté en formato correcto
        if 'fecha' in df.columns:
            df['fecha'] = pd.to_datetime(df['fecha']).dt.date
        
        # Guardar como Excel
        df.to_excel(destino, index=False, engine='openpyxl')
        
        if os.path.exists(destino) and os.path.getsize(destino) > 0:
            print(f"[OK] Archivo guardado exitosamente: {os.path.getsize(destino)} bytes")
            return True
        else:
            raise RuntimeError("El archivo guardado está vacío o no existe")
            
    except Exception as e:
        raise RuntimeError(f"Error al guardar el archivo Excel: {e}")


def limpiar_archivos_anteriores(download_path: str, filename: str):
    """Elimina el archivo destino si ya existe."""
    destino = os.path.join(download_path, filename)
    if os.path.exists(destino):
        try:
            os.remove(destino)
            print(f"[INFO] Archivo anterior '{filename}' eliminado")
        except PermissionError:
            print(f"[WARN] No se pudo eliminar '{filename}' porque está en uso. Continuando...")
        except Exception as e:
            print(f"[WARN] No se pudo eliminar '{filename}': {e}")


def main():
    """Función principal."""
    print("=" * 80)
    print("DESCARGA DE EXPECTATIVAS DE INFLACIÓN - BCRP (PERÚ) - API")
    print("=" * 80)
    
    historicos_path = asegurar_historicos()
    destino = os.path.join(historicos_path, DEST_FILENAME)
    
    print(f"[INFO] Carpeta de destino: {historicos_path}")
    print(f"[INFO] Archivo destino: {DEST_FILENAME}")
    print(f"[INFO] Serie ID: {SERIE_ID}")
    print("=" * 80)
    
    try:
        # Limpiar archivo anterior si existe
        limpiar_archivos_anteriores(historicos_path, DEST_FILENAME)
        
        # Obtener rango de fechas
        fecha_inicio, fecha_fin = obtener_fechas_rango()
        print(f"[INFO] Rango de fechas: {fecha_inicio} a {fecha_fin}")
        
        # Descargar datos desde la API
        df = descargar_datos_bcrp(SERIE_ID, fecha_inicio, fecha_fin)
        
        # Guardar como Excel
        guardar_excel(df, destino)
        
        print(f"\n[SUCCESS] Proceso completado. Archivo guardado en: {destino}")
        
    except Exception as e:
        print(f"\n[ERROR] Error durante el proceso: {e}")
        import traceback
        traceback.print_exc()
        raise


if __name__ == "__main__":
    main()
