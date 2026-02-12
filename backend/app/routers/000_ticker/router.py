"""API routes for ticker data (Wall Street style)."""
from datetime import date, datetime
from typing import List, Dict, Optional
from flask import Blueprint, jsonify
from ...database import execute_query, execute_query_single

bp = Blueprint('ticker', __name__)


def parse_fecha(fecha_val):
    """Convierte fecha de SQLite a date."""
    if isinstance(fecha_val, date):
        return fecha_val
    fecha_str = str(fecha_val)
    if ' ' in fecha_str:
        fecha_str = fecha_str.split(' ')[0]
    return date.fromisoformat(fecha_str)


@bp.route('/ticker', methods=['GET'])
def get_ticker_data():
    """
    Obtiene los últimos valores de tipos de cambio y otros indicadores para el ticker.
    Retorna datos para Uruguay, Chile, Perú y otros países configurados.
    """
    try:
        # Países y variables para el ticker
        # Uruguay (858), Chile, Perú, Argentina (32), etc.
        ticker_config = [
            {'id_pais': 858, 'nombre_pais': 'Uruguay', 'id_variable': 6, 'nombre_variable': 'USD/UYU'},
            {'id_pais': 32, 'nombre_pais': 'Argentina', 'id_variable': 22, 'nombre_variable': 'USD/ARS'},
            # Agregar más países según necesidad
        ]
        
        # Query simplificado para obtener últimos valores de tipos de cambio
        query = """
            SELECT 
                m.id_variable,
                m.id_pais,
                v.id_nombre_variable as nombre_variable,
                pg.nombre_pais_grupo as nombre_pais,
                mp.fecha as ultima_fecha,
                mp.valor as ultimo_valor
            FROM maestro m
            LEFT JOIN variables v ON m.id_variable = v.id_variable
            LEFT JOIN pais_grupo pg ON m.id_pais = pg.id_pais
            INNER JOIN (
                SELECT 
                    id_variable,
                    id_pais,
                    MAX(fecha) as max_fecha
                FROM maestro_precios
                GROUP BY id_variable, id_pais
            ) latest ON m.id_variable = latest.id_variable AND m.id_pais = latest.id_pais
            INNER JOIN maestro_precios mp ON mp.id_variable = latest.id_variable 
                AND mp.id_pais = latest.id_pais 
                AND mp.fecha = latest.max_fecha
            WHERE m.periodicidad = 'D'
            AND (m.activo = 1 OR CAST(m.activo AS INTEGER) = 1)
            AND (
                (v.id_nombre_variable LIKE '%USD%' OR v.id_nombre_variable LIKE '%USD/LC%')
                OR (m.id_variable = 6 AND m.id_pais = 858)  -- USD/UYU Uruguay
                OR (m.id_variable = 22 AND m.id_pais = 32)   -- USD/ARS Argentina
            )
            AND m.id_pais IN (858, 32, 152, 170, 484)  -- Uruguay, Argentina, Chile, Perú, México
            AND mp.valor IS NOT NULL
            ORDER BY pg.nombre_pais_grupo, v.id_nombre_variable
        """
        
        results = execute_query(query)
        
        ticker_items = []
        for row in results:
            id_variable = row['id_variable']
            id_pais = row['id_pais']
            nombre_variable = row['nombre_variable'] or 'Tipo de cambio'
            nombre_pais = row['nombre_pais'] or 'N/A'
            ultima_fecha = parse_fecha(row['ultima_fecha']) if row['ultima_fecha'] else None
            ultimo_valor = row['ultimo_valor']
            
            if ultimo_valor is not None and ultima_fecha:
                # Formatear valor con punto como separador de millares y coma como decimal
                # Ejemplo: 3638.49 -> "3.638,49"
                try:
                    valor_num = float(ultimo_valor)
                except (TypeError, ValueError):
                    valor_num = 0.0
                valor_str = f"{valor_num:,.2f}"  # Formato: "3,638.49"
                partes = valor_str.split('.')
                if len(partes) >= 2:
                    # Separar miles con punto y decimales con coma
                    parte_entera = partes[0].replace(',', '.')  # "3,638" -> "3.638"
                    parte_decimal = partes[1]  # "49"
                    valor_formateado = f"{parte_entera},{parte_decimal}"  # "3.638,49"
                else:
                    # Si no tiene punto (un solo segmento)
                    valor_formateado = valor_str.replace(',', '.')
                
                ticker_items.append({
                    'pais': nombre_pais,
                    'variable': nombre_variable,
                    'valor': valor_num,
                    'valor_formateado': valor_formateado,
                    'fecha': str(ultima_fecha),
                    'id_variable': id_variable,
                    'id_pais': id_pais
                })
        
        return jsonify({
            'success': True,
            'data': ticker_items
        })
        
    except Exception as e:
        # No devolver 500 para no romper la app (Home/Licitaciones cargan igual)
        print(f"[Ticker] Error: {e}")
        return jsonify({
            'success': True,
            'data': []
        })
