"""
Aplica migration_ipc_desagregados_nivel.sql contra PostgreSQL (DATABASE_URL en .env).
Idempotente: ADD COLUMN IF NOT EXISTS, DROP CONSTRAINT IF EXISTS, CREATE INDEX IF NOT EXISTS.

Uso desde la raíz del repo:
  python scripts/run_migration_ipc_nivel.py
"""
from __future__ import annotations

import sys
from pathlib import Path

root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root))

from db.connection import get_db_connection

SQL_PATH = Path(__file__).resolve().parent / "migration_ipc_desagregados_nivel.sql"


def _statements(sql_text: str) -> list[str]:
    out: list[str] = []
    buf: list[str] = []
    for line in sql_text.splitlines():
        stripped = line.strip()
        if stripped.startswith("--"):
            continue
        buf.append(line)
        if stripped.endswith(";"):
            stmt = "\n".join(buf).strip()
            if stmt:
                out.append(stmt)
            buf = []
    if buf:
        s = "\n".join(buf).strip()
        if s:
            out.append(s)
    return out


def main() -> int:
    if not SQL_PATH.is_file():
        print(f"[ERROR] No existe {SQL_PATH}", file=sys.stderr)
        return 1
    raw = SQL_PATH.read_text(encoding="utf-8")
    stmts = _statements(raw)
    if not stmts:
        print("[ERROR] No se parsearon sentencias SQL.", file=sys.stderr)
        return 1

    conn = get_db_connection()
    try:
        cur = conn.cursor()
        for i, st in enumerate(stmts, 1):
            try:
                cur.execute(st)
            except Exception as e:
                print(f"[ERROR] Sentencia {i}/{len(stmts)} falló:\n{st[:200]}...\n{e}", file=sys.stderr)
                conn.rollback()
                return 1
        conn.commit()
        print(f"[OK] Migración IPC nivel: {len(stmts)} sentencias aplicadas.")
    finally:
        conn.close()

    # Verificación rápida
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_schema = 'public' AND table_name = 'ipc_desagregados' "
            "AND column_name = 'nivel'"
        )
        if not cur.fetchone():
            print("[WARN] Columna nivel no aparece en information_schema.", file=sys.stderr)
            return 1
        cur.execute("SELECT COUNT(*) AS n, COUNT(nivel) AS con_nivel FROM ipc_desagregados")
        row = cur.fetchone()
        print(f"[OK] ipc_desagregados: filas={row['n']}, con nivel={row['con_nivel']}")
    finally:
        conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
