"""
Seed: variables y maestro para Inflación implícita curva soberana (1 a 10 años).
Ejecutar desde la raíz del proyecto con DATABASE_URL configurado:
  python scripts/seed_inflacion_implicita_curva.py
"""
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from db.connection import execute_query_single, execute_update

ID_SUB_FAMILIA = 10   # Curva soberana
ID_PAIS = 858         # Uruguay
NOMBRES = [
    "Inflación implícita curva soberana 1 año",
    "Inflación implícita curva soberana 2 años",
    "Inflación implícita curva soberana 3 años",
    "Inflación implícita curva soberana 4 años",
    "Inflación implícita curva soberana 5 años",
    "Inflación implícita curva soberana 6 años",
    "Inflación implícita curva soberana 7 años",
    "Inflación implícita curva soberana 8 años",
    "Inflación implícita curva soberana 9 años",
    "Inflación implícita curva soberana 10 años",
]


def main():
    print("Seed: Inflación implícita curva soberana (variables + maestro Uruguay)")
    # Idempotente: si ya existen, no insertar de nuevo (patrón como parámetro para no interpretar % como placeholder)
    exist = execute_query_single(
        "SELECT 1 FROM variables WHERE id_nombre_variable LIKE ? LIMIT 1",
        ("Inflación implícita curva soberana%",),
    )
    if exist:
        print("  Ya existen variables de inflación implícita. Nada que hacer.")
        return
    # Siguiente id_variable
    r = execute_query_single("SELECT COALESCE(MAX(id_variable), 0) + 1 AS next_id FROM variables")
    base_id = int(r["next_id"]) if r else 1
    ids_vars = list(range(base_id, base_id + 10))
    if len(ids_vars) != 10:
        print("[ERROR] No se pudieron obtener 10 ids consecutivos")
        return

    # Insertar variables
    for i, nombre in enumerate(NOMBRES):
        q = """
            INSERT INTO variables (id_variable, id_nombre_variable, id_sub_familia, nominal_o_real, moneda, id_tipo_serie)
            VALUES (?, ?, ?, 'n', 'LC', 1)
        """
        ok, err, _ = execute_update(q, (ids_vars[i], nombre, ID_SUB_FAMILIA))
        if not ok:
            print(f"[ERROR] Variable {nombre}: {err}")
            return
        print(f"  Variable: id={ids_vars[i]} -> {nombre}")

    # Siguiente id maestro
    r = execute_query_single("SELECT COALESCE(MAX(id), 0) + 1 AS next_id FROM maestro")
    maestro_id = int(r["next_id"]) if r else 1

    # Insertar maestro (Uruguay, D, activo=1, fuente=BEVSA)
    for i, id_var in enumerate(ids_vars):
        q = """
            INSERT INTO maestro (id, nombre, tipo, fuente, periodicidad, unidad, categoria,
                                 activo, es_cotizacion, pais, id_variable, id_pais, link, script_update)
            VALUES (?, ?, NULL, 'BEVSA', 'D', NULL, NULL, 1, 0, NULL, ?, ?, NULL, NULL)
        """
        ok, err, _ = execute_update(q, (maestro_id, NOMBRES[i], id_var, ID_PAIS))
        if not ok:
            print(f"[ERROR] Maestro id_variable={id_var}: {err}")
            return
        maestro_id += 1
    print(f"  Maestro: 10 filas para id_pais={ID_PAIS} (Uruguay)")
    print("Listo.")


if __name__ == "__main__":
    main()
