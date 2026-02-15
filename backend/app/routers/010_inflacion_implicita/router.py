"""API routes for Inflación implícita curva soberana (1-10 años)."""
from datetime import date
from typing import List, Tuple

from flask import Blueprint, request, jsonify

from ...database import execute_query, execute_query_single

bp = Blueprint('inflacion_implicita', __name__)

ID_PAIS = 858  # Uruguay
# id_variable 86 (1 año) .. 95 (10 años), fijados por seed
PLAZOS_IMPLICITA: List[Tuple[int, str]] = [
    (86, "1 año"), (87, "2 años"), (88, "3 años"), (89, "4 años"), (90, "5 años"),
    (91, "6 años"), (92, "7 años"), (93, "8 años"), (94, "9 años"), (95, "10 años"),
]


def parse_fecha(fecha_val):
    if isinstance(fecha_val, date):
        return fecha_val
    s = str(fecha_val)
    if ' ' in s:
        s = s.split(' ')[0]
    return date.fromisoformat(s)


def _get_plazos_ordenados() -> List[Tuple[int, str]]:
    """Lista de (id_variable, nombre_plazo) ordenada por plazo 1..10."""
    return PLAZOS_IMPLICITA


@bp.route('/inflacion-implicita/fechas', methods=['GET'])
def get_fechas():
    """Fechas disponibles para la curva de inflación implícita."""
    try:
        plazos = _get_plazos_ordenados()
        if not plazos:
            return jsonify({"ultima_fecha": None, "fechas_disponibles": []})
        id_vars = [p[0] for p in plazos]
        placeholders = ",".join(["?" for _ in id_vars])
        q = f"""
            SELECT DISTINCT fecha
            FROM maestro_precios
            WHERE id_pais = ? AND id_variable IN ({placeholders})
            ORDER BY fecha DESC
        """
        r = execute_query(q, (ID_PAIS,) + tuple(id_vars))
        fechas = sorted([parse_fecha(x["fecha"]) for x in r], reverse=True)
        ultima = fechas[0].isoformat() if fechas else None
        return jsonify({
            "ultima_fecha": ultima,
            "fechas_disponibles": [f.isoformat() for f in fechas],
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@bp.route('/inflacion-implicita/curva', methods=['GET'])
def get_curva():
    """
    Curva de inflación implícita por plazo para una fecha.
    Query: fecha=YYYY-MM-DD (opcional; si no se envía, se usa la última disponible).
    """
    try:
        plazos = _get_plazos_ordenados()
        if not plazos:
            return jsonify({"error": "No hay variables de inflación implícita"}), 404
        fecha_str = request.args.get("fecha")
        if fecha_str:
            fecha_obj = date.fromisoformat(fecha_str)
        else:
            ult = execute_query_single(
                "SELECT MAX(fecha) AS m FROM maestro_precios WHERE id_pais = ? AND id_variable = ?",
                (ID_PAIS, plazos[0][0]),
            )
            if not ult or not ult.get("m"):
                return jsonify({"error": "No hay datos"}), 404
            fecha_obj = parse_fecha(ult["m"])
        plazos_nombres = []
        valores = []
        for id_var, nombre in plazos:
            row = execute_query_single(
                "SELECT valor FROM maestro_precios WHERE id_variable = ? AND id_pais = ? AND fecha = ?",
                (id_var, ID_PAIS, fecha_obj.isoformat()),
            )
            plazos_nombres.append(nombre)
            valores.append(round(float(row["valor"]), 2) if row and row.get("valor") is not None else None)
        return jsonify({
            "fecha": fecha_obj.isoformat(),
            "plazos": plazos_nombres,
            "valores": valores,
        })
    except ValueError as e:
        return jsonify({"error": f"Fecha inválida: {e}"}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@bp.route('/inflacion-implicita/evolucion', methods=['GET'])
def get_evolucion():
    """
    Evolución temporal de la inflación implícita para un plazo.
    Query: plazo=1..10, fecha_desde=YYYY-MM-DD, fecha_hasta=YYYY-MM-DD.
    """
    try:
        plazos = _get_plazos_ordenados()
        if not plazos:
            return jsonify({"error": "No hay variables de inflación implícita"}), 404
        plazo_num = request.args.get("plazo", type=int)
        if plazo_num is None or plazo_num < 1 or plazo_num > 10:
            return jsonify({"error": "plazo debe ser entre 1 y 10"}), 400
        id_var = plazos[plazo_num - 1][0]
        nombre_plazo = plazos[plazo_num - 1][1]
        fecha_desde = request.args.get("fecha_desde")
        fecha_hasta = request.args.get("fecha_hasta")
        if not fecha_desde or not fecha_hasta:
            return jsonify({"error": "fecha_desde y fecha_hasta son obligatorios"}), 400
        q = """
            SELECT fecha, valor
            FROM maestro_precios
            WHERE id_variable = ? AND id_pais = ? AND fecha >= ? AND fecha <= ?
            ORDER BY fecha
        """
        rows = execute_query(q, (id_var, ID_PAIS, fecha_desde, fecha_hasta))
        data = [
            {"fecha": parse_fecha(r["fecha"]).isoformat(), "valor": round(float(r["valor"]), 2)}
            for r in rows if r.get("valor") is not None
        ]
        return jsonify({
            "plazo": plazo_num,
            "nombre_plazo": nombre_plazo,
            "id_variable": id_var,
            "data": data,
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@bp.route('/inflacion-implicita/plazos', methods=['GET'])
def get_plazos():
    """Lista de plazos disponibles (1-10 años) con id_variable para selectores."""
    try:
        plazos = _get_plazos_ordenados()
        out = [
            {"plazo": i + 1, "nombre": nombre, "id_variable": id_var}
            for i, (id_var, nombre) in enumerate(plazos)
        ]
        return jsonify({"plazos": out})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
