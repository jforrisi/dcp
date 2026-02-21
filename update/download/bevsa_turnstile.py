"""
Resolución automática de Cloudflare Turnstile (BEVSA) vía 2captcha.
Uso: definir env 2CAPTCHA_API_KEY; los scripts de BEVSA intentarán resolver el CAPTCHA solos.
"""

import os
import time
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


def _get_api_key():
    return (os.getenv("2CAPTCHA_API_KEY") or os.getenv("CAPTCHA_2CAPTCHA_API_KEY") or "").strip()


def get_turnstile_sitekey(driver, timeout=15):
    """
    Obtiene el data-sitekey del widget Turnstile en la página.
    Retorna None si no hay widget o no tiene sitekey.
    """
    import re
    # 1) Elemento con data-sitekey
    try:
        wait = WebDriverWait(driver, min(timeout, 5))
        el = wait.until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "[data-sitekey]"))
        )
        sitekey = el.get_attribute("data-sitekey")
        if sitekey:
            return sitekey.strip()
    except Exception:
        pass
    # 2) Iframe de Turnstile (URL puede llevar k= o sitekey=)
    try:
        iframes = driver.find_elements(By.CSS_SELECTOR, "iframe[src*='turnstile'], iframe[src*='challenges.cloudflare.com']")
        for ifr in iframes:
            src = ifr.get_attribute("src") or ""
            for pat in [r"[?&]k=([^&]+)", r"[?&]sitekey=([^&]+)"]:
                m = re.search(pat, src)
                if m:
                    return m.group(1).strip()
    except Exception:
        pass
    # 3) Buscar en el HTML (widget a veces se inyecta por JS con sitekey en script)
    try:
        html = driver.page_source or ""
        m = re.search(r'["\']?sitekey["\']?\s*[:=]\s*["\']([^"\']+)["\']', html, re.I)
        if m:
            return m.group(1).strip()
        m = re.search(r'turnstile\.render\s*\([^,]+,\s*\{[^}]*sitekey\s*:\s*["\']([^"\']+)["\']', html, re.I | re.DOTALL)
        if m:
            return m.group(1).strip()
    except Exception:
        pass
    return None


def solve_and_submit_turnstile(driver, return_url_after_success=None):
    """
    Resuelve el Turnstile de BEVSA con 2captcha e inyecta el token.
    BEVSA valida con fetch a /CaptchaValidate.ashx y redirige con returnUrl.

    Args:
        driver: WebDriver de Selenium.
        return_url_after_success: URL a la que debe ir tras validar (opcional; si no, se usa returnUrl de la página).

    Returns:
        True si se resolvió y se envió el token (luego hay que esperar la redirección).
        False si no hay API key, no hay sitekey, o falló el solver.
    """
    api_key = _get_api_key()
    if not api_key:
        return False

    try:
        from twocaptcha import TwoCaptcha
    except ImportError:
        print("[WARN] 2captcha-python no instalado. pip install 2captcha-python para resolución automática.")
        return False

    url = driver.current_url
    if "Checkpoint.aspx" not in url:
        return False

    sitekey = get_turnstile_sitekey(driver)
    if not sitekey:
        print("[WARN] No se encontró sitekey de Turnstile en la página.")
        return False

    print("[INFO] Resolviendo Turnstile con 2captcha (sitekey=%s)..." % (sitekey[:20] + "..." if len(sitekey) > 20 else sitekey))
    try:
        solver = TwoCaptcha(api_key)  # type: ignore
        result = solver.turnstile(sitekey=sitekey, url=url)
        token = None
        if isinstance(result, dict):
            token = result.get("code") or (result.get("solution") or {}).get("token")
        elif isinstance(result, str):
            token = result
        if not token:
            print("[WARN] 2captcha no devolvió token.")
            return False
        print("[INFO] Token recibido, enviando validación a BEVSA...")
    except Exception as e:
        print("[WARN] Error 2captcha: %s" % e)
        return False

    # BEVSA: onTurnstileSuccess hace fetch a CaptchaValidate.ashx y redirige
    target_url = return_url_after_success or ""
    js = """
    var token = arguments[0];
    var returnUrl = arguments[1];
    fetch('/CaptchaValidate.ashx?token=' + encodeURIComponent(token) + '&mode=managed')
        .then(function(r) { return r.json(); })
        .then(function(d) {
            if (d.success) {
                var url = returnUrl || (new URLSearchParams(window.location.search).get('returnUrl')) || '/Default.aspx';
                window.location = url;
            }
        });
    """
    try:
        driver.execute_script(js, token, target_url)
    except Exception as e:
        print("[WARN] No se pudo inyectar token: %s" % e)
        return False

    return True


def wait_after_turnstile_submit(driver, timeout=30, url_contains="Historico"):
    """
    Después de solve_and_submit_turnstile, espera a que la página redirija (p.ej. a Historico.aspx).
    Returns True si la URL contiene url_contains dentro del timeout, False si no.
    """
    from selenium.webdriver.support.ui import WebDriverWait
    try:
        WebDriverWait(driver, timeout).until(
            lambda d: url_contains in (d.current_url or "")
        )
        time.sleep(2)
        return True
    except Exception:
        return False
