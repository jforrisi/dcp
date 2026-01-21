"""
Script de diagnóstico 1: Cálculo Precio / IPC
==============================================
Prueba el cálculo básico de Precio dividido por IPC para un producto.
"""

import sqlite3
from datetime import date, datetime
from pathlib import Path

# Conectar a la base de datos
DB_PATH = Path(__file__).parent / "series_tiempo.db"
conn = sqlite3.connect(str(DB_PATH))
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

print("=" * 80)
print("DIAGNÓSTICO 1: CÁLCULO PRECIO / IPC")
print("=" * 80)

# Configuración de prueba
PRODUCTO_ID = 1  # Cambiar según necesidad
IPC_ID = 11
FECHA_DESDE = date(2024, 1, 1)
FECHA_HASTA = date(2024, 12, 31)

print(f"\nConfiguración:")
print(f"  Producto ID: {PRODUCTO_ID}")
print(f"  IPC ID: {IPC_ID}")
print(f"  Rango: {FECHA_DESDE} a {FECHA_HASTA}")

# 1. Obtener información del producto
print(f"\n1. Información del producto:")
cursor.execute("""
    SELECT id, nombre, periodicidad, unidad
    FROM maestro
    WHERE id = ? AND tipo = 'P' AND activo = 1
""", (PRODUCTO_ID,))
producto = cursor.fetchone()

if not producto:
    print(f"  ERROR: No se encontró producto con ID {PRODUCTO_ID}")
    conn.close()
    exit(1)

print(f"  Nombre: {producto['nombre']}")
print(f"  Periodicidad: {producto['periodicidad']}")
print(f"  Unidad: {producto['unidad']}")

# 2. Obtener precios del producto
print(f"\n2. Obteniendo precios del producto:")
cursor.execute("""
    SELECT fecha, valor
    FROM maestro_precios
    WHERE maestro_id = ? AND fecha BETWEEN ? AND ?
    ORDER BY fecha ASC
""", (PRODUCTO_ID, FECHA_DESDE, FECHA_HASTA))
precios_raw = cursor.fetchall()

if not precios_raw:
    print(f"  ERROR: No se encontraron precios para el producto")
    conn.close()
    exit(1)

print(f"  Registros encontrados: {len(precios_raw)}")
print(f"  Primera fecha: {precios_raw[0]['fecha']}")
print(f"  Última fecha: {precios_raw[-1]['fecha']}")

# 3. Convertir precios a mensual (simplificado)
print(f"\n3. Convirtiendo precios a mensual:")
periodicidad = producto['periodicidad']

def parse_fecha(fecha_str):
    """Convierte fecha de SQLite (puede ser date o datetime string) a date."""
    if isinstance(fecha_str, date):
        return fecha_str
    fecha_str = str(fecha_str)
    # Si tiene hora, tomar solo la parte de fecha
    if ' ' in fecha_str:
        fecha_str = fecha_str.split(' ')[0]
    return date.fromisoformat(fecha_str)

if periodicidad == 'M':
    # Ya es mensual
    precios_mensuales = [
        {
            'fecha': parse_fecha(p['fecha']),
            'valor': float(p['valor'])
        }
        for p in precios_raw
    ]
    # Normalizar fechas al primer día del mes
    precios_mensuales = [
        {
            'fecha': date(p['fecha'].year, p['fecha'].month, 1),
            'valor': p['valor']
        }
        for p in precios_mensuales
    ]
else:
    # Agrupar por mes y calcular promedio
    monthly_dict = {}
    for p in precios_raw:
        fecha_obj = parse_fecha(p['fecha'])
        year_month = (fecha_obj.year, fecha_obj.month)
        
        if year_month not in monthly_dict:
            monthly_dict[year_month] = {'sum': 0.0, 'count': 0}
        
        monthly_dict[year_month]['sum'] += float(p['valor'])
        monthly_dict[year_month]['count'] += 1
    
    precios_mensuales = [
        {
            'fecha': date(year, month, 1),
            'valor': stats['sum'] / stats['count']
        }
        for (year, month), stats in sorted(monthly_dict.items())
    ]

print(f"  Meses con datos: {len(precios_mensuales)}")
if precios_mensuales:
    print(f"  Primer mes: {precios_mensuales[0]['fecha']}, Precio: {precios_mensuales[0]['valor']:.4f}")
    print(f"  Último mes: {precios_mensuales[-1]['fecha']}, Precio: {precios_mensuales[-1]['valor']:.4f}")

# 4. Obtener IPC mensual
print(f"\n4. Obteniendo IPC mensual:")
cursor.execute("""
    SELECT fecha, valor
    FROM maestro_precios
    WHERE maestro_id = ? AND fecha BETWEEN ? AND ?
    ORDER BY fecha ASC
""", (IPC_ID, FECHA_DESDE, FECHA_HASTA))
ipc_raw = cursor.fetchall()

if not ipc_raw:
    print(f"  ERROR: No se encontraron datos de IPC")
    conn.close()
    exit(1)

print(f"  Registros encontrados: {len(ipc_raw)}")

# IPC ya es mensual, solo normalizar fechas
ipc_mensual = {}
for ipc in ipc_raw:
    fecha_obj = parse_fecha(ipc['fecha'])
    fecha_mes = date(fecha_obj.year, fecha_obj.month, 1)
    ipc_mensual[fecha_mes] = float(ipc['valor'])

print(f"  Meses con IPC: {len(ipc_mensual)}")
if ipc_mensual:
    primera_fecha = min(ipc_mensual.keys())
    ultima_fecha = max(ipc_mensual.keys())
    print(f"  Primer mes: {primera_fecha}, IPC: {ipc_mensual[primera_fecha]:.4f}")
    print(f"  Último mes: {ultima_fecha}, IPC: {ipc_mensual[ultima_fecha]:.4f}")

# 5. Calcular Precio / IPC
print(f"\n5. Calculando Precio / IPC:")
resultados = []
for precio_item in precios_mensuales:
    mes_fecha = precio_item['fecha']
    precio = precio_item['valor']
    
    if mes_fecha in ipc_mensual:
        ipc_valor = ipc_mensual[mes_fecha]
        if ipc_valor > 0:
            ratio = precio / ipc_valor
            resultados.append({
                'fecha': mes_fecha,
                'precio': precio,
                'ipc': ipc_valor,
                'precio_ipc': ratio
            })

if not resultados:
    print(f"  ERROR: No se encontraron meses con datos de precio e IPC")
    conn.close()
    exit(1)

print(f"\n  Meses calculados: {len(resultados)}")
print(f"\n  Primeros 5 resultados:")
print(f"  {'Fecha':<12} {'Precio':>12} {'IPC':>12} {'Precio/IPC':>15}")
print(f"  {'-'*12} {'-'*12} {'-'*12} {'-'*15}")
for r in resultados[:5]:
    print(f"  {r['fecha']}  {r['precio']:>12.4f}  {r['ipc']:>12.4f}  {r['precio_ipc']:>15.6f}")

if len(resultados) > 5:
    print(f"\n  Últimos 5 resultados:")
    print(f"  {'Fecha':<12} {'Precio':>12} {'IPC':>12} {'Precio/IPC':>15}")
    print(f"  {'-'*12} {'-'*12} {'-'*12} {'-'*15}")
    for r in resultados[-5:]:
        print(f"  {r['fecha']}  {r['precio']:>12.4f}  {r['ipc']:>12.4f}  {r['precio_ipc']:>15.6f}")

print(f"\n  Estadísticas:")
print(f"    Min Precio/IPC: {min(r['precio_ipc'] for r in resultados):.6f}")
print(f"    Max Precio/IPC: {max(r['precio_ipc'] for r in resultados):.6f}")
print(f"    Promedio Precio/IPC: {sum(r['precio_ipc'] for r in resultados) / len(resultados):.6f}")

print(f"\n{'='*80}")
print("DIAGNÓSTICO 1 COMPLETADO")
print(f"{'='*80}")

conn.close()
