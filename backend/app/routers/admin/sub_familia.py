"""Admin routes for sub_familia."""
from flask import Blueprint, request, jsonify
from ...database import execute_query, execute_query_single, execute_update
from ...middleware import admin_session_required

bp = Blueprint('admin_sub_familia', __name__)


@bp.route('/sub-familia', methods=['GET'])
@admin_session_required
def get_all_sub_familias():
    """Get all sub_familias, optionally filtered by familia_id."""
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
        
        return jsonify(results)
    except Exception as e:
        return jsonify({'error': f'Error al obtener sub-familias: {str(e)}'}), 500


@bp.route('/sub-familia/<int:sub_familia_id>', methods=['GET'])
@admin_session_required
def get_sub_familia(sub_familia_id: int):
    """Get a single sub_familia by ID."""
    try:
        query = """
            SELECT sf.id_sub_familia, sf.nombre_sub_familia, sf.id_familia, f.nombre_familia
            FROM sub_familia sf
            LEFT JOIN familia f ON sf.id_familia = f.id_familia
            WHERE sf.id_sub_familia = ?
        """
        result = execute_query_single(query, (sub_familia_id,))
        if not result:
            return jsonify({'error': 'Sub-familia no encontrada'}), 404
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': f'Error al obtener sub-familia: {str(e)}'}), 500


@bp.route('/sub-familia', methods=['POST'])
@admin_session_required
def create_sub_familia():
    """Create a new sub_familia."""
    try:
        data = request.get_json()
        if not data or 'nombre_sub_familia' not in data:
            return jsonify({'error': 'Se requiere nombre_sub_familia'}), 400
        
        nombre = data['nombre_sub_familia'].strip()
        if not nombre:
            return jsonify({'error': 'nombre_sub_familia no puede estar vacío'}), 400
        
        id_familia = data.get('id_familia')
        if id_familia is not None:
            # Verificar que la familia existe
            familia_check = "SELECT id_familia FROM familia WHERE id_familia = ?"
            familia_exists = execute_query_single(familia_check, (id_familia,))
            if not familia_exists:
                return jsonify({'error': 'La familia especificada no existe'}), 400
        
        # Verificar si ya existe
        check_query = "SELECT id_sub_familia FROM sub_familia WHERE nombre_sub_familia = ?"
        existing = execute_query_single(check_query, (nombre,))
        if existing:
            return jsonify({'error': 'Ya existe una sub-familia con ese nombre'}), 400
        
        # Insertar
        insert_query = """
            INSERT INTO sub_familia (nombre_sub_familia, id_familia)
            VALUES (?, ?)
        """
        success, error, lastrowid = execute_update(insert_query, (nombre, id_familia))
        
        if not success:
            return jsonify({'error': f'Error al crear sub-familia: {error}'}), 500
        
        return jsonify({'id_sub_familia': lastrowid, 'nombre_sub_familia': nombre, 'id_familia': id_familia}), 201
    
    except Exception as e:
        return jsonify({'error': f'Error al crear sub-familia: {str(e)}'}), 500


@bp.route('/sub-familia/<int:sub_familia_id>', methods=['PUT'])
@admin_session_required
def update_sub_familia(sub_familia_id: int):
    """Update a sub_familia."""
    try:
        data = request.get_json()
        if not data or 'nombre_sub_familia' not in data:
            return jsonify({'error': 'Se requiere nombre_sub_familia'}), 400
        
        nombre = data['nombre_sub_familia'].strip()
        if not nombre:
            return jsonify({'error': 'nombre_sub_familia no puede estar vacío'}), 400
        
        id_familia = data.get('id_familia')
        if id_familia is not None:
            # Verificar que la familia existe
            familia_check = "SELECT id_familia FROM familia WHERE id_familia = ?"
            familia_exists = execute_query_single(familia_check, (id_familia,))
            if not familia_exists:
                return jsonify({'error': 'La familia especificada no existe'}), 400
        
        # Verificar que existe
        check_query = "SELECT id_sub_familia FROM sub_familia WHERE id_sub_familia = ?"
        existing = execute_query_single(check_query, (sub_familia_id,))
        if not existing:
            return jsonify({'error': 'Sub-familia no encontrada'}), 404
        
        # Verificar si el nuevo nombre ya existe en otro registro
        duplicate_query = "SELECT id_sub_familia FROM sub_familia WHERE nombre_sub_familia = ? AND id_sub_familia != ?"
        duplicate = execute_query_single(duplicate_query, (nombre, sub_familia_id))
        if duplicate:
            return jsonify({'error': 'Ya existe otra sub-familia con ese nombre'}), 400
        
        # Actualizar
        update_query = """
            UPDATE sub_familia
            SET nombre_sub_familia = ?, id_familia = ?
            WHERE id_sub_familia = ?
        """
        success, error, _ = execute_update(update_query, (nombre, id_familia, sub_familia_id))
        
        if not success:
            return jsonify({'error': f'Error al actualizar sub-familia: {error}'}), 500
        
        return jsonify({'id_sub_familia': sub_familia_id, 'nombre_sub_familia': nombre, 'id_familia': id_familia}), 200
    
    except Exception as e:
        return jsonify({'error': f'Error al actualizar sub-familia: {str(e)}'}), 500


@bp.route('/sub-familia/<int:sub_familia_id>', methods=['DELETE'])
@admin_session_required
def delete_sub_familia(sub_familia_id: int):
    """Delete a sub_familia."""
    try:
        # Verificar que existe
        check_query = "SELECT id_sub_familia FROM sub_familia WHERE id_sub_familia = ?"
        existing = execute_query_single(check_query, (sub_familia_id,))
        if not existing:
            return jsonify({'error': 'Sub-familia no encontrada'}), 404
        
        # Verificar si tiene variables asociadas
        variables_query = "SELECT COUNT(*) as count FROM variables WHERE id_sub_familia = ?"
        variables_count = execute_query_single(variables_query, (sub_familia_id,))
        if variables_count and variables_count.get('count', 0) > 0:
            return jsonify({'error': 'No se puede eliminar: la sub-familia tiene variables asociadas'}), 400
        
        # Eliminar
        delete_query = "DELETE FROM sub_familia WHERE id_sub_familia = ?"
        success, error, _ = execute_update(delete_query, (sub_familia_id,))
        
        if not success:
            return jsonify({'error': f'Error al eliminar sub-familia: {error}'}), 500
        
        return jsonify({'message': 'Sub-familia eliminada correctamente'}), 200
    
    except Exception as e:
        return jsonify({'error': f'Error al eliminar sub-familia: {str(e)}'}), 500
