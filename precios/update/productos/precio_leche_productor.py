"""
Script: precio_leche_productor
------------------------------
Actualiza la base de datos con la serie de precio al productor de leche (INALE),
siguiendo el flujo del README:

1) Intentar lectura directa del Excel con pandas desde la URL.
2) Si falla, seguir el flujo del README (avisar, pedir confirmación, crear scripts con Selenium si confirma).
3) Validar fechas.
4) Mostrar resumen de datos.
5) Solicitar confirmación del usuario.
6) Insertar en SQLite solo si el usuario confirma.
"""

import os
import sqlite3
import sys

import pandas as pd


# Configuración de origen de datos
URL_EXCEL_INALE = "https://www.inale.org/wp-content/uploads/2025/12/Precio-leche-en-tambo-y-composicion.xlsx"
DATA_RAW_DIR = "data_raw"
LOCAL_EXCEL_NAME = "precio_leche_productor.xlsx"

# Configuración de base de datos
DB_NAME = "series_tiempo.db"


# Datos del maestro según especificación del usuario
MAESTRO_LECHE_PRODUCTOR = {
    "id": 4,
    "nombre": "Precio al productor de leche – INALE",
    "tipo": "P",
    "fuente": "INALE – Precio leche en tambo y composición",
    "periodicidad": "M",  # mensual
    "unidad": "UYU/litro",  # ajustar según corresponda
    "categoria": "Lácteos",
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
    Devuelve un DataFrame o lanza excepción si falla.
    """
    print("\n[INFO] Intentando leer Excel directamente desde la URL de INALE...")
    leche_productor = pd.read_excel(
        URL_EXCEL_INALE,
        sheet_name="Listado Datos",
        usecols="B,G",  # B = fecha, G = precio
        header=None,
    )
    leche_productor.columns = ["FECHA", "PRECIO"]
    # Filtrar filas donde la fecha no es válida (texto, notas, etc.)
    leche_productor = leche_productor.dropna(subset=["FECHA"])
    # Intentar parsear fechas y filtrar las que no se pueden parsear
    fechas_parseadas = pd.to_datetime(leche_productor["FECHA"], errors="coerce")
    leche_productor = leche_productor[fechas_parseadas.notna()].copy()
    print(f"[OK] Leido desde URL: {len(leche_productor)} registros válidos")
    return leche_productor


def leer_excel_desde_data_raw():
    """
    Lee el Excel local desde data_raw/precio_leche_productor.xlsx.
    Lanza excepción si no existe o falla.
    """
    base_dir = os.getcwd()
    ruta_local = os.path.join(base_dir, DATA_RAW_DIR, LOCAL_EXCEL_NAME)

    if not os.path.exists(ruta_local):
        raise FileNotFoundError(
            f"No se encontró el archivo local esperado: {ruta_local}. "
            "Ejecutá primero el script de descarga (precio_leche_productor en precios/download/productos/)."
        )

    print(f"\n[INFO] Leyendo Excel local desde: {ruta_local}")
    leche_productor = pd.read_excel(
        ruta_local,
        sheet_name="Listado Datos",
        usecols="B,G",  # B = fecha, G = precio
        header=None,
    )
    leche_productor.columns = ["FECHA", "PRECIO"]
    # Filtrar filas donde la fecha no es válida (texto, notas, etc.)
    leche_productor = leche_productor.dropna(subset=["FECHA"])
    # Intentar parsear fechas y filtrar las que no se pueden parsear
    fechas_parseadas = pd.to_datetime(leche_productor["FECHA"], errors="coerce")
    leche_productor = leche_productor[fechas_parseadas.notna()].copy()
    print(f"[OK] Leido desde archivo local: {len(leche_productor)} registros válidos")
    return leche_productor


def manejar_fallo_pandas(error: Exception):
    """
    Maneja el fallo de pandas según el flujo del README (líneas 297-308):
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
    print(f"   URL intentada: {URL_EXCEL_INALE}")
    print("\n[INFO] Según el flujo del README, si pandas falla se debe:")
    print("   1. Crear un script de descarga con Selenium en:")
    print(f"      precios/download/productos/precio_leche_productor.py")
    print("   2. Modificar este script para leer desde data_raw/")
    print(f"      (eliminando el código de pandas de lectura directa)")
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

    # Si confirma, crear los scripts con Selenium
    print("\n[INFO] Creando scripts con Selenium...")
    crear_script_download_selenium()
    modificar_script_update_para_selenium()
    print("\n[OK] Scripts creados/modificados. Ejecutá primero el script de descarga:")
    print(f"   python precios/download/productos/precio_leche_productor.py")
    print("   Luego ejecutá este script nuevamente.")
    sys.exit(0)


def crear_script_download_selenium():
    """Crea el script de descarga con Selenium."""
    script_download_path = os.path.join(
        os.getcwd(), "precios", "download", "productos", "precio_leche_productor.py"
    )
    
    # Asegurar que el directorio existe
    os.makedirs(os.path.dirname(script_download_path), exist_ok=True)

    contenido_download = '''"""
Script: precio_leche_productor
------------------------------
Usa Selenium + Chrome para descargar el Excel de precio al productor de leche de INALE
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
# AJUSTAR ESTA URL SEGÚN LA PÁGINA REAL DE INALE
INALE_LECHE_PRODUCTOR_URL = "https://www.inale.org/..."  # AJUSTAR

# Carpeta y nombre de archivo destino dentro del proyecto
DATA_RAW_DIR = "data_raw"
DEST_FILENAME = "precio_leche_productor.xlsx"


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
    # Deja visible el navegador para debugging; si se quiere headless se puede agregar:
    # chrome_options.add_argument("--headless=new")
    driver = webdriver.Chrome(options=chrome_options)
    return driver


def descargar_excel_inale():
    """
    Abre la página de INALE con Selenium,
    hace clic en el enlace de descarga del Excel y lo guarda en data_raw.

    NOTA: Dependiendo de cómo esté construida la página, puede ser necesario
    ajustar el localizador (By.LINK_TEXT, By.PARTIAL_LINK_TEXT, XPATH, etc.).
    """
    data_raw_path = asegurar_data_raw()
    print(f"[INFO] Carpeta de descargas configurada en: {data_raw_path}")

    driver = configurar_driver_descargas(download_dir=data_raw_path)

    try:
        print(f"[INFO] Abriendo pagina de INALE: {INALE_LECHE_PRODUCTOR_URL}")
        driver.get(INALE_LECHE_PRODUCTOR_URL)

        wait = WebDriverWait(driver, 30)

        # AJUSTAR ESTE SELECTOR SEGÚN LA ESTRUCTURA REAL DE LA PÁGINA
        # Ejemplo: enlace que contiene la palabra "Excel" o similar
        link = wait.until(
            EC.element_to_be_clickable(
                (By.PARTIAL_LINK_TEXT, "Excel")  # AJUSTAR SEGÚN NECESARIO
            )
        )

        print("[INFO] Haciendo clic en el enlace de descarga del Excel...")
        link.click()

        # Esperar a que el archivo aparezca en la carpeta de descargas
        import time

        print("[INFO] Esperando a que termine la descarga...")
        time.sleep(10)

        # Renombrar/mover el archivo descargado al nombre estándar si es necesario
        candidatos = [
            f
            for f in os.listdir(data_raw_path)
            if f.lower().endswith((".xls", ".xlsx"))
        ]
        if not candidatos:
            raise RuntimeError("No se encontro ningun Excel descargado en data_raw.")

        # Elegimos el más reciente por fecha de modificación
        candidatos_paths = [os.path.join(data_raw_path, f) for f in candidatos]
        ultimo = max(candidatos_paths, key=os.path.getmtime)

        destino = os.path.join(data_raw_path, DEST_FILENAME)
        if os.path.abspath(ultimo) != os.path.abspath(destino):
            os.replace(ultimo, destino)

        print(f"[OK] Excel guardado como: {destino}")
        return destino

    finally:
        driver.quit()


if __name__ == "__main__":
    descargar_excel_inale()
'''

    with open(script_download_path, "w", encoding="utf-8") as f:
        f.write(contenido_download)
    
    print(f"[OK] Script de descarga creado: {script_download_path}")


def modificar_script_update_para_selenium():
    """
    Modifica este script para eliminar el código de pandas de lectura directa
    y dejar solo la lectura desde data_raw/.
    """
    # Leer el contenido actual del script
    script_path = __file__
    with open(script_path, "r", encoding="utf-8") as f:
        contenido = f.read()

    # Eliminar la función leer_excel_desde_url() y modificar obtener_datos()
    # Reemplazar obtener_datos() para que solo lea desde data_raw
    nuevo_contenido = contenido.replace(
        'def leer_excel_desde_url():\n    """\n    Intenta leer el Excel directamente desde la URL con pandas.\n    Devuelve un DataFrame o lanza excepción si falla.\n    """\n    print("\\n[INFO] Intentando leer Excel directamente desde la URL de INALE...")\n    leche_productor = pd.read_excel(\n        URL_EXCEL_INALE,\n        sheet_name="Listado Datos",\n        usecols="B,G",  # B = fecha, G = precio\n        header=None,\n    )\n    leche_productor.columns = ["FECHA", "PRECIO"]\n    # Filtrar filas donde la fecha no es válida (texto, notas, etc.)\n    leche_productor = leche_productor.dropna(subset=["FECHA"])\n    # Intentar parsear fechas y filtrar las que no se pueden parsear\n    fechas_parseadas = pd.to_datetime(leche_productor["FECHA"], errors="coerce")\n    leche_productor = leche_productor[fechas_parseadas.notna()].copy()\n    print(f"[OK] Leido desde URL: {len(leche_productor)} registros válidos")\n    return leche_productor\n\n\n',
        '# Función leer_excel_desde_url() eliminada - ahora se usa solo Selenium + data_raw\n\n'
    )

    nuevo_contenido = nuevo_contenido.replace(
        'def obtener_leche_productor():\n    """\n    Implementa el flujo:\n    1) Intentar lectura directa desde URL.\n    2) Si falla, intentar lectura desde data_raw.\n    """\n    try:\n        return leer_excel_desde_url()\n    except Exception as e:\n        print(f"[WARN] No se pudo leer desde la URL: {e}")\n        print("       Se intentara leer el archivo local en data_raw...")\n        return leer_excel_desde_data_raw()',
        'def obtener_leche_productor():\n    """\n    Lee el Excel desde data_raw/ (descargado previamente con Selenium).\n    """\n    return leer_excel_desde_data_raw()'
    )

    nuevo_contenido = nuevo_contenido.replace(
        'def manejar_fallo_pandas(error: Exception):',
        '# Función manejar_fallo_pandas() eliminada - ya no se usa pandas directo\n# def manejar_fallo_pandas(error: Exception):'
    )

    # Guardar el contenido modificado
    with open(script_path, "w", encoding="utf-8") as f:
        f.write(nuevo_contenido)
    
    print(f"[OK] Script de update modificado para usar solo data_raw/")


def obtener_leche_productor():
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
        for fila_excel, fecha, motivo in fechas_invalidas[:10]:
            print(f"   Fila Excel {fila_excel}: {fecha} - {motivo}")
        if len(fechas_invalidas) > 10:
            print(f"   ... y {len(fechas_invalidas) - 10} mas")
        raise ValueError("Hay fechas invalidas. No se puede continuar.")

    df["FECHA"] = pd.to_datetime(df["FECHA"])
    print(f"[OK] Todas las {len(fechas_validas)} fechas son validas")
    print(f"   Rango: {df['FECHA'].min()} a {df['FECHA'].max()}")
    return df


def preparar_datos_maestro_precios(df_leche: pd.DataFrame, maestro_id: int) -> pd.DataFrame:
    """Prepara el DataFrame para maestro_precios."""
    df_precios = df_leche.copy()
    df_precios["maestro_id"] = maestro_id
    df_precios = df_precios[["maestro_id", "FECHA", "PRECIO"]]
    df_precios.columns = ["maestro_id", "fecha", "valor"]
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
    print("ACTUALIZACION DE DATOS: PRECIO AL PRODUCTOR DE LECHE (INALE)")
    print("=" * 60)

    crear_base_datos()

    leche_productor = obtener_leche_productor()
    leche_productor = validar_fechas(leche_productor)

    df_maestro = pd.DataFrame([MAESTRO_LECHE_PRODUCTOR])
    df_precios = preparar_datos_maestro_precios(leche_productor, MAESTRO_LECHE_PRODUCTOR["id"])

    mostrar_resumen(df_maestro, df_precios)

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


if __name__ == "__main__":
    main()
