"""Admin routes for pais_grupo."""
from flask import Blueprint, request, jsonify
from ...database import execute_query, execute_query_single, execute_update
from ...middleware import admin_session_required

bp = Blueprint('admin_pais_grupo', __name__)


@bp.route('/pais-grupo', methods=['GET'])
@admin_session_required
def get_all_paises():
    """Get all pais_grupo."""
    try:
        query = """
            SELECT id_pais, nombre_pais_grupo
            FROM pais_grupo
            ORDER BY nombre_pais_grupo
        """
        results = execute_query(query)
        return jsonify(results)
    except Exception as e:
        return jsonify({'error': f'Error al obtener países: {str(e)}'}), 500


@bp.route('/pais-grupo/<int:pais_id>', methods=['GET'])
@admin_session_required
def get_pais(pais_id: int):
    """Get a single pais_grupo by ID."""
    try:
        query = """
            SELECT id_pais, nombre_pais_grupo
            FROM pais_grupo
            WHERE id_pais = ?
        """
        result = execute_query_single(query, (pais_id,))
        if not result:
            return jsonify({'error': 'País no encontrado'}), 404
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': f'Error al obtener país: {str(e)}'}), 500


@bp.route('/pais-grupo', methods=['POST'])
@admin_session_required
def create_pais():
    """Create a new pais_grupo."""
    try:
        data = request.get_json()
        if not data or 'nombre_pais_grupo' not in data:
            return jsonify({'error': 'Se requiere nombre_pais_grupo'}), 400
        
        nombre = data['nombre_pais_grupo'].strip()
        if not nombre:
            return jsonify({'error': 'nombre_pais_grupo no puede estar vacío'}), 400
        
        # Verificar si ya existe
        check_query = "SELECT id_pais FROM pais_grupo WHERE nombre_pais_grupo = ?"
        existing = execute_query_single(check_query, (nombre,))
        if existing:
            return jsonify({'error': 'Ya existe un país con ese nombre'}), 400
        
        # Insertar
        insert_query = """
            INSERT INTO pais_grupo (nombre_pais_grupo)
            VALUES (?)
        """
        success, error, lastrowid = execute_update(insert_query, (nombre,))
        
        if not success:
            return jsonify({'error': f'Error al crear país: {error}'}), 500
        
        return jsonify({'id_pais': lastrowid, 'nombre_pais_grupo': nombre}), 201
    
    except Exception as e:
        return jsonify({'error': f'Error al crear país: {str(e)}'}), 500


@bp.route('/pais-grupo/<int:pais_id>', methods=['PUT'])
@admin_session_required
def update_pais(pais_id: int):
    """Update a pais_grupo."""
    try:
        data = request.get_json()
        if not data or 'nombre_pais_grupo' not in data:
            return jsonify({'error': 'Se requiere nombre_pais_grupo'}), 400
        
        nombre = data['nombre_pais_grupo'].strip()
        if not nombre:
            return jsonify({'error': 'nombre_pais_grupo no puede estar vacío'}), 400
        
        # Verificar que existe
        check_query = "SELECT id_pais FROM pais_grupo WHERE id_pais = ?"
        existing = execute_query_single(check_query, (pais_id,))
        if not existing:
            return jsonify({'error': 'País no encontrado'}), 404
        
        # Verificar si el nuevo nombre ya existe en otro registro
        duplicate_query = "SELECT id_pais FROM pais_grupo WHERE nombre_pais_grupo = ? AND id_pais != ?"
        duplicate = execute_query_single(duplicate_query, (nombre, pais_id))
        if duplicate:
            return jsonify({'error': 'Ya existe otro país con ese nombre'}), 400
        
        # Actualizar
        update_query = """
            UPDATE pais_grupo
            SET nombre_pais_grupo = ?
            WHERE id_pais = ?
        """
        success, error, _ = execute_update(update_query, (nombre, pais_id))
        
        if not success:
            return jsonify({'error': f'Error al actualizar país: {error}'}), 500
        
        return jsonify({'id_pais': pais_id, 'nombre_pais_grupo': nombre}), 200
    
    except Exception as e:
        return jsonify({'error': f'Error al actualizar país: {str(e)}'}), 500


@bp.route('/pais-grupo/<int:pais_id>', methods=['DELETE'])
@admin_session_required
def delete_pais(pais_id: int):
    """Delete a pais_grupo."""
    try:
        # Verificar que existe
        check_query = "SELECT id_pais FROM pais_grupo WHERE id_pais = ?"
        existing = execute_query_single(check_query, (pais_id,))
        if not existing:
            return jsonify({'error': 'País no encontrado'}), 404
        
        # Verificar si está siendo usado en maestro o filtros_graph_pais
        maestro_query = "SELECT COUNT(*) as count FROM maestro WHERE id_pais = ?"
        maestro_count = execute_query_single(maestro_query, (pais_id,))
        if maestro_count and maestro_count.get('count', 0) > 0:
            return jsonify({'error': 'No se puede eliminar: el país está siendo usado en maestro'}), 400
        
        filtros_query = "SELECT COUNT(*) as count FROM filtros_graph_pais WHERE id_pais = ?"
        filtros_count = execute_query_single(filtros_query, (pais_id,))
        if filtros_count and filtros_count.get('count', 0) > 0:
            return jsonify({'error': 'No se puede eliminar: el país está siendo usado en filtros_graph_pais'}), 400
        
        # Eliminar
        delete_query = "DELETE FROM pais_grupo WHERE id_pais = ?"
        success, error, _ = execute_update(delete_query, (pais_id,))
        
        if not success:
            return jsonify({'error': f'Error al eliminar país: {error}'}), 500
        
        return jsonify({'message': 'País eliminado correctamente'}), 200
    
    except Exception as e:
        return jsonify({'error': f'Error al eliminar país: {str(e)}'}), 500
