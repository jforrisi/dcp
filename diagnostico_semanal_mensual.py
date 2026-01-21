"""
Script de diagnóstico para mostrar cómo se convierten datos semanales a mensuales
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
    """Convierte serie a mensual (igual que en dcp.py)."""
    # Normalizar todas las fechas a objetos date
    normalized_data = []
    for item in series_data:
        normalized_data.append({
            'fecha': parse_fecha(item['fecha']),
            'valor': float(item['valor'])
        })
    
    if periodicidad == 'M':
        # Ya es mensual, pero puede haber múltiples valores por mes
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
    
    # Para D o W, agrupar por año-mes y calcular promedio
    monthly_dict = {}
    
    for item in normalized_data:
        fecha_obj = item['fecha']
        year_month = (fecha_obj.year, fecha_obj.month)
        
        if year_month not in monthly_dict:
            monthly_dict[year_month] = {'sum': 0.0, 'count': 0, 'valores': []}
        
        monthly_dict[year_month]['sum'] += item['valor']
        monthly_dict[year_month]['count'] += 1
        monthly_dict[year_month]['valores'].append({
            'fecha': fecha_obj,
            'valor': item['valor']
        })
    
    # Calcular promedios y crear lista de resultados
    result = []
    for (year, month), stats in sorted(monthly_dict.items()):
        if stats['count'] > 0:
            promedio = stats['sum'] / stats['count']
            result.append({
                'fecha': date(year, month, 1),
                'valor': promedio,
                'valores_originales': stats['valores']
            })
    
    return result

# Conectar a la base de datos
conn = sqlite3.connect(str(DB_PATH))
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

# Buscar un producto con periodicidad semanal
cursor.execute("""
    SELECT id, nombre, periodicidad 
    FROM maestro 
    WHERE periodicidad = 'W' AND tipo = 'P' AND activo = 1
    LIMIT 1
""")
product = cursor.fetchone()

if not product:
    print("No se encontró ningún producto con periodicidad semanal.")
    conn.close()
    exit()

product_id = product['id']
product_name = product['nombre']
periodicidad = product['periodicidad']

print(f"=" * 80)
print(f"PRODUCTO: {product_name} (ID: {product_id})")
print(f"PERIODICIDAD: {periodicidad} (Semanal)")
print(f"=" * 80)

# Obtener datos semanales de enero 2025 como ejemplo
fecha_desde = date(2025, 1, 1)
fecha_hasta = date(2025, 1, 31)

query = """
    SELECT fecha, valor
    FROM maestro_precios
    WHERE maestro_id = ? AND fecha BETWEEN ? AND ?
    ORDER BY fecha ASC
"""
cursor.execute(query, (product_id, fecha_desde, fecha_hasta))
raw_data = cursor.fetchall()

if not raw_data:
    print(f"\nNo hay datos para el rango {fecha_desde} a {fecha_hasta}")
    conn.close()
    exit()

print(f"\nDATOS SEMANALES ORIGINALES (Enero 2025):")
print(f"{'Fecha':<15} {'Valor':<15} {'Dia de la semana':<20}")
print("-" * 50)

dias_semana = ['Lunes', 'Martes', 'Miercoles', 'Jueves', 'Viernes', 'Sabado', 'Domingo']
for row in raw_data:
    fecha_obj = parse_fecha(row['fecha'])
    dia_semana = dias_semana[fecha_obj.weekday()]
    print(f"{fecha_obj}     {row['valor']:<15.2f} {dia_semana}")

# Convertir a mensual
data_dict = [{'fecha': row['fecha'], 'valor': row['valor']} for row in raw_data]
monthly_data = convert_to_monthly(data_dict, periodicidad)

print(f"\nCONVERSION A MENSUAL:")
print(f"{'Mes':<15} {'Promedio Mensual':<20} {'Observaciones':<20}")
print("-" * 55)

for item in monthly_data:
    fecha_mes = item['fecha']
    promedio = item['valor']
    valores_orig = item.get('valores_originales', [])
    num_obs = len(valores_orig)
    
    print(f"{fecha_mes.strftime('%Y-%m')}        {promedio:<20.2f} {num_obs} observaciones")
    
    if valores_orig:
        print(f"  Valores incluidos en el promedio:")
        for v in valores_orig:
            print(f"    - {v['fecha']}: {v['valor']:.2f}")
        print()

conn.close()

print(f"\nEXPLICACION:")
print(f"   - Se agruparon todas las observaciones semanales que caen dentro de enero 2025")
print(f"   - Se calculó el promedio de esas observaciones")
print(f"   - El resultado es un único valor mensual asignado al primer día del mes (2025-01-01)")
print(f"   - Este proceso se repite para cada mes del rango seleccionado")
