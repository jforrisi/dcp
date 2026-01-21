"""
Script: servicios_no_tradicionales
-----------------------------------
Calcula y actualiza la base de datos con la serie "Servicios no tradicionales - sin software"
como promedio mensual de las series:
- id 14: Ingeniería
- id 15: Arquitectura
- id 16: Contabilidad (CPA)
- id 17: Bookkeeping / payroll

Siguiendo el flujo del README:

1) Leer las 4 series desde maestro_precios.
2) Calcular promedio mensual por fecha.
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

# Configuración de base de datos y archivos de salida
DB_NAME = "series_tiempo.db"
EXCEL_PRUEBA_NAME = "prueba_servicios_no_tradicionales.xlsx"

# IDs de las series fuente
SERIES_FUENTE = [14, 15, 16, 17]  # Ingeniería, Arquitectura, Contabilidad, Bookkeeping

# Datos del maestro según especificación del usuario
MAESTRO_SERVICIOS_NO_TRAD = {
    "id": 18,
    "nombre": "Servicios no tradicionales - sin software",
    "tipo": "S",  # servicio
    "fuente": "BLS",
    "periodicidad": "M",  # mensual
    "unidad": "Indice",
    "categoria": None,
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


def leer_series_fuente():
    """
    Lee las 4 series fuente (14, 15, 16, 17) desde maestro_precios.
    Retorna un DataFrame con fecha y valores de cada serie.
    """
    print("\n[INFO] Leyendo series fuente desde la base de datos...")
    print(f"   Series: {SERIES_FUENTE}")
    
    conn = sqlite3.connect(DB_NAME)
    
    # Leer todas las series fuente
    dfs = []
    for serie_id in SERIES_FUENTE:
        query = """
            SELECT fecha, valor
            FROM maestro_precios
            WHERE maestro_id = ?
            ORDER BY fecha ASC
        """
        df = pd.read_sql_query(query, conn, params=(serie_id,))
        if len(df) == 0:
            print(f"[WARN] Serie id={serie_id} no tiene datos")
            continue
        
        df['fecha'] = pd.to_datetime(df['fecha'])
        df = df.rename(columns={'valor': f'valor_{serie_id}'})
        dfs.append(df)
        print(f"[OK] Serie id={serie_id}: {len(df)} registros")
    
    conn.close()
    
    if not dfs:
        raise ValueError("No se encontraron datos en ninguna serie fuente")
    
    # Combinar todas las series por fecha
    df_combinado = dfs[0]
    for df in dfs[1:]:
        df_combinado = pd.merge(df_combinado, df, on='fecha', how='outer')
    
    # Ordenar por fecha
    df_combinado = df_combinado.sort_values('fecha').reset_index(drop=True)
    
    print(f"[OK] Series combinadas: {len(df_combinado)} fechas únicas")
    return df_combinado


def calcular_promedio_mensual(df_combinado: pd.DataFrame) -> pd.DataFrame:
    """
    Calcula el promedio mensual de las 4 series fuente.
    Solo incluye fechas donde hay al menos una serie disponible.
    """
    print("\n[INFO] Calculando promedio mensual...")
    
    # Obtener columnas de valores
    columnas_valores = [col for col in df_combinado.columns if col.startswith('valor_')]
    
    if not columnas_valores:
        raise ValueError("No se encontraron columnas de valores")
    
    # Calcular promedio de las columnas disponibles (ignorando NaN)
    df_combinado['promedio'] = df_combinado[columnas_valores].mean(axis=1, skipna=True)
    
    # Filtrar solo filas donde hay al menos un valor
    df_resultado = df_combinado[df_combinado['promedio'].notna()].copy()
    
    # Seleccionar solo fecha y promedio
    df_resultado = df_resultado[['fecha', 'promedio']].copy()
    df_resultado = df_resultado.rename(columns={'promedio': 'valor'})
    
    # Mostrar estadísticas de cobertura
    print(f"[INFO] Cobertura por serie:")
    for col in columnas_valores:
        serie_id = col.replace('valor_', '')
        count = df_combinado[col].notna().sum()
        print(f"   Serie id={serie_id}: {count} valores disponibles")
    
    print(f"[OK] Promedio calculado: {len(df_resultado)} registros")
    return df_resultado


def validar_fechas(df: pd.DataFrame) -> pd.DataFrame:
    """Valida que todas las fechas sean válidas (OBLIGATORIO según README)."""
    print("\n[INFO] Validando fechas...")

    fechas_invalidas = []
    fechas_validas = []

    for idx, fecha in enumerate(df["fecha"]):
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

    df["fecha"] = pd.to_datetime(df["fecha"])
    print(f"[OK] Todas las {len(fechas_validas)} fechas son validas")
    print(f"   Rango: {df['fecha'].min()} a {df['fecha'].max()}")
    return df


def preparar_datos_maestro_precios(df_promedio: pd.DataFrame, maestro_id: int) -> pd.DataFrame:
    """Prepara el DataFrame para maestro_precios."""
    df_precios = df_promedio.copy()
    df_precios["maestro_id"] = maestro_id
    df_precios = df_precios[["maestro_id", "fecha", "valor"]]
    
    # Asegurar que valor sea numérico
    df_precios["valor"] = pd.to_numeric(df_precios["valor"], errors="coerce")
    
    # Eliminar filas con valor nulo
    df_precios = df_precios.dropna(subset=["valor"])
    
    # Asegurar que fecha sea date (sin hora)
    df_precios["fecha"] = pd.to_datetime(df_precios["fecha"]).dt.date
    
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
    """Solicita confirmación explícita del usuario (OBLIGATORIO según README)."""
    print("\n" + "=" * 60)
    print("CONFIRMACION DEL USUARIO")
    print("=" * 60)
    print(f"Archivo Excel generado para validacion: {excel_path}")
    print("Revisa el Excel (hojas 'maestro' y 'maestro_precios').")
    respuesta = (
        input("¿Confirmas la insercion en la base de datos? (sí/no): ")
        .strip()
        .lower()
    )

    if respuesta not in ["sí", "si", "yes", "y", "s"]:
        print("\n[INFO] Insercion cancelada por el usuario.")
        print("       No se insertaron datos en la base de datos.")
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
                maestro_row.get("categoria", None),
                maestro_row["activo"],
            )
        )
        
        if cursor.rowcount > 0:
            print(f"[OK] Insertado 1 registro en tabla 'maestro' (id={maestro_id})")
        else:
            print(f"[INFO] El registro con id={maestro_id} ya existe en 'maestro', se omite la insercion")

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
            print(f"[INFO] Se insertaran {len(df_precios_nuevos)} nuevos registros (de {len(df_precios)} totales)")
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
    print("ACTUALIZACION DE DATOS: SERVICIOS NO TRADICIONALES - SIN SOFTWARE")
    print("=" * 60)
    print("Calcula el promedio mensual de las series:")
    print("  - id 14: Ingeniería")
    print("  - id 15: Arquitectura")
    print("  - id 16: Contabilidad (CPA)")
    print("  - id 17: Bookkeeping / payroll")

    crear_base_datos()

    # Leer series fuente
    df_combinado = leer_series_fuente()
    
    # Calcular promedio mensual
    df_promedio = calcular_promedio_mensual(df_combinado)
    
    # Mostrar primeros y últimos datos
    print("\n[INFO] Datos del promedio calculado:")
    print("\nPrimeros datos:")
    print(df_promedio.head())
    print("\nÚltimos datos:")
    print(df_promedio.tail())
    
    # Validar fechas
    df_promedio = validar_fechas(df_promedio)

    # Preparar datos
    df_maestro = pd.DataFrame([MAESTRO_SERVICIOS_NO_TRAD])
    df_precios = preparar_datos_maestro_precios(df_promedio, MAESTRO_SERVICIOS_NO_TRAD["id"])

    # Generar Excel de prueba y mostrar resumen
    excel_path = generar_excel_prueba(df_maestro, df_precios)
    mostrar_resumen(df_maestro, df_precios)

    # Solicitar confirmación
    solicitar_confirmacion_usuario(excel_path)

    # Insertar en base de datos
    insertar_en_bd(df_maestro, df_precios)


if __name__ == "__main__":
    main()
