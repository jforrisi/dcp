"""
Script de Actualización: Tipo de Cambio (TC)
============================================
Ejecuta solo los scripts relacionados con tipo de cambio:
- Download: dolar_bevsa_uyu (dólar Uruguay)
- Direct: 027_tipo_cambio_usd, 019_nxr_argy, 021_nxr_bcch_multipais, 022_nxr_bra, 023_nxr_chile (Perú va en 021)
- Calculate: 002_uyu_nxr_sintetico (NXR sintético Uruguay, al final)

Pensado para ejecutarse a las 16:15 Uruguay (después del cierre BEVSA).
"""

import sys
import time
from pathlib import Path
from datetime import datetime

# Asegurar que la raíz del proyecto esté en el path (funciona desde repo root o desde update/)
_script_dir = Path(__file__).resolve().parent
_repo_root = _script_dir.parent
if str(_repo_root) not in sys.path:
    sys.path.insert(0, str(_repo_root))

# Reutilizar lógica de update_database
from update.update_database import ejecutar_script, PROJECT_ROOT, TIMEOUT_SCRIPT

REPORTE_FILE = PROJECT_ROOT / "update_tc.txt"

# Scripts fijos para TC
TC_DOWNLOAD_SCRIPTS = [
    PROJECT_ROOT / "update" / "download" / "dolar_bevsa_uyu.py",
]
TC_DIRECT_SCRIPTS = [
    PROJECT_ROOT / "update" / "direct" / "027_tipo_cambio_usd.py",
    PROJECT_ROOT / "update" / "direct" / "019_nxr_argy.py",
    PROJECT_ROOT / "update" / "direct" / "021_nxr_bcch_multipais.py",
    PROJECT_ROOT / "update" / "direct" / "022_nxr_bra.py",
    PROJECT_ROOT / "update" / "direct" / "023_nxr_chile.py",
]
TC_CALCULATE_SCRIPTS = [
    PROJECT_ROOT / "update" / "calculate" / "002_uyu_nxr_sintetico.py",
]


def main():
    print("=" * 80)
    print("ACTUALIZACIÓN: TIPO DE CAMBIO (TC)")
    print("=" * 80)
    print(f"Fecha/Hora: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    resultados_fase1 = {'exitosos': [], 'fallidos': []}
    resultados_fase2 = {'exitosos': [], 'fallidos': []}
    inicio_total = time.time()

    # FASE 1: Download
    print("=" * 80)
    print("FASE 1: DOWNLOAD (dolar_bevsa_uyu)")
    print("=" * 80)
    for script_path in TC_DOWNLOAD_SCRIPTS:
        if not script_path.exists():
            resultados_fase1['fallidos'].append({
                'script': script_path.name,
                'error': f'Archivo no encontrado: {script_path}',
                'tiempo': 0
            })
            print(f"[ERROR] No encontrado: {script_path.name}")
            continue
        print(f"Ejecutando: {script_path.name}")
        exitoso, mensaje, tiempo, _ = ejecutar_script(script_path, modo_automatico=True)
        if exitoso:
            resultados_fase1['exitosos'].append({'script': script_path.name, 'tiempo': tiempo})
            print(f"[OK] {script_path.name} ({tiempo:.2f}s)")
        else:
            resultados_fase1['fallidos'].append({'script': script_path.name, 'error': mensaje, 'tiempo': tiempo})
            print(f"[ERROR] {script_path.name}: {mensaje[:200]}...")
        print()

    # FASE 2: Direct
    print("=" * 80)
    print("FASE 2: DIRECT (tipo cambio + NXR)")
    print("=" * 80)
    for script_path in TC_DIRECT_SCRIPTS:
        if not script_path.exists():
            resultados_fase2['fallidos'].append({
                'script': script_path.name,
                'error': f'Archivo no encontrado: {script_path}',
                'tiempo': 0
            })
            print(f"[ERROR] No encontrado: {script_path.name}")
            continue
        print(f"Ejecutando: {script_path.name}")
        exitoso, mensaje, tiempo, _ = ejecutar_script(script_path, modo_automatico=True)
        if exitoso:
            resultados_fase2['exitosos'].append({'script': script_path.name, 'tiempo': tiempo})
            print(f"[OK] {script_path.name} ({tiempo:.2f}s)")
        else:
            resultados_fase2['fallidos'].append({'script': script_path.name, 'error': mensaje, 'tiempo': tiempo})
            print(f"[ERROR] {script_path.name}: {mensaje[:200]}...")
        print()

    # FASE 3: Calculate (NXR sintético al final)
    print("=" * 80)
    print("FASE 3: CALCULATE (NXR sintético Uruguay)")
    print("=" * 80)
    for script_path in TC_CALCULATE_SCRIPTS:
        if not script_path.exists():
            resultados_fase2['fallidos'].append({
                'script': script_path.name,
                'error': f'Archivo no encontrado: {script_path}',
                'tiempo': 0
            })
            print(f"[ERROR] No encontrado: {script_path.name}")
            continue
        print(f"Ejecutando: {script_path.name}")
        exitoso, mensaje, tiempo, _ = ejecutar_script(script_path, modo_automatico=True)
        if exitoso:
            resultados_fase2['exitosos'].append({'script': script_path.name, 'tiempo': tiempo})
            print(f"[OK] {script_path.name} ({tiempo:.2f}s)")
        else:
            resultados_fase2['fallidos'].append({'script': script_path.name, 'error': mensaje, 'tiempo': tiempo})
            print(f"[ERROR] {script_path.name}: {mensaje[:200]}...")
        print()

    tiempo_total = time.time() - inicio_total

    # Generar reporte
    reporte = []
    reporte.append("=" * 80)
    reporte.append("REPORTE: ACTUALIZACIÓN TIPO DE CAMBIO (TC)")
    reporte.append("=" * 80)
    reporte.append(f"Fecha/Hora: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    reporte.append("")
    reporte.append(f"FASE 1 (Download): {len(resultados_fase1['exitosos'])} OK, {len(resultados_fase1['fallidos'])} fallidos")
    reporte.append(f"FASE 2 (Direct) + FASE 3 (Calculate): {len(resultados_fase2['exitosos'])} OK, {len(resultados_fase2['fallidos'])} fallidos")
    reporte.append(f"Tiempo total: {tiempo_total:.2f}s")
    reporte.append("")
    if resultados_fase1['fallidos'] or resultados_fase2['fallidos']:
        for r in resultados_fase1['fallidos'] + resultados_fase2['fallidos']:
            reporte.append(f"ERROR {r['script']}: {r.get('error', 'Unknown')[:500]}")
            reporte.append("")
    reporte.append("=" * 80)

    with open(REPORTE_FILE, 'w', encoding='utf-8') as f:
        f.write("\n".join(reporte))

    print("=" * 80)
    print("COMPLETADO")
    print("=" * 80)
    print(f"Reporte: {REPORTE_FILE}")

    total_fallidos = len(resultados_fase1['fallidos']) + len(resultados_fase2['fallidos'])
    sys.exit(1 if total_fallidos > 0 else 0)


if __name__ == "__main__":
    main()
