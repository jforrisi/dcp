"""
Script: ipc_uy_desagregado_ine (direct)
---------------------------------------
1) Crea tablas ipc_desagregados / ipc_desagregados_valores si no existen (ADD COLUMN idempotente).
2) Lee update/historicos/ipc_uy_div_gr_cl_sc_pr.xlsx (Cuadro INE, header fila 11).

Solo modifica ipc_desagregados_valores. El maestro ipc_desagregados se carga una sola vez fuera de
update/ (mismo formato que ipc_desagregados_export.xlsx):
  python scripts/carga_inicial_ipc_desagregados_desde_export.py

Ejecutar antes: python update/download/ipc_uy_desagregado_ine.py
"""

from __future__ import annotations

import os
import re
import sys
import unicodedata
from datetime import date
from pathlib import Path

import pandas as pd

_project_root = Path(__file__).resolve().parent.parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from db.connection import execute_query, execute_update, insert_dataframe

ID_PAIS = 858
HISTORICOS_REL = "update/historicos/ipc_uy_div_gr_cl_sc_pr.xlsx"
HEADER_ROW_ZERO_BASED = 10  # fila 11 en Excel
MAX_ETIQUETA = 42

DDL_STATEMENTS = [
    """
    CREATE TABLE IF NOT EXISTS ipc_desagregados (
        id SERIAL PRIMARY KEY,
        id_pais INTEGER NOT NULL DEFAULT 858 REFERENCES pais_grupo(id_pais),
        division VARCHAR(32),
        grupo VARCHAR(32),
        clase VARCHAR(32),
        subclase VARCHAR(32),
        producto VARCHAR(64),
        descripcion TEXT,
        etiqueta VARCHAR(96),
        ponderacion NUMERIC(18, 8),
        nivel VARCHAR(16) NOT NULL
    )
    """,
    """
    CREATE UNIQUE INDEX IF NOT EXISTS uq_ipc_desagregados_natural
        ON ipc_desagregados (
            id_pais,
            COALESCE(division, ''),
            COALESCE(grupo, ''),
            COALESCE(clase, ''),
            COALESCE(subclase, ''),
            COALESCE(producto, '')
        )
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_ipc_desagregados_id_pais ON ipc_desagregados(id_pais)
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_ipc_desagregados_pais_nivel
        ON ipc_desagregados (id_pais, nivel)
    """,
    """
    CREATE TABLE IF NOT EXISTS ipc_desagregados_valores (
        id SERIAL PRIMARY KEY,
        id_ipc_desagregado INTEGER NOT NULL REFERENCES ipc_desagregados(id) ON DELETE CASCADE,
        id_pais INTEGER NOT NULL DEFAULT 858 REFERENCES pais_grupo(id_pais),
        fecha DATE NOT NULL,
        valor NUMERIC(18, 6) NOT NULL,
        UNIQUE (id_ipc_desagregado, fecha)
    )
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_ipc_desag_valores_rubro_fecha
        ON ipc_desagregados_valores(id_ipc_desagregado, fecha)
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_ipc_desag_valores_pais_fecha
        ON ipc_desagregados_valores(id_pais, fecha)
    """,
]


def _fold_key(s: str) -> str:
    """Clave normalizada (mayúsculas, sin acentos) para matchear descripciones del INE."""
    if not s:
        return ""
    n = unicodedata.normalize("NFKD", s)
    a = "".join(c for c in n if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", a).upper().strip()


# Mapa exacto: descripción INE (variantes) -> etiqueta corta para gráficos
_ETIQUETAS_EXACTAS: dict[str, str] = {}


def _reg_etq(etiqueta: str, *textos: str) -> None:
    for t in textos:
        _ETIQUETAS_EXACTAS[_fold_key(t)] = etiqueta


_reg_etq("IPC general", "GENERAL")
_reg_etq("Alim. y beb. s/alcohol", "ALIMENTOS Y BEBIDAS NO ALCOHÓLICAS", "ALIMENTOS Y BEBIDAS NO ALCOHOLICAS")
_reg_etq("Beb. alc., tabaco y narc.", "BEBIDAS ALCOHÓLICAS, TABACO Y NARCÓTICOS", "BEBIDAS ALCOHOLICAS, TABACO Y NARCOTICOS")
_reg_etq("Ropa y calzado", "ROPA Y CALZADO")
_reg_etq("Vivienda, agua, elect., gas", "VIVIENDA, AGUA, ELECTRICIDAD, GAS Y OTROS COMBUSTIBLES")
_reg_etq(
    "Mobil., enseres y art. hog.",
    "MOBILIARIO, ENSERES DOMÉSTICOS y DEMÁS ARTÍCULOS REGULARES DE LOS HOGARES",
    "MOBILIARIO, ENSERES DOMESTICOS y DEMAS ARTICULOS REGULARES DE LOS HOGARES",
    "MOBILIARIO, ENSERES DOMÉSTICOS Y DEMÁS ARTÍCULOS REGULARES DE LOS HOGARES",
)
_reg_etq("Salud", "SALUD")
_reg_etq("Transporte", "TRANSPORTE")
_reg_etq("Inform. y comunic.", "INFORMACIÓN Y COMUNICACIÓN", "INFORMACION Y COMUNICACION")
_reg_etq("Recreac., dep. y cult.", "RECREACIÓN, DEPORTE Y CULTURA", "RECREACION, DEPORTE Y CULTURA")
_reg_etq("Educación", "SERVICIOS DE EDUCACIÓN", "SERVICIOS DE EDUCACION")
_reg_etq("Restaur. y alojam.", "RESTAURANTES Y SERVICIOS DE ALOJAMIENTO")
_reg_etq("Seguros y finanzas", "SEGUROS Y SERVICIOS FINANCIEROS")
_reg_etq(
    "Cuid. pers., prot. soc., bienes div.",
    "CUIDADO PERSONAL, PROTECCIÓN SOCIAL Y BIENES DIVERSOS",
    "CUIDADO PERSONAL, PROTECCION SOCIAL Y BIENES DIVERSOS",
)

# Si el Excel trae encoding raro, igual matchear por trozos clave
_ETIQUETAS_FUZZY: list[tuple[tuple[str, ...], str]] = [
    (("CUIDADO PERSONAL", "PROTECC", "BIENES DIVERSOS"), "Cuid. pers., prot. soc., bienes div."),
    (("ALIMENTOS", "BEBIDAS", "ALCOH"), "Alim. y beb. s/alcohol"),
    (("BEBIDAS ALCOH", "TABACO"), "Beb. alc., tabaco y narc."),
    (("MOBILIARIO", "ENSERES", "HOGAR"), "Mobil., enseres y art. hog."),
    (("VIVIENDA", "ELECTRICIDAD", "COMBUST"), "Vivienda, agua, elect., gas"),
    (("INFORMACION", "COMUNICACION"), "Inform. y comunic."),
    (("RECREACION", "DEPORTE", "CULTURA"), "Recreac., dep. y cult."),
    (("SERVICIOS", "EDUCACION"), "Educación"),
]

_STOPWORDS = frozenset({"Y", "E", "DE", "DEL", "LA", "LAS", "LOS", "EN", "A", "O"})


def _palabra_corta_grafico(p: str, max_sin_abrev: int = 7) -> str:
    """Abrevia palabras largas manteniendo el casing del INE (mejor para leyendas)."""
    pu = p.upper()
    if pu in _STOPWORDS:
        return p.lower()
    if len(p) <= max_sin_abrev:
        return p
    n = min(5, max(3, len(p) // 2))
    return p[:n] + "."


def _acortar_fragmento(frag: str, lim: int) -> str:
    palabras = frag.split()
    if not palabras:
        return ""
    partes = [_palabra_corta_grafico(p) for p in palabras]
    s = " ".join(partes)
    if len(s) > lim:
        return s[: max(lim - 1, 8)] + "…"
    return s


def _acortar_descripcion_automatica(s: str, max_len: int) -> str:
    s = s.strip()
    partes = [p.strip() for p in re.split(r"[,;]", s) if p.strip()]
    if len(partes) >= 2:
        trozos = [_acortar_fragmento(p, 20) for p in partes[:4]]
        out = ", ".join(trozos)
        if len(partes) > 4:
            out = out + "…"
        if len(out) > max_len:
            return out[: max_len - 1] + "…"
        return out
    return _acortar_fragmento(s, max_len)


def generar_etiqueta(descripcion: str | None) -> str | None:
    """Nombre corto para leyendas; `descripcion` sigue siendo el texto oficial del INE."""
    if not descripcion:
        return None
    d = descripcion.strip()
    fk = _fold_key(d)
    if fk in _ETIQUETAS_EXACTAS:
        return _ETIQUETAS_EXACTAS[fk]
    for partes, etq in _ETIQUETAS_FUZZY:
        if all(p in fk for p in partes):
            return etq
    if len(d) <= MAX_ETIQUETA:
        return d
    return _acortar_descripcion_automatica(d, MAX_ETIQUETA)


def _blank(v) -> bool:
    if v is None:
        return True
    if isinstance(v, float) and pd.isna(v):
        return True
    s = str(v).strip()
    return s == "" or s.lower() == "nan" or s == "_____"


def _norm_code(v) -> str | None:
    if _blank(v):
        return None
    if isinstance(v, str):
        s = v.strip()
        return s if s else None
    if isinstance(v, (int, float)):
        if isinstance(v, float) and pd.isna(v):
            return None
        fv = float(v)
        if abs(fv - round(fv)) < 1e-9:
            return str(int(round(fv)))
        return str(fv)
    s = str(v).strip()
    return s if s else None


def inferir_nivel(
    division: str | None,
    grupo: str | None,
    clase: str | None,
    subclase: str | None,
    producto: str | None,
) -> str:
    """
    Nivel para documentación / CSV de mapeo (alineado a maestro manual: general, division, grupo, …).
    IPC general = división 99 sin códigos inferiores.
    """
    if division is not None and str(division).strip() == "99":
        if grupo is None and clase is None and subclase is None and producto is None:
            return "general"
    if producto is not None:
        return "producto"
    if subclase is not None:
        return "subclase"
    if clase is not None:
        return "clase"
    if grupo is not None:
        return "grupo"
    if division is not None:
        return "division"
    return "division"


def _norm_ponderacion(v) -> float | None:
    if _blank(v):
        return None
    s = str(v).strip().replace(",", ".")
    if s == "_____" or s == "":
        return None
    try:
        return float(s)
    except ValueError:
        return None


def _norm_descripcion(v) -> str | None:
    if _blank(v):
        return None
    return str(v).strip()


def ensure_tablas() -> None:
    for stmt in DDL_STATEMENTS:
        ok, err, _ = execute_update(stmt.strip())
        if not ok:
            raise RuntimeError(f"DDL falló: {err}")
    ok, err, _ = execute_update(
        "ALTER TABLE ipc_desagregados ADD COLUMN IF NOT EXISTS etiqueta VARCHAR(96)"
    )
    if not ok:
        raise RuntimeError(f"ALTER etiqueta falló: {err}")
    ok, err, _ = execute_update(
        "ALTER TABLE ipc_desagregados ADD COLUMN IF NOT EXISTS nivel VARCHAR(16)"
    )
    if not ok:
        raise RuntimeError(f"ALTER nivel falló: {err}")
    # No backfill de nivel: el maestro y la columna nivel se mantienen fuera de este script.
    ok, err, _ = execute_update(
        "CREATE INDEX IF NOT EXISTS idx_ipc_desagregados_pais_nivel "
        "ON ipc_desagregados (id_pais, nivel)"
    )
    if not ok:
        raise RuntimeError(f"CREATE INDEX idx_ipc_desagregados_pais_nivel falló: {err}")


def leer_excel(path: Path) -> tuple[pd.DataFrame, list]:
    df = pd.read_excel(path, sheet_name=0, header=HEADER_ROW_ZERO_BASED, engine="openpyxl")
    if df.shape[1] < 8:
        raise ValueError("Excel: se esperan al menos 8 columnas (metadatos + fechas).")

    meta = df.iloc[:, :7].copy()
    meta.columns = [
        "division",
        "grupo",
        "clase",
        "subclase",
        "producto",
        "descripcion",
        "ponderacion",
    ]
    date_block = df.iloc[:, 7:]
    wide = pd.concat([meta, date_block], axis=1)
    date_cols = list(date_block.columns)
    return wide, date_cols


def preparar_rubros(wide: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Devuelve (wide_filtrado, rubros) con la misma cantidad de filas alineadas."""
    keep_idx: list[int] = []
    rubro_rows: list[dict] = []
    for i in range(len(wide)):
        r = wide.iloc[i]
        div = _norm_code(r["division"])
        gr = _norm_code(r["grupo"])
        cl = _norm_code(r["clase"])
        sc = _norm_code(r["subclase"])
        pr = _norm_code(r["producto"])
        desc = _norm_descripcion(r["descripcion"])
        pond = _norm_ponderacion(r["ponderacion"])

        sin_codigos = all(x is None for x in (div, gr, cl, sc, pr))
        if sin_codigos and desc and "GENERAL" in desc.upper():
            div = "99"
            gr = cl = sc = pr = None

        if sin_codigos and not desc:
            continue
        if not sin_codigos and div is None and desc is None:
            continue

        keep_idx.append(i)
        rubro_rows.append(
            {
                "id_pais": ID_PAIS,
                "division": div,
                "grupo": gr,
                "clase": cl,
                "subclase": sc,
                "producto": pr,
                "descripcion": desc,
                "etiqueta": generar_etiqueta(desc),
                "ponderacion": pond,
                "nivel": inferir_nivel(div, gr, cl, sc, pr),
            }
        )
    wide_f = wide.iloc[keep_idx].reset_index(drop=True)
    rubros = pd.DataFrame(rubro_rows)
    return wide_f, rubros


def validar_ponderaciones_division(df_rubros: pd.DataFrame) -> None:
    """Suma ponderación de filas solo-división (excl. 99) ≈ 1 o 100."""

    def _es_division_general(d) -> bool:
        if d is None or (isinstance(d, float) and pd.isna(d)):
            return False
        return str(d).strip() == "99"

    mask = (
        df_rubros["division"].notna()
        & ~df_rubros["division"].map(_es_division_general)
        & df_rubros["grupo"].isna()
    )
    sub = df_rubros.loc[mask, "ponderacion"].dropna()
    if sub.empty:
        print("[WARN] No hay filas solo-división con ponderación; se omite chequeo de suma.")
        return
    s = float(sub.sum())
    ok_frac = abs(s - 1.0) <= 0.02
    ok_pct = abs(s - 100.0) <= 2.0
    if not ok_frac and not ok_pct:
        raise ValueError(
            f"Suma de ponderaciones (solo división, excl. 99) = {s:.6f}; "
            "se esperaba ~1.0 (fracción) o ~100 (porcentaje)."
        )
    print(f"[OK] Suma ponderaciones solo-división (excl. 99) = {s:.6f}")


def _key_part(v) -> str:
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return ""
    s = str(v).strip()
    return s if s else ""


def construir_valores(wide_f: pd.DataFrame, rubros: pd.DataFrame, date_cols: list) -> pd.DataFrame:
    key_to_id: dict[tuple, int] = {}
    loaded = execute_query(
        "SELECT id, division, grupo, clase, subclase, producto FROM ipc_desagregados WHERE id_pais = ?",
        (ID_PAIS,),
    )
    for row in loaded:
        k = (
            ID_PAIS,
            _key_part(row.get("division")),
            _key_part(row.get("grupo")),
            _key_part(row.get("clase")),
            _key_part(row.get("subclase")),
            _key_part(row.get("producto")),
        )
        key_to_id[k] = row["id"]

    records = []
    sin_match = 0
    for i in range(len(wide_f)):
        r = wide_f.iloc[i]
        kr = rubros.iloc[i]
        key = (
            ID_PAIS,
            _key_part(kr.get("division")),
            _key_part(kr.get("grupo")),
            _key_part(kr.get("clase")),
            _key_part(kr.get("subclase")),
            _key_part(kr.get("producto")),
        )
        if key not in key_to_id:
            sin_match += 1
            continue
        rid = key_to_id[key]
        for col in date_cols:
            raw = r[col]
            if _blank(raw):
                continue
            try:
                val = float(str(raw).replace(",", "."))
            except ValueError:
                continue
            if pd.isna(val):
                continue
            if hasattr(col, "year") and hasattr(col, "month"):
                ts = pd.Timestamp(col)
            else:
                ts = pd.to_datetime(col, errors="coerce")
            if pd.isna(ts):
                continue
            fd = date(int(ts.year), int(ts.month), 1)
            records.append(
                {
                    "id_ipc_desagregado": rid,
                    "id_pais": ID_PAIS,
                    "fecha": fd,
                    "valor": val,
                }
            )
    if sin_match:
        print(f"[WARN] {sin_match} filas del Excel no coinciden con ningún rubro del maestro en BD (omitidas).")
    return pd.DataFrame(records)


def main():
    os.chdir(_project_root)
    path = _project_root / HISTORICOS_REL
    if not path.is_file():
        print(f"[ERROR] No existe {path}. Ejecutá: python update/download/ipc_uy_desagregado_ine.py")
        sys.exit(1)

    pg = execute_query("SELECT 1 FROM pais_grupo WHERE id_pais = ?", (ID_PAIS,))
    if not pg:
        print(f"[ERROR] id_pais={ID_PAIS} no está en pais_grupo. Cargá referencias antes.")
        sys.exit(1)

    print("[INFO] Asegurando tablas IPC desagregado...")
    ensure_tablas()

    cnt = execute_query(
        "SELECT COUNT(*) AS c FROM ipc_desagregados WHERE id_pais = ?",
        (ID_PAIS,),
    )
    n_m = int(cnt[0]["c"]) if cnt else 0
    if n_m == 0:
        print(
            "[ERROR] No hay rubros en ipc_desagregados para id_pais=%s. "
            "Cargá el maestro una vez con: python scripts/carga_inicial_ipc_desagregados_desde_export.py"
            % ID_PAIS
        )
        sys.exit(1)
    print(f"[INFO] Maestro en BD: {n_m} rubros (no se modifica en esta corrida).")

    print(f"[INFO] Leyendo {path}")
    wide, date_cols = leer_excel(path)
    wide_f, rubros = preparar_rubros(wide)

    valores = construir_valores(wide_f, rubros, date_cols)
    if valores.empty:
        print(
            "[ERROR] No se generaron valores mensuales. "
            "Revisá que las claves COICOP del Excel coincidan con ipc_desagregados."
        )
        sys.exit(1)

    ok, err, _ = execute_update(
        "DELETE FROM ipc_desagregados_valores WHERE id_pais = ?",
        (ID_PAIS,),
    )
    if not ok:
        raise RuntimeError(err)
    print("[OK] ipc_desagregados_valores: datos previos id_pais=%s eliminados." % ID_PAIS)

    insert_dataframe("ipc_desagregados_valores", valores, if_exists="append", index=False)
    print(f"[OK] Insertados {len(valores)} registros en ipc_desagregados_valores")


if __name__ == "__main__":
    main()
