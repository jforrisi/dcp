# -*- coding: utf-8 -*-
"""
Extrae y compara precios de nafta y gasoil de Argentina, Brasil y Uruguay.
Convierte todos los precios a una moneda común (pesos uruguayos) usando tipos de cambio.
"""

import pandas as pd
import requests
import os
import shutil
import importlib
import config

# Recargar config para asegurar valores actualizados
importlib.reload(config)
from config import mes, año, imesi_arg, imesi_bra, ID_CARPETA_DRIVE, RUTA_DRIVE_LOCAL, ID_SHEET_NAFTA, ID_SHEET_GASOIL
from tc_consolidado import obtener_ratios

def leer_combustible_argentina(archivo="combustible_argentina_csv.csv"):
    """
    Lee el archivo CSV local de combustibles de Argentina.
    
    Args:
        archivo: Nombre del archivo CSV
        
    Returns:
        DataFrame con los datos, o None si hay error
    """
    if not os.path.exists(archivo):
        print(f"Archivo no encontrado: {archivo}")
        print("Ejecuta primero: python combustible_argentina.py")
        return None
    
    try:
        df = pd.read_csv(archivo, low_memory=False)
        return df
    except Exception as e:
        print(f"Error al leer {archivo}: {e}")
        return None

def obtener_precios_argentina(df_argy):
    """
    Obtiene los precios promedio de nafta y gasoil de Argentina (Concordia).
    
    Args:
        df_argy: DataFrame con datos de Argentina
        
    Returns:
        Tupla (nafta_argentina, gasoil_argentina) o (None, None) si hay error
    """
    try:
        concordia = df_argy[df_argy['mes'] == mes].copy()
        concordia = concordia[concordia['anio'] == año]
        concordia = concordia[concordia['localidad'] == 'CONCORDIA']
        
        if concordia.empty:
            print(f"No hay datos para Concordia en {mes}/{año}")
            return None, None
        
        gasoil_argentina = concordia[concordia['idproducto'] == 19]["precio"].mean()
        nafta_argentina = concordia[concordia['idproducto'] == 2]["precio"].mean()
        
        return nafta_argentina, gasoil_argentina
    except Exception as e:
        print(f"Error al obtener precios de Argentina: {e}")
        return None, None

def obtener_precios_brasil():
    """
    Obtiene los precios promedio de nafta y gasoil de Brasil (Santana do Livramento).
    
    Returns:
        Tupla (nafta_brasil, gasoil_brasil) o (None, None) si hay error
    """
    mes_str = f"{mes:02d}"
    
    try:
        # Gasoil
        url_diesel = (
            f"https://www.gov.br/anp/pt-br/centrais-de-conteudo/"
            f"dados-abertos/arquivos/shpc/dsan/{año}/"
            f"precos-diesel-gnv-{mes_str}.csv"
        )
        df_diesel = pd.read_csv(url_diesel, sep=";", encoding="latin1")
        df_filtrado = df_diesel[
            (df_diesel["Estado - Sigla"] == "RS") &
            (df_diesel["Produto"] == "DIESEL") &
            (df_diesel["Municipio"] == "SANTANA DO LIVRAMENTO")
        ]
        
        if df_filtrado.empty:
            print(f"No hay datos de gasoil para Brasil en {mes}/{año}")
            gasoil_brasil = None
        else:
            df_filtrado["Valor de Venda"] = (
                df_filtrado["Valor de Venda"]
                .astype(str)
                .str.replace(",", ".")
                .astype(float)
            )
            gasoil_brasil = df_filtrado["Valor de Venda"].mean()
        
        # Nafta
        url_gasolina = (
            f"https://www.gov.br/anp/pt-br/centrais-de-conteudo/"
            f"dados-abertos/arquivos/shpc/dsan/{año}/"
            f"precos-gasolina-etanol-{mes_str}.csv"
        )
        df_gasolina = pd.read_csv(url_gasolina, sep=";", encoding="latin1")
        df_filtrado = df_gasolina[
            (df_gasolina["Estado - Sigla"] == "RS") &
            (df_gasolina["Produto"] == "GASOLINA") &
            (df_gasolina["Municipio"] == "SANTANA DO LIVRAMENTO")
        ]
        
        if df_filtrado.empty:
            print(f"No hay datos de nafta para Brasil en {mes}/{año}")
            nafta_brasil = None
        else:
            df_filtrado["Valor de Venda"] = (
                df_filtrado["Valor de Venda"]
                .astype(str)
                .str.replace(",", ".")
                .astype(float)
            )
            nafta_brasil = df_filtrado["Valor de Venda"].mean()
        
        return nafta_brasil, gasoil_brasil
        
    except Exception as e:
        print(f"Error al obtener precios de Brasil: {e}")
        import traceback
        traceback.print_exc()
        return None, None

def obtener_precios_uruguay():
    """
    Obtiene los precios de nafta y gasoil de Uruguay.
    
    Returns:
        Tupla (nafta_uruguay, gasoil_uruguay, gasoil_uruguay_sin_iva) o (None, None, None) si hay error
    """
    url_excel = "https://www.ancap.com.uy/innovaportal/file/2147/1/historicodatos_prec_web_desde_01.07.23.xlsx"
    
    try:
        # Nafta
        df_nafta = pd.read_excel(url_excel, sheet_name="Gasolina Súper")
        df_nafta["Fecha"] = pd.to_datetime(df_nafta.iloc[:, 0], dayfirst=True, format='mixed', errors="coerce")
        df_nafta["mes"] = df_nafta["Fecha"].dt.month
        df_nafta["anio"] = df_nafta["Fecha"].dt.year
        df_nafta_filtrado = df_nafta[
            (df_nafta["mes"] == mes) &
            (df_nafta["anio"] == año)
        ]
        
        if df_nafta_filtrado.empty:
            print(f"No hay datos de nafta para Uruguay en {mes}/{año}")
            nafta_uruguay = None
        else:
            nafta_uruguay = df_nafta_filtrado.iloc[0, 1]
        
        # Gasoil
        df_gasoil = pd.read_excel(url_excel, sheet_name="Gasoil 50-S")
        df_gasoil["Fecha"] = pd.to_datetime(df_gasoil.iloc[:, 0], dayfirst=True, format='mixed', errors="coerce")
        df_gasoil["mes"] = df_gasoil["Fecha"].dt.month
        df_gasoil["anio"] = df_gasoil["Fecha"].dt.year
        df_gasoil_filtrado = df_gasoil[
            (df_gasoil["mes"] == mes) &
            (df_gasoil["anio"] == año)
        ]
        
        if df_gasoil_filtrado.empty:
            print(f"No hay datos de gasoil para Uruguay en {mes}/{año}")
            gasoil_uruguay = None
            gasoil_uruguay_sin_iva = None
        else:
            gasoil_uruguay = df_gasoil_filtrado.iloc[0, 1]
            gasoil_uruguay_sin_iva = gasoil_uruguay / 1.22
        
        return nafta_uruguay, gasoil_uruguay, gasoil_uruguay_sin_iva
        
    except Exception as e:
        print(f"Error al obtener precios de Uruguay: {e}")
        import traceback
        traceback.print_exc()
        return None, None, None

def crear_dataframe_combustibles():
    """
    Crea DataFrames con todos los precios convertidos a pesos uruguayos.
    
    Returns:
        Tupla (df_nafta, df_gasoil) con los DataFrames ordenados por precio_mn
    """
    # DEBUG: Mostrar valores que se están usando
    print(f"\n{'='*60}")
    print(f"DEBUG - Valores de configuración:")
    print(f"  mes = {mes}")
    print(f"  año = {año}")
    print(f"{'='*60}\n")
    
    # Obtener tipos de cambio
    brl_uyu, arg_uyu = obtener_ratios(mes, año)
    
    # DEBUG: Mostrar resultados
    print(f"DEBUG - Ratios obtenidos:")
    print(f"  brl_uyu = {brl_uyu}")
    print(f"  arg_uyu = {arg_uyu}")
    print()
    
    if brl_uyu is None or arg_uyu is None:
        print("Error: No se pudieron obtener los tipos de cambio")
        return None, None
    
    # Leer datos de Argentina
    df_argy = leer_combustible_argentina()
    if df_argy is None:
        return None, None
    
    # Obtener precios
    nafta_argentina, gasoil_argentina = obtener_precios_argentina(df_argy)
    nafta_brasil, gasoil_brasil = obtener_precios_brasil()
    nafta_uruguay, gasoil_uruguay, gasoil_uruguay_sin_iva = obtener_precios_uruguay()
    
    # Calcular precios con descuentos de frontera
    descuento = 0.32
    nafta_uruguay_brasil = nafta_uruguay * (1 - imesi_bra) if nafta_uruguay else None
    nafta_uruguay_argentina = nafta_uruguay * (1 - imesi_arg) if nafta_uruguay else None
    
    # Crear lista de datos para nafta
    datos_nafta = []
    
    # Manejar precios de frontera: si son iguales, mostrar solo "Uruguay frontera"
    if nafta_uruguay_argentina is not None and nafta_uruguay_brasil is not None:
        if abs(nafta_uruguay_argentina - nafta_uruguay_brasil) < 0.01:  # Son iguales (con tolerancia)
            datos_nafta.append({
                'pais': 'Uruguay frontera',
                'precio_mo': nafta_uruguay_argentina,
                'cotizacion': 1.0,
                'precio_mn': nafta_uruguay_argentina * 1.0
            })
        else:  # Son distintos, mostrar ambos
            datos_nafta.append({
                'pais': 'Uruguay frontera Argentina',
                'precio_mo': nafta_uruguay_argentina,
                'cotizacion': 1.0,
                'precio_mn': nafta_uruguay_argentina * 1.0
            })
            datos_nafta.append({
                'pais': 'Uruguay frontera Brasil',
                'precio_mo': nafta_uruguay_brasil,
                'cotizacion': 1.0,
                'precio_mn': nafta_uruguay_brasil * 1.0
            })
    elif nafta_uruguay_argentina is not None:
        datos_nafta.append({
            'pais': 'Uruguay frontera Argentina',
            'precio_mo': nafta_uruguay_argentina,
            'cotizacion': 1.0,
            'precio_mn': nafta_uruguay_argentina * 1.0
        })
    elif nafta_uruguay_brasil is not None:
        datos_nafta.append({
            'pais': 'Uruguay frontera Brasil',
            'precio_mo': nafta_uruguay_brasil,
            'cotizacion': 1.0,
            'precio_mn': nafta_uruguay_brasil * 1.0
        })
    
    if nafta_uruguay is not None:
        datos_nafta.append({
            'pais': 'Uruguay',
            'precio_mo': nafta_uruguay,
            'cotizacion': 1.0,
            'precio_mn': nafta_uruguay
        })
    
    if nafta_brasil is not None:
        datos_nafta.append({
            'pais': 'Brasil',
            'precio_mo': nafta_brasil,
            'cotizacion': brl_uyu,
            'precio_mn': nafta_brasil * brl_uyu
        })
    
    if nafta_argentina is not None:
        datos_nafta.append({
            'pais': 'Argentina',
            'precio_mo': nafta_argentina,
            'cotizacion': arg_uyu,
            'precio_mn': nafta_argentina * arg_uyu
        })
    
    # Crear lista de datos para gasoil
    datos_gasoil = []
    
    if gasoil_uruguay is not None:
        datos_gasoil.append({
            'pais': 'Uruguay',
            'precio_mo': gasoil_uruguay,
            'cotizacion': 1.0,
            'precio_mn': gasoil_uruguay
        })
        
        if gasoil_uruguay_sin_iva is not None:
            datos_gasoil.append({
                'pais': 'Uruguay sin IVA',
                'precio_mo': gasoil_uruguay_sin_iva,
                'cotizacion': 1.0,
                'precio_mn': gasoil_uruguay_sin_iva
            })
    
    if gasoil_brasil is not None:
        datos_gasoil.append({
            'pais': 'Brasil',
            'precio_mo': gasoil_brasil,
            'cotizacion': brl_uyu,
            'precio_mn': gasoil_brasil * brl_uyu
        })
    
    if gasoil_argentina is not None:
        datos_gasoil.append({
            'pais': 'Argentina',
            'precio_mo': gasoil_argentina,
            'cotizacion': arg_uyu,
            'precio_mn': gasoil_argentina * arg_uyu
        })
    
    # Crear DataFrames
    df_nafta = pd.DataFrame(datos_nafta)
    df_gasoil = pd.DataFrame(datos_gasoil)
    
    # Función para obtener la bandera según el país
    def obtener_bandera(pais):
        if 'Uruguay' in pais:
            return 'https://public.flourish.studio/country-flags/svg/uy.svg'
        elif 'Argentina' in pais:
            return 'https://public.flourish.studio/country-flags/svg/ar.svg'
        elif 'Brasil' in pais:
            return 'https://public.flourish.studio/country-flags/svg/br.svg'
        else:
            return ''
    
    # Agregar columna de bandera
    if not df_nafta.empty:
        df_nafta['bandera'] = df_nafta['pais'].apply(obtener_bandera)
    
    if not df_gasoil.empty:
        df_gasoil['bandera'] = df_gasoil['pais'].apply(obtener_bandera)
    
    # Ordenar por precio_mn de mayor a menor
    if not df_nafta.empty:
        df_nafta = df_nafta.sort_values('precio_mn', ascending=False).reset_index(drop=True)
    
    if not df_gasoil.empty:
        df_gasoil = df_gasoil.sort_values('precio_mn', ascending=False).reset_index(drop=True)
    
    return df_nafta, df_gasoil

def subir_a_google_sheets(df, sheet_id, nombre_hoja="Sheet1"):
    """
    Sube un DataFrame a Google Sheets, reemplazando los datos existentes.
    
    Args:
        df: DataFrame a subir
        sheet_id: ID de la hoja de Google Sheets
        nombre_hoja: Nombre de la hoja dentro del documento (por defecto: "Sheet1")
    
    Returns:
        True si se subió correctamente, False en caso contrario
    """
    if sheet_id is None or not sheet_id:
        return False
    
    if df is None or df.empty:
        print("No hay datos para subir a Google Sheets")
        return False
    
    try:
        import gspread
        from google.oauth2.service_account import Credentials
        
        # Verificar si existe el archivo de credenciales
        credenciales_file = "credentials_sheets.json"
        if not os.path.exists(credenciales_file):
            print(f"Archivo de credenciales no encontrado: {credenciales_file}")
            print("Necesitas crear credenciales de Google Sheets API.")
            print("Ve a: https://console.cloud.google.com/")
            return False
        
        # Autenticación
        scope = [
            "https://spreadsheets.google.com/feeds",
            "https://www.googleapis.com/auth/drive"
        ]
        creds = Credentials.from_service_account_file(credenciales_file, scopes=scope)
        client = gspread.authorize(creds)
        
        # Abrir la hoja
        sheet = client.open_by_key(sheet_id)
        
        # Seleccionar o crear la hoja
        try:
            worksheet = sheet.worksheet(nombre_hoja)
        except gspread.exceptions.WorksheetNotFound:
            worksheet = sheet.add_worksheet(title=nombre_hoja, rows=1000, cols=20)
        
        # Limpiar datos existentes
        worksheet.clear()
        
        # Subir encabezados
        headers = list(df.columns)
        worksheet.append_row(headers)
        
        # Subir datos
        valores = df.values.tolist()
        if valores:
            worksheet.append_rows(valores)
        
        print(f"Datos subidos a Google Sheets: {sheet.title} - {nombre_hoja}")
        print(f"URL: https://docs.google.com/spreadsheets/d/{sheet_id}/edit")
        return True
        
    except ImportError as e:
        print(f"Error: gspread no está instalado. Instala con: python -m pip install gspread google-auth")
        print(f"Detalle: {e}")
        return False
    except Exception as e:
        print(f"Error al subir a Google Sheets: {e}")
        import traceback
        traceback.print_exc()
        return False

def copiar_a_drive(archivo, ruta_drive_local=None, id_carpeta=None):
    """
    Copia un archivo a la carpeta de Google Drive.
    Primero intenta con ruta local, luego con API de Google Drive.
    
    Args:
        archivo: Nombre del archivo a copiar
        ruta_drive_local: Ruta local de la carpeta de Drive (si está sincronizada)
        id_carpeta: ID de la carpeta de Google Drive
    
    Returns:
        True si se copió correctamente, False en caso contrario
    """
    if not os.path.exists(archivo):
        print(f"Archivo no encontrado: {archivo}")
        return False
    
    # Primero intentar con ruta local (más rápido si está sincronizada)
    if ruta_drive_local and os.path.exists(ruta_drive_local):
        try:
            destino = os.path.join(ruta_drive_local, os.path.basename(archivo))
            shutil.copy2(archivo, destino)
            print(f"Archivo copiado a Drive (local): {destino}")
            return True
        except Exception as e:
            print(f"Error al copiar a ruta local: {e}")
    
    # Si no funciona la ruta local, intentar con API de Google Drive
    if id_carpeta:
        try:
            from pydrive2.auth import GoogleAuth
            from pydrive2.drive import GoogleDrive
            
            # Autenticación
            gauth = GoogleAuth()
            gauth.LoadCredentialsFile("credentials.json")
            
            if gauth.credentials is None:
                # Autenticar si no hay credenciales
                gauth.LocalWebserverAuth()
            elif gauth.access_token_expired:
                # Refrescar si expiró
                gauth.Refresh()
            else:
                gauth.Authorize()
            
            # Guardar credenciales
            gauth.SaveCredentialsFile("credentials.json")
            
            drive = GoogleDrive(gauth)
            
            # Buscar si el archivo ya existe en la carpeta
            nombre_archivo = os.path.basename(archivo)
            file_list = drive.ListFile({
                'q': f"'{id_carpeta}' in parents and title='{nombre_archivo}' and trashed=false"
            }).GetList()
            
            # Si existe, eliminarlo para sobreescribir
            if file_list:
                for file_drive in file_list:
                    file_drive.Delete()
            
            # Subir el archivo nuevo
            file_drive = drive.CreateFile({
                'title': nombre_archivo,
                'parents': [{'id': id_carpeta}]
            })
            file_drive.SetContentFile(archivo)
            file_drive.Upload()
            
            print(f"Archivo subido a Google Drive: {nombre_archivo}")
            return True
            
        except ImportError:
            # PyDrive2 no está instalado, pero no es crítico si no se usa
            # No mostrar mensaje, solo retornar False silenciosamente
            return False
        except Exception as e:
            print(f"Error al subir a Google Drive: {e}")
            return False
    
    return False

if __name__ == "__main__":
    print("=" * 60)
    print("ANÁLISIS DE PRECIOS DE COMBUSTIBLES MERCOSUR")
    print("=" * 60)
    
    df_nafta, df_gasoil = crear_dataframe_combustibles()
    
    if df_nafta is not None and not df_nafta.empty:
        print("\n" + "=" * 60)
        print("PRECIOS DE NAFTA (ordenados de mayor a menor)")
        print("=" * 60)
        print(df_nafta.to_string(index=False))
        
        # Guardar en Excel
        try:
            df_nafta.to_excel('nafta_mercosur.xlsx', index=False, engine='openpyxl')
            print("\nDatos guardados en: nafta_mercosur.xlsx")
        except PermissionError:
            print("\nError: El archivo 'nafta_mercosur.xlsx' está abierto. Ciérralo e intenta de nuevo.")
        except Exception as e:
            print(f"\nError al guardar nafta_mercosur.xlsx: {e}")
        
        # Copiar a Drive
        copiar_a_drive('nafta_mercosur.xlsx', RUTA_DRIVE_LOCAL, ID_CARPETA_DRIVE)
        
        # Subir a Google Sheets para Flourish
        if ID_SHEET_NAFTA:
            subir_a_google_sheets(df_nafta, ID_SHEET_NAFTA, "Datos")
    else:
        print("\nNo se pudieron obtener los precios de nafta")
    
    if df_gasoil is not None and not df_gasoil.empty:
        print("\n" + "=" * 60)
        print("PRECIOS DE GASOIL (ordenados de mayor a menor)")
        print("=" * 60)
        print(df_gasoil.to_string(index=False))
        
        # Guardar en Excel
        try:
            df_gasoil.to_excel('gasoil_mercosur.xlsx', index=False, engine='openpyxl')
            print("\nDatos guardados en: gasoil_mercosur.xlsx")
        except PermissionError:
            print("\nError: El archivo 'gasoil_mercosur.xlsx' está abierto. Ciérralo e intenta de nuevo.")
        except Exception as e:
            print(f"\nError al guardar gasoil_mercosur.xlsx: {e}")
        
        # Copiar a Drive
        copiar_a_drive('gasoil_mercosur.xlsx', RUTA_DRIVE_LOCAL, ID_CARPETA_DRIVE)
        
        # Subir a Google Sheets para Flourish
        if ID_SHEET_GASOIL:
            subir_a_google_sheets(df_gasoil, ID_SHEET_GASOIL, "Datos")
    else:
        print("\nNo se pudieron obtener los precios de gasoil")
