"""
Carga única del maestro ipc_desagregados desde un Excel con el mismo formato que genera
scripts/export_ipc_maestro_a_excel.py (hoja ipc_desagregados).

Los scripts bajo update/ no modifican ipc_desagregados; solo ipc_desagregados_valores (p. ej. 036).

Uso (primera vez, sin rubros para ese país):
  python scripts/carga_inicial_ipc_desagregados_desde_export.py

Si ya hay datos y querés reemplazar maestro + borrar valores de ese país:
  python scripts/carga_inicial_ipc_desagregados_desde_export.py --reemplazar-pais

Por defecto lee ipc_desagregados_export.xlsx en la raíz del repo y id_pais=858.
"""

from __future__ import annotations

import argparse
import importlib.util
import os
import re
import sys
from pathlib import Path

import pandas as pd

_project_root = Path(__file__).resolve().parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from db.connection import execute_query, execute_update, insert_dataframe

NIVELES_OK = frozenset({"general", "division", "grupo", "clase", "subclase", "producto"})


def _norm_col(c) -> str:
    s = str(c).strip().lower()
    s = re.sub(r"\s+", "_", s)
    aliases = {"id_rubro": "id", "id_ipc": "id", "id_ipc_desagregado": "id"}
    return aliases.get(s, s)


def _code_cell(v):
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return None
    if isinstance(v, (int, float)):
        fv = float(v)
        if abs(fv - round(fv)) < 1e-9:
            return str(int(round(fv)))
        return str(fv).strip()
    s = str(v).strip()
    return s if s else None


def _ensure_tablas_ipc() -> None:
    p036 = _project_root / "update" / "direct" / "036_ipc_uy_desagregado_ine.py"
    spec = importlib.util.spec_from_file_location("_dcp_036_ipc_uy", p036)
    mod = importlib.util.module_from_spec(spec)
    if spec.loader is None:
        raise RuntimeError("No se pudo cargar el módulo 036")
    spec.loader.exec_module(mod)
    mod.ensure_tablas()


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Carga inicial de ipc_desagregados desde Excel (formato export maestro)"
    )
    ap.add_argument(
        "--input",
        type=Path,
        default=_project_root / "ipc_desagregados_export.xlsx",
        help="Ruta al .xlsx (default: ipc_desagregados_export.xlsx en la raíz)",
    )
    ap.add_argument("--pais", type=int, default=858, help="id_pais (filtra filas del Excel)")
    ap.add_argument(
        "--reemplazar-pais",
        action="store_true",
        help="Elimina valores y rubros de --pais en BD y vuelve a insertar el maestro desde el Excel",
    )
    args = ap.parse_args()
    os.chdir(_project_root)

    path = args.input.resolve()
    if not path.is_file():
        print(f"[ERROR] No existe {path}", file=sys.stderr)
        return 1

    pg = execute_query("SELECT 1 FROM pais_grupo WHERE id_pais = ?", (args.pais,))
    if not pg:
        print(f"[ERROR] id_pais={args.pais} no está en pais_grupo.", file=sys.stderr)
        return 1

    _ensure_tablas_ipc()

    try:
        df = pd.read_excel(path, sheet_name="ipc_desagregados", engine="openpyxl")
    except ValueError:
        df = pd.read_excel(path, sheet_name=0, engine="openpyxl")

    df.columns = [_norm_col(c) for c in df.columns]

    if "nivel" not in df.columns:
        print("[ERROR] El Excel debe incluir la columna nivel.", file=sys.stderr)
        return 1

    if "id_pais" not in df.columns:
        df["id_pais"] = args.pais
    else:
        df["id_pais"] = pd.to_numeric(df["id_pais"], errors="coerce").fillna(args.pais).astype(int)

    df = df[df["id_pais"] == args.pais].copy()
    if df.empty:
        print(f"[ERROR] No hay filas con id_pais={args.pais}.", file=sys.stderr)
        return 1

    for col in ("division", "grupo", "clase", "subclase", "producto"):
        if col in df.columns:
            df[col] = df[col].map(_code_cell)

    bad: list[tuple[int, str]] = []
    for i, row in df.iterrows():
        n = row.get("nivel")
        if n is None or (isinstance(n, float) and pd.isna(n)):
            bad.append((int(i), "nivel vacío"))
            continue
        nv = str(n).strip().lower()
        if nv not in NIVELES_OK:
            bad.append((int(i), f"nivel inválido: {nv!r}"))
    if bad:
        for idx, msg in bad[:20]:
            print(f"[ERROR] Fila Excel ~{idx + 2}: {msg}", file=sys.stderr)
        if len(bad) > 20:
            print(f"[ERROR] ... y {len(bad) - 20} filas más.", file=sys.stderr)
        return 1

    df["nivel"] = df["nivel"].map(lambda x: str(x).strip().lower())

    cnt = execute_query(
        "SELECT COUNT(*) AS c FROM ipc_desagregados WHERE id_pais = ?",
        (args.pais,),
    )
    n_exist = int(cnt[0]["c"]) if cnt else 0

    if n_exist > 0 and not args.reemplazar_pais:
        print(
            f"[ERROR] Ya hay {n_exist} rubros en ipc_desagregados para id_pais={args.pais}. "
            "Carga inicial: tabla ya poblada. Para sobrescribir desde el Excel usá --reemplazar-pais "
            "(se borran también ipc_desagregados_valores de ese país).",
            file=sys.stderr,
        )
        return 1

    if args.reemplazar_pais:
        ok, err, _ = execute_update(
            "DELETE FROM ipc_desagregados_valores WHERE id_pais = ?",
            (args.pais,),
        )
        if not ok:
            print(f"[ERROR] {err}", file=sys.stderr)
            return 1
        ok, err, _ = execute_update(
            "DELETE FROM ipc_desagregados WHERE id_pais = ?",
            (args.pais,),
        )
        if not ok:
            print(f"[ERROR] {err}", file=sys.stderr)
            return 1
        print(f"[INFO] Eliminados valores y rubros previos (id_pais={args.pais}).")

    cols_order = [
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
        "nivel",
    ]
    present = [c for c in cols_order if c in df.columns]
    if "id" in present and df["id"].isna().all():
        present.remove("id")

    df_ins = df[present].copy()

    if "descripcion" in df_ins.columns:
        df_ins["descripcion"] = df_ins["descripcion"].map(
            lambda x: None if x is None or (isinstance(x, float) and pd.isna(x)) else str(x).strip() or None
        )
    if "etiqueta" in df_ins.columns:
        df_ins["etiqueta"] = df_ins["etiqueta"].map(
            lambda x: None if x is None or (isinstance(x, float) and pd.isna(x)) else str(x).strip() or None
        )

    if "ponderacion" in df_ins.columns:
        def _pond(v):
            if v is None or (isinstance(v, float) and pd.isna(v)):
                return None
            try:
                return float(str(v).replace(",", ".").strip())
            except ValueError:
                return None

        df_ins["ponderacion"] = df_ins["ponderacion"].map(_pond)

    if "id" in df_ins.columns:
        df_ins["id"] = pd.to_numeric(df_ins["id"], errors="coerce")
        if df_ins["id"].isna().any():
            print("[ERROR] Columna id: hay valores vacíos o no numéricos.", file=sys.stderr)
            return 1
        df_ins["id"] = df_ins["id"].astype(int)

    insert_dataframe("ipc_desagregados", df_ins, if_exists="append", index=False)

    ok, err, _ = execute_update(
        "SELECT setval(pg_get_serial_sequence('ipc_desagregados', 'id'), "
        "COALESCE((SELECT MAX(id) FROM ipc_desagregados), 1))"
    )
    if not ok:
        print(f"[WARN] No se pudo ajustar la secuencia de id: {err}", file=sys.stderr)

    print(f"[OK] Insertados {len(df_ins)} rubros en ipc_desagregados (id_pais={args.pais}).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
