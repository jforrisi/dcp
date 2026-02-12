"""
Script: Ejecutar solo los scripts que dan problema (excl. update_tc)
====================================================================
Corre únicamente los scripts que fallaron en el run completo de update_database,
EXCLUYENDO los que ya están en update_tc.yml (esos están bien).

Genera update_problemas_report.txt con detalle de qué pasó en cada uno.
Uso: python -m update.run_problemas
"""

import sys
import time
from pathlib import Path
from datetime import datetime

from update.update_database import ejecutar_script, PROJECT_ROOT

# Reporte en la raíz del proyecto
REPORTE_FILE = PROJECT_ROOT / "update_problemas_report.txt"

# Scripts que están en update_tc.yml → NO incluir (ya funcionan)
TC_DOWNLOAD = {"dolar_bevsa_uyu.py"}
TC_DIRECT = {
    "027_tipo_cambio_usd.py",
    "019_nxr_argy.py",
    "021_nxr_bcch_multipais.py",
    "022_nxr_bra.py",
    "023_nxr_chile.py",
    "024_nxr_peru.py",
}

# Scripts que probamos en Run Problemas (de a uno) - solo estos 5
PROBLEMAS_DOWNLOAD = [
    "anexo_estadistico_paraguay.py",
    "expectativas_economicas_paraguay.py",
    "ipc_paraguay.py",
]
PROBLEMAS_DIRECT = [
    "016_ipc.py",
    "018_ipc_paraguay.py",
]


def main():
    print("=" * 80)
    print("EJECUCIÓN: SOLO SCRIPTS QUE DAN PROBLEMA (excl. update_tc)")
    print("=" * 80)
    print(f"Fecha/Hora: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("Excluidos: scripts de update_tc (dolar_bevsa, 027, 019, 021, 022, 023, 024)")
    print()

    download_dir = PROJECT_ROOT / "update" / "download"
    direct_dir = PROJECT_ROOT / "update" / "direct"

    # Construir lista (ruta, fase, nombre)
    scripts_a_ejecutar = []
    for name in PROBLEMAS_DOWNLOAD:
        p = download_dir / name
        if p.exists():
            scripts_a_ejecutar.append((p, "download", name))
        else:
            scripts_a_ejecutar.append((None, "download", name))
    for name in PROBLEMAS_DIRECT:
        p = direct_dir / name
        if p.exists():
            scripts_a_ejecutar.append((p, "direct", name))
        else:
            scripts_a_ejecutar.append((None, "direct", name))

    resultados = []
    inicio_total = time.time()

    for i, (ruta, fase, nombre) in enumerate(scripts_a_ejecutar, 1):
        print(f"[{i}/{len(scripts_a_ejecutar)}] [{fase}] {nombre}")
        print("-" * 80)

        if ruta is None:
            resultado = {
                "fase": fase,
                "script": nombre,
                "exitoso": False,
                "tiempo": 0,
                "mensaje": "Archivo no encontrado",
                "output": "",
            }
            resultados.append(resultado)
            print("[ERROR] Archivo no encontrado")
            print()
            continue

        exitoso, mensaje, tiempo, output = ejecutar_script(ruta, modo_automatico=True)

        resultado = {
            "fase": fase,
            "script": nombre,
            "exitoso": exitoso,
            "tiempo": tiempo,
            "mensaje": mensaje,
            "output": output,
        }
        resultados.append(resultado)

        if exitoso:
            print(f"[OK] {nombre} - Tiempo: {tiempo:.2f}s")
        else:
            print(f"[ERROR] {nombre}")
            print(f"  {mensaje[:300]}...")
        print()

    tiempo_total = time.time() - inicio_total

    # Escribir reporte .txt
    lineas = []
    lineas.append("=" * 80)
    lineas.append("REPORTE: SCRIPTS QUE DAN PROBLEMA (excl. update_tc)")
    lineas.append("=" * 80)
    lineas.append(f"Fecha/Hora: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lineas.append(f"Tiempo total: {tiempo_total:.2f}s ({tiempo_total/60:.2f} min)")
    lineas.append("")
    lineas.append("Scripts ejecutados (solo los que fallaron en update_database, sin los de update_tc):")
    lineas.append("  FASE 1 (download): " + ", ".join(PROBLEMAS_DOWNLOAD))
    lineas.append("  FASE 2 (direct):   " + ", ".join(PROBLEMAS_DIRECT))
    lineas.append("")
    lineas.append("=" * 80)
    lineas.append("RESUMEN POR SCRIPT")
    lineas.append("=" * 80)
    lineas.append("")

    exitosos = sum(1 for r in resultados if r["exitoso"])
    fallidos = sum(1 for r in resultados if not r["exitoso"])

    for r in resultados:
        estado = "OK" if r["exitoso"] else "ERROR"
        lineas.append(f"[{estado}] {r['fase']}/{r['script']} ({r['tiempo']:.2f}s)")
        if not r["exitoso"]:
            lineas.append(f"  Mensaje: {r['mensaje'][:500]}")
            # Incluir últimas 30 líneas del output para contexto
            out_lines = (r["output"] or "").strip().split("\n")
            if len(out_lines) > 30:
                out_lines = out_lines[-30:]
            lineas.append("  Últimas líneas de salida:")
            for ln in out_lines:
                lineas.append("    " + ln[:200])
        lineas.append("")

    lineas.append("=" * 80)
    lineas.append("DETALLE COMPLETO DE ERRORES (salida completa del script)")
    lineas.append("=" * 80)
    lineas.append("")

    for r in resultados:
        if not r["exitoso"] and r["output"]:
            lineas.append("-" * 80)
            lineas.append(f"SCRIPT: {r['fase']}/{r['script']}")
            lineas.append("-" * 80)
            lineas.append(r["output"])
            lineas.append("")

    lineas.append("=" * 80)
    lineas.append(f"FIN DEL REPORTE - Exitosos: {exitosos} | Fallidos: {fallidos}")
    lineas.append("=" * 80)

    with open(REPORTE_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(lineas))

    print("=" * 80)
    print("COMPLETADO")
    print("=" * 80)
    print(f"Exitosos: {exitosos} | Fallidos: {fallidos}")
    print(f"Reporte guardado en: {REPORTE_FILE}")
    print()
    print("Revisá el .txt, validá, y después hacemos el resto.")

    sys.exit(0)


if __name__ == "__main__":
    main()
