# -*- coding: utf-8 -*-
"""Helpers compartidos para extracción TPM desde BCCH."""

import pandas as pd
from bcchapi import Siete

from tpm_multipais_config import BCCH_PASSWORD, BCCH_USER


def extraer_tasa_pm_bcch(
    codigo_serie: str,
    nombre_pais: str,
    fecha_inicio: str,
    fecha_fin: str,
) -> pd.DataFrame | None:
    """Extrae TPM diaria desde BCCH."""
    print(f"\n[INFO] Extrayendo Tasa PM de {nombre_pais}...")
    print(f"   Código de serie: {codigo_serie}")
    print(f"   Rango solicitado: {fecha_inicio} a {fecha_fin}")

    try:
        siete = Siete(BCCH_USER, BCCH_PASSWORD)
        df = siete.cuadro(
            series=[codigo_serie],
            nombres=["tasa_pm"],
            desde=fecha_inicio,
            hasta=fecha_fin,
        )

        if df is None or df.empty:
            print(f"[WARN] No se obtuvieron datos del BCCH para {nombre_pais}")
            return None

        print(f"[OK] Se obtuvieron {len(df)} registros del BCCH")
        df = df.reset_index()

        if "index" in df.columns:
            df.rename(columns={"index": "Fecha"}, inplace=True)
        elif "Fecha" not in df.columns and len(df.columns) > 0:
            df.columns = ["Fecha"] + list(df.columns[1:])

        if "tasa_pm" in df.columns:
            df["Tasa_PM"] = df["tasa_pm"]
        elif len(df.columns) >= 2:
            df["Tasa_PM"] = df.iloc[:, 1]

        if "Fecha" not in df.columns or "Tasa_PM" not in df.columns:
            print(f"[ERROR] No se pudo identificar Fecha/Tasa_PM para {nombre_pais}")
            return None

        df = df[["Fecha", "Tasa_PM"]].copy()
        df["Fecha"] = pd.to_datetime(df["Fecha"], errors="coerce")
        df = df.dropna(subset=["Fecha"])
        df["Tasa_PM"] = pd.to_numeric(df["Tasa_PM"], errors="coerce")
        df = df.dropna(subset=["Tasa_PM"])
        df = df.drop_duplicates(subset="Fecha", keep="last")
        df = df.sort_values("Fecha").reset_index(drop=True)

        if len(df) > 0:
            print(
                f"[OK] {len(df)} registros válidos "
                f"({df['Fecha'].min().strftime('%Y-%m-%d')} a {df['Fecha'].max().strftime('%Y-%m-%d')})"
            )
        return df

    except Exception as exc:
        print(f"[ERROR] Error al obtener datos del BCCH para {nombre_pais}: {exc}")
        import traceback

        traceback.print_exc()
        return None
