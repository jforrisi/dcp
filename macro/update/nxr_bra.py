# -*- coding: utf-8 -*-
"""
Script: nxr_bra
---------------
Actualiza la base de datos con la serie de tipo de cambio USD/BRL del Banco Central de Brasil (BCB),
siguiendo el flujo del README:

1) Extraer datos desde API del BCB.
2) Completar días faltantes (forward fill para feriados/fines de semana).
3) Validar fechas.
4) Generar Excel de prueba.
5) Solicitar confirmación del usuario.
6) Insertar en SQLite solo si el usuario confirma.
"""

import os
import sqlite3
import sys
from datetime import datetime

import pandas as pd
import requests

# Configuración de base de datos y archivos de salida
DB_NAME = "series_tiempo.db"
EXCEL_PRUEBA_NAME = "prueba_tipo_cambio_brasil.xlsx"

# Datos del maestro
MAESTRO_TIPO_CAMBIO_BRASIL = {
    "id": 23,
    "nombre": "Tipo de cambio USD/BRL (Brasil)",
    "tipo": "M",  # variable macro
    "fuente": "BCB_API_PTAX",
    "periodicidad": "D",  # diario
    "unidad": "BRL por USD",
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


def extraer_bcb_brasil(fecha_inicio=None, fecha_fin=None):
    """
    Extrae datos de tipo de cambio del Banco Central de Brasil (BCB).
    
    Args:
        fecha_inicio: Fecha de inicio en formato MM-DD-YYYY (por defecto: 01-01-2025)
        fecha_fin: Fecha de fin en formato MM-DD-YYYY (por defecto: hoy)
        
    Returns:
        DataFrame con columnas: Fecha, Tipo_Cambio (promedio de compra y venta)
    """
    try:
        # Fechas por defecto
        if fecha_inicio is None:
            fecha_inicio = "01-01-2010"  # MM-DD-YYYY - desde 2010 como solicitado
        if fecha_fin is None:
            fecha_fin = datetime.today().strftime("%m-%d-%Y")
        
        # Endpoint oficial BCB (PTAX)
        url = (
            "https://olinda.bcb.gov.br/olinda/servico/PTAX/versao/v1/odata/"
            "CotacaoDolarPeriodo(dataInicial=@dataInicial,dataFinalCotacao=@dataFinalCotacao)?"
            f"@dataInicial='{fecha_inicio}'"
            f"&@dataFinalCotacao='{fecha_fin}'"
            "&$format=json"
        )
        
        # Request
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        data = response.json()["value"]
        
        if not data:
            print("No se encontraron datos en el rango de fechas especificado")
            return None
        
        # DataFrame
        df = pd.DataFrame(data)
        
        # Crear DataFrame con las columnas necesarias
        datos = pd.DataFrame({
            'Fecha': pd.to_datetime(df["dataHoraCotacao"]).dt.date,
            'Compra': df["cotacaoCompra"],
            'Venta': df["cotacaoVenda"]
        })
        
        # Limpiar datos: eliminar filas vacías o con NaN en fecha
        datos = datos.dropna(subset=['Fecha'])
        
        # Convertir fecha a datetime
        datos['Fecha'] = pd.to_datetime(datos['Fecha'])
        
        # Convertir compra y venta a numérico
        datos['Compra'] = pd.to_numeric(datos['Compra'], errors='coerce')
        datos['Venta'] = pd.to_numeric(datos['Venta'], errors='coerce')
        
        # Calcular promedio de compra y venta
        datos['Tipo_Cambio'] = (datos['Compra'] + datos['Venta']) / 2
        
        # Seleccionar solo Fecha y Tipo_Cambio
        tc_brasil = datos[['Fecha', 'Tipo_Cambio']].copy()
        
        # Eliminar filas donde Tipo_Cambio es NaN
        tc_brasil = tc_brasil.dropna(subset=['Tipo_Cambio'])
        
        # Agrupar por fecha y promediar (por si hay duplicados)
        tc_brasil = tc_brasil.groupby('Fecha')['Tipo_Cambio'].mean().reset_index()
        
        # Ordenar por fecha (más reciente primero)
        tc_brasil = tc_brasil.sort_values('Fecha', ascending=False).reset_index(drop=True)
        
        return tc_brasil
        
    except Exception as e:
        print(f"Error al procesar los datos: {e}")
        import traceback
        traceback.print_exc()
        return None


def completar_dias_faltantes(df: pd.DataFrame, columna_fecha: str = 'Fecha', columna_valor: str = 'Tipo_Cambio') -> pd.DataFrame:
    """
    Completa días faltantes en una serie diaria usando forward fill.
    
    Para series diarias, garantiza que existan datos para todos los días del rango
    (lunes a domingo). Si un día no tiene datos (feriados, fines de semana), 
    usa el valor del día anterior.
    
    Args:
        df: DataFrame con columnas de fecha y valor
        columna_fecha: Nombre de la columna con fechas
        columna_valor: Nombre de la columna con valores
        
    Returns:
        DataFrame con todos los días completados (forward fill)
    """
    print("\n[INFO] Completando días faltantes en serie diaria...")
    
    # Asegurar que la columna de fecha sea datetime
    df = df.copy()
    df[columna_fecha] = pd.to_datetime(df[columna_fecha])
    
    # Ordenar por fecha
    df = df.sort_values(columna_fecha).reset_index(drop=True)
    
    # Obtener rango completo de fechas
    fecha_min = df[columna_fecha].min()
    fecha_max = df[columna_fecha].max()
    
    # Crear rango completo de días
    rango_completo = pd.date_range(start=fecha_min, end=fecha_max, freq='D')
    df_completo = pd.DataFrame({columna_fecha: rango_completo})
    
    # Hacer merge con los datos originales
    df_completo = df_completo.merge(
        df[[columna_fecha, columna_valor]], 
        on=columna_fecha, 
        how='left'
    )
    
    # Aplicar forward fill (usar valor del día anterior)
    # Usar ffill() que es compatible con versiones recientes de pandas
    df_completo[columna_valor] = df_completo[columna_valor].ffill()
    
    # Contar cuántos días se completaron
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
    
    # Asegurar que valor sea numérico
    df_precios["valor"] = pd.to_numeric(df_precios["valor"], errors="coerce")
    
    # Eliminar filas con valor nulo
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
    """
    Solicita confirmación explícita del usuario antes de insertar,
    cumpliendo el flujo del README.
    """
    print("\n" + "=" * 60)
    print("CONFIRMACION DEL USUARIO")
    print("=" * 60)
    print(f"Archivo Excel generado para validación: {excel_path}")
    print("Revisá el Excel (hojas 'maestro' y 'maestro_precios').")
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

        # Verificar qué precios ya existen para evitar duplicados
        cursor.execute(
            """
            SELECT fecha FROM maestro_precios 
            WHERE maestro_id = ?
            """,
            (maestro_id,)
        )
        fechas_existentes = {row[0] for row in cursor.fetchall()}
        
        # Filtrar precios que ya existen
        df_precios_nuevos = df_precios[
            ~df_precios["fecha"].astype(str).isin([str(f) for f in fechas_existentes])
        ]
        
        if len(df_precios_nuevos) == 0:
            print(f"[INFO] Todos los precios ya existen en la base de datos, no se insertan nuevos registros")
        else:
            print(f"[INFO] Se insertarán {len(df_precios_nuevos)} nuevos registros (de {len(df_precios)} totales)")
            df_precios_nuevos.to_sql("maestro_precios", conn, if_exists="append", index=False)
            print(f"[OK] Insertados {len(df_precios_nuevos)} registro(s) en tabla 'maestro_precios'")

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
    print("ACTUALIZACION DE DATOS: TIPO DE CAMBIO USD/BRL (BRASIL)")
    print("=" * 60)

    crear_base_datos()

    # Extraer datos desde API del BCB (desde 2010)
    print("\n[INFO] Extrayendo datos del Banco Central de Brasil (desde 2010)...")
    df = extraer_bcb_brasil(fecha_inicio="01-01-2010", fecha_fin=None)
    
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
    df_maestro = pd.DataFrame([MAESTRO_TIPO_CAMBIO_BRASIL])
    df_precios = preparar_datos_maestro_precios(df, MAESTRO_TIPO_CAMBIO_BRASIL["id"])

    # Generar Excel de prueba
    excel_path = generar_excel_prueba(df_maestro, df_precios)
    
    # Mostrar resumen
    mostrar_resumen(df_maestro, df_precios)
    
    # Solicitar confirmación del usuario
    solicitar_confirmacion_usuario(excel_path)

    # Insertar en BD solo si el usuario confirma
    insertar_en_bd(df_maestro, df_precios)


if __name__ == "__main__":
    main()
