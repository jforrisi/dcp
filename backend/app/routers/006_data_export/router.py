"""API routes for data export."""
from datetime import date, datetime
from typing import List, Dict, Optional
from io import BytesIO
from flask import Blueprint, request, jsonify, send_file
from openpyxl import Workbook
from openpyxl.styles import Font, Alignment, PatternFill
from ...database import execute_query, execute_query_single

bp = Blueprint('data_export', __name__)


@bp.route('/export/families', methods=['GET'])
def get_families():
    """Obtiene todas las familias."""
    try:
        query = """
            SELECT id_familia, nombre_familia
            FROM familia
            ORDER BY nombre_familia
        """
        results = execute_query(query)
        # Asegurarse de que siempre devolvemos un array
        if not isinstance(results, list):
            results = []
        return jsonify(results)
    except Exception as e:
        # En caso de error, devolver array vacío
        print(f"Error en get_families: {e}")
        return jsonify([])


@bp.route('/export/subfamilies', methods=['GET'])
def get_subfamilies():
    """Obtiene subfamilias, opcionalmente filtradas por familia."""
    try:
        familia_id = request.args.get('familia_id', type=int)
        
        if familia_id:
            query = """
                SELECT sf.id_sub_familia, sf.nombre_sub_familia, sf.id_familia, f.nombre_familia
                FROM sub_familia sf
                LEFT JOIN familia f ON sf.id_familia = f.id_familia
                WHERE sf.id_familia = ?
                ORDER BY sf.nombre_sub_familia
            """
            results = execute_query(query, (familia_id,))
        else:
            query = """
                SELECT sf.id_sub_familia, sf.nombre_sub_familia, sf.id_familia, f.nombre_familia
                FROM sub_familia sf
                LEFT JOIN familia f ON sf.id_familia = f.id_familia
                ORDER BY f.nombre_familia, sf.nombre_sub_familia
            """
            results = execute_query(query)
        
        # Asegurarse de que siempre devolvemos un array
        if not isinstance(results, list):
            results = []
        
        return jsonify(results)
    except Exception as e:
        # En caso de error, devolver array vacío
        print(f"Error en get_subfamilies: {e}")
        return jsonify([])


@bp.route('/export/variables', methods=['GET'])
def get_variables():
    """Obtiene variables, opcionalmente filtradas por subfamilias."""
    try:
        subfamilia_ids = request.args.getlist('subfamilia_ids[]', type=int)
        
        if subfamilia_ids:
            # Filtrar por subfamilias seleccionadas
            placeholders = ','.join(['?'] * len(subfamilia_ids))
            query = f"""
                SELECT DISTINCT
                    v.id_variable,
                    v.id_nombre_variable as nombre,
                    sf.id_sub_familia,
                    sf.nombre_sub_familia,
                    f.id_familia,
                    f.nombre_familia
                FROM variables v
                LEFT JOIN sub_familia sf ON v.id_sub_familia = sf.id_sub_familia
                LEFT JOIN familia f ON sf.id_familia = f.id_familia
                WHERE v.id_sub_familia IN ({placeholders})
                ORDER BY f.nombre_familia, sf.nombre_sub_familia, v.id_nombre_variable
            """
            results = execute_query(query, tuple(subfamilia_ids))
        else:
            # Devolver todas las variables
            query = """
                SELECT DISTINCT
                    v.id_variable,
                    v.id_nombre_variable as nombre,
                    sf.id_sub_familia,
                    sf.nombre_sub_familia,
                    f.id_familia,
                    f.nombre_familia
                FROM variables v
                LEFT JOIN sub_familia sf ON v.id_sub_familia = sf.id_sub_familia
                LEFT JOIN familia f ON sf.id_familia = f.id_familia
                ORDER BY f.nombre_familia, sf.nombre_sub_familia, v.id_nombre_variable
            """
            results = execute_query(query)
        
        # Asegurarse de que siempre devolvemos un array
        if not isinstance(results, list):
            results = []
        
        return jsonify(results)
    except Exception as e:
        # En caso de error, devolver array vacío en lugar de objeto de error
        print(f"Error en get_variables: {e}")
        return jsonify([])


@bp.route('/export/countries', methods=['GET'])
def get_countries():
    """Obtiene países disponibles para las variables seleccionadas."""
    try:
        variable_ids = request.args.getlist('variable_ids[]', type=int)
        
        if not variable_ids:
            return jsonify([])
        
        placeholders = ','.join(['?'] * len(variable_ids))
        query = f"""
            SELECT DISTINCT
                pg.id_pais,
                pg.nombre_pais_grupo as nombre_pais
            FROM maestro_precios mp
            LEFT JOIN pais_grupo pg ON mp.id_pais = pg.id_pais
            WHERE mp.id_variable IN ({placeholders})
            AND pg.nombre_pais_grupo IS NOT NULL
            ORDER BY pg.nombre_pais_grupo
        """
        results = execute_query(query, tuple(variable_ids))
        
        # Asegurarse de que siempre devolvemos un array
        if not isinstance(results, list):
            results = []
        
        return jsonify(results)
    except Exception as e:
        # En caso de error, devolver array vacío
        print(f"Error en get_countries: {e}")
        return jsonify([])


@bp.route('/export/preview', methods=['GET'])
def get_preview():
    """Obtiene preview de las últimas 10 filas de datos."""
    try:
        variable_ids = request.args.getlist('variable_ids[]', type=int)
        pais_ids = request.args.getlist('pais_ids[]', type=int)
        fecha_desde = request.args.get('fecha_desde')
        fecha_hasta = request.args.get('fecha_hasta')
        
        if not variable_ids or not pais_ids:
            return jsonify({'error': 'Se requieren variables y países'}), 400
        
        # Construir condiciones
        var_placeholders = ','.join(['?'] * len(variable_ids))
        pais_placeholders = ','.join(['?'] * len(pais_ids))
        params = list(variable_ids) + list(pais_ids)
        
        where_clauses = [
            f"mp.id_variable IN ({var_placeholders})",
            f"mp.id_pais IN ({pais_placeholders})"
        ]
        
        if fecha_desde:
            where_clauses.append("mp.fecha >= ?")
            params.append(fecha_desde)
        
        if fecha_hasta:
            where_clauses.append("mp.fecha <= ?")
            params.append(fecha_hasta)
        
        query = f"""
            SELECT 
                v.id_nombre_variable as variable,
                pg.nombre_pais_grupo as pais,
                mp.fecha,
                mp.valor
            FROM maestro_precios mp
            LEFT JOIN variables v ON mp.id_variable = v.id_variable
            LEFT JOIN pais_grupo pg ON mp.id_pais = pg.id_pais
            WHERE {' AND '.join(where_clauses)}
            ORDER BY mp.fecha DESC, v.id_nombre_variable, pg.nombre_pais_grupo
            LIMIT 10
        """
        
        results = execute_query(query, tuple(params))
        
        # Asegurarse de que siempre devolvemos un array
        if not isinstance(results, list):
            results = []
        
        return jsonify(results)
    except Exception as e:
        # En caso de error, devolver array vacío
        print(f"Error en get_preview: {e}")
        return jsonify([])


@bp.route('/export/download', methods=['GET'])
def download_excel():
    """Exporta datos a Excel."""
    try:
        variable_ids = request.args.getlist('variable_ids[]', type=int)
        pais_ids = request.args.getlist('pais_ids[]', type=int)
        fecha_desde = request.args.get('fecha_desde')
        fecha_hasta = request.args.get('fecha_hasta')
        
        if not variable_ids or not pais_ids:
            return jsonify({'error': 'Se requieren variables y países'}), 400
        
        # Construir query
        var_placeholders = ','.join(['?'] * len(variable_ids))
        pais_placeholders = ','.join(['?'] * len(pais_ids))
        params = list(variable_ids) + list(pais_ids)
        
        where_clauses = [
            f"mp.id_variable IN ({var_placeholders})",
            f"mp.id_pais IN ({pais_placeholders})"
        ]
        
        if fecha_desde:
            where_clauses.append("mp.fecha >= ?")
            params.append(fecha_desde)
        
        if fecha_hasta:
            where_clauses.append("mp.fecha <= ?")
            params.append(fecha_hasta)
        
        query = f"""
            SELECT 
                v.id_nombre_variable as variable,
                pg.nombre_pais_grupo as pais,
                mp.fecha,
                mp.valor
            FROM maestro_precios mp
            LEFT JOIN variables v ON mp.id_variable = v.id_variable
            LEFT JOIN pais_grupo pg ON mp.id_pais = pg.id_pais
            WHERE {' AND '.join(where_clauses)}
            ORDER BY v.id_nombre_variable, pg.nombre_pais_grupo, mp.fecha
        """
        
        results = execute_query(query, tuple(params))
        
        # Crear Excel
        wb = Workbook()
        ws = wb.active
        ws.title = "Datos"
        
        # Headers
        headers = ['Variable', 'País', 'Fecha', 'Valor']
        ws.append(headers)
        
        # Estilo headers
        header_fill = PatternFill(start_color="366092", end_color="366092", fill_type="solid")
        header_font = Font(bold=True, color="FFFFFF")
        for cell in ws[1]:
            cell.fill = header_fill
            cell.font = header_font
            cell.alignment = Alignment(horizontal="center")
        
        # Datos
        for row in results:
            ws.append([
                row['variable'],
                row['pais'],
                row['fecha'],
                row['valor']
            ])
        
        # Ajustar ancho de columnas
        ws.column_dimensions['A'].width = 30
        ws.column_dimensions['B'].width = 20
        ws.column_dimensions['C'].width = 12
        ws.column_dimensions['D'].width = 15
        
        # Guardar en BytesIO
        output = BytesIO()
        wb.save(output)
        output.seek(0)
        
        filename = f"exportacion_datos_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        return send_file(
            output,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name=filename
        )
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500
