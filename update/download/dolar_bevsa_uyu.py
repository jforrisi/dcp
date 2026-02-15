"""
Script: dolar_bevsa_uyu
------------------------
Descarga el Excel del dólar BEVSA desde el botón "Exportar" en HistoricoDiario.aspx
(viene con formato correcto). Guarda en dolar_bevsa_uyu_temp.xlsx y hace merge con
dolar_bevsa_uyu.xlsx (base histórica).
"""

import os
import sys
import time
import pandas as pd
from datetime import datetime, timedelta
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# Agregar el directorio raíz al path para importar utils
root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

from update.utils.logger import ScriptLogger

# URL de la página BEVSA - Histórico diario del dólar
BEVSA_URL = "https://web.bevsa.com.uy/Mercado/MercadoCambios/HistoricoDiario.aspx"

# Carpeta destino: siempre update/historicos del proyecto (de ahí lee la base de datos)
DOWNLOAD_DIR = os.path.join(root_dir, "update", "historicos")
DEST_FILENAME = "dolar_bevsa_uyu_temp.xlsx"
HISTORICO_FILENAME = "dolar_bevsa_uyu.xlsx"
HISTORICO_FALLBACK = "dolar_bevsa_uy.xlsx"  # Si dolar_bevsa_uyu no existe
ULTIMOS_N = 60

# ID del botón Exportar Excel en BEVSA
EXPORTAR_BUTTON_ID = "ContentPlaceHolder1_LinkButton2"


def asegurar_directorio():
    """Crea el directorio de descarga si no existe y devuelve su ruta absoluta."""
    os.makedirs(DOWNLOAD_DIR, exist_ok=True)
    return os.path.abspath(DOWNLOAD_DIR)


def configurar_driver(download_dir):
    """Configura Chrome con carpeta de descargas y perfil BEVSA."""
    chrome_options = Options()
    base_dir = os.getcwd()
    user_data_dir = os.path.join(base_dir, ".chrome_profile_bevsa")
    os.makedirs(user_data_dir, exist_ok=True)
    chrome_options.add_argument(f"--user-data-dir={user_data_dir}")

    prefs = {
        "download.default_directory": download_dir,
        "download.prompt_for_download": False,
        "download.directory_upgrade": True,
        "safebrowsing.enabled": True,
    }
    chrome_options.add_experimental_option("prefs", prefs)

    is_railway = os.getenv('RAILWAY_ENVIRONMENT') or os.getenv('RAILWAY')
    is_azure = os.getenv('AZURE_ENVIRONMENT') or os.getenv('AZURE') or os.getenv('WEBSITE_INSTANCE_ID') or os.getenv('AZURE_FUNCTIONS_ENVIRONMENT') or os.getenv('CONTAINER_NAME')
    is_cloud = is_railway or is_azure

    if is_cloud:
        chrome_options.add_argument("--headless=new")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument("--disable-extensions")
        chrome_options.add_argument("--disable-setuid-sandbox")
        chrome_options.add_argument("--disable-web-security")
        chrome_options.add_argument("--disable-features=VizDisplayCompositor")
        chrome_options.add_argument("--remote-debugging-port=9222")
        chrome_options.add_argument("--remote-debugging-address=0.0.0.0")
        chrome_options.add_argument("--no-first-run")
        chrome_options.add_argument("--no-default-browser-check")
        chrome_options.add_argument("--disable-background-networking")
        chrome_options.add_argument("--disable-popup-blocking")
        chrome_options.add_argument("--disable-sync")
        chrome_options.add_argument("--disable-translate")
        chrome_options.add_argument("--metrics-recording-only")
        chrome_options.add_argument("--no-crash-upload")
        chrome_options.add_argument("--mute-audio")
        chrome_options.add_argument("--hide-scrollbars")

        chrome_bin = os.getenv('CHROME_BIN')
        if not chrome_bin:
            for path in ['/root/.nix-profile/bin/chromium', '/usr/bin/google-chrome', '/usr/bin/chromium-browser', '/usr/bin/chromium']:
                if os.path.exists(path):
                    chrome_bin = path
                    break
        if chrome_bin and os.path.exists(chrome_bin):
            chrome_options.binary_location = chrome_bin

        chromedriver_path = os.getenv('CHROMEDRIVER_PATH')
        if not chromedriver_path:
            for path in ['/root/.nix-profile/bin/chromedriver', '/usr/bin/chromedriver', '/usr/local/bin/chromedriver']:
                if os.path.exists(path):
                    chromedriver_path = path
                    break

        if chromedriver_path and os.path.exists(chromedriver_path):
            service = Service(chromedriver_path)
            driver = webdriver.Chrome(service=service, options=chrome_options)
        else:
            driver = webdriver.Chrome(options=chrome_options)
        time.sleep(2)
    else:
        driver = webdriver.Chrome(options=chrome_options)

    return driver


def aceptar_terminos(driver):
    """Acepta términos y condiciones si aparece el disclaimer."""
    from selenium.common.exceptions import NoSuchWindowException, WebDriverException
    try:
        wait = WebDriverWait(driver, 10)
        checkbox = wait.until(EC.presence_of_element_located((By.ID, "ContentPlaceHolder1_chkAcceptTerms")))
        driver.execute_script("arguments[0].scrollIntoView(true);", checkbox)
        time.sleep(0.5)
        if not checkbox.is_selected():
            checkbox.click()
            time.sleep(1)
        aceptar_button = wait.until(EC.presence_of_element_located((By.ID, "ContentPlaceHolder1_btnContinue")))
        if aceptar_button.get_attribute("disabled"):
            wait.until(lambda d: not d.find_element(By.ID, "ContentPlaceHolder1_btnContinue").get_attribute("disabled"))
        driver.execute_script("arguments[0].scrollIntoView(true);", aceptar_button)
        time.sleep(0.5)
        aceptar_button.click()
        print("[INFO] Términos aceptados")
        time.sleep(3)
    except Exception as e:
        print(f"[WARN] Error al aceptar términos: {e}")


def detectar_anti_bot(driver):
    """Detecta si hay anti-bot/CAPTCHA."""
    try:
        indicators = ["captcha", "cloudflare", "challenge", "verification", "hcaptcha", "recaptcha", "turnstile"]
        source = driver.page_source.lower()
        title = driver.title.lower()
        for ind in indicators:
            if ind in source or ind in title:
                return True
        try:
            driver.find_element(By.ID, "challenge-form")
            return True
        except Exception:
            pass
        try:
            driver.find_element(By.CLASS_NAME, "cf-browser-verification")
            return True
        except Exception:
            pass
    except Exception:
        pass
    return False


def esperar_resolucion_anti_bot(driver):
    """Espera hasta 20 segundos si hay anti-bot (antes 60s, demasiado lento)."""
    print("[INFO] Anti-bot detectado, esperando 20 segundos...")
    for _ in range(4):
        try:
            _ = driver.current_url
            time.sleep(5)
        except Exception:
            raise RuntimeError("Chrome se cerró durante la espera")
    print("[INFO] Continuando...")


def descargar_excel_bevsa(driver, download_path):
    """
    Navega a BEVSA, acepta términos si hace falta, hace clic en Exportar
    y espera el Excel descargado. Lo copia/renombra a dolar_bevsa_uyu_temp.xlsx.
    Devuelve la ruta del archivo o None si falla.
    """
    print(f"[INFO] Accediendo a: {BEVSA_URL}")
    driver.get(BEVSA_URL)
    time.sleep(3)

    if "Disclaimer.aspx" in driver.current_url:
        aceptar_terminos(driver)
        driver.get(BEVSA_URL)
        time.sleep(3)
    else:
        try:
            cb = driver.find_element(By.ID, "ContentPlaceHolder1_chkAcceptTerms")
            if cb:
                aceptar_terminos(driver)
                driver.get(BEVSA_URL)
                time.sleep(3)
        except Exception:
            pass

    if detectar_anti_bot(driver):
        esperar_resolucion_anti_bot(driver)

    # Buscar y hacer clic en el botón Exportar (LinkButton2)
    print("[INFO] Buscando botón Exportar Excel...")
    wait = WebDriverWait(driver, 15)
    try:
        btn_exportar = wait.until(
            EC.element_to_be_clickable((By.ID, EXPORTAR_BUTTON_ID))
        )
        driver.execute_script("arguments[0].scrollIntoView(true);", btn_exportar)
        time.sleep(0.5)
        archivos_antes = set(f for f in os.listdir(download_path) if f.endswith(('.xlsx', '.xls')))
        btn_exportar.click()
        print("[INFO] Clic en Exportar, esperando descarga...")
    except Exception as e:
        raise RuntimeError(f"No se encontró el botón Exportar ({EXPORTAR_BUTTON_ID}): {e}")

    # Esperar a que aparezca el archivo Excel
    tiempo_max = 30
    inicio = time.time()
    archivo_descargado = None
    while time.time() - inicio < tiempo_max:
        time.sleep(1)
        archivos_ahora = set(f for f in os.listdir(download_path) if f.endswith(('.xlsx', '.xls')))
        nuevos = archivos_ahora - archivos_antes
        # Excluir .crdownload y archivos temporales
        completos = [f for f in nuevos if not f.endswith('.crdownload') and not f.endswith('.tmp')]
        if completos:
            archivo_descargado = completos[0]
            break
    if not archivo_descargado:
        raise RuntimeError(f"Timeout: no se detectó archivo Excel descargado en {tiempo_max}s")

    origen = os.path.join(download_path, archivo_descargado)
    destino = os.path.join(download_path, DEST_FILENAME)

    # El Excel descargado ya tiene formato correcto. Si tiene más de 60 filas, tomar últimas 60
    df = pd.read_excel(origen, engine='openpyxl')
    fecha_col = df.columns[0] if len(df.columns) > 0 else None
    if fecha_col and len(df) > ULTIMOS_N:
        df[fecha_col] = pd.to_datetime(df[fecha_col], errors='coerce')
        df = df.dropna(subset=[fecha_col])
        df = df.sort_values(fecha_col, ascending=False).head(ULTIMOS_N).sort_values(fecha_col, ascending=True)
    df.to_excel(destino, index=False, engine='openpyxl')
    if archivo_descargado != DEST_FILENAME and os.path.exists(origen):
        try:
            os.remove(origen)
        except Exception:
            pass
    print(f"[OK] Excel guardado: {destino} ({len(df)} filas)")
    return destino


def actualizar_historico(download_path):
    """Merge de dolar_bevsa_uyu_temp con dolar_bevsa_uyu (o dolar_bevsa_uy como fallback)."""
    historico_path = os.path.join(download_path, HISTORICO_FILENAME)
    historico_fallback = os.path.join(download_path, HISTORICO_FALLBACK)
    temp_path = os.path.join(download_path, DEST_FILENAME)

    print("\n[INFO] Actualizando archivo histórico con merge...")

    # Se asume que el histórico siempre existe (dolar_bevsa_uyu.xlsx o dolar_bevsa_uy.xlsx)
    path_historico = historico_path if os.path.exists(historico_path) else historico_fallback
    if not os.path.exists(path_historico):
        print(f"[ERROR] No existe el archivo histórico. Debe existir {HISTORICO_FILENAME} o {HISTORICO_FALLBACK} en {download_path}")
        return

    df_historico = pd.read_excel(path_historico, engine='openpyxl')
    print(f"[OK] Histórico leído: {path_historico} ({len(df_historico)} registros)")

    if not os.path.exists(temp_path):
        print(f"[ERROR] No existe el archivo temporal: {temp_path}")
        return

    df_temp = pd.read_excel(temp_path, engine='openpyxl')
    print(f"[OK] Temp leído: {len(df_temp)} registros")

    # Normalizar columna fecha si viene como MultiIndex string ej: "('FECHA', 'Unnamed: 0_level_1')"
    def _norm_fecha_col(df_in):
        for col in df_in.columns:
            s = str(col).strip()
            if s.upper() == 'FECHA':
                return col
            if s.startswith("('") and "FECHA" in s.upper() and "'," in s:
                return col
        return df_in.columns[0]

    fecha_col_hist = _norm_fecha_col(df_historico)
    fecha_col_temp = _norm_fecha_col(df_temp)

    if fecha_col_hist not in df_historico.columns:
        fecha_col_hist = df_historico.columns[0]
    if fecha_col_temp not in df_temp.columns:
        fecha_col_temp = df_temp.columns[0]

    # Estandarizar a FECHA en ambos
    if str(fecha_col_temp).strip().upper() != 'FECHA':
        df_temp = df_temp.rename(columns={fecha_col_temp: 'FECHA'})
        fecha_col_temp = 'FECHA'
    if str(fecha_col_hist).strip().upper() != 'FECHA':
        df_historico = df_historico.rename(columns={fecha_col_hist: 'FECHA'})
        fecha_col_hist = 'FECHA'
    fecha_col = 'FECHA'

    df_historico[fecha_col] = pd.to_datetime(df_historico[fecha_col], errors='coerce')
    df_historico = df_historico.dropna(subset=[fecha_col])
    df_temp[fecha_col] = pd.to_datetime(df_temp[fecha_col], errors='coerce')
    df_temp = df_temp.dropna(subset=[fecha_col])

    if df_historico.empty:
        df_combinado = df_temp.copy()
    else:
        all_cols = set(df_historico.columns) | set(df_temp.columns)
        df_merged = pd.merge(
            df_historico, df_temp,
            on=fecha_col, how='outer',
            suffixes=('_hist', '_nuevo')
        )
        df_combinado = pd.DataFrame()
        df_combinado[fecha_col] = df_merged[fecha_col]
        for col in all_cols:
            if col == fecha_col:
                continue
            ch = f"{col}_hist" if f"{col}_hist" in df_merged.columns else None
            cn = f"{col}_nuevo" if f"{col}_nuevo" in df_merged.columns else None
            if ch and cn:
                df_combinado[col] = df_merged[cn].fillna(df_merged[ch])
            elif cn:
                df_combinado[col] = df_merged[cn]
            elif ch:
                df_combinado[col] = df_merged[ch]

    df_combinado = df_combinado.dropna(subset=[fecha_col])
    df_combinado = df_combinado.sort_values(fecha_col, ascending=True).reset_index(drop=True)

    output_path = os.path.join(download_path, HISTORICO_FILENAME)
    df_combinado.to_excel(output_path, index=False, engine='openpyxl')
    print(f"[OK] Histórico actualizado: {output_path} ({len(df_combinado)} registros)")
    if len(df_combinado) > 0:
        print(f"     Rango: {df_combinado[fecha_col].min()} a {df_combinado[fecha_col].max()}")


def main():
    script_name = "dolar_bevsa_uyu"
    with ScriptLogger(script_name) as logger:
        try:
            logger.info("=" * 80)
            logger.info("EXTRACCIÓN DÓLAR BEVSA - HISTÓRICO DIARIO")
            logger.info("=" * 80)

            download_path = asegurar_directorio()
            logger.info(f"Carpeta: {download_path}")

            logger.info("Configurando Chrome...")
            driver = configurar_driver(download_path)

            logger.info("Descargando Excel desde BEVSA (botón Exportar)...")
            descargar_excel_bevsa(driver, download_path)

            logger.info("Actualizando histórico...")
            actualizar_historico(download_path)

            logger.info("=" * 80)
            logger.info("PROCESO COMPLETADO EXITOSAMENTE")
            logger.info("=" * 80)

        except Exception as e:
            logger.log_exception(e, "main()")
            raise
        finally:
            if 'driver' in locals():
                try:
                    driver.quit()
                except Exception:
                    pass


if __name__ == "__main__":
    main()
