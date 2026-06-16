"""
Validación de cálculos IPC desagregado:
1. Inflación interanual por división
2. Contribución a la inflación (cascada) = (indice_div_t / indice_div_t-12 - 1) * ponderador
3. Suma de contribuciones ≈ inflación general

Ejecutar: python scripts/validate_ipc_calculos.py
"""
import sys
from pathlib import Path
from datetime import date
from decimal import Decimal

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from db.connection import execute_query

ID_PAIS = 858


def get_divisiones():
    """Obtiene las 12 divisiones + general (99)."""
    rows = execute_query(
        """
        SELECT id, division, descripcion, etiqueta, ponderacion
        FROM ipc_desagregados
        WHERE id_pais = %s
          AND division IS NOT NULL
          AND grupo IS NULL
        ORDER BY division
        """,
        (ID_PAIS,),
    )
    return rows


def get_indice(id_rubro, fecha):
    """Obtiene el valor del indice para un rubro en una fecha."""
    row = execute_query(
        """
        SELECT valor FROM ipc_desagregados_valores
        WHERE id_ipc_desagregado = %s AND fecha = %s
        """,
        (id_rubro, fecha.isoformat()),
    )
    return float(row[0]["valor"]) if row else None


def get_fechas_disponibles():
    """Obtiene todas las fechas disponibles ordenadas."""
    rows = execute_query(
        """
        SELECT DISTINCT fecha FROM ipc_desagregados_valores
        WHERE id_pais = %s
        ORDER BY fecha DESC
        """,
        (ID_PAIS,),
    )
    return [r["fecha"] for r in rows]


def calcular_inflacion_interanual(id_rubro, fecha_actual):
    """Calcula variacion % interanual del indice."""
    fecha_anterior = date(fecha_actual.year - 1, fecha_actual.month, 1)
    val_actual = get_indice(id_rubro, fecha_actual)
    val_anterior = get_indice(id_rubro, fecha_anterior)
    if val_actual is None or val_anterior is None or val_anterior == 0:
        return None
    return (val_actual / val_anterior - 1) * 100


def main():
    divisiones = get_divisiones()
    print(f"Divisiones encontradas: {len(divisiones)}")
    print()

    general = None
    divs = []
    for d in divisiones:
        div_code = str(d["division"]).strip()
        if div_code == "99":
            general = d
        else:
            divs.append(d)
        pond_str = str(d['ponderacion']) if d['ponderacion'] else 'N/A'
        print(f"  div={div_code:>4s}  pond={pond_str:>12s}  {d['etiqueta'] or d['descripcion']}")

    print(f"\nDivisiones COICOP: {len(divs)}, General: {'SI' if general else 'NO'}")

    fechas = get_fechas_disponibles()
    if not fechas:
        print("[ERROR] No hay fechas")
        return

    fecha_analisis = fechas[0]
    if isinstance(fecha_analisis, str):
        fecha_analisis = date.fromisoformat(fecha_analisis)
    fecha_base = date(fecha_analisis.year - 1, fecha_analisis.month, 1)

    print(f"\n{'='*70}")
    print(f"ANALISIS: {fecha_analisis.strftime('%B %Y')} vs {fecha_base.strftime('%B %Y')}")
    print(f"{'='*70}")

    if general:
        infl_general = calcular_inflacion_interanual(general["id"], fecha_analisis)
        print(f"\nInflacion GENERAL interanual: {infl_general:.4f}%" if infl_general else "\nInflacion GENERAL: N/A")

    print(f"\n{'Etiqueta':<35s} {'Infl.%':>8s} {'Pond.':>8s} {'Contrib.':>10s}")
    print("-" * 65)

    suma_contribuciones = 0.0
    for d in divs:
        pond = float(d["ponderacion"]) if d["ponderacion"] else 0
        infl = calcular_inflacion_interanual(d["id"], fecha_analisis)
        if infl is not None:
            contribucion = infl * pond / 100 if pond > 1 else infl * pond
            suma_contribuciones += contribucion
            etiq = (d["etiqueta"] or d["descripcion"] or "?")[:34]
            print(f"  {etiq:<34s} {infl:>7.2f}% {pond:>7.4f} {contribucion:>9.4f}%")
        else:
            etiq = (d["etiqueta"] or d["descripcion"] or "?")[:34]
            print(f"  {etiq:<34s} {'N/A':>8s} {pond:>7.4f} {'N/A':>10s}")

    print("-" * 65)
    print(f"  {'SUMA CONTRIBUCIONES':<34s} {'':>8s} {'':>8s} {suma_contribuciones:>9.4f}%")
    if general and infl_general:
        print(f"  {'INFLACION GENERAL':<34s} {'':>8s} {'':>8s} {infl_general:>9.4f}%")
        diff = abs(suma_contribuciones - infl_general)
        ok = "OK" if diff < 0.05 else "REVISAR"
        print(f"\n  Diferencia: {diff:.4f}% [{ok}]")


if __name__ == "__main__":
    main()
