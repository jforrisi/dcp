"""
Script: salario_real
--------------------
Actualiza la base de datos con la serie de Salario Real (índice, sector privado)
del INE, siguiendo el flujo definido en 0_README:

1) Intentar lectura directa del Excel con pandas desde la URL.
2) Si falla, seguir el flujo del README (avisar, pedir confirmación, crear scripts con Selenium si confirma).
3) Validar fechas.
4) Generar Excel de prueba.
5) Solicitar confirmación del usuario.
6) Insertar en SQLite solo si el usuario confirma.
"""

import os
import sqlite3
import sys

import pandas as pd


# Configuración de origen de datos
URL_EXCEL_INE = "https://www5.ine.gub.uy/documents/Estad%C3%ADsticasecon%C3%B3micas/SERIES%20Y%20OTROS/IMS/Base%20Julio%202008=100/IMS%20C1%20SR%20Gral%20P-P%20M%20emp%20B08.xls"
DATA_RAW_DIR = "data_raw"
LOCAL_EXCEL_NAME = "salario_real_ine.xls"

# Configuración de base de datos y archivos de salida
DB_NAME = "series_tiempo.db"
EXCEL_PRUEBA_NAME = "prueba_salario_real_ine.xlsx"


# Datos del maestro según especificación del usuario
MAESTRO_SALARIO_REAL = {
    "id": 19,
    "nombre": "Salario Real",
    "tipo": "M",
    "fuente": "INE",
    "periodicidad": "M",
    "unidad": "Indice",
    "categoria": "Macro",
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
    Intenta leer el Excel directamente desde la URL con pandas.
    Usa columnas A (fecha) y C (salario real privado), desde la fila 40.
    Devuelve un DataFrame o lanza excepción si falla.
    """
    print("\n[INFO] Intentando leer Excel directamente desde la URL del INE...")
    print(f"   URL: {URL_EXCEL_INE}")

    salario_df = pd.read_excel(
        URL_EXCEL_INE,
        sheet_name=0,
        usecols=[0, 2],  # Columnas A y C
        skiprows=39,  # comienza en la fila 40 (0-index)
        header=None,
    )

    salario_df.columns = ["FECHA", "SALARIO_REAL"]

    # Eliminar filas completamente vacías
    salario_df = salario_df.dropna(how="all")

    # Eliminar filas donde fecha o salario sean nulos
    salario_df = salario_df.dropna(subset=["FECHA", "SALARIO_REAL"])

    print(f"[OK] Leido desde URL: {len(salario_df)} registros válidos")
    return salario_df


def leer_excel_desde_data_raw():
    """
    Lee el Excel local desde data_raw/salario_real_ine.xls.
    Lanza excepción si no existe o falla.
    """
    base_dir = os.getcwd()
    ruta_local = os.path.join(base_dir, DATA_RAW_DIR, LOCAL_EXCEL_NAME)

    if not os.path.exists(ruta_local):
        raise FileNotFoundError(
            f"No se encontró el archivo local esperado: {ruta_local}. "
            "Ejecutá primero el script de descarga (salario_real en macro/download/)."
        )

    print(f"\n[INFO] Leyendo Excel local desde: {ruta_local}")
    salario_df = pd.read_excel(
        ruta_local,
        sheet_name=0,
        usecols=[0, 2],
        skiprows=39,
        header=None,
    )
    salario_df.columns = ["FECHA", "SALARIO_REAL"]

    # Eliminar filas completamente vacías
    salario_df = salario_df.dropna(how="all")

    # Eliminar filas donde fecha o salario sean nulos
    salario_df = salario_df.dropna(subset=["FECHA", "SALARIO_REAL"])

    print(f"[OK] Leido desde archivo local: {len(salario_df)} registros válidos")
    return salario_df


def manejar_fallo_pandas(error: Exception):
    """
    Maneja el fallo de pandas según el flujo del README:
    - Avisar claramente el error específico.
    - Informar que se necesitarán 2 archivos (download y update con Selenium).
    - Solicitar confirmación explícita antes de cambiar a Selenium.
    - Si confirma: eliminar código de pandas y crear scripts con Selenium.
    - Si no confirma: no proceder.
    """
    print("\n" + "=" * 60)
    print("ERROR AL LEER CON PANDAS DESDE LA URL")
    print("=" * 60)
    print(f"\n[ERROR] No se pudo leer el Excel directamente desde la URL con pandas.")
    print(f"   Error específico: {type(error).__name__}: {error}")
    print(f"   URL intentada: {URL_EXCEL_INE}")
    print("\n[INFO] Según el flujo del README, si pandas falla se debe:")
    print("   1. Crear un script de descarga con Selenium en:")
    print("      macro/download/salario_real.py")
    print("   2. Modificar este script para leer desde data_raw/")
    print("      (eliminando el código de pandas de lectura directa)")
    print("\n[ADVERTENCIA] Si confirmás, se procederá a:")
    print("   - Eliminar el código de pandas de este script")
    print("   - Crear el script de descarga con Selenium")
    print("   - Modificar este script para leer solo desde data_raw/")

    respuesta = (
        input("\n¿Confirmás que querés cambiar a Selenium? (sí/no): ")
        .strip()
        .lower()
    )

    if respuesta not in ["sí", "si", "yes", "y", "s"]:
        print("\n[INFO] Cambio a Selenium cancelado por el usuario.")
        print("       No se realizará ninguna modificación.")
        sys.exit(0)

    print("\n[INFO] Creando scripts con Selenium...")
    crear_script_download_selenium()
    modificar_script_update_para_selenium()
    print("\n[OK] Scripts creados/modificados. Ejecutá primero el script de descarga:")
    print("   python macro/download/salario_real.py")
    print("   Luego ejecutá este script nuevamente.")
    sys.exit(0)


def crear_script_download_selenium():
    """Crea el script de descarga con Selenium."""
    script_download_path = os.path.join(
        os.getcwd(), "macro", "download", "salario_real.py"
    )

    os.makedirs(os.path.dirname(script_download_path), exist_ok=True)

    contenido_download = '''"""
Script: salario_real
--------------------
Usa Selenium + Chrome para descargar el Excel de Salario Real del INE
y guardarlo dentro de la carpeta `data_raw/`, según el flujo definido en 0_README.

NOTA: Este script fue generado automáticamente porque pandas no pudo leer directamente
desde la URL. Ajustá los selectores de Selenium según la estructura real de la página.
"""

import os

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


# URL de la página donde está el enlace al Excel
INE_SALARIO_URL = "https://www5.ine.gub.uy/documents/Estad%C3%ADsticasecon%C3%B3micas/SERIES%20Y%20OTROS/IMS/Base%20Julio%202008=100/IMS%20C1%20SR%20Gral%20P-P%20M%20emp%20B08.xls"

# Carpeta y nombre de archivo destino dentro del proyecto
DATA_RAW_DIR = "data_raw"
DEST_FILENAME = "salario_real_ine.xls"


def asegurar_data_raw():
    """Crea la carpeta data_raw si no existe y devuelve su ruta absoluta."""
    base_dir = os.getcwd()
    data_raw_path = os.path.join(base_dir, DATA_RAW_DIR)
    os.makedirs(data_raw_path, exist_ok=True)
    return data_raw_path


def configurar_driver_descargas(download_dir: str):
    """
    Configura Chrome para que descargue archivos automáticamente
    en el directorio indicado, sin preguntar.
    """
    chrome_options = Options()
    prefs = {
        "download.default_directory": download_dir,
        "download.prompt_for_download": False,
        "download.directory_upgrade": True,
        "safebrowsing.enabled": True,
    }
    chrome_options.add_experimental_option("prefs", prefs)
    driver = webdriver.Chrome(options=chrome_options)
    return driver


def descargar_excel_ine():
    """
    Abre la URL del INE con Selenium y descarga el Excel directamente.
    """
    data_raw_path = asegurar_data_raw()
    print(f"[INFO] Carpeta de descargas configurada en: {data_raw_path}")

    driver = configurar_driver_descargas(download_dir=data_raw_path)

    try:
        print(f"[INFO] Abriendo URL del INE: {INE_SALARIO_URL}")
        driver.get(INE_SALARIO_URL)

        # Esperar a que el archivo se descargue
        import time

        print("[INFO] Esperando a que termine la descarga...")
        time.sleep(10)

        # Buscar el archivo descargado y renombrarlo
        candidatos = [
            f
            for f in os.listdir(data_raw_path)
            if f.lower().endswith((".xls", ".xlsx"))
        ]
        if not candidatos:
            raise RuntimeError("No se encontro ningun Excel descargado en data_raw.")

        candidatos_paths = [os.path.join(data_raw_path, f) for f in candidatos]
        ultimo = max(candidatos_paths, key=os.path.getmtime)

        destino = os.path.join(data_raw_path, DEST_FILENAME)
        if os.path.abspath(ultimo) != os.path.abspath(destino):
            if os.path.exists(destino):
                os.remove(destino)
            os.replace(ultimo, destino)

        print(f"[OK] Excel guardado como: {destino}")
        return destino

    finally:
        driver.quit()


if __name__ == "__main__":
    descargar_excel_ine()
'''

    with open(script_download_path, "w", encoding="utf-8") as f:
        f.write(contenido_download)

    print(f"[OK] Script de descarga creado: {script_download_path}")


def modificar_script_update_para_selenium():
    """
    Modifica este script para eliminar el código de pandas de lectura directa
    y dejar solo la lectura desde data_raw/.
    """
    script_path = __file__
    with open(script_path, "r", encoding="utf-8") as f:
        contenido = f.read()

    nuevo_contenido = contenido.replace(
        'def leer_excel_desde_url():\n    """\n    Intenta leer el Excel directamente desde la URL con pandas.\n    Usa columnas A (fecha) y C (salario real privado), desde la fila 40.\n    Devuelve un DataFrame o lanza excepción si falla.\n    """\n    print("\\n[INFO] Intentando leer Excel directamente desde la URL del INE...")\n    print(f"   URL: {URL_EXCEL_INE}")\n\n    salario_df = pd.read_excel(\n        URL_EXCEL_INE,\n        sheet_name=0,\n        usecols=[0, 2],  # Columnas A y C\n        skiprows=39,  # comienza en la fila 40 (0-index)\n        header=None,\n    )\n\n    salario_df.columns = ["FECHA", "SALARIO_REAL"]\n\n    # Eliminar filas completamente vacías\n    salario_df = salario_df.dropna(how="all")\n\n    # Eliminar filas donde fecha o salario sean nulos\n    salario_df = salario_df.dropna(subset=["FECHA", "SALARIO_REAL"])\n\n    print(f"[OK] Leido desde URL: {len(salario_df)} registros válidos")\n    return salario_df\n\n\n',
        '# Función leer_excel_desde_url() eliminada - ahora se usa solo Selenium + data_raw\n\n'
    )

    nuevo_contenido = nuevo_contenido.replace(
        'def obtener_salario_real():\n    """\n    Implementa el flujo:\n    1) Intentar lectura directa desde URL.\n    2) Si falla, manejar según el README.\n    """\n    try:\n        return leer_excel_desde_url()\n    except Exception as e:\n        manejar_fallo_pandas(e)',
        'def obtener_salario_real():\n    """\n    Lee el Excel desde data_raw/ (descargado previamente con Selenium).\n    """\n    return leer_excel_desde_data_raw()'
    )

    nuevo_contenido = nuevo_contenido.replace(
        'def manejar_fallo_pandas(error: Exception):',
        '# Función manejar_fallo_pandas() eliminada - ya no se usa pandas directo\n# def manejar_fallo_pandas(error: Exception):'
    )

    with open(script_path, "w", encoding="utf-8") as f:
        f.write(nuevo_contenido)

    print(f"[OK] Script de update modificado para usar solo data_raw/")


def obtener_salario_real():
    """
    Implementa el flujo:
    1) Intentar lectura directa desde URL.
    2) Si falla, manejar según el README (avisar, pedir confirmación, crear scripts con Selenium si confirma).
    """
    try:
        return leer_excel_desde_url()
    except Exception as e:
        manejar_fallo_pandas(e)


def validar_fechas(df: pd.DataFrame) -> pd.DataFrame:
    """Valida que todas las fechas sean válidas (OBLIGATORIO según README)."""
    print("\n[INFO] Validando fechas...")

    fechas_invalidas = []
    fechas_validas = []

    for idx, fecha in enumerate(df["FECHA"]):
        try:
            if pd.isna(fecha):
                fechas_invalidas.append((idx, fecha, "Fecha nula"))
            else:
                fecha_parseada = pd.to_datetime(fecha, errors="coerce", dayfirst=True)
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

    df["FECHA"] = pd.to_datetime(df["FECHA"], dayfirst=True)
    print(f"[OK] Todas las {len(fechas_validas)} fechas son validas")
    print(f"   Rango: {df['FECHA'].min()} a {df['FECHA'].max()}")
    return df


def preparar_datos_maestro_precios(df_salario: pd.DataFrame, maestro_id: int) -> pd.DataFrame:
    """Prepara el DataFrame para maestro_precios."""
    df_precios = df_salario.copy()
    df_precios["maestro_id"] = maestro_id
    df_precios = df_precios[["maestro_id", "FECHA", "SALARIO_REAL"]]
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


def insertar_en_bd(df_maestro: pd.DataFrame, df_precios: pd.DataFrame) -> None:
    """Inserta los datos en la base de datos SQLite."""
    print("\n[INFO] Insertando datos en la base de datos...")

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    try:
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

        cursor.execute(
            """
            SELECT fecha FROM maestro_precios 
            WHERE maestro_id = ?
            """,
            (maestro_id,)
        )
        fechas_existentes = {row[0] for row in cursor.fetchall()}

        df_precios_nuevos = df_precios[
            ~df_precios["fecha"].astype(str).isin([str(f) for f in fechas_existentes])
        ]

        if len(df_precios_nuevos) == 0:
            print("[INFO] Todos los precios ya existen en la base de datos, no se insertan nuevos registros")
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


def main():
    print("=" * 60)
    print("ACTUALIZACION DE DATOS: SALARIO REAL (INE)")
    print("=" * 60)

    crear_base_datos()

    salario_df = obtener_salario_real()

    print("\n[INFO] Datos de la serie cruda:")
    print("\nPrimeros datos:")
    print(salario_df.head())
    print("\nÚltimos datos:")
    print(salario_df.tail())

    salario_df = validar_fechas(salario_df)

    df_maestro = pd.DataFrame([MAESTRO_SALARIO_REAL])
    df_precios = preparar_datos_maestro_precios(salario_df, MAESTRO_SALARIO_REAL["id"])

    excel_path = generar_excel_prueba(df_maestro, df_precios)
    mostrar_resumen(df_maestro, df_precios)
    solicitar_confirmacion_usuario(excel_path)

    insertar_en_bd(df_maestro, df_precios)


if __name__ == "__main__":
    main()
