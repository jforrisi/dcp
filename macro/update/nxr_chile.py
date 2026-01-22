# -*- coding: utf-8 -*-
"""
Script: nxr_chile
----------------
Actualiza la base de datos con la serie de tipo de cambio USD/CLP del Banco Central 
de Chile (BCCH), usando su API oficial (bcchapi).

1) Extraer datos desde API del BCCH usando bcchapi (desde 2010-01-01).
2) Filtrar valores no numéricos.
3) Completar días faltantes (forward fill).
4) Validar fechas.
5) Insertar directamente en SQLite (sin Excel de prueba).
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

# Código de serie del BCCH para Dólar Observado (puede variar, se busca automáticamente)
# Código típico: "F032.TCO.PRE.Z.D" o similar
CODIGO_SERIE_BCCH = None  # Se buscará automáticamente

# Datos del maestro
MAESTRO_TIPO_CAMBIO_CHILE = {
    "id": 25,  # Verificar que no esté en uso
    "nombre": "Tipo de cambio USD/CLP (Chile - Dólar Observado)",
    "tipo": "M",  # variable macro
    "fuente": "BCCH_API",
    "periodicidad": "D",  # diario
    "unidad": "CLP por USD",
    "categoria": "Macro - Tipo de cambio",
    "activo": True,
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


def buscar_codigo_serie(siete: Siete):
    """
    Busca el código de serie para el Dólar Observado en el BCCH.
    
    Returns:
        Código de serie (str) o None si no se encuentra
    """
    print("[INFO] Buscando código de serie para 'Dólar Observado'...")
    
    try:
        df_busqueda = siete.buscar("Dólar Observado")
        
        if df_busqueda is None or df_busqueda.empty:
            print("[WARN] No se encontraron series con 'Dólar Observado'")
            # Intentar otras búsquedas
            df_busqueda = siete.buscar("dolar")
            if df_busqueda is None or df_busqueda.empty:
                return None
        
        print(f"[INFO] Se encontraron {len(df_busqueda)} series:")
        print(df_busqueda.head())
        
        # Buscar la serie diaria (frecuencia 'D' o 'DAILY')
        # Priorizar series diarias sobre anuales o mensuales
        serie_diaria = None
        
        for idx, row in df_busqueda.iterrows():
            # Intentar diferentes formas de acceder a las columnas
            if isinstance(row, pd.Series):
                codigo = str(row.get('seriesId', row.get('codigo', row.iloc[0] if len(row) > 0 else '')))
                frecuencia = str(row.get('frequencyCode', row.get('frecuencia', row.iloc[-1] if len(row) > 1 else '')))
            else:
                # Si es una lista o tupla, buscar por posición
                codigo = str(row.get('seriesId', '')) if hasattr(row, 'get') else (str(row[0]) if len(row) > 0 else '')
                frecuencia = str(row.get('frequencyCode', '')) if hasattr(row, 'get') else (str(row[-1]) if len(row) > 1 else '')
            
            # Buscar serie diaria (DAILY o D)
            if frecuencia.upper() in ['DAILY', 'D', 'DIARIA', 'DIARIO']:
                if 'TCO' in codigo.upper() or 'DOLAR' in codigo.upper():
                    print(f"[OK] Código diario encontrado: {codigo}")
                    return codigo
                elif serie_diaria is None:
                    serie_diaria = codigo  # Guardar primera serie diaria encontrada
        
        # Si encontramos una serie diaria (aunque no tenga TCO), usarla
        if serie_diaria:
            print(f"[INFO] Usando serie diaria encontrada: {serie_diaria}")
            return serie_diaria
        
        # Si no se encuentra diaria, buscar cualquier serie con TCO
        for idx, row in df_busqueda.iterrows():
            if isinstance(row, pd.Series):
                codigo = str(row.get('seriesId', row.get('codigo', row.iloc[0] if len(row) > 0 else '')))
            else:
                codigo = str(row.get('seriesId', '')) if hasattr(row, 'get') else (str(row[0]) if len(row) > 0 else '')
            
            if 'TCO' in codigo.upper():
                print(f"[INFO] Usando serie con TCO: {codigo}")
                return codigo
        
        # Si no se encuentra específicamente, tomar el primero
        if len(df_busqueda) > 0:
            primer_row = df_busqueda.iloc[0]
            if isinstance(primer_row, pd.Series):
                primer_codigo = str(primer_row.get('seriesId', primer_row.get('codigo', primer_row.iloc[0] if len(primer_row) > 0 else '')))
            else:
                primer_codigo = str(primer_row.get('seriesId', '')) if hasattr(primer_row, 'get') else (str(primer_row[0]) if len(primer_row) > 0 else '')
            print(f"[WARN] Usando primer código encontrado (puede no ser diario): {primer_codigo}")
            return primer_codigo
        
        return None
        
    except Exception as e:
        print(f"[ERROR] Error al buscar código de serie: {e}")
        import traceback
        traceback.print_exc()
        return None


def extraer_bcch_chile(fecha_inicio="2010-01-01", fecha_fin=None):
    """
    Extrae datos de tipo de cambio del Banco Central de Chile usando bcchapi.
    
    Args:
        fecha_inicio: Fecha de inicio en formato YYYY-MM-DD (por defecto: 2010-01-01)
        fecha_fin: Fecha de fin en formato YYYY-MM-DD (por defecto: hoy)
        
    Returns:
        DataFrame con columnas: Fecha, Tipo_Cambio
    """
    print(f"[INFO] Extrayendo datos desde API del BCCH...")
    
    if fecha_fin is None:
        fecha_fin = datetime.today().strftime("%Y-%m-%d")
    
    try:
        # Inicializar conexión con BCCH
        print(f"[INFO] Conectando al BCCH con usuario: {BCCH_USER}")
        siete = Siete(BCCH_USER, BCCH_PASSWORD)
        
        # Buscar código de serie si no está definido
        codigo_serie = CODIGO_SERIE_BCCH
        if codigo_serie is None:
            codigo_serie = buscar_codigo_serie(siete)
            if codigo_serie is None:
                print("[WARN] No se pudo encontrar el código de serie automáticamente")
                print("[INFO] Intentando con código común: F032.TCO.PRE.Z.D")
                codigo_serie = "F032.TCO.PRE.Z.D"
        
        print(f"[INFO] Usando código de serie: {codigo_serie}")
        print(f"[INFO] Rango solicitado: {fecha_inicio} a {fecha_fin}")
        
        # Obtener datos
        df = siete.cuadro(
            series=[codigo_serie],
            nombres=["dolar_observado"],
            desde=fecha_inicio,
            hasta=fecha_fin
        )
        
        if df is None or df.empty:
            print("[ERROR] No se obtuvieron datos del BCCH")
            return None
        
        print(f"[OK] Se obtuvieron {len(df)} registros del BCCH")
        
        # El DataFrame de bcchapi generalmente tiene:
        # - Una columna de fecha (índice o columna 'Fecha')
        # - Una columna con el valor (nombre de la serie o 'dolar_observado')
        
        # Preparar DataFrame estándar
        datos = []
        
        # Verificar estructura del DataFrame
        print(f"[DEBUG] Columnas del DataFrame: {list(df.columns)}")
        print(f"[DEBUG] Índice: {df.index.name if df.index.name else 'Sin nombre'}")
        print(f"[DEBUG] Primeras filas:")
        print(df.head())
        
        # Intentar diferentes estructuras posibles
        if 'dolar_observado' in df.columns:
            # Estructura: columna de fecha + columna 'dolar_observado'
            if df.index.name and 'fecha' in str(df.index.name).lower():
                df['Fecha'] = df.index
            elif 'Fecha' in df.columns:
                pass  # Ya existe
            else:
                # Asumir que el índice es la fecha
                df = df.reset_index()
                if 'index' in df.columns:
                    df.rename(columns={'index': 'Fecha'}, inplace=True)
            
            df['Tipo_Cambio'] = df['dolar_observado']
        
        elif len(df.columns) == 1:
            # Solo una columna de valores, el índice es la fecha
            df = df.reset_index()
            df.columns = ['Fecha', 'Tipo_Cambio']
        
        else:
            # Intentar usar la primera columna como fecha y la segunda como valor
            df = df.reset_index()
            if len(df.columns) >= 2:
                df.columns = ['Fecha'] + list(df.columns[1:])
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
        print(f"   Rango: {df['Fecha'].min().strftime('%d/%m/%Y')} a {df['Fecha'].max().strftime('%d/%m/%Y')}")
        
        return df
        
    except Exception as e:
        print(f"[ERROR] Error al obtener datos del BCCH: {e}")
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
    print("ACTUALIZACION DE DATOS: TIPO DE CAMBIO USD/CLP (CHILE)")
    print("=" * 60)

    crear_base_datos()

    # Extraer datos desde API del BCCH (desde 2010-01-01)
    print("\n[INFO] Extrayendo datos del Banco Central de Chile (API)...")
    df = extraer_bcch_chile(fecha_inicio="2010-01-01", fecha_fin=None)
    
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
    df_maestro = pd.DataFrame([MAESTRO_TIPO_CAMBIO_CHILE])
    df_precios = preparar_datos_maestro_precios(df, MAESTRO_TIPO_CAMBIO_CHILE["id"])

    # Mostrar resumen (sin Excel)
    mostrar_resumen(df_maestro, df_precios)
    
    # Insertar directamente en BD (sin confirmación, sin Excel)
    insertar_en_bd(df_maestro, df_precios)


if __name__ == "__main__":
    main()
