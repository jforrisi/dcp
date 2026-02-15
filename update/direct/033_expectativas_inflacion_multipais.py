# -*- coding: utf-8 -*-
"""
Script: expectativas_inflacion_multipais
----------------------------------------
Carga expectativas de inflación (12 y 24 meses) para Chile, Uruguay, Colombia,
México y Perú en maestro_precios.

Variables en BD:
  - id_variable 23: Inflación esperada 12 meses
  - id_variable 24: Inflación esperada 24 meses

Fuentes:
  - Chile:   API BCCH F089.IPC.V12.14.M (12m), F089.IPC.V12.15.M (24m)
  - Uruguay: update/historicos/expectativas_inflacion_uyu_bcu.xls (col B fecha, X 12m, AM 24m)
  - Perú:    update/historicos/expectativas_inflacion_peru.xlsx (col A fecha, B 12m)
  - México:  update/historicos/expectativas_inflacion_mexico.xlsx (fecha, valor = 12m)
  - Colombia: update/historicos/expectativas_eme_analistas_banrep.xlsx primera hoja (A fecha, J 12m, P 24m)

Requisito: En maestro deben existir los registros (id_variable, id_pais) para cada serie.
"""

import os
import sys
from pathlib import Path
from datetime import datetime

import pandas as pd
import requests

# Raíz del proyecto (update/direct -> update -> raíz)
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from _helpers import insertar_en_bd_unificado

# IDs en BD
ID_VAR_12M = 23   # Inflación esperada 12 meses
ID_VAR_24M = 24   # Inflación esperada 24 meses

# id_pais por país (pais_grupo)
ID_CHILE = 152
ID_URUGUAY = 858
ID_COLOMBIA = 170
ID_MEXICO = 484
ID_PERU = 604

HISTORICOS = PROJECT_ROOT / "update" / "historicos"

# Credenciales BCCH (mismo que otros scripts)
BCCH_USER = "joaquin.forrisi@gmail.com"
BCCH_PASSWORD = "Joaquin.13"

# Banxico API (expectativas inflación 12m - México)
BANXICO_TOKEN = "eb42b7168baa77063b964ad9e2501a29b6c4d7ba9c67d7f417098725555aa1eb"
BANXICO_SERIE_EXPECTATIVAS = "SR16774"  # Expectativas inflación 12 meses (mediana)
BANXICO_API_BASE = "https://www.banxico.org.mx/SieAPIRest/service/v1"


def chile_bcch() -> dict:
    """Chile: API BCCH. Retorna {'12m': df, '24m': df}."""
    from bcchapi import Siete

    codigo_12 = "F089.IPC.V12.14.M"
    codigo_24 = "F089.IPC.V12.15.M"
    fecha_fin = datetime.today().strftime("%Y-%m-%d")
    fecha_ini = "2010-01-01"

    out = {}
    try:
        siete = Siete(BCCH_USER, BCCH_PASSWORD)
        for codigo, key in [(codigo_12, "12m"), (codigo_24, "24m")]:
            df = siete.cuadro(series=[codigo], nombres=["valor"], desde=fecha_ini, hasta=fecha_fin)
            if df is None or df.empty:
                print(f"[WARN] Chile {key}: sin datos BCCH")
                continue
            df = df.reset_index()
            df = df.rename(columns={"index": "Fecha", "valor": "VALOR"})
            if "VALOR" not in df.columns and len(df.columns) >= 2:
                df["VALOR"] = pd.to_numeric(df.iloc[:, 1], errors="coerce")
            df["Fecha"] = pd.to_datetime(df["Fecha"], errors="coerce")
            df = df.dropna(subset=["Fecha", "VALOR"])
            df["FECHA"] = df["Fecha"].dt.strftime("%Y-%m-%d")
            df = df[["FECHA", "VALOR"]].drop_duplicates(subset=["FECHA"]).sort_values("FECHA").reset_index(drop=True)
            out[key] = df
            print(f"[OK] Chile {key}: {len(df)} registros")
    except Exception as e:
        print(f"[ERROR] Chile BCCH: {e}")
    return out


def uruguay_xls() -> dict:
    """Uruguay: expectativas_inflacion_uyu_bcu.xls. Col B=fecha, X=12m, AM=24m."""
    path = HISTORICOS / "expectativas_inflacion_uyu_bcu.xls"
    out = {}
    if not path.exists():
        print(f"[WARN] Uruguay: no existe {path}")
        return out
    try:
        # .xls requiere xlrd: pip install xlrd
        df = pd.read_excel(path, header=None)
    except Exception as e:
        print(f"[ERROR] Uruguay leyendo xls: {e}")
        return out
    # Col B = índice 1, X = 24 (0-based), AM = 40 (0-based)
    col_fecha, col_12, col_24 = 1, 23, 38  # B=fecha, X=12m, AM=24m
    if df.shape[1] <= col_24:
        print(f"[WARN] Uruguay: Excel con pocas columnas ({df.shape[1]})")
        return out
    df = df.iloc[:, [col_fecha, col_12, col_24]].copy()
    df.columns = ["Fecha", "VALOR_12", "VALOR_24"]
    df["Fecha"] = pd.to_datetime(df["Fecha"], errors="coerce")
    df = df.dropna(subset=["Fecha"])
    df["FECHA"] = df["Fecha"].dt.strftime("%Y-%m-%d")
    for key, col in [("12m", "VALOR_12"), ("24m", "VALOR_24")]:
        d = df[["FECHA", col]].copy()
        d = d.rename(columns={col: "VALOR"})
        d["VALOR"] = pd.to_numeric(d["VALOR"], errors="coerce")
        d = d.dropna(subset=["VALOR"])
        out[key] = d[["FECHA", "VALOR"]].sort_values("FECHA").reset_index(drop=True)
        print(f"[OK] Uruguay {key}: {len(out[key])} registros")
    return out


def peru_xlsx() -> dict:
    """Perú: expectativas_inflacion_peru.xlsx. Col A=fecha, B=12m (solo 12m)."""
    path = HISTORICOS / "expectativas_inflacion_peru.xlsx"
    if not path.exists():
        path = HISTORICOS / "expectaivas_infalcion_peru.xlsx"  # typo posible
    out = {}
    if not path.exists():
        print(f"[WARN] Perú: no existe archivo de expectativas en {HISTORICOS}")
        return out
    try:
        df = pd.read_excel(path, usecols=[0, 1], header=None, names=["Fecha", "VALOR"])
    except Exception as e:
        print(f"[ERROR] Perú leyendo xlsx: {e}")
        return out
    df["Fecha"] = pd.to_datetime(df["Fecha"], errors="coerce")
    df = df.dropna(subset=["Fecha"])
    df["VALOR"] = pd.to_numeric(df["VALOR"], errors="coerce")
    df = df.dropna(subset=["VALOR"])
    df["FECHA"] = df["Fecha"].dt.strftime("%Y-%m-%d")
    out["12m"] = df[["FECHA", "VALOR"]].sort_values("FECHA").reset_index(drop=True)
    print(f"[OK] Perú 12m: {len(out['12m'])} registros")
    return out


def mexico_descargar_banxico() -> bool:
    """Descarga expectativas de inflación 12m desde API Banxico y guarda Excel. Retorna True si OK."""
    HISTORICOS.mkdir(parents=True, exist_ok=True)
    path = HISTORICOS / "expectativas_inflacion_mexico.xlsx"
    fecha_fin = datetime.today().strftime("%Y-%m-%d")
    fecha_ini = "2015-01-01"
    url = f"{BANXICO_API_BASE}/series/{BANXICO_SERIE_EXPECTATIVAS}/datos/{fecha_ini}/{fecha_fin}"
    try:
        r = requests.get(
            url,
            headers={"Bmx-Token": BANXICO_TOKEN, "Accept": "application/json"},
            timeout=60,
        )
        r.raise_for_status()
        data = r.json()
        if not isinstance(data, dict) or "bmx" not in data or not data["bmx"].get("series"):
            print("[WARN] México Banxico: respuesta sin series")
            return False
        datos_serie = data["bmx"]["series"][0].get("datos", [])
        if not datos_serie:
            print("[WARN] México Banxico: sin datos")
            return False
        registros = []
        for item in datos_serie:
            fecha_str = item.get("fecha", "")
            valor_str = item.get("dato", "")
            if valor_str in ("N/E", "n.d.", "nan", "", "-", "N/A", None):
                continue
            try:
                fecha = pd.to_datetime(fecha_str, format="%d/%m/%Y", errors="coerce")
                if pd.isna(fecha):
                    fecha = pd.to_datetime(fecha_str, errors="coerce")
                if pd.isna(fecha):
                    continue
                valor = float(str(valor_str).replace(",", "").replace(" ", ""))
                registros.append({"fecha": fecha.date(), "valor": valor})
            except (ValueError, TypeError):
                continue
        if not registros:
            return False
        df = pd.DataFrame(registros).sort_values("fecha").drop_duplicates(subset=["fecha"])
        df.to_excel(path, index=False, engine="openpyxl")
        print(f"[OK] México: descargados {len(df)} registros desde Banxico → {path.name}")
        return True
    except Exception as e:
        print(f"[WARN] México Banxico descarga: {e}")
        return False


def mexico_xlsx() -> dict:
    """México: expectativas_inflacion_mexico.xlsx (fecha, valor = 12m). Si no existe, descarga desde Banxico."""
    path = HISTORICOS / "expectativas_inflacion_mexico.xlsx"
    out = {}
    if not path.exists():
        print("[INFO] México: archivo no encontrado, descargando desde Banxico...")
        mexico_descargar_banxico()
    if not path.exists():
        print("[WARN] México: no se pudo obtener archivo")
        return out
    try:
        df = pd.read_excel(path)
    except Exception as e:
        print(f"[ERROR] México leyendo xlsx: {e}")
        return out
    col_fecha = "fecha" if "fecha" in df.columns else df.columns[0]
    col_valor = "valor" if "valor" in df.columns else df.columns[1]
    df = df[[col_fecha, col_valor]].copy()
    df.columns = ["Fecha", "VALOR"]
    df["Fecha"] = pd.to_datetime(df["Fecha"], errors="coerce")
    df["VALOR"] = pd.to_numeric(df["VALOR"], errors="coerce")
    df = df.dropna(subset=["Fecha", "VALOR"])
    df["FECHA"] = df["Fecha"].dt.strftime("%Y-%m-%d")
    out["12m"] = df[["FECHA", "VALOR"]].sort_values("FECHA").reset_index(drop=True)
    print(f"[OK] México 12m: {len(out['12m'])} registros")
    return out


def colombia_xlsx() -> dict:
    """Colombia: expectativas_eme_analistas_banrep.xlsx primera hoja. A=fecha, J=12m, P=24m."""
    path = HISTORICOS / "expectativas_eme_analistas_banrep.xlsx"
    out = {}
    if not path.exists():
        print(f"[WARN] Colombia: no existe {path}")
        return out
    try:
        df = pd.read_excel(path, sheet_name=0, usecols=[0, 9, 15], header=None,
                           names=["Fecha", "VALOR_12", "VALOR_24"])
    except Exception as e:
        print(f"[ERROR] Colombia leyendo xlsx: {e}")
        return out
    df["Fecha"] = pd.to_datetime(df["Fecha"], errors="coerce")
    df = df.dropna(subset=["Fecha"])
    df["FECHA"] = df["Fecha"].dt.strftime("%Y-%m-%d")
    for key, col in [("12m", "VALOR_12"), ("24m", "VALOR_24")]:
        d = df[["FECHA", col]].copy()
        d = d.rename(columns={col: "VALOR"})
        d["VALOR"] = pd.to_numeric(d["VALOR"], errors="coerce")
        d = d.dropna(subset=["VALOR"])
        out[key] = d[["FECHA", "VALOR"]].sort_values("FECHA").reset_index(drop=True)
        print(f"[OK] Colombia {key}: {len(out[key])} registros")
    return out


def main():
    only = (sys.argv[1].strip().lower() if len(sys.argv) > 1 else None)
    if only and only not in ("chile", "uruguay", "peru", "mexico", "colombia"):
        print("Uso: python 033_expectativas_inflacion_multipais.py [chile|uruguay|peru|mexico|colombia]")
        print("  Sin argumentos: ejecuta todos los países.")
        return

    print("=" * 60)
    print("EXPECTATIVAS DE INFLACIÓN - MULTIPAÍS (23=12m, 24=24m)")
    print("=" * 60)

    if not only or only == "chile":
        print("\n--- Chile (BCCH API) ---")
        chile = chile_bcch()
        if chile.get("12m") is not None and not chile["12m"].empty:
            insertar_en_bd_unificado(ID_VAR_12M, ID_CHILE, chile["12m"])
        if chile.get("24m") is not None and not chile["24m"].empty:
            insertar_en_bd_unificado(ID_VAR_24M, ID_CHILE, chile["24m"])

    if not only or only == "uruguay":
        print("\n--- Uruguay (BCU xls) ---")
        uyu = uruguay_xls()
        if uyu.get("12m") is not None and not uyu["12m"].empty:
            insertar_en_bd_unificado(ID_VAR_12M, ID_URUGUAY, uyu["12m"])
        if uyu.get("24m") is not None and not uyu["24m"].empty:
            insertar_en_bd_unificado(ID_VAR_24M, ID_URUGUAY, uyu["24m"])

    if not only or only == "peru":
        print("\n--- Perú ---")
        peru = peru_xlsx()
        if peru.get("12m") is not None and not peru["12m"].empty:
            insertar_en_bd_unificado(ID_VAR_12M, ID_PERU, peru["12m"])

    if not only or only == "mexico":
        print("\n--- México (Banxico) ---")
        mex = mexico_xlsx()
        if mex.get("12m") is not None and not mex["12m"].empty:
            insertar_en_bd_unificado(ID_VAR_12M, ID_MEXICO, mex["12m"])

    if not only or only == "colombia":
        print("\n--- Colombia ---")
        col = colombia_xlsx()
        if col.get("12m") is not None and not col["12m"].empty:
            df12 = col["12m"].copy()
            df12["VALOR"] = df12["VALOR"] * 100
            insertar_en_bd_unificado(ID_VAR_12M, ID_COLOMBIA, df12)
        if col.get("24m") is not None and not col["24m"].empty:
            df24 = col["24m"].copy()
            df24["VALOR"] = df24["VALOR"] * 100
            insertar_en_bd_unificado(ID_VAR_24M, ID_COLOMBIA, df24)

    print("\n" + "=" * 60)
    print("[OK] Expectativas de inflación multipaís finalizado.")
    print("=" * 60)


if __name__ == "__main__":
    main()
