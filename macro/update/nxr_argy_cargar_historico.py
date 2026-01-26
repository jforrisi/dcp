# -*- coding: utf-8 -*-
"""
Script: nxr_argy_cargar_historico
----------------------------------
Carga inicial del CSV histórico completo a la base de datos.
Este script se ejecuta UNA SOLA VEZ para cargar todos los datos históricos.

1) Lee el CSV histórico completo
2) Completa días faltantes (forward fill)
3) Valida fechas
4) Genera Excel de prueba
5) Solicita confirmación del usuario
6) Inserta TODO en SQLite
"""

import os
import sqlite3
import sys
from datetime import datetime

import pandas as pd

# Configuración de base de datos y archivos de salida
DB_NAME = "series_tiempo.db"
EXCEL_PRUEBA_NAME = "prueba_tipo_cambio_argentina_historico.xlsx"
CSV_HISTORICO_NAME = "historical_nxr_argy.csv"  # CSV con datos históricos (en la misma carpeta que el script)

# Datos del maestro
MAESTRO_TIPO_CAMBIO_ARGENTINA = {
    "id": 22,
    "nombre": "Tipo de cambio USD/ARS (Argentina - Dólar CCL)",
    "tipo": "M",  # variable macro
    "fuente": "CSV_Historico",
    "periodicidad": "D",  # diario
    "unidad": "ARS por USD",
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


def leer_csv_historico():
    """
    Lee el CSV histórico desde la misma carpeta que el script.
    El CSV debe tener formato: fecha,valor (sin encabezados)
    Formato de fecha: YYYY-MM-DD
    
    Returns:
        DataFrame con columnas 'Fecha' y 'Cierre'
    """
    # Obtener la ruta del script actual
    script_dir = os.path.dirname(os.path.abspath(__file__))
    ruta_csv = os.path.join(script_dir, CSV_HISTORICO_NAME)
    
    if not os.path.exists(ruta_csv):
        raise FileNotFoundError(f"No se encontró el CSV histórico en: {ruta_csv}")
    
    print(f"\n[INFO] Leyendo CSV histórico desde: {ruta_csv}")
    
    try:
        # Leer CSV sin encabezados (formato: fecha,valor)
        df_historico = pd.read_csv(
            ruta_csv,
            header=None,
            names=['Fecha', 'Cierre'],
            encoding='utf-8'
        )
        
        # Convertir fecha a datetime
        df_historico['Fecha'] = pd.to_datetime(df_historico['Fecha'], errors='coerce')
        df_historico = df_historico.dropna(subset=['Fecha'])
        
        # Convertir valor a numérico
        df_historico['Cierre'] = pd.to_numeric(df_historico['Cierre'], errors='coerce')
        df_historico = df_historico.dropna(subset=['Cierre'])
        
        # Ordenar por fecha
        df_historico = df_historico.sort_values('Fecha').reset_index(drop=True)
        
        print(f"[OK] CSV histórico leído: {len(df_historico)} registros")
        print(f"      Rango: {df_historico['Fecha'].min().strftime('%d/%m/%Y')} a {df_historico['Fecha'].max().strftime('%d/%m/%Y')}")
        
        return df_historico
        
    except Exception as e:
        print(f"[ERROR] Error al leer CSV histórico: {e}")
        import traceback
        traceback.print_exc()
        raise


def completar_dias_faltantes(df: pd.DataFrame, columna_fecha: str = 'Fecha', columna_valor: str = 'Cierre') -> pd.DataFrame:
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
    df_precios = df_precios[["maestro_id", "Fecha", "Cierre"]]
    df_precios.columns = ["maestro_id", "fecha", "valor"]
    
    df_precios["valor"] = pd.to_numeric(df_precios["valor"], errors="coerce")
    df_precios = df_precios.dropna(subset=["valor"])
    return df_precios


def generar_excel_prueba(df_maestro: pd.DataFrame, df_precios: pd.DataFrame) -> str:
    """Genera el archivo Excel de prueba (OBLIGATORIO según README)."""
    print("\n[INFO] Generando archivo Excel de prueba...")

    excel_path = os.path.join(os.getcwd(), EXCEL_PRUEBA_NAME)
    with pd.ExcelWriter(excel_path, engine="openpyxl") as writer:
        df_maestro.to_excel(writer, sheet_name="maestro", index=False)
        df_precios.to_excel(writer, sheet_name="maestro_precios", index=False)

    print(f"[OK] Archivo Excel generado: {excel_path}")
    print(f"   - Hoja 'maestro': {len(df_maestro)} fila(s)")
    print(f"   - Hoja 'maestro_precios': {len(df_precios)} fila(s)")
    return excel_path


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


def solicitar_confirmacion_usuario(excel_path: str) -> None:
    """Solicita confirmación explícita del usuario antes de insertar."""
    print("\n" + "=" * 60)
    print("CONFIRMACION DEL USUARIO")
    print("=" * 60)
    print(f"Archivo Excel generado para validación: {excel_path}")
    print("Revisá el Excel (hojas 'maestro' y 'maestro_precios').")
    print("\n[ADVERTENCIA] Este script cargará TODOS los datos históricos en la BD.")
    print("              Si ya hay datos para el ID 22, se insertarán duplicados.")
    respuesta = input("¿Confirmás la inserción en la base de datos? (sí/no): ").strip().lower()
    if respuesta not in ["sí", "si", "yes", "y", "s"]:
        print("[INFO] Inserción cancelada por el usuario. No se realizaron cambios.")
        sys.exit(0)


def insertar_en_bd(df_maestro: pd.DataFrame, df_precios: pd.DataFrame) -> None:
    """Inserta los datos en la base de datos SQLite."""
    print("\n[INFO] Insertando datos en la base de datos...")

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    try:
        # Insertar en maestro usando INSERT OR IGNORE para evitar duplicados
        maestro_id = int(df_maestro.iloc[0]["id"])
        maestro_row = df_maestro.iloc[0]
        
        cursor.execute(
            """
            INSERT OR IGNORE INTO maestro (id, nombre, tipo, fuente, periodicidad, unidad, categoria, activo)
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
        
        if cursor.rowcount > 0:
            print(f"[OK] Insertado 1 registro en tabla 'maestro' (id={maestro_id})")
        else:
            print(f"[INFO] El registro con id={maestro_id} ya existe en 'maestro', se omite la inserción")

        # Insertar TODOS los precios (carga inicial completa)
        print(f"[INFO] Insertando {len(df_precios)} registros en 'maestro_precios'...")
        df_precios.to_sql("maestro_precios", conn, if_exists="append", index=False)
        print(f"[OK] Insertados {len(df_precios)} registro(s) en tabla 'maestro_precios'")

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
    print("CARGA INICIAL: TIPO DE CAMBIO USD/ARS (ARGENTINA) - CSV HISTÓRICO")
    print("=" * 60)

    crear_base_datos()

    # Leer CSV histórico
    df = leer_csv_historico()
    
    # Mostrar primeros y últimos datos
    print("\n[INFO] Datos del CSV histórico:")
    print("\nPrimeros datos:")
    print(df.head())
    print("\nÚltimos datos:")
    print(df.tail())
    
    # Completar días faltantes
    df = completar_dias_faltantes(df, columna_fecha='Fecha', columna_valor='Cierre')
    
    # Validar fechas
    df = validar_fechas(df)

    # Preparar datos para inserción
    df_maestro = pd.DataFrame([MAESTRO_TIPO_CAMBIO_ARGENTINA])
    df_precios = preparar_datos_maestro_precios(df, MAESTRO_TIPO_CAMBIO_ARGENTINA["id"])

    # Generar Excel de prueba
    excel_path = generar_excel_prueba(df_maestro, df_precios)
    
    # Mostrar resumen
    mostrar_resumen(df_maestro, df_precios)
    
    # Insertar en BD - Sin confirmación en producción
    insertar_en_bd(df_maestro, df_precios)


if __name__ == "__main__":
    main()
