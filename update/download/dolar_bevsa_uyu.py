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
MAX_STALENESS_DAYS = int(os.getenv("BEVSA_MAX_STALENESS_DAYS", "5"))

# ID del botón Exportar Excel en BEVSA (puede cambiar con actualizaciones del sitio)
EXPORTAR_BUTTON_ID = "ContentPlaceHolder1_LinkButton2"
# Selectores alternativos por si BEVSA cambia el ID
EXPORTAR_SELECTORS = [
    (By.ID, EXPORTAR_BUTTON_ID),
    (By.CSS_SELECTOR, "a[id*='LinkButton2']"),
    (By.PARTIAL_LINK_TEXT, "Exportar"),
    (By.LINK_TEXT, "Exportar"),
    (By.XPATH, "//a[contains(., 'Exportar')]"),
    (By.XPATH, "//input[@type='submit' or @type='button'][contains(@value, 'Exportar')]"),
]


def en_ci():
    """True si corre en GitHub Actions u otro CI; ahí no se puede resolver CAPTCHA manual."""
    if os.getenv("GITHUB_ACTIONS") == "true":
        return True
    if os.getenv("RAILWAY_ENVIRONMENT") or os.getenv("RAILWAY"):
        return True
    if os.getenv("AZURE_ENVIRONMENT") or os.getenv("AZURE") or os.getenv("WEBSITE_INSTANCE_ID"):
        return True
    return False


def asegurar_directorio():
    """Crea el directorio de descarga si no existe y devuelve su ruta absoluta."""
    os.makedirs(DOWNLOAD_DIR, exist_ok=True)
    return os.path.abspath(DOWNLOAD_DIR)


def configurar_driver(download_dir):
    """Configura Chrome con undetected_chromedriver (local y CI) para evitar Cloudflare."""
    base_dir = os.getcwd()
    user_data_dir = os.path.join(base_dir, ".chrome_profile_bevsa")
    os.makedirs(user_data_dir, exist_ok=True)

    is_cloud = bool(
        os.getenv('GITHUB_ACTIONS') or os.getenv('RAILWAY_ENVIRONMENT') or os.getenv('RAILWAY')
        or os.getenv('AZURE_ENVIRONMENT') or os.getenv('AZURE') or os.getenv('WEBSITE_INSTANCE_ID')
    )
    chrome_bin = os.getenv('CHROME_BIN') or ""
    if not chrome_bin:
        for p in ['/usr/bin/google-chrome', '/usr/bin/chromium-browser', '/usr/bin/chromium',
                   '/root/.nix-profile/bin/chromium']:
            if os.path.exists(p):
                chrome_bin = p
                break

    # -- Intentar undetected_chromedriver (local y CI) --
    try:
        import undetected_chromedriver as uc
        uc_options = uc.ChromeOptions()
        uc_options.add_experimental_option("prefs", {
            "download.default_directory": download_dir,
            "download.prompt_for_download": False,
            "download.directory_upgrade": True,
            "safebrowsing.enabled": True,
        })
        if is_cloud:
            uc_options.add_argument("--no-sandbox")
            uc_options.add_argument("--disable-dev-shm-usage")
            uc_options.add_argument("--disable-gpu")
            uc_options.add_argument("--window-size=1920,1080")

        uc_kwargs = {"options": uc_options, "headless": is_cloud}
        if not is_cloud:
            uc_kwargs["user_data_dir"] = user_data_dir
        if chrome_bin and os.path.exists(chrome_bin):
            uc_kwargs["browser_executable_path"] = chrome_bin

        driver = uc.Chrome(**uc_kwargs)
        for cdp in ["Browser.setDownloadBehavior", "Page.setDownloadBehavior"]:
            try:
                driver.execute_cdp_cmd(cdp, {"behavior": "allow", "downloadPath": download_dir})
                break
            except Exception:
                pass
        print(f"[INFO] undetected_chromedriver OK (headless={is_cloud})")
        return driver
    except Exception as e:
        print(f"[WARN] undetected_chromedriver falló: {e}")

    # -- Fallback: Selenium estándar --
    print("[INFO] Usando Selenium estándar como fallback")
    fb = Options()
    fb.add_experimental_option("prefs", {
        "download.default_directory": download_dir,
        "download.prompt_for_download": False,
        "download.directory_upgrade": True,
        "safebrowsing.enabled": True,
    })
    fb.add_experimental_option("excludeSwitches", ["enable-automation"])
    fb.add_experimental_option("useAutomationExtension", False)
    fb.add_argument("--disable-blink-features=AutomationControlled")
    fb.add_argument(f"--user-data-dir={user_data_dir}")
    if is_cloud:
        fb.add_argument("--headless=new")
        fb.add_argument("--no-sandbox")
        fb.add_argument("--disable-dev-shm-usage")
        fb.add_argument("--disable-gpu")
        fb.add_argument("--window-size=1920,1080")
    if chrome_bin and os.path.exists(chrome_bin):
        fb.binary_location = chrome_bin
    chromedriver_path = os.getenv('CHROMEDRIVER_PATH', '')
    if chromedriver_path and os.path.exists(chromedriver_path):
        driver = webdriver.Chrome(service=Service(chromedriver_path), options=fb)
    else:
        driver = webdriver.Chrome(options=fb)
    time.sleep(2)
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
    """Detecta si hay anti-bot/CAPTCHA (excluye Disclaimer.aspx que es la página de términos)."""
    try:
        from urllib.parse import urlparse
        url = (driver.current_url or "").lower()
        path = urlparse(url).path.lower()

        if "checkpoint" in path:
            return True
        if "disclaimer.aspx" in path:
            return False
        if "historicodiario" in path or "historico.aspx" in path:
            return False
        indicators = [
            "captcha",
            "cloudflare",
            "challenge",
            "verification",
            "verificación",
            "security check",
            "seguridad",
            "hcaptcha",
            "recaptcha",
            "turnstile",
        ]
        title = driver.title.lower()
        for ind in indicators:
            if ind in title:
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


def intentar_click_turnstile(driver):
    """Intenta encontrar y clicar el checkbox del Turnstile dentro de iframes."""
    try:
        iframes = driver.find_elements(By.CSS_SELECTOR,
            "iframe[src*='turnstile'], iframe[src*='challenges.cloudflare.com']")
        for iframe in iframes:
            try:
                driver.switch_to.frame(iframe)
                for sel in ["input[type='checkbox']", ".cb-lb", "#challenge-stage"]:
                    try:
                        el = driver.find_element(By.CSS_SELECTOR, sel)
                        el.click()
                        print(f"[INFO] Turnstile element clicked: {sel}")
                        driver.switch_to.default_content()
                        return True
                    except Exception:
                        pass
                driver.switch_to.default_content()
            except Exception:
                driver.switch_to.default_content()
    except Exception:
        pass
    return False


def esperar_resolucion_anti_bot(driver, target_url=None, max_wait=45):
    """Espera resolución de Turnstile: auto-resolución con uc, click en iframe, o espera manual."""
    print(f"[INFO] Anti-bot detectado. URL actual: {driver.current_url}")
    print(f"[INFO] Esperando resolución automática (hasta {max_wait}s)...")

    for i in range(max_wait // 3):
        time.sleep(3)
        cur = driver.current_url or ""
        if target_url and target_url.split("?")[0] in cur:
            print("[INFO] Redirigido a la página objetivo, anti-bot resuelto.")
            return True
        if not detectar_anti_bot(driver):
            print("[INFO] Anti-bot ya no detectado en la página.")
            return True
        if i % 3 == 1:
            intentar_click_turnstile(driver)

    if target_url:
        print(f"[INFO] Reintentando navegación a: {target_url}")
        driver.get(target_url)
        time.sleep(5)
        if not detectar_anti_bot(driver):
            print("[INFO] Anti-bot resuelto tras re-navegar.")
            return True

    print("[WARN] Anti-bot no se resolvió automáticamente.")
    return False


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
        resuelto = esperar_resolucion_anti_bot(driver, target_url=BEVSA_URL, max_wait=45)

        if not resuelto and detectar_anti_bot(driver):
            try:
                from update.download.bevsa_turnstile import solve_and_submit_turnstile, wait_after_turnstile_submit
                max_captcha_attempts = 3
                for attempt in range(1, max_captcha_attempts + 1):
                    print(f"[INFO] 2captcha intento {attempt}/{max_captcha_attempts}...")
                    if solve_and_submit_turnstile(driver, return_url_after_success=BEVSA_URL):
                        time.sleep(5)
                        cur = driver.current_url or ""
                        if "Disclaimer" in cur:
                            print("[INFO] 2captcha resolvió Turnstile → Disclaimer. Aceptando términos...")
                            aceptar_terminos(driver)
                            driver.get(BEVSA_URL)
                            time.sleep(5)
                            resuelto = True
                        elif wait_after_turnstile_submit(driver, timeout=35, url_contains="HistoricoDiario"):
                            resuelto = True
                        if resuelto:
                            print("[INFO] Turnstile resuelto con 2captcha.")
                            break
                    if attempt < max_captcha_attempts:
                        print(f"[WARN] 2captcha intento {attempt} falló, reintentando en 10s...")
                        time.sleep(10)
                        driver.get(BEVSA_URL)
                        time.sleep(5)
            except Exception as e:
                print(f"[DEBUG] 2captcha no usada: {e}")

        cur_after = driver.current_url or ""
        if "Disclaimer" in cur_after:
            print("[INFO] En Disclaimer.aspx. Aceptando términos...")
            aceptar_terminos(driver)
            driver.get(BEVSA_URL)
            time.sleep(5)
            resuelto = True

        if not resuelto and detectar_anti_bot(driver):
            if en_ci():
                raise RuntimeError(
                    "CI: BEVSA bloqueado por Cloudflare/Turnstile y no se pudo resolver automáticamente. "
                    "Resultado: NO se descargó el Excel (se mantiene el archivo anterior). "
                    "Revisar secret CAPTCHA_API_KEY / 2captcha y reintentar."
                )
            print("[WARN] Anti-bot persistente. Esperando 30s adicionales...")
            time.sleep(30)
            driver.get(BEVSA_URL)
            time.sleep(5)

    # Asegurar que estamos en la página correcta con datos cargados
    cur = driver.current_url or ""
    if "HistoricoDiario" not in cur:
        print(f"[INFO] URL actual no es HistoricoDiario ({cur}). Navegando...")
        driver.get(BEVSA_URL)
        time.sleep(5)
    print(f"[INFO] URL antes de exportar: {driver.current_url}")

    # Esperar a que la tabla de datos exista (señal de que la página cargó completa)
    try:
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "table, .GridView, [id*='Grid']"))
        )
        print("[INFO] Tabla/datos detectados en la página.")
    except Exception:
        print("[WARN] No se detectó tabla de datos, intentando Exportar de todas formas...")

    # Buscar y hacer clic en el botón Exportar (probar varios selectores; BEVSA puede cambiar el ID)
    print("[INFO] Buscando botón Exportar Excel...")
    btn_exportar = None
    last_error = None
    for by, selector in EXPORTAR_SELECTORS:
        try:
            wait_one = WebDriverWait(driver, 6)
            btn_exportar = wait_one.until(
                EC.element_to_be_clickable((by, selector))
            )
            if btn_exportar:
                sel_str = selector if isinstance(selector, str) else str(selector)[:60]
                print(f"[INFO] Botón Exportar encontrado: {by}=%s" % sel_str)
                break
        except Exception as e:
            last_error = e
            continue
    if not btn_exportar:
        raise RuntimeError(
            "No se encontró el botón Exportar (probados ID y alternativas). "
            "Último error: %s" % (last_error or "timeout")
        )
    try:
        driver.execute_script("arguments[0].scrollIntoView(true);", btn_exportar)
        time.sleep(0.5)
        archivos_antes = set(f for f in os.listdir(download_path) if f.endswith(('.xlsx', '.xls')))
        # Intentar click normal y JS click; BEVSA usa __doPostBack para exportar
        try:
            driver.execute_script("arguments[0].click();", btn_exportar)
            print("[INFO] Clic en Exportar (JS click), esperando descarga...")
        except Exception:
            btn_exportar.click()
            print("[INFO] Clic en Exportar (click directo), esperando descarga...")
    except Exception as e:
        raise RuntimeError(f"Error al hacer clic en Exportar: {e}")

    # Esperar a que aparezca el archivo Excel (buscar en download_path y en ~/Downloads)
    user_downloads = os.path.join(os.path.expanduser("~"), "Downloads")
    search_dirs = [download_path]
    if os.path.isdir(user_downloads) and os.path.abspath(user_downloads) != os.path.abspath(download_path):
        search_dirs.append(user_downloads)

    archivos_antes_extra = {}
    for d in search_dirs:
        archivos_antes_extra[d] = set(f for f in os.listdir(d) if f.endswith(('.xlsx', '.xls')))
    archivos_antes_extra[download_path] = archivos_antes

    tiempo_max = 45
    inicio = time.time()
    archivo_descargado = None
    archivo_dir = download_path
    while time.time() - inicio < tiempo_max:
        time.sleep(1)
        for d in search_dirs:
            try:
                ahora = set(f for f in os.listdir(d) if f.endswith(('.xlsx', '.xls')))
                nuevos = ahora - archivos_antes_extra[d]
                completos = [f for f in nuevos if not f.endswith('.crdownload') and not f.endswith('.tmp')]
                if completos:
                    archivo_descargado = completos[0]
                    archivo_dir = d
                    print(f"[INFO] Archivo detectado en: {d}/{archivo_descargado}")
                    break
            except Exception:
                pass
        if archivo_descargado:
            break
    if not archivo_descargado:
        # Fallback: intentar __doPostBack directo para el botón Exportar
        print("[WARN] No se detectó descarga. Intentando __doPostBack directo...")
        try:
            driver.execute_script("__doPostBack('ctl00$ContentPlaceHolder1$LinkButton2','');")
            print("[INFO] __doPostBack ejecutado, esperando 30s...")
            inicio2 = time.time()
            while time.time() - inicio2 < 30:
                time.sleep(1)
                for d in search_dirs:
                    try:
                        ahora = set(f for f in os.listdir(d) if f.endswith(('.xlsx', '.xls')))
                        nuevos = ahora - archivos_antes_extra[d]
                        completos = [f for f in nuevos if not f.endswith('.crdownload') and not f.endswith('.tmp')]
                        if completos:
                            archivo_descargado = completos[0]
                            archivo_dir = d
                            print(f"[INFO] Archivo detectado (postback) en: {d}/{archivo_descargado}")
                            break
                    except Exception:
                        pass
                if archivo_descargado:
                    break
        except Exception as e:
            print(f"[WARN] __doPostBack falló: {e}")

    if not archivo_descargado:
        # Último fallback: descargar con requests usando las cookies de Selenium
        print("[WARN] Descarga con Selenium falló. Intentando con requests...")
        try:
            import requests as req
            session = req.Session()
            for cookie in driver.get_cookies():
                session.cookies.set(cookie['name'], cookie['value'], domain=cookie.get('domain', ''))
            page_html = driver.page_source
            import re
            vs = re.search(r'id="__VIEWSTATE"\s+value="([^"]*)"', page_html)
            evval = re.search(r'id="__EVENTVALIDATION"\s+value="([^"]*)"', page_html)
            vsg = re.search(r'id="__VIEWSTATEGENERATOR"\s+value="([^"]*)"', page_html)
            data = {
                '__EVENTTARGET': 'ctl00$ContentPlaceHolder1$LinkButton2',
                '__EVENTARGUMENT': '',
            }
            if vs: data['__VIEWSTATE'] = vs.group(1)
            if evval: data['__EVENTVALIDATION'] = evval.group(1)
            if vsg: data['__VIEWSTATEGENERATOR'] = vsg.group(1)
            resp = session.post(BEVSA_URL, data=data, headers={
                'User-Agent': driver.execute_script("return navigator.userAgent;"),
                'Referer': BEVSA_URL,
            }, timeout=30)
            if resp.status_code == 200 and len(resp.content) > 500:
                dest_direct = os.path.join(download_path, "bevsa_export_direct.xlsx")
                with open(dest_direct, 'wb') as f:
                    f.write(resp.content)
                archivo_descargado = "bevsa_export_direct.xlsx"
                archivo_dir = download_path
                print(f"[INFO] Descargado con requests: {len(resp.content)} bytes")
            else:
                print(f"[WARN] Respuesta requests: status={resp.status_code}, size={len(resp.content)}")
        except Exception as e:
            print(f"[WARN] Descarga con requests falló: {e}")

    if not archivo_descargado:
        raise RuntimeError(f"Timeout: no se detectó archivo Excel descargado (probados 3 métodos)")

    origen = os.path.join(archivo_dir, archivo_descargado)
    destino = os.path.join(download_path, DEST_FILENAME)

    # El Excel descargado ya tiene formato correcto. Si tiene más de 60 filas, tomar últimas 60
    df = pd.read_excel(origen, engine='openpyxl')
    fecha_col = df.columns[0] if len(df.columns) > 0 else None
    if fecha_col and len(df) > ULTIMOS_N:
        df[fecha_col] = pd.to_datetime(df[fecha_col], errors='coerce')
        df = df.dropna(subset=[fecha_col])
        df = df.sort_values(fecha_col, ascending=False).head(ULTIMOS_N).sort_values(fecha_col, ascending=True)
    df.to_excel(destino, index=False, engine='openpyxl')
    try:
        max_fecha = None
        if fecha_col and not df.empty:
            _s = pd.to_datetime(df[fecha_col], errors="coerce").dropna()
            if len(_s):
                max_fecha = _s.max().date()
        hoy = datetime.now().date()
        print(f"[INFO] Temp BEVSA guardado. max_fecha={max_fecha} hoy={hoy} filas={len(df)}")
        if en_ci() and max_fecha and max_fecha < (hoy - timedelta(days=MAX_STALENESS_DAYS)):
            raise RuntimeError(
                f"CI: Descarga BEVSA produjo datos viejos (max_fecha={max_fecha}, hoy={hoy}). "
                "Esto indica que NO se está obteniendo el export actualizado."
            )
    except Exception:
        # Si esto falla, preferimos no frenar el flujo local; en CI el RuntimeError ya corta.
        if en_ci():
            raise
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

        except RuntimeError as e:
            logger.log_exception(e, "main()")
            raise
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
