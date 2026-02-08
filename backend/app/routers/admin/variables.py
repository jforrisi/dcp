"""Admin routes for variables."""
from flask import Blueprint, request, jsonify
from ...database import execute_query, execute_query_single, execute_update
from ...middleware import admin_only

bp = Blueprint('admin_variables', __name__)


@bp.route('/variables', methods=['GET'])
@admin_only
def get_all_variables():
    """Get all variables, optionally filtered by sub_familia_id."""
    try:
        sub_familia_id = request.args.get('sub_familia_id', type=int)
        
        if sub_familia_id:
            query = """
                SELECT v.id_variable, v.id_nombre_variable, v.id_sub_familia, 
                       v.nominal_o_real, v.moneda, v.id_tipo_serie,
                       sf.nombre_sub_familia,
                       ts.nombre_tipo_serie as tipo_serie
                FROM variables v
                LEFT JOIN sub_familia sf ON v.id_sub_familia = sf.id_sub_familia
                LEFT JOIN tipo_serie ts ON v.id_tipo_serie = ts.id_tipo_serie
                WHERE v.id_sub_familia = ?
                ORDER BY v.id_nombre_variable
            """
            results = execute_query(query, (sub_familia_id,))
        else:
            query = """
                SELECT v.id_variable, v.id_nombre_variable, v.id_sub_familia, 
                       v.nominal_o_real, v.moneda, v.id_tipo_serie,
                       sf.nombre_sub_familia,
                       ts.nombre_tipo_serie as tipo_serie
                FROM variables v
                LEFT JOIN sub_familia sf ON v.id_sub_familia = sf.id_sub_familia
                LEFT JOIN tipo_serie ts ON v.id_tipo_serie = ts.id_tipo_serie
                ORDER BY v.id_nombre_variable
            """
            results = execute_query(query)
        
        return jsonify(results)
    except Exception as e:
        return jsonify({'error': f'Error al obtener variables: {str(e)}'}), 500


@bp.route('/variables/<int:variable_id>', methods=['GET'])
@admin_only
def get_variable(variable_id: int):
    """Get a single variable by ID."""
    try:
        query = """
            SELECT v.id_variable, v.id_nombre_variable, v.id_sub_familia, 
                   v.nominal_o_real, v.moneda, v.id_tipo_serie,
                   sf.nombre_sub_familia, sf.id_familia,
                   ts.nombre_tipo_serie as tipo_serie
            FROM variables v
            LEFT JOIN sub_familia sf ON v.id_sub_familia = sf.id_sub_familia
            LEFT JOIN tipo_serie ts ON v.id_tipo_serie = ts.id_tipo_serie
            WHERE v.id_variable = ?
        """
        result = execute_query_single(query, (variable_id,))
        if not result:
            return jsonify({'error': 'Variable no encontrada'}), 404
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': f'Error al obtener variable: {str(e)}'}), 500


@bp.route('/variables', methods=['POST'])
@admin_only
def create_variable():
    """Create a new variable."""
    try:
        data = request.get_json()
        if not data or 'id_nombre_variable' not in data:
            return jsonify({'error': 'Se requiere id_nombre_variable'}), 400
        
        nombre = data['id_nombre_variable'].strip()
        if not nombre:
            return jsonify({'error': 'id_nombre_variable no puede estar vacío'}), 400
        
        id_sub_familia = data.get('id_sub_familia')
        if id_sub_familia is not None:
            # Verificar que la sub_familia existe
            sub_familia_check = "SELECT id_sub_familia FROM sub_familia WHERE id_sub_familia = ?"
            sub_familia_exists = execute_query_single(sub_familia_check, (id_sub_familia,))
            if not sub_familia_exists:
                return jsonify({'error': 'La sub-familia especificada no existe'}), 400
        
        nominal_o_real = data.get('nominal_o_real', '').strip().lower()
        if nominal_o_real and nominal_o_real not in ['n', 'r']:
            return jsonify({'error': 'nominal_o_real solo puede ser "n" o "r"'}), 400
        if not nominal_o_real:
            nominal_o_real = None
        
        moneda = data.get('moneda', '').strip() or None
        
        # Validar y obtener id_tipo_serie
        id_tipo_serie = data.get('id_tipo_serie', 1)  # Default 1 = Original
        if id_tipo_serie is not None:
            # Verificar que el tipo_serie existe
            tipo_serie_check = "SELECT id_tipo_serie FROM tipo_serie WHERE id_tipo_serie = ?"
            tipo_serie_exists = execute_query_single(tipo_serie_check, (id_tipo_serie,))
            if not tipo_serie_exists:
                return jsonify({'error': 'El tipo de serie especificado no existe'}), 400
        else:
            id_tipo_serie = 1  # Default a Original
        
        # Verificar si ya existe
        check_query = "SELECT id_variable FROM variables WHERE id_nombre_variable = ?"
        existing = execute_query_single(check_query, (nombre,))
        if existing:
            return jsonify({'error': 'Ya existe una variable con ese nombre'}), 400
        
        # Insertar
        insert_query = """
            INSERT INTO variables (id_nombre_variable, id_sub_familia, nominal_o_real, moneda, id_tipo_serie)
            VALUES (?, ?, ?, ?, ?)
        """
        success, error, lastrowid = execute_update(insert_query, (nombre, id_sub_familia, nominal_o_real, moneda, id_tipo_serie))
        
        if not success:
            return jsonify({'error': f'Error al crear variable: {error}'}), 500
        
        return jsonify({
            'id_variable': lastrowid,
            'id_nombre_variable': nombre,
            'id_sub_familia': id_sub_familia,
            'nominal_o_real': nominal_o_real,
            'moneda': moneda,
            'id_tipo_serie': id_tipo_serie
        }), 201
    
    except Exception as e:
        return jsonify({'error': f'Error al crear variable: {str(e)}'}), 500


@bp.route('/variables/<int:variable_id>', methods=['PUT'])
@admin_only
def update_variable(variable_id: int):
    """Update a variable."""
    try:
        data = request.get_json()
        if not data or 'id_nombre_variable' not in data:
            return jsonify({'error': 'Se requiere id_nombre_variable'}), 400
        
        nombre = data['id_nombre_variable'].strip()
        if not nombre:
            return jsonify({'error': 'id_nombre_variable no puede estar vacío'}), 400
        
        id_sub_familia = data.get('id_sub_familia')
        if id_sub_familia is not None:
            # Verificar que la sub_familia existe
            sub_familia_check = "SELECT id_sub_familia FROM sub_familia WHERE id_sub_familia = ?"
            sub_familia_exists = execute_query_single(sub_familia_check, (id_sub_familia,))
            if not sub_familia_exists:
                return jsonify({'error': 'La sub-familia especificada no existe'}), 400
        
        nominal_o_real = data.get('nominal_o_real', '').strip().lower()
        if nominal_o_real and nominal_o_real not in ['n', 'r']:
            return jsonify({'error': 'nominal_o_real solo puede ser "n" o "r"'}), 400
        if not nominal_o_real:
            nominal_o_real = None
        
        moneda = data.get('moneda', '').strip() or None
        
        # Validar y obtener id_tipo_serie
        id_tipo_serie = data.get('id_tipo_serie', 1)
        if id_tipo_serie is not None:
            tipo_serie_check = "SELECT id_tipo_serie FROM tipo_serie WHERE id_tipo_serie = ?"
            tipo_serie_exists = execute_query_single(tipo_serie_check, (id_tipo_serie,))
            if not tipo_serie_exists:
                return jsonify({'error': 'El tipo de serie especificado no existe'}), 400
        else:
            id_tipo_serie = 1
        
        # Verificar que existe
        check_query = "SELECT id_variable FROM variables WHERE id_variable = ?"
        existing = execute_query_single(check_query, (variable_id,))
        if not existing:
            return jsonify({'error': 'Variable no encontrada'}), 404
        
        # Verificar si el nuevo nombre ya existe en otro registro
        duplicate_query = "SELECT id_variable FROM variables WHERE id_nombre_variable = ? AND id_variable != ?"
        duplicate = execute_query_single(duplicate_query, (nombre, variable_id))
        if duplicate:
            return jsonify({'error': 'Ya existe otra variable con ese nombre'}), 400
        
        # Actualizar
        update_query = """
            UPDATE variables
            SET id_nombre_variable = ?, id_sub_familia = ?, nominal_o_real = ?, moneda = ?, id_tipo_serie = ?
            WHERE id_variable = ?
        """
        success, error, _ = execute_update(update_query, (nombre, id_sub_familia, nominal_o_real, moneda, id_tipo_serie, variable_id))
        
        if not success:
            return jsonify({'error': f'Error al actualizar variable: {error}'}), 500
        
        return jsonify({
            'id_variable': variable_id,
            'id_nombre_variable': nombre,
            'id_sub_familia': id_sub_familia,
            'nominal_o_real': nominal_o_real,
            'moneda': moneda,
            'id_tipo_serie': id_tipo_serie
        }), 200
    
    except Exception as e:
        return jsonify({'error': f'Error al actualizar variable: {str(e)}'}), 500


@bp.route('/variables/<int:variable_id>', methods=['DELETE'])
@admin_only
def delete_variable(variable_id: int):
    """Delete a variable."""
    try:
        # Verificar que existe
        check_query = "SELECT id_variable FROM variables WHERE id_variable = ?"
        existing = execute_query_single(check_query, (variable_id,))
        if not existing:
            return jsonify({'error': 'Variable no encontrada'}), 404
        
        # Verificar si está siendo usada en maestro
        maestro_query = "SELECT COUNT(*) as count FROM maestro WHERE id_nombre_variable = ?"
        maestro_count = execute_query_single(maestro_query, (variable_id,))
        if maestro_count and maestro_count.get('count', 0) > 0:
            return jsonify({'error': 'No se puede eliminar: la variable está siendo usada en maestro'}), 400
        
        # Eliminar
        delete_query = "DELETE FROM variables WHERE id_variable = ?"
        success, error, _ = execute_update(delete_query, (variable_id,))
        
        if not success:
            return jsonify({'error': f'Error al eliminar variable: {error}'}), 500
        
        return jsonify({'message': 'Variable eliminada correctamente'}), 200
    
    except Exception as e:
        return jsonify({'error': f'Error al eliminar variable: {str(e)}'}), 500
