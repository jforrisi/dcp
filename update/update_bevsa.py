"""
Actualización BEVSA: descargas (dólar + curvas) y carga en base de datos.
========================================
Ejecuta en orden:
  FASE 1 - Download: dolar_bevsa_uyu, curva_pesos_uyu_temp, curva_pesos_uyu_ui_temp
  FASE 2 - Direct:   027_tipo_cambio_usd, 029_curva_pesos_uyu_bevsa_nominal, 030_curva_pesos_uyu_bevsa_real

Pensado para correr localmente o desde GitHub Actions (workflow update_bevsa).
Requiere CAPTCHA_API_KEY para resolver Turnstile en CI; DATABASE_URL para los direct.
"""

import sys
import time
from pathlib import Path
from datetime import datetime

_script_dir = Path(__file__).resolve().parent
_repo_root = _script_dir.parent
if str(_repo_root) not in sys.path:
    sys.path.insert(0, str(_repo_root))

from update.update_database import ejecutar_script, PROJECT_ROOT, TIMEOUT_SCRIPT

REPORTE_FILE = PROJECT_ROOT / "update_bevsa.txt"

BEVSA_DOWNLOAD_SCRIPTS = [
    PROJECT_ROOT / "update" / "download" / "dolar_bevsa_uyu.py",
    PROJECT_ROOT / "update" / "download" / "curva_pesos_uyu_temp.py",
    PROJECT_ROOT / "update" / "download" / "curva_pesos_uyu_ui_temp.py",
]
BEVSA_DIRECT_SCRIPTS = [
    PROJECT_ROOT / "update" / "direct" / "027_tipo_cambio_usd.py",
    PROJECT_ROOT / "update" / "direct" / "029_curva_pesos_uyu_bevsa_nominal.py",
    PROJECT_ROOT / "update" / "direct" / "030_curva_pesos_uyu_bevsa_real.py",
]


def main():
    print("=" * 80)
    print("ACTUALIZACIÓN BEVSA (descargas + carga en BD)")
    print("=" * 80)
    print(f"Fecha/Hora: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    resultados_fase1 = {"exitosos": [], "fallidos": []}
    resultados_fase2 = {"exitosos": [], "fallidos": []}
    inicio_total = time.time()

    # FASE 1: Download
    print("=" * 80)
    print("FASE 1: DOWNLOAD (dolar_bevsa_uyu, curva_pesos_uyu_temp, curva_pesos_uyu_ui_temp)")
    print("=" * 80)
    for script_path in BEVSA_DOWNLOAD_SCRIPTS:
        if not script_path.exists():
            resultados_fase1["fallidos"].append({
                "script": script_path.name,
                "error": f"Archivo no encontrado: {script_path}",
                "tiempo": 0,
            })
            print(f"[ERROR] No encontrado: {script_path.name}")
            continue
        print(f"Ejecutando: {script_path.name}")
        exitoso, mensaje, tiempo, _ = ejecutar_script(script_path, modo_automatico=True)
        if exitoso:
            resultados_fase1["exitosos"].append({"script": script_path.name, "tiempo": tiempo})
            print(f"[OK] {script_path.name} ({tiempo:.2f}s)")
        else:
            resultados_fase1["fallidos"].append({"script": script_path.name, "error": mensaje, "tiempo": tiempo})
            print(f"[ERROR] {script_path.name}: {mensaje[:300]}")
        print()

    # FASE 2: Direct (cargar en BD)
    print("=" * 80)
    print("FASE 2: DIRECT (027 tipo cambio, 029 curva nominal, 030 curva real)")
    print("=" * 80)
    for script_path in BEVSA_DIRECT_SCRIPTS:
        if not script_path.exists():
            resultados_fase2["fallidos"].append({
                "script": script_path.name,
                "error": f"Archivo no encontrado: {script_path}",
                "tiempo": 0,
            })
            print(f"[ERROR] No encontrado: {script_path.name}")
            continue
        print(f"Ejecutando: {script_path.name}")
        exitoso, mensaje, tiempo, _ = ejecutar_script(script_path, modo_automatico=True)
        if exitoso:
            resultados_fase2["exitosos"].append({"script": script_path.name, "tiempo": tiempo})
            print(f"[OK] {script_path.name} ({tiempo:.2f}s)")
        else:
            resultados_fase2["fallidos"].append({"script": script_path.name, "error": mensaje, "tiempo": tiempo})
            print(f"[ERROR] {script_path.name}: {mensaje[:300]}")
        print()

    tiempo_total = time.time() - inicio_total

    # Reporte
    reporte = []
    reporte.append("=" * 80)
    reporte.append("REPORTE: ACTUALIZACIÓN BEVSA")
    reporte.append("=" * 80)
    reporte.append(f"Fecha/Hora: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    reporte.append("")
    reporte.append(f"FASE 1 (Download): {len(resultados_fase1['exitosos'])} OK, {len(resultados_fase1['fallidos'])} fallidos")
    reporte.append(f"FASE 2 (Direct):   {len(resultados_fase2['exitosos'])} OK, {len(resultados_fase2['fallidos'])} fallidos")
    reporte.append(f"Tiempo total: {tiempo_total:.2f}s")
    reporte.append("")
    for r in resultados_fase1["fallidos"] + resultados_fase2["fallidos"]:
        reporte.append(f"ERROR {r['script']}: {r.get('error', 'Unknown')[:500]}")
        reporte.append("")
    reporte.append("=" * 80)

    with open(REPORTE_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(reporte))

    print("=" * 80)
    print("COMPLETADO")
    print("=" * 80)
    print(f"Reporte: {REPORTE_FILE}")

    total_fallidos = len(resultados_fase1["fallidos"]) + len(resultados_fase2["fallidos"])
    sys.exit(1 if total_fallidos > 0 else 0)


if __name__ == "__main__":
    main()
