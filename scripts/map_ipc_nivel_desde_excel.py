"""
Exporta un CSV con los rubros del cuadro INE y la columna `nivel` inferida
(misma lógica que update/direct/036_ipc_uy_desagregado_ine.py).

No usa base de datos: sirve para revisar en Excel que el mapeo COICOP coincide
con lo que ves en el archivo fuente.

Uso (desde la raíz del repo):
  python scripts/map_ipc_nivel_desde_excel.py
  python scripts/map_ipc_nivel_desde_excel.py --input ruta/al/archivo.xlsx --out salida.csv
"""

from __future__ import annotations

import argparse
import importlib.util
import sys
from pathlib import Path

_project_root = Path(__file__).resolve().parent.parent


def _load_036():
    path = _project_root / "update" / "direct" / "036_ipc_uy_desagregado_ine.py"
    spec = importlib.util.spec_from_file_location("ipc_uy_desagregado_ine_036", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"No se pudo cargar {path}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def main() -> int:
    m = _load_036()
    default_xlsx = _project_root / m.HISTORICOS_REL

    ap = argparse.ArgumentParser(description="CSV de rubros IPC + nivel inferido (sin BD)")
    ap.add_argument(
        "--input",
        type=Path,
        default=default_xlsx,
        help=f"Excel INE (default: {default_xlsx})",
    )
    ap.add_argument(
        "--out",
        type=Path,
        default=_project_root / "update" / "historicos" / "ipc_nivel_mapeo.csv",
        help="CSV de salida (UTF-8 con BOM para Excel)",
    )
    args = ap.parse_args()

    if not args.input.is_file():
        print(f"[ERROR] No existe el archivo: {args.input}", file=sys.stderr)
        return 1

    wide, _date_cols = m.leer_excel(args.input)
    _wide_f, rubros = m.preparar_rubros(wide)

    cols = [
        "orden",
        "division",
        "grupo",
        "clase",
        "subclase",
        "producto",
        "descripcion",
        "ponderacion",
        "etiqueta",
        "nivel",
    ]
    out = rubros.copy()
    out.insert(0, "orden", range(1, len(out) + 1))

    args.out.parent.mkdir(parents=True, exist_ok=True)
    out[cols].to_csv(args.out, index=False, encoding="utf-8-sig")

    print(f"[OK] {len(out)} filas -> {args.out}")
    print("Columnas: orden, codigos COICOP, descripcion, ponderacion, etiqueta, nivel")
    return 0


if __name__ == "__main__":
    sys.exit(main())
