"""API routes for Licitaciones LRM Analysis."""
from datetime import date, datetime, timedelta
from typing import List, Dict, Optional, Tuple
from flask import Blueprint, request, jsonify, send_file
from ...database import execute_query, execute_query_single
import subprocess
import threading
import sys
from pathlib import Path
import os
from .pdf_generator import crear_pdf_licitacion

bp = Blueprint('licitaciones_lrm', __name__)

# Configuración
ID_PAIS = 858  # Uruguay

# Configuración de variables LRM por plazo
# Mapeo: {plazo_dias: {variable: id_variable}}
LRM_VARIABLES = {
    30: {
        "licitacion": 33,
        "adjudicado": 29,
        "tasa_corte": 25
    },
    90: {
        "licitacion": 34,
        "adjudicado": 30,
        "tasa_corte": 26
    },
    180: {
        "licitacion": 35,
        "adjudicado": 31,
        "tasa_corte": 27
    },
    360: {
        "licitacion": 36,
        "adjudicado": 32,
        "tasa_corte": 28
    }
}

# Mapeo de plazo LRM a variable BEVSA nominal
PLAZO_TO_BEVSA = {
    30: {"nombre": "1 mes", "id_variable": 37},
    90: {"nombre": "3 meses", "id_variable": 39},
    180: {"nombre": "6 meses", "id_variable": 40},
    360: {"nombre": "1 año", "id_variable": 42}
}

# Variables de curva BEVSA nominal (para el gráfico)
BEVSA_NOMINAL_VARIABLES = {
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


def parse_fecha(fecha_val):
    """Convierte fecha de SQLite (puede ser date o datetime string) a date."""
    if isinstance(fecha_val, date):
        return fecha_val
    fecha_str = str(fecha_val)
    if ' ' in fecha_str:
        fecha_str = fecha_str.split(' ')[0]
    return date.fromisoformat(fecha_str)


def obtener_fechas_disponibles_licitaciones() -> List[Dict]:
    """
    Obtiene todas las combinaciones (fecha, plazo) disponibles para licitaciones LRM.
    Retorna una lista de dicts con 'fecha' y 'plazo'.
    """
    combinaciones = []
    
    # Para cada plazo, obtener sus fechas disponibles
    for plazo, config in LRM_VARIABLES.items():
        id_variable = config["licitacion"]
        query = """
            SELECT DISTINCT fecha
            FROM maestro_precios
            WHERE id_variable = ? AND id_pais = ?
            ORDER BY fecha DESC
        """
        
        results = execute_query(query, (id_variable, ID_PAIS))
        for row in results:
            if row['fecha']:
                fecha_parsed = parse_fecha(row['fecha'])
                combinaciones.append({
                    "fecha": fecha_parsed,
                    "plazo": plazo
                })
    
    # Ordenar por fecha descendente, luego por plazo
    combinaciones.sort(key=lambda x: (x["fecha"], x["plazo"]), reverse=True)
    
    return combinaciones


def determinar_plazo_por_fecha(fecha: date) -> Optional[int]:
    """
    Determina el plazo (30, 90, 180, 360) para una fecha específica.
    Busca en todas las variables de licitación y retorna el plazo que tenga datos.
    """
    for plazo, config in LRM_VARIABLES.items():
        id_variable = config["licitacion"]
        query = """
            SELECT COUNT(*) as count
            FROM maestro_precios
            WHERE id_variable = ? AND id_pais = ? AND fecha = ?
        """
        result = execute_query_single(query, (id_variable, ID_PAIS, fecha))
        if result and result.get('count', 0) > 0:
            return plazo
    return None


def obtener_datos_licitacion(fecha: date, plazo: int) -> Optional[Dict]:
    """Obtiene los datos de una licitación específica."""
    config = LRM_VARIABLES.get(plazo)
    if not config:
        return None
    
    datos = {}
    
    # Obtener cada variable
    for var_nombre, id_variable in config.items():
        query = """
            SELECT valor
            FROM maestro_precios
            WHERE id_variable = ? AND id_pais = ? AND fecha = ?
            LIMIT 1
        """
        result = execute_query_single(query, (id_variable, ID_PAIS, fecha))
        if result:
            datos[var_nombre] = result.get('valor')
        else:
            datos[var_nombre] = None
    
    return datos


def obtener_tasa_bevsa(plazo: int, fecha_limite: Optional[date] = None) -> Optional[Dict]:
    """
    Obtiene la tasa BEVSA para un plazo específico.
    Si fecha_limite está especificada, busca el último dato antes o igual a esa fecha.
    """
    bevsa_config = PLAZO_TO_BEVSA.get(plazo)
    if not bevsa_config:
        return None
    
    id_variable = bevsa_config["id_variable"]
    
    # Obtener último dato disponible
    if fecha_limite:
        query = """
            SELECT fecha, valor
            FROM maestro_precios
            WHERE id_variable = ? AND id_pais = ? AND fecha <= ?
            ORDER BY fecha DESC
            LIMIT 1
        """
        result = execute_query_single(query, (id_variable, ID_PAIS, fecha_limite))
    else:
        query = """
            SELECT fecha, valor
            FROM maestro_precios
            WHERE id_variable = ? AND id_pais = ?
            ORDER BY fecha DESC
            LIMIT 1
        """
        result = execute_query_single(query, (id_variable, ID_PAIS))
    
    if not result:
        return None
    
    ultima_fecha = parse_fecha(result['fecha'])
    ultimo_valor = result['valor']
    
    # Obtener mínimo y máximo de últimos 5 días con sus fechas
    fecha_desde = ultima_fecha - timedelta(days=5)
    
    # Obtener min y max valores
    query_min_max = """
        SELECT MIN(valor) as min_valor, MAX(valor) as max_valor
        FROM maestro_precios
        WHERE id_variable = ? AND id_pais = ? 
          AND fecha >= ? AND fecha <= ?
    """
    result_min_max = execute_query_single(
        query_min_max, 
        (id_variable, ID_PAIS, fecha_desde, ultima_fecha)
    )
    
    min_valor = result_min_max.get('min_valor') if result_min_max else None
    max_valor = result_min_max.get('max_valor') if result_min_max else None
    
    # Obtener fechas correspondientes
    fecha_min = None
    fecha_max = None
    
    if min_valor is not None:
        query_fecha_min = """
            SELECT fecha
            FROM maestro_precios
            WHERE id_variable = ? AND id_pais = ? 
              AND fecha >= ? AND fecha <= ? AND valor = ?
            ORDER BY fecha DESC
            LIMIT 1
        """
        result_fecha_min = execute_query_single(
            query_fecha_min,
            (id_variable, ID_PAIS, fecha_desde, ultima_fecha, min_valor)
        )
        if result_fecha_min and result_fecha_min.get('fecha'):
            fecha_min = parse_fecha(result_fecha_min['fecha']).isoformat()
    
    if max_valor is not None:
        query_fecha_max = """
            SELECT fecha
            FROM maestro_precios
            WHERE id_variable = ? AND id_pais = ? 
              AND fecha >= ? AND fecha <= ? AND valor = ?
            ORDER BY fecha DESC
            LIMIT 1
        """
        result_fecha_max = execute_query_single(
            query_fecha_max,
            (id_variable, ID_PAIS, fecha_desde, ultima_fecha, max_valor)
        )
        if result_fecha_max and result_fecha_max.get('fecha'):
            fecha_max = parse_fecha(result_fecha_max['fecha']).isoformat()
    
    return {
        "plazo": plazo,
        "nombre": bevsa_config["nombre"],
        "id_variable": id_variable,
        "ultima_fecha": ultima_fecha.isoformat(),
        "ultimo_valor": ultimo_valor,
        "min_5_dias": min_valor,
        "max_5_dias": max_valor,
        "fecha_min": fecha_min,
        "fecha_max": fecha_max
    }


def obtener_estadisticas_ultimas_5_licitaciones(plazo: int, fecha_limite: date) -> Dict:
    """
    Obtiene estadísticas de las últimas 5 licitaciones para un plazo específico.
    Calcula el % de adjudicación ponderado.
    Incluye tasa de corte y tasa BEVSA para cada licitación.
    """
    config = LRM_VARIABLES.get(plazo)
    if not config:
        return {"error": "Plazo no válido"}
    
    id_licitacion = config["licitacion"]
    id_adjudicado = config["adjudicado"]
    id_tasa_corte = config["tasa_corte"]
    
    # Obtener últimas 5 licitaciones (ordenadas por fecha descendente)
    query = """
        SELECT 
            mp1.fecha, 
            mp1.valor as monto_licitado, 
            mp2.valor as adjudicado,
            mp3.valor as tasa_corte
        FROM maestro_precios mp1
        LEFT JOIN maestro_precios mp2 ON mp1.fecha = mp2.fecha 
            AND mp2.id_variable = ? AND mp2.id_pais = ?
        LEFT JOIN maestro_precios mp3 ON mp1.fecha = mp3.fecha 
            AND mp3.id_variable = ? AND mp3.id_pais = ?
        WHERE mp1.id_variable = ? AND mp1.id_pais = ? AND mp1.fecha <= ?
        ORDER BY mp1.fecha DESC
        LIMIT 5
    """
    
    results = execute_query(
        query, 
        (id_adjudicado, ID_PAIS, id_tasa_corte, ID_PAIS, id_licitacion, ID_PAIS, fecha_limite)
    )
    
    if not results:
        return {
            "total_licitado": 0,
            "total_adjudicado": 0,
            "porcentaje_adjudicacion": 0,
            "licitaciones": []
        }
    
    # Obtener configuración BEVSA para este plazo
    bevsa_config = PLAZO_TO_BEVSA.get(plazo)
    id_bevsa = bevsa_config["id_variable"] if bevsa_config else None
    
    licitaciones = []
    total_licitado = 0
    total_adjudicado = 0
    
    for row in results:
        fecha_lic = parse_fecha(row['fecha'])
        monto_licitado = row.get('monto_licitado') or 0
        adjudicado = row.get('adjudicado') or 0
        tasa_corte = row.get('tasa_corte')
        
        # Calcular monto adjudicado (adjudicado está en formato decimal: 1 = 100%)
        monto_adjudicado = monto_licitado * adjudicado
        
        # Obtener tasa BEVSA para esta fecha y plazo
        tasa_bevsa = None
        if id_bevsa:
            query_bevsa = """
                SELECT valor
                FROM maestro_precios
                WHERE id_variable = ? AND id_pais = ? AND fecha <= ?
                ORDER BY fecha DESC
                LIMIT 1
            """
            result_bevsa = execute_query_single(
                query_bevsa,
                (id_bevsa, ID_PAIS, fecha_lic)
            )
            if result_bevsa:
                tasa_bevsa = result_bevsa.get('valor')
        
        total_licitado += monto_licitado
        total_adjudicado += monto_adjudicado
        
        licitaciones.append({
            "fecha": fecha_lic.isoformat(),
            "monto_licitado": monto_licitado,
            "adjudicado": adjudicado,
            "monto_adjudicado": monto_adjudicado,
            "porcentaje_adjudicacion": adjudicado * 100,  # Convertir a porcentaje para mostrar
            "tasa_corte": tasa_corte,
            "tasa_bevsa": tasa_bevsa
        })
    
    # Calcular % de adjudicación ponderado
    porcentaje_adjudicacion = (total_adjudicado / total_licitado * 100) if total_licitado > 0 else 0
    
    return {
        "plazo": plazo,
        "total_licitado": total_licitado,
        "total_adjudicado": total_adjudicado,
        "porcentaje_adjudicacion": porcentaje_adjudicacion,
        "licitaciones": licitaciones
    }


def obtener_ultima_curva_bevsa_nominal() -> Dict:
    """Obtiene la última curva BEVSA nominal disponible."""
    # Obtener la última fecha disponible para todas las variables
    id_variables = list(BEVSA_NOMINAL_VARIABLES.values())
    placeholders = ','.join(['?'] * len(id_variables))
    
    query = f"""
        SELECT MAX(fecha) as ultima_fecha
        FROM maestro_precios
        WHERE id_variable IN ({placeholders}) AND id_pais = ?
    """
    
    result = execute_query_single(query, tuple(id_variables) + (ID_PAIS,))
    if not result or not result.get('ultima_fecha'):
        return {"fecha": None, "data": []}
    
    ultima_fecha = parse_fecha(result['ultima_fecha'])
    
    # Obtener datos de todas las variables para esa fecha
    data = []
    for nombre, id_variable in BEVSA_NOMINAL_VARIABLES.items():
        query_valor = """
            SELECT valor
            FROM maestro_precios
            WHERE id_variable = ? AND id_pais = ? AND fecha = ?
            LIMIT 1
        """
        result_valor = execute_query_single(
            query_valor, 
            (id_variable, ID_PAIS, ultima_fecha)
        )
        
        valor = result_valor.get('valor') if result_valor else None
        
        data.append({
            "nombre": nombre,
            "id_variable": id_variable,
            "valor": valor
        })
    
    return {
        "fecha": ultima_fecha.isoformat(),
        "data": data
    }


def obtener_curva_bevsa_por_fecha(fecha_limite: date) -> Dict:
    """
    Obtiene la curva BEVSA nominal para una fecha específica o la más cercana anterior.
    Si no hay datos para esa fecha, busca la fecha más cercana anterior.
    """
    id_variables = list(BEVSA_NOMINAL_VARIABLES.values())
    placeholders = ','.join(['?'] * len(id_variables))
    
    # Buscar la fecha más cercana (igual o anterior a fecha_limite)
    query_fecha = f"""
        SELECT MAX(fecha) as fecha_curva
        FROM maestro_precios
        WHERE id_variable IN ({placeholders}) AND id_pais = ? AND fecha <= ?
    """
    
    result_fecha = execute_query_single(
        query_fecha, 
        tuple(id_variables) + (ID_PAIS, fecha_limite)
    )
    
    if not result_fecha or not result_fecha.get('fecha_curva'):
        return {"fecha": None, "data": [], "fecha_original": fecha_limite.isoformat()}
    
    fecha_curva = parse_fecha(result_fecha['fecha_curva'])
    
    # Obtener datos de todas las variables para esa fecha
    data = []
    for nombre, id_variable in BEVSA_NOMINAL_VARIABLES.items():
        query_valor = """
            SELECT valor
            FROM maestro_precios
            WHERE id_variable = ? AND id_pais = ? AND fecha = ?
            LIMIT 1
        """
        result_valor = execute_query_single(
            query_valor, 
            (id_variable, ID_PAIS, fecha_curva)
        )
        
        valor = result_valor.get('valor') if result_valor else None
        
        data.append({
            "nombre": nombre,
            "id_variable": id_variable,
            "valor": valor
        })
    
    return {
        "fecha": fecha_curva.isoformat(),
        "fecha_original": fecha_limite.isoformat(),
        "data": data
    }


def obtener_timeseries_bevsa(plazo: int, fecha_hasta: date, dias: int = 90) -> List[Dict]:
    """
    Obtiene el comportamiento temporal de la tasa BEVSA para un plazo específico.
    
    Args:
        plazo: Plazo en días (30, 90, 180, 360)
        fecha_hasta: Fecha hasta la cual buscar
        dias: Número de días hacia atrás (default: 90)
    
    Returns:
        Lista de dicts con fecha y valor
    """
    bevsa_config = PLAZO_TO_BEVSA.get(plazo)
    if not bevsa_config:
        return []
    
    id_variable = bevsa_config["id_variable"]
    fecha_desde = fecha_hasta - timedelta(days=dias)
    
    query = """
        SELECT fecha, valor
        FROM maestro_precios
        WHERE id_variable = ? AND id_pais = ? 
          AND fecha >= ? AND fecha <= ?
        ORDER BY fecha ASC
    """
    
    results = execute_query(
        query, 
        (id_variable, ID_PAIS, fecha_desde, fecha_hasta)
    )
    
    timeseries = []
    for row in results:
        fecha_parsed = parse_fecha(row['fecha'])
        timeseries.append({
            "fecha": fecha_parsed.isoformat(),
            "valor": row.get('valor')
        })
    
    return timeseries


# ==================== ENDPOINTS ====================

@bp.route('/licitaciones-lrm/dates', methods=['GET'])
def get_dates():
    """
    Obtiene las combinaciones (fecha, plazo) disponibles para licitaciones LRM.
    Retorna un array de objetos con 'fecha' y 'plazo'.
    """
    try:
        combinaciones = obtener_fechas_disponibles_licitaciones()
        
        # Determinar la última combinación (fecha más reciente)
        ultima_combinacion = combinaciones[0] if combinaciones else None
        
        return jsonify({
            "ultima_fecha": ultima_combinacion["fecha"].isoformat() if ultima_combinacion else None,
            "ultimo_plazo": ultima_combinacion["plazo"] if ultima_combinacion else None,
            "combinaciones": [
                {
                    "fecha": c["fecha"].isoformat(),
                    "plazo": c["plazo"]
                }
                for c in combinaciones
            ]
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@bp.route('/licitaciones-lrm/data', methods=['GET'])
def get_licitacion_data():
    """
    Obtiene los datos de una licitación específica.
    Parámetros:
        - fecha: Fecha en formato YYYY-MM-DD
        - plazo: Plazo en días (30, 90, 180, 360)
    """
    try:
        fecha_str = request.args.get('fecha')
        plazo = request.args.get('plazo', type=int)
        
        if not fecha_str:
            return jsonify({"error": "Parámetro 'fecha' requerido"}), 400
        
        if not plazo:
            return jsonify({"error": "Parámetro 'plazo' requerido"}), 400
        
        if plazo not in [30, 90, 180, 360]:
            return jsonify({"error": "Plazo debe ser 30, 90, 180, o 360"}), 400
        
        fecha = date.fromisoformat(fecha_str)
        
        # Obtener datos de la licitación
        datos = obtener_datos_licitacion(fecha, plazo)
        if not datos:
            return jsonify({"error": "No hay datos de licitación para esta fecha y plazo"}), 404
        
        return jsonify({
            "fecha": fecha.isoformat(),
            "plazo": plazo,
            "monto_licitado": datos.get("licitacion"),
            "adjudicado": datos.get("adjudicado"),
            "tasa_corte": datos.get("tasa_corte")
        })
    except ValueError as e:
        return jsonify({"error": f"Fecha inválida: {str(e)}"}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@bp.route('/licitaciones-lrm/bevsa-rate', methods=['GET'])
def get_bevsa_rate():
    """
    Obtiene la tasa BEVSA para un plazo específico.
    Parámetros:
        - plazo: 30, 90, 180, o 360
        - fecha_limite: (opcional) Fecha límite en formato YYYY-MM-DD
    """
    try:
        plazo = request.args.get('plazo', type=int)
        if plazo not in [30, 90, 180, 360]:
            return jsonify({"error": "Plazo debe ser 30, 90, 180, o 360"}), 400
        
        fecha_limite_str = request.args.get('fecha_limite')
        fecha_limite = None
        if fecha_limite_str:
            fecha_limite = date.fromisoformat(fecha_limite_str)
        
        resultado = obtener_tasa_bevsa(plazo, fecha_limite)
        if not resultado:
            return jsonify({"error": "No se encontraron datos BEVSA para este plazo"}), 404
        
        return jsonify(resultado)
    except ValueError as e:
        return jsonify({"error": f"Fecha inválida: {str(e)}"}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@bp.route('/licitaciones-lrm/stats', methods=['GET'])
def get_stats():
    """
    Obtiene estadísticas de las últimas 5 licitaciones.
    Parámetros:
        - plazo: 30, 90, 180, o 360
        - fecha_limite: Fecha límite en formato YYYY-MM-DD
    """
    try:
        plazo = request.args.get('plazo', type=int)
        if plazo not in [30, 90, 180, 360]:
            return jsonify({"error": "Plazo debe ser 30, 90, 180, o 360"}), 400
        
        fecha_limite_str = request.args.get('fecha_limite')
        if not fecha_limite_str:
            return jsonify({"error": "Parámetro 'fecha_limite' requerido"}), 400
        
        fecha_limite = date.fromisoformat(fecha_limite_str)
        
        resultado = obtener_estadisticas_ultimas_5_licitaciones(plazo, fecha_limite)
        return jsonify(resultado)
    except ValueError as e:
        return jsonify({"error": f"Fecha inválida: {str(e)}"}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@bp.route('/licitaciones-lrm/curve', methods=['GET'])
def get_curve():
    """Obtiene la última curva BEVSA nominal disponible."""
    try:
        resultado = obtener_ultima_curva_bevsa_nominal()
        return jsonify(resultado)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@bp.route('/licitaciones-lrm/curve-by-date', methods=['GET'])
def get_curve_by_date():
    """
    Obtiene la curva BEVSA nominal para una fecha específica o la más cercana.
    Parámetros:
        - fecha: Fecha en formato YYYY-MM-DD
    """
    try:
        fecha_str = request.args.get('fecha')
        if not fecha_str:
            return jsonify({"error": "Parámetro 'fecha' requerido"}), 400
        
        fecha = date.fromisoformat(fecha_str)
        resultado = obtener_curva_bevsa_por_fecha(fecha)
        return jsonify(resultado)
    except ValueError as e:
        return jsonify({"error": f"Fecha inválida: {str(e)}"}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@bp.route('/licitaciones-lrm/bevsa-timeseries', methods=['GET'])
def get_bevsa_timeseries():
    """
    Obtiene el comportamiento temporal de la tasa BEVSA para un plazo específico.
    Parámetros:
        - plazo: 30, 90, 180, o 360
        - fecha_hasta: Fecha hasta en formato YYYY-MM-DD
        - dias: Número de días hacia atrás (opcional, default: 90)
    """
    try:
        plazo = request.args.get('plazo', type=int)
        if plazo not in [30, 90, 180, 360]:
            return jsonify({"error": "Plazo debe ser 30, 90, 180, o 360"}), 400
        
        fecha_hasta_str = request.args.get('fecha_hasta')
        if not fecha_hasta_str:
            return jsonify({"error": "Parámetro 'fecha_hasta' requerido"}), 400
        
        fecha_hasta = date.fromisoformat(fecha_hasta_str)
        dias = request.args.get('dias', type=int, default=90)
        
        resultado = obtener_timeseries_bevsa(plazo, fecha_hasta, dias)
        return jsonify({"data": resultado})
    except ValueError as e:
        return jsonify({"error": f"Fecha inválida: {str(e)}"}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# Variables globales para el estado de actualización
update_lrm_in_progress = False
update_lrm_status = {
    'running': False,
    'started_at': None,
    'completed_at': None,
    'returncode': None,
    'output': None,
    'error': None,
    'step': None  # 'download' o 'update'
}


@bp.route('/licitaciones-lrm/update', methods=['POST'])
def update_licitaciones_lrm():
    """
    Ejecuta la actualización de datos de Licitaciones LRM.
    Primero descarga el Excel, luego actualiza la base de datos.
    """
    global update_lrm_in_progress, update_lrm_status
    
    # Evitar ejecuciones simultáneas
    if update_lrm_in_progress:
        return jsonify({
            'error': 'Update already in progress',
            'status': update_lrm_status
        }), 409
    
    # Ejecutar en thread separado para no bloquear
    def run_update():
        global update_lrm_in_progress, update_lrm_status
        update_lrm_in_progress = True
        update_lrm_status = {
            'running': True,
            'started_at': datetime.now().isoformat(),
            'completed_at': None,
            'returncode': None,
            'output': [],
            'error': None,
            'step': None
        }
        
        try:
            # Obtener el directorio raíz del proyecto
            project_root = Path(__file__).parent.parent.parent.parent.parent
            
            # Determinar Python a usar
            if os.getenv('RAILWAY_ENVIRONMENT') or os.getenv('RAILWAY') or os.getenv('AZURE_ENVIRONMENT'):
                python_path = project_root / 'backend' / 'venv' / 'bin' / 'python'
                if not python_path.exists():
                    python_path = 'python3'
            else:
                python_path = sys.executable
            
            output_lines = []
            
            # PASO 1: Descargar Excel
            update_lrm_status['step'] = 'download'
            script_download = project_root / 'update' / 'download' / 'instrumentos_emitidos_bcu_y_gobierno_central.py'
            
            if not script_download.exists():
                raise FileNotFoundError(f'Script not found: {script_download}')
            
            output_lines.append(f"[PASO 1] Descargando Excel desde BCU...")
            result_download = subprocess.run(
                [str(python_path), str(script_download)],
                cwd=str(project_root),
                capture_output=True,
                text=True,
                timeout=1800  # 30 minutos máximo
            )
            
            output_lines.append(result_download.stdout)
            if result_download.stderr:
                output_lines.append(f"STDERR: {result_download.stderr}")
            
            if result_download.returncode != 0:
                error_msg = f'Download script failed with return code {result_download.returncode}'
                if result_download.stderr:
                    error_msg += f'\n\nError details:\n{result_download.stderr[-2000:]}'  # Últimos 2000 caracteres
                if result_download.stdout:
                    error_msg += f'\n\nOutput:\n{result_download.stdout[-2000:]}'  # Últimos 2000 caracteres
                raise Exception(error_msg)
            
            output_lines.append(f"[OK] Excel descargado exitosamente")
            
            # PASO 2: Actualizar base de datos
            update_lrm_status['step'] = 'update'
            script_update = project_root / 'update' / 'direct' / '020_licitaciones_lrm_bcu.py'
            
            if not script_update.exists():
                raise FileNotFoundError(f'Script not found: {script_update}')
            
            output_lines.append(f"\n[PASO 2] Actualizando base de datos...")
            result_update = subprocess.run(
                [str(python_path), str(script_update)],
                cwd=str(project_root),
                capture_output=True,
                text=True,
                timeout=1800  # 30 minutos máximo
            )
            
            output_lines.append(result_update.stdout)
            if result_update.stderr:
                output_lines.append(f"STDERR: {result_update.stderr}")
            
            # Preparar mensaje de error completo si falló
            error_message = None
            if result_update.returncode != 0:
                error_parts = []
                if result_update.stderr:
                    error_parts.append(f"STDERR: {result_update.stderr[-5000:]}")
                if result_update.stdout:
                    # Buscar líneas de error en el output
                    stdout_lines = result_update.stdout.split('\n')
                    error_lines = [line for line in stdout_lines if any(keyword in line.lower() for keyword in ['error', 'exception', 'traceback', 'failed', 'fallo'])]
                    if error_lines:
                        error_parts.append(f"Output errors: {chr(10).join(error_lines[-20:])}")
                error_message = '\n\n'.join(error_parts) if error_parts else 'Unknown error'
            
            update_lrm_status = {
                'running': False,
                'started_at': update_lrm_status['started_at'],
                'completed_at': datetime.now().isoformat(),
                'returncode': result_update.returncode,
                'output': '\n'.join(output_lines)[-20000:],  # Últimos 20KB
                'error': error_message,
                'step': 'completed'
            }
            
        except subprocess.TimeoutExpired:
            update_lrm_status = {
                'running': False,
                'started_at': update_lrm_status['started_at'],
                'completed_at': datetime.now().isoformat(),
                'returncode': -1,
                'error': 'Timeout: Script took more than 30 minutes',
                'step': update_lrm_status.get('step', 'unknown')
            }
        except Exception as e:
            update_lrm_status = {
                'running': False,
                'started_at': update_lrm_status['started_at'],
                'completed_at': datetime.now().isoformat(),
                'returncode': -1,
                'error': str(e),
                'step': update_lrm_status.get('step', 'unknown')
            }
        finally:
            update_lrm_in_progress = False
    
    thread = threading.Thread(target=run_update, daemon=True)
    thread.start()
    
    return jsonify({
        'status': 'started',
        'message': 'Update started in background',
        'started_at': update_lrm_status['started_at']
    })


@bp.route('/licitaciones-lrm/update/status', methods=['GET'])
def get_update_licitaciones_lrm_status():
    """Obtiene el estado de la última ejecución de actualización."""
    return jsonify(update_lrm_status)


@bp.route('/licitaciones-lrm/generate-pdf', methods=['POST'])
def generate_pdf():
    """
    Genera un PDF con el informe de licitación LRM.
    Espera JSON con: fecha, plazo
    """
    try:
        data = request.get_json()
        fecha_str = data.get('fecha')
        plazo = data.get('plazo')
        
        if not fecha_str or not plazo:
            return jsonify({'error': 'Se requieren fecha y plazo'}), 400
        
        try:
            plazo = int(plazo)
        except ValueError:
            return jsonify({'error': 'Plazo debe ser un número'}), 400
        
        # Convertir fecha string a date object
        try:
            fecha = datetime.strptime(fecha_str, '%Y-%m-%d').date()
        except ValueError:
            return jsonify({'error': 'Formato de fecha inválido. Use YYYY-MM-DD'}), 400
        
        # Obtener datos de la licitación
        licitacion_data_raw = obtener_datos_licitacion(fecha, plazo)
        if not licitacion_data_raw:
            return jsonify({'error': f'No se encontraron datos para fecha {fecha_str} y plazo {plazo}'}), 404
        
        # Preparar datos de licitación en el formato del frontend
        licitacion_data = {
            'fecha': fecha,
            'plazo': plazo,
            'monto_licitado': licitacion_data_raw.get('licitacion'),
            'adjudicado': licitacion_data_raw.get('adjudicado'),  # Este es el porcentaje (0-1)
            'tasa_corte': licitacion_data_raw.get('tasa_corte'),
        }
        
        # Obtener tasa BEVSA (con min/max de 5 días)
        bevsa_rate = obtener_tasa_bevsa(plazo, fecha)
        
        # Obtener estadísticas de últimas 5 licitaciones
        stats = obtener_estadisticas_ultimas_5_licitaciones(plazo, fecha)
        
        # Obtener curva BEVSA del día
        curve_data = obtener_curva_bevsa_por_fecha(fecha)
        
        # Obtener serie temporal de últimos 40 días (para gráfico en PDF)
        timeseries_data = obtener_timeseries_bevsa(plazo, fecha, dias=40)
        
        # Preparar datos para el PDF
        pdf_data = {
            'licitacion_data': licitacion_data,
            'bevsa_rate': bevsa_rate,
            'stats': stats,
            'curve_data': curve_data,
            'timeseries_data': timeseries_data
        }
        
        # Generar PDF
        pdf_buffer = crear_pdf_licitacion(pdf_data)
        
        # Nombre del archivo
        filename = f"licitacion_lrm_{fecha_str}_{plazo}dias.pdf"
        
        return send_file(
            pdf_buffer,
            mimetype='application/pdf',
            as_attachment=True,
            download_name=filename
        )
        
    except Exception as e:
        print(f"[ERROR] generate_pdf: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': f'Error al generar PDF: {str(e)}'}), 500
