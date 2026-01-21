"""
Script para verificar datos del ID 5 (Precio carne export)
"""
import sqlite3
import pandas as pd

DB_NAME = "series_tiempo.db"
MAESTRO_ID = 5

conn = sqlite3.connect(DB_NAME)
cursor = conn.cursor()

# Obtener información de la serie
cursor.execute("SELECT * FROM maestro WHERE id = ?", (MAESTRO_ID,))
maestro_row = cursor.fetchone()

if not maestro_row:
    print(f"[ERROR] No se encontró la serie con ID {MAESTRO_ID}")
    conn.close()
    exit(1)

# Obtener nombres de columnas
cursor.execute("PRAGMA table_info(maestro)")
columnas_maestro = [col[1] for col in cursor.fetchall()]

# Crear diccionario con los datos
maestro_dict = dict(zip(columnas_maestro, maestro_row))

print("=" * 80)
print(f"INFORMACION DE LA SERIE ID {MAESTRO_ID}")
print("=" * 80)
print(f"Nombre: {maestro_dict.get('nombre', 'N/A')}")
print(f"Tipo: {maestro_dict.get('tipo', 'N/A')}")
print(f"Fuente: {maestro_dict.get('fuente', 'N/A')}")
print(f"Periodicidad: {maestro_dict.get('periodicidad', 'N/A')}")
print(f"Unidad: {maestro_dict.get('unidad', 'N/A')}")
print(f"Categoria: {maestro_dict.get('categoria', 'N/A')}")
print(f"Activo: {maestro_dict.get('activo', 'N/A')}")
print(f"Mercado: {maestro_dict.get('mercado', 'N/A')}")
print(f"Link: {maestro_dict.get('link', 'N/A')}")

# Verificar datos en maestro_precios
print("\n" + "=" * 80)
print("DATOS EN maestro_precios")
print("=" * 80)

cursor.execute(
    "SELECT COUNT(*) FROM maestro_precios WHERE maestro_id = ?",
    (MAESTRO_ID,)
)
total_registros = cursor.fetchone()[0]

print(f"\nTotal de registros: {total_registros}")

if total_registros > 0:
    # Obtener rango de fechas
    cursor.execute(
        """
        SELECT MIN(fecha), MAX(fecha), MIN(valor), MAX(valor), AVG(valor)
        FROM maestro_precios
        WHERE maestro_id = ?
        """,
        (MAESTRO_ID,)
    )
    min_fecha, max_fecha, min_valor, max_valor, avg_valor = cursor.fetchone()
    
    print(f"\nRango de fechas: {min_fecha} a {max_fecha}")
    print(f"Valor mínimo: {min_valor:.2f}")
    print(f"Valor máximo: {max_valor:.2f}")
    print(f"Valor promedio: {avg_valor:.2f}")
    
    # Mostrar primeros y últimos registros
    print("\nPrimeros 5 registros:")
    df_primeros = pd.read_sql_query(
        """
        SELECT fecha, valor
        FROM maestro_precios
        WHERE maestro_id = ?
        ORDER BY fecha ASC
        LIMIT 5
        """,
        conn,
        params=(MAESTRO_ID,)
    )
    print(df_primeros.to_string(index=False))
    
    print("\nÚltimos 5 registros:")
    df_ultimos = pd.read_sql_query(
        """
        SELECT fecha, valor
        FROM maestro_precios
        WHERE maestro_id = ?
        ORDER BY fecha DESC
        LIMIT 5
        """,
        conn,
        params=(MAESTRO_ID,)
    )
    print(df_ultimos.to_string(index=False))
    
    # Verificar periodicidad esperada vs real
    print("\n[INFO] Verificando periodicidad...")
    df_todas = pd.read_sql_query(
        """
        SELECT fecha, valor
        FROM maestro_precios
        WHERE maestro_id = ?
        ORDER BY fecha ASC
        """,
        conn,
        params=(MAESTRO_ID,)
    )
    df_todas['fecha'] = pd.to_datetime(df_todas['fecha'])
    df_todas = df_todas.sort_values('fecha')
    
    # Calcular diferencias entre fechas consecutivas
    df_todas['diff_dias'] = df_todas['fecha'].diff().dt.days
    
    periodicidad_esperada = maestro_dict.get('periodicidad', 'M')
    if periodicidad_esperada == 'W':
        esperado_dias = 7
    elif periodicidad_esperada == 'M':
        esperado_dias = 28  # Aproximadamente mensual
    else:
        esperado_dias = 1
    
    diff_promedio = df_todas['diff_dias'].mean()
    print(f"   Periodicidad esperada: {periodicidad_esperada}")
    print(f"   Diferencia promedio entre fechas: {diff_promedio:.1f} días")
    
else:
    print("\n[WARN] No hay registros en maestro_precios para este ID")

print("\n" + "=" * 80)

conn.close()
