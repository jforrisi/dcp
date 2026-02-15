"""
Script: embi_bancentral_do
--------------------------
Descarga el Excel "Serie Historica Spread del EMBI" desde el Banco Central
de la Republica Dominicana.

Pagina: https://www.bancentral.gov.do/a/d/2585-entorno-internacional
Enlace: CDN Serie_Historica_Spread_del_EMBI.xlsx

Se guarda como: embi.xlsx en update/historicos
"""

import os
import sys

import requests

root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

from update.utils.logger import ScriptLogger

EXCEL_URL = "https://cdn.bancentral.gov.do/documents/entorno-internacional/documents/Serie_Historica_Spread_del_EMBI.xlsx"

DOWNLOAD_DIR = os.path.join(root_dir, "update", "historicos")
DEST_FILENAME = "embi.xlsx"


def asegurar_directorio():
    os.makedirs(DOWNLOAD_DIR, exist_ok=True)
    return os.path.abspath(DOWNLOAD_DIR)


def descargar():
    asegurar_directorio()
    destino = os.path.join(DOWNLOAD_DIR, DEST_FILENAME)

    print("[INFO] Descargando Serie Historica Spread del EMBI (Bancentral RD)...")
    print(f"[INFO] URL: {EXCEL_URL}")
    print(f"[INFO] Destino: {destino}")

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet,*/*",
    }
    response = requests.get(EXCEL_URL, headers=headers, timeout=60, stream=True)
    response.raise_for_status()

    with open(destino, "wb") as f:
        for chunk in response.iter_content(chunk_size=8192):
            if chunk:
                f.write(chunk)

    if not os.path.exists(destino) or os.path.getsize(destino) == 0:
        raise RuntimeError("El archivo descargado esta vacio o no se creo.")

    print(f"[OK] Guardado: {destino} ({os.path.getsize(destino):,} bytes)")
    return destino


def main():
    script_name = "embi_bancentral_do"
    with ScriptLogger(script_name) as logger:
        try:
            logger.info("=" * 60)
            logger.info("DESCARGA SERIE HISTORICA SPREAD EMBI - BANCENTRAL RD")
            logger.info("=" * 60)
            destino = descargar()
            logger.info(f"Excel guardado: {destino}")
            logger.info("=" * 60)
            logger.info("PROCESO COMPLETADO EXITOSAMENTE")
            logger.info("=" * 60)
            return destino
        except Exception as e:
            logger.log_exception(e, "main()")
            raise


if __name__ == "__main__":
    main()
