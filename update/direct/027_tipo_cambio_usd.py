"""
Script: tipo_cambio_usd
------------------------
Actualiza la base de datos con la serie de tipo de cambio USD/UYU.

Fuentes:
- BCCH F072.UYU.USD.N.O.D desde 2005-01-01 hasta el día anterior al primer dato BEVSA.
- BEVSA (update/historicos/dolar_bevsa_uyu.xlsx, CIERRE BCU BILLETE) desde que empieza el histórico local.

Ejecutá primero update/run_single.py dolar_bevsa_uyu para actualizar el Excel BEVSA.
"""

import os

import pandas as pd
from bcchapi import Siete
from _helpers import (
    completar_dias_faltantes,
    parse_fechas_uruguay_excel,
    validar_fechas_solo_nulas,
    insertar_en_bd_unificado,
)

# Configuración de origen de datos (BEVSA)
HISTORICOS_DIR = "update/historicos"
EXCEL_BEVSA = "dolar_bevsa_uyu.xlsx"
EXCEL_BEVSA_FALLBACK = "dolar_bevsa_uy.xlsx"

# BCCH backfill Uruguay
FECHA_INICIO = "2005-01-01"
BCCH_SERIE_UYU = "F072.UYU.USD.N.O.D"
BCCH_USER = "joaquin.forrisi@gmail.com"
BCCH_PASSWORD = "Joaquin.13"

# Configuración de base de datos
ID_VARIABLE = 20  # USD/LC (desde maestro_database.xlsx Sheet1_old)
ID_PAIS = 858  # Uruguay


def leer_excel_bevsa():
    """
    Lee el Excel de BEVSA con columna A (FECHA) y B (CIERRE BCU BILLETE).
    Usa dolar_bevsa_uyu.xlsx o dolar_bevsa_uy.xlsx como fallback.
    """
    base_dir = os.getcwd()
    ruta_principal = os.path.join(base_dir, HISTORICOS_DIR, EXCEL_BEVSA)
    ruta_fallback = os.path.join(base_dir, HISTORICOS_DIR, EXCEL_BEVSA_FALLBACK)

    ruta = ruta_principal if os.path.exists(ruta_principal) else ruta_fallback
    if not os.path.exists(ruta):
        raise FileNotFoundError(
            f"No se encontró {EXCEL_BEVSA} ni {EXCEL_BEVSA_FALLBACK} en {HISTORICOS_DIR}. "
            "Ejecutá primero: python update/run_single.py dolar_bevsa_uyu"
        )

    print(f"\n[INFO] Leyendo Excel BEVSA desde: {ruta}")
    tc_df = pd.read_excel(ruta, sheet_name=0, header=0)

    col_fecha = None
    col_valor = None
    for c in tc_df.columns:
        cstr = str(c).strip().upper()
        if "FECHA" in cstr or cstr == "FECHA":
            col_fecha = c
        if "CIERRE" in cstr and "BILLETE" in cstr:
            col_valor = c
    if col_fecha is None:
        col_fecha = tc_df.columns[0]
    if col_valor is None:
        raise ValueError(
            "No se encontró la columna 'CIERRE BCU BILLETE' en el Excel. "
            f"Columnas presentes: {list(tc_df.columns)}"
        )
    print(f"   Usando columna de valor: '{col_valor}' (CIERRE BCU BILLETE)")
    tc_df = tc_df[[col_fecha, col_valor]].copy()
    tc_df = tc_df.rename(columns={col_fecha: "FECHA", col_valor: "VALOR"})
    tc_df = tc_df.dropna(how="all")
    tc_df = tc_df.dropna(subset=["FECHA"])
    tc_df["FECHA"] = parse_fechas_uruguay_excel(tc_df["FECHA"])
    tc_df = tc_df.dropna(subset=["FECHA"])
    tc_df["VALOR"] = pd.to_numeric(tc_df["VALOR"], errors="coerce")
    tc_df = tc_df.dropna(subset=["VALOR"])

    print(f"[OK] Leídos {len(tc_df)} registros BEVSA válidos")
    return tc_df[["FECHA", "VALOR"]]


def extraer_bcch_uyu(fecha_inicio: str, fecha_fin: str) -> pd.DataFrame:
    """Extrae USD/UYU desde BCCH (serie F072.UYU.USD.N.O.D)."""
    print(f"\n[INFO] Extrayendo BCCH {BCCH_SERIE_UYU} ({fecha_inicio} a {fecha_fin})...")
    try:
        siete = Siete(BCCH_USER, BCCH_PASSWORD)
        df = siete.cuadro(
            series=[BCCH_SERIE_UYU],
            nombres=["tipo_cambio"],
            desde=fecha_inicio,
            hasta=fecha_fin,
        )
        if df is None or df.empty:
            print("[WARN] BCCH no devolvió datos para Uruguay")
            return pd.DataFrame(columns=["FECHA", "VALOR"])

        df = df.reset_index()
        if "index" in df.columns:
            df = df.rename(columns={"index": "FECHA"})
        col_valor = "tipo_cambio" if "tipo_cambio" in df.columns else df.columns[-1]
        df = df.rename(columns={col_valor: "VALOR"})
        df = df[["FECHA", "VALOR"]].copy()
        df["FECHA"] = pd.to_datetime(df["FECHA"], errors="coerce")
        df["VALOR"] = pd.to_numeric(df["VALOR"], errors="coerce")
        df = df.dropna(subset=["FECHA", "VALOR"])
        df = df.drop_duplicates(subset="FECHA", keep="last")
        df = df.sort_values("FECHA").reset_index(drop=True)
        print(
            f"[OK] BCCH Uruguay: {len(df)} registros "
            f"({df['FECHA'].min().strftime('%Y-%m-%d')} a {df['FECHA'].max().strftime('%Y-%m-%d')})"
        )
        return df
    except Exception as exc:
        print(f"[ERROR] Error al obtener datos BCCH Uruguay: {exc}")
        raise


def combinar_bcch_y_bevsa(bevsa_df: pd.DataFrame) -> pd.DataFrame:
    """BCCH hasta el día anterior al primer BEVSA; BEVSA gana en solapamiento."""
    bevsa_df = bevsa_df.copy()
    bevsa_min = bevsa_df["FECHA"].min()
    inicio_bcch = pd.Timestamp(FECHA_INICIO)

    if bevsa_min <= inicio_bcch:
        print("[INFO] BEVSA ya cubre desde 2005; no se usa backfill BCCH.")
        return bevsa_df

    fecha_fin_bcch = (bevsa_min - pd.Timedelta(days=1)).strftime("%Y-%m-%d")
    bcch_df = extraer_bcch_uyu(FECHA_INICIO, fecha_fin_bcch)
    if bcch_df.empty:
        print("[WARN] Sin backfill BCCH; se usa solo BEVSA.")
        return bevsa_df

    combined = pd.concat([bcch_df, bevsa_df], ignore_index=True)
    combined = combined.drop_duplicates(subset="FECHA", keep="last")
    combined = combined.sort_values("FECHA").reset_index(drop=True)
    print(
        f"[OK] Serie combinada: {len(combined)} registros "
        f"({combined['FECHA'].min().strftime('%Y-%m-%d')} a {combined['FECHA'].max().strftime('%Y-%m-%d')})"
    )
    print(f"   BCCH: {len(bcch_df)} | BEVSA: {len(bevsa_df)}")
    return combined


def obtener_tipo_cambio_usd():
    """Obtiene USD/UYU: BCCH (2005+) + BEVSA (histórico local)."""
    return combinar_bcch_y_bevsa(leer_excel_bevsa())


def main():
    print("=" * 60)
    print("ACTUALIZACION DE DATOS: TIPO DE CAMBIO USD/UYU (BCCH + BEVSA)")
    print("=" * 60)

    tc_df = obtener_tipo_cambio_usd()

    print("\n[INFO] Datos obtenidos:")
    print("\nPrimeros datos:")
    print(tc_df.head())
    print("\nÚltimos datos:")
    print(tc_df.tail())

    tc_df = completar_dias_faltantes(
        tc_df, columna_fecha="FECHA", columna_valor="VALOR", solo_lunes_a_viernes=True
    )
    tc_df = validar_fechas_solo_nulas(tc_df)

    if ID_VARIABLE is None or ID_PAIS is None:
        print("\n[ERROR] ID_VARIABLE e ID_PAIS deben estar configurados en el script.")
        return

    print("\n[INFO] Actualizando base de datos...")
    insertar_en_bd_unificado(ID_VARIABLE, ID_PAIS, tc_df)


if __name__ == "__main__":
    main()
