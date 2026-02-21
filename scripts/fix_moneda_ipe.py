"""Script para corregir la moneda de las variables IPE a USD."""
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

try:
    from dotenv import load_dotenv
    load_dotenv(PROJECT_ROOT / ".env")
except ImportError:
    pass

from db.connection import execute_update, execute_query

print("Actualizando moneda de variables IPE (53-68) a USD...")
print()

ids = list(range(53, 69))
for vid in ids:
    success, error, _ = execute_update(
        "UPDATE variables SET moneda = ? WHERE id_variable = ?",
        ("usd", vid)
    )
    if success:
        # Verificar el cambio
        result = execute_query(
            "SELECT id_variable, id_nombre_variable, moneda FROM variables WHERE id_variable = ?",
            (vid,)
        )
        if result:
            row = result[0]
            print(f"[OK] id_variable={vid}: {row['id_nombre_variable'][:40]:40} -> moneda={row['moneda']}")
        else:
            print(f"[WARN] id_variable={vid}: Actualizado pero no encontrado al verificar")
    else:
        print(f"[ERROR] id_variable={vid}: {error}")

print()
print("Verificando todas las variables IPE...")
result = execute_query("""
    SELECT id_variable, id_nombre_variable, moneda
    FROM variables
    WHERE id_variable BETWEEN 53 AND 68
    ORDER BY id_variable
""")

print()
for row in result:
    moneda = row['moneda'] or 'NULL'
    status = '[OK]' if moneda.lower() == 'usd' else '[ERROR]'
    print(f"{status} {row['id_variable']:2}: {row['id_nombre_variable'][:45]:45} | Moneda: {moneda}")

print()
print("Proceso completado.")
