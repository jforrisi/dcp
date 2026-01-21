"""
Script de diagnóstico 2: Conversión Tipo de Cambio Diario a Mensual
=====================================================================
Prueba la conversión de tipo de cambio diario a promedio mensual.
"""

import sqlite3
from datetime import date
from pathlib import Path

# Conectar a la base de datos
DB_PATH = Path(__file__).parent / "series_tiempo.db"
conn = sqlite3.connect(str(DB_PATH))
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

print("=" * 80)
print("DIAGNÓSTICO 2: CONVERSIÓN TC DIARIO A MENSUAL")
print("=" * 80)

# Configuración de prueba
TC_USD_ID = 6  # Tipo de cambio USD/UYU
FECHA_DESDE = date(2024, 1, 1)
FECHA_HASTA = date(2024, 3, 31)  # 3 meses para ver mejor el detalle

print(f"\nConfiguración:")
print(f"  TC USD/UYU ID: {TC_USD_ID}")
print(f"  Rango: {FECHA_DESDE} a {FECHA_HASTA}")

# 1. Obtener información del tipo de cambio
print(f"\n1. Información del tipo de cambio:")
cursor.execute("""
    SELECT id, nombre, periodicidad
    FROM maestro
    WHERE id = ?
""", (TC_USD_ID,))
tc_info = cursor.fetchone()

if not tc_info:
    print(f"  ERROR: No se encontró tipo de cambio con ID {TC_USD_ID}")
    conn.close()
    exit(1)

print(f"  Nombre: {tc_info['nombre']}")
print(f"  Periodicidad: {tc_info['periodicidad']}")

# 2. Obtener datos diarios
print(f"\n2. Obteniendo datos diarios:")
cursor.execute("""
    SELECT fecha, valor
    FROM maestro_precios
    WHERE maestro_id = ? AND fecha BETWEEN ? AND ?
    ORDER BY fecha ASC
""", (TC_USD_ID, FECHA_DESDE, FECHA_HASTA))
tc_diarios = cursor.fetchall()

if not tc_diarios:
    print(f"  ERROR: No se encontraron datos de tipo de cambio")
    conn.close()
    exit(1)

print(f"  Registros diarios encontrados: {len(tc_diarios)}")
print(f"  Primera fecha: {tc_diarios[0]['fecha']}")
print(f"  Última fecha: {tc_diarios[-1]['fecha']}")

# Mostrar algunos valores diarios
print(f"\n  Primeros 10 valores diarios:")
print(f"  {'Fecha':<12} {'TC':>12}")
print(f"  {'-'*12} {'-'*12}")
for tc in tc_diarios[:10]:
    fecha_str = str(tc['fecha'])
    print(f"  {fecha_str:<12} {float(tc['valor']):>12.4f}")

def parse_fecha(fecha_str):
    """Convierte fecha de SQLite (puede ser date o datetime string) a date."""
    if isinstance(fecha_str, date):
        return fecha_str
    fecha_str = str(fecha_str)
    # Si tiene hora, tomar solo la parte de fecha
    if ' ' in fecha_str:
        fecha_str = fecha_str.split(' ')[0]
    return date.fromisoformat(fecha_str)

# 3. Convertir a mensual (agrupar por mes y calcular promedio)
print(f"\n3. Convirtiendo a mensual (promedio):")
monthly_dict = {}

for tc in tc_diarios:
    fecha_obj = parse_fecha(tc['fecha'])
    year_month = (fecha_obj.year, fecha_obj.month)
    
    if year_month not in monthly_dict:
        monthly_dict[year_month] = {'sum': 0.0, 'count': 0, 'valores': []}
    
    valor = float(tc['valor'])
    monthly_dict[year_month]['sum'] += valor
    monthly_dict[year_month]['count'] += 1
    monthly_dict[year_month]['valores'].append(valor)

# Calcular promedios
tc_mensuales = []
for (year, month), stats in sorted(monthly_dict.items()):
    promedio = stats['sum'] / stats['count']
    fecha_mes = date(year, month, 1)
    tc_mensuales.append({
        'fecha': fecha_mes,
        'promedio': promedio,
        'count': stats['count'],
        'min': min(stats['valores']),
        'max': max(stats['valores'])
    })

print(f"  Meses calculados: {len(tc_mensuales)}")
print(f"\n  Resultados mensuales:")
print(f"  {'Mes':<12} {'Promedio':>12} {'Min':>12} {'Max':>12} {'Días':>8}")
print(f"  {'-'*12} {'-'*12} {'-'*12} {'-'*12} {'-'*8}")
for tc in tc_mensuales:
    print(f"  {tc['fecha']}  {tc['promedio']:>12.4f}  {tc['min']:>12.4f}  {tc['max']:>12.4f}  {tc['count']:>8}")

# 4. Validación: comparar con función convert_to_monthly
print(f"\n4. Validación con función convert_to_monthly:")
try:
    # Importar función del módulo
    import sys
    sys.path.insert(0, str(Path(__file__).parent / "backend"))
    from app.routers.dcp import convert_to_monthly
    
    # Preparar datos en formato esperado
    tc_data = [
        {'fecha': parse_fecha(tc['fecha']), 'valor': float(tc['valor'])}
        for tc in tc_diarios
    ]
    
    # Convertir usando función
    tc_mensual_func = convert_to_monthly(tc_data, 'D')
    
    print(f"  Meses usando función: {len(tc_mensual_func)}")
    print(f"\n  Comparación (primeros 5 meses):")
    print(f"  {'Mes':<12} {'Manual':>12} {'Función':>12} {'Diferencia':>12}")
    print(f"  {'-'*12} {'-'*12} {'-'*12} {'-'*12}")
    
    for i, tc_manual in enumerate(tc_mensuales[:5]):
        if i < len(tc_mensual_func):
            tc_func = tc_mensual_func[i]
            diff = abs(tc_manual['promedio'] - tc_func['valor'])
            match = "✓" if diff < 0.0001 else "✗"
            print(f"  {tc_manual['fecha']}  {tc_manual['promedio']:>12.4f}  {tc_func['valor']:>12.4f}  {diff:>12.6f} {match}")
    
    print(f"\n  Validación: {'✓ OK' if len(tc_mensuales) == len(tc_mensual_func) else '✗ DIFERENTE'}")
    
except Exception as e:
    print(f"  ERROR al importar función: {str(e)}")
    print(f"  (Esto es normal si el módulo no está disponible)")

print(f"\n{'='*80}")
print("DIAGNÓSTICO 2 COMPLETADO")
print(f"{'='*80}")

conn.close()
