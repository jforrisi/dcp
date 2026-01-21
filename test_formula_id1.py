"""
Script de prueba para verificar la fórmula con producto ID 1
Período: Diciembre 2024 - Noviembre 2025
"""

import sys
from datetime import date
from pathlib import Path

# Agregar el directorio backend al path
backend_path = Path(__file__).parent / 'backend'
sys.path.insert(0, str(backend_path))

from app.database import execute_query
from app.routers.dcp import (
    get_macro_series,
    convert_to_monthly,
    TC_USD_ID,
    TC_EUR_ID,
    IPC_ID
)

def test_formula_celulosa():
    """Prueba la fórmula para Celulosa (ID 12)"""
    
    product_id = 12  # Celulosa
    fecha_desde = date(2025, 1, 1)
    fecha_hasta = date(2025, 12, 31)
    
    print("=" * 80)
    print(f"PRUEBA DE FORMULA - Celulosa (Producto ID {product_id})")
    print(f"Periodo solicitado: {fecha_desde} a {fecha_hasta}")
    print("=" * 80)
    
    # Obtener información del producto
    query_product = """
        SELECT id, nombre, periodicidad, moneda, nominal_real
        FROM maestro
        WHERE id = ? AND activo = 1
    """
    product_info = execute_query(query_product, (product_id,))
    
    if not product_info:
        print(f"ERROR: Producto ID {product_id} no encontrado o inactivo")
        return
    
    product = product_info[0]
    product_name = product['nombre']
    periodicidad = product['periodicidad']
    moneda = product.get('moneda') or 'uyu'
    nominal_real_raw = product.get('nominal_real') or 'n'
    # Normalizar nominal_real: si no es 'r' o 'R', tratarlo como nominal ('n')
    if isinstance(nominal_real_raw, str):
        nominal_real = 'r' if nominal_real_raw.lower() == 'r' else 'n'
    else:
        nominal_real = 'n'
    
    print(f"\nProducto: {product_name}")
    print(f"Periodicidad: {periodicidad}")
    print(f"Moneda: {moneda}")
    print(f"Nominal/Real (raw): {nominal_real_raw}")
    print(f"Nominal/Real (normalizado): {nominal_real}")
    
    # Obtener precios del producto
    query_prices = """
        SELECT fecha, valor
        FROM maestro_precios
        WHERE maestro_id = ? AND fecha <= ?
        ORDER BY fecha ASC
    """
    raw_prices = execute_query(query_prices, (product_id, fecha_hasta))
    
    if not raw_prices:
        print(f"\nERROR: No hay precios para el producto ID {product_id}")
        return
    
    # Normalizar fechas
    for item in raw_prices:
        fecha_val = item['fecha']
        if not isinstance(fecha_val, date):
            fecha_str = str(fecha_val)
            if ' ' in fecha_str:
                fecha_str = fecha_str.split(' ')[0]
            item['fecha'] = date.fromisoformat(fecha_str)
    
    prices_monthly = convert_to_monthly(raw_prices, periodicidad)
    
    # Filtrar precios por rango
    fecha_desde_ym = (fecha_desde.year, fecha_desde.month)
    fecha_hasta_ym = (fecha_hasta.year, fecha_hasta.month)
    
    prices_monthly_filtered = []
    for price_item in prices_monthly:
        mes_fecha = price_item['fecha']
        if not isinstance(mes_fecha, date):
            if isinstance(mes_fecha, str):
                mes_fecha = date.fromisoformat(mes_fecha)
            else:
                continue
        
        mes_fecha_ym = (mes_fecha.year, mes_fecha.month)
        if mes_fecha_ym >= fecha_desde_ym and mes_fecha_ym <= fecha_hasta_ym:
            prices_monthly_filtered.append(price_item)
    
    if not prices_monthly_filtered:
        print(f"\nERROR: No hay precios en el rango seleccionado")
        return
    
    # Obtener fechas inicial y final del producto
    fecha_inicial_producto = prices_monthly_filtered[0]['fecha']
    fecha_final_producto = prices_monthly_filtered[-1]['fecha']
    precio_inicial = float(prices_monthly_filtered[0]['valor'])
    precio_final = float(prices_monthly_filtered[-1]['valor'])
    
    print(f"\nFechas del producto:")
    print(f"  Inicial: {fecha_inicial_producto} - Precio: {precio_inicial:.2f}")
    print(f"  Final: {fecha_final_producto} - Precio: {precio_final:.2f}")
    
    # Calcular variación del precio nominal
    variacion_precio_nominal = ((precio_final - precio_inicial) / precio_inicial) * 100 if precio_inicial > 0 else 0.0
    print(f"\nVariación precio nominal: {variacion_precio_nominal:.2f}%")
    
    # Obtener series macro
    tc_usd_monthly = get_macro_series(TC_USD_ID, fecha_desde, fecha_hasta)
    tc_eur_monthly = get_macro_series(TC_EUR_ID, fecha_desde, fecha_hasta)
    ipc_monthly = get_macro_series(IPC_ID, fecha_desde, fecha_hasta)
    
    # Filtrar TC según la moneda del producto
    tc_filtered = {}
    if moneda == 'eur' and tc_eur_monthly:
        for f, v in tc_eur_monthly.items():
            if fecha_inicial_producto <= f <= fecha_final_producto:
                tc_filtered[f] = v
    elif moneda == 'usd' and tc_usd_monthly:
        for f, v in tc_usd_monthly.items():
            if fecha_inicial_producto <= f <= fecha_final_producto:
                tc_filtered[f] = v
    elif moneda == 'uyu' or moneda is None:
        # Para UYU, crear TC=1.0 para todas las fechas del producto
        for p in prices_monthly_filtered:
            tc_filtered[p['fecha']] = 1.0
    
    # Calcular variación de TC
    variacion_tc = 0.0
    if tc_filtered and len(tc_filtered) >= 2:
        tc_fechas = sorted(tc_filtered.keys())
        tc_inicial = tc_filtered[tc_fechas[0]]
        tc_final = tc_filtered[tc_fechas[-1]]
        if tc_inicial > 0:
            variacion_tc = ((tc_final - tc_inicial) / tc_inicial) * 100
        print(f"\nVariación TC ({moneda.upper()}): {variacion_tc:.2f}%")
        print(f"  TC inicial ({tc_fechas[0]}): {tc_inicial:.4f}")
        print(f"  TC final ({tc_fechas[-1]}): {tc_final:.4f}")
    else:
        print(f"\nVariación TC: 0.00% (moneda UYU o sin datos)")
    
    # Filtrar IPC por fechas del producto
    ipc_filtered = {}
    if nominal_real == 'n' and ipc_monthly:
        for f, v in ipc_monthly.items():
            if fecha_inicial_producto <= f <= fecha_final_producto:
                ipc_filtered[f] = v
    
    # Calcular variación de IPC
    variacion_ipc = 0.0
    if ipc_filtered and len(ipc_filtered) >= 2:
        ipc_fechas = sorted(ipc_filtered.keys())
        ipc_inicial = ipc_filtered[ipc_fechas[0]]
        ipc_final = ipc_filtered[ipc_fechas[-1]]
        if ipc_inicial > 0:
            variacion_ipc = ((ipc_final - ipc_inicial) / ipc_inicial) * 100
        print(f"\nVariación IPC: {variacion_ipc:.2f}%")
        print(f"  IPC inicial ({ipc_fechas[0]}): {ipc_inicial:.4f}")
        print(f"  IPC final ({ipc_fechas[-1]}): {ipc_final:.4f}")
    else:
        print(f"\nVariación IPC: 0.00% (variable real o sin datos)")
    
    # Calcular índices DCP para obtener variación real
    # Determinar TC mensual (igual que el backend)
    if moneda == 'eur':
        tc_monthly = tc_eur_monthly
    elif moneda == 'usd':
        tc_monthly = tc_usd_monthly
    elif moneda == 'uyu' or moneda is None:
        # Para productos en UYU, crear TC=1.0 para todas las fechas de precios mensuales filtrados
        tc_monthly = {p['fecha']: 1.0 for p in prices_monthly_filtered}
    else:
        # Moneda desconocida, usar USD por defecto
        tc_monthly = tc_usd_monthly
    
    if not tc_monthly:
        print(f"\nERROR: No hay TC disponible para el producto")
        return
    
    # Calcular índices originales (igual que el backend - solo con precios filtrados)
    indices_orig = []
    for price_item in prices_monthly_filtered:
        mes_fecha = price_item['fecha']
        precio = float(price_item['valor'])
        
        # Asegurar que mes_fecha sea un objeto date para la comparación
        if not isinstance(mes_fecha, date):
            if isinstance(mes_fecha, str):
                mes_fecha = date.fromisoformat(mes_fecha)
            else:
                continue
        
        # Verificar que exista TC (y si es nominal, IPC) para este mes
        if mes_fecha in tc_monthly:
            tc_valor = float(tc_monthly[mes_fecha])
            base_valor = precio * tc_valor
            
            if nominal_real == 'r':
                indices_orig.append({'fecha': mes_fecha, 'valor': base_valor})
            else:
                if mes_fecha in ipc_monthly:
                    ipc_valor = float(ipc_monthly[mes_fecha])
                    if ipc_valor > 0:  # Evitar división por cero
                        indices_orig.append({'fecha': mes_fecha, 'valor': base_valor / ipc_valor})
    
    if not indices_orig:
        print(f"\nERROR: No se pudieron calcular índices")
        return
    
    # Filtrar índices por rango (igual que el backend)
    fecha_hasta_ym = (fecha_hasta.year, fecha_hasta.month)
    indices_filtered = [
        idx for idx in indices_orig 
        if idx['fecha'] >= fecha_desde 
        and (idx['fecha'].year, idx['fecha'].month) <= fecha_hasta_ym
    ]
    
    if not indices_filtered:
        print(f"\nERROR: No hay índices en el rango filtrado")
        return
    
    # Normalizar índices (igual que el backend)
    first_value = indices_filtered[0]['valor']
    if first_value == 0:
        print(f"\nERROR: Primer valor del índice es cero")
        return
    
    factor = 100.0 / first_value
    indices_normalized = [
        {'fecha': idx['fecha'], 'valor': idx['valor'] * factor}
        for idx in indices_filtered
    ]
    
    # Calcular variación real (usando el índice normalizado que se grafica)
    variacion_real = 0.0
    if indices_normalized and len(indices_normalized) >= 2:
        indice_inicial = indices_normalized[0]['valor']
        indice_final = indices_normalized[-1]['valor']
        if indice_inicial > 0:
            variacion_real = ((indice_final - indice_inicial) / indice_inicial) * 100
    
    print(f"\nVariación real (índice DCP normalizado): {variacion_real:.2f}%")
    print(f"  Índice inicial: {indices_normalized[0]['valor']:.4f}")
    print(f"  Índice final: {indices_normalized[-1]['valor']:.4f}")
    print(f"  Total de meses en índice: {len(indices_normalized)}")
    
    # Verificar fórmula: (1+var_precio_nominal) * (1+var_tc) / (1+var_inflacion) = (1+var_real)
    print("\n" + "=" * 80)
    print("VERIFICACIÓN DE FÓRMULA:")
    print("(1 + var_precio_nominal) × (1 + var_tc) / (1 + var_inflacion) = (1 + var_real)")
    print("=" * 80)
    
    var_precio_decimal = variacion_precio_nominal / 100.0
    var_tc_decimal = variacion_tc / 100.0
    var_inflacion_decimal = variacion_ipc / 100.0
    var_real_decimal = variacion_real / 100.0
    
    lado_izquierdo = (1 + var_precio_decimal) * (1 + var_tc_decimal) / (1 + var_inflacion_decimal)
    lado_derecho = 1 + var_real_decimal
    
    print(f"\nLado izquierdo: (1 + {var_precio_decimal:.6f}) × (1 + {var_tc_decimal:.6f}) / (1 + {var_inflacion_decimal:.6f})")
    print(f"                = {lado_izquierdo:.6f}")
    print(f"\nLado derecho:   1 + {var_real_decimal:.6f}")
    print(f"                = {lado_derecho:.6f}")
    
    diferencia = abs(lado_izquierdo - lado_derecho)
    print(f"\nDiferencia:     {diferencia:.6f}")
    
    if diferencia <= 0.01:  # Tolerancia de 0.01 (1%)
        print("\n[OK] FORMULA VALIDADA: La diferencia es menor o igual a 0.01 (1%)")
        print("  La formula se cumple correctamente.")
    else:
        print(f"\n[ERROR] FORMULA NO VALIDADA: La diferencia ({diferencia:.6f}) es mayor a 0.01 (1%)")
        print("  Hay un error en el calculo.")
    
    print("\n" + "=" * 80)

if __name__ == "__main__":
    try:
        test_formula_celulosa()
    except Exception as e:
        import traceback
        print(f"\nERROR: {str(e)}")
        print(traceback.format_exc())
