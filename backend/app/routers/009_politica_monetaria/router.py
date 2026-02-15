"""API para pantalla Instancia Política Monetaria.
Devuelve por país (Chile, Colombia, Perú, Uruguay, México): inflación interanual,
expectativas, objetivo, TPM, última variación TPM con fecha, tasa real.
"""
from datetime import date, datetime, timedelta
from typing import Optional, Dict, Any, List
from flask import Blueprint, jsonify, request
from ...database import execute_query, execute_query_single

bp = Blueprint('politica_monetaria', __name__)

# id_variable: 9 IPC, 23 expectativa 12m, 24 expectativa 24m, 52 TPM, 22 EMBI
ID_IPC = 9
ID_EXP_12 = 23
ID_EXP_24 = 24
ID_TPM = 52
ID_EMBI = 22

# Chile, Colombia, Perú, Uruguay, México (sin Brasil)
PAISES = [
    {"id_pais": 152, "nombre": "Chile", "codigo": "CL"},
    {"id_pais": 170, "nombre": "Colombia", "codigo": "CO"},
    {"id_pais": 604, "nombre": "Perú", "codigo": "PE"},
    {"id_pais": 858, "nombre": "Uruguay", "codigo": "UY"},
    {"id_pais": 484, "nombre": "México", "codigo": "MX"},
]

# Expectativas: 24m para Chile, Uruguay, Colombia; 12m para Perú, México
EXPECTATIVA_VAR = {
    152: ID_EXP_24,  # Chile
    170: ID_EXP_24,  # Colombia
    604: ID_EXP_12,  # Perú
    858: ID_EXP_24,  # Uruguay
    484: ID_EXP_12,  # México
}

# Objetivo de inflación: centro y banda (±). Para "en rango": [centro - banda, centro + banda]
OBJETIVO = {
    152: {"centro": 2.0, "banda": 1.0, "texto": "2,00% +/- 1,00%"},
    170: {"centro": 3.0, "banda": 1.0, "texto": "3,00% +/- 1,00%"},
    604: {"centro": 2.0, "banda": 1.0, "texto": "2,00% +/- 1,00%"},
    858: {"centro": 4.5, "banda": 1.5, "texto": "4,50% +/- 1,50%"},
    484: {"centro": 3.0, "banda": 1.0, "texto": "3,00% +/- 1,00%"},
}


def parse_fecha(fecha_val):
    if isinstance(fecha_val, date):
        return fecha_val
    s = str(fecha_val).split(" ")[0]
    return date.fromisoformat(s)


def get_ipc_mensual(id_pais: int, meses_atras: int = 13) -> Dict[date, float]:
    """Obtiene IPC mensual para los últimos meses. Agrupa por mes (último valor del mes)."""
    query = """
        SELECT fecha, valor
        FROM maestro_precios
        WHERE id_variable = ? AND id_pais = ?
        ORDER BY fecha DESC
        LIMIT 500
    """
    rows = execute_query(query, (ID_IPC, id_pais))
    if not rows:
        return {}
    # Agrupar por (año, mes) y quedarse con el valor más reciente del mes
    por_mes = {}
    for r in rows:
        f = parse_fecha(r["fecha"])
        key = (f.year, f.month)
        if key not in por_mes:
            por_mes[key] = {"fecha": f, "valor": float(r["valor"])}
    # Ordenar por fecha y tomar los últimos meses_atras
    ordenados = sorted(por_mes.values(), key=lambda x: x["fecha"], reverse=True)
    return {x["fecha"]: x["valor"] for x in ordenados[:meses_atras]}


def inflacion_interanual_from_ipc(ipc_mensual: Dict[date, float]) -> Optional[float]:
    """Calcula inflación interanual (%) del último mes con datos vs mismo mes hace 12 meses."""
    if len(ipc_mensual) < 2:
        return None
    fechas_ord = sorted(ipc_mensual.keys(), reverse=True)
    ultima = fechas_ord[0]
    ipc_actual = ipc_mensual[ultima]
    # Hace 12 meses
    try:
        hace12 = ultima.replace(year=ultima.year - 1) if ultima.month > 0 else date(ultima.year - 1, 12, ultima.day)
    except ValueError:
        hace12 = date(ultima.year - 1, ultima.month, min(28, ultima.day))
    ipc_12 = ipc_mensual.get(hace12)
    if ipc_12 is None:
        # Buscar el valor más cercano a hace 12 meses
        for f in fechas_ord[1:]:
            if (f.year, f.month) == (hace12.year, hace12.month):
                ipc_12 = ipc_mensual[f]
                break
        if ipc_12 is None:
            return None
    if ipc_12 == 0:
        return None
    return (ipc_actual / ipc_12 - 1.0) * 100.0


def get_expectativa(id_pais: int) -> Optional[float]:
    """Último valor de expectativa (12m o 24m según país)."""
    id_var = EXPECTATIVA_VAR.get(id_pais, ID_EXP_12)
    query = """
        SELECT valor FROM maestro_precios
        WHERE id_variable = ? AND id_pais = ?
        ORDER BY fecha DESC LIMIT 1
    """
    r = execute_query_single(query, (id_var, id_pais))
    if r and r.get("valor") is not None:
        return float(r["valor"])
    return None


def get_tpm_ultimo_cambio(id_pais: int) -> Dict[str, Any]:
    """
    Obtiene TPM actual y la última variación (cuando cambió la tasa).
    fecha_cambio = primera fecha en que la tasa tomó el valor actual (cuando se hizo el cambio).
    variacion_pp = diferencia en p.p. respecto al valor anterior.
    """
    query = """
        SELECT fecha, valor
        FROM maestro_precios
        WHERE id_variable = ? AND id_pais = ?
        ORDER BY fecha DESC
        LIMIT 500
    """
    rows = execute_query(query, (ID_TPM, id_pais))
    if not rows:
        return {"tpm": None, "variacion_pp": None, "fecha_cambio": None}
    tpm_actual = float(rows[0]["valor"])
    variacion_pp = None
    # Fechas donde la tasa es la actual: la primera (más antigua) es cuando se hizo el cambio
    fechas_valor_actual = []
    for r in rows:
        v = float(r["valor"])
        if v == tpm_actual:
            fechas_valor_actual.append(parse_fecha(r["fecha"]))
        else:
            if variacion_pp is None:
                variacion_pp = round(tpm_actual - v, 2)
            break
    fecha_cambio = min(fechas_valor_actual) if fechas_valor_actual else parse_fecha(rows[0]["fecha"])
    return {
        "tpm": tpm_actual,
        "variacion_pp": variacion_pp,
        "fecha_cambio": fecha_cambio.isoformat() if fecha_cambio else None,
    }


def en_rango(valor: Optional[float], centro: float, banda: float) -> bool:
    if valor is None:
        return False
    return (centro - banda) <= valor <= (centro + banda)


def get_embi_ultimo(id_pais: int) -> Optional[float]:
    """Último valor de EMBI en puntos básicos. En BD está en decimal (ej. 0.71607); se devuelve × 100 (71.607)."""
    query = """
        SELECT valor FROM maestro_precios
        WHERE id_variable = ? AND id_pais = ?
        ORDER BY fecha DESC LIMIT 1
    """
    r = execute_query_single(query, (ID_EMBI, id_pais))
    if r and r.get("valor") is not None:
        return float(r["valor"]) * 100
    return None


@bp.route("/politica-monetaria", methods=["GET"])
def get_politica_monetaria():
    """Devuelve tabla de política monetaria para Chile, Colombia, Perú, Uruguay, México."""
    resultados = []
    for p in PAISES:
        id_pais = p["id_pais"]
        nombre = p["nombre"]
        codigo = p["codigo"]
        obj = OBJETIVO.get(id_pais, {})
        centro = obj.get("centro", 0)
        banda = obj.get("banda", 0)
        objetivo_texto = obj.get("texto", "")

        ipc_mensual = get_ipc_mensual(id_pais)
        inflacion = inflacion_interanual_from_ipc(ipc_mensual)
        expectativa = get_expectativa(id_pais)
        tpm_data = get_tpm_ultimo_cambio(id_pais)
        tpm = tpm_data["tpm"]
        variacion_pp = tpm_data["variacion_pp"]
        fecha_cambio = tpm_data["fecha_cambio"]

        # Tasa real = (1 + TPM/100) / (1 + expectativa/100) - 1, en %
        tasa_real = None
        if tpm is not None and expectativa is not None and (1 + expectativa / 100) != 0:
            tasa_real = ((1 + tpm / 100) / (1 + expectativa / 100) - 1) * 100

        inflacion_en_rango = en_rango(inflacion, centro, banda)
        expectativa_en_rango = en_rango(expectativa, centro, banda)
        embi = get_embi_ultimo(id_pais)

        resultados.append({
            "id_pais": id_pais,
            "pais": nombre,
            "codigo": codigo,
            "inflacion_interanual": round(inflacion, 2) if inflacion is not None else None,
            "expectativas": round(expectativa, 2) if expectativa is not None else None,
            "objetivo": objetivo_texto,
            "objetivo_centro": centro,
            "objetivo_banda": banda,
            "tpm": round(tpm, 2) if tpm is not None else None,
            "variacion_tpm_pp": variacion_pp,
            "fecha_cambio_tpm": fecha_cambio,
            "tasa_real": round(tasa_real, 2) if tasa_real is not None else None,
            "embi": round(embi, 2) if embi is not None else None,
            "inflacion_en_rango": inflacion_en_rango,
            "expectativa_en_rango": expectativa_en_rango,
        })
    return jsonify(resultados)


def _parse_desde_hasta():
    """Lee desde/hasta de query (YYYY-MM-DD o DD-MM-YYYY). Devuelve (desde, hasta) como date o None."""
    desde_s = request.args.get("desde") or ""
    hasta_s = request.args.get("hasta") or ""
    default_hasta = date.today()
    default_desde = default_hasta - timedelta(days=365)
    try:
        if len(desde_s) == 10:
            if desde_s[2] == "-" and desde_s[5] == "-":  # DD-MM-YYYY
                d, m, y = desde_s.split("-")
                desde = date(int(y), int(m), int(d))
            else:  # YYYY-MM-DD
                desde = date.fromisoformat(desde_s)
        else:
            desde = default_desde
    except (ValueError, IndexError):
        desde = default_desde
    try:
        if len(hasta_s) == 10:
            if hasta_s[2] == "-" and hasta_s[5] == "-":
                d, m, y = hasta_s.split("-")
                hasta = date(int(y), int(m), int(d))
            else:
                hasta = date.fromisoformat(hasta_s)
        else:
            hasta = default_hasta
    except (ValueError, IndexError):
        hasta = default_hasta
    if desde > hasta:
        desde, hasta = hasta, desde
    return desde, hasta


@bp.route("/politica-monetaria/series/tpm", methods=["GET"])
def get_series_tpm():
    """Series de TPM por país en rango de fechas. Query: desde=DD-MM-YYYY&hasta=DD-MM-YYYY (o YYYY-MM-DD)."""
    desde, hasta = _parse_desde_hasta()
    resultados = []
    for p in PAISES:
        query = """
            SELECT fecha, valor
            FROM maestro_precios
            WHERE id_variable = ? AND id_pais = ? AND fecha >= ? AND fecha <= ?
            ORDER BY fecha
        """
        rows = execute_query(query, (ID_TPM, p["id_pais"], desde.isoformat(), hasta.isoformat()))
        datos = [{"fecha": str(r["fecha"]).split(" ")[0], "valor": round(float(r["valor"]), 2)} for r in rows]
        resultados.append({"pais": p["nombre"], "codigo": p["codigo"], "data": datos})
    return jsonify(resultados)


@bp.route("/politica-monetaria/series/expectativas", methods=["GET"])
def get_series_expectativas():
    """
    Series de expectativas de inflación por país en rango de fechas.
    Se agrupa por mes-año: un solo dato por mes (se toma el valor del registro en ese mes; si hay varios, el último por fecha).
    Fecha en la respuesta: primer día del mes (YYYY-MM-01).
    """
    desde, hasta = _parse_desde_hasta()
    resultados = []
    for p in PAISES:
        id_var = EXPECTATIVA_VAR.get(p["id_pais"], ID_EXP_12)
        query = """
            SELECT fecha, valor
            FROM maestro_precios
            WHERE id_variable = ? AND id_pais = ? AND fecha >= ? AND fecha <= ?
            ORDER BY fecha
        """
        rows = execute_query(query, (id_var, p["id_pais"], desde.isoformat(), hasta.isoformat()))
        # Agrupar por (año, mes): quedarse con el último valor del mes (última publicación)
        por_mes = {}
        for r in rows:
            f = parse_fecha(r["fecha"])
            key = (f.year, f.month)
            # Siempre guardar el más reciente del mes (las filas vienen ordenadas por fecha)
            por_mes[key] = {"fecha": date(f.year, f.month, 1), "valor": round(float(r["valor"]), 2)}
        datos = [{"fecha": v["fecha"].isoformat(), "valor": v["valor"]} for _, v in sorted(por_mes.items())]
        resultados.append({"pais": p["nombre"], "codigo": p["codigo"], "data": datos})
    return jsonify(resultados)


@bp.route("/politica-monetaria/series/embi", methods=["GET"])
def get_series_embi():
    """Series de EMBI (spread en pb) por país en rango de fechas. Diario, mismo filtro que TPM."""
    desde, hasta = _parse_desde_hasta()
    resultados = []
    for p in PAISES:
        query = """
            SELECT fecha, valor
            FROM maestro_precios
            WHERE id_variable = ? AND id_pais = ? AND fecha >= ? AND fecha <= ?
            ORDER BY fecha
        """
        rows = execute_query(query, (ID_EMBI, p["id_pais"], desde.isoformat(), hasta.isoformat()))
        # Excel/BD tiene valor en decimal (ej. 0.71607); gráfico en puntos básicos (× 100)
        datos = [{"fecha": str(r["fecha"]).split(" ")[0], "valor": round(float(r["valor"]) * 100, 2)} for r in rows]
        resultados.append({"pais": p["nombre"], "codigo": p["codigo"], "data": datos})
    return jsonify(resultados)


# id_variable 20 = tipo de cambio USD/LC (cotización oficial)
ID_TC_USD = 20


@bp.route("/politica-monetaria/series/monedas", methods=["GET"])
def get_series_monedas():
    """
    Series de tipo de cambio USD/LC por país en rango de fechas.
    Para graficar en base 100 (primer dato = 100) en el frontend.
    """
    desde, hasta = _parse_desde_hasta()
    resultados = []
    for p in PAISES:
        query = """
            SELECT fecha, valor
            FROM maestro_precios
            WHERE id_variable = ? AND id_pais = ? AND fecha >= ? AND fecha <= ?
            ORDER BY fecha
        """
        rows = execute_query(query, (ID_TC_USD, p["id_pais"], desde.isoformat(), hasta.isoformat()))
        datos = [{"fecha": str(r["fecha"]).split(" ")[0], "valor": round(float(r["valor"]), 4)} for r in rows]
        resultados.append({"pais": p["nombre"], "codigo": p["codigo"], "data": datos})
    return jsonify(resultados)
