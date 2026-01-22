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
5) Insertar directamente en SQLite (sin Excel de prueba).
6) Actualizar nombre de Argentina (ID 22) a "Argentina (CCL)".
"""

import os
import sqlite3
import sys
from datetime import datetime

import pandas as pd
from bcchapi import Siete

# Configuración de base de datos
DB_NAME = "series_tiempo.db"

# Credenciales del BCCH
BCCH_USER = "joaquin.forrisi@gmail.com"
BCCH_PASSWORD = "Joaquin.13"

# Configuración de países
PAISES_CONFIG = [
    {
        "codigo_serie": "F072.MXN.USD.N.O.D",
        "id": 26,
        "nombre": "Tipo de cambio USD/MXN (México)",
        "unidad": "MXN por USD",
        "moneda": "MXN"
    },
    {
        "codigo_serie": "F072.COP.USD.N.O.D",
        "id": 27,
        "nombre": "Tipo de cambio USD/COP (Colombia)",
        "unidad": "COP por USD",
        "moneda": "COP"
    },
    {
        "codigo_serie": "F072.AUD.USD.N.O.D",
        "id": 28,
        "nombre": "Tipo de cambio USD/AUD (Australia)",
        "unidad": "AUD por USD",
        "moneda": "AUD"
    },
    {
        "codigo_serie": "F072.NZD.USD.N.O.D",
        "id": 29,
        "nombre": "Tipo de cambio USD/NZD (Nueva Zelanda)",
        "unidad": "NZD por USD",
        "moneda": "NZD"
    },
    {
        "codigo_serie": "F072.ZAR.USD.N.O.D",
        "id": 30,
        "nombre": "Tipo de cambio USD/ZAR (Sudáfrica)",
        "unidad": "ZAR por USD",
        "moneda": "ZAR"
    },
    {
        "codigo_serie": "F072.PYG.USD.N.O.D",
        "id": 31,
        "nombre": "Tipo de cambio USD/PYG (Paraguay)",
        "unidad": "PYG por USD",
        "moneda": "PYG"
    },
    {
        "codigo_serie": "F072.ARS.USD.N.O.D",
        "id": 32,
        "nombre": "Tipo de cambio USD/ARS (Argentina - Oficial)",
        "unidad": "ARS por USD",
        "moneda": "ARS"
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
        # El DataFrame de bcchapi generalmente tiene el índice como fecha
        df = df.reset_index()
        
        # Identificar columna de fecha y valor
        if 'index' in df.columns:
            df.rename(columns={'index': 'Fecha'}, inplace=True)
        elif 'Fecha' not in df.columns and len(df.columns) > 0:
            # Asumir que la primera columna es la fecha
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


def completar_dias_faltantes(df: pd.DataFrame, columna_fecha: str = 'Fecha', columna_valor: str = 'Tipo_Cambio') -> pd.DataFrame:
    """
    Completa días faltantes en una serie diaria usando forward fill.
    """
    if df is None or df.empty:
        return df
    
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


def preparar_datos_maestro_precios(df_tc: pd.DataFrame, maestro_id: int) -> pd.DataFrame:
    """Prepara el DataFrame para maestro_precios."""
    if df_tc is None or df_tc.empty:
        return pd.DataFrame(columns=["maestro_id", "fecha", "valor"])
    
    df_precios = df_tc.copy()
    df_precios["maestro_id"] = maestro_id
    df_precios = df_precios[["maestro_id", "Fecha", "Tipo_Cambio"]]
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
            (id, nombre, tipo, fuente, periodicidad, unidad, categoria, activo, es_cotizacion, nominal_real, moneda)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                1,  # es_cotizacion
                "N",  # nominal_real
                pais_config["moneda"]
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


def actualizar_nombre_argentina_ccl():
    """Actualiza el nombre del ID 22 (Argentina) para agregar 'CCL'."""
    print("\n[INFO] Actualizando nombre de Argentina (ID 22) a 'Argentina (CCL)'...")
    
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    try:
        cursor.execute(
            """
            UPDATE maestro 
            SET nombre = 'Tipo de cambio USD/ARS (Argentina - CCL)'
            WHERE id = 22
            """
        )
        
        if cursor.rowcount > 0:
            print(f"[OK] Nombre actualizado para ID 22")
        else:
            print(f"[WARN] No se encontró registro con ID 22")
        
        conn.commit()
    except Exception as e:
        conn.rollback()
        print(f"[ERROR] Error al actualizar nombre: {e}")
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
        
        # Completar días faltantes
        df = completar_dias_faltantes(df, columna_fecha='Fecha', columna_valor='Tipo_Cambio')
        
        # Validar fechas
        df = validar_fechas(df)
        
        # Preparar datos para inserción
        df_maestro = pd.DataFrame([{
            "id": pais_config["id"],
            "nombre": pais_config["nombre"],
            "tipo": "M",
            "fuente": "BCCH_API",
            "periodicidad": "D",
            "unidad": pais_config["unidad"],
            "categoria": "Macro - Tipo de cambio",
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
    print("ACTUALIZACION DE DATOS: TIPOS DE CAMBIO MULTIPAIES (BCCH)")
    print("=" * 60)
    
    crear_base_datos()
    
    # Actualizar nombre de Argentina (ID 22)
    actualizar_nombre_argentina_ccl()
    
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
