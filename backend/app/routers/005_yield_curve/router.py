"""API routes for Yield Curve (Curva de Rendimiento)."""
from datetime import date, datetime, timedelta
from typing import List, Dict, Optional
from flask import Blueprint, request, jsonify
from ...database import execute_query, execute_query_single

bp = Blueprint('yield_curve', __name__)

# Configuración de variables de la curva de rendimiento
# Mapeo de nombres a id_variable para nominales y reales
# Nominales: id_variable 37-51
YIELD_CURVE_VARIABLES_NOMINAL = {
    "1 mes": 37,
    "2 meses": 38,
    "3 meses": 39,
    "6 meses": 40,
    "9 meses": 41,
    "1 año": 42,
    "2 años": 43,
    "3 años": 44,
    "4 años": 45,
    "5 años": 46,
    "6 años": 47,
    "7 años": 48,
    "8 años": 49,
    "9 años": 50,
    "10 años": 51,
}

# Reales: id_variable 73-84, 69-72
YIELD_CURVE_VARIABLES_REAL = {
    "3 meses": 73,
    "6 meses": 74,
    "1 año": 75,
    "2 años": 76,
    "3 años": 77,
    "4 años": 78,
    "5 años": 79,
    "6 años": 80,
    "7 años": 81,
    "8 años": 82,
    "9 años": 83,
    "10 años": 84,
    "15 años": 69,
    "20 años": 70,
    "25 años": 71,
    "30 años": 72,
}

ID_PAIS = 858  # Uruguay
ID_SUB_FAMILIA = 10  # Curva soberana


def get_yield_curve_variables(tipo: str):
    """
    Obtiene el diccionario de variables según el tipo.
    
    Args:
        tipo: 'nominal' o 'real'
    
    Returns:
        Dict con nombre -> id_variable
    """
    if tipo == 'real':
        return YIELD_CURVE_VARIABLES_REAL
    else:  # nominal por defecto
        return YIELD_CURVE_VARIABLES_NOMINAL


def parse_fecha(fecha_val):
    """Convierte fecha de SQLite (puede ser date o datetime string) a date."""
    if isinstance(fecha_val, date):
        return fecha_val
    fecha_str = str(fecha_val)
    # Si tiene hora (contiene espacio), tomar solo la parte de fecha
    if ' ' in fecha_str:
        fecha_str = fecha_str.split(' ')[0]
    return date.fromisoformat(fecha_str)


def obtener_ultima_fecha_disponible(tipo: Optional[str] = None) -> Optional[date]:
    """
    Obtiene la última fecha disponible para las variables de la curva.
    
    Args:
        tipo: 'nominal', 'real', o None para ambos
    
    Returns:
        date o None si no hay datos
    """
    # Obtener todas las id_variable según el tipo
    if tipo:
        variables = get_yield_curve_variables(tipo)
        id_variables = list(variables.values())
    else:
        # Ambos tipos
        id_variables = list(YIELD_CURVE_VARIABLES_NOMINAL.values()) + list(YIELD_CURVE_VARIABLES_REAL.values())
    
    if not id_variables:
        return None
    
    # Construir query para obtener la fecha máxima
    placeholders = ','.join(['?' for _ in id_variables])
    query = f"""
        SELECT MAX(fecha) as ultima_fecha
        FROM maestro_precios
        WHERE id_pais = ? 
        AND id_variable IN ({placeholders})
    """
    params = [ID_PAIS] + id_variables
    
    result = execute_query_single(query, tuple(params))
    
    if result and result.get('ultima_fecha'):
        return parse_fecha(result['ultima_fecha'])
    
    return None


@bp.route('/yield-curve/dates', methods=['GET'])
def get_yield_curve_dates():
    """
    Obtiene las fechas disponibles para la curva de rendimiento.
    Considera tanto variables nominales como reales.
    
    Returns:
        {
            "ultima_fecha": "YYYY-MM-DD",
            "fechas_disponibles": ["YYYY-MM-DD", ...]
        }
    """
    try:
        # Obtener fechas de ambos tipos (nominal y real)
        id_variables = list(YIELD_CURVE_VARIABLES_NOMINAL.values()) + list(YIELD_CURVE_VARIABLES_REAL.values())
        
        if not id_variables:
            return jsonify({
                "ultima_fecha": None,
                "fechas_disponibles": []
            })
        
        placeholders = ','.join(['?' for _ in id_variables])
        
        # Obtener última fecha
        query_max = f"""
            SELECT MAX(fecha) as ultima_fecha
            FROM maestro_precios
            WHERE id_pais = ? 
            AND id_variable IN ({placeholders})
        """
        result_max = execute_query_single(query_max, tuple([ID_PAIS] + id_variables))
        ultima_fecha = None
        if result_max and result_max.get('ultima_fecha'):
            ultima_fecha = parse_fecha(result_max['ultima_fecha'])
        
        # Obtener todas las fechas disponibles (únicas)
        query = f"""
            SELECT DISTINCT fecha
            FROM maestro_precios
            WHERE id_pais = ? 
            AND id_variable IN ({placeholders})
            ORDER BY fecha DESC
        """
        params = [ID_PAIS] + id_variables
        
        fechas_raw = execute_query(query, tuple(params))
        fechas_disponibles = sorted([parse_fecha(f['fecha']) for f in fechas_raw], reverse=True)
        
        return jsonify({
            "ultima_fecha": ultima_fecha.isoformat() if ultima_fecha else None,
            "fechas_disponibles": [f.isoformat() for f in fechas_disponibles]
        })
    
    except Exception as e:
        return jsonify({'error': f'Error al obtener fechas: {str(e)}'}), 500


@bp.route('/yield-curve/data', methods=['GET'])
def get_yield_curve_data():
    """
    Obtiene los datos de la curva de rendimiento para una fecha específica.
    
    Query params:
    - fecha: Fecha en formato YYYY-MM-DD (opcional, por defecto usa la última fecha disponible)
    - tipo: 'nominal' o 'real' (opcional, por defecto 'nominal')
    
    Returns:
        {
            "fecha": "YYYY-MM-DD",
            "data": [
                {
                    "nombre": "1 mes",
                    "id_variable": 37,
                    "valor": 5.25
                },
                ...
            ]
        }
    """
    try:
        fecha_str = request.args.get('fecha')
        tipo = request.args.get('tipo', 'nominal').lower()
        
        if tipo not in ['nominal', 'real']:
            return jsonify({'error': 'Tipo debe ser "nominal" o "real"'}), 400
        
        # Si no se proporciona fecha, usar la última disponible para el tipo especificado
        if not fecha_str:
            fecha_obj = obtener_ultima_fecha_disponible(tipo)
            if not fecha_obj:
                return jsonify({'error': 'No hay datos disponibles'}), 404
        else:
            fecha_obj = date.fromisoformat(fecha_str)
        
        fecha_str_query = fecha_obj.isoformat()
        
        # Obtener variables según el tipo
        variables = get_yield_curve_variables(tipo)
        
        # Obtener datos para todas las variables de la curva en la fecha especificada
        result_data = []
        
        for nombre, id_variable in variables.items():
            query = """
                SELECT valor
                FROM maestro_precios
                WHERE id_variable = ? AND id_pais = ? 
                AND DATE(fecha) = DATE(?)
                ORDER BY fecha DESC
                LIMIT 1
            """
            
            result = execute_query_single(query, (id_variable, ID_PAIS, fecha_str_query))
            
            valor = result['valor'] if result and result.get('valor') is not None else None
            
            result_data.append({
                "nombre": nombre,
                "id_variable": id_variable,
                "valor": float(valor) if valor is not None else None
            })
        
        return jsonify({
            "fecha": fecha_obj.isoformat(),
            "data": result_data
        })
    
    except ValueError as e:
        return jsonify({'error': f'Error en formato de fecha: {str(e)}'}), 400
    except Exception as e:
        return jsonify({'error': f'Error al obtener datos de curva: {str(e)}'}), 500


@bp.route('/yield-curve/table', methods=['GET'])
def get_yield_curve_table():
    """
    Obtiene la tabla con las tasas, último valor y variaciones.
    
    Query params:
    - fecha: Fecha en formato YYYY-MM-DD (opcional, por defecto usa la última fecha disponible)
    - tipo: 'nominal' o 'real' (opcional, por defecto 'nominal')
    
    Returns:
        {
            "fecha_referencia": "YYYY-MM-DD",
            "data": [
                {
                    "nombre": "1 mes",
                    "id_variable": 37,
                    "valor_referencia": 5.25,
                    "variacion_5_dias": 0.10,
                    "variacion_30_dias": 0.25,
                    "variacion_360_dias": 1.50,
                    "variacion_anio_actual": 0.75
                },
                ...
            ]
        }
    """
    try:
        # Obtener fecha y tipo del parámetro
        fecha_str = request.args.get('fecha')
        tipo = request.args.get('tipo', 'nominal').lower()
        
        if tipo not in ['nominal', 'real']:
            return jsonify({'error': 'Tipo debe ser "nominal" o "real"'}), 400
        
        if fecha_str:
            try:
                fecha_referencia = date.fromisoformat(fecha_str)
            except ValueError:
                return jsonify({'error': 'Formato de fecha inválido. Use YYYY-MM-DD'}), 400
        else:
            fecha_referencia = obtener_ultima_fecha_disponible(tipo)
        
        if not fecha_referencia:
            return jsonify({
                "fecha_referencia": None,
                "data": []
            })
        
        fecha_referencia_str = fecha_referencia.isoformat()
        
        # Obtener variables según el tipo
        variables = get_yield_curve_variables(tipo)
        
        result_data = []
        
        for nombre, id_variable in variables.items():
            
            # Obtener valor para la fecha de referencia
            query_valor = """
                SELECT valor
                FROM maestro_precios
                WHERE id_variable = ? AND id_pais = ? 
                AND DATE(fecha) = DATE(?)
                ORDER BY fecha DESC
                LIMIT 1
            """
            result_valor = execute_query_single(query_valor, (id_variable, ID_PAIS, fecha_referencia_str))
            valor_referencia = result_valor['valor'] if result_valor and result_valor.get('valor') is not None else None
            
            if valor_referencia is None:
                result_data.append({
                    "nombre": nombre,
                    "id_variable": id_variable,
                    "valor_referencia": None,
                    "variacion_5_dias": None,
                    "variacion_30_dias": None,
                    "variacion_360_dias": None,
                    "variacion_anio_actual": None
                })
                continue
            
            valor_referencia = float(valor_referencia)
            
            # Calcular fechas de referencia para variaciones
            fecha_5_dias = fecha_referencia - timedelta(days=5)
            fecha_30_dias = fecha_referencia - timedelta(days=30)
            fecha_360_dias = fecha_referencia - timedelta(days=360)
            fecha_inicio_anio = date(fecha_referencia.year, 1, 1)
            
            # Función helper para obtener valor en una fecha (o la más cercana anterior)
            def obtener_valor_en_fecha(fecha_obj):
                fecha_str = fecha_obj.isoformat()
                query = """
                    SELECT valor
                    FROM maestro_precios
                    WHERE id_variable = ? AND id_pais = ? 
                    AND DATE(fecha) <= DATE(?)
                    ORDER BY fecha DESC
                    LIMIT 1
                """
                result = execute_query_single(query, (id_variable, ID_PAIS, fecha_str))
                if result and result.get('valor') is not None:
                    return float(result['valor'])
                return None
            
            # Obtener valores de referencia para variaciones
            valor_5_dias = obtener_valor_en_fecha(fecha_5_dias)
            valor_30_dias = obtener_valor_en_fecha(fecha_30_dias)
            valor_360_dias = obtener_valor_en_fecha(fecha_360_dias)
            valor_inicio_anio = obtener_valor_en_fecha(fecha_inicio_anio)
            
            # Calcular variaciones (en puntos porcentuales)
            def calcular_variacion(valor_anterior, valor_actual):
                if valor_anterior is None or valor_actual is None:
                    return None
                if valor_anterior == 0:
                    return None
                return valor_actual - valor_anterior  # Diferencia en puntos porcentuales
            
            variacion_5_dias = calcular_variacion(valor_5_dias, valor_referencia)
            variacion_30_dias = calcular_variacion(valor_30_dias, valor_referencia)
            variacion_360_dias = calcular_variacion(valor_360_dias, valor_referencia)
            variacion_anio_actual = calcular_variacion(valor_inicio_anio, valor_referencia)
            
            result_data.append({
                "nombre": nombre,
                "id_variable": id_variable,
                "valor_referencia": valor_referencia,
                "variacion_5_dias": round(variacion_5_dias, 4) if variacion_5_dias is not None else None,
                "variacion_30_dias": round(variacion_30_dias, 4) if variacion_30_dias is not None else None,
                "variacion_360_dias": round(variacion_360_dias, 4) if variacion_360_dias is not None else None,
                "variacion_anio_actual": round(variacion_anio_actual, 4) if variacion_anio_actual is not None else None
            })
        
        return jsonify({
            "fecha_referencia": fecha_referencia_str,
            "data": result_data
        })
    
    except Exception as e:
        return jsonify({'error': f'Error al obtener tabla: {str(e)}'}), 500


@bp.route('/yield-curve/timeseries', methods=['GET'])
def get_yield_curve_timeseries():
    """
    Obtiene datos históricos de tasas para plazos seleccionados.
    
    Query params:
    - id_variables[]: Array de id_variable (plazos) a mostrar
    - fecha_desde: YYYY-MM-DD
    - fecha_hasta: YYYY-MM-DD
    
    Returns:
    {
        "data": [
            {
                "id_variable": 40,
                "nombre": "6 meses",
                "data": [
                    {"fecha": "2025-01-01", "valor": 5.25},
                    ...
                ]
            },
            ...
        ]
    }
    """
    try:
        id_variables = request.args.getlist('id_variables[]')
        fecha_desde = request.args.get('fecha_desde')
        fecha_hasta = request.args.get('fecha_hasta')
        
        if not id_variables:
            return jsonify({'error': 'Debe seleccionar al menos un plazo'}), 400
        
        if not fecha_desde or not fecha_hasta:
            return jsonify({'error': 'Debe proporcionar fecha_desde y fecha_hasta'}), 400
        
        try:
            fecha_desde_obj = date.fromisoformat(fecha_desde)
            fecha_hasta_obj = date.fromisoformat(fecha_hasta)
        except ValueError:
            return jsonify({'error': 'Formato de fecha inválido. Use YYYY-MM-DD'}), 400
        
        result_data = []
        
        for id_var_str in id_variables:
            try:
                id_variable = int(id_var_str)
            except ValueError:
                continue
            
            # Buscar el nombre del plazo en nominales o reales
            plazo_nombre = None
            plazo_tipo = None
            
            # Buscar en nominales
            for nombre, var_id in YIELD_CURVE_VARIABLES_NOMINAL.items():
                if var_id == id_variable:
                    plazo_nombre = nombre
                    plazo_tipo = 'nominal'
                    break
            
            # Si no está en nominales, buscar en reales
            if not plazo_nombre:
                for nombre, var_id in YIELD_CURVE_VARIABLES_REAL.items():
                    if var_id == id_variable:
                        plazo_nombre = nombre
                        plazo_tipo = 'real'
                        break
            
            if not plazo_nombre:
                continue
            
            # Obtener datos históricos
            query = """
                SELECT fecha, valor
                FROM maestro_precios
                WHERE id_variable = ? 
                AND id_pais = ?
                AND DATE(fecha) >= DATE(?)
                AND DATE(fecha) <= DATE(?)
                ORDER BY fecha ASC
            """
            
            results = execute_query(query, (id_variable, ID_PAIS, fecha_desde, fecha_hasta))
            
            data_points = []
            for row in results:
                fecha_parsed = parse_fecha(row['fecha'])
                data_points.append({
                    "fecha": fecha_parsed.isoformat(),
                    "valor": float(row['valor']) if row['valor'] is not None else None
                })
            
            result_data.append({
                "id_variable": id_variable,
                "nombre": f"{plazo_nombre} ({plazo_tipo})",
                "data": data_points
            })
        
        return jsonify({"data": result_data})
    
    except Exception as e:
        return jsonify({'error': f'Error al obtener datos: {str(e)}'}), 500
