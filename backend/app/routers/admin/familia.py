"""Admin routes for familia."""
from flask import Blueprint, request, jsonify
from ...database import execute_query, execute_query_single, execute_update
from ...middleware import admin_session_required

bp = Blueprint('admin_familia', __name__)


@bp.route('/familia', methods=['GET'])
@admin_session_required
def get_all_familias():
    """Get all familias."""
    try:
        query = """
            SELECT id_familia, nombre_familia
            FROM familia
            ORDER BY nombre_familia
        """
        results = execute_query(query)
        
        # Asegurar que siempre devolvemos un array
        if not isinstance(results, list):
            print(f"[AdminAPI] Warning: execute_query no devolvió una lista, devolvió: {type(results)}")
            results = []
        
        print(f"[AdminAPI] get_all_familias: {len(results)} familias encontradas")
        return jsonify(results)
    except Exception as e:
        print(f"[AdminAPI] Error en get_all_familias: {str(e)}")
        import traceback
        traceback.print_exc()
        # En caso de error, devolver array vacío en lugar de error para que el frontend no falle
        return jsonify([])


@bp.route('/familia/<int:familia_id>', methods=['GET'])
@admin_session_required
def get_familia(familia_id: int):
    """Get a single familia by ID."""
    try:
        query = """
            SELECT id_familia, nombre_familia
            FROM familia
            WHERE id_familia = ?
        """
        result = execute_query_single(query, (familia_id,))
        if not result:
            return jsonify({'error': 'Familia no encontrada'}), 404
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': f'Error al obtener familia: {str(e)}'}), 500


@bp.route('/familia', methods=['POST'])
@admin_session_required
def create_familia():
    """Create a new familia."""
    try:
        data = request.get_json()
        if not data or 'nombre_familia' not in data:
            return jsonify({'error': 'Se requiere nombre_familia'}), 400
        
        nombre = data['nombre_familia'].strip()
        if not nombre:
            return jsonify({'error': 'nombre_familia no puede estar vacío'}), 400
        
        # Verificar si ya existe
        check_query = "SELECT id_familia FROM familia WHERE nombre_familia = ?"
        existing = execute_query_single(check_query, (nombre,))
        if existing:
            return jsonify({'error': 'Ya existe una familia con ese nombre'}), 400
        
        # Insertar
        insert_query = """
            INSERT INTO familia (nombre_familia)
            VALUES (?)
        """
        success, error, lastrowid = execute_update(insert_query, (nombre,))
        
        if not success:
            return jsonify({'error': f'Error al crear familia: {error}'}), 500
        
        return jsonify({'id_familia': lastrowid, 'nombre_familia': nombre}), 201
    
    except Exception as e:
        return jsonify({'error': f'Error al crear familia: {str(e)}'}), 500


@bp.route('/familia/<int:familia_id>', methods=['PUT'])
@admin_session_required
def update_familia(familia_id: int):
    """Update a familia."""
    try:
        data = request.get_json()
        if not data or 'nombre_familia' not in data:
            return jsonify({'error': 'Se requiere nombre_familia'}), 400
        
        nombre = data['nombre_familia'].strip()
        if not nombre:
            return jsonify({'error': 'nombre_familia no puede estar vacío'}), 400
        
        # Verificar que existe
        check_query = "SELECT id_familia FROM familia WHERE id_familia = ?"
        existing = execute_query_single(check_query, (familia_id,))
        if not existing:
            return jsonify({'error': 'Familia no encontrada'}), 404
        
        # Verificar si el nuevo nombre ya existe en otro registro
        duplicate_query = "SELECT id_familia FROM familia WHERE nombre_familia = ? AND id_familia != ?"
        duplicate = execute_query_single(duplicate_query, (nombre, familia_id))
        if duplicate:
            return jsonify({'error': 'Ya existe otra familia con ese nombre'}), 400
        
        # Actualizar
        update_query = """
            UPDATE familia
            SET nombre_familia = ?
            WHERE id_familia = ?
        """
        success, error, _ = execute_update(update_query, (nombre, familia_id))
        
        if not success:
            return jsonify({'error': f'Error al actualizar familia: {error}'}), 500
        
        return jsonify({'id_familia': familia_id, 'nombre_familia': nombre}), 200
    
    except Exception as e:
        return jsonify({'error': f'Error al actualizar familia: {str(e)}'}), 500


@bp.route('/familia/<int:familia_id>', methods=['DELETE'])
@admin_session_required
def delete_familia(familia_id: int):
    """Delete a familia."""
    try:
        # Verificar que existe
        check_query = "SELECT id_familia FROM familia WHERE id_familia = ?"
        existing = execute_query_single(check_query, (familia_id,))
        if not existing:
            return jsonify({'error': 'Familia no encontrada'}), 404
        
        # Verificar si tiene sub_familia asociadas
        sub_familia_query = "SELECT COUNT(*) as count FROM sub_familia WHERE id_familia = ?"
        sub_familia_count = execute_query_single(sub_familia_query, (familia_id,))
        if sub_familia_count and sub_familia_count.get('count', 0) > 0:
            return jsonify({'error': 'No se puede eliminar: la familia tiene sub-familias asociadas'}), 400
        
        # Eliminar
        delete_query = "DELETE FROM familia WHERE id_familia = ?"
        success, error, _ = execute_update(delete_query, (familia_id,))
        
        if not success:
            return jsonify({'error': f'Error al eliminar familia: {error}'}), 500
        
        return jsonify({'message': 'Familia eliminada correctamente'}), 200
    
    except Exception as e:
        return jsonify({'error': f'Error al eliminar familia: {str(e)}'}), 500
