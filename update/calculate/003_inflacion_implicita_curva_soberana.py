# -*- coding: utf-8 -*-
"""
Script: inflación implícita curva soberana (1 a 10 años)
---------------------------------------------------------
Calcula la inflación implícita por plazo como (1 + tasa_nominal/100) / (1 + tasa_real/100) - 1,
en %, desde la primera fecha donde haya dato en ambas series (nominal y real) para ese plazo.

- Nominales Uruguay: id_variable 42 (1 año) .. 51 (10 años).
- Reales Uruguay: id_variable 75 (1 año) .. 84 (10 años).
- Destino: variables "Inflación implícita curva soberana X año" (id_variable desde seed), id_pais=858.

Debe ejecutarse después de cargar curvas nominal y real (direct).
"""
import sys
from pathlib import Path

import pandas as pd

SCRIPT_DIR = Path(__file__).resolve().parent.absolute()
PROJECT_ROOT = SCRIPT_DIR.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "update" / "direct"))

from db.connection import execute_query
from _helpers import validar_fechas_solo_nulas, insertar_en_bd_unificado

ID_PAIS = 858  # Uruguay
# Inflación implícita: id_variable 86 (1 año) .. 95 (10 años), fijados por seed
ID_VARIABLES_IMPLICITA = [(86 + i - 1, i) for i in range(1, 11)]  # (86,1), (87,2), ..., (95,10)
# Plazo 1..10 años: id nominal = 41 + plazo, id real = 74 + plazo
ID_NOMINAL_POR_PLAZO = {i: 41 + i for i in range(1, 11)}  # 42..51
ID_REAL_POR_PLAZO = {i: 74 + i for i in range(1, 11)}    # 75..84


def leer_serie(id_variable: int) -> pd.DataFrame:
    """Lee serie id_variable, id_pais=858 desde maestro_precios."""
    rows = execute_query(
        """
        SELECT fecha, valor
        FROM maestro_precios
        WHERE id_variable = ? AND id_pais = ?
        ORDER BY fecha
        """,
        (id_variable, ID_PAIS),
    )
    if not rows:
        return pd.DataFrame()
    df = pd.DataFrame(rows)
    df["fecha"] = pd.to_datetime(df["fecha"]).dt.normalize()
    return df


def main():
    print("=" * 60)
    print("INFLACIÓN IMPLÍCITA CURVA SOBERANA (1 A 10 AÑOS)")
    print("=" * 60)

    config = ID_VARIABLES_IMPLICITA
    for id_var_impl, años in config:
        id_nom = ID_NOMINAL_POR_PLAZO.get(años)
        id_real = ID_REAL_POR_PLAZO.get(años)
        if id_nom is None or id_real is None:
            continue
        df_nom = leer_serie(id_nom)
        df_real = leer_serie(id_real)
        if df_nom.empty or df_real.empty:
            print(f"[WARN] Plazo {años} años: sin datos nominal o real, se omite.")
            continue
        # Join por fecha: solo fechas con dato en ambas
        df_nom = df_nom.rename(columns={"valor": "nominal"})
        df_real = df_real.rename(columns={"valor": "real"})
        j = df_nom[["fecha", "nominal"]].merge(
            df_real[["fecha", "real"]], on="fecha", how="inner"
        )
        j["nominal"] = pd.to_numeric(j["nominal"], errors="coerce")
        j["real"] = pd.to_numeric(j["real"], errors="coerce")
        j = j.dropna(subset=["nominal", "real"])
        if j.empty:
            print(f"[WARN] Plazo {años} años: sin fechas comunes, se omite.")
            continue
        # (1+nom/100)/(1+real/100)-1 en porcentaje
        j["VALOR"] = ((1 + j["nominal"] / 100) / (1 + j["real"] / 100) - 1) * 100
        out = j[["fecha", "VALOR"]].copy()
        out["FECHA"] = out["fecha"].dt.strftime("%Y-%m-%d")
        out = out[["FECHA", "VALOR"]]
        out = validar_fechas_solo_nulas(out)
        insertar_en_bd_unificado(id_var_impl, ID_PAIS, out)
        print(f"[OK] Plazo {años} años: {len(out)} registros")

    print("[OK] Carga finalizada.")


if __name__ == "__main__":
    main()
