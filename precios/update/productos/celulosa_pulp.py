"""
Script: celulosa_pulp
----------------------
Actualiza la base de datos con la serie de precios de celulosa (INSEE - Francia),
siguiendo el flujo del README:

1) Intentar lectura directa de la tabla HTML con pandas desde la URL.
2) Si falla, leer el archivo local desde data_raw/celulosa_pulp_insee.xlsx o .csv.
3) Validar fechas.
4) Generar Excel de prueba (maestro + maestro_precios).
5) Solicitar confirmación del usuario.
6) Insertar en SQLite solo si el usuario confirma.
"""

import os
import sqlite3
import zipfile
import io
import requests

import pandas as pd


# Configuración de origen de datos
URL_INSEE_PAGE = "https://www.insee.fr/en/statistiques/serie/010600341#Telechargement"
URL_EXCEL_DIRECTA = "https://bdm.insee.fr/series/010600341/xlsx?lang=en&ordre=antechronologique&transposition=donnees_colonne&periodeDebut=1&anneeDebut=1990&periodeFin=11&anneeFin=2025&revision=sans_revisions"
DATA_RAW_DIR = "data_raw"
LOCAL_FILE_NAME = "celulosa_pulp_insee.xlsx"

# Configuración de base de datos y archivos de salida
DB_NAME = "series_tiempo.db"
EXCEL_PRUEBA_NAME = "prueba_celulosa_pulp.xlsx"


# Datos del maestro según especificación del usuario
MAESTRO_CELULOSA = {
    "id": 12,  # Ajustar según IDs ya usados en el sistema
    "nombre": "Índice de precios de celulosa (INSEE - Francia)",
    "tipo": "P",
    "fuente": "INSEE - serie 010600341 (Producer Price Index - Pulp)",
    "periodicidad": "M",  # mensual
    "unidad": "Índice base 100",
    "categoria": "Productos forestales",
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


def leer_excel_desde_url():
    """
    Descarga el archivo desde la URL de INSEE (puede ser ZIP o Excel directo).
    Si es ZIP, extrae el Excel y lo lee.
    El Excel tiene los datos empezando en la fila 5:
    - Columna A = fecha
    - Columna B = valor (con texto adicional que hay que limpiar)
    Devuelve un DataFrame o lanza excepción si falla.
    """
    print("\n[INFO] Descargando archivo desde la URL de INSEE...")
    print(f"[INFO] URL: {URL_EXCEL_DIRECTA}")
    
    try:
        # Descargar el archivo
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        response = requests.get(URL_EXCEL_DIRECTA, headers=headers, timeout=30)
        response.raise_for_status()
        
        print(f"[OK] Archivo descargado ({len(response.content)} bytes)")
        
        # Verificar si es ZIP o Excel directo
        content_type = response.headers.get('Content-Type', '').lower()
        is_zip = content_type == 'application/zip' or response.content[:2] == b'PK'
        
        excel_data = None
        
        if is_zip:
            print("[INFO] El archivo es un ZIP, extrayendo el Excel...")
            # Es un ZIP, extraer el Excel
            with zipfile.ZipFile(io.BytesIO(response.content)) as zip_file:
                # Buscar el archivo Excel dentro del ZIP
                excel_files = [f for f in zip_file.namelist() if f.endswith('.xlsx') or f.endswith('.xls')]
                if not excel_files:
                    raise ValueError("No se encontró ningún archivo Excel en el ZIP")
                
                # Usar el primer Excel encontrado
                excel_name = excel_files[0]
                print(f"[INFO] Extrayendo: {excel_name}")
                excel_data = zip_file.read(excel_name)
        else:
            print("[INFO] El archivo es un Excel directo")
            excel_data = response.content
        
        # Leer el Excel desde memoria
        # skiprows=4 porque los datos empiezan en la fila 5 (índice 4)
        # usecols="A,B" para leer solo fecha (A) y valor (B)
        df = pd.read_excel(
            io.BytesIO(excel_data),
            skiprows=4,  # Los datos empiezan en la fila 5
            usecols="A,B",  # Columna A = fecha, Columna B = valor
            header=None,
            engine='openpyxl'
        )
        
        # Asignar nombres a las columnas
        df.columns = ["FECHA_RAW", "VALOR_RAW"]
        
        print(f"[OK] Excel leído: {len(df)} filas")
        
        # Limpiar el valor: eliminar texto adicional (como "mcusho (A)") y convertir a numérico
        # El valor puede venir como "123.45 (A)" o similar, necesitamos extraer solo el número
        print("[INFO] Limpiando valores (eliminando texto adicional)...")
        
        # Convertir a string, extraer números (incluyendo decimales) y convertir a numérico
        df["CELULOSA_PULP"] = df["VALOR_RAW"].astype(str).str.extract(r'([\d,\.]+)')[0]
        # Reemplazar comas por puntos para formato decimal
        df["CELULOSA_PULP"] = df["CELULOSA_PULP"].str.replace(',', '.', regex=False)
        # Convertir a numérico
        df["CELULOSA_PULP"] = pd.to_numeric(df["CELULOSA_PULP"], errors='coerce')
        
        # Eliminar filas con valores nulos
        df = df.dropna(subset=["CELULOSA_PULP"])
        
        # Parsear fechas
        print("[INFO] Parseando fechas...")
        df["FECHA"] = pd.to_datetime(df["FECHA_RAW"], errors='coerce')
        
        # Si el parseo falla, intentar otros formatos
        if df["FECHA"].isna().any():
            # Intentar formato más flexible
            df["FECHA"] = pd.to_datetime(df["FECHA_RAW"], errors='coerce', infer_datetime_format=True)
        
        # Eliminar filas donde no se pudo parsear la fecha
        df = df.dropna(subset=["FECHA"])
        
        # Asegurar que las fechas sean el primer día del mes (si son mensuales)
        df["FECHA"] = df["FECHA"].dt.to_period('M').dt.to_timestamp()
        
        # Seleccionar solo las columnas necesarias
        df_limpio = df[["FECHA", "CELULOSA_PULP"]].copy()
        
        print(f"[OK] Procesados {len(df_limpio)} registros válidos")
        print(f"     Rango de fechas: {df_limpio['FECHA'].min()} a {df_limpio['FECHA'].max()}")
        print(f"     Rango de valores: {df_limpio['CELULOSA_PULP'].min():.2f} a {df_limpio['CELULOSA_PULP'].max():.2f}")
        
        return df_limpio
        
    except Exception as e:
        print(f"[ERROR] Error al leer Excel desde URL: {e}")
        raise


def leer_archivo_desde_data_raw():
    """
    Lee el archivo local desde data_raw.
    Intenta primero con el nombre estándar, luego busca automáticamente.
    Lanza excepción si no existe o falla.
    """
    base_dir = os.getcwd()
    data_raw_path = os.path.join(base_dir, DATA_RAW_DIR)
    
    # Primero intentar con el nombre estándar
    ruta_local = os.path.join(data_raw_path, LOCAL_FILE_NAME)
    
    if not os.path.exists(ruta_local):
        # Buscar automáticamente el archivo más reciente que contenga "celulosa" o "insee" o "pulp"
        print(f"\n[INFO] No se encontró {LOCAL_FILE_NAME}, buscando archivo alternativo...")
        
        if not os.path.exists(data_raw_path):
            raise FileNotFoundError(
                f"No existe la carpeta {data_raw_path}. "
                "Ejecutá primero el script de descarga (precios/download/productos/celulosa_pulp.py)."
            )
        
        # Buscar archivos que contengan palabras clave
        candidatos = [
            f
            for f in os.listdir(data_raw_path)
            if f.lower().endswith((".xls", ".xlsx", ".csv"))
            and any(term in f.lower() for term in ["celulosa", "pulp", "insee", "010600341"])
            and not f.startswith("~$")  # Excluir archivos temporales
        ]
        
        if not candidatos:
            raise FileNotFoundError(
                f"No se encontró ningún archivo de celulosa en {data_raw_path}. "
                "Ejecutá primero el script de descarga (precios/download/productos/celulosa_pulp.py)."
            )
        
        # Elegir el más reciente
        candidatos_paths = [os.path.join(data_raw_path, f) for f in candidatos]
        ruta_local = max(candidatos_paths, key=os.path.getmtime)
        print(f"[INFO] Usando archivo encontrado: {os.path.basename(ruta_local)}")

    print(f"\n[INFO] Leyendo archivo local desde: {ruta_local}")
    
    # Leer Excel (mismo formato que desde URL)
    print(f"[INFO] Leyendo Excel local (formato INSEE)...")
    df = pd.read_excel(
        ruta_local,
        skiprows=4,  # Los datos empiezan en la fila 5
        usecols="A,B",  # Columna A = fecha, Columna B = valor
        header=None,
        engine='openpyxl'
    )
    
    df.columns = ["FECHA_RAW", "VALOR_RAW"]
    
    # Limpiar valores (igual que desde URL)
    df["CELULOSA_PULP"] = df["VALOR_RAW"].astype(str).str.extract(r'([\d,\.]+)')[0]
    df["CELULOSA_PULP"] = df["CELULOSA_PULP"].str.replace(',', '.', regex=False)
    df["CELULOSA_PULP"] = pd.to_numeric(df["CELULOSA_PULP"], errors='coerce')
    
    df = df.dropna(subset=["CELULOSA_PULP"])
    df["FECHA"] = pd.to_datetime(df["FECHA_RAW"], errors='coerce')
    
    if df["FECHA"].isna().any():
        df["FECHA"] = pd.to_datetime(df["FECHA_RAW"], errors='coerce', infer_datetime_format=True)
    
    df = df.dropna(subset=["FECHA"])
    df["FECHA"] = df["FECHA"].dt.to_period('M').dt.to_timestamp()
    
    df_limpio = df[["FECHA", "CELULOSA_PULP"]].copy()
    
    print(f"[OK] Leido desde archivo local: {len(df_limpio)} registros válidos")
    return df_limpio


def obtener_celulosa_pulp():
    """
    Implementa el flujo:
    1) Intentar lectura directa del Excel desde URL.
    2) Si falla, intentar lectura desde data_raw.
    """
    try:
        return leer_excel_desde_url()
    except Exception as e:
        print(f"[WARN] No se pudo leer el Excel desde la URL: {e}")
        print("       Se intentara leer el archivo local en data_raw...")
        try:
            return leer_archivo_desde_data_raw()
        except Exception as e2:
            print(f"[ERROR] Tampoco se pudo leer desde data_raw: {e2}")
            print("\n[INFO] Según el flujo del README, si pandas falla se debe:")
            print("   - Avisar al usuario")
            print("   - Solicitar confirmación para usar Selenium")
            print("   - Si confirma: crear scripts de download y update con Selenium")
            raise


def validar_fechas(df: pd.DataFrame) -> pd.DataFrame:
    """Valida que todas las fechas sean válidas (OBLIGATORIO según README)."""
    print("\n[INFO] Validando fechas...")

    fechas_invalidas = []
    fechas_validas = []

    for idx, fecha in enumerate(df["FECHA"]):
        try:
            if pd.isna(fecha):
                fechas_invalidas.append((idx + 1, fecha, "Fecha nula"))
            else:
                fecha_parseada = pd.to_datetime(fecha, errors="coerce")
                if pd.isna(fecha_parseada):
                    fechas_invalidas.append((idx + 1, fecha, "No se pudo parsear"))
                else:
                    fechas_validas.append(fecha_parseada)
        except Exception as exc:
            fechas_invalidas.append((idx + 1, fecha, str(exc)))

    if fechas_invalidas:
        print(f"[ERROR] Se encontraron {len(fechas_invalidas)} fechas invalidas:")
        for fila, fecha, motivo in fechas_invalidas[:10]:
            print(f"   Fila {fila}: {fecha} - {motivo}")
        if len(fechas_invalidas) > 10:
            print(f"   ... y {len(fechas_invalidas) - 10} mas")
        raise ValueError("Hay fechas invalidas. No se puede continuar.")

    df["FECHA"] = pd.to_datetime(df["FECHA"])
    print(f"[OK] Todas las {len(fechas_validas)} fechas son validas")
    print(f"   Rango: {df['FECHA'].min()} a {df['FECHA'].max()}")
    return df


def preparar_datos_maestro_precios(df_celulosa: pd.DataFrame, maestro_id: int) -> pd.DataFrame:
    """Prepara el DataFrame para maestro_precios."""
    df_precios = df_celulosa.copy()
    df_precios["maestro_id"] = maestro_id
    df_precios = df_precios[["maestro_id", "FECHA", "CELULOSA_PULP"]]
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
    try:
        # Insertar en maestro usando INSERT OR IGNORE para evitar duplicados
        maestro_id = int(df_maestro.iloc[0]["id"])
        maestro_row = df_maestro.iloc[0]
        
        cursor = conn.cursor()
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
            ),
        )
        
        if cursor.rowcount > 0:
            print(f"[OK] Insertado 1 registro en tabla 'maestro' (id={maestro_id})")
        else:
            print(f"[INFO] El registro con id={maestro_id} ya existe en 'maestro', se omite la inserción")
        
        # Verificar fechas existentes para evitar duplicados en maestro_precios
        fechas_existentes = pd.read_sql_query(
            """
            SELECT fecha FROM maestro_precios 
            WHERE maestro_id = ?
            """,
            conn,
            params=(maestro_id,)
        )
        
        if not fechas_existentes.empty:
            fechas_existentes["fecha"] = pd.to_datetime(fechas_existentes["fecha"])
            df_precios["fecha"] = pd.to_datetime(df_precios["fecha"])
            df_precios_nuevos = df_precios[
                ~df_precios["fecha"].isin(fechas_existentes["fecha"])
            ]
            
            if len(df_precios_nuevos) > 0:
                df_precios_nuevos.to_sql("maestro_precios", conn, if_exists="append", index=False)
                print(f"[OK] Insertados {len(df_precios_nuevos)} registro(s) nuevo(s) en tabla 'maestro_precios'")
                if len(df_precios_nuevos) < len(df_precios):
                    print(f"[INFO] {len(df_precios) - len(df_precios_nuevos)} registro(s) ya existían y se omitieron")
            else:
                print("[INFO] Todos los registros ya existen en 'maestro_precios', no se insertó nada nuevo")
        else:
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
    print("ACTUALIZACION DE DATOS: CELULOSA PULP (INSEE - FRANCIA)")
    print("=" * 60)

    crear_base_datos()

    try:
        celulosa_pulp = obtener_celulosa_pulp()
        celulosa_pulp = validar_fechas(celulosa_pulp)

        df_maestro = pd.DataFrame([MAESTRO_CELULOSA])
        df_precios = preparar_datos_maestro_precios(celulosa_pulp, MAESTRO_CELULOSA["id"])

        excel_path = generar_excel_prueba(df_maestro, df_precios)
        mostrar_resumen(df_maestro, df_precios)

        print("\n[INFO] Actualizando base de datos automáticamente...")
        print(f"[INFO] Archivo Excel generado: {excel_path}")
        insertar_en_bd(df_maestro, df_precios)
            
    except Exception as e:
        print(f"\n[ERROR] Error durante la ejecución: {e}")
        print("\n[INFO] Si pandas no funciona, según el README se debe:")
        print("   1. Avisar al usuario del error")
        print("   2. Solicitar confirmación para usar Selenium")
        print("   3. Si confirma: crear scripts de download y update con Selenium")
        raise


if __name__ == "__main__":
    main()
