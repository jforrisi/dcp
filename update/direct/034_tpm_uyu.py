"""
Script: tpm_uyu (Tasa de Política Monetaria - Uruguay)
------------------------------------------------------
Lee update/historicos/tpm_uyu.xlsx (col A fecha, col B TPM) y carga en maestro_precios.
El Excel lo genera update/download/tpm_uyu.py (Tasa 1 Día BCU).
"""

import sys
from pathlib import Path

import pandas as pd

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))
from _helpers import insertar_en_bd_unificado

HISTORICOS = PROJECT_ROOT / "update" / "historicos"
ARCHIVO = HISTORICOS / "tpm_uyu.xlsx"
ID_VARIABLE = 52   # Tasa de PM
ID_PAIS = 858      # Uruguay


def main():
    if not ARCHIVO.exists():
        print(f"[WARN] No existe {ARCHIVO}. Ejecutá antes: python update/download/tpm_uyu.py")
        return
    # Primera fila es encabezado (Fecha, Tasa de Política Monetaria); col B puede venir "6,50%"
    df = pd.read_excel(ARCHIVO, usecols=[0, 1], header=0)
    df = df.rename(columns={df.columns[0]: "FECHA", df.columns[1]: "VALOR"})
    df["FECHA"] = pd.to_datetime(df["FECHA"], dayfirst=True, errors="coerce")
    df = df.dropna(subset=["FECHA"])
    # Normalizar valor: "6,50%" -> 6.5 (coma a punto, quitar %)
    val = df["VALOR"].astype(str).str.replace(",", ".", regex=False).str.replace("%", "", regex=False).str.strip()
    df["VALOR"] = pd.to_numeric(val, errors="coerce")
    df = df.dropna(subset=["VALOR"])
    df["FECHA"] = df["FECHA"].dt.strftime("%Y-%m-%d")
    df = df[["FECHA", "VALOR"]].sort_values("FECHA").drop_duplicates(subset=["FECHA"]).reset_index(drop=True)
    if df.empty:
        print("[WARN] Sin filas válidas en el Excel.")
        return
    print(f"[OK] TPM Uruguay: {len(df)} registros")
    insertar_en_bd_unificado(ID_VARIABLE, ID_PAIS, df)
    print("[OK] Carga finalizada.")


if __name__ == "__main__":
    main()
