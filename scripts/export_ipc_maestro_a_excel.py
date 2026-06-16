"""
Exporta a Excel las tablas IPC desagregado (maestro + valores mensuales).

Uso (desde la raíz del repo, con DATABASE_URL en .env):
  python scripts/export_ipc_maestro_a_excel.py
  python scripts/export_ipc_maestro_a_excel.py --out C:\\temp\\ipc.xlsx --pais 858
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

_project_root = Path(__file__).resolve().parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from sqlalchemy import text

from db.connection import get_db_engine


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--out",
        type=Path,
        default=_project_root / "ipc_desagregados_export.xlsx",
        help="Ruta del .xlsx de salida",
    )
    ap.add_argument("--pais", type=int, default=858, help="id_pais a filtrar (default Uruguay)")
    ap.add_argument(
        "--solo-maestro",
        action="store_true",
        help="Solo hoja maestro (no ipc_desagregados_valores)",
    )
    args = ap.parse_args()

    engine = get_db_engine()
    idp = args.pais

    cols_q = text(
        "SELECT column_name FROM information_schema.columns "
        "WHERE table_schema = 'public' AND table_name = 'ipc_desagregados' ORDER BY ordinal_position"
    )
    with engine.connect() as conn:
        colrows = conn.execute(cols_q).fetchall()
    have = {r[0] for r in colrows}
    base_cols = [
        "id",
        "id_pais",
        "division",
        "grupo",
        "clase",
        "subclase",
        "producto",
        "descripcion",
        "etiqueta",
        "ponderacion",
    ]
    select_cols = [c for c in base_cols if c in have]
    if "nivel" in have:
        select_cols.append("nivel")
    if not select_cols:
        print("[ERROR] Tabla ipc_desagregados no encontrada o sin columnas esperadas.", file=sys.stderr)
        return 1

    col_sql = ", ".join(select_cols)
    q_maestro = text(
        f"SELECT {col_sql} FROM ipc_desagregados WHERE id_pais = :id "
        "ORDER BY division, grupo, clase, subclase, producto"
    )
    df_m = pd.read_sql_query(q_maestro, engine, params={"id": idp})

    args.out = args.out.resolve()
    args.out.parent.mkdir(parents=True, exist_ok=True)

    with pd.ExcelWriter(args.out, engine="openpyxl") as w:
        df_m.to_excel(w, sheet_name="ipc_desagregados", index=False)
        if not args.solo_maestro:
            q_val = text(
                "SELECT v.id, v.id_ipc_desagregado, v.id_pais, v.fecha, v.valor "
                "FROM ipc_desagregados_valores v WHERE v.id_pais = :id ORDER BY v.fecha, v.id_ipc_desagregado"
            )
            df_v = pd.read_sql_query(q_val, engine, params={"id": idp})
            df_v.to_excel(w, sheet_name="ipc_desagregados_valores", index=False)

    extra = "" if args.solo_maestro else f" + valores ({len(df_v)} filas)"
    print(f"[OK] {len(df_m)} rubros maestro{extra} -> {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
