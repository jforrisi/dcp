"""
Actualización de TPM (Tasa de Política Monetaria)
==================================================
- 037: histórico multipaís BCCH desde 2005
- 034: Uruguay desde Excel BCU
"""

import sys
import time
from datetime import datetime
from pathlib import Path

_script_dir = Path(__file__).resolve().parent
_repo_root = _script_dir.parent
if str(_repo_root) not in sys.path:
    sys.path.insert(0, str(_repo_root))

from update.update_database import ejecutar_script, PROJECT_ROOT

REPORTE_FILE = PROJECT_ROOT / "update_tpm.txt"

TPM_SCRIPTS = [
    PROJECT_ROOT / "update" / "direct" / "037_tasa_pm_multipais.py",
    PROJECT_ROOT / "update" / "direct" / "034_tpm_uyu.py",
]


def main():
    print("=" * 80)
    print("ACTUALIZACIÓN: TPM (TASA DE POLÍTICA MONETARIA)")
    print("=" * 80)
    print(f"Fecha/Hora: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    exitosos = []
    fallidos = []
    inicio = time.time()

    for script_path in TPM_SCRIPTS:
        if not script_path.exists():
            fallidos.append({"script": script_path.name, "error": "No encontrado", "tiempo": 0})
            continue
        print(f"Ejecutando: {script_path.name}")
        ok, msg, t, _ = ejecutar_script(script_path, modo_automatico=True)
        if ok:
            exitosos.append({"script": script_path.name, "tiempo": t})
            print(f"[OK] {script_path.name} ({t:.2f}s)")
        else:
            fallidos.append({"script": script_path.name, "error": msg, "tiempo": t})
            print(f"[ERROR] {script_path.name}: {msg[:300]}")
        print()

    reporte = [
        "=" * 80,
        "REPORTE: ACTUALIZACIÓN TPM",
        "=" * 80,
        f"Fecha/Hora: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"OK: {len(exitosos)} | Fallidos: {len(fallidos)}",
        f"Tiempo total: {time.time() - inicio:.2f}s",
        "",
    ]
    for f in fallidos:
        reporte.append(f"ERROR {f['script']}: {f.get('error', '')[:500]}")
    reporte.append("=" * 80)

    REPORTE_FILE.write_text("\n".join(reporte), encoding="utf-8")
    print(f"Reporte: {REPORTE_FILE}")
    sys.exit(1 if fallidos else 0)


if __name__ == "__main__":
    main()
