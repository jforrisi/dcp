"""
Script: ipc_uy_desagregado_ine
-----------------------------
Descarga el Excel del INE Uruguay: serie país IPC por división, grupo, clase, subclase y producto
(base octubre 2022 = 100).

Guarda en: update/historicos/ipc_uy_div_gr_cl_sc_pr.xlsx
No inserta en base de datos. El direct 036 solo actualiza ipc_desagregados_valores. El maestro
ipc_desagregados se carga una vez con scripts/carga_inicial_ipc_desagregados_desde_export.py.
"""

import os
import sys
from pathlib import Path

import requests

root_dir = Path(__file__).resolve().parent.parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

URL_EXCEL_INE = (
    "https://www5.ine.gub.uy/documents/Estad%C3%ADsticasecon%C3%B3micas/"
    "SERIES%20Y%20OTROS/IPC/Base%20Octubre%202022=100/"
    "SERIE%20PA%C3%8DS_DivGrCLScPr_Desde%20Octubre%202022.xlsx"
)
HISTORICOS_DIR = "update/historicos"
DEST_FILENAME = "ipc_uy_div_gr_cl_sc_pr.xlsx"


def _dir_historicos() -> Path:
    base = Path(os.getcwd())
    d = base / HISTORICOS_DIR
    d.mkdir(parents=True, exist_ok=True)
    return d


def _descargar() -> bytes:
    try:
        r = requests.get(URL_EXCEL_INE, timeout=120)
        r.raise_for_status()
        return r.content
    except requests.exceptions.SSLError as e:
        print(f"[WARN] SSL: {e}")
        print("[INFO] Reintentando sin verificar SSL...")
        import urllib3
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        r = requests.get(URL_EXCEL_INE, timeout=120, verify=False)
        r.raise_for_status()
        return r.content


def main():
    dest_dir = _dir_historicos()
    dest_path = dest_dir / DEST_FILENAME
    print(f"[INFO] Descargando INE -> {dest_path}")
    content = _descargar()
    dest_path.write_bytes(content)
    print(f"[OK] Guardado ({len(content)} bytes)")


if __name__ == "__main__":
    main()
