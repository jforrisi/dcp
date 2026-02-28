"""
Script: curva_pesos_uyu_temp
-----------------------------
Extrae la tabla histórica de ITLUP (nominales) desde BEVSA y la guarda como Excel.
La tabla contiene la curva de pesos uruguayos nominales con diferentes plazos (1 mes a 10 años).
"""

import os
import sys
import time
import pandas as pd
from datetime import datetime, timedelta
from urllib.parse import quote
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

# URL de la página BEVSA (ITLUP = nominales)
BEVSA_URL = "https://web.bevsa.com.uy/CurvasVectorPrecios/CurvasIndices/Historico.aspx?I=ITLUP"
# Checkpoint Cloudflare/Turnstile: si llevamos returnUrl, al resolver el CAPTCHA redirige a la curva
CHECKPOINT_BASE = "https://web.bevsa.com.uy/Checkpoint.aspx"

# Carpeta destino: siempre update/historicos del proyecto (de ahí lee la base de datos)
DOWNLOAD_DIR = os.path.join(root_dir, "update", "historicos")
DEST_FILENAME = "curva_pesos_uyu_temp.xlsx"
HISTORICO_FILENAME = "curva_pesos_uyu.xlsx"

# Modo "Chrome existente": conectar a un Chrome que vos abras (sin automatización).
# Así resolvés el CAPTCHA en un navegador normal y el script usa esa sesión.
# Uso: BEVSA_USE_EXISTING_CHROME=1 python curva_pesos_uyu_temp.py
DEBUGGER_PORT = 9222


def en_ci():
    """True si corre en GitHub Actions u otro CI (headless); ahí no se puede resolver CAPTCHA."""
    if os.getenv("GITHUB_ACTIONS") == "true":
        return True
    if os.getenv("RAILWAY_ENVIRONMENT") or os.getenv("RAILWAY"):
        return True
    if os.getenv("AZURE_ENVIRONMENT") or os.getenv("AZURE") or os.getenv("WEBSITE_INSTANCE_ID"):
        return True
    return False


def normalizar_tasa_a_porcentaje(val, divisor_grande=10000):
    """
    Lleva tasas a porcentaje (rango 1-20%). Si ya está en [1, 20] no modifica.
    Evita que 7.45 pase a 0.0734 cuando la fuente mezcla escalas.
    """
    if pd.isna(val) or val == 0:
        return val
    if 1 <= val <= 20:
        return val
    if 0 < val < 1:
        return val * 100  # ya estaba sobre-dividido (ej. 0.0734 -> 7.34)
    if 20 < val <= 10000:
        return val / 100
    return val / divisor_grande


def asegurar_directorio():
    """Crea el directorio de descarga si no existe y devuelve su ruta absoluta."""
    os.makedirs(DOWNLOAD_DIR, exist_ok=True)
    return DOWNLOAD_DIR


def esta_en_checkpoint(driver):
    """Indica si la página actual es el Checkpoint de Cloudflare/Turnstile."""
    try:
        return "Checkpoint.aspx" in (driver.current_url or "")
    except Exception:
        return False


def checkpoint_con_return_url():
    """URL del Checkpoint con returnUrl apuntando a la página de la curva (para que al resolver CAPTCHA redirija ahí)."""
    return f"{CHECKPOINT_BASE}?returnUrl={quote(BEVSA_URL, safe='')}"


def asegurar_checkpoint_con_return_url(driver):
    """
    Si estamos en Checkpoint sin returnUrl, navega a Checkpoint?returnUrl=BEVSA_URL.
    Así, cuando el usuario resuelva el CAPTCHA, irá a la curva en lugar de a Default.aspx.
    """
    if not esta_en_checkpoint(driver):
        return
    try:
        url_actual = driver.current_url
        if "returnUrl=" in url_actual:
            return
        destino = checkpoint_con_return_url()
        print(f"[INFO] Ajustando Checkpoint con returnUrl para que al resolver CAPTCHA vaya a la curva...")
        driver.get(destino)
        time.sleep(2)
    except Exception as e:
        print(f"[WARN] No se pudo ajustar returnUrl en Checkpoint: {e}")


def configurar_driver():
    """Configura Chrome con undetected_chromedriver (local y CI) para evitar Cloudflare."""
    base_dir = os.getcwd()
    user_data_dir = os.path.join(base_dir, ".chrome_profile_bevsa")
    os.makedirs(user_data_dir, exist_ok=True)

    use_existing = os.getenv("BEVSA_USE_EXISTING_CHROME", "").strip().lower() in ("1", "true", "yes")
    if use_existing:
        try:
            opts = Options()
            opts.add_experimental_option("debuggerAddress", f"127.0.0.1:{DEBUGGER_PORT}")
            driver = webdriver.Chrome(options=opts)
            print("[INFO] Conectado a Chrome existente (modo sesión manual).")
            return driver
        except Exception as e:
            print(f"[ERROR] No se pudo conectar a Chrome en 127.0.0.1:{DEBUGGER_PORT}: {e}")
            raise

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
        print(f"[INFO] undetected_chromedriver OK (headless={is_cloud})")
        return driver
    except Exception as e:
        print(f"[WARN] undetected_chromedriver falló: {e}")

    # -- Fallback: Selenium estándar --
    print("[INFO] Usando Selenium estándar como fallback")
    fb = Options()
    fb.add_argument(f"--user-data-dir={user_data_dir}")
    fb.add_experimental_option("excludeSwitches", ["enable-automation"])
    fb.add_experimental_option("useAutomationExtension", False)
    fb.add_argument("--disable-blink-features=AutomationControlled")
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
    """
    Acepta los términos y condiciones:
    1. Marca el checkbox con id 'ContentPlaceHolder1_chkAcceptTerms'
    2. Espera a que el botón se habilite (ya no esté disabled)
    3. Hace clic en el botón 'ContentPlaceHolder1_btnContinue'
    """
    from selenium.common.exceptions import NoSuchWindowException, WebDriverException
    try:
        wait = WebDriverWait(driver, 10)
        
        # Verificar si estamos en la página de disclaimer
        try:
            current_url = driver.current_url
        except (NoSuchWindowException, WebDriverException) as e:
            print(f"[WARN] No se pudo obtener URL (Chrome puede haberse cerrado): {e}")
            return
        
        if "Disclaimer.aspx" in current_url:
            print("[INFO] Detectada página de términos y condiciones (Disclaimer)")
        else:
            # Verificar si hay redirección al disclaimer
            print(f"[INFO] URL actual: {current_url}")
            print("[INFO] Verificando si hay formulario de términos en la página actual...")
        
        # Buscar el checkbox por su ID específico
        print("[INFO] Buscando checkbox de términos (ContentPlaceHolder1_chkAcceptTerms)...")
        checkbox = wait.until(
            EC.presence_of_element_located((By.ID, "ContentPlaceHolder1_chkAcceptTerms"))
        )
        
        # Hacer scroll al checkbox para asegurar que sea visible
        driver.execute_script("arguments[0].scrollIntoView(true);", checkbox)
        time.sleep(0.5)
        
        # Marcar el checkbox si no está marcado
        if not checkbox.is_selected():
            checkbox.click()
            print("[INFO] Checkbox marcado")
            time.sleep(1)  # Esperar a que el botón se habilite
        else:
            print("[INFO] Checkbox ya estaba marcado")
        
        # Buscar el botón por su ID específico
        print("[INFO] Buscando botón aceptar (ContentPlaceHolder1_btnContinue)...")
        aceptar_button = wait.until(
            EC.presence_of_element_located((By.ID, "ContentPlaceHolder1_btnContinue"))
        )
        
        # Esperar a que el botón se habilite (ya no esté disabled)
        if aceptar_button.get_attribute("disabled"):
            print("[INFO] Botón está deshabilitado, esperando a que se habilite...")
            wait.until(lambda d: not d.find_element(By.ID, "ContentPlaceHolder1_btnContinue").get_attribute("disabled"))
            print("[INFO] Botón habilitado")
        
        # Hacer scroll al botón
        driver.execute_script("arguments[0].scrollIntoView(true);", aceptar_button)
        time.sleep(0.5)
        
        # Hacer clic en el botón
        aceptar_button.click()
        print("[INFO] Botón aceptar presionado")
        time.sleep(3)  # Esperar a que la página cargue después de aceptar
        
    except Exception as e:
        from selenium.common.exceptions import NoSuchWindowException, WebDriverException
        print(f"[WARN] No se encontró el formulario de términos (puede que ya esté aceptado o no aparezca): {e}")
        try:
            current_url = driver.current_url
            print(f"[INFO] URL actual: {current_url}")
        except (NoSuchWindowException, WebDriverException):
            print("[WARN] No se pudo obtener URL (Chrome puede haberse cerrado)")
        print("[INFO] Continuando...")


def esperar_resolucion_anti_bot(driver):
    """
    Espera automáticamente a que se resuelva el anti-bot/CAPTCHA.
    Espera hasta 60 segundos antes de continuar.
    Verifica periódicamente que Chrome sigue abierto.
    """
    print("\n" + "=" * 60)
    print("ANTI-BOT DETECTADO (Cloudflare/Turnstile)")
    print("=" * 60)
    print("[INFO] Resuelva el CAPTCHA en la ventana del navegador.")
    print("[INFO] Si al hacer clic sale 'La verificación falló', usá el MODO CHROME EXISTENTE:")
    print("       1. Cerrá este Chrome y ejecutá:  bevsa_abrir_chrome_para_script.bat")
    print("       2. En ese Chrome (normal) entrá a BEVSA y pasá el CAPTCHA.")
    print("       3. Ejecutá:  set BEVSA_USE_EXISTING_CHROME=1 && python curva_pesos_uyu_temp.py")
    print("=" * 60 + "\n")
    
    # Esperar en intervalos de 5 segundos, verificando que Chrome sigue abierto
    from selenium.common.exceptions import NoSuchWindowException, WebDriverException
    total_wait = 60
    waited = 0
    check_interval = 5
    
    while waited < total_wait:
        try:
            # Verificar que Chrome sigue abierto
            _ = driver.current_url
            time.sleep(check_interval)
            waited += check_interval
            if waited % 15 == 0:  # Log cada 15 segundos
                print(f"[INFO] Esperando... ({waited}/{total_wait} segundos)")
        except (NoSuchWindowException, WebDriverException) as e:
            print(f"[ERROR] Chrome se cerró durante la espera: {e}")
            raise RuntimeError("Chrome se cerró inesperadamente durante la espera de Cloudflare")
    
    print("[INFO] Continuando con la extracción de la tabla...")
    
    # Verificar una última vez que Chrome sigue abierto
    try:
        _ = driver.current_url
        time.sleep(2)  # Dar un momento para que la página termine de cargar
    except (NoSuchWindowException, WebDriverException) as e:
        print(f"[ERROR] Chrome se cerró justo después de la espera: {e}")
        raise RuntimeError("Chrome se cerró inesperadamente después de la espera de Cloudflare")


def detectar_anti_bot(driver):
    """
    Detecta si hay un anti-bot/CAPTCHA en la página (excluye Disclaimer.aspx y páginas de datos).
    Retorna True si detecta anti-bot, False si no.
    """
    try:
        from selenium.common.exceptions import NoSuchWindowException, WebDriverException
        from urllib.parse import urlparse
        try:
            url = (driver.current_url or "").lower()
        except (NoSuchWindowException, WebDriverException) as e:
            print(f"[WARN] Chrome se cerró durante detección de anti-bot: {e}")
            return False

        path = urlparse(url).path.lower()

        if "checkpoint" in path:
            print("[INFO] Posible anti-bot detectado: checkpoint URL")
            return True
        if "disclaimer.aspx" in path:
            return False
        if "historico.aspx" in path:
            return False

        try:
            page_source_lower = driver.page_source.lower()
            page_title_lower = driver.title.lower()
        except (NoSuchWindowException, WebDriverException) as e:
            print(f"[WARN] No se pudo obtener page_source/title: {e}")
            return False

        anti_bot_indicators = [
            "captcha",
            "verificación de seguridad",
            "security check",
        ]
        
        for indicator in anti_bot_indicators:
            if indicator in page_title_lower:
                print(f"[INFO] Posible anti-bot detectado: {indicator}")
                return True
        
        # Buscar por elementos comunes de Cloudflare
        try:
            driver.find_element(By.ID, "challenge-form")
            print("[INFO] Cloudflare challenge detectado")
            return True
        except:
            pass
        
        try:
            driver.find_element(By.CLASS_NAME, "cf-browser-verification")
            print("[INFO] Cloudflare verification detectado")
            return True
        except:
            pass
        
        return False
    except Exception as e:
        print(f"[WARN] Error al detectar anti-bot: {e}")
        return False


def extraer_tabla(driver):
    """
    Extrae la tabla histórica de ITLUP PAR desde la página usando Selenium directamente.
    Retorna un DataFrame de pandas con todas las columnas.
    
    Flujo:
    1. Intenta ir directamente a la URL de la tabla
    2. Si aparece disclaimer, lo acepta y luego navega a la tabla
    3. Extrae los datos celda por celda usando Selenium
    """
    # Si ya estamos en Checkpoint (p. ej. desde main), no hacer get(BEVSA_URL) para no re-disparar sin returnUrl
    if not esta_en_checkpoint(driver):
        print(f"[INFO] Accediendo a: {BEVSA_URL}")
        driver.get(BEVSA_URL)
        time.sleep(3)
    # Si nos redirigieron al Checkpoint Cloudflare, llevar returnUrl para que al resolver vaya a la curva
    if esta_en_checkpoint(driver):
        asegurar_checkpoint_con_return_url(driver)
        time.sleep(2)
    
    # Verificar si estamos en la página de disclaimer
    if "Disclaimer.aspx" in driver.current_url:
        print("[INFO] Detectada página de términos y condiciones")
        # Aceptar términos
        aceptar_terminos(driver)
        
        # Después de aceptar, navegar explícitamente a la URL de la tabla
        print(f"[INFO] Navegando a la página de datos: {BEVSA_URL}")
        driver.get(BEVSA_URL)
        time.sleep(3)
    else:
        # Verificar si hay formulario de términos en la página actual
        try:
            checkbox = driver.find_element(By.ID, "ContentPlaceHolder1_chkAcceptTerms")
            if checkbox:
                print("[INFO] Formulario de términos detectado en la página actual")
                aceptar_terminos(driver)
                # Navegar a la URL de la tabla después de aceptar
                print(f"[INFO] Navegando a la página de datos: {BEVSA_URL}")
                driver.get(BEVSA_URL)
                time.sleep(3)
        except:
            print("[INFO] No se encontró formulario de términos, continuando...")
    
    # Verificar si hay anti-bot
    if detectar_anti_bot(driver):
        try:
            esperar_resolucion_anti_bot(driver)
        except RuntimeError as e:
            print(f"[ERROR] Error durante la espera de Cloudflare: {e}")
            raise

    # Si seguimos en Checkpoint, no hacer get(BEVSA_URL) (re-dispararía el CAPTCHA sin returnUrl).
    # Esperar a que el usuario haya resuelto y la URL cambie a Historico, o ir a la curva si estamos en otra página.
    from selenium.common.exceptions import NoSuchWindowException, WebDriverException
    try:
        current_url = driver.current_url
        if esta_en_checkpoint(driver):
            # Asegurar returnUrl y esperar hasta 120 s a que redirija tras resolver el CAPTCHA
            asegurar_checkpoint_con_return_url(driver)
            print("[INFO] En Checkpoint: resuelva el CAPTCHA en el navegador; se esperará hasta 120 s la redirección a la curva...")
            wait_redirect = WebDriverWait(driver, 120)
            wait_redirect.until(lambda d: "Historico.aspx" in (d.current_url or ""))
            print("[INFO] Redirección a la página de la curva detectada")
            time.sleep(3)
        elif "Historico.aspx" not in current_url and "ITLUP" not in current_url:
            print(f"[WARN] No estamos en la página correcta. URL actual: {current_url}")
            print(f"[INFO] Navegando a: {BEVSA_URL}")
            driver.get(BEVSA_URL)
            time.sleep(3)
    except Exception as e:
        if "Message:" in str(e) and "timeout" in str(e).lower():
            print("[WARN] Timeout esperando redirección desde Checkpoint. Intentando navegar a la curva...")
            driver.get(BEVSA_URL)
            time.sleep(3)
        else:
            raise
    except (NoSuchWindowException, WebDriverException) as e:
        print(f"[ERROR] Chrome se cerró inesperadamente: {e}")
        raise RuntimeError(f"Chrome se cerró inesperadamente: {e}")
    
    # Esperar a que la tabla se cargue
    print("[INFO] Esperando a que la tabla se cargue...")
    wait = WebDriverWait(driver, 60)
    
    # Buscar la tabla por su ID (ITLUP = nominales)
    tabla_id = "ctl00_ContentPlaceHolder1_GridHistoricoITLUP_ctl00"
    try:
        tabla = wait.until(
            EC.presence_of_element_located((By.ID, tabla_id))
        )
    except Exception as e:
        print(f"[ERROR] No se pudo encontrar la tabla. URL actual: {driver.current_url}")
        print(f"[ERROR] Título de la página: {driver.title}")
        print(f"[INFO] Esperando 10 segundos adicionales e intentando nuevamente...")
        time.sleep(10)
        
        # Intentar nuevamente con más tiempo
        try:
            tabla = wait.until(
                EC.presence_of_element_located((By.ID, tabla_id))
            )
        except:
            raise Exception(f"No se pudo encontrar la tabla después de múltiples intentos. URL: {driver.current_url}")
    
    print("[INFO] Tabla encontrada, extrayendo datos...")
    
    # Hacer scroll vertical para cargar todas las filas
    print("[INFO] Haciendo scroll vertical para cargar todas las filas...")
    last_height = driver.execute_script("return arguments[0].scrollHeight || arguments[0].clientHeight;", tabla)
    scroll_attempts = 0
    max_scroll_attempts = 50
    
    while scroll_attempts < max_scroll_attempts:
        driver.execute_script("arguments[0].scrollTop = arguments[0].scrollHeight;", tabla)
        time.sleep(1)
        new_height = driver.execute_script("return arguments[0].scrollHeight || arguments[0].clientHeight;", tabla)
        if new_height == last_height:
            break
        last_height = new_height
        scroll_attempts += 1
        print(f"[INFO] Scroll vertical: intento {scroll_attempts}, altura actual: {new_height}")
    
    # Volver al inicio de la tabla
    driver.execute_script("arguments[0].scrollTop = 0;", tabla)
    time.sleep(1)
    
    # Hacer scroll horizontal para asegurar que todas las columnas estén cargadas
    print("[INFO] Haciendo scroll horizontal para cargar todas las columnas...")
    driver.execute_script("arguments[0].scrollLeft = arguments[0].scrollWidth;", tabla)
    time.sleep(3)  # Esperar más tiempo para que se carguen todas las columnas
    
    # Volver al inicio horizontal
    driver.execute_script("arguments[0].scrollLeft = 0;", tabla)
    time.sleep(1)
    
    # Extraer headers de la tabla
    print("[INFO] Extrayendo headers de la tabla...")
    try:
        # Buscar el thead o la primera fila con headers
        headers = []
        try:
            # Intentar encontrar el thead
            thead = tabla.find_element(By.TAG_NAME, "thead")
            header_rows = thead.find_elements(By.TAG_NAME, "tr")
            if header_rows:
                header_cells = header_rows[0].find_elements(By.TAG_NAME, "th")
                for cell in header_cells:
                    text = cell.text.strip()
                    if text:
                        headers.append(text)
        except:
            # Si no hay thead, buscar la primera fila
            first_row = tabla.find_element(By.TAG_NAME, "tr")
            header_cells = first_row.find_elements(By.TAG_NAME, "td")
            if not header_cells:
                header_cells = first_row.find_elements(By.TAG_NAME, "th")
            for cell in header_cells:
                text = cell.text.strip()
                if text:
                    headers.append(text)
        
        if not headers:
            # Último recurso: usar pd.read_html para obtener headers
            print("[INFO] No se pudieron extraer headers con Selenium, usando pd.read_html...")
            tabla_html = tabla.get_attribute('outerHTML')
            import io
            dfs = pd.read_html(io.StringIO(tabla_html))
            if dfs:
                df_temp = dfs[0]
                headers = list(df_temp.columns)
        
        print(f"[INFO] Headers encontrados: {headers}")
        print(f"[INFO] Total de headers: {len(headers)}")
        
        # Verificar que tenemos las columnas esperadas
        columnas_esperadas = ['FECHA', '1 MES', '2 MESES', '3 MESES', '6 MESES', '9 MESES', 
                             '1 AÑO', '2 AÑOS', '3 AÑOS', '4 AÑOS', '5 AÑOS', '6 AÑOS', 
                             '7 AÑOS', '8 AÑOS', '9 AÑOS', '10 AÑOS']
        
        # Normalizar headers (eliminar espacios extra, convertir a mayúsculas para comparación)
        headers_normalizados = [h.strip().upper() for h in headers]
        columnas_esperadas_normalizadas = [c.strip().upper() for c in columnas_esperadas]
        
        faltantes = []
        for col_esperada in columnas_esperadas_normalizadas:
            if col_esperada not in headers_normalizados:
                faltantes.append(col_esperada)
        
        if faltantes:
            print(f"[WARN] Faltan columnas: {faltantes}")
            print(f"[INFO] Intentando extraer con método alternativo...")
            
            # Intentar extraer usando pd.read_html con diferentes opciones
            tabla_html = tabla.get_attribute('outerHTML')
            import io
            # Intentar con diferentes parámetros
            for flavor in ['html5lib', 'lxml', 'bs4']:
                try:
                    dfs = pd.read_html(io.StringIO(tabla_html), flavor=flavor)
                    if dfs:
                        df_temp = dfs[0]
                        headers_alt = list(df_temp.columns)
                        headers_normalizados_alt = [h.strip().upper() for h in headers_alt]
                        faltantes_alt = [c for c in columnas_esperadas_normalizadas if c not in headers_normalizados_alt]
                        if len(faltantes_alt) < len(faltantes):
                            print(f"[INFO] Método {flavor} encontró más columnas")
                            headers = headers_alt
                            headers_normalizados = headers_normalizados_alt
                            faltantes = faltantes_alt
                            if not faltantes:
                                break
                except:
                    continue
        
        # Si aún faltan columnas, intentar extraer celda por celda
        if faltantes:
            print(f"[INFO] Extrayendo datos celda por celda para asegurar todas las columnas...")
            # Buscar todas las filas de datos
            tbody = tabla.find_element(By.TAG_NAME, "tbody")
            rows = tbody.find_elements(By.TAG_NAME, "tr")
            
            if rows:
                # Extraer headers de la primera fila si no los tenemos
                if not headers or len(headers) < len(columnas_esperadas):
                    first_row_cells = rows[0].find_elements(By.TAG_NAME, "td")
                    if first_row_cells:
                        headers = []
                        for cell in first_row_cells:
                            text = cell.text.strip()
                            if text:
                                headers.append(text)
                        print(f"[INFO] Headers extraídos de primera fila: {headers}")
                
                # Extraer datos de todas las filas
                data = []
                for row in rows:
                    cells = row.find_elements(By.TAG_NAME, "td")
                    row_data = []
                    for cell in cells:
                        text = cell.text.strip()
                        row_data.append(text)
                    if row_data:
                        data.append(row_data)
                
                # Asegurar que todas las filas tengan el mismo número de columnas
                max_cols = max(len(row) for row in data) if data else 0
                if max_cols > len(headers):
                    # Agregar headers faltantes
                    for i in range(len(headers), max_cols):
                        headers.append(f"Columna_{i+1}")
                
                # Crear DataFrame
                df = pd.DataFrame(data, columns=headers[:max_cols] if headers else None)
                print(f"[OK] Tabla extraída celda por celda: {len(df)} filas, {len(df.columns)} columnas")
            else:
                raise ValueError("No se encontraron filas de datos en la tabla")
        else:
            # Usar pd.read_html si tenemos todos los headers
            print("[INFO] Usando pd.read_html para extraer datos...")
            tabla_html = tabla.get_attribute('outerHTML')
            # pd.read_html necesita un objeto tipo archivo o StringIO para strings HTML
            import io
            dfs = pd.read_html(io.StringIO(tabla_html))
            if not dfs:
                raise ValueError("No se pudo extraer la tabla con pd.read_html")
            df = dfs[0]
            
            # Normalizar nombres de columnas
            df.columns = [col.strip() for col in df.columns]
            print(f"[OK] Tabla extraída: {len(df)} filas, {len(df.columns)} columnas")
        
        print(f"[INFO] Columnas finales: {list(df.columns)}")
        
        # Verificar que tenemos las columnas mínimas requeridas
        columnas_finales_normalizadas = [c.strip().upper() for c in df.columns]
        faltantes_final = [c for c in columnas_esperadas_normalizadas if c not in columnas_finales_normalizadas]
        
        if faltantes_final:
            print(f"[ERROR] Aún faltan columnas después de la extracción: {faltantes_final}")
            print(f"[INFO] Columnas encontradas: {columnas_finales_normalizadas}")
            raise ValueError(f"Faltan columnas requeridas: {faltantes_final}")
        
        # Normalizar tasas a porcentaje (rango 1-20): detectar escala en lugar de dividir siempre por 10000
        print("[INFO] Normalizando valores numéricos a porcentaje (rango 1-20)...")
        fecha_col = None
        for col in df.columns:
            if col.strip().upper() == 'FECHA':
                fecha_col = col
                break
        
        if not fecha_col:
            fecha_col = df.columns[0]  # Usar primera columna si no encontramos FECHA
        
        for col in df.columns:
            if col != fecha_col:
                df[col] = pd.to_numeric(df[col], errors='coerce').apply(
                    lambda x: normalizar_tasa_a_porcentaje(x, divisor_grande=10000)
                )
        
        print("[OK] Valores normalizados a porcentaje")
        return df
        
    except Exception as e:
        print(f"[ERROR] Error al extraer la tabla: {e}")
        import traceback
        traceback.print_exc()
        raise


def guardar_excel(df, download_path):
    """Guarda el DataFrame como Excel."""
    destino = os.path.join(download_path, DEST_FILENAME)
    
    # Guardar como Excel
    df.to_excel(destino, index=False, engine='openpyxl')
    print(f"[OK] Excel guardado como: {destino}")
    return destino


def actualizar_historico(download_path):
    """
    Actualiza el archivo histórico con los datos nuevos del archivo temporal.
    Hace un merge inteligente que preserva los datos históricos para columnas
    que no están en el archivo temporal.
    """
    historico_path = os.path.join(download_path, HISTORICO_FILENAME)
    temp_path = os.path.join(download_path, DEST_FILENAME)
    
    print("\n[INFO] Actualizando archivo histórico con merge inteligente...")
    
    # Leer archivo histórico si existe
    if os.path.exists(historico_path):
        try:
            df_historico = pd.read_excel(historico_path, engine='openpyxl')
            print(f"[OK] Archivo histórico leído: {len(df_historico)} registros")
        except Exception as e:
            print(f"[WARN] Error al leer archivo histórico: {e}")
            print("[INFO] Se creará un nuevo archivo histórico")
            df_historico = pd.DataFrame()
    else:
        print("[INFO] Archivo histórico no existe, se creará uno nuevo")
        df_historico = pd.DataFrame()
    
    # Leer archivo temporal con datos nuevos
    if not os.path.exists(temp_path):
        print(f"[ERROR] No se encontró el archivo temporal: {temp_path}")
        return
    
    try:
        df_nuevos = pd.read_excel(temp_path, engine='openpyxl')
        print(f"[OK] Archivo temporal leído: {len(df_nuevos)} registros")
    except Exception as e:
        print(f"[ERROR] Error al leer archivo temporal: {e}")
        return
    
    # Obtener el nombre de la columna de fecha (primera columna)
    fecha_col_nuevos = df_nuevos.columns[0]  # Primera columna es FECHA/fecha
    
    if df_historico.empty:
        # Si no hay histórico, usar solo los nuevos datos
        df_combinado = df_nuevos.copy()
        print("[INFO] No hay datos históricos, usando solo datos nuevos")
        fecha_col = fecha_col_nuevos
    else:
        # Obtener el nombre de la columna de fecha del histórico (primera columna)
        fecha_col_historico = df_historico.columns[0]
        
        # Normalizar nombres de columnas: usar el nombre del histórico para ambos
        # Esto maneja diferencias de mayúsculas/minúsculas
        df_nuevos_normalizado = df_nuevos.copy()
        df_nuevos_normalizado.rename(columns={fecha_col_nuevos: fecha_col_historico}, inplace=True)
        fecha_col = fecha_col_historico
        
        print(f"[INFO] Columna de fecha detectada: '{fecha_col}'")
        
        # Convertir fechas a formato comparable
        # El histórico ya tiene fechas en formato datetime
        # El temp puede tener fechas como texto DD/MM/YYYY o como datetime (si Excel las convirtió)
        try:
            # Convertir histórico
            df_historico[fecha_col] = pd.to_datetime(df_historico[fecha_col], errors='coerce')
            
            # Verificar tipo de dato del temp antes de convertir
            tipo_temp = df_nuevos_normalizado[fecha_col].dtype
            print(f"[INFO] Tipo de dato de fecha en temp: {tipo_temp}")
            print(f"[INFO] Primeras 3 fechas del temp (antes de convertir): {df_nuevos_normalizado[fecha_col].head(3).tolist()}")
            
            # Si es string/object, intentar con formato DD/MM/YYYY
            if df_nuevos_normalizado[fecha_col].dtype == 'object':
                print("[INFO] Fechas del temp son texto, convirtiendo con formato DD/MM/YYYY...")
                df_nuevos_normalizado[fecha_col] = pd.to_datetime(
                    df_nuevos_normalizado[fecha_col], 
                    format='%d/%m/%Y', 
                    errors='coerce'
                )
                # Si falla, intentar sin formato específico
                if df_nuevos_normalizado[fecha_col].isna().all():
                    print("[WARN] Formato DD/MM/YYYY falló, intentando conversión automática...")
                    df_nuevos_normalizado[fecha_col] = pd.to_datetime(df_nuevos_normalizado[fecha_col], errors='coerce')
            else:
                # Ya es datetime, solo asegurar que esté en formato correcto
                print("[INFO] Fechas del temp ya son datetime, convirtiendo directamente...")
                df_nuevos_normalizado[fecha_col] = pd.to_datetime(df_nuevos_normalizado[fecha_col], errors='coerce')
            
            print(f"[INFO] Primeras 3 fechas del temp (después de convertir): {df_nuevos_normalizado[fecha_col].head(3).tolist()}")
            print(f"[INFO] Última fecha del temp: {df_nuevos_normalizado[fecha_col].max()}")
            
        except Exception as e:
            print(f"[WARN] Error al convertir fechas: {e}")
            import traceback
            traceback.print_exc()
            # Intentar conversión automática como fallback
            df_historico[fecha_col] = pd.to_datetime(df_historico[fecha_col], errors='coerce')
            df_nuevos_normalizado[fecha_col] = pd.to_datetime(df_nuevos_normalizado[fecha_col], errors='coerce')
        
        # Eliminar filas con fechas nulas antes del merge
        filas_antes_hist = len(df_historico)
        filas_antes_nuevos = len(df_nuevos_normalizado)
        df_historico = df_historico.dropna(subset=[fecha_col])
        df_nuevos_normalizado = df_nuevos_normalizado.dropna(subset=[fecha_col])
        filas_despues_hist = len(df_historico)
        filas_despues_nuevos = len(df_nuevos_normalizado)
        
        if filas_antes_hist != filas_despues_hist:
            print(f"[WARN] Eliminadas {filas_antes_hist - filas_despues_hist} filas con fechas inválidas del histórico")
        if filas_antes_nuevos != filas_despues_nuevos:
            print(f"[WARN] Eliminadas {filas_antes_nuevos - filas_despues_nuevos} filas con fechas inválidas del temp")
        
        # Filtrar fechas futuras o corruptas del histórico
        # Usar la fecha máxima del temp como referencia (no debería haber fechas más recientes que las del temp)
        if len(df_nuevos_normalizado) > 0:
            fecha_max_temp = df_nuevos_normalizado[fecha_col].max()
            # Permitir fechas hasta 7 días después de la fecha máxima del temp (por si hay diferencias menores)
            fecha_max_aceptable = fecha_max_temp + timedelta(days=7)
            print(f"[INFO] Fecha máxima del temp: {fecha_max_temp}, fecha máxima aceptable en histórico: {fecha_max_aceptable}")
        else:
            # Si no hay temp, usar fecha actual + 30 días como límite
            fecha_max_aceptable = datetime.now() + timedelta(days=30)
        
        filas_antes_filtro = len(df_historico)
        df_historico = df_historico[df_historico[fecha_col] <= fecha_max_aceptable]
        filas_despues_filtro = len(df_historico)
        
        if filas_antes_filtro != filas_despues_filtro:
            print(f"[WARN] Eliminadas {filas_antes_filtro - filas_despues_filtro} filas con fechas futuras/corruptas del histórico (fechas > {fecha_max_aceptable.date()})")
        
        print(f"[INFO] Rango de fechas del histórico después de limpieza: {df_historico[fecha_col].min()} a {df_historico[fecha_col].max()}")
        print(f"[INFO] Rango de fechas del temp: {df_nuevos_normalizado[fecha_col].min()} a {df_nuevos_normalizado[fecha_col].max()}")
        
        # MERGE INTELIGENTE: combinar columnas preservando datos históricos
        print("[INFO] Realizando merge inteligente...")
        
        # Identificar todas las columnas únicas de ambos DataFrames
        columnas_historico = set(df_historico.columns)
        columnas_nuevos = set(df_nuevos_normalizado.columns)
        todas_las_columnas = columnas_historico.union(columnas_nuevos)
        
        print(f"[INFO] Columnas en histórico: {len(columnas_historico)}")
        print(f"[INFO] Columnas en nuevos: {len(columnas_nuevos)}")
        print(f"[INFO] Total de columnas únicas: {len(todas_las_columnas)}")
        
        # Hacer merge outer para incluir todas las fechas de ambos DataFrames
        # Usar sufijos para identificar de dónde vienen los datos
        df_merged = pd.merge(
            df_historico,
            df_nuevos_normalizado,
            on=fecha_col,
            how='outer',
            suffixes=('_hist', '_nuevo')
        )
        
        print(f"[INFO] Merge inicial: {len(df_merged)} registros")
        
        # Para cada columna, combinar valores: preferir nuevos si existen, sino mantener históricos
        df_combinado = pd.DataFrame()
        df_combinado[fecha_col] = df_merged[fecha_col]
        
        for col in todas_las_columnas:
            if col == fecha_col:
                continue
            
            col_hist = f"{col}_hist" if f"{col}_hist" in df_merged.columns else None
            col_nuevo = f"{col}_nuevo" if f"{col}_nuevo" in df_merged.columns else None
            
            if col_hist and col_nuevo:
                # Ambas columnas existen: usar nuevo si no es NaN, sino usar histórico
                df_combinado[col] = df_merged[col_nuevo].fillna(df_merged[col_hist])
            elif col_nuevo:
                # Solo existe en nuevos
                df_combinado[col] = df_merged[col_nuevo]
            elif col_hist:
                # Solo existe en histórico
                df_combinado[col] = df_merged[col_hist]
            else:
                # Columna no existe en ninguno (no debería pasar)
                df_combinado[col] = None
        
        # Eliminar filas con fechas nulas después del merge
        filas_antes_limpieza = len(df_combinado)
        df_combinado = df_combinado.dropna(subset=[fecha_col])
        filas_despues_limpieza = len(df_combinado)
        
        if filas_antes_limpieza != filas_despues_limpieza:
            print(f"[WARN] Eliminadas {filas_antes_limpieza - filas_despues_limpieza} filas con fechas nulas después del merge")
        
        # Ordenar por fecha ascendente
        df_combinado = df_combinado.sort_values(fecha_col, ascending=True).reset_index(drop=True)
        
        print(f"[OK] Merge inteligente completado: {len(df_combinado)} registros finales")
    
    # Guardar archivo histórico actualizado
    try:
        df_combinado.to_excel(historico_path, index=False, engine='openpyxl')
        print(f"[OK] Archivo histórico actualizado: {historico_path}")
        print(f"      Total de registros: {len(df_combinado)}")
        if len(df_combinado) > 0:
            fecha_min = df_combinado[fecha_col].min()
            fecha_max = df_combinado[fecha_col].max()
            print(f"      Rango: {fecha_min} a {fecha_max}")
    except Exception as e:
        print(f"[ERROR] Error al guardar archivo histórico: {e}")
        raise


def main():
    """Función principal con logging mejorado."""
    script_name = "curva_pesos_uyu_temp"
    
    with ScriptLogger(script_name) as logger:
        try:
            logger.info("=" * 80)
            logger.info("EXTRACCIÓN DE CURVA DE PESOS UYU - BEVSA")
            logger.info("=" * 80)

            download_path = asegurar_directorio()
            logger.info(f"Carpeta de destino: {download_path}")

            # Configurar driver con logging
            logger.info("Configurando Chrome/Chromium...")
            logger.debug(f"CHROME_BIN={os.getenv('CHROME_BIN')}")
            logger.debug(f"CHROMEDRIVER_PATH={os.getenv('CHROMEDRIVER_PATH')}")
            logger.debug(f"RAILWAY_ENVIRONMENT={os.getenv('RAILWAY_ENVIRONMENT')}")

            driver = configurar_driver()
            logger.info("Driver configurado exitosamente")
            
            # Navegar a la página
            logger.info(f"Navegando a: {BEVSA_URL}")
            driver.get(BEVSA_URL)
            
            # Esperar a que la página cargue completamente
            logger.info("Esperando a que la página cargue...")
            time.sleep(5)
            
            # Verificar que el driver sigue conectado
            try:
                current_url = driver.current_url
                logger.debug(f"URL después de navegar: {current_url}")
            except Exception as e:
                logger.error(f"Chrome se desconectó después de navegar: {e}")
                raise
            
            logger.log_selenium_state(driver, "Después de navegar")

            # Si estamos en Checkpoint Cloudflare, asegurar returnUrl para que al resolver vaya a la curva
            if esta_en_checkpoint(driver):
                asegurar_checkpoint_con_return_url(driver)
            
            # Aceptar términos si es necesario
            logger.info("Verificando términos y condiciones...")
            aceptar_terminos(driver)
            logger.log_selenium_state(driver, "Después de aceptar términos")
            
            # Resolución de Cloudflare Turnstile: automática (2captcha) o manual / skip en CI
            logger.info("Verificando anti-bot/CAPTCHA...")
            if detectar_anti_bot(driver):
                asegurar_checkpoint_con_return_url(driver)
                resuelto_auto = False
                try:
                    from update.download.bevsa_turnstile import solve_and_submit_turnstile, wait_after_turnstile_submit
                    max_captcha_attempts = 3
                    for attempt in range(1, max_captcha_attempts + 1):
                        logger.info("2captcha intento %d/%d..." % (attempt, max_captcha_attempts))
                        if solve_and_submit_turnstile(driver, return_url_after_success=BEVSA_URL):
                            time.sleep(5)
                            cur = driver.current_url or ""
                            if "Disclaimer" in cur:
                                logger.info("2captcha resolvió Turnstile → Disclaimer. Aceptando términos...")
                                aceptar_terminos(driver)
                                driver.get(BEVSA_URL)
                                time.sleep(5)
                                resuelto_auto = True
                            elif wait_after_turnstile_submit(driver, timeout=35, url_contains="Historico"):
                                resuelto_auto = True
                            if resuelto_auto:
                                logger.info("Turnstile resuelto automáticamente (2captcha).")
                                break
                        if attempt < max_captcha_attempts:
                            logger.warn("2captcha intento %d falló, reintentando en 10s..." % attempt)
                            time.sleep(10)
                            driver.get(BEVSA_URL)
                            time.sleep(5)
                except Exception as e:
                    logger.debug("Resolución automática no usada: %s" % e)

                cur_after = driver.current_url or ""
                if not resuelto_auto and "Disclaimer" in cur_after:
                    logger.info("Post-2captcha: en Disclaimer. Aceptando términos...")
                    aceptar_terminos(driver)
                    driver.get(BEVSA_URL)
                    time.sleep(5)
                    resuelto_auto = True

                if not resuelto_auto:
                    if en_ci():
                        raise RuntimeError(
                            "CI: BEVSA bloqueado por Cloudflare/Turnstile y no se pudo resolver automáticamente. "
                            "Resultado: NO se actualizó la curva (se mantiene el archivo anterior). "
                            "Revisar secret CAPTCHA_API_KEY / 2captcha y reintentar."
                        )
                    logger.warn("Anti-bot detectado, esperando resolución manual...")
                    esperar_resolucion_anti_bot(driver)
                logger.log_selenium_state(driver, "Después de anti-bot")
            
            # Extraer tabla
            logger.info("Extrayendo tabla de datos...")
            df = extraer_tabla(driver)
            logger.info(f"Tabla extraída: {len(df)} filas, {len(df.columns)} columnas")

            # Mostrar primeros y últimos datos
            logger.info("Primeros datos:")
            logger.debug(f"\n{df.head()}")
            logger.info("Últimos datos:")
            logger.debug(f"\n{df.tail()}")

            # Guardar como Excel temporal
            logger.info("Guardando Excel...")
            destino = guardar_excel(df, download_path)
            logger.info(f"Excel guardado: {destino}")

            # Actualizar archivo histórico
            logger.info("Actualizando archivo histórico...")
            actualizar_historico(download_path)
            logger.info("Archivo histórico actualizado")
        
            logger.info("=" * 80)
            logger.info("PROCESO COMPLETADO EXITOSAMENTE")
            logger.info("=" * 80)

        except Exception as e:
            logger.log_exception(e, "main()")
            if 'driver' in locals():
                logger.log_selenium_state(driver, "Estado al momento del error")
            raise
        finally:
            if 'driver' in locals():
                try:
                    logger.info("Cerrando navegador...")
                    driver.quit()
                    logger.info("Navegador cerrado")
                except Exception as e:
                    logger.warn(f"Error al cerrar navegador: {e}")


if __name__ == "__main__":
    main()
