"""API routes for DCP (Dominant Currency Paradigm) index calculation."""
from datetime import date, datetime
from typing import List, Dict, Optional
from io import BytesIO
from flask import Blueprint, request, jsonify, abort, send_file
from openpyxl import Workbook
from openpyxl.styles import Font, Alignment, PatternFill
from ..database import execute_query, execute_query_single

bp = Blueprint('dcp', __name__)

# IDs de variables macro según el sistema
TC_USD_ID = 6  # Tipo de cambio USD/UYU
TC_EUR_ID = 7  # Tipo de cambio EUR/UYU
IPC_ID = 11    # IPC general


def is_celulosa(product_name: str) -> bool:
    """Identifica si un producto es celulosa por su nombre."""
    return 'celulosa' in product_name.lower()


def convert_to_monthly(series_data: List[Dict], periodicidad: str) -> List[Dict]:
    """
    Convierte una serie de datos a frecuencia mensual.
    
    Args:
        series_data: Lista de dicts con 'fecha' (date o string) y 'valor' (float)
        periodicidad: 'D', 'W', o 'M'
    
    Returns:
        Lista de dicts con fechas al primer día del mes y valores promediados
    """
    # Normalizar todas las fechas a objetos date
    normalized_data = []
    for item in series_data:
        fecha_val = item['fecha']
        if isinstance(fecha_val, str):
            fecha_obj = date.fromisoformat(fecha_val)
        elif isinstance(fecha_val, date):
            fecha_obj = fecha_val
        else:
            # Intentar convertir desde otros formatos
            fecha_obj = date.fromisoformat(str(fecha_val))
        
        normalized_data.append({
            'fecha': fecha_obj,
            'valor': float(item['valor'])
        })
    
    if periodicidad == 'M':
        # Ya es mensual, solo normalizar fechas al primer día
        return [
            {
                'fecha': date(d['fecha'].year, d['fecha'].month, 1),
                'valor': d['valor']
            }
            for d in normalized_data
        ]
    
    # Para D o W, agrupar por año-mes y calcular promedio
    monthly_dict = {}
    
    for item in normalized_data:
        fecha_obj = item['fecha']
        year_month = (fecha_obj.year, fecha_obj.month)
        
        if year_month not in monthly_dict:
            monthly_dict[year_month] = {'sum': 0.0, 'count': 0}
        
        monthly_dict[year_month]['sum'] += item['valor']
        monthly_dict[year_month]['count'] += 1
    
    # Calcular promedios y crear lista de resultados
    result = []
    for (year, month), stats in sorted(monthly_dict.items()):
        if stats['count'] > 0:
            result.append({
                'fecha': date(year, month, 1),
                'valor': stats['sum'] / stats['count']
            })
    
    return result


def get_macro_series(maestro_id: int, fecha_desde: date, fecha_hasta: date) -> Dict[date, float]:
    """
    Obtiene una serie macro (TC o IPC) y la convierte a mensual.
    
    Args:
        maestro_id: ID de la serie macro en maestro
        fecha_desde: Fecha inicial
        fecha_hasta: Fecha final
    
    Returns:
        Dict con fechas (primer día del mes) como keys y valores como values
    """
    # Obtener periodicidad de la serie macro
    query_maestro = "SELECT periodicidad FROM maestro WHERE id = ?"
    maestro_info = execute_query_single(query_maestro, (maestro_id,))
    
    if not maestro_info:
        return {}
    
    periodicidad = maestro_info['periodicidad']
    
    # Obtener datos de la serie
    query = """
        SELECT fecha, valor
        FROM maestro_precios
        WHERE maestro_id = ? AND fecha BETWEEN ? AND ?
        ORDER BY fecha ASC
    """
    try:
        raw_data = execute_query(query, (maestro_id, fecha_desde, fecha_hasta))
    except Exception as e:
        # Si hay error, retornar dict vacío
        return {}
    
    if not raw_data:
        return {}
    
    # Convertir a mensual (la función convert_to_monthly maneja la conversión de fechas)
    monthly_data = convert_to_monthly(raw_data, periodicidad)
    
    # Convertir a dict con fecha como key
    return {item['fecha']: item['valor'] for item in monthly_data}


@bp.route('/dcp/indices', methods=['GET'])
def get_dcp_indices():
    """
    Calcula índices DCP para productos seleccionados.
    
    Parámetros:
    - product_ids[]: Lista de IDs de productos
    - fecha_desde: Fecha inicial (YYYY-MM-DD)
    - fecha_hasta: Fecha final (YYYY-MM-DD)
    
    Retorna:
    JSON con índices normalizados a base 100
    """
    try:
        product_ids = request.args.getlist('product_ids[]', type=int)
        
        if not product_ids:
            return jsonify([])
        
        fecha_desde_str = request.args.get('fecha_desde', type=str)
        fecha_hasta_str = request.args.get('fecha_hasta', type=str)
        
        if not fecha_desde_str or not fecha_hasta_str:
            abort(400, description="fecha_desde and fecha_hasta are required")
        
        try:
            fecha_desde = date.fromisoformat(fecha_desde_str)
            fecha_hasta = date.fromisoformat(fecha_hasta_str)
        except ValueError as e:
            abort(400, description=f"Invalid date format: {str(e)}")
        
        # Obtener información de productos
        placeholders = ",".join("?" * len(product_ids))
        query_products = f"""
            SELECT id, nombre, periodicidad
            FROM maestro
            WHERE id IN ({placeholders}) AND tipo = 'P' AND activo = 1
        """
        products = execute_query(query_products, tuple(product_ids))
        
        if not products:
            return jsonify([])
        
        # Obtener TC e IPC mensuales (una vez para todos los productos)
        tc_usd_monthly = get_macro_series(TC_USD_ID, fecha_desde, fecha_hasta)
        tc_eur_monthly = get_macro_series(TC_EUR_ID, fecha_desde, fecha_hasta)
        ipc_monthly = get_macro_series(IPC_ID, fecha_desde, fecha_hasta)
        
        if not ipc_monthly:
            return jsonify({
                'error': 'IPC data not available for the selected date range',
                'message': 'No hay datos de IPC disponibles para el rango de fechas seleccionado'
            }), 400
        
        result = []
        
        # Procesar cada producto
        for product in products:
            product_id = product['id']
            product_name = product['nombre']
            periodicidad = product['periodicidad']
            
            # Obtener precios del producto
            query_prices = """
                SELECT fecha, valor
                FROM maestro_precios
                WHERE maestro_id = ? AND fecha BETWEEN ? AND ?
                ORDER BY fecha ASC
            """
            try:
                raw_prices = execute_query(query_prices, (product_id, fecha_desde, fecha_hasta))
            except Exception as e:
                continue
            
            if not raw_prices:
                continue
            
            # Convertir precios a mensual (la función maneja la conversión de fechas)
            prices_monthly = convert_to_monthly(raw_prices, periodicidad)
            
            # Determinar qué tipo de cambio usar
            use_eur = is_celulosa(product_name)
            tc_monthly = tc_eur_monthly if use_eur else tc_usd_monthly
            
            if not tc_monthly:
                continue  # No hay TC disponible
            
            # Calcular índices para cada mes
            indices_original = []
            for price_item in prices_monthly:
                mes_fecha = price_item['fecha']
                precio = float(price_item['valor'])
                
                # Asegurar que mes_fecha sea un objeto date para la comparación
                if not isinstance(mes_fecha, date):
                    if isinstance(mes_fecha, str):
                        mes_fecha = date.fromisoformat(mes_fecha)
                    else:
                        continue
                
                # Verificar que existan TC e IPC para este mes
                if mes_fecha in tc_monthly and mes_fecha in ipc_monthly:
                    tc_valor = float(tc_monthly[mes_fecha])
                    ipc_valor = float(ipc_monthly[mes_fecha])
                    
                    if ipc_valor > 0:  # Evitar división por cero
                        indice = (precio * tc_valor) / ipc_valor
                        indices_original.append({
                            'fecha': mes_fecha,
                            'valor': indice
                        })
            
            if not indices_original:
                continue
            
            # Normalizar a base 100
            # Filtrar desde fecha_desde y encontrar primer valor
            indices_filtered = [idx for idx in indices_original if idx['fecha'] >= fecha_desde]
            
            if not indices_filtered:
                continue
            
            first_value = indices_filtered[0]['valor']
            
            if first_value == 0 or first_value is None:
                continue  # No se puede normalizar
            
            factor = 100.0 / first_value
            
            # Aplicar normalización
            indices_normalized = [
                {
                    'fecha': idx['fecha'].isoformat(),
                    'valor': idx['valor'] * factor
                }
                for idx in indices_filtered
            ]
            
            result.append({
                'product_id': product_id,
                'product_name': product_name,
                'data': indices_normalized
            })
        
        return jsonify(result)
    except Exception as e:
        import traceback
        traceback.print_exc()
        abort(500, description=f"Error calculating DCP indices: {str(e)}")


@bp.route('/dcp/indices/export', methods=['GET'])
def export_dcp_indices_to_excel():
    """
    Exporta índices DCP a Excel con 3 hojas.
    
    Parámetros: iguales a /dcp/indices
    Retorna: archivo Excel
    """
    product_ids = request.args.getlist('product_ids[]', type=int)
    
    if not product_ids:
        abort(400, description="At least one product_id is required")
    
    fecha_desde_str = request.args.get('fecha_desde', type=str)
    fecha_hasta_str = request.args.get('fecha_hasta', type=str)
    
    if not fecha_desde_str or not fecha_hasta_str:
        abort(400, description="fecha_desde and fecha_hasta are required")
    
    fecha_desde = date.fromisoformat(fecha_desde_str)
    fecha_hasta = date.fromisoformat(fecha_hasta_str)
    
    # Obtener datos (similar a /indices pero necesitamos originales también)
    placeholders = ",".join("?" * len(product_ids))
    query_products = f"""
        SELECT id, nombre, periodicidad
        FROM maestro
        WHERE id IN ({placeholders}) AND tipo = 'P' AND activo = 1
    """
    products = execute_query(query_products, tuple(product_ids))
    
    if not products:
        abort(400, description="No valid products found")
    
    # Obtener macro series
    tc_usd_monthly = get_macro_series(TC_USD_ID, fecha_desde, fecha_hasta)
    tc_eur_monthly = get_macro_series(TC_EUR_ID, fecha_desde, fecha_hasta)
    ipc_monthly = get_macro_series(IPC_ID, fecha_desde, fecha_hasta)
    
    if not ipc_monthly:
        abort(400, description="IPC data not available")
    
    # Calcular índices originales y normalizados para cada producto
    all_indices_original = {}  # {product_id: [(fecha, valor), ...]}
    all_indices_normalized = {}  # {product_id: [(fecha, valor), ...]}
    product_names = {}  # {product_id: nombre}
    product_formulas = {}  # {product_id: 'USD/UYU' o 'EUR/UYU'}
    
    for product in products:
        product_id = product['id']
        product_name = product['nombre']
        periodicidad = product['periodicidad']
        product_names[product_id] = product_name
        
        # Obtener precios
        query_prices = """
            SELECT fecha, valor
            FROM maestro_precios
            WHERE maestro_id = ? AND fecha BETWEEN ? AND ?
            ORDER BY fecha ASC
        """
        raw_prices = execute_query(query_prices, (product_id, fecha_desde, fecha_hasta))
        
        if not raw_prices:
            continue
        
        for item in raw_prices:
            if isinstance(item['fecha'], str):
                item['fecha'] = date.fromisoformat(item['fecha'])
        
        prices_monthly = convert_to_monthly(raw_prices, periodicidad)
        
        # Determinar TC
        use_eur = is_celulosa(product_name)
        tc_monthly = tc_eur_monthly if use_eur else tc_usd_monthly
        product_formulas[product_id] = 'EUR/UYU' if use_eur else 'USD/UYU'
        
        if not tc_monthly:
            continue
        
        # Calcular índices originales
        indices_orig = []
        for price_item in prices_monthly:
            mes_fecha = price_item['fecha']
            precio = price_item['valor']
            
            if mes_fecha in tc_monthly and mes_fecha in ipc_monthly:
                tc_valor = tc_monthly[mes_fecha]
                ipc_valor = ipc_monthly[mes_fecha]
                
                if ipc_valor > 0:
                    indice = (precio * tc_valor) / ipc_valor
                    indices_orig.append((mes_fecha, indice))
        
        if not indices_orig:
            continue
        
        all_indices_original[product_id] = indices_orig
        
        # Normalizar
        indices_filtered = [idx for idx in indices_orig if idx[0] >= fecha_desde]
        if not indices_filtered:
            continue
        
        first_value = indices_filtered[0][1]
        if first_value == 0 or first_value is None:
            continue
        
        factor = 100.0 / first_value
        indices_norm = [(fecha, valor * factor) for fecha, valor in indices_filtered]
        all_indices_normalized[product_id] = indices_norm
    
    # Crear Excel
    wb = Workbook()
    
    # Estilos
    header_fill = PatternFill(start_color="366092", end_color="366092", fill_type="solid")
    header_font = Font(bold=True, color="FFFFFF", size=12)
    header_alignment = Alignment(horizontal="center", vertical="center")
    data_alignment = Alignment(horizontal="right", vertical="center")
    
    # Hoja 1: Índices Normalizados
    ws1 = wb.active
    ws1.title = "Índices Normalizados"
    
    # Encabezados
    ws1['A1'] = 'Fecha'
    ws1['A1'].fill = header_fill
    ws1['A1'].font = header_font
    ws1['A1'].alignment = header_alignment
    
    col = 2
    for product_id in sorted(all_indices_normalized.keys()):
        cell = ws1.cell(row=1, column=col)
        cell.value = product_names[product_id]
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = header_alignment
        col += 1
    
    # Obtener todas las fechas únicas
    all_dates = set()
    for indices in all_indices_normalized.values():
        all_dates.update([idx[0] for idx in indices])
    sorted_dates = sorted(all_dates)
    
    # Escribir datos
    row = 2
    for fecha in sorted_dates:
        ws1.cell(row=row, column=1).value = fecha
        col = 2
        for product_id in sorted(all_indices_normalized.keys()):
            indices = all_indices_normalized[product_id]
            valor = next((idx[1] for idx in indices if idx[0] == fecha), None)
            if valor is not None:
                cell = ws1.cell(row=row, column=col)
                cell.value = valor
                cell.alignment = data_alignment
            col += 1
        row += 1
    
    # Hoja 2: Índices Originales
    ws2 = wb.create_sheet("Índices Originales")
    
    ws2['A1'] = 'Fecha'
    ws2['A1'].fill = header_fill
    ws2['A1'].font = header_font
    ws2['A1'].alignment = header_alignment
    
    col = 2
    for product_id in sorted(all_indices_original.keys()):
        cell = ws2.cell(row=1, column=col)
        cell.value = product_names[product_id]
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = header_alignment
        col += 1
    
    all_dates_orig = set()
    for indices in all_indices_original.values():
        all_dates_orig.update([idx[0] for idx in indices])
    sorted_dates_orig = sorted(all_dates_orig)
    
    row = 2
    for fecha in sorted_dates_orig:
        ws2.cell(row=row, column=1).value = fecha
        col = 2
        for product_id in sorted(all_indices_original.keys()):
            indices = all_indices_original[product_id]
            valor = next((idx[1] for idx in indices if idx[0] == fecha), None)
            if valor is not None:
                cell = ws2.cell(row=row, column=col)
                cell.value = valor
                cell.alignment = data_alignment
            col += 1
        row += 1
    
    # Hoja 3: Metadatos
    ws3 = wb.create_sheet("Metadatos")
    
    ws3['A1'] = 'Campo'
    ws3['A1'].fill = header_fill
    ws3['A1'].font = header_font
    ws3['B1'] = 'Valor'
    ws3['B1'].fill = header_fill
    ws3['B1'].font = header_font
    
    metadata = [
        ('Fecha de exportación', datetime.now().strftime('%Y-%m-%d %H:%M:%S')),
        ('Rango de fechas', f'{fecha_desde} a {fecha_hasta}'),
        ('Productos incluidos', ', '.join([product_names[pid] for pid in sorted(all_indices_normalized.keys())])),
    ]
    
    row = 2
    for campo, valor in metadata:
        ws3.cell(row=row, column=1).value = campo
        ws3.cell(row=row, column=2).value = valor
        row += 1
    
    # Agregar fórmulas por producto
    ws3.cell(row=row, column=1).value = 'Fórmulas aplicadas'
    ws3.cell(row=row, column=1).font = Font(bold=True)
    row += 1
    
    for product_id in sorted(all_indices_normalized.keys()):
        ws3.cell(row=row, column=1).value = product_names[product_id]
        ws3.cell(row=row, column=2).value = f'Precio × TC {product_formulas[product_id]} / IPC'
        row += 1
    
    # Ajustar anchos de columna
    for ws in [ws1, ws2]:
        ws.column_dimensions['A'].width = 15
        for col in range(2, len(all_indices_normalized) + 2):
            ws.column_dimensions[chr(64 + col)].width = 25
    
    ws3.column_dimensions['A'].width = 30
    ws3.column_dimensions['B'].width = 50
    
    # Guardar a BytesIO
    output = BytesIO()
    wb.save(output)
    output.seek(0)
    
    # Nombre de archivo
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f'indices_dcp_{timestamp}.xlsx'
    
    return send_file(
        output,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name=filename
    )
