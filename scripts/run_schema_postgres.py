"""
Ejecuta el schema PostgreSQL en la base de datos.

OPCIÓN 1 - Usuario/contraseña local:
  set DATABASE_URL=postgresql://usuario:pass@servidor:5432/macrodata?sslmode=require
  python scripts/run_schema_postgres.py

OPCIÓN 2 - Azure Active Directory (lo que mostrás en el portal):
  set PGHOST=server-fit.postgres.database.azure.com
  set PGUSER=administracion@fitcon.onmicrosoft.com
  set PGDATABASE=macrodata
  python scripts/run_schema_postgres.py
  (Requiere: az login y Azure CLI instalado)
"""
import os
import sys
import subprocess
from pathlib import Path
from urllib.parse import quote_plus

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATABASE_URL = os.environ.get("DATABASE_URL")

# Si no hay DATABASE_URL, intentar con Azure AD (PGHOST, PGUSER, etc.)
if not DATABASE_URL and os.environ.get("PGHOST"):
    print("[INFO] Usando Azure Active Directory (PGHOST, PGUSER, etc.)")
    host = os.environ.get("PGHOST", "localhost")
    user = os.environ.get("PGUSER", "")
    database = os.environ.get("PGDATABASE", "macrodata")
    port = os.environ.get("PGPORT", "5432")

    if not user:
        print("[ERROR] Definí PGUSER (ej: administracion@fitcon.onmicrosoft.com)")
        sys.exit(1)

    # Obtener token de Azure (Azure CLI o azure-identity)
    token = None
    try:
        result = subprocess.run(
            [
                "az", "account", "get-access-token",
                "--resource", "https://ossrdbms-aad.database.windows.net",
                "--query", "accessToken",
                "--output", "tsv"
            ],
            capture_output=True,
            text=True,
            check=True,
            timeout=10
        )
        token = result.stdout.strip() if result.stdout else None
    except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
        pass

    # Fallback: azure-identity (abre navegador para login)
    if not token:
        try:
            from azure.identity import InteractiveBrowserCredential
            credential = InteractiveBrowserCredential()
            token = credential.get_token("https://ossrdbms-aad.database.windows.net/.default").token
            print("[INFO] Token obtenido via navegador (azure-identity)")
        except ImportError:
            print("[ERROR] No se pudo obtener el token de Azure.")
            print("  Opción 1: Instalá Azure CLI y ejecutá 'az login'")
            print("  Opción 2: pip install azure-identity (abre navegador para login)")
            sys.exit(1)
        except Exception as e:
            print(f"[ERROR] azure-identity falló: {e}")
            sys.exit(1)

    if not token:
        print("[ERROR] Token vacío")
        sys.exit(1)

    # Armar connection string (el @ en user se codifica como %40)
    user_enc = quote_plus(user)
    token_enc = quote_plus(token)
    DATABASE_URL = f"postgresql://{user_enc}:{token_enc}@{host}:{port}/{database}?sslmode=require"

if not DATABASE_URL or not DATABASE_URL.startswith(("postgresql://", "postgres://")):
    print("[ERROR] Definí la conexión de una de estas formas:")
    print()
    print("  A) DATABASE_URL con usuario/contraseña:")
    print('     set DATABASE_URL=postgresql://usuario:pass@servidor:5432/macrodata?sslmode=require')
    print()
    print("  B) Variables para Azure AD (después de 'az login'):")
    print("     set PGHOST=server-fit.postgres.database.azure.com")
    print("     set PGUSER=administracion@fitcon.onmicrosoft.com")
    print("     set PGDATABASE=macrodata")
    sys.exit(1)

schema_path = PROJECT_ROOT / "scripts" / "schema_postgresql.sql"
if not schema_path.exists():
    print(f"[ERROR] No se encuentra {schema_path}")
    sys.exit(1)

try:
    import psycopg2
except ImportError:
    print("[ERROR] Instalá psycopg2: pip install psycopg2-binary")
    sys.exit(1)

print("[INFO] Conectando a PostgreSQL...")
conn = psycopg2.connect(DATABASE_URL)
conn.autocommit = True

with open(schema_path, encoding="utf-8") as f:
    sql = f.read()

# Quitar líneas que son solo comentarios, luego split por ;
lines = [line for line in sql.split("\n") if not line.strip().startswith("--")]
sql_clean = "\n".join(lines)
statements = [s.strip() + ";" for s in sql_clean.split(";") if s.strip()]

with conn.cursor() as cur:
    for stmt in statements:
        if not stmt:
            continue
        try:
            cur.execute(stmt)
            print(f"[OK] Ejecutado: {stmt[:60]}...")
        except Exception as e:
            if "already exists" in str(e).lower():
                print(f"[SKIP] Ya existe: {stmt[:50]}...")
            else:
                print(f"[ERROR] {e}")
                raise

conn.close()
print("\n[OK] Schema ejecutado correctamente")
