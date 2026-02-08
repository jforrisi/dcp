"""
Script: expectativas_inflacion_mexico_banxico
----------------------------------------------
Descarga los datos de Expectativas de Inflación desde Banxico usando su API.
Convierte los datos JSON a Excel y los guarda en update/historicos.
"""

import os
import pandas as pd
import requests
from datetime import datetime

# Configuración
# Serie: Expectativas de Inflación para los Próximos 12 Meses (mes t+1) - Mediana
# ID Serie: SR16774
# Descripción: Encuestas Sobre las Expectativas de los Especialistas en Economía del Sector Privado
# Periodicidad: Mensual
# Unidad: Porcentajes
SERIE_ID = "SR16774"
HISTORICOS_DIR = "update/historicos"
DEST_FILENAME = "expectativas_inflacion_mexico.xlsx"

# Token de Banxico (desde 017_ipc_multipais.py)
BANXICO_TOKEN = "eb42b7168baa77063b964ad9e2501a29b6c4d7ba9c67d7f417098725555aa1eb"

# URL base de la API de Banxico
BANXICO_API_BASE = "https://www.banxico.org.mx/SieAPIRest/service/v1"


def asegurar_historicos():
    """Crea la carpeta update/historicos si no existe y devuelve su ruta absoluta."""
    base_dir = os.getcwd()
    historicos_path = os.path.join(base_dir, HISTORICOS_DIR)
    os.makedirs(historicos_path, exist_ok=True)
    return historicos_path


def obtener_fechas_rango():
    """
    Obtiene el rango de fechas para descargar.
    Por defecto, descarga desde 2015-01-01 hasta el día actual.
    """
    hoy = datetime.now()
    fecha_fin = hoy.strftime("%Y-%m-%d")
    fecha_inicio = "2015-01-01"  # Inicio razonable para tener datos históricos
    return fecha_inicio, fecha_fin


def descargar_datos_banxico(serie_id: str, fecha_inicio: str, fecha_fin: str):
    """
    Descarga los datos de la serie desde la API de Banxico.
    
    Args:
        serie_id: ID de la serie (ej: CR155_1)
        fecha_inicio: Fecha inicio en formato YYYY-MM-DD
        fecha_fin: Fecha fin en formato YYYY-MM-DD
    
    Returns:
        DataFrame con los datos (fecha, valor)
    """
    url = f"{BANXICO_API_BASE}/series/{serie_id}/datos/{fecha_inicio}/{fecha_fin}"
    
    print(f"[INFO] Descargando datos desde la API de Banxico...")
    print(f"[INFO] URL: {url}")
    
    headers = {
        "Bmx-Token": BANXICO_TOKEN,
        "Accept": "application/json",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=60)
        
        # Si hay error, mostrar el mensaje de la API
        if response.status_code != 200:
            try:
                error_data = response.json()
                print(f"[ERROR] Respuesta de la API: {error_data}")
            except:
                print(f"[ERROR] Status code: {response.status_code}")
                print(f"[ERROR] Response text: {response.text[:500]}")
            response.raise_for_status()
        
        data = response.json()
        
        # Verificar que la respuesta tenga la estructura esperada
        if not isinstance(data, dict) or "bmx" not in data:
            raise ValueError("La respuesta de la API no tiene la estructura esperada (falta 'bmx')")
        
        bmx_data = data["bmx"]
        if "series" not in bmx_data or len(bmx_data["series"]) == 0:
            raise ValueError("No se encontraron series en la respuesta")
        
        serie_data = bmx_data["series"][0]
        datos_serie = serie_data.get("datos", [])
        
        if not datos_serie:
            raise ValueError("No se obtuvieron datos de la API")
        
        # Convertir a DataFrame
        registros = []
        for item in datos_serie:
            fecha_str = item.get("fecha", "")
            valor_str = item.get("dato", "")
            
            # Filtrar valores inválidos
            if valor_str in ['N/E', 'n.d.', 'nan', '', '-', 'N/A', 'N.D.', None]:
                continue
            
            # Parsear fecha formato DD/MM/YYYY (Banxico usa formato día/mes/año)
            try:
                fecha = pd.to_datetime(fecha_str, format='%d/%m/%Y', errors='coerce')
                if pd.isna(fecha):
                    # Si falla con el formato específico, intentar auto-detección
                    fecha = pd.to_datetime(fecha_str, errors='coerce')
                if pd.isna(fecha):
                    print(f"[WARN] Fecha no válida: {fecha_str}")
                    continue
                
                # Convertir valor a numérico
                valor_limpio = str(valor_str).replace(',', '').replace(' ', '')
                valor_num = float(valor_limpio)
                
                # Convertir fecha a date
                fecha_date = fecha.date() if isinstance(fecha, pd.Timestamp) else fecha
                registros.append({
                    "fecha": fecha_date,
                    "valor": valor_num
                })
            except (ValueError, TypeError) as e:
                print(f"[WARN] Error procesando fecha '{fecha_str}', valor '{valor_str}': {e}")
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
    print("DESCARGA DE EXPECTATIVAS DE INFLACIÓN - BANXICO (MÉXICO) - API")
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
        df = descargar_datos_banxico(SERIE_ID, fecha_inicio, fecha_fin)
        
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
