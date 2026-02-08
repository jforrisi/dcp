"""
Sistema de logging mejorado para scripts de descarga.
Guarda logs detallados en archivos .txt para debugging.
"""
import os
import sys
from datetime import datetime
from pathlib import Path
import traceback

LOG_DIR = Path(__file__).parent.parent / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

class ScriptLogger:
    """Logger que escribe tanto a stdout como a archivo."""
    
    def __init__(self, script_name: str):
        self.script_name = script_name
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        self.log_file = LOG_DIR / f"{script_name}_{timestamp}.log"
        self.error_file = LOG_DIR / f"{script_name}_{timestamp}_ERRORS.log"
        self._log_file_handle = None
        self._error_file_handle = None
        
    def __enter__(self):
        self._log_file_handle = open(self.log_file, 'w', encoding='utf-8')
        self._error_file_handle = open(self.error_file, 'w', encoding='utf-8')
        self.info("=" * 80)
        self.info(f"INICIO DE EJECUCIÓN: {self.script_name}")
        self.info(f"Timestamp: {datetime.now().isoformat()}")
        self.info("=" * 80)
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            self.error(f"EXCEPCIÓN NO MANEJADA: {exc_type.__name__}: {exc_val}")
            self.error(traceback.format_exc())
        self.info("=" * 80)
        self.info(f"FIN DE EJECUCIÓN: {self.script_name}")
        self.info("=" * 80)
        if self._log_file_handle:
            self._log_file_handle.close()
        if self._error_file_handle:
            self._error_file_handle.close()
    
    def _write(self, level: str, message: str, is_error: bool = False):
        """Escribe a stdout y archivo."""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        formatted = f"[{timestamp}] [{level}] {message}"
        
        # Escribir a stdout
        print(formatted)
        sys.stdout.flush()
        
        # Escribir a archivo de log
        if self._log_file_handle:
            self._log_file_handle.write(formatted + '\n')
            self._log_file_handle.flush()
        
        # Escribir a archivo de errores si es error
        if is_error and self._error_file_handle:
            self._error_file_handle.write(formatted + '\n')
            self._error_file_handle.flush()
    
    def info(self, message: str):
        self._write("INFO", message)
    
    def warn(self, message: str):
        self._write("WARN", message, is_error=True)
    
    def error(self, message: str):
        self._write("ERROR", message, is_error=True)
    
    def debug(self, message: str):
        self._write("DEBUG", message)
    
    def log_exception(self, e: Exception, context: str = ""):
        """Registra una excepción con contexto."""
        error_msg = f"EXCEPCIÓN en {context}: {type(e).__name__}: {str(e)}"
        self.error(error_msg)
        self.error(traceback.format_exc())
    
    def log_selenium_state(self, driver, context: str = ""):
        """Registra el estado actual de Selenium."""
        try:
            self.debug(f"=== ESTADO SELENIUM - {context} ===")
            self.debug(f"URL actual: {driver.current_url}")
            self.debug(f"Título: {driver.title}")
            self.debug(f"Window handles: {len(driver.window_handles)}")
            try:
                page_source_length = len(driver.page_source)
                self.debug(f"Tamaño del HTML: {page_source_length} caracteres")
                # Guardar primeros 5000 caracteres del HTML para debugging
                if page_source_length > 0:
                    html_preview = driver.page_source[:5000]
                    self.debug(f"HTML preview (primeros 5000 chars):\n{html_preview}")
            except Exception as e:
                self.debug(f"No se pudo obtener page_source: {e}")
        except Exception as e:
            self.warn(f"No se pudo obtener estado de Selenium: {e}")
