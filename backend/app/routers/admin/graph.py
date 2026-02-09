"""Admin routes for graph."""
from flask import Blueprint, request, jsonify
from ...database import execute_query, execute_query_single, execute_update
from ...middleware import admin_session_required

bp = Blueprint('admin_graph', __name__)


@bp.route('/graph', methods=['GET'])
@admin_session_required
def get_all_graphs():
    """Get all graphs."""
    try:
        query = """
            SELECT id_graph, nombre_graph, selector
            FROM graph
            ORDER BY id_graph
        """
        results = execute_query(query)
        return jsonify(results)
    except Exception as e:
        return jsonify({'error': f'Error al obtener graphs: {str(e)}'}), 500


@bp.route('/graph/<int:graph_id>', methods=['GET'])
@admin_session_required
def get_graph(graph_id: int):
    """Get a single graph by ID."""
    try:
        query = """
            SELECT id_graph, nombre_graph, selector
            FROM graph
            WHERE id_graph = ?
        """
        result = execute_query_single(query, (graph_id,))
        if not result:
            return jsonify({'error': 'Graph no encontrado'}), 404
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': f'Error al obtener graph: {str(e)}'}), 500


@bp.route('/graph/<int:graph_id>/filtros', methods=['GET'])
@admin_session_required
def get_graph_filtros(graph_id: int):
    """Get filtros for a specific graph."""
    try:
        query = """
            SELECT f.id_pais, pg.nombre_pais_grupo
            FROM filtros_graph_pais f
            JOIN pais_grupo pg ON f.id_pais = pg.id_pais
            WHERE f.id_graph = ?
            ORDER BY pg.nombre_pais_grupo
        """
        results = execute_query(query, (graph_id,))
        return jsonify(results)
    except Exception as e:
        return jsonify({'error': f'Error al obtener filtros: {str(e)}'}), 500


@bp.route('/graph', methods=['POST'])
@admin_session_required
def create_graph():
    """Create a new graph."""
    try:
        data = request.get_json()
        if not data or 'nombre_graph' not in data:
            return jsonify({'error': 'Se requiere nombre_graph'}), 400
        
        nombre = data['nombre_graph'].strip()
        if not nombre:
            return jsonify({'error': 'nombre_graph no puede estar vacío'}), 400
        
        selector = data.get('selector', '').strip() or None
        
        # Insertar
        insert_query = """
            INSERT INTO graph (nombre_graph, selector)
            VALUES (?, ?)
        """
        success, error, lastrowid = execute_update(insert_query, (nombre, selector))
        
        if not success:
            return jsonify({'error': f'Error al crear graph: {error}'}), 500
        
        return jsonify({'id_graph': lastrowid, 'nombre_graph': nombre, 'selector': selector}), 201
    
    except Exception as e:
        return jsonify({'error': f'Error al crear graph: {str(e)}'}), 500


@bp.route('/graph/<int:graph_id>', methods=['PUT'])
@admin_session_required
def update_graph(graph_id: int):
    """Update a graph."""
    try:
        data = request.get_json()
        if not data or 'nombre_graph' not in data:
            return jsonify({'error': 'Se requiere nombre_graph'}), 400
        
        nombre = data['nombre_graph'].strip()
        if not nombre:
            return jsonify({'error': 'nombre_graph no puede estar vacío'}), 400
        
        selector = data.get('selector', '').strip() or None
        
        # Verificar que existe
        check_query = "SELECT id_graph FROM graph WHERE id_graph = ?"
        existing = execute_query_single(check_query, (graph_id,))
        if not existing:
            return jsonify({'error': 'Graph no encontrado'}), 404
        
        # Actualizar
        update_query = """
            UPDATE graph
            SET nombre_graph = ?, selector = ?
            WHERE id_graph = ?
        """
        success, error, _ = execute_update(update_query, (nombre, selector, graph_id))
        
        if not success:
            return jsonify({'error': f'Error al actualizar graph: {error}'}), 500
        
        return jsonify({'id_graph': graph_id, 'nombre_graph': nombre, 'selector': selector}), 200
    
    except Exception as e:
        return jsonify({'error': f'Error al actualizar graph: {str(e)}'}), 500


@bp.route('/graph/<int:graph_id>', methods=['DELETE'])
@admin_session_required
def delete_graph(graph_id: int):
    """Delete a graph."""
    try:
        # Verificar que existe
        check_query = "SELECT id_graph FROM graph WHERE id_graph = ?"
        existing = execute_query_single(check_query, (graph_id,))
        if not existing:
            return jsonify({'error': 'Graph no encontrado'}), 404
        
        # Verificar si tiene filtros asociados
        filtros_query = "SELECT COUNT(*) as count FROM filtros_graph_pais WHERE id_graph = ?"
        filtros_count = execute_query_single(filtros_query, (graph_id,))
        if filtros_count and filtros_count.get('count', 0) > 0:
            return jsonify({'error': 'No se puede eliminar: el graph tiene filtros asociados'}), 400
        
        # Eliminar
        delete_query = "DELETE FROM graph WHERE id_graph = ?"
        success, error, _ = execute_update(delete_query, (graph_id,))
        
        if not success:
            return jsonify({'error': f'Error al eliminar graph: {error}'}), 500
        
        return jsonify({'message': 'Graph eliminado correctamente'}), 200
    
    except Exception as e:
        return jsonify({'error': f'Error al eliminar graph: {str(e)}'}), 500
