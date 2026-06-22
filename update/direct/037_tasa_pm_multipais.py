# -*- coding: utf-8 -*-
"""
Script: tasa_pm_multipais
-------------------------
Carga histórica completa de TPM (id_variable=52) desde BCCH desde 2005-01-01.

No corre en update_database diario (excluido); usar update/update_tpm.py o ejecutar manual.
"""

import sys
from datetime import datetime
from pathlib import Path

script_dir = Path(__file__).parent
base_dir = script_dir.parent.parent
if str(script_dir) not in sys.path:
    sys.path.insert(0, str(script_dir))
if str(base_dir) not in sys.path:
    sys.path.insert(0, str(base_dir))

from _helpers import insertar_en_bd_unificado, validar_fechas_solo_nulas
from tpm_bcch_helpers import extraer_tasa_pm_bcch
from tpm_multipais_config import FECHA_INICIO, ID_VARIABLE, PAISES_CONFIG


def procesar_pais(pais_config: dict, fecha_inicio: str, fecha_fin: str) -> bool:
    id_pais = pais_config["id_pais"]
    df = extraer_tasa_pm_bcch(
        codigo_serie=pais_config["codigo"],
        nombre_pais=pais_config["nombre"],
        fecha_inicio=fecha_inicio,
        fecha_fin=fecha_fin,
    )
    if df is None or df.empty:
        print(f"[WARN] Sin datos para {pais_config['nombre']}")
        return False

    df = df.rename(columns={"Fecha": "FECHA", "Tasa_PM": "VALOR"})
    df = validar_fechas_solo_nulas(df)
    if df.empty:
        return False

    print(f"\n[INFO] Cargando BD: {pais_config['nombre']} (id_pais={id_pais})...")
    insertar_en_bd_unificado(ID_VARIABLE, id_pais, df)
    return True


def main():
    print("=" * 60)
    print("CARGA HISTÓRICA TPM MULTIPAÍS (BCCH desde 2005)")
    print("=" * 60)

    fecha_fin = datetime.today().strftime("%Y-%m-%d")
    print(f"\n[INFO] Rango: {FECHA_INICIO} a {fecha_fin}")
    print(f"[INFO] Países: {len(PAISES_CONFIG)}\n")

    resultados = {}
    for pais_config in PAISES_CONFIG:
        resultados[pais_config["nombre"]] = procesar_pais(
            pais_config, FECHA_INICIO, fecha_fin
        )

    exitosos = sum(1 for ok in resultados.values() if ok)
    print("\n" + "=" * 60)
    print("RESUMEN")
    print("=" * 60)
    print(f"Exitosos: {exitosos} | Fallidos/sin datos: {len(resultados) - exitosos}")
    if exitosos < len(resultados):
        print("\nSin datos o error:")
        for nombre, ok in resultados.items():
            if not ok:
                print(f"  - {nombre}")
    print("=" * 60)


if __name__ == "__main__":
    main()
