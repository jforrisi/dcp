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
5) Insertar directamente en SQLite (sin Excel de prueba).
"""

import os
import sqlite3
import sys
import re
from datetime import datetime

import pandas as pd
import requests

# Configuración de base de datos
DB_NAME = "series_tiempo.db"

# Código de serie del BCRP para TC Interbancario (Venta)
CODIGO_SERIE_BCRP = "PD04638PD"

# Base URL de la API del BCRP
BASE_URL_API = "https://estadisticas.bcrp.gob.pe/estadisticas/series/api"

# Datos del maestro
MAESTRO_TIPO_CAMBIO_PERU = {
    "id": 24,  # Verificar que no esté en uso
    "nombre": "Tipo de cambio USD/PEN (Perú - TC Interbancario Venta)",
    "tipo": "M",  # variable macro
    "fuente": "BCRP_API",
    "periodicidad": "D",  # diario
    "unidad": "PEN por USD",
    "categoria": "Macro - Tipo de cambio",
    "activo": True,
}

# Mapeo de meses en español (por si acaso vienen en formato "02Ene97")
MESES_BCRP = {
    'Ene': '01', 'Feb': '02', 'Mar': '03', 'Abr': '04',
    'May': '05', 'Jun': '06', 'Jul': '07', 'Ago': '08',
    'Set': '09', 'Oct': '10', 'Nov': '11', 'Dic': '12'
}


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
        # Formato: /api/[código]/[formato]/[periodo_inicial]/[periodo_final]/[idioma]
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
                    # Convertir a formato estándar
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
            print(f"[DEBUG] Estructura de respuesta: {type(data)}")
            if isinstance(data, dict):
                print(f"[DEBUG] Keys: {list(data.keys())}")
                # Imprimir muestra de la estructura para debugging
                if len(str(data)) < 500:
                    print(f"[DEBUG] Contenido: {data}")
            return None
        
        df = pd.DataFrame(datos)
        
        # Eliminar duplicados por fecha (mantener el último)
        df = df.drop_duplicates(subset='Fecha', keep='last')
        
        # Ordenar por fecha
        df = df.sort_values('Fecha').reset_index(drop=True)
        
        print(f"[OK] Se extrajeron {len(df)} registros")
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


def completar_dias_faltantes(df: pd.DataFrame, columna_fecha: str = 'Fecha', columna_valor: str = 'Tipo_Cambio') -> pd.DataFrame:
    """
    Completa días faltantes en una serie diaria usando forward fill.
    """
    print("\n[INFO] Completando días faltantes en serie diaria...")
    
    df = df.copy()
    df[columna_fecha] = pd.to_datetime(df[columna_fecha])
    df = df.sort_values(columna_fecha).reset_index(drop=True)
    
    fecha_min = df[columna_fecha].min()
    fecha_max = df[columna_fecha].max()
    
    rango_completo = pd.date_range(start=fecha_min, end=fecha_max, freq='D')
    df_completo = pd.DataFrame({columna_fecha: rango_completo})
    
    df_completo = df_completo.merge(
        df[[columna_fecha, columna_valor]], 
        on=columna_fecha, 
        how='left'
    )
    
    df_completo[columna_valor] = df_completo[columna_valor].ffill()
    
    dias_originales = len(df)
    dias_completados = len(df_completo)
    dias_agregados = dias_completados - dias_originales
    
    if dias_agregados > 0:
        print(f"[INFO] Se completaron {dias_agregados} días faltantes (de {dias_originales} a {dias_completados} días)")
        print(f"   Rango: {fecha_min.strftime('%d/%m/%Y')} a {fecha_max.strftime('%d/%m/%Y')}")
    else:
        print(f"[OK] No había días faltantes ({dias_originales} días en el rango)")
    
    return df_completo


def validar_fechas(df: pd.DataFrame) -> pd.DataFrame:
    """Valida que todas las fechas sean válidas (OBLIGATORIO según README)."""
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


def preparar_datos_maestro_precios(df_tc: pd.DataFrame, maestro_id: int) -> pd.DataFrame:
    """Prepara el DataFrame para maestro_precios."""
    df_precios = df_tc.copy()
    df_precios["maestro_id"] = maestro_id
    df_precios = df_precios[["maestro_id", "Fecha", "Tipo_Cambio"]]
    df_precios.columns = ["maestro_id", "fecha", "valor"]
    
    df_precios["valor"] = pd.to_numeric(df_precios["valor"], errors="coerce")
    df_precios = df_precios.dropna(subset=["valor"])
    return df_precios


def mostrar_resumen(df_maestro: pd.DataFrame, df_precios: pd.DataFrame) -> None:
    """Muestra resumen de los datos que se van a insertar."""
    print("\n" + "=" * 60)
    print("RESUMEN DE DATOS A INSERTAR")
    print("=" * 60)

    print("\nTABLA: maestro")
    print("-" * 60)
    print(df_maestro.to_string(index=False))

    print("\nTABLA: maestro_precios")
    print("-" * 60)
    print(f"Total de registros: {len(df_precios)}")
    print("\nPrimeros 5 registros:")
    print(df_precios.head().to_string(index=False))
    print("\nÚltimos 5 registros:")
    print(df_precios.tail().to_string(index=False))
    print(f"\nRango de fechas: {df_precios['fecha'].min()} a {df_precios['fecha'].max()}")
    print(
        f"Valores: min={df_precios['valor'].min():.2f}, "
        f"max={df_precios['valor'].max():.2f}, "
        f"promedio={df_precios['valor'].mean():.2f}"
    )
    print("=" * 60)


def insertar_en_bd(df_maestro: pd.DataFrame, df_precios: pd.DataFrame) -> None:
    """Inserta los datos en la base de datos SQLite."""
    print("\n[INFO] Insertando datos en la base de datos...")

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    try:
        # Insertar en maestro
        maestro_id = int(df_maestro.iloc[0]["id"])
        maestro_row = df_maestro.iloc[0]
        
        cursor.execute(
            """
            INSERT OR REPLACE INTO maestro (id, nombre, tipo, fuente, periodicidad, unidad, categoria, activo)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
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
            )
        )
        
        print(f"[OK] Insertado/actualizado registro en tabla 'maestro' (id={maestro_id})")

        # Eliminar registros existentes para este maestro_id (para reemplazar completamente)
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
    print("ACTUALIZACION DE DATOS: TIPO DE CAMBIO USD/PEN (PERÚ)")
    print("=" * 60)

    crear_base_datos()

    # Extraer datos desde API del BCRP (desde el primer dato disponible)
    print("\n[INFO] Extrayendo datos del Banco Central de Reserva del Perú (API)...")
    df = extraer_bcrp_peru()
    
    if df is None or df.empty:
        print("No se pudieron extraer los datos")
        return
    
    # Mostrar primeros y últimos datos de la serie cruda
    print("\n[INFO] Datos de la serie cruda:")
    print("\nPrimeros datos:")
    print(df.head())
    print("\nÚltimos datos:")
    print(df.tail())
    
    # COMPLETAR DÍAS FALTANTES (OBLIGATORIO para series diarias según README)
    df = completar_dias_faltantes(df, columna_fecha='Fecha', columna_valor='Tipo_Cambio')
    
    # Validar fechas
    df = validar_fechas(df)

    # Preparar datos para inserción
    df_maestro = pd.DataFrame([MAESTRO_TIPO_CAMBIO_PERU])
    df_precios = preparar_datos_maestro_precios(df, MAESTRO_TIPO_CAMBIO_PERU["id"])

    # Mostrar resumen (sin Excel)
    mostrar_resumen(df_maestro, df_precios)
    
    # Insertar directamente en BD (sin confirmación, sin Excel)
    insertar_en_bd(df_maestro, df_precios)


if __name__ == "__main__":
    main()
