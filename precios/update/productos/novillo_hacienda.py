"""
Script: novillo_hacienda
-------------------------
Actualiza la base de datos con la serie de novillo hacienda (INAC),
siguiendo el flujo del README:

1) Intentar lectura directa del Excel con pandas desde la URL.
2) Si falla, leer el Excel local desde data_raw/precios_hacienda_inac.xlsx.
3) Validar fechas.
4) Generar Excel de prueba (maestro + maestro_precios).
5) Solicitar confirmación del usuario.
6) Insertar en SQLite solo si el usuario confirma.
"""

import os
import sqlite3

import pandas as pd


# Configuración de origen de datos
URL_EXCEL_INAC = "https://www.inac.uy/innovaportal/file/10953/1/precios-hacienda-mensual.xlsx"
DATA_RAW_DIR = "data_raw"
LOCAL_EXCEL_NAME = "precios_hacienda_inac.xlsx"

# Configuración de base de datos y archivos de salida
DB_NAME = "series_tiempo.db"
EXCEL_PRUEBA_NAME = "prueba_novillo_hacienda.xlsx"


# Datos del maestro según especificación del usuario
MAESTRO_NOVILLO = {
    "id": 1,
    "nombre": "Precio novillo hacienda (INAC) – USD/4ta balanza",
    "tipo": "P",
    "fuente": "INAC – serie mensual precios de hacienda",
    "periodicidad": "M",  # mensual (serie mensual de precios)
    "unidad": "USD/kg",
    "categoria": None,
    "activo": True,
}


def mapear_mes_espanol_a_numero(mes_str):
    """
    Mapea el mes en español abreviado a número de mes (1-12).
    Ene -> 1, Feb -> 2, ..., Dic -> 12
    """
    meses_espanol = {
        "Ene": 1,
        "Feb": 2,
        "Mar": 3,
        "Abr": 4,
        "May": 5,
        "Jun": 6,
        "Jul": 7,
        "Ago": 8,
        "Set": 9,
        "Oct": 10,
        "Nov": 11,
        "Dic": 12,
    }
    return meses_espanol.get(mes_str, None)


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


def leer_excel_desde_url():
    """
    Intenta leer el Excel directamente desde la URL con pandas.
    Devuelve un DataFrame o lanza excepción si falla.
    Estructura del Excel: Año (col A), Mes (col C), Precio 4ta balanza (col E).
    """
    print("\n[INFO] Intentando leer Excel directamente desde la URL de INAC...")
    df = pd.read_excel(
        URL_EXCEL_INAC,
        sheet_name="HACIENDA",
        skiprows=12,
        usecols="A,C,E",  # Año, Mes, Precio 4ta balanza
        header=None,
    )
    df.columns = ["AÑO", "MES", "NOVILLO_HACIENDA"]
    
    # Construir fecha a partir de Año y Mes (meses en español)
    df = df.dropna(subset=["AÑO", "MES", "NOVILLO_HACIENDA"])
    
    # Mapear meses en español a números
    df["MES_NUM"] = df["MES"].astype(str).str.strip().apply(mapear_mes_espanol_a_numero)
    df = df.dropna(subset=["MES_NUM"])
    
    # Construir fecha usando año y número de mes
    df["FECHA"] = pd.to_datetime(
        df["AÑO"].astype(int).astype(str)
        + "-"
        + df["MES_NUM"].astype(int).astype(str).str.zfill(2)
        + "-01",
        format="%Y-%m-%d",
        errors="coerce",
    )
    df = df.dropna(subset=["FECHA"])
    df = df[["FECHA", "NOVILLO_HACIENDA"]]
    
    print(f"[OK] Leido desde URL: {len(df)} registros")
    return df


def leer_excel_desde_data_raw():
    """
    Lee el Excel local desde data_raw.
    Primero intenta usar el nombre estándar (precios_hacienda_inac.xlsx).
    Si no existe, busca automáticamente el Excel más reciente que contenga "hacienda" o "inac" en el nombre.
    Lanza excepción si no existe o falla.
    """
    base_dir = os.getcwd()
    data_raw_path = os.path.join(base_dir, DATA_RAW_DIR)
    
    # Primero intentar con el nombre estándar
    ruta_local = os.path.join(data_raw_path, LOCAL_EXCEL_NAME)
    
    if not os.path.exists(ruta_local):
        # Buscar automáticamente el Excel más reciente que contenga "hacienda" o "inac"
        print(f"\n[INFO] No se encontró {LOCAL_EXCEL_NAME}, buscando archivo alternativo...")
        
        if not os.path.exists(data_raw_path):
            raise FileNotFoundError(
                f"No existe la carpeta {data_raw_path}. "
                "Ejecutá primero el script de descarga (precios/download/productos/novillo_hacienda.py)."
            )
        
        # Buscar archivos Excel que contengan "hacienda" en el nombre
        # Priorizar archivos que contengan "precios" y "hacienda" juntos
        candidatos_prioritarios = [
            f
            for f in os.listdir(data_raw_path)
            if f.lower().endswith((".xls", ".xlsx"))
            and "hacienda" in f.lower()
            and "precios" in f.lower()
            and not f.startswith("~$")  # Excluir archivos temporales de Excel
        ]
        
        # Si no hay candidatos prioritarios, buscar cualquier archivo con "hacienda"
        if not candidatos_prioritarios:
            candidatos_prioritarios = [
                f
                for f in os.listdir(data_raw_path)
                if f.lower().endswith((".xls", ".xlsx"))
                and "hacienda" in f.lower()
                and not f.startswith("~$")
            ]
        
        if not candidatos_prioritarios:
            raise FileNotFoundError(
                f"No se encontró ningún archivo Excel de precios de hacienda en {data_raw_path}. "
                "Ejecutá primero el script de descarga (precios/download/productos/novillo_hacienda.py)."
            )
        
        # Elegir el más reciente por fecha de modificación entre los candidatos prioritarios
        candidatos_paths = [os.path.join(data_raw_path, f) for f in candidatos_prioritarios]
        ruta_local = max(candidatos_paths, key=os.path.getmtime)
        print(f"[INFO] Usando archivo encontrado: {os.path.basename(ruta_local)}")

    print(f"\n[INFO] Leyendo Excel local desde: {ruta_local}")
    df = pd.read_excel(
        ruta_local,
        sheet_name="HACIENDA",
        skiprows=12,
        usecols="A,C,E",  # Año, Mes, Precio 4ta balanza
        header=None,
    )
    df.columns = ["AÑO", "MES", "NOVILLO_HACIENDA"]
    
    # Construir fecha a partir de Año y Mes (meses en español)
    df = df.dropna(subset=["AÑO", "MES", "NOVILLO_HACIENDA"])
    
    # Mapear meses en español a números
    df["MES_NUM"] = df["MES"].astype(str).str.strip().apply(mapear_mes_espanol_a_numero)
    df = df.dropna(subset=["MES_NUM"])
    
    # Construir fecha usando año y número de mes
    df["FECHA"] = pd.to_datetime(
        df["AÑO"].astype(int).astype(str)
        + "-"
        + df["MES_NUM"].astype(int).astype(str).str.zfill(2)
        + "-01",
        format="%Y-%m-%d",
        errors="coerce",
    )
    df = df.dropna(subset=["FECHA"])
    df = df[["FECHA", "NOVILLO_HACIENDA"]]
    
    print(f"[OK] Leido desde archivo local: {len(df)} registros")
    return df


def obtener_novillo_hacienda():
    """
    Implementa el flujo:
    1) Intentar lectura directa desde URL.
    2) Si falla, intentar lectura desde data_raw.
    """
    try:
        return leer_excel_desde_url()
    except Exception as e:
        print(f"[WARN] No se pudo leer desde la URL: {e}")
        print("       Se intentara leer el archivo local en data_raw...")
        return leer_excel_desde_data_raw()


def validar_fechas(df: pd.DataFrame) -> pd.DataFrame:
    """Valida que todas las fechas sean válidas (OBLIGATORIO según README)."""
    print("\n[INFO] Validando fechas...")

    fechas_invalidas = []
    fechas_validas = []

    for idx, fecha in enumerate(df["FECHA"]):
        try:
            if pd.isna(fecha):
                fechas_invalidas.append((idx + 13, fecha, "Fecha nula"))
            else:
                fecha_parseada = pd.to_datetime(fecha, errors="coerce")
                if pd.isna(fecha_parseada):
                    fechas_invalidas.append((idx + 13, fecha, "No se pudo parsear"))
                else:
                    fechas_validas.append(fecha_parseada)
        except Exception as exc:
            fechas_invalidas.append((idx + 13, fecha, str(exc)))

    if fechas_invalidas:
        print(f"[ERROR] Se encontraron {len(fechas_invalidas)} fechas invalidas:")
        for fila_excel, fecha, motivo in fechas_invalidas[:10]:
            print(f"   Fila Excel {fila_excel}: {fecha} - {motivo}")
        if len(fechas_invalidas) > 10:
            print(f"   ... y {len(fechas_invalidas) - 10} mas")
        raise ValueError("Hay fechas invalidas. No se puede continuar.")

    df["FECHA"] = pd.to_datetime(df["FECHA"])
    print(f"[OK] Todas las {len(fechas_validas)} fechas son validas")
    print(f"   Rango: {df['FECHA'].min()} a {df['FECHA'].max()}")
    return df


def preparar_datos_maestro_precios(df_novillo: pd.DataFrame, maestro_id: int) -> pd.DataFrame:
    """Prepara el DataFrame para maestro_precios."""
    df_precios = df_novillo.copy()
    df_precios["maestro_id"] = maestro_id
    df_precios = df_precios[["maestro_id", "FECHA", "NOVILLO_HACIENDA"]]
    df_precios.columns = ["maestro_id", "fecha", "valor"]
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


def insertar_en_bd(df_maestro: pd.DataFrame, df_precios: pd.DataFrame) -> None:
    """Inserta los datos en la base de datos SQLite."""
    print("\n[INFO] Insertando datos en la base de datos...")

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    try:
        # Insertar en maestro usando INSERT OR IGNORE para evitar duplicados
        maestro_id = int(df_maestro.iloc[0]["id"])
        maestro_row = df_maestro.iloc[0]
        
        # Verificar si existe la columna mercado
        cursor.execute("PRAGMA table_info(maestro)")
        columnas = [col[1] for col in cursor.fetchall()]
        tiene_mercado = "mercado" in columnas
        
        if tiene_mercado:
            cursor.execute(
                """
                INSERT OR IGNORE INTO maestro (id, nombre, tipo, fuente, periodicidad, unidad, categoria, activo, mercado)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                    maestro_row.get("mercado", None),
                )
            )
        else:
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
    print("ACTUALIZACION DE DATOS: NOVILLO HACIENDA (INAC)")
    print("=" * 60)

    crear_base_datos()

    novillo_hacienda = obtener_novillo_hacienda()
    novillo_hacienda = validar_fechas(novillo_hacienda)

    df_maestro = pd.DataFrame([MAESTRO_NOVILLO])
    df_precios = preparar_datos_maestro_precios(novillo_hacienda, MAESTRO_NOVILLO["id"])

    excel_path = generar_excel_prueba(df_maestro, df_precios)
    mostrar_resumen(df_maestro, df_precios)

    print("\nIMPORTANTE: Revisa el archivo Excel generado antes de continuar:")
    print(f"   {excel_path}")

    respuesta = (
        input(
            "\n¿Confirmás que los datos son correctos y querés insertarlos en la BD? (sí/no): "
        )
        .strip()
        .lower()
    )

    if respuesta in ["sí", "si", "yes", "y", "s"]:
        insertar_en_bd(df_maestro, df_precios)
    else:
        print(
            "\n[INFO] Insercion cancelada por el usuario. "
            "Los datos NO fueron insertados en la BD."
        )
        print("   Podés revisar el Excel y ejecutar el script nuevamente cuando estés listo.")


if __name__ == "__main__":
    main()

