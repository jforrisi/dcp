# -*- coding: utf-8 -*-
"""
Script: tasa_pm_multipais_incremental
--------------------------------------
Actualización incremental de TPM (id_variable=52) desde BCCH (últimos 30 días).
Para carga histórica desde 2005 usar 037_tasa_pm_multipais.py o update/update_tpm.py.
"""

import sys
from datetime import datetime, timedelta
from pathlib import Path

script_dir = Path(__file__).parent
base_dir = script_dir.parent.parent
if str(script_dir) not in sys.path:
    sys.path.insert(0, str(script_dir))
if str(base_dir) not in sys.path:
    sys.path.insert(0, str(base_dir))

from db.connection import execute_query_single, execute_update
from _helpers import validar_fechas_solo_nulas
from tpm_bcch_helpers import extraer_tasa_pm_bcch
from tpm_multipais_config import ID_VARIABLE, PAISES_CONFIG

DIAS_ATRAS = 30


def insertar_con_replace(id_variable: int, id_pais: int, df) -> bool:
    """Inserta o actualiza filas en maestro_precios."""
    print(f"\n[INFO] Actualizando BD incremental id_variable={id_variable}, id_pais={id_pais}...")

    row = execute_query_single(
        "SELECT id_variable, id_pais FROM maestro WHERE id_variable = ? AND id_pais = ?",
        (id_variable, id_pais),
    )
    if not row:
        print(f"[ERROR] No existe registro en maestro para id_pais={id_pais}")
        return False

    insertados = 0
    actualizados = 0
    try:
        for _, row in df.iterrows():
            fecha = row["FECHA"]
            valor = row["VALOR"]
            fecha_str = fecha.strftime("%Y-%m-%d") if hasattr(fecha, "strftime") else str(fecha)

            existe = execute_query_single(
                "SELECT id FROM maestro_precios WHERE id_variable = ? AND id_pais = ? AND fecha = ?",
                (id_variable, id_pais, fecha_str),
            )
            if existe:
                success, error, _ = execute_update(
                    "UPDATE maestro_precios SET valor = ? WHERE id_variable = ? AND id_pais = ? AND fecha = ?",
                    (valor, id_variable, id_pais, fecha_str),
                )
                if success:
                    actualizados += 1
            else:
                success, error, _ = execute_update(
                    "INSERT INTO maestro_precios (id_variable, id_pais, fecha, valor) VALUES (?, ?, ?, ?)",
                    (id_variable, id_pais, fecha_str, valor),
                )
                if success:
                    insertados += 1

        print(f"[OK] Insertados: {insertados}, Actualizados: {actualizados}")
        return True
    except Exception as exc:
        print(f"[ERROR] Error al insertar datos: {exc}")
        return False


def procesar_pais(pais_config: dict, fecha_inicio: str, fecha_fin: str) -> bool:
    print("\n" + "=" * 60)
    print(f"PROCESANDO: {pais_config['nombre']}")
    print("=" * 60)

    df = extraer_tasa_pm_bcch(
        codigo_serie=pais_config["codigo"],
        nombre_pais=pais_config["nombre"],
        fecha_inicio=fecha_inicio,
        fecha_fin=fecha_fin,
    )
    if df is None or df.empty:
        return False

    df = df.rename(columns={"Fecha": "FECHA", "Tasa_PM": "VALOR"})
    df = validar_fechas_solo_nulas(df)
    if df.empty:
        return False

    return insertar_con_replace(ID_VARIABLE, pais_config["id_pais"], df)


def main():
    print("=" * 60)
    print("ACTUALIZACIÓN INCREMENTAL: TASA PM MULTIPAÍS")
    print("=" * 60)

    fecha_fin = datetime.today()
    fecha_inicio = fecha_fin - timedelta(days=DIAS_ATRAS)
    fecha_inicio_str = fecha_inicio.strftime("%Y-%m-%d")
    fecha_fin_str = fecha_fin.strftime("%Y-%m-%d")

    print(f"\n[INFO] Rango: {fecha_inicio_str} a {fecha_fin_str} ({DIAS_ATRAS} días)")
    print(f"[INFO] Países: {len(PAISES_CONFIG)}\n")

    resultados = {
        p["nombre"]: procesar_pais(p, fecha_inicio_str, fecha_fin_str) for p in PAISES_CONFIG
    }

    exitosos = sum(1 for ok in resultados.values() if ok)
    print("\n" + "=" * 60)
    print(f"Exitosos: {exitosos} | Con problemas: {len(resultados) - exitosos}")
    print("=" * 60)


if __name__ == "__main__":
    main()
