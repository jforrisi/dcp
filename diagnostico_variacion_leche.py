"""
Script de diagnóstico para entender la variación de leche en polvo
"""
import sqlite3
from datetime import date
from pathlib import Path

# Ruta a la base de datos
DB_PATH = Path(__file__).parent / "series_tiempo.db"

def parse_fecha(fecha_val) -> date:
    """Normaliza un valor de fecha a un objeto date."""
    if isinstance(fecha_val, date):
        return fecha_val
    elif isinstance(fecha_val, str):
        if ' ' in fecha_val:
            return date.fromisoformat(fecha_val.split(' ')[0])
        return date.fromisoformat(fecha_val)
    else:
        return date.fromisoformat(str(fecha_val).split(' ')[0])

def convert_to_monthly(series_data, periodicidad):
    """Convierte serie a mensual."""
    normalized_data = []
    for item in series_data:
        normalized_data.append({
            'fecha': parse_fecha(item['fecha']),
            'valor': float(item['valor'])
        })
    
    if periodicidad == 'M':
        # Ya es mensual, pero puede haber múltiples valores por mes
        # Agrupar por año-mes y calcular promedio
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
    
    monthly_dict = {}
    for item in normalized_data:
        fecha_obj = item['fecha']
        year_month = (fecha_obj.year, fecha_obj.month)
        
        if year_month not in monthly_dict:
            monthly_dict[year_month] = {'sum': 0.0, 'count': 0}
        
        monthly_dict[year_month]['sum'] += item['valor']
        monthly_dict[year_month]['count'] += 1
    
    result = []
    for (year, month), stats in sorted(monthly_dict.items()):
        if stats['count'] > 0:
            result.append({
                'fecha': date(year, month, 1),
                'valor': stats['sum'] / stats['count']
            })
    
    return result

def get_macro_series(maestro_id, fecha_desde, fecha_hasta):
    """Obtiene serie macro mensual."""
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    query_maestro = "SELECT periodicidad FROM maestro WHERE id = ?"
    cursor.execute(query_maestro, (maestro_id,))
    maestro_info = cursor.fetchone()
    
    if not maestro_info:
        conn.close()
        return {}
    
    periodicidad = maestro_info['periodicidad']
    
    query = """
        SELECT fecha, valor
        FROM maestro_precios
        WHERE maestro_id = ? AND fecha BETWEEN ? AND ?
        ORDER BY fecha ASC
    """
    cursor.execute(query, (maestro_id, fecha_desde, fecha_hasta))
    raw_data = [dict(row) for row in cursor.fetchall()]
    
    conn.close()
    
    if not raw_data:
        return {}
    
    monthly_data = convert_to_monthly(raw_data, periodicidad)
    return {item['fecha']: item['valor'] for item in monthly_data}

# IDs de variables macro
TC_USD_ID = 6
TC_EUR_ID = 7
IPC_ID = 11
LECHE_POLVO_ID = 2

# Rango de fechas: Enero 2025 a Enero 2026
fecha_desde = date(2025, 1, 1)
fecha_hasta = date(2026, 1, 31)  # Incluir todo enero 2026

print("=" * 80)
print("DIAGNÓSTICO: VARIACIÓN LECHE EN POLVO (ID 2)")
print("=" * 80)
print(f"\nRango de fechas: {fecha_desde} a {fecha_hasta}")
print(f"Esto debería incluir: Enero 2025 y Enero 2026\n")

# Obtener información del producto
conn = sqlite3.connect(str(DB_PATH))
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

query_product = "SELECT id, nombre, periodicidad FROM maestro WHERE id = ?"
cursor.execute(query_product, (LECHE_POLVO_ID,))
product = cursor.fetchone()

if not product:
    print("ERROR: Producto no encontrado")
    conn.close()
    exit(1)

product_id = product['id']
product_name = product['nombre']
periodicidad = product['periodicidad']

print(f"Producto: {product_name} (ID: {product_id}, Periodicidad: {periodicidad})")

# Obtener precios del producto
query_prices = """
    SELECT fecha, valor
    FROM maestro_precios
    WHERE maestro_id = ? AND fecha BETWEEN ? AND ?
    ORDER BY fecha ASC
"""
cursor.execute(query_prices, (product_id, fecha_desde, fecha_hasta))
raw_prices = [dict(row) for row in cursor.fetchall()]

print(f"\nPrecios brutos encontrados: {len(raw_prices)}")
for i, p in enumerate(raw_prices[:5]):
    print(f"  {i+1}. Fecha: {p['fecha']}, Valor: {p['valor']}")
if len(raw_prices) > 5:
    print(f"  ... y {len(raw_prices) - 5} más")

# Convertir a mensual
prices_monthly = convert_to_monthly(raw_prices, periodicidad)
print(f"\nPrecios mensuales: {len(prices_monthly)}")
for p in prices_monthly:
    print(f"  {p['fecha']}: {p['valor']:.2f}")

# Obtener macro series
tc_usd_monthly = get_macro_series(TC_USD_ID, fecha_desde, fecha_hasta)
tc_eur_monthly = get_macro_series(TC_EUR_ID, fecha_desde, fecha_hasta)
ipc_monthly = get_macro_series(IPC_ID, fecha_desde, fecha_hasta)

print(f"\nTC USD mensual: {len(tc_usd_monthly)} meses")
print(f"TC EUR mensual: {len(tc_eur_monthly)} meses")
print(f"IPC mensual: {len(ipc_monthly)} meses")

# Calcular índices
indices = []
for price_item in prices_monthly:
    mes_fecha = price_item['fecha']
    precio = float(price_item['valor'])
    
    if mes_fecha in ipc_monthly and mes_fecha in tc_usd_monthly:
        ipc_valor = float(ipc_monthly[mes_fecha])
        tc_valor = float(tc_usd_monthly[mes_fecha])
        
        if ipc_valor > 0:
            indice = (precio / ipc_valor) * tc_valor
            indices.append({
                'fecha': mes_fecha,
                'valor': indice
            })
            print(f"\n  {mes_fecha}: Precio={precio:.2f}, IPC={ipc_valor:.2f}, TC={tc_valor:.2f} => Índice={indice:.4f}")

print(f"\n\nÍndices calculados: {len(indices)}")
for idx in indices:
    print(f"  {idx['fecha']}: {idx['valor']:.4f}")

# Filtrar por rango
indices_filtered = [idx for idx in indices if idx['fecha'] >= fecha_desde and idx['fecha'] <= fecha_hasta]
indices_filtered.sort(key=lambda x: x['fecha'])

print(f"\n\nÍndices filtrados (>= {fecha_desde} y <= {fecha_hasta}): {len(indices_filtered)}")
for idx in indices_filtered:
    print(f"  {idx['fecha']}: {idx['valor']:.4f}")

if len(indices_filtered) >= 2:
    indice_inicial = indices_filtered[0]['valor']
    indice_final = indices_filtered[-1]['valor']
    fecha_inicial = indices_filtered[0]['fecha']
    fecha_final = indices_filtered[-1]['fecha']
    
    variacion_percent = ((indice_final - indice_inicial) / indice_inicial) * 100.0
    
    print(f"\n" + "=" * 80)
    print("RESULTADO DE VARIACIÓN:")
    print("=" * 80)
    print(f"Fecha inicial: {fecha_inicial}")
    print(f"Índice inicial: {indice_inicial:.4f}")
    print(f"\nFecha final: {fecha_final}")
    print(f"Índice final: {indice_final:.4f}")
    print(f"\nVariación: {variacion_percent:.2f}%")
    print(f"\nFórmula: (({indice_final:.4f} - {indice_inicial:.4f}) / {indice_inicial:.4f}) * 100")
else:
    print("\nERROR: No hay suficientes índices para calcular variación")

conn.close()
