"""
Seed de tipo_serie y asignación Original a todas las variables.

Crea/actualiza en tipo_serie:
  1 = Original
  2 = Desestacionalizado
  3 = Tendencia-Ciclo

Y pone id_tipo_serie = 1 (Original) en todas las variables existentes.

Uso (con DATABASE_URL ya definida, ej. Azure):
  python scripts/seed_tipo_serie.py
"""
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Cargar .env si existe (como db/connection.py)
try:
    from dotenv import load_dotenv
    load_dotenv(PROJECT_ROOT / ".env")
except ImportError:
    pass

DATABASE_URL = os.environ.get("DATABASE_URL")
if not DATABASE_URL or not DATABASE_URL.startswith(("postgresql://", "postgres://")):
    print("[ERROR] Definí DATABASE_URL (en .env o en la consola).")
    print("  Ejemplo: postgresql://user:pass@host:5432/dbname?sslmode=require")
    sys.exit(1)

try:
    import psycopg2
except ImportError:
    print("[ERROR] pip install psycopg2-binary")
    sys.exit(1)

def main():
    conn = psycopg2.connect(DATABASE_URL)
    conn.autocommit = True
    cur = conn.cursor()

    # Insertar o actualizar los 3 tipos de serie
    cur.execute("""
        INSERT INTO tipo_serie (id_tipo_serie, nombre_tipo_serie) VALUES
            (1, 'Original'),
            (2, 'Desestacionalizado'),
            (3, 'Tendencia-Ciclo')
        ON CONFLICT (id_tipo_serie) DO UPDATE SET nombre_tipo_serie = EXCLUDED.nombre_tipo_serie
    """)
    print("[OK] tipo_serie: 1=Original, 2=Desestacionalizado, 3=Tendencia-Ciclo")

    # Todas las variables en Original (id_tipo_serie = 1)
    cur.execute("UPDATE variables SET id_tipo_serie = 1")
    n = cur.rowcount
    print(f"[OK] variables: {n} actualizadas a id_tipo_serie = 1 (Original)")

    cur.close()
    conn.close()
    print("\n[OK] seed_tipo_serie finalizado.")

if __name__ == "__main__":
    main()
