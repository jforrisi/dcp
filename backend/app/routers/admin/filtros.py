"""Admin routes for filtros_graph_pais."""
from flask import Blueprint, request, jsonify
from ...database import execute_query, execute_query_single, execute_update
from ...middleware import admin_only

bp = Blueprint('admin_filtros', __name__)


@bp.route('/filtros', methods=['GET'])
@admin_only
def get_filtros():
    """Get filtros, optionally filtered by graph_id."""
    try:
        graph_id = request.args.get('graph_id', type=int)
        
        if graph_id:
            query = """
                SELECT f.id_graph, f.id_pais, pg.nombre_pais_grupo, g.nombre_graph
                FROM filtros_graph_pais f
                JOIN pais_grupo pg ON f.id_pais = pg.id_pais
                JOIN graph g ON f.id_graph = g.id_graph
                WHERE f.id_graph = ?
                ORDER BY pg.nombre_pais_grupo
            """
            results = execute_query(query, (graph_id,))
        else:
            query = """
                SELECT f.id_graph, f.id_pais, pg.nombre_pais_grupo, g.nombre_graph
                FROM filtros_graph_pais f
                JOIN pais_grupo pg ON f.id_pais = pg.id_pais
                JOIN graph g ON f.id_graph = g.id_graph
                ORDER BY g.nombre_graph, pg.nombre_pais_grupo
            """
            results = execute_query(query)
        
        return jsonify(results)
    except Exception as e:
        return jsonify({'error': f'Error al obtener filtros: {str(e)}'}), 500


@bp.route('/filtros', methods=['POST'])
@admin_only
def create_filtro():
    """Add a filtro (graph_id, pais_id)."""
    try:
        data = request.get_json()
        if not data or 'id_graph' not in data or 'id_pais' not in data:
            return jsonify({'error': 'Se requiere id_graph e id_pais'}), 400
        
        graph_id = data['id_graph']
        pais_id = data['id_pais']
        
        # Verificar que graph existe
        graph_check = "SELECT id_graph FROM graph WHERE id_graph = ?"
        graph_exists = execute_query_single(graph_check, (graph_id,))
        if not graph_exists:
            return jsonify({'error': 'El graph especificado no existe'}), 400
        
        # Verificar que pais existe
        pais_check = "SELECT id_pais FROM pais_grupo WHERE id_pais = ?"
        pais_exists = execute_query_single(pais_check, (pais_id,))
        if not pais_exists:
            return jsonify({'error': 'El país especificado no existe'}), 400
        
        # Verificar si ya existe
        check_query = "SELECT id_graph, id_pais FROM filtros_graph_pais WHERE id_graph = ? AND id_pais = ?"
        existing = execute_query_single(check_query, (graph_id, pais_id))
        if existing:
            return jsonify({'error': 'Ya existe este filtro'}), 400
        
        # Insertar
        insert_query = """
            INSERT INTO filtros_graph_pais (id_graph, id_pais)
            VALUES (?, ?)
        """
        success, error, _ = execute_update(insert_query, (graph_id, pais_id))
        
        if not success:
            return jsonify({'error': f'Error al crear filtro: {error}'}), 500
        
        return jsonify({'id_graph': graph_id, 'id_pais': pais_id, 'message': 'Filtro creado correctamente'}), 201
    
    except Exception as e:
        return jsonify({'error': f'Error al crear filtro: {str(e)}'}), 500


@bp.route('/filtros', methods=['DELETE'])
@admin_only
def delete_filtro():
    """Delete a filtro (using query params: graph_id, pais_id)."""
    try:
        graph_id = request.args.get('graph_id', type=int)
        pais_id = request.args.get('id_pais', type=int)
        
        if not graph_id or not pais_id:
            return jsonify({'error': 'Se requiere graph_id e id_pais como query params'}), 400
        
        # Verificar que existe
        check_query = "SELECT id_graph, id_pais FROM filtros_graph_pais WHERE id_graph = ? AND id_pais = ?"
        existing = execute_query_single(check_query, (graph_id, pais_id))
        if not existing:
            return jsonify({'error': 'Filtro no encontrado'}), 404
        
        # Eliminar
        delete_query = "DELETE FROM filtros_graph_pais WHERE id_graph = ? AND id_pais = ?"
        success, error, _ = execute_update(delete_query, (graph_id, pais_id))
        
        if not success:
            return jsonify({'error': f'Error al eliminar filtro: {error}'}), 500
        
        return jsonify({'message': 'Filtro eliminado correctamente'}), 200
    
    except Exception as e:
        return jsonify({'error': f'Error al eliminar filtro: {str(e)}'}), 500


@bp.route('/filtros/bulk', methods=['PUT'])
@admin_only
def update_filtros_bulk():
    """Update multiple filtros for a graph (replaces all existing filtros)."""
    try:
        data = request.get_json()
        if not data or 'id_graph' not in data:
            return jsonify({'error': 'Se requiere id_graph'}), 400
        
        graph_id = data['id_graph']
        pais_ids = data.get('pais_ids', [])
        
        # Verificar que graph existe
        graph_check = "SELECT id_graph FROM graph WHERE id_graph = ?"
        graph_exists = execute_query_single(graph_check, (graph_id,))
        if not graph_exists:
            return jsonify({'error': 'El graph especificado no existe'}), 400
        
        # Verificar que todos los países existen
        if pais_ids:
            placeholders = ','.join(['?'] * len(pais_ids))
            pais_check_query = f"SELECT COUNT(*) as count FROM pais_grupo WHERE id_pais IN ({placeholders})"
            pais_count = execute_query_single(pais_check_query, tuple(pais_ids))
            if pais_count and pais_count.get('count', 0) != len(pais_ids):
                return jsonify({'error': 'Uno o más países no existen'}), 400
        
        # Eliminar filtros existentes para este graph
        delete_query = "DELETE FROM filtros_graph_pais WHERE id_graph = ?"
        success, error, _ = execute_update(delete_query, (graph_id,))
        if not success:
            return jsonify({'error': f'Error al eliminar filtros existentes: {error}'}), 500
        
        # Insertar nuevos filtros
        if pais_ids:
            insert_query = "INSERT INTO filtros_graph_pais (id_graph, id_pais) VALUES (?, ?)"
            for pais_id in pais_ids:
                success, error, _ = execute_update(insert_query, (graph_id, pais_id))
                if not success:
                    return jsonify({'error': f'Error al crear filtro: {error}'}), 500
        
        return jsonify({
            'id_graph': graph_id,
            'pais_ids': pais_ids,
            'message': f'Filtros actualizados correctamente ({len(pais_ids)} países)'
        }), 200
    
    except Exception as e:
        return jsonify({'error': f'Error al actualizar filtros: {str(e)}'}), 500
