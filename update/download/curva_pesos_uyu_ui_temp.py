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


def asegurar_directorio():
    """Crea el directorio de descarga si no existe y devuelve su ruta absoluta."""
    base_dir = os.getcwd()
    download_path = os.path.join(base_dir, DOWNLOAD_DIR)
    os.makedirs(download_path, exist_ok=True)
    return download_path


def configurar_driver():
    """
    Configura Chrome para scraping.
    Usa un perfil persistente para guardar cookies y evitar disclaimer en futuras ejecuciones.
    """
    chrome_options = Options()
    
    # Detectar entornos cloud (Railway, Azure, etc.)
    is_railway = os.getenv('RAILWAY_ENVIRONMENT') or os.getenv('RAILWAY')
    is_azure = os.getenv('WEBSITE_INSTANCE_ID') or os.getenv('AZURE_FUNCTIONS_ENVIRONMENT') or os.getenv('CONTAINER_NAME')
    is_cloud = is_railway or is_azure
    
    # Usar perfil persistente para guardar cookies (evita disclaimer repetido)
    # PERO NO en cloud (causa problemas de desconexión)
    if not is_cloud:
        base_dir = os.getcwd()
        user_data_dir = os.path.join(base_dir, ".chrome_profile_bevsa")
        os.makedirs(user_data_dir, exist_ok=True)
        chrome_options.add_argument(f"--user-data-dir={user_data_dir}")
    
    if is_cloud:
        chrome_options.add_argument("--headless=new")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument("--disable-software-rasterizer")
        chrome_options.add_argument("--disable-extensions")
        chrome_options.add_argument("--disable-setuid-sandbox")
        chrome_options.add_argument("--disable-web-security")
        chrome_options.add_argument("--disable-features=VizDisplayCompositor")
        chrome_options.add_argument("--remote-debugging-port=9222")
        chrome_options.add_argument("--remote-debugging-address=0.0.0.0")
        chrome_options.add_argument("--no-first-run")
        chrome_options.add_argument("--no-default-browser-check")
        chrome_options.add_argument("--disable-background-networking")
        chrome_options.add_argument("--disable-background-timer-throttling")
        chrome_options.add_argument("--disable-backgrounding-occluded-windows")
        chrome_options.add_argument("--disable-breakpad")
        chrome_options.add_argument("--disable-client-side-phishing-detection")
        chrome_options.add_argument("--disable-default-apps")
        chrome_options.add_argument("--disable-hang-monitor")
        chrome_options.add_argument("--disable-popup-blocking")
        chrome_options.add_argument("--disable-prompt-on-repost")
        chrome_options.add_argument("--disable-sync")
        chrome_options.add_argument("--disable-translate")
        chrome_options.add_argument("--metrics-recording-only")
        chrome_options.add_argument("--no-crash-upload")
        chrome_options.add_argument("--enable-features=NetworkService,NetworkServiceInProcess")
        chrome_options.add_argument("--force-color-profile=srgb")
        chrome_options.add_argument("--hide-scrollbars")
        chrome_options.add_argument("--mute-audio")
        chrome_options.add_argument("--use-mock-keychain")
        # NO usar user-data-dir en Railway (causa problemas)
        # chrome_options.add_argument(f"--user-data-dir={user_data_dir}")
        
        chrome_bin = os.getenv('CHROME_BIN')
        if not chrome_bin:
            possible_paths = [
                '/root/.nix-profile/bin/chromium',  # Railway/Nixpacks (prioridad)
                '/usr/bin/google-chrome',
                '/usr/bin/chromium-browser',
                '/usr/bin/chromium',
            ]
            for path in possible_paths:
                if os.path.exists(path):
                    chrome_bin = path
                    break
        
        if chrome_bin and os.path.exists(chrome_bin):
            chrome_options.binary_location = chrome_bin
            print(f"[INFO] Usando Chrome/Chromium en: {chrome_bin}")
        else:
            print(f"[WARNING] Chrome/Chromium no encontrado. CHROME_BIN={os.getenv('CHROME_BIN')}")
        
        chromedriver_path = os.getenv('CHROMEDRIVER_PATH')
        if not chromedriver_path:
            possible_paths = [
                '/root/.nix-profile/bin/chromedriver',  # Railway/Nixpacks (prioridad)
                '/usr/bin/chromedriver',
                '/usr/local/bin/chromedriver',
            ]
            for path in possible_paths:
                if os.path.exists(path):
                    chromedriver_path = path
                    break
        
        if chromedriver_path and os.path.exists(chromedriver_path):
            print(f"[INFO] Usando ChromeDriver en: {chromedriver_path}")
        else:
            print(f"[WARNING] ChromeDriver no encontrado. CHROMEDRIVER_PATH={os.getenv('CHROMEDRIVER_PATH')}")
        
        if chromedriver_path and os.path.exists(chromedriver_path):
            service = Service(chromedriver_path)
            driver = webdriver.Chrome(service=service, options=chrome_options)
        else:
            driver = webdriver.Chrome(options=chrome_options)
        
        # Esperar a que Chrome esté completamente inicializado
        time.sleep(2)
        
        # Verificar que el driver esté conectado
        try:
            driver.current_url
        except Exception as e:
            print(f"[WARN] Error al verificar conexión inicial: {e}")
            print("[INFO] Reintentando crear driver...")
            time.sleep(3)
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
    
    # Procesar valores numéricos
    # Los valores vienen con coma como separador decimal (2,5102)
    # Necesitamos convertirlos a float y luego dividir entre 100000
    print(f"[INFO] Procesando valores numéricos (convertir coma a punto y dividir entre 100000)...")
    
    for col in df.columns:
        if col != fecha_col:
            # Convertir valores con coma a numérico
            # Primero reemplazar coma por punto
            df[col] = df[col].astype(str).str.replace(',', '.', regex=False)
            # Convertir a numérico
            df[col] = pd.to_numeric(df[col], errors='coerce')
            # Dividir entre 100000
            df[col] = df[col] / 100000
    
    print("[OK] Fechas convertidas y valores procesados")
    print(f"[INFO] Primeros valores después de procesar:")
    print(df.head())
    
    return df


def guardar_excel(df, download_path):
    """Guarda el DataFrame como Excel temporal."""
    destino = os.path.join(download_path, DEST_FILENAME)
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
        df_nuevos = pd.read_excel(temp_path, engine='openpyxl')
        print(f"[OK] Archivo temporal leído: {len(df_nuevos)} registros")
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
        
        # Combinar ambos DataFrames
        df_combinado = pd.concat([df_historico, df_nuevos_normalizado], ignore_index=True)
        print(f"[INFO] Datos combinados: {len(df_combinado)} registros totales")
        
        # Eliminar duplicados basados en la columna FECHA (mantener datos nuevos)
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
            
            # Esperar anti-bot si es necesario
            logger.info("Verificando anti-bot/CAPTCHA...")
            if detectar_anti_bot(driver):
                logger.warn("Anti-bot detectado, esperando resolución...")
                esperar_resolucion_anti_bot(driver)
                logger.log_selenium_state(driver, "Después de anti-bot")
            
            # Extraer tabla
            logger.info("Extrayendo tabla de datos...")
            df = extraer_tabla(driver)
            logger.info(f"Tabla extraída: {len(df)} filas, {len(df.columns)} columnas")

            # Procesar fechas y valores
            logger.info("Procesando fechas y valores...")
            df = procesar_fechas_y_valores(df)

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
