"""Admin routes for tipo_serie."""
from flask import Blueprint, jsonify
from ...database import execute_query
from ...middleware import admin_only

bp = Blueprint('admin_tipo_serie', __name__)


@bp.route('/tipo-serie', methods=['GET'])
@admin_only
def get_all_tipo_serie():
    """Get all tipo_serie."""
    try:
        query = """
            SELECT id_tipo_serie, nombre_tipo_serie
            FROM tipo_serie
            ORDER BY id_tipo_serie
        """
        results = execute_query(query)
        
        # Asegurar que siempre devolvemos un array
        if not isinstance(results, list):
            print(f"[AdminAPI] Warning: execute_query no devolvió una lista, devolvió: {type(results)}")
            results = []
        
        print(f"[AdminAPI] get_all_tipo_serie: {len(results)} tipos de serie encontrados")
        return jsonify(results)
    except Exception as e:
        print(f"[AdminAPI] Error en get_all_tipo_serie: {str(e)}")
        import traceback
        traceback.print_exc()
        # En caso de error, devolver array vacío en lugar de error para que el frontend no falle
        return jsonify([])
