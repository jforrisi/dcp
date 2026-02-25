"""
Script: curva_pesos_uyu_ui_temp
-------------------------------
Extrae la tabla histórica de CUI desde BEVSA y actualiza curva_pesos_uyu_ui.xlsx.
Solo actualiza el Excel, no inserta en base de datos.
"""

import os
import sys
import time
import pandas as pd
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

# URL de la página BEVSA para CUI
BEVSA_URL = "https://web.bevsa.com.uy/CurvasVectorPrecios/CurvasIndices/Historico.aspx?I=CUI"

# Carpeta y nombre de archivo destino
DOWNLOAD_DIR = "update/historicos"
DEST_FILENAME = "curva_pesos_uyu_ui_temp.xlsx"
HISTORICO_FILENAME = "curva_pesos_uyu_ui.xlsx"


def en_ci():
    """True si corre en GitHub Actions u otro CI (headless); ahí no se puede resolver CAPTCHA."""
    if os.getenv("GITHUB_ACTIONS") == "true":
        return True
    if os.getenv("RAILWAY_ENVIRONMENT") or os.getenv("RAILWAY"):
        return True
    if os.getenv("AZURE_ENVIRONMENT") or os.getenv("AZURE") or os.getenv("WEBSITE_INSTANCE_ID"):
        return True
    return False


def valor_5_digitos_div_10000(val):
    """
    Normaliza un valor de tasa: siempre 5 dígitos (relleno a la derecha con ceros),
    luego se divide por 10000. Ej: 314 -> 31400 -> 3.14; 25102 -> 2.5102.
    """
    if pd.isna(val):
        return float("nan")
    s = str(val).replace(",", "").replace(".", "").strip()
    if not s or not s.lstrip("-").isdigit():
        return float("nan")
    s = s.lstrip("-")
    if len(s) > 5:
        s = s[:5]
    s = s.ljust(5, "0")
    return int(s) / 10000


def normalizar_tasa_a_porcentaje(val, divisor_grande=100000):
    """
    Lleva tasas a porcentaje (rango 1-20%). Si ya está en [1, 20] no modifica.
    CUI puede venir en escala 100000, por eso divisor_grande por defecto 100000.
    """
    if pd.isna(val) or val == 0:
        return val
    if 1 <= val <= 20:
        return val
    if 0 < val < 1:
        return val * 1000
    if 20 < val <= 10000:
        return val / 100
    return val / divisor_grande


def _get_proyecto_root():
    """Raíz del proyecto: subir desde update/download hasta la raíz."""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    # script_dir = .../update/download -> subir 2 niveles = proyecto
    return os.path.dirname(os.path.dirname(script_dir))


def asegurar_directorio():
    """Crea el directorio de descarga si no existe y devuelve su ruta absoluta.
    Usa la ruta del script para que los archivos vayan siempre al proyecto (update/historicos)."""
    base_dir = _get_proyecto_root()
    download_path = os.path.join(base_dir, DOWNLOAD_DIR)
    os.makedirs(download_path, exist_ok=True)
    return download_path


def configurar_driver():
    """Configura Chrome con undetected_chromedriver (local y CI) para evitar Cloudflare."""
    base_dir = _get_proyecto_root()
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
    2. Espera a que el botón se habilite
    3. Hace clic en el botón 'ContentPlaceHolder1_btnContinue'
    """
    try:
        wait = WebDriverWait(driver, 10)
        
        if "Disclaimer.aspx" in driver.current_url:
            print("[INFO] Detectada página de términos y condiciones (Disclaimer)")
        
        print("[INFO] Buscando checkbox de términos (ContentPlaceHolder1_chkAcceptTerms)...")
        checkbox = wait.until(
            EC.presence_of_element_located((By.ID, "ContentPlaceHolder1_chkAcceptTerms"))
        )
        
        driver.execute_script("arguments[0].scrollIntoView(true);", checkbox)
        time.sleep(0.5)
        
        if not checkbox.is_selected():
            checkbox.click()
            print("[INFO] Checkbox marcado")
            time.sleep(1)
        else:
            print("[INFO] Checkbox ya estaba marcado")
        
        print("[INFO] Buscando botón aceptar (ContentPlaceHolder1_btnContinue)...")
        aceptar_button = wait.until(
            EC.presence_of_element_located((By.ID, "ContentPlaceHolder1_btnContinue"))
        )
        
        if aceptar_button.get_attribute("disabled"):
            print("[INFO] Botón está deshabilitado, esperando a que se habilite...")
            wait.until(lambda d: not d.find_element(By.ID, "ContentPlaceHolder1_btnContinue").get_attribute("disabled"))
            print("[INFO] Botón habilitado")
        
        driver.execute_script("arguments[0].scrollIntoView(true);", aceptar_button)
        time.sleep(0.5)
        aceptar_button.click()
        print("[INFO] Botón aceptar presionado")
        time.sleep(3)
        
    except Exception as e:
        print(f"[WARN] No se encontró el formulario de términos (puede que ya esté aceptado): {e}")
        print(f"[INFO] URL actual: {driver.current_url}")
        print("[INFO] Continuando...")


def esperar_resolucion_anti_bot(driver):
    """
    Espera automáticamente a que se resuelva el anti-bot/CAPTCHA.
    Espera hasta 60 segundos antes de continuar.
    """
    print("\n" + "=" * 60)
    print("ANTI-BOT DETECTADO")
    print("=" * 60)
    print("[INFO] Esperando automáticamente hasta 60 segundos para que se resuelva...")
    print("[INFO] Si el anti-bot persiste, el script continuará de todas formas.")
    print("=" * 60 + "\n")
    
    time.sleep(60)
    print("[INFO] Continuando con la extracción de la tabla...")
    time.sleep(2)


def detectar_anti_bot(driver):
    """
    Detecta si hay un anti-bot/CAPTCHA en la página.
    Retorna True si detecta anti-bot, False si no.
    """
    try:
        anti_bot_indicators = [
            "captcha", "cloudflare", "challenge", "verification",
            "bot detection", "security check", "hcaptcha", "recaptcha", "turnstile"
        ]
        
        page_source_lower = driver.page_source.lower()
        page_title_lower = driver.title.lower()
        
        for indicator in anti_bot_indicators:
            if indicator in page_source_lower or indicator in page_title_lower:
                print(f"[INFO] Posible anti-bot detectado: {indicator}")
                return True
        
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
    Extrae la tabla histórica de CUI desde la página.
    Retorna un DataFrame de pandas.
    """
    print(f"[INFO] Accediendo a: {BEVSA_URL}")
    driver.get(BEVSA_URL)
    time.sleep(3)
    
    # Verificar si estamos en la página de disclaimer
    if "Disclaimer.aspx" in driver.current_url:
        print("[INFO] Detectada página de términos y condiciones")
        aceptar_terminos(driver)
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
                print(f"[INFO] Navegando a la página de datos: {BEVSA_URL}")
                driver.get(BEVSA_URL)
                time.sleep(3)
        except:
            print("[INFO] No se encontró formulario de términos, continuando...")
    
    # Verificar si hay anti-bot
    if detectar_anti_bot(driver):
        esperar_resolucion_anti_bot(driver)
    
    # Verificar que estamos en la página correcta
    if "Historico.aspx" not in driver.current_url and "CUI" not in driver.current_url:
        print(f"[WARN] No estamos en la página correcta. URL actual: {driver.current_url}")
        print(f"[INFO] Navegando explícitamente a: {BEVSA_URL}")
        driver.get(BEVSA_URL)
        time.sleep(3)
    
    # Esperar a que la tabla se cargue
    print("[INFO] Esperando a que la tabla se cargue...")
    wait = WebDriverWait(driver, 60)
    
    # Buscar la tabla por su ID (confirmado del HTML proporcionado)
    tabla_id = "ctl00_ContentPlaceHolder1_GridHistoricoCUI_ctl00"
    
    try:
        tabla = wait.until(
            EC.presence_of_element_located((By.ID, tabla_id))
        )
    except Exception as e:
        print(f"[ERROR] No se pudo encontrar la tabla. URL actual: {driver.current_url}")
        print(f"[ERROR] Título de la página: {driver.title}")
        print(f"[INFO] Esperando 10 segundos adicionales e intentando nuevamente...")
        time.sleep(10)
        
        try:
            tabla = wait.until(
                EC.presence_of_element_located((By.ID, tabla_id))
            )
        except:
            raise Exception(f"No se pudo encontrar la tabla después de múltiples intentos. URL: {driver.current_url}")
    
    print("[INFO] Tabla encontrada, extrayendo datos...")
    
    # Hacer scroll horizontal para asegurar que todas las columnas estén cargadas
    print("[INFO] Haciendo scroll horizontal para cargar todas las columnas...")
    driver.execute_script("arguments[0].scrollLeft = arguments[0].scrollWidth;", tabla)
    time.sleep(2)
    driver.execute_script("arguments[0].scrollLeft = 0;", tabla)
    time.sleep(1)
    
    # Extraer el HTML completo de la tabla
    tabla_html = tabla.get_attribute('outerHTML')
    page_source = driver.page_source
    
    # Leer la tabla HTML con pandas
    try:
        import io
        dfs = pd.read_html(io.StringIO(tabla_html))
        if not dfs:
            print("[INFO] Intentando extraer desde el HTML completo de la página...")
            dfs = pd.read_html(io.StringIO(page_source))
        
        if not dfs:
            raise ValueError("No se pudo extraer ninguna tabla del HTML")
        
        df = dfs[0]
        print(f"[OK] Tabla extraída: {len(df)} filas, {len(df.columns)} columnas")
        print(f"[INFO] Columnas encontradas: {list(df.columns)}")
        
        # Verificar columnas mínimas esperadas
        columnas_esperadas_min = 15
        if len(df.columns) < columnas_esperadas_min:
            print(f"[WARN] Se encontraron solo {len(df.columns)} columnas, se esperaban al menos {columnas_esperadas_min}")
            print("[INFO] Intentando esperar más tiempo y recargar la tabla...")
            time.sleep(5)
            tabla_html = tabla.get_attribute('outerHTML')
            import io
            dfs = pd.read_html(io.StringIO(tabla_html))
            if dfs:
                df = dfs[0]
                print(f"[INFO] Segunda extracción: {len(df)} filas, {len(df.columns)} columnas")
        
        # Eliminar columna "ÍNDICE" si existe (última columna)
        if 'ÍNDICE' in df.columns:
            df = df.drop(columns=['ÍNDICE'])
            print("[INFO] Columna 'ÍNDICE' eliminada")
        
        # Eliminar columnas vacías (que tienen &nbsp;)
        df = df.loc[:, ~df.columns.str.contains('Unnamed', case=False)]
        # También eliminar columnas que sean completamente NaN
        df = df.dropna(axis=1, how='all')
        
        print(f"[OK] Tabla procesada: {len(df)} filas, {len(df.columns)} columnas")
        print(f"[INFO] Columnas finales: {list(df.columns)}")
        
        return df
    except Exception as e:
        print(f"[ERROR] Error al parsear la tabla HTML: {e}")
        raise


def procesar_fechas_y_valores(df):
    """
    Procesa el DataFrame:
    - Convierte fechas de formato DD/MM/YYYY a datetime
    - Convierte valores de formato con coma (2,5102) a numérico
    - Divide valores numéricos entre 100000 (como en curva_pesos_uyu_ui.xlsx)
    """
    fecha_col = df.columns[0]
    
    # Convertir fechas de formato DD/MM/YYYY a datetime
    print(f"[INFO] Convirtiendo fechas de formato DD/MM/YYYY a datetime...")
    df[fecha_col] = pd.to_datetime(df[fecha_col], format='%d/%m/%Y', errors='coerce')
    
    fechas_nulas = df[fecha_col].isna().sum()
    if fechas_nulas > 0:
        print(f"[WARN] {fechas_nulas} fechas no se pudieron convertir")
        print(df[df[fecha_col].isna()].head())
    
    print(f"[OK] Primeros valores de fecha (después):")
    print(df[fecha_col].head())
    
    # Procesar valores numéricos: siempre 5 dígitos (relleno a la derecha con ceros), luego / 10000
    print(f"[INFO] Procesando valores numéricos (5 dígitos, relleno a la derecha con ceros, dividir por 10000)...")
    columnas_valor = [c for c in df.columns if c != fecha_col]
    for col in columnas_valor:
        df[col] = df[col].apply(valor_5_digitos_div_10000)

    print("[OK] Fechas convertidas y valores normalizados (5 dígitos / 10000)")
    print(f"[INFO] Primeros valores después de procesar:")
    print(df.head())
    
    return df


def guardar_excel(df, download_path, df_crudo=None):
    """
    Guarda el DataFrame como Excel temporal.
    Si df_crudo está definido, Hoja 1 = datos procesados, Hoja 2 = datos tal cual del scrape.
    """
    destino = os.path.join(download_path, DEST_FILENAME)
    if df_crudo is not None:
        with pd.ExcelWriter(destino, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='Procesado', index=False)
            df_crudo.to_excel(writer, sheet_name='Scrap crudo', index=False)
        print(f"[OK] Excel guardado como: {destino} (Hoja 1: Procesado, Hoja 2: Scrap crudo)")
    else:
        df.to_excel(destino, index=False, engine='openpyxl')
        print(f"[OK] Excel guardado como: {destino}")
    return destino


def actualizar_historico(download_path):
    """
    Actualiza curva_pesos_uyu_ui.xlsx con los datos nuevos.
    Combina ambos archivos eliminando duplicados basados en la columna FECHA.
    """
    historico_path = os.path.join(download_path, HISTORICO_FILENAME)
    temp_path = os.path.join(download_path, DEST_FILENAME)
    
    print("\n[INFO] Actualizando archivo histórico...")
    
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
        # Leer explícitamente la hoja "Procesado" para que coincida con lo que se guardó (evitar diferencias con el histórico)
        df_nuevos = pd.read_excel(temp_path, sheet_name='Procesado', engine='openpyxl')
        print(f"[OK] Archivo temporal leído (hoja Procesado): {len(df_nuevos)} registros")
    except Exception as e:
        print(f"[ERROR] Error al leer archivo temporal: {e}")
        return
    
    # Obtener el nombre de la columna de fecha (primera columna)
    fecha_col_nuevos = df_nuevos.columns[0]
    
    if df_historico.empty:
        df_combinado = df_nuevos.copy()
        print("[INFO] No hay datos históricos, usando solo datos nuevos")
    else:
        fecha_col_historico = df_historico.columns[0]
        df_nuevos_normalizado = df_nuevos.copy()
        df_nuevos_normalizado.rename(columns={fecha_col_nuevos: fecha_col_historico}, inplace=True)
        fecha_col = fecha_col_historico
        
        print(f"[INFO] Columna de fecha detectada: '{fecha_col}'")
        
        # Convertir fechas a formato comparable si es necesario
        try:
            df_historico[fecha_col] = pd.to_datetime(df_historico[fecha_col], errors='coerce')
            df_nuevos_normalizado[fecha_col] = pd.to_datetime(df_nuevos_normalizado[fecha_col], errors='coerce')
        except:
            pass
        
        # Combinar: NUEVOS primero para que al eliminar duplicados (keep='first') queden los del scrape
        df_combinado = pd.concat([df_nuevos_normalizado, df_historico], ignore_index=True)
        print(f"[INFO] Datos combinados: {len(df_combinado)} registros totales")
        
        # Eliminar duplicados por FECHA (mantener datos nuevos = primera aparición tras ordenar desc)
        registros_antes = len(df_combinado)
        df_combinado = df_combinado.sort_values(fecha_col, ascending=False)
        df_combinado = df_combinado.drop_duplicates(subset=[fecha_col], keep='first')
        registros_despues = len(df_combinado)
        duplicados_eliminados = registros_antes - registros_despues
        
        if duplicados_eliminados > 0:
            print(f"[INFO] Se eliminaron {duplicados_eliminados} fechas duplicadas (se mantuvieron los datos nuevos)")
        
        # Ordenar por fecha ascendente
        df_combinado = df_combinado.sort_values(fecha_col, ascending=True).reset_index(drop=True)
    
    # Guardar archivo histórico actualizado
    try:
        df_combinado.to_excel(historico_path, index=False, engine='openpyxl')
        print(f"[OK] Archivo histórico actualizado: {historico_path}")
        print(f"      Total de registros: {len(df_combinado)}")
        if len(df_combinado) > 0:
            fecha_col = df_combinado.columns[0]
            fecha_min = df_combinado[fecha_col].min()
            fecha_max = df_combinado[fecha_col].max()
            print(f"      Rango: {fecha_min} a {fecha_max}")
    except Exception as e:
        print(f"[ERROR] Error al guardar archivo histórico: {e}")
        raise


def main():
    """Función principal con logging mejorado."""
    script_name = "curva_pesos_uyu_ui_temp"
    
    with ScriptLogger(script_name) as logger:
        try:
            logger.info("=" * 80)
            logger.info("ACTUALIZACIÓN DE CURVA_PESOS_UYU_UI.XLSX - BEVSA (CUI)")
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
            from selenium.common.exceptions import NoSuchWindowException, WebDriverException
            try:
                current_url = driver.current_url
                logger.debug(f"URL después de navegar: {current_url}")
            except (NoSuchWindowException, WebDriverException) as e:
                logger.error(f"Chrome se desconectó después de navegar: {e}")
                raise RuntimeError(f"Chrome se cerró inesperadamente después de navegar: {e}")
            except Exception as e:
                logger.error(f"Error al obtener URL después de navegar: {e}")
                raise
            
            logger.log_selenium_state(driver, "Después de navegar")
            
            # Aceptar términos si es necesario
            logger.info("Verificando términos y condiciones...")
            aceptar_terminos(driver)
            logger.log_selenium_state(driver, "Después de aceptar términos")
            
            # Resolución de Cloudflare Turnstile: automática (2captcha) o manual / skip en CI
            logger.info("Verificando anti-bot/CAPTCHA...")
            if detectar_anti_bot(driver):
                resuelto_auto = False
                try:
                    from update.download.bevsa_turnstile import solve_and_submit_turnstile, wait_after_turnstile_submit
                    if solve_and_submit_turnstile(driver, return_url_after_success=BEVSA_URL):
                        time.sleep(3)
                        if wait_after_turnstile_submit(driver, timeout=35, url_contains="Historico"):
                            resuelto_auto = True
                            logger.info("Turnstile resuelto automáticamente (2captcha).")
                except Exception as e:
                    logger.debug("Resolución automática no usada: %s" % e)
                if not resuelto_auto:
                    if en_ci():
                        raise RuntimeError(
                            "CI: BEVSA bloqueado por Cloudflare/Turnstile y no se pudo resolver automáticamente. "
                            "Resultado: NO se actualizó la curva CUI (se mantiene el archivo anterior). "
                            "Revisar secret CAPTCHA_API_KEY / 2captcha y reintentar."
                        )
                    logger.warn("Anti-bot detectado, esperando resolución manual...")
                    esperar_resolucion_anti_bot(driver)
                logger.log_selenium_state(driver, "Después de anti-bot")
            
            # Extraer tabla
            logger.info("Extrayendo tabla de datos...")
            df = extraer_tabla(driver)
            logger.info(f"Tabla extraída: {len(df)} filas, {len(df.columns)} columnas")
            df_crudo = df.copy()

            # Procesar fechas y valores
            logger.info("Procesando fechas y valores...")
            df = procesar_fechas_y_valores(df)

            # Mostrar primeros y últimos datos
            logger.info("Primeros datos:")
            logger.debug(f"\n{df.head()}")
            logger.info("Últimos datos:")
            logger.debug(f"\n{df.tail()}")

            # Guardar como Excel temporal (Hoja 1: procesado, Hoja 2: scrap crudo)
            logger.info("Guardando Excel...")
            destino = guardar_excel(df, download_path, df_crudo=df_crudo)
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
    if len(sys.argv) > 1 and sys.argv[1] == "--solo-actualizar":
        download_path = asegurar_directorio()
        print(f"[INFO] Ejecutando solo actualizar_historico en: {download_path}")
        actualizar_historico(download_path)
        print("[OK] Listo.")
    else:
        main()
