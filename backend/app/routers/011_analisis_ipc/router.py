"""API routes para Analisis IPC — usa vistas precalculadas."""
from datetime import date
from flask import Blueprint, request, jsonify
from ...database import execute_query

bp = Blueprint('analisis_ipc', __name__)
ID_PAIS = 858


def _d(val):
    if isinstance(val, date):
        return val.isoformat()
    return str(val).split(' ')[0]


@bp.route('/analisis-ipc/fechas', methods=['GET'])
def get_fechas():
    rows = execute_query(
        "SELECT DISTINCT fecha FROM ipc_desagregados_valores "
        "WHERE id_pais = %s ORDER BY fecha DESC", (ID_PAIS,))
    fechas = [_d(r['fecha']) for r in rows]
    return jsonify({'ultima_fecha': fechas[0] if fechas else None, 'fechas': fechas})


@bp.route('/analisis-ipc/rubros', methods=['GET'])
def get_rubros():
    div = request.args.get('division')
    grupo = request.args.get('grupo')
    clase = request.args.get('clase')
    subclase = request.args.get('subclase')
    hijos_de = (request.args.get('hijos_de') or '').strip().lower()

    if hijos_de == 'general':
        sql = """SELECT r.id, r.division, r.grupo, r.clase, r.subclase, r.producto,
                        r.descripcion, r.etiqueta, r.ponderacion, r.nivel,
                        EXISTS(SELECT 1 FROM ipc_desagregados c
                               WHERE c.id_pais=%s AND c.division=r.division AND c.nivel = 'grupo'
                        ) as has_children
                 FROM ipc_desagregados r
                 WHERE r.id_pais=%s AND (
                    r.nivel = 'division'
                    OR (
                        r.nivel IS NULL
                        AND NULLIF(BTRIM(COALESCE(r.division::text, '')), '') IS NOT NULL
                        AND BTRIM(COALESCE(r.division::text, '')) <> '99'
                        AND (r.grupo IS NULL OR BTRIM(COALESCE(r.grupo::text, '')) = '')
                        AND (r.clase IS NULL OR BTRIM(COALESCE(r.clase::text, '')) = '')
                        AND (r.subclase IS NULL OR BTRIM(COALESCE(r.subclase::text, '')) = '')
                        AND (r.producto IS NULL OR BTRIM(COALESCE(r.producto::text, '')) = '')
                    )
                 )
                 ORDER BY r.division"""
        rows = execute_query(sql, (ID_PAIS, ID_PAIS))
    elif subclase:
        sql = """SELECT r.id, r.division, r.grupo, r.clase, r.subclase, r.producto,
                        r.descripcion, r.etiqueta, r.ponderacion, r.nivel,
                        FALSE as has_children
                 FROM ipc_desagregados r
                 WHERE r.id_pais=%s AND r.subclase=%s AND r.nivel = 'producto'
                 ORDER BY r.producto"""
        rows = execute_query(sql, (ID_PAIS, subclase))
    elif clase:
        sql = """SELECT r.id, r.division, r.grupo, r.clase, r.subclase, r.producto,
                        r.descripcion, r.etiqueta, r.ponderacion, r.nivel,
                        EXISTS(SELECT 1 FROM ipc_desagregados c
                               WHERE c.id_pais=%s AND c.subclase=r.subclase AND c.nivel = 'producto'
                        ) as has_children
                 FROM ipc_desagregados r
                 WHERE r.id_pais=%s AND r.clase=%s AND r.nivel = 'subclase'
                 ORDER BY r.subclase"""
        rows = execute_query(sql, (ID_PAIS, ID_PAIS, clase))
    elif grupo:
        sql = """SELECT r.id, r.division, r.grupo, r.clase, r.subclase, r.producto,
                        r.descripcion, r.etiqueta, r.ponderacion, r.nivel,
                        EXISTS(SELECT 1 FROM ipc_desagregados c
                               WHERE c.id_pais=%s AND c.clase=r.clase AND c.nivel = 'subclase'
                        ) as has_children
                 FROM ipc_desagregados r
                 WHERE r.id_pais=%s AND r.grupo=%s AND r.nivel = 'clase'
                 ORDER BY r.clase"""
        rows = execute_query(sql, (ID_PAIS, ID_PAIS, grupo))
    elif div and div != '99':
        sql = """SELECT r.id, r.division, r.grupo, r.clase, r.subclase, r.producto,
                        r.descripcion, r.etiqueta, r.ponderacion, r.nivel,
                        EXISTS(SELECT 1 FROM ipc_desagregados c
                               WHERE c.id_pais=%s AND c.grupo=r.grupo AND c.nivel = 'clase'
                        ) as has_children
                 FROM ipc_desagregados r
                 WHERE r.id_pais=%s AND r.division=%s AND r.nivel = 'grupo'
                 ORDER BY r.grupo"""
        rows = execute_query(sql, (ID_PAIS, ID_PAIS, div))
    else:
        sql = """SELECT r.id, r.division, r.grupo, r.clase, r.subclase, r.producto,
                        r.descripcion, r.etiqueta, r.ponderacion, r.nivel,
                        CASE
                        WHEN r.nivel = 'general' OR BTRIM(COALESCE(r.division::text, '')) = '99' THEN
                             EXISTS(SELECT 1 FROM ipc_desagregados c
                                    WHERE c.id_pais=%s AND (
                                        c.nivel = 'division'
                                        OR (
                                            c.nivel IS NULL
                                            AND NULLIF(BTRIM(COALESCE(c.division::text, '')), '') IS NOT NULL
                                            AND BTRIM(COALESCE(c.division::text, '')) <> '99'
                                            AND (c.grupo IS NULL OR BTRIM(COALESCE(c.grupo::text, '')) = '')
                                            AND (c.clase IS NULL OR BTRIM(COALESCE(c.clase::text, '')) = '')
                                            AND (c.subclase IS NULL OR BTRIM(COALESCE(c.subclase::text, '')) = '')
                                            AND (c.producto IS NULL OR BTRIM(COALESCE(c.producto::text, '')) = '')
                                        )
                                    ))
                        ELSE EXISTS(SELECT 1 FROM ipc_desagregados c
                                    WHERE c.id_pais=%s AND c.division=r.division AND c.nivel = 'grupo')
                        END as has_children
                 FROM ipc_desagregados r
                 WHERE r.id_pais=%s AND (
                    r.nivel IN ('general', 'division')
                    OR (
                        r.nivel IS NULL
                        AND NULLIF(BTRIM(COALESCE(r.division::text, '')), '') IS NOT NULL
                        AND (r.grupo IS NULL OR BTRIM(COALESCE(r.grupo::text, '')) = '')
                        AND (r.clase IS NULL OR BTRIM(COALESCE(r.clase::text, '')) = '')
                        AND (r.subclase IS NULL OR BTRIM(COALESCE(r.subclase::text, '')) = '')
                        AND (r.producto IS NULL OR BTRIM(COALESCE(r.producto::text, '')) = '')
                    )
                 )
                 ORDER BY CASE WHEN r.nivel = 'general' OR BTRIM(COALESCE(r.division::text, '')) = '99'
                               THEN 0 ELSE 1 END, r.division"""
        rows = execute_query(sql, (ID_PAIS, ID_PAIS, ID_PAIS))

    result = []
    for r in rows:
        item = {
            'id': r['id'],
            'id_ipc': r['id'],
            'descripcion': r['descripcion'],
            'etiqueta': r.get('etiqueta') or r['descripcion'],
            'ponderacion': float(r['ponderacion']) if r['ponderacion'] else None,
            'has_children': bool(r.get('has_children', False)),
            'nivel': r.get('nivel'),
        }
        for k in ('division', 'grupo', 'clase', 'subclase', 'producto'):
            v = r.get(k)
            if v is not None and str(v).strip() != '':
                item[k] = str(v).strip()
        result.append(item)
    return jsonify({'rubros': result})


@bp.route('/analisis-ipc/rubros-nivel', methods=['GET'])
def get_rubros_nivel():
    """Retorna todos los rubros de un nivel jerárquico."""
    nivel = (request.args.get('nivel') or 'division').lower()
    niveles_ok = ('general', 'division', 'grupo', 'clase', 'subclase', 'producto')
    if nivel not in niveles_ok:
        nivel = 'division'
    rows = execute_query(
        "SELECT id, division, grupo, clase, subclase, producto, "
        "descripcion, etiqueta, ponderacion, nivel "
        "FROM ipc_desagregados WHERE id_pais = %s AND nivel = %s "
        "ORDER BY division, grupo, clase, subclase, producto",
        (ID_PAIS, nivel),
    )
    result = []
    for r in rows:
        item = {
            'id': r['id'],
            'id_ipc': r['id'],
            'descripcion': r['descripcion'],
            'etiqueta': r.get('etiqueta') or r['descripcion'],
            'ponderacion': float(r['ponderacion']) if r['ponderacion'] else None,
            'nivel': r.get('nivel'),
        }
        for k in ('division', 'grupo', 'clase', 'subclase', 'producto'):
            v = r.get(k)
            if v is not None and str(v).strip() != '':
                item[k] = str(v).strip()
        result.append(item)
    return jsonify({'rubros': result})


@bp.route('/analisis-ipc/inflacion-serie', methods=['GET'])
def get_inflacion_serie():
    ids_str = request.args.get('ids', '')
    fd = request.args.get('fecha_desde')
    fh = request.args.get('fecha_hasta')
    if not ids_str or not fd or not fh:
        return jsonify({'error': 'Parametros ids, fecha_desde, fecha_hasta requeridos'}), 400

    ids = [int(x) for x in ids_str.split(',') if x.strip()]
    if not ids:
        return jsonify({'series': []})

    placeholders = ','.join(['%s'] * len(ids))
    rows = execute_query(
        f"SELECT id_ipc_desagregado, etiqueta, fecha, inflacion "
        f"FROM v_ipc_inflacion "
        f"WHERE id_ipc_desagregado IN ({placeholders}) "
        f"AND fecha >= %s AND fecha <= %s AND inflacion IS NOT NULL "
        f"ORDER BY id_ipc_desagregado, fecha",
        tuple(ids) + (fd, fh))

    by_id = {}
    for r in rows:
        rid = r['id_ipc_desagregado']
        if rid not in by_id:
            by_id[rid] = {'id': rid, 'nombre': r['etiqueta'], 'data': []}
        by_id[rid]['data'].append({
            'fecha': _d(r['fecha']),
            'valor': round(float(r['inflacion']), 4)
        })

    series = [by_id[rid] for rid in ids if rid in by_id]
    return jsonify({'series': series})


@bp.route('/analisis-ipc/cascada', methods=['GET'])
def get_cascada():
    fecha_str = request.args.get('fecha')
    if not fecha_str:
        row = execute_query("SELECT MAX(fecha) AS mx FROM v_ipc_contribucion")
        if not row or not row[0]['mx']:
            return jsonify({'error': 'Sin datos'}), 404
        fecha_str = _d(row[0]['mx'])

    rows = execute_query(
        "SELECT c.division, c.etiqueta, c.ponderacion, c.indice_div, "
        "c.indice_general_12, c.indice_general, c.aporte, c.inflacion_general, "
        "i.inflacion AS inflacion_propia "
        "FROM v_ipc_contribucion c "
        "LEFT JOIN v_ipc_inflacion i "
        "  ON i.id_ipc_desagregado = c.id_ipc_desagregado AND i.fecha = c.fecha "
        "WHERE c.fecha = %s ORDER BY c.aporte",
        (fecha_str,))

    if not rows:
        return jsonify({'error': f'Sin datos para {fecha_str}'}), 404

    inflacion_general = round(float(rows[0]['inflacion_general']), 4)
    suma = 0.0
    items = []
    for r in rows:
        ap = round(float(r['aporte']), 4)
        suma += ap
        infl_propia = round(float(r['inflacion_propia']), 4) if r.get('inflacion_propia') is not None else None
        items.append({
            'division': r['division'],
            'etiqueta': r['etiqueta'],
            'ponderacion': round(float(r['ponderacion']), 6),
            'indice_t': round(float(r['indice_div']), 4),
            'inflacion_propia': infl_propia,
            'aporte': ap,
        })

    return jsonify({
        'fecha': fecha_str,
        'inflacion_general': inflacion_general,
        'suma_aportes': round(suma, 4),
        'divisiones': items,
    })


@bp.route('/analisis-ipc/contribuciones-serie', methods=['GET'])
def get_contribuciones_serie():
    fd = request.args.get('fecha_desde')
    fh = request.args.get('fecha_hasta')
    if not fd or not fh:
        return jsonify({'error': 'fecha_desde y fecha_hasta requeridos'}), 400

    rows = execute_query(
        "SELECT division, etiqueta, fecha, aporte, inflacion_general "
        "FROM v_ipc_contribucion WHERE fecha >= %s AND fecha <= %s "
        "ORDER BY fecha, division", (fd, fh))

    by_div = {}
    inflacion_map = {}
    for r in rows:
        dv = r['division']
        if dv not in by_div:
            by_div[dv] = {'division': dv, 'etiqueta': r['etiqueta'], 'data': []}
        by_div[dv]['data'].append({
            'fecha': _d(r['fecha']),
            'valor': round(float(r['aporte']), 4)
        })
        f = _d(r['fecha'])
        if f not in inflacion_map:
            inflacion_map[f] = round(float(r['inflacion_general']), 4)

    sorted_fechas = sorted(inflacion_map.keys())
    inflacion_gral = [{'fecha': f, 'valor': inflacion_map[f]} for f in sorted_fechas]

    divs_sorted = sorted(by_div.keys())
    series = [by_div[d] for d in divs_sorted]

    return jsonify({
        'fecha_desde': fd, 'fecha_hasta': fh,
        'inflacion_general': inflacion_gral, 'series': series,
    })
