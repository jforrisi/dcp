"""
Script: commodities_banco_mundial
--------------------------------
Descarga el Excel "CMO Historical Data Monthly" (Monthly prices) desde el Banco Mundial.
URL: https://www.worldbank.org/en/research/commodity-markets
Archivo: CMO-Historical-Data-Monthly.xlsx
Se guarda como: commodities_banco_mundial.xlsx en update/historicos
"""

import os
import sys
import time
import requests
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service

# Agregar el directorio raíz al path para importar utils
root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

from update.utils.logger import ScriptLogger

# URL directa al Excel (Monthly prices)
EXCEL_URL = "https://thedocs.worldbank.org/en/doc/74e8be41ceb20fa0da750cda2f6b9e4e-0050012026/related/CMO-Historical-Data-Monthly.xlsx"

# Carpeta y nombre de archivo destino
HISTORICOS_DIR = "update/historicos"
DEST_FILENAME = "commodities_banco_mundial.xlsx"


def asegurar_historicos():
    """Crea la carpeta update/historicos si no existe y devuelve su ruta absoluta."""
    base_dir = os.getcwd()
    historicos_path = os.path.join(base_dir, HISTORICOS_DIR)
    os.makedirs(historicos_path, exist_ok=True)
    return historicos_path


def descargar_con_requests(url: str, destino: str) -> bool:
    """Intenta descargar el archivo usando requests."""
    try:
        print(f"[INFO] Intentando descargar con requests...")
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        response = requests.get(url, headers=headers, timeout=60, stream=True)
        response.raise_for_status()

        content_type = response.headers.get('Content-Type', '').lower()
        if 'excel' not in content_type and 'spreadsheet' not in content_type and 'application/octet-stream' not in content_type:
            print(f"[WARN] Content-Type: {content_type}")

        with open(destino, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)

        if os.path.exists(destino) and os.path.getsize(destino) > 0:
            print(f"[OK] Descargado con requests: {os.path.getsize(destino)} bytes")
            return True
        return False
    except Exception as e:
        print(f"[WARN] requests falló: {e}")
        return False


def descargar_con_selenium(url: str, destino: str) -> bool:
    """Descarga usando Selenium (navegador)."""
    historicos_path = os.path.dirname(destino)
    historicos_path_abs = os.path.abspath(historicos_path)

    chrome_options = Options()
    prefs = {
        "download.default_directory": historicos_path_abs,
        "download.prompt_for_download": False,
        "download.directory_upgrade": True,
        "safebrowsing.enabled": True,
    }
    chrome_options.add_experimental_option("prefs", prefs)

    is_railway = os.getenv('RAILWAY_ENVIRONMENT') or os.getenv('RAILWAY') or os.getenv('AZURE_ENVIRONMENT') or os.getenv('AZURE')
    if is_railway:
        chrome_options.add_argument("--headless=new")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")

    driver = None
    try:
        driver = webdriver.Chrome(options=chrome_options)
        archivos_antes = set(os.listdir(historicos_path))
        print(f"[INFO] Navegando a la URL del Excel...")
        driver.get(url)
        print("[INFO] Esperando descarga...")
        for _ in range(60):
            time.sleep(1)
            archivos_ahora = set(os.listdir(historicos_path))
            archivos_nuevos = archivos_ahora - archivos_antes
            excel_nuevos = [f for f in archivos_nuevos if f.lower().endswith((".xls", ".xlsx"))]
            if excel_nuevos:
                ultimo = max(
                    (os.path.join(historicos_path, f) for f in excel_nuevos),
                    key=os.path.getmtime
                )
                if os.path.abspath(ultimo) != os.path.abspath(destino):
                    if os.path.exists(destino):
                        os.remove(destino)
                    os.replace(ultimo, destino)
                print(f"[OK] Descargado con Selenium: {destino}")
                return True
        print("[ERROR] Timeout esperando descarga")
        return False
    except Exception as e:
        print(f"[ERROR] Selenium falló: {e}")
        return False
    finally:
        if driver:
            driver.quit()


def descargar_excel():
    """Descarga el Excel del Banco Mundial."""
    historicos_path = asegurar_historicos()
    destino = os.path.join(historicos_path, DEST_FILENAME)
    print(f"[INFO] Destino: {destino}")

    if descargar_con_requests(EXCEL_URL, destino):
        return destino
    if descargar_con_selenium(EXCEL_URL, destino):
        return destino
    raise RuntimeError("No se pudo descargar el Excel del Banco Mundial")


def main():
    """Función principal."""
    script_name = "commodities_banco_mundial"

    with ScriptLogger(script_name) as logger:
        try:
            logger.info("=" * 80)
            logger.info("DESCARGA DE COMMODITIES - BANCO MUNDIAL (CMO Historical Data Monthly)")
            logger.info("=" * 80)

            historicos_path = asegurar_historicos()
            logger.info(f"Carpeta de descargas: {historicos_path}")

            destino = descargar_excel()
            logger.info(f"Excel guardado como: {destino}")
            logger.info("=" * 80)
            logger.info("PROCESO COMPLETADO EXITOSAMENTE")
            logger.info("=" * 80)
            return destino

        except Exception as e:
            logger.log_exception(e, "main()")
            raise


if __name__ == "__main__":
    main()
