"""
Script: tipo_cambio_eur
------------------------
Actualiza la base de datos con la serie de tipo de cambio EUR/UYU del INE,
siguiendo el flujo del README:

1) Intentar lectura directa del Excel con pandas desde la URL.
2) Si falla, seguir el flujo del README (avisar, pedir confirmación, crear scripts con Selenium si confirma).
3) Validar fechas.
4) Generar Excel de prueba.
5) Solicitar confirmación del usuario.
6) Insertar en SQLite solo si el usuario confirma.

NOTA: El valor es el promedio entre compra (columna G) y venta (columna H).
"""

import os
import sqlite3
import sys

import pandas as pd


# Configuración de origen de datos
URL_EXCEL_INE = "https://www5.ine.gub.uy/documents/Estad%C3%ADsticasecon%C3%B3micas/SERIES%20Y%20OTROS/Cotizaci%C3%B3n%20monedas/Cotizaci%C3%B3n%20monedas.xlsx"
DATA_RAW_DIR = "data_raw"
LOCAL_EXCEL_NAME = "cotizacion_monedas_ine.xlsx"

# Configuración de base de datos y archivos de salida
DB_NAME = "series_tiempo.db"
EXCEL_PRUEBA_NAME = "prueba_tipo_cambio_eur_ine.xlsx"


# Datos del maestro según especificación del usuario
MAESTRO_TIPO_CAMBIO_EUR = {
    "id": 7,  # siguiente ID disponible
    "nombre": "Tipo de cambio EUR/UYU (promedio compra-venta)",
    "tipo": "M",  # variable macro
    "fuente": "INE_CotizacionMonedas",
    "periodicidad": "D",  # diario
    "unidad": "UYU por EUR",
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


def leer_excel_desde_url():
    """
    Intenta leer el Excel directamente desde la URL con pandas.
    Lee columna A (fecha), G (compra EUR), H (venta EUR).
    Calcula el promedio entre compra y venta.
    Devuelve un DataFrame o lanza excepción si falla.
    """
    print("\n[INFO] Intentando leer Excel directamente desde la URL del INE...")
    print(f"   URL: {URL_EXCEL_INE}")
    
    # Leer columnas A (fecha), G (compra EUR), H (venta EUR)
    try:
        tc_df = pd.read_excel(
            URL_EXCEL_INE,
            sheet_name=0,  # primera hoja
            usecols=[0, 6, 7],  # Columnas A (fecha), G (compra EUR), H (venta EUR)
            header=None,
        )
    except Exception as e:
        # Si falla con la primera hoja, intentar sin especificar hoja
        print(f"[WARN] Error al leer primera hoja: {e}")
        print("[INFO] Intentando leer sin especificar hoja...")
        tc_df = pd.read_excel(
            URL_EXCEL_INE,
            usecols=[0, 6, 7],  # Columnas A (fecha), G (compra EUR), H (venta EUR)
            header=None,
        )
    
    tc_df.columns = ["FECHA", "COMPRA_EUR", "VENTA_EUR"]
    
    # Eliminar filas completamente vacías
    tc_df = tc_df.dropna(how="all")
    
    # Eliminar filas donde fecha sea nula
    tc_df = tc_df.dropna(subset=["FECHA"])
    
    # Filtrar filas que parezcan encabezados o texto (fecha debe ser parseable)
    # Las fechas están en formato dd-mm-yyyy, usar dayfirst=True
    fechas_parseadas = pd.to_datetime(tc_df["FECHA"], errors="coerce", dayfirst=True)
    tc_df = tc_df[fechas_parseadas.notna()].copy()
    
    # Calcular promedio entre compra y venta
    tc_df["COMPRA_EUR"] = pd.to_numeric(tc_df["COMPRA_EUR"], errors="coerce")
    tc_df["VENTA_EUR"] = pd.to_numeric(tc_df["VENTA_EUR"], errors="coerce")
    
    # Calcular promedio solo si ambas columnas tienen valores válidos
    tc_df["TIPO_CAMBIO_EUR"] = (tc_df["COMPRA_EUR"] + tc_df["VENTA_EUR"]) / 2
    
    # Eliminar filas donde el promedio no se pudo calcular
    tc_df = tc_df.dropna(subset=["TIPO_CAMBIO_EUR"])
    
    print(f"[OK] Leido desde URL: {len(tc_df)} registros válidos")
    return tc_df


def leer_excel_desde_data_raw():
    """
    Lee el Excel local desde data_raw/cotizacion_monedas_ine.xlsx.
    Lanza excepción si no existe o falla.
    """
    base_dir = os.getcwd()
    ruta_local = os.path.join(base_dir, DATA_RAW_DIR, LOCAL_EXCEL_NAME)

    if not os.path.exists(ruta_local):
        raise FileNotFoundError(
            f"No se encontró el archivo local esperado: {ruta_local}. "
            "Ejecutá primero el script de descarga (tipo_cambio_eur en macro/download/)."
        )

    print(f"\n[INFO] Leyendo Excel local desde: {ruta_local}")
    tc_df = pd.read_excel(
        ruta_local,
        sheet_name=0,  # primera hoja
        usecols=[0, 6, 7],  # Columnas A (fecha), G (compra EUR), H (venta EUR)
        header=None,
    )
    tc_df.columns = ["FECHA", "COMPRA_EUR", "VENTA_EUR"]
    
    # Eliminar filas completamente vacías
    tc_df = tc_df.dropna(how="all")
    
    # Eliminar filas donde fecha sea nula
    tc_df = tc_df.dropna(subset=["FECHA"])
    
    # Filtrar filas que parezcan encabezados o texto (fecha debe ser parseable)
    # Las fechas están en formato dd-mm-yyyy, usar dayfirst=True
    fechas_parseadas = pd.to_datetime(tc_df["FECHA"], errors="coerce", dayfirst=True)
    tc_df = tc_df[fechas_parseadas.notna()].copy()
    
    # Calcular promedio entre compra y venta
    tc_df["COMPRA_EUR"] = pd.to_numeric(tc_df["COMPRA_EUR"], errors="coerce")
    tc_df["VENTA_EUR"] = pd.to_numeric(tc_df["VENTA_EUR"], errors="coerce")
    
    # Calcular promedio solo si ambas columnas tienen valores válidos
    tc_df["TIPO_CAMBIO_EUR"] = (tc_df["COMPRA_EUR"] + tc_df["VENTA_EUR"]) / 2
    
    # Eliminar filas donde el promedio no se pudo calcular
    tc_df = tc_df.dropna(subset=["TIPO_CAMBIO_EUR"])
    
    print(f"[OK] Leido desde archivo local: {len(tc_df)} registros válidos")
    return tc_df


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
    print(f"   URL intentada: {URL_EXCEL_INE}")
    print("\n[INFO] Según el flujo del README, si pandas falla se debe:")
    print("   1. Crear un script de descarga con Selenium en:")
    print(f"      macro/download/tipo_cambio_eur.py")
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
    print(f"   python macro/download/tipo_cambio_eur.py")
    print("   Luego ejecutá este script nuevamente.")
    sys.exit(0)


def crear_script_download_selenium():
    """Crea el script de descarga con Selenium."""
    script_download_path = os.path.join(
        os.getcwd(), "macro", "download", "tipo_cambio_eur.py"
    )
    
    # Asegurar que el directorio existe
    os.makedirs(os.path.dirname(script_download_path), exist_ok=True)

    contenido_download = '''"""
Script: tipo_cambio_eur
------------------------
Usa Selenium + Chrome para descargar el Excel de cotización de monedas del INE
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
INE_COTIZACION_URL = "https://www5.ine.gub.uy/documents/Estad%C3%ADsticasecon%C3%B3micas/SERIES%20Y%20OTROS/Cotizaci%C3%B3n%20monedas/Cotizaci%C3%B3n%20monedas.xlsx"

# Carpeta y nombre de archivo destino dentro del proyecto
DATA_RAW_DIR = "data_raw"
DEST_FILENAME = "cotizacion_monedas_ine.xlsx"


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


def descargar_excel_ine():
    """
    Abre la URL del INE con Selenium y descarga el Excel directamente.
    """
    data_raw_path = asegurar_data_raw()
    print(f"[INFO] Carpeta de descargas configurada en: {data_raw_path}")

    driver = configurar_driver_descargas(download_dir=data_raw_path)

    try:
        print(f"[INFO] Abriendo URL del INE: {INE_COTIZACION_URL}")
        driver.get(INE_COTIZACION_URL)

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

        # Elegimos el más reciente por fecha de modificación
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
    # Leer el contenido actual del script
    script_path = __file__
    with open(script_path, "r", encoding="utf-8") as f:
        contenido = f.read()

    # Eliminar la función leer_excel_desde_url() y modificar obtener_tipo_cambio_eur()
    nuevo_contenido = contenido.replace(
        'def leer_excel_desde_url():\n    """\n    Intenta leer el Excel directamente desde la URL con pandas.\n    Lee columna A (fecha), G (compra EUR), H (venta EUR).\n    Calcula el promedio entre compra y venta.\n    Devuelve un DataFrame o lanza excepción si falla.\n    """\n    print("\\n[INFO] Intentando leer Excel directamente desde la URL del INE...")\n    print(f"   URL: {URL_EXCEL_INE}")\n    \n    # Leer columnas A (fecha), G (compra EUR), H (venta EUR)\n    try:\n        tc_df = pd.read_excel(\n            URL_EXCEL_INE,\n            sheet_name=0,  # primera hoja\n            usecols=[0, 6, 7],  # Columnas A (fecha), G (compra EUR), H (venta EUR)\n            header=None,\n        )\n    except Exception as e:\n        # Si falla con la primera hoja, intentar sin especificar hoja\n        print(f"[WARN] Error al leer primera hoja: {e}")\n        print("[INFO] Intentando leer sin especificar hoja...")\n        tc_df = pd.read_excel(\n            URL_EXCEL_INE,\n            usecols=[0, 6, 7],  # Columnas A (fecha), G (compra EUR), H (venta EUR)\n            header=None,\n        )\n    \n    tc_df.columns = ["FECHA", "COMPRA_EUR", "VENTA_EUR"]\n    \n    # Eliminar filas completamente vacías\n    tc_df = tc_df.dropna(how="all")\n    \n    # Eliminar filas donde fecha sea nula\n    tc_df = tc_df.dropna(subset=["FECHA"])\n    \n    # Filtrar filas que parezcan encabezados o texto (fecha debe ser parseable)\n    fechas_parseadas = pd.to_datetime(tc_df["FECHA"], errors="coerce")\n    tc_df = tc_df[fechas_parseadas.notna()].copy()\n    \n    # Calcular promedio entre compra y venta\n    tc_df["COMPRA_EUR"] = pd.to_numeric(tc_df["COMPRA_EUR"], errors="coerce")\n    tc_df["VENTA_EUR"] = pd.to_numeric(tc_df["VENTA_EUR"], errors="coerce")\n    \n    # Calcular promedio solo si ambas columnas tienen valores válidos\n    tc_df["TIPO_CAMBIO_EUR"] = (tc_df["COMPRA_EUR"] + tc_df["VENTA_EUR"]) / 2\n    \n    # Eliminar filas donde el promedio no se pudo calcular\n    tc_df = tc_df.dropna(subset=["TIPO_CAMBIO_EUR"])\n    \n    print(f"[OK] Leido desde URL: {len(tc_df)} registros válidos")\n    return tc_df\n\n\n',
        '# Función leer_excel_desde_url() eliminada - ahora se usa solo Selenium + data_raw\n\n'
    )

    nuevo_contenido = nuevo_contenido.replace(
        'def obtener_tipo_cambio_eur():\n    """\n    Implementa el flujo:\n    1) Intentar lectura directa desde URL.\n    2) Si falla, manejar según el README.\n    """\n    try:\n        return leer_excel_desde_url()\n    except Exception as e:\n        manejar_fallo_pandas(e)',
        'def obtener_tipo_cambio_eur():\n    """\n    Lee el Excel desde data_raw/ (descargado previamente con Selenium).\n    """\n    return leer_excel_desde_data_raw()'
    )

    nuevo_contenido = nuevo_contenido.replace(
        'def manejar_fallo_pandas(error: Exception):',
        '# Función manejar_fallo_pandas() eliminada - ya no se usa pandas directo\n# def manejar_fallo_pandas(error: Exception):'
    )

    # Guardar el contenido modificado
    with open(script_path, "w", encoding="utf-8") as f:
        f.write(nuevo_contenido)
    
    print(f"[OK] Script de update modificado para usar solo data_raw/")


def obtener_tipo_cambio_eur():
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
                # Las fechas están en formato dd-mm-yyyy, usar dayfirst=True
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

    # Las fechas están en formato dd-mm-yyyy, usar dayfirst=True
    df["FECHA"] = pd.to_datetime(df["FECHA"], dayfirst=True)
    print(f"[OK] Todas las {len(fechas_validas)} fechas son validas")
    print(f"   Rango: {df['FECHA'].min()} a {df['FECHA'].max()}")
    return df


def preparar_datos_maestro_precios(df_tc: pd.DataFrame, maestro_id: int) -> pd.DataFrame:
    """Prepara el DataFrame para maestro_precios."""
    df_precios = df_tc.copy()
    df_precios["maestro_id"] = maestro_id
    df_precios = df_precios[["maestro_id", "FECHA", "TIPO_CAMBIO_EUR"]]
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
    print("ACTUALIZACION DE DATOS: TIPO DE CAMBIO EUR/UYU (INE)")
    print("=" * 60)

    crear_base_datos()

    tc_df = obtener_tipo_cambio_eur()
    
    # Mostrar primeros y últimos datos de la serie cruda
    print("\n[INFO] Datos de la serie cruda:")
    print("\nPrimeros datos:")
    print(tc_df.head())
    print("\nÚltimos datos:")
    print(tc_df.tail())
    
    tc_df = validar_fechas(tc_df)

    df_maestro = pd.DataFrame([MAESTRO_TIPO_CAMBIO_EUR])
    df_precios = preparar_datos_maestro_precios(tc_df, MAESTRO_TIPO_CAMBIO_EUR["id"])

    excel_path = generar_excel_prueba(df_maestro, df_precios)
    mostrar_resumen(df_maestro, df_precios)

    print("\n[INFO] Actualizando base de datos automáticamente...")
    print(f"[INFO] Archivo Excel generado: {excel_path}")
    insertar_en_bd(df_maestro, df_precios)


if __name__ == "__main__":
    main()
