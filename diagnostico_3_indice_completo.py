"""
Script de diagnóstico 3: Cálculo Completo del Índice DCP
==========================================================
Prueba el cálculo completo: (Precio / IPC) × TC
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
print("DIAGNÓSTICO 3: CÁLCULO COMPLETO ÍNDICE DCP")
print("=" * 80)

# Configuración de prueba
PRODUCTO_ID = 1  # Cambiar según necesidad
TC_USD_ID = 6
IPC_ID = 11
FECHA_DESDE = date(2024, 1, 1)
FECHA_HASTA = date(2024, 12, 31)

print(f"\nConfiguración:")
print(f"  Producto ID: {PRODUCTO_ID}")
print(f"  TC USD/UYU ID: {TC_USD_ID}")
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

# 2. Obtener y convertir precios a mensual
print(f"\n2. Obteniendo precios mensuales:")
cursor.execute("""
    SELECT fecha, valor
    FROM maestro_precios
    WHERE maestro_id = ? AND fecha BETWEEN ? AND ?
    ORDER BY fecha ASC
""", (PRODUCTO_ID, FECHA_DESDE, FECHA_HASTA))
precios_raw = cursor.fetchall()

if not precios_raw:
    print(f"  ERROR: No se encontraron precios")
    conn.close()
    exit(1)

def parse_fecha(fecha_str):
    """Convierte fecha de SQLite (puede ser date o datetime string) a date."""
    if isinstance(fecha_str, date):
        return fecha_str
    fecha_str = str(fecha_str)
    # Si tiene hora, tomar solo la parte de fecha
    if ' ' in fecha_str:
        fecha_str = fecha_str.split(' ')[0]
    return date.fromisoformat(fecha_str)

# Convertir a mensual
periodicidad = producto['periodicidad']
if periodicidad == 'M':
    precios_mensuales = [
        {
            'fecha': parse_fecha(p['fecha']),
            'valor': float(p['valor'])
        }
        for p in precios_raw
    ]
    precios_mensuales = [
        {'fecha': date(p['fecha'].year, p['fecha'].month, 1), 'valor': p['valor']}
        for p in precios_mensuales
    ]
else:
    monthly_dict = {}
    for p in precios_raw:
        fecha_obj = parse_fecha(p['fecha'])
        year_month = (fecha_obj.year, fecha_obj.month)
        if year_month not in monthly_dict:
            monthly_dict[year_month] = {'sum': 0.0, 'count': 0}
        monthly_dict[year_month]['sum'] += float(p['valor'])
        monthly_dict[year_month]['count'] += 1
    precios_mensuales = [
        {'fecha': date(year, month, 1), 'valor': stats['sum'] / stats['count']}
        for (year, month), stats in sorted(monthly_dict.items())
    ]

print(f"  Meses con precios: {len(precios_mensuales)}")

# 3. Obtener IPC mensual
print(f"\n3. Obteniendo IPC mensual:")
cursor.execute("""
    SELECT fecha, valor
    FROM maestro_precios
    WHERE maestro_id = ? AND fecha BETWEEN ? AND ?
    ORDER BY fecha ASC
""", (IPC_ID, FECHA_DESDE, FECHA_HASTA))
ipc_raw = cursor.fetchall()

ipc_mensual = {}
for ipc in ipc_raw:
    fecha_obj = parse_fecha(ipc['fecha'])
    fecha_mes = date(fecha_obj.year, fecha_obj.month, 1)
    ipc_mensual[fecha_mes] = float(ipc['valor'])

print(f"  Meses con IPC: {len(ipc_mensual)}")

# 4. Obtener TC mensual (promedio de diarios)
print(f"\n4. Obteniendo TC mensual:")
cursor.execute("""
    SELECT fecha, valor
    FROM maestro_precios
    WHERE maestro_id = ? AND fecha BETWEEN ? AND ?
    ORDER BY fecha ASC
""", (TC_USD_ID, FECHA_DESDE, FECHA_HASTA))
tc_diarios = cursor.fetchall()

# Convertir TC a mensual
monthly_dict = {}
for tc in tc_diarios:
    fecha_obj = parse_fecha(tc['fecha'])
    year_month = (fecha_obj.year, fecha_obj.month)
    if year_month not in monthly_dict:
        monthly_dict[year_month] = {'sum': 0.0, 'count': 0}
    monthly_dict[year_month]['sum'] += float(tc['valor'])
    monthly_dict[year_month]['count'] += 1

tc_mensual = {
    date(year, month, 1): stats['sum'] / stats['count']
    for (year, month), stats in monthly_dict.items()
}

print(f"  Meses con TC: {len(tc_mensual)}")

# 5. Calcular índice completo: (Precio / IPC) × TC
print(f"\n5. Calculando índice completo: (Precio / IPC) × TC")
resultados = []
for precio_item in precios_mensuales:
    mes_fecha = precio_item['fecha']
    precio = precio_item['valor']
    
    if mes_fecha in ipc_mensual and mes_fecha in tc_mensual:
        ipc_valor = ipc_mensual[mes_fecha]
        tc_valor = tc_mensual[mes_fecha]
        
        if ipc_valor > 0:
            precio_ipc = precio / ipc_valor
            indice = precio_ipc * tc_valor
            resultados.append({
                'fecha': mes_fecha,
                'precio': precio,
                'ipc': ipc_valor,
                'tc': tc_valor,
                'precio_ipc': precio_ipc,
                'indice': indice
            })

if not resultados:
    print(f"  ERROR: No se encontraron meses con todos los datos")
    conn.close()
    exit(1)

print(f"\n  Meses calculados: {len(resultados)}")
print(f"\n  Primeros 5 resultados:")
print(f"  {'Fecha':<12} {'Precio':>10} {'IPC':>10} {'TC':>10} {'Precio/IPC':>12} {'Índice':>12}")
print(f"  {'-'*12} {'-'*10} {'-'*10} {'-'*10} {'-'*12} {'-'*12}")
for r in resultados[:5]:
    print(f"  {r['fecha']}  {r['precio']:>10.4f}  {r['ipc']:>10.4f}  {r['tc']:>10.4f}  {r['precio_ipc']:>12.6f}  {r['indice']:>12.6f}")

# 6. Normalizar a base 100
print(f"\n6. Normalizando a base 100:")
if resultados:
    first_value = resultados[0]['indice']
    if first_value > 0:
        factor = 100.0 / first_value
        resultados_normalizados = [
            {
                'fecha': r['fecha'],
                'indice_original': r['indice'],
                'indice_normalizado': r['indice'] * factor
            }
            for r in resultados
        ]
        
        print(f"  Primer valor: {first_value:.6f}")
        print(f"  Factor: {factor:.6f}")
        print(f"\n  Primeros 5 resultados normalizados:")
        print(f"  {'Fecha':<12} {'Original':>12} {'Normalizado':>12}")
        print(f"  {'-'*12} {'-'*12} {'-'*12}")
        for r in resultados_normalizados[:5]:
            print(f"  {r['fecha']}  {r['indice_original']:>12.6f}  {r['indice_normalizado']:>12.6f}")
        
        print(f"\n  Estadísticas normalizados:")
        valores_norm = [r['indice_normalizado'] for r in resultados_normalizados]
        print(f"    Min: {min(valores_norm):.2f}")
        print(f"    Max: {max(valores_norm):.2f}")
        print(f"    Promedio: {sum(valores_norm) / len(valores_norm):.2f}")
        print(f"    Primer valor (debe ser 100): {resultados_normalizados[0]['indice_normalizado']:.2f}")

print(f"\n{'='*80}")
print("DIAGNÓSTICO 3 COMPLETADO")
print(f"{'='*80}")

conn.close()
