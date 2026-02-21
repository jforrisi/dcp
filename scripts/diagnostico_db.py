"""
Script de diagnóstico para verificar conexión a base de datos y datos recientes.
"""
import os
import sys
from pathlib import Path
from datetime import datetime, timedelta

# Agregar raíz del proyecto al path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Cargar .env
try:
    from dotenv import load_dotenv
    load_dotenv(PROJECT_ROOT / ".env")
except ImportError:
    pass

print("=" * 80)
print("DIAGNÓSTICO DE BASE DE DATOS")
print("=" * 80)
print()

# 1. Verificar DATABASE_URL
print("1. Verificando DATABASE_URL...")
database_url = os.environ.get("DATABASE_URL")
if database_url:
    # Ocultar contraseña en el output
    if "@" in database_url:
        parts = database_url.split("@")
        if ":" in parts[0]:
            user_pass = parts[0].split("://")[1] if "://" in parts[0] else parts[0]
            if ":" in user_pass:
                user, _ = user_pass.split(":", 1)
                masked_url = database_url.replace(user_pass, f"{user}:***")
            else:
                masked_url = database_url
        else:
            masked_url = database_url
    else:
        masked_url = database_url
    print(f"   [OK] DATABASE_URL está configurada: {masked_url[:80]}...")
else:
    print("   [ERROR] DATABASE_URL NO está configurada")
    print("   Esto causará que los scripts fallen al intentar conectarse a la BD")
    sys.exit(1)

print()

# 2. Intentar conectar a la base de datos
print("2. Intentando conectar a la base de datos...")
try:
    from db.connection import get_db_connection, execute_query
    conn = get_db_connection()
    print("   [OK] Conexión exitosa a PostgreSQL")
    conn.close()
except Exception as e:
    print(f"   [ERROR] Error al conectar: {e}")
    sys.exit(1)

print()

# 3. Verificar datos recientes en maestro_precios
print("3. Verificando datos recientes en maestro_precios...")
try:
    # Obtener la fecha más reciente en maestro_precios
    query = """
        SELECT MAX(fecha) as fecha_maxima, COUNT(*) as total_registros
        FROM maestro_precios
    """
    result = execute_query(query)
    if result and len(result) > 0:
        fecha_max = result[0].get('fecha_maxima')
        total = result[0].get('total_registros', 0)
        print(f"   [OK] Total de registros: {total:,}")
        if fecha_max:
            fecha_max_obj = fecha_max if isinstance(fecha_max, datetime) else datetime.fromisoformat(str(fecha_max))
            dias_desde_ultimo = (datetime.now() - fecha_max_obj).days
            print(f"   [OK] Fecha más reciente: {fecha_max_obj.strftime('%Y-%m-%d')} ({dias_desde_ultimo} días atrás)")
            if dias_desde_ultimo > 7:
                print(f"   [WARN] ADVERTENCIA: Los datos más recientes tienen más de 7 días")
        else:
            print("   [WARN] No hay fechas en maestro_precios")
    else:
        print("   [WARN] No se encontraron datos en maestro_precios")
except Exception as e:
    print(f"   ✗ Error al consultar datos: {e}")

print()

# 4. Verificar datos insertados en las últimas 24 horas
print("4. Verificando datos insertados en las últimas 24 horas...")
try:
    fecha_ayer = datetime.now() - timedelta(days=1)
    query = """
        SELECT COUNT(*) as registros_recientes
        FROM maestro_precios
        WHERE fecha >= ?
    """
    result = execute_query(query, (fecha_ayer.date(),))
    if result and len(result) > 0:
        registros_recientes = result[0].get('registros_recientes', 0)
        print(f"   [OK] Registros insertados en últimas 24h: {registros_recientes:,}")
        if registros_recientes == 0:
            print("   [WARN] ADVERTENCIA: No se insertaron datos en las últimas 24 horas")
    else:
        print("   [WARN] No se encontraron datos recientes")
except Exception as e:
    print(f"   [ERROR] Error al consultar datos recientes: {e}")

print()

# 5. Verificar algunas variables específicas (IPE)
print("5. Verificando variables IPE (53-68)...")
try:
    query = """
        SELECT v.id_variable, v.id_nombre_variable, v.moneda,
               COUNT(mp.fecha) as registros,
               MAX(mp.fecha) as fecha_maxima
        FROM variables v
        LEFT JOIN maestro_precios mp ON v.id_variable = mp.id_variable AND mp.id_pais = 858
        WHERE v.id_variable BETWEEN 53 AND 68
        GROUP BY v.id_variable, v.id_nombre_variable, v.moneda
        ORDER BY v.id_variable
    """
    result = execute_query(query)
    if result:
        print(f"   [OK] Variables IPE encontradas: {len(result)}")
        for row in result:
            id_var = row.get('id_variable')
            nombre = row.get('id_nombre_variable', 'N/A')
            moneda = row.get('moneda', 'N/A')
            registros = row.get('registros', 0)
            fecha_max = row.get('fecha_maxima')
            fecha_str = fecha_max.strftime('%Y-%m-%d') if fecha_max else 'N/A'
            print(f"      - {id_var}: {nombre[:40]:40} | Moneda: {moneda:5} | Registros: {registros:6} | Última fecha: {fecha_str}")
    else:
        print("   [WARN] No se encontraron variables IPE")
except Exception as e:
    print(f"   [ERROR] Error al consultar variables IPE: {e}")

print()
print("=" * 80)
print("FIN DEL DIAGNÓSTICO")
print("=" * 80)
