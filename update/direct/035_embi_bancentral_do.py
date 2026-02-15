# -*- coding: utf-8 -*-
"""
Script: embi_bancentral_do
--------------------------
Carga la Serie Historica Spread del EMBI (Banco Central Republica Dominicana)
desde update/historicos/embi.xlsx a maestro_precios.

- id_variable = 22 (EMBI Spread)
- Fila 2 del Excel = nombres de columnas (Fecha, Global, LATINO, DOM, Argentina, ...)
- Columnas Global y LATINO se omiten (no son pais).

Requisito: En maestro deben existir (id_variable=22, id_pais) para cada pais a cargar.
"""

import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from db.connection import execute_query, execute_query_single
from _helpers import insertar_en_bd_unificado

ID_VARIABLE_EMBI = 22
ARCHIVO_EMBI = PROJECT_ROOT / "update" / "historicos" / "embi.xlsx"

# Mapeo fijo: nombre de columna (fila 2 del Excel) -> id_pais (pais_grupo)
# Global y LATINO no se mapean (se omiten). Fecha = columna de fechas.
COLUMNA_A_ID_PAIS = {
    "DOM": 214,                        # Republica Dominicana
    "República Dominicana": 214,
    "Republica Dominicana": 214,
    "Argentina": 32,
    "Bolivia": 68,
    "Brasil": 76,
    "Chile": 152,
    "Colombia": 170,
    "Costa Rica": 188,
    "Ecuador": 218,
    "Salvador": 222,                   # El Salvador
    "El Salvador": 222,
    "Guatemala": 320,
    "Honduras": 340,
    "México": 484,
    "Mexico": 484,
    "Paraguay": 600,
    "Perú": 604,
    "Peru": 604,
    "Panamá": 591,
    "Panama": 591,
    "Uruguay": 858,
    "Venezuela": 862,
}


def listar_paises_maestro_embi():
    """Lista (id_pais, nombre_pais) que tienen id_variable=22 en maestro."""
    rows = execute_query(
        """
        SELECT m.id_pais, pg.nombre_pais_grupo
        FROM maestro m
        JOIN pais_grupo pg ON pg.id_pais = m.id_pais
        WHERE m.id_variable = ?
        ORDER BY pg.nombre_pais_grupo
        """,
        (ID_VARIABLE_EMBI,),
    )
    return [(r["id_pais"], r["nombre_pais_grupo"]) for r in rows] if rows else []


def existe_en_maestro(id_pais):
    """True si existe (id_variable=22, id_pais) en maestro."""
    row = execute_query_single(
        "SELECT 1 FROM maestro WHERE id_variable = ? AND id_pais = ?",
        (ID_VARIABLE_EMBI, id_pais),
    )
    return row is not None


def leer_embi_excel():
    """
    Lee embi.xlsx. Fila 2 (header=1) = nombres de columnas (Fecha, Global, LATINO, DOM, Argentina, ...).
    Columna 0 = fechas, resto = una columna por pais/indicador.
    """
    if not ARCHIVO_EMBI.exists():
        raise FileNotFoundError(f"No existe el archivo: {ARCHIVO_EMBI}")

    # header=1 usa la fila 2 (0-indexed row 1) como nombres de columnas
    df = pd.read_excel(ARCHIVO_EMBI, header=1, engine="openpyxl")
    if df.empty or len(df.columns) < 2:
        raise ValueError("El Excel no tiene suficientes columnas (se espera fecha + al menos un pais)")

    # Primera columna = fecha
    col_fecha = df.columns[0]
    df[col_fecha] = pd.to_datetime(df[col_fecha], errors="coerce")
    df = df.dropna(subset=[col_fecha])
    df["FECHA"] = df[col_fecha].dt.strftime("%Y-%m-%d")

    return df, col_fecha


def main():
    print("=" * 60)
    print("EMBI SPREAD - CARGA DESDE BANCENTRAL RD (id_variable=22)")
    print("=" * 60)

    # 1) Listar paises que tienen id_variable 22 en maestro
    paises = listar_paises_maestro_embi()
    if not paises:
        print("[WARN] No hay ningun (id_variable=22, id_pais) en maestro.")
        print("       Agrega registros en maestro para EMBI y vuelve a ejecutar.")
        return

    print("\n[INFO] Paises configurados en maestro para id_variable 22 (EMBI):")
    for id_pais, nombre in paises:
        print(f"   id_pais={id_pais}  {nombre}")
    print()

    # 2) Leer Excel (fila 2 = nombres de columnas)
    df, col_fecha = leer_embi_excel()

    # 3) Por cada columna: si esta en COLUMNA_A_ID_PAIS, cargar (y en maestro)
    columnas_valor = [c for c in df.columns if c != col_fecha and c != "FECHA"]
    insertados = 0
    omitidos = []

    for col in columnas_valor:
        col_nombre = str(col).strip() if col is not None else ""
        id_pais = COLUMNA_A_ID_PAIS.get(col_nombre) or COLUMNA_A_ID_PAIS.get(col)
        if id_pais is None:
            omitidos.append(col)  # Global, LATINO u otra sin mapeo
            continue
        if not existe_en_maestro(id_pais):
            omitidos.append(f"{col} (id_pais={id_pais} no en maestro)")
            continue

        serie = df[["FECHA", col]].copy()
        serie.columns = ["FECHA", "VALOR"]
        serie["VALOR"] = pd.to_numeric(serie["VALOR"], errors="coerce")
        serie = serie.dropna(subset=["VALOR", "FECHA"])
        if serie.empty:
            omitidos.append(f"{col} (sin datos)")
            continue

        print(f"\n[INFO] Insertando EMBI para {col} (id_pais={id_pais}, {serie.shape[0]} registros)...")
        try:
            insertar_en_bd_unificado(ID_VARIABLE_EMBI, id_pais, serie)
            insertados += 1
        except Exception as e:
            print(f"[ERROR] {col} id_pais={id_pais}: {e}")
            omitidos.append(f"{col} (error)")

    if omitidos:
        print("\n[INFO] Columnas omitidas (sin mapeo o sin datos):")
        for o in omitidos[:20]:
            print(f"   - {o}")
        if len(omitidos) > 20:
            print(f"   ... y {len(omitidos) - 20} mas")

    print("\n" + "=" * 60)
    print(f"[OK] EMBI cargado para {insertados} paises.")
    print("=" * 60)


if __name__ == "__main__":
    main()
