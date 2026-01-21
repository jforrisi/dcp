"""
Actualiza series de combustibles MIEM:
- Gasoil (id 20) columna AM
- Propano/Súpergas (id 21) columna BX

Flujo según 0_README:
- Validar fechas.
- Generar Excel de prueba (maestro + maestro_precios) en raíz.
- Mostrar resumen y pedir confirmación antes de insertar.
"""

import os
import sqlite3
import sys
from datetime import datetime

import pandas as pd

# Configuración
EXCEL_PATH = os.path.join("data_raw", "miem_derivados", "precios medios de derivados de petroleo con y sin impuestos.xls")
DB_NAME = "series_tiempo.db"
EXCEL_PRUEBA_NAME = "prueba_combustibles_miem.xlsx"

# Metadatos maestro
MAESTRO_GASOIL = {
    "id": 20,
    "nombre": "Gasoil",
    "tipo": "M",
    "fuente": "ANCAP",
    "periodicidad": "M",
    "unidad": "$ por litro",
    "categoria": "Combustibles",
    "activo": True,
    "moneda": "uyu",
}

MAESTRO_PROPANO = {
    "id": 21,
    "nombre": "Propano industrial (sin impuestos)",
    "tipo": "M",
    "fuente": "ANCAP",
    "periodicidad": "M",
    "unidad": "USD/ton",
    "categoria": "Combustibles",
    "activo": True,
    "moneda": "usd",
}


def crear_base_datos():
    """Crea tablas si no existen."""
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS maestro (
            id INTEGER PRIMARY KEY,
            nombre VARCHAR(255) NOT NULL,
            tipo CHAR(1) NOT NULL CHECK (tipo IN ('P','S','M')),
            fuente VARCHAR(255) NOT NULL,
            periodicidad CHAR(1) NOT NULL CHECK (periodicidad IN ('D','W','M')),
            unidad VARCHAR(100),
            categoria VARCHAR(255),
            activo BOOLEAN NOT NULL DEFAULT 1
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS maestro_precios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            maestro_id INTEGER NOT NULL,
            fecha DATE NOT NULL,
            valor NUMERIC(18,6) NOT NULL,
            FOREIGN KEY (maestro_id) REFERENCES maestro(id)
        )
        """
    )
    conn.commit()
    conn.close()


def leer_excel():
    """
    Lee el Excel principal usando:
    - Gasoil desde 'Hoja1' (columna 'gas oil - $/litro')
    - Propano industrial sin impuestos desde 'precio medio comb' columna CA
    """
    if not os.path.exists(EXCEL_PATH):
        raise FileNotFoundError(f"No se encuentra el Excel: {EXCEL_PATH}")

    # Gasoil desde Hoja1
    hoja1 = pd.read_excel(EXCEL_PATH, sheet_name="Hoja1", header=1)
    for col in ["fecha", "gas oil - $/litro"]:
        if col not in hoja1.columns:
            raise ValueError(f"Falta columna '{col}' en hoja Hoja1")
    df_g = hoja1[["fecha", "gas oil - $/litro"]].rename(columns={"gas oil - $/litro": "gasoil"})
    df_g["fecha"] = pd.to_datetime(df_g["fecha"], errors="coerce")
    df_g["gasoil"] = pd.to_numeric(df_g["gasoil"], errors="coerce")
    df_g = df_g.dropna(subset=["fecha", "gasoil"])

    # Propano industrial sin impuestos desde 'precio medio comb' (CA = índice 78 con header en fila 3)
    comb = pd.read_excel(EXCEL_PATH, sheet_name="precio medio comb", header=2)
    # Columnas base
    col_anio = comb.columns[0]
    col_mes = comb.columns[1]
    col_ca = comb.columns[78]  # CA (0-index)

    df_p = comb[[col_anio, col_mes, col_ca]].copy()
    df_p.columns = ["anio", "mes", "propano"]
    df_p["anio"] = pd.to_numeric(df_p["anio"], errors="coerce")
    df_p["mes"] = pd.to_numeric(df_p["mes"], errors="coerce")
    df_p["propano"] = pd.to_numeric(df_p["propano"], errors="coerce")
    df_p = df_p.dropna(subset=["anio", "mes", "propano"])
    df_p["fecha"] = pd.to_datetime(
        df_p["anio"].astype(int).astype(str) + "-" + df_p["mes"].astype(int).astype(str) + "-01",
        errors="coerce",
    )
    df_p = df_p.dropna(subset=["fecha", "propano"])

    # Merge por fecha (outer) para no perder meses
    out = pd.merge(df_g, df_p[["fecha", "propano"]], on="fecha", how="outer")
    out = out.sort_values("fecha")
    return out[["fecha", "gasoil", "propano"]]


def preparar_precios(df: pd.DataFrame, maestro_id: int, columna_valor: str) -> pd.DataFrame:
    out = df[["fecha", columna_valor]].copy()
    out = out.dropna(subset=[columna_valor])
    out["maestro_id"] = maestro_id
    out = out[["maestro_id", "fecha", columna_valor]]
    out.columns = ["maestro_id", "fecha", "valor"]
    return out


def generar_excel_prueba(df_maestro: pd.DataFrame, df_precios: pd.DataFrame) -> str:
    base_path = os.path.join(os.getcwd(), EXCEL_PRUEBA_NAME)
    excel_path = base_path
    try:
        with pd.ExcelWriter(excel_path, engine="openpyxl") as writer:
            df_maestro.to_excel(writer, sheet_name="maestro", index=False)
            df_precios.to_excel(writer, sheet_name="maestro_precios", index=False)
        return excel_path
    except PermissionError:
        # Si el archivo está abierto/bloqueado, generar uno con timestamp
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        name, ext = os.path.splitext(EXCEL_PRUEBA_NAME)
        excel_path = os.path.join(os.getcwd(), f"{name}_{ts}{ext}")
        with pd.ExcelWriter(excel_path, engine="openpyxl") as writer:
            df_maestro.to_excel(writer, sheet_name="maestro", index=False)
            df_precios.to_excel(writer, sheet_name="maestro_precios", index=False)
        return excel_path


def mostrar_resumen(df_maestro: pd.DataFrame, df_precios: pd.DataFrame):
    print("\n" + "=" * 60)
    print("RESUMEN DE DATOS A INSERTAR")
    print("=" * 60)
    print("\nTABLA: maestro")
    print("-" * 60)
    print(df_maestro.to_string(index=False))
    print("\nTABLA: maestro_precios")
    print("-" * 60)
    print(f"Total de registros: {len(df_precios)}")
    print("\nPrimeros 5 registros:")
    print(df_precios.head().to_string(index=False))
    print("\nÚltimos 5 registros:")
    print(df_precios.tail().to_string(index=False))
    print(f"\nRango de fechas: {df_precios['fecha'].min()} a {df_precios['fecha'].max()}")
    print(
        f"Valores: min={df_precios['valor'].min():.2f}, "
        f"max={df_precios['valor'].max():.2f}, "
        f"promedio={df_precios['valor'].mean():.2f}"
    )
    print("=" * 60)


def solicitar_confirmacion(excel_path: str):
    print("\n" + "=" * 60)
    print("CONFIRMACION DEL USUARIO")
    print("=" * 60)
    print(f"Archivo Excel generado para validación: {excel_path}")
    print("Revisá el Excel (hojas 'maestro' y 'maestro_precios').")
    resp = input("¿Confirmás la inserción en la base de datos? (sí/no): ").strip().lower()
    if resp not in ["sí", "si", "yes", "y", "s"]:
        print("[INFO] Inserción cancelada por el usuario. No se realizaron cambios.")
        sys.exit(0)


def insertar(df_maestro: pd.DataFrame, df_precios: pd.DataFrame):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    try:
        for _, row in df_maestro.iterrows():
            cur.execute(
                """
                INSERT OR IGNORE INTO maestro (id, nombre, tipo, fuente, periodicidad, unidad, categoria, activo)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    int(row["id"]),
                    row["nombre"],
                    row["tipo"],
                    row["fuente"],
                    row["periodicidad"],
                    row["unidad"],
                    row["categoria"],
                    row["activo"],
                ),
            )
        conn.commit()

        # Evitar duplicados en maestro_precios
        cur.execute(
            "SELECT maestro_id, fecha FROM maestro_precios WHERE maestro_id IN (?, ?)",
            (MAESTRO_GASOIL["id"], MAESTRO_PROPANO["id"]),
        )
        existentes = {(r[0], r[1]) for r in cur.fetchall()}
        df_new = df_precios[~df_precios.apply(lambda r: (r["maestro_id"], str(r["fecha"])) in {(mid, str(f)) for mid, f in existentes}, axis=1)]
        if len(df_new) == 0:
            print("[INFO] Todos los registros ya existían, no se insertan nuevos.")
        else:
            df_new.to_sql("maestro_precios", conn, if_exists="append", index=False)
            print(f"[OK] Insertados {len(df_new)} registro(s) en maestro_precios")
        conn.commit()
    finally:
        conn.close()


def main():
    print("=" * 60)
    print("ACTUALIZACION DE DATOS: COMBUSTIBLES MIEM (Gasoil, Propano)")
    print("=" * 60)
    crear_base_datos()
    df_raw = leer_excel()
    print(f"[INFO] Registros crudos: {len(df_raw)}")
    print(df_raw.head())
    print(df_raw.tail())

    df_gasoil = preparar_precios(df_raw, MAESTRO_GASOIL["id"], "gasoil")
    df_propano = preparar_precios(df_raw, MAESTRO_PROPANO["id"], "propano")
    df_precios = pd.concat([df_gasoil, df_propano], ignore_index=True)

    df_maestro = pd.DataFrame([MAESTRO_GASOIL, MAESTRO_PROPANO])

    excel_path = generar_excel_prueba(df_maestro, df_precios)
    mostrar_resumen(df_maestro, df_precios)
    solicitar_confirmacion(excel_path)
    insertar(df_maestro, df_precios)
    print(f"[OK] Datos insertados en {DB_NAME}")


if __name__ == "__main__":
    main()
