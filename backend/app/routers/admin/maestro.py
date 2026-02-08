"""Admin routes for maestro."""
from flask import Blueprint, request, jsonify
from ...database import execute_query, execute_query_single, execute_update
from ...middleware import admin_only

bp = Blueprint('admin_maestro', __name__)


@bp.route('/maestro', methods=['GET'])
@admin_only
def get_all_maestro():
    """Get all maestro records, with optional filters."""
    try:
        activo = request.args.get('activo', type=str)
        variable_id = request.args.get('variable_id', type=int)
        pais_id = request.args.get('pais_id', type=int)
        variable_nombre = request.args.get('variable_nombre', type=str)
        pais_nombre = request.args.get('pais_nombre', type=str)
        page = request.args.get('page', type=int, default=1)
        per_page = request.args.get('per_page', type=int, default=50)
        
        # Construir query con filtros opcionales
        where_clauses = []
        params = []
        
        if activo is not None:
            where_clauses.append("m.activo = ?")
            params.append(1 if activo.lower() == 'true' else 0)
        
        if variable_id is not None:
            where_clauses.append("m.id_variable = ?")
            params.append(variable_id)
        
        if pais_id is not None:
            where_clauses.append("m.id_pais = ?")
            params.append(pais_id)
        
        if variable_nombre:
            where_clauses.append("v.id_nombre_variable LIKE ?")
            params.append(f"%{variable_nombre}%")
        
        if pais_nombre:
            where_clauses.append("pg.nombre_pais_grupo LIKE ?")
            params.append(f"%{pais_nombre}%")
        
        where_sql = " WHERE " + " AND ".join(where_clauses) if where_clauses else ""
        
        # Calcular offset para paginación
        offset = (page - 1) * per_page
        
        query = f"""
            SELECT m.nombre, m.tipo, m.fuente, m.periodicidad, m.unidad, 
                   m.categoria, m.activo, m.es_cotizacion, m.pais,
                   m.id_variable, m.id_pais, m.link, m.script_update,
                   v.id_nombre_variable as variable_nombre,
                   pg.nombre_pais_grupo as pais_nombre,
                   COALESCE(COUNT(mp.fecha), 0) as cantidad_datos,
                   MAX(mp.fecha) as ultima_fecha
            FROM maestro m
            LEFT JOIN variables v ON m.id_variable = v.id_variable
            LEFT JOIN pais_grupo pg ON m.id_pais = pg.id_pais
            LEFT JOIN maestro_precios mp ON mp.id_variable = m.id_variable AND mp.id_pais = m.id_pais
            {where_sql}
            GROUP BY m.id_variable, m.id_pais, m.nombre, m.tipo, m.fuente, m.periodicidad, 
                     m.unidad, m.categoria, m.activo, m.es_cotizacion, m.pais, m.link, 
                     m.script_update, v.id_nombre_variable, pg.nombre_pais_grupo
            ORDER BY v.id_nombre_variable, pg.nombre_pais_grupo
            LIMIT ? OFFSET ?
        """
        
        params.extend([per_page, offset])
        results = execute_query(query, tuple(params))
        
        # Obtener total para paginación
        count_query = f"""
            SELECT COUNT(DISTINCT m.id_variable || '_' || m.id_pais) as total
            FROM maestro m
            LEFT JOIN variables v ON m.id_variable = v.id_variable
            LEFT JOIN pais_grupo pg ON m.id_pais = pg.id_pais
            {where_sql}
        """
        count_params = params[:-2]  # Remover LIMIT y OFFSET
        total_result = execute_query_single(count_query, tuple(count_params))
        total = total_result['total'] if total_result else 0
        
        return jsonify({
            'data': results,
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': total,
                'pages': (total + per_page - 1) // per_page if total > 0 else 0
            }
        })
    except Exception as e:
        return jsonify({'error': f'Error al obtener maestro: {str(e)}'}), 500


@bp.route('/maestro/<int:id_variable>/<int:id_pais>', methods=['GET'])
@admin_only
def get_maestro(id_variable: int, id_pais: int):
    """Get a single maestro record by composite key (id_variable, id_pais)."""
    try:
        query = """
            SELECT m.nombre, m.tipo, m.fuente, m.periodicidad, m.unidad, 
                   m.categoria, m.activo, m.es_cotizacion, m.pais,
                   m.id_variable, m.id_pais, m.link, m.script_update,
                   v.id_nombre_variable as variable_nombre,
                   pg.nombre_pais_grupo as pais_nombre
            FROM maestro m
            LEFT JOIN variables v ON m.id_variable = v.id_variable
            LEFT JOIN pais_grupo pg ON m.id_pais = pg.id_pais
            WHERE m.id_variable = ? AND m.id_pais = ?
        """
        result = execute_query_single(query, (id_variable, id_pais))
        if not result:
            return jsonify({'error': 'Registro maestro no encontrado'}), 404
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': f'Error al obtener maestro: {str(e)}'}), 500


@bp.route('/maestro', methods=['POST'])
@admin_only
def create_maestro():
    """Create a new maestro record."""
    try:
        data = request.get_json()
        
        # Periodicidad es obligatoria
        periodicidad = data.get('periodicidad', '').strip().upper()
        if not periodicidad:
            return jsonify({'error': 'La periodicidad es obligatoria'}), 400
        if periodicidad not in ['D', 'W', 'M']:
            return jsonify({'error': 'periodicidad solo puede ser "D", "W" o "M"'}), 400
        
        nombre = data.get('nombre', '').strip() or None
        tipo = data.get('tipo', '').strip().upper() or None
        fuente = data.get('fuente', '').strip() or None
        unidad = data.get('unidad', '').strip() or None
        categoria = None  # Eliminado
        
        activo = data.get('activo', True)
        if isinstance(activo, str):
            activo = activo.lower() == 'true'
        activo = 1 if activo else 0
        
        # Observaciones (mapeado desde 'observaciones' en el frontend, pero guardado como 'pais' en BD)
        observaciones = data.get('observaciones', '').strip() or None
        
        id_variable = data.get('id_variable')
        if id_variable is not None:
            # Verificar que la variable existe
            variable_check = "SELECT id_variable FROM variables WHERE id_variable = ?"
            variable_exists = execute_query_single(variable_check, (id_variable,))
            if not variable_exists:
                return jsonify({'error': 'La variable especificada no existe'}), 400
        
        id_pais = data.get('id_pais')
        if id_pais is not None:
            # Verificar que el país existe
            pais_check = "SELECT id_pais FROM pais_grupo WHERE id_pais = ?"
            pais_exists = execute_query_single(pais_check, (id_pais,))
            if not pais_exists:
                return jsonify({'error': 'El país especificado no existe'}), 400
        
        link = data.get('link', '').strip() or None
        script_update = data.get('script_update', '').strip() or None
        
        # Insertar (sin nombre, tipo, categoria, es_cotizacion)
        insert_query = """
            INSERT INTO maestro (nombre, tipo, fuente, periodicidad, unidad, categoria, 
                               activo, es_cotizacion, pais, id_variable, id_pais, link, script_update)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        # nombre y tipo pueden ser None, categoria es None, es_cotizacion es 0 por defecto
        es_cotizacion = 0  # Siempre 0, campo eliminado del formulario
        params = (nombre, tipo, fuente, periodicidad, unidad, categoria, activo, 
                 es_cotizacion, observaciones, id_variable, id_pais, link, script_update)
        
        # Verificar si ya existe un registro con esta clave compuesta
        if id_variable is not None and id_pais is not None:
            check_existing = "SELECT id_variable, id_pais FROM maestro WHERE id_variable = ? AND id_pais = ?"
            existing = execute_query_single(check_existing, (id_variable, id_pais))
            if existing:
                return jsonify({'error': 'Ya existe un registro con esta variable y país'}), 400
        
        success, error, _ = execute_update(insert_query, params)
        
        if not success:
            return jsonify({'error': f'Error al crear registro maestro: {error}'}), 500
        
        return jsonify({
            'nombre': nombre,
            'tipo': tipo,
            'fuente': fuente,
            'periodicidad': periodicidad,
            'unidad': unidad,
            'categoria': categoria,
            'activo': activo,
            'es_cotizacion': es_cotizacion,
            'pais': observaciones,  # Devolver como 'pais' para compatibilidad, pero viene de 'observaciones'
            'id_variable': id_variable,
            'id_pais': id_pais,
            'link': link,
            'script_update': script_update
        }), 201
    
    except Exception as e:
        return jsonify({'error': f'Error al crear registro maestro: {str(e)}'}), 500


@bp.route('/maestro/bulk', methods=['POST'])
@admin_only
def create_maestro_bulk():
    """Create multiple maestro records for the same variable but different countries."""
    try:
        data = request.get_json()
        
        # Periodicidad es obligatoria
        periodicidad = data.get('periodicidad', '').strip().upper()
        if not periodicidad:
            return jsonify({'error': 'La periodicidad es obligatoria'}), 400
        if periodicidad not in ['D', 'W', 'M']:
            return jsonify({'error': 'periodicidad solo puede ser "D", "W" o "M"'}), 400
        
        # Obtener lista de países
        id_paises = data.get('id_paises', [])
        if not id_paises or not isinstance(id_paises, list):
            return jsonify({'error': 'Debe proporcionar una lista de países (id_paises)'}), 400
        
        if len(id_paises) == 0:
            return jsonify({'error': 'Debe seleccionar al menos un país'}), 400
        
        nombre = data.get('nombre', '').strip() or None
        tipo = data.get('tipo', '').strip().upper() or None
        fuente = data.get('fuente', '').strip() or None
        unidad = data.get('unidad', '').strip() or None
        categoria = None  # Eliminado
        
        activo = data.get('activo', True)
        if isinstance(activo, str):
            activo = activo.lower() == 'true'
        activo = 1 if activo else 0
        
        # Observaciones (mapeado desde 'observaciones' en el frontend, pero guardado como 'pais' en BD)
        observaciones = data.get('observaciones', '').strip() or None
        
        id_variable = data.get('id_variable')
        if id_variable is None:
            return jsonify({'error': 'La variable es obligatoria'}), 400
        
        # Verificar que la variable existe
        variable_check = "SELECT id_variable FROM variables WHERE id_variable = ?"
        variable_exists = execute_query_single(variable_check, (id_variable,))
        if not variable_exists:
            return jsonify({'error': 'La variable especificada no existe'}), 400
        
        link = data.get('link', '').strip() or None
        script_update = data.get('script_update', '').strip() or None
        es_cotizacion = 0  # Siempre 0
        
        # Verificar que todos los países existen
        for id_pais in id_paises:
            pais_check = "SELECT id_pais FROM pais_grupo WHERE id_pais = ?"
            pais_exists = execute_query_single(pais_check, (id_pais,))
            if not pais_exists:
                return jsonify({'error': f'El país con id {id_pais} no existe'}), 400
        
        # Verificar duplicados antes de insertar
        placeholders = ','.join(['?' for _ in id_paises])
        check_existing_query = f"""
            SELECT id_variable, id_pais 
            FROM maestro 
            WHERE id_variable = ? AND id_pais IN ({placeholders})
        """
        existing_params = [id_variable] + id_paises
        existing_records = execute_query(check_existing_query, tuple(existing_params))
        
        if existing_records:
            existing_pairs = [f"variable {r['id_variable']} - país {r['id_pais']}" for r in existing_records]
            return jsonify({
                'error': f'Ya existen registros para: {", ".join(existing_pairs)}'
            }), 400
        
        # Insertar todos los registros
        insert_query = """
            INSERT INTO maestro (nombre, tipo, fuente, periodicidad, unidad, categoria, 
                               activo, es_cotizacion, pais, id_variable, id_pais, link, script_update)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        
        created_records = []
        errors = []
        
        for id_pais in id_paises:
            params = (nombre, tipo, fuente, periodicidad, unidad, categoria, activo, 
                     es_cotizacion, observaciones, id_variable, id_pais, link, script_update)
            
            success, error, _ = execute_update(insert_query, params)
            
            if success:
                created_records.append({
                    'id_variable': id_variable,
                    'id_pais': id_pais
                })
            else:
                errors.append(f'Error al crear registro para país {id_pais}: {error}')
        
        if errors:
            return jsonify({
                'error': 'Algunos registros no se pudieron crear',
                'details': errors,
                'created': created_records
            }), 207  # Multi-Status
        
        return jsonify({
            'message': f'Se crearon {len(created_records)} registros correctamente',
            'created': created_records
        }), 201
    
    except Exception as e:
        return jsonify({'error': f'Error al crear registros maestro: {str(e)}'}), 500


@bp.route('/maestro/<int:id_variable>/<int:id_pais>', methods=['PUT'])
@admin_only
def update_maestro(id_variable: int, id_pais: int):
    """Update a maestro record by composite key."""
    try:
        data = request.get_json()
        
        # Periodicidad es obligatoria
        periodicidad = data.get('periodicidad', '').strip().upper()
        if not periodicidad:
            return jsonify({'error': 'La periodicidad es obligatoria'}), 400
        if periodicidad not in ['D', 'W', 'M']:
            return jsonify({'error': 'periodicidad solo puede ser "D", "W" o "M"'}), 400
        
        nombre = data.get('nombre', '').strip() or None
        tipo = data.get('tipo', '').strip().upper() or None
        fuente = data.get('fuente', '').strip() or None
        unidad = data.get('unidad', '').strip() or None
        categoria = None  # Eliminado
        
        activo = data.get('activo', True)
        if isinstance(activo, str):
            activo = activo.lower() == 'true'
        activo = 1 if activo else 0
        
        es_cotizacion = 0  # Siempre 0, campo eliminado del formulario
        
        # Observaciones (mapeado desde 'observaciones' en el frontend, pero guardado como 'pais' en BD)
        observaciones = data.get('observaciones', '').strip() or None
        
        new_id_variable = data.get('id_variable')
        if new_id_variable is not None:
            # Verificar que la variable existe
            variable_check = "SELECT id_variable FROM variables WHERE id_variable = ?"
            variable_exists = execute_query_single(variable_check, (new_id_variable,))
            if not variable_exists:
                return jsonify({'error': 'La variable especificada no existe'}), 400
        
        new_id_pais = data.get('id_pais')
        if new_id_pais is not None:
            # Verificar que el país existe
            pais_check = "SELECT id_pais FROM pais_grupo WHERE id_pais = ?"
            pais_exists = execute_query_single(pais_check, (new_id_pais,))
            if not pais_exists:
                return jsonify({'error': 'El país especificado no existe'}), 400
        
        link = data.get('link', '').strip() or None
        script_update = data.get('script_update', '').strip() or None
        
        # Verificar que existe el registro original
        check_query = "SELECT id_variable, id_pais FROM maestro WHERE id_variable = ? AND id_pais = ?"
        existing = execute_query_single(check_query, (id_variable, id_pais))
        if not existing:
            return jsonify({'error': 'Registro maestro no encontrado'}), 404
        
        # Si se cambió la clave compuesta, verificar que no exista otro registro con la nueva clave
        if (new_id_variable is not None and new_id_pais is not None and 
            (new_id_variable != id_variable or new_id_pais != id_pais)):
            check_new_key = "SELECT id_variable, id_pais FROM maestro WHERE id_variable = ? AND id_pais = ?"
            new_key_exists = execute_query_single(check_new_key, (new_id_variable, new_id_pais))
            if new_key_exists:
                return jsonify({'error': 'Ya existe otro registro con la nueva variable y país'}), 400
        
        # Actualizar (usar los nuevos valores si se proporcionaron, sino mantener los originales)
        final_id_variable = new_id_variable if new_id_variable is not None else id_variable
        final_id_pais = new_id_pais if new_id_pais is not None else id_pais
        
        update_query = """
            UPDATE maestro
            SET nombre = ?, tipo = ?, fuente = ?, periodicidad = ?, unidad = ?, 
                categoria = ?, activo = ?, es_cotizacion = ?, pais = ?, 
                id_variable = ?, id_pais = ?, link = ?, script_update = ?
            WHERE id_variable = ? AND id_pais = ?
        """
        params = (nombre, tipo, fuente, periodicidad, unidad, categoria, activo, 
                 es_cotizacion, observaciones, final_id_variable, final_id_pais, link, script_update,
                 id_variable, id_pais)
        
        success, error, _ = execute_update(update_query, params)
        
        if not success:
            return jsonify({'error': f'Error al actualizar registro maestro: {error}'}), 500
        
        return jsonify({
            'nombre': nombre,
            'tipo': tipo,
            'fuente': fuente,
            'periodicidad': periodicidad,
            'unidad': unidad,
            'categoria': categoria,
            'activo': activo,
            'es_cotizacion': es_cotizacion,
            'pais': observaciones,  # Devolver como 'pais' para compatibilidad, pero viene de 'observaciones'
            'id_variable': final_id_variable,
            'id_pais': final_id_pais,
            'link': link,
            'script_update': script_update
        }), 200
    
    except Exception as e:
        return jsonify({'error': f'Error al actualizar registro maestro: {str(e)}'}), 500


@bp.route('/maestro/<int:id_variable>/<int:id_pais>', methods=['DELETE'])
@admin_only
def delete_maestro(id_variable: int, id_pais: int):
    """Delete a maestro record by composite key."""
    try:
        # Verificar que existe
        check_query = "SELECT id_variable, id_pais FROM maestro WHERE id_variable = ? AND id_pais = ?"
        existing = execute_query_single(check_query, (id_variable, id_pais))
        if not existing:
            return jsonify({'error': 'Registro maestro no encontrado'}), 404
        
        # Verificar si tiene precios asociados
        precios_query = "SELECT COUNT(*) as count FROM maestro_precios WHERE id_variable = ? AND id_pais = ?"
        precios_count = execute_query_single(precios_query, (id_variable, id_pais))
        if precios_count and precios_count.get('count', 0) > 0:
            return jsonify({'error': 'No se puede eliminar: el registro tiene precios asociados'}), 400
        
        # Eliminar
        delete_query = "DELETE FROM maestro WHERE id_variable = ? AND id_pais = ?"
        success, error, _ = execute_update(delete_query, (id_variable, id_pais))
        
        if not success:
            return jsonify({'error': f'Error al eliminar registro maestro: {error}'}), 500
        
        return jsonify({'message': 'Registro maestro eliminado correctamente'}), 200
    
    except Exception as e:
        return jsonify({'error': f'Error al eliminar registro maestro: {str(e)}'}), 500
