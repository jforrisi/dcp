"""
Script: uyu_nxr_sintetico
-------------------------
Calcula el tipo de cambio Uruguay sintético (NXR sintético) como serie que replica
la variación diaria promedio de Brasil, Chile, Colombia y México, anclada al valor
real de Uruguay en una fecha base.

- Lee desde maestro_precios: NXR (id_variable=20) para Brasil, Chile, Colombia, México y Uruguay.
- Variación sintética = promedio de las variaciones diarias (pct_change) de los 4 países.
- Fecha base: 2023-01-04 (valor inicial = NXR Uruguay real ese día).
- Hacia adelante: nxr_sint(t) = nxr_sint(t-1) * (1 + variacion_sint(t)).
- Hacia atrás: nxr_sint(t) = nxr_sint(t+1) / (1 + variacion_sint(t+1)).
- Guarda en maestro_precios: id_variable=85, id_pais=858 (Uruguay).

Debe ejecutarse al final del update (después de los direct que cargan NXR).
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd

SCRIPT_DIR = Path(__file__).resolve().parent.absolute()
PROJECT_ROOT = SCRIPT_DIR.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "update" / "direct"))

from db.connection import execute_query
from _helpers import validar_fechas_solo_nulas, insertar_en_bd_unificado

# NXR = tipo de cambio USD (id_variable 20)
ID_VAR_NXR = 20
# Países para variación sintética: Brasil, Chile, Colombia, México
NXR_FUENTES = [
    (76, "bra"),   # Brasil
    (152, "chi"),  # Chile
    (170, "col"),  # Colombia
    (484, "mex"),  # México
]
# Uruguay real (anchor)
ID_PAIS_UYU = 858
# Serie destino: NXR sintético Uruguay
ID_VARIABLE = 85
ID_PAIS = 858

FECHA_BASE = "2023-01-04"


def leer_serie_nxr(id_pais: int) -> pd.DataFrame:
    """Lee serie NXR (id_variable=20) para un país desde maestro_precios."""
    rows = execute_query(
        """
        SELECT fecha, valor
        FROM maestro_precios
        WHERE id_variable = ? AND id_pais = ?
        ORDER BY fecha
        """,
        (ID_VAR_NXR, id_pais),
    )
    if not rows:
        return pd.DataFrame()
    df = pd.DataFrame(rows)
    df["fecha"] = pd.to_datetime(df["fecha"])
    return df


def main():
    print("=" * 60)
    print("NXR SINTÉTICO URUGUAY (id_variable=85, id_pais=858)")
    print("=" * 60)

    # 1) Cargar NXR de los 4 países y Uruguay
    dfs = {}
    for id_pais, key in NXR_FUENTES:
        df = leer_serie_nxr(id_pais)
        if df.empty:
            print(f"[WARN] Sin datos NXR para id_pais={id_pais} ({key})")
            continue
        df = df.rename(columns={"valor": key})
        dfs[key] = df
        print(f"[OK] NXR {key}: {len(df)} registros")

    if len(dfs) < 4:
        print("[ERROR] Se necesitan los 4 países (BRA, CHI, COL, MEX) para calcular la variación sintética.")
        return

    df_uyu = leer_serie_nxr(ID_PAIS_UYU)
    if df_uyu.empty:
        print("[ERROR] Sin datos NXR Uruguay para anclar la serie sintética.")
        return
    df_uyu = df_uyu.rename(columns={"valor": "nxr_uyu"})
    print(f"[OK] NXR Uruguay: {len(df_uyu)} registros")

    # 2) Unir todos por fecha (outer para tener todas las fechas)
    df_all = dfs["bra"][["fecha", "bra"]].copy()
    for key in ["chi", "col", "mex"]:
        if key in dfs:
            df_all = df_all.merge(dfs[key][["fecha", key]], on="fecha", how="outer")
    df_all = df_all.sort_values("fecha").reset_index(drop=True)

    # 3) Variación diaria de cada país y promedio
    for key in ["bra", "chi", "col", "mex"]:
        if key in df_all.columns:
            df_all[f"variacion_{key}"] = df_all[key].pct_change()
    cols_var = [c for c in df_all.columns if c.startswith("variacion_") and c != "variacion_uyu_sintetico"]
    df_all["variacion_uyu_sintetico"] = df_all[cols_var].mean(axis=1)

    # 4) Merge con Uruguay (inner: solo fechas donde hay UYU y variación sintética)
    df_all = df_all.merge(df_uyu[["fecha", "nxr_uyu"]], on="fecha", how="inner")
    df_all = df_all.dropna(subset=["variacion_uyu_sintetico"])
    df_all = df_all.sort_values("fecha").reset_index(drop=True)

    if df_all.empty:
        print("[ERROR] No quedaron fechas comunes entre NXR 4 países y Uruguay.")
        return

    # 5) Fecha base
    fecha_base = pd.to_datetime(FECHA_BASE)
    if fecha_base not in df_all["fecha"].values:
        # Usar la primera fecha disponible que tenga nxr_uyu
        fecha_base = df_all["fecha"].min()
        print(f"[INFO] Fecha base no encontrada; usando {fecha_base.date()}")

    df_all = df_all.set_index("fecha").sort_index()
    # Asegurar dtypes numéricos para evitar FutureWarning al asignar
    df_all["variacion_uyu_sintetico"] = df_all["variacion_uyu_sintetico"].astype(np.float64)

    # 6) Construir serie sintética (asignaciones en float64 para evitar dtype incompatible)
    valor_inicial = float(df_all.loc[fecha_base, "nxr_uyu"])
    df_all["nxr_sintetico"] = np.nan
    df_all["nxr_sintetico"] = df_all["nxr_sintetico"].astype(np.float64)
    df_all.loc[fecha_base, "nxr_sintetico"] = valor_inicial

    idx = df_all.index
    # Hacia adelante (t > fecha_base)
    pos_base = idx.get_loc(fecha_base)
    for i in range(pos_base + 1, len(idx)):
        t = idx[i]
        t_ant = idx[i - 1]
        var = df_all.loc[t, "variacion_uyu_sintetico"]
        df_all.loc[t, "nxr_sintetico"] = float(df_all.loc[t_ant, "nxr_sintetico"] * (1 + var))

    # Hacia atrás (t < fecha_base)
    for i in range(pos_base - 1, -1, -1):
        t = idx[i]
        t_sig = idx[i + 1]
        var_sig = df_all.loc[t_sig, "variacion_uyu_sintetico"]
        df_all.loc[t, "nxr_sintetico"] = float(df_all.loc[t_sig, "nxr_sintetico"] / (1 + var_sig))

    # 7) Salida: FECHA, VALOR
    out = df_all.reset_index()
    out = out[["fecha", "nxr_sintetico"]].dropna(subset=["nxr_sintetico"])
    out = out.rename(columns={"fecha": "FECHA", "nxr_sintetico": "VALOR"})
    out["FECHA"] = out["FECHA"].dt.strftime("%Y-%m-%d")

    print(f"[OK] NXR sintético: {len(out)} registros (desde {out['FECHA'].min()} hasta {out['FECHA'].max()})")

    out = validar_fechas_solo_nulas(out)
    insertar_en_bd_unificado(ID_VARIABLE, ID_PAIS, out)
    print("[OK] Carga finalizada.")


if __name__ == "__main__":
    main()
