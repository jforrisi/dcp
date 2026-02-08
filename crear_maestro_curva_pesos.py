"""
Script para crear 15 registros en la tabla maestro para las variables de curva de pesos
de Uruguay con fuente BEVSA y periodicidad diaria
"""

import sqlite3
import os

# Configuración
DB_NAME = "series_tiempo.db"
FUENTE = "BEVSA"
PERIODICIDAD = "D"  # Diario
TIPO = "M"  # Macro
ACTIVO = 1

# IDs de las variables creadas anteriormente (37-51)
ID_VARIABLES = list(range(37, 52))  # [37, 38, 39, ..., 51]

def obtener_id_uruguay(conn):
    """Obtiene el ID de Uruguay en pais_grupo."""
    cursor = conn.cursor()
    
    # Verificar estructura de pais_grupo
    cursor.execute("PRAGMA table_info(pais_grupo)")
    columnas = [col[1] for col in cursor.fetchall()]
    
    # Determinar nombre de columnas
    id_col = 'id_pais' if 'id_pais' in columnas else 'id_pais_grupo'
    nombre_col = 'nombre_pais' if 'nombre_pais' in columnas else 'nombre_pais_grupo'
    
    # Buscar Uruguay con diferentes variaciones
    cursor.execute(f"""
        SELECT {id_col}, {nombre_col} 
        FROM pais_grupo 
        WHERE {nombre_col} LIKE '%Uruguay%' 
           OR {nombre_col} LIKE '%uruguay%'
        ORDER BY {id_col}
    """)
    resultados = cursor.fetchall()
    
    if not resultados:
        raise ValueError("No se encontró Uruguay en la tabla pais_grupo")
    
    if len(resultados) > 1:
        print(f"[WARN] Se encontraron múltiples registros de Uruguay:")
        for id_pais, nombre in resultados:
            print(f"  - ID {id_pais}: {nombre}")
        print(f"[INFO] Usando el primero: ID {resultados[0][0]}")
    
    return resultados[0][0]

def verificar_estructura_maestro(conn):
    """Verifica la estructura de la tabla maestro."""
    cursor = conn.cursor()
    cursor.execute("PRAGMA table_info(maestro)")
    columnas = [col[1] for col in cursor.fetchall()]
    
    print(f"[INFO] Columnas en maestro: {', '.join(columnas)}")
    
    # Verificar columnas necesarias
    tiene_id_variable = 'id_variable' in columnas or 'id_nombre_variable' in columnas
    tiene_id_pais = 'id_pais' in columnas or 'id_region' in columnas
    
    if not tiene_id_variable:
        raise ValueError("La tabla maestro no tiene columna id_variable ni id_nombre_variable")
    
    if not tiene_id_pais:
        raise ValueError("La tabla maestro no tiene columna id_pais ni id_region")
    
    return {
        'id_variable_col': 'id_variable' if 'id_variable' in columnas else 'id_nombre_variable',
        'id_pais_col': 'id_pais' if 'id_pais' in columnas else 'id_region',
        'tiene_nombre': 'nombre' in columnas,
        'tiene_tipo': 'tipo' in columnas,
        'tiene_fuente': 'fuente' in columnas,
        'tiene_periodicidad': 'periodicidad' in columnas,
        'tiene_activo': 'activo' in columnas
    }

def verificar_variables_existentes(conn, id_variables):
    """Verifica que todas las variables existen."""
    cursor = conn.cursor()
    variables_faltantes = []
    
    for id_var in id_variables:
        cursor.execute("SELECT id_variable, id_nombre_variable FROM variables WHERE id_variable = ?", (id_var,))
        if not cursor.fetchone():
            variables_faltantes.append(id_var)
    
    if variables_faltantes:
        raise ValueError(f"Las siguientes variables no existen: {variables_faltantes}")
    
    print(f"[OK] Todas las {len(id_variables)} variables existen")

def verificar_registros_existentes(conn, id_variables, id_uruguay, estructura):
    """Verifica si ya existen registros en maestro para estas variables y Uruguay."""
    cursor = conn.cursor()
    registros_existentes = []
    
    id_variable_col = estructura['id_variable_col']
    id_pais_col = estructura['id_pais_col']
    
    for id_var in id_variables:
        query = f"SELECT id FROM maestro WHERE {id_variable_col} = ? AND {id_pais_col} = ?"
        cursor.execute(query, (id_var, id_uruguay))
        if cursor.fetchone():
            registros_existentes.append(id_var)
    
    return registros_existentes

def obtener_siguiente_id_maestro(conn):
    """Obtiene el siguiente ID disponible en maestro."""
    cursor = conn.cursor()
    cursor.execute("SELECT MAX(id) FROM maestro")
    max_id = cursor.fetchone()[0]
    return (max_id or 0) + 1

def obtener_nombre_variable(conn, id_variable):
    """Obtiene el nombre de la variable."""
    cursor = conn.cursor()
    cursor.execute("SELECT id_nombre_variable FROM variables WHERE id_variable = ?", (id_variable,))
    resultado = cursor.fetchone()
    return resultado[0] if resultado else None

def crear_registros_maestro(conn):
    """Crea los 15 registros en maestro."""
    cursor = conn.cursor()
    
    # Verificar estructura
    print("\n[INFO] Verificando estructura de maestro...")
    estructura = verificar_estructura_maestro(conn)
    
    # Obtener ID de Uruguay
    print("\n[INFO] Obteniendo ID de Uruguay...")
    id_uruguay = obtener_id_uruguay(conn)
    print(f"[OK] ID de Uruguay: {id_uruguay}")
    
    # Verificar variables
    print(f"\n[INFO] Verificando que las {len(ID_VARIABLES)} variables existen...")
    verificar_variables_existentes(conn, ID_VARIABLES)
    
    # Verificar registros existentes
    print(f"\n[INFO] Verificando registros existentes...")
    registros_existentes = verificar_registros_existentes(conn, ID_VARIABLES, id_uruguay, estructura)
    if registros_existentes:
        print(f"[WARN] Se encontraron {len(registros_existentes)} registros existentes:")
        for id_var in registros_existentes:
            nombre = obtener_nombre_variable(conn, id_var)
            print(f"  - Variable ID {id_var}: {nombre}")
        respuesta = input("\n¿Deseas continuar y crear solo los que no existen? (s/n): ")
        if respuesta.lower() != 's':
            print("[INFO] Operación cancelada")
            return
    else:
        print("[OK] No se encontraron registros duplicados")
    
    # Obtener siguiente ID
    siguiente_id = obtener_siguiente_id_maestro(conn)
    print(f"\n[INFO] Siguiente ID disponible en maestro: {siguiente_id}")
    
    # Preparar columnas y valores
    id_variable_col = estructura['id_variable_col']
    id_pais_col = estructura['id_pais_col']
    
    # Construir query dinámicamente
    campos = ['id', id_variable_col, id_pais_col, 'fuente', 'periodicidad', 'activo']
    valores_base = [None, None, id_uruguay, FUENTE, PERIODICIDAD, ACTIVO]
    
    if estructura['tiene_nombre']:
        campos.append('nombre')
        valores_base.append(None)
    
    if estructura['tiene_tipo']:
        campos.append('tipo')
        valores_base.append(TIPO)
    
    placeholders = ', '.join(['?'] * len(campos))
    campos_str = ', '.join(campos)
    
    # Crear registros
    print(f"\n[INFO] Creando {len(ID_VARIABLES)} registros en maestro...")
    registros_creados = 0
    registros_omitidos = 0
    
    for i, id_var in enumerate(ID_VARIABLES):
        # Verificar si ya existe
        query_check = f"SELECT id FROM maestro WHERE {id_variable_col} = ? AND {id_pais_col} = ?"
        cursor.execute(query_check, (id_var, id_uruguay))
        if cursor.fetchone():
            print(f"[SKIP] Registro para variable {id_var} ya existe, omitiendo...")
            registros_omitidos += 1
            continue
        
        # Obtener nombre de la variable
        nombre_var = obtener_nombre_variable(conn, id_var)
        
        # Preparar valores
        valores = valores_base.copy()
        valores[0] = siguiente_id + i - registros_omitidos  # ID
        valores[1] = id_var  # id_variable
        
        # Si tiene nombre, usar el nombre de la variable
        if estructura['tiene_nombre']:
            idx_nombre = campos.index('nombre')
            valores[idx_nombre] = nombre_var
        
        # Insertar
        try:
            insert_query = f"INSERT INTO maestro ({campos_str}) VALUES ({placeholders})"
            cursor.execute(insert_query, valores)
            print(f"[OK] Registro creado: ID {valores[0]} - Variable {id_var} ({nombre_var}) - Uruguay")
            registros_creados += 1
        except sqlite3.IntegrityError as e:
            print(f"[ERROR] Error al crear registro para variable {id_var}: {e}")
            registros_omitidos += 1
    
    # Confirmar cambios
    conn.commit()
    
    print(f"\n[RESUMEN]")
    print(f"  Registros creados: {registros_creados}")
    print(f"  Registros omitidos: {registros_omitidos}")
    print(f"  Total procesados: {len(ID_VARIABLES)}")
    
    if registros_creados > 0:
        print(f"\n[OK] {registros_creados} registros creados exitosamente en maestro")
    else:
        print(f"\n[INFO] No se crearon nuevos registros (todos ya existían)")

def main():
    """Función principal."""
    print("=" * 80)
    print("CREACIÓN DE REGISTROS EN MAESTRO - CURVA DE PESOS")
    print("=" * 80)
    print(f"Base de datos: {DB_NAME}")
    print(f"Fuente: {FUENTE}")
    print(f"Periodicidad: {PERIODICIDAD} (Diario)")
    print(f"Tipo: {TIPO} (Macro)")
    print(f"Total de variables: {len(ID_VARIABLES)}")
    print("=" * 80)
    
    # Verificar que existe la base de datos
    if not os.path.exists(DB_NAME):
        print(f"[ERROR] No se encontró la base de datos: {DB_NAME}")
        print(f"[INFO] Asegúrate de ejecutar este script desde la raíz del proyecto")
        return
    
    # Conectar a la base de datos
    try:
        conn = sqlite3.connect(DB_NAME)
        print(f"\n[OK] Conectado a la base de datos: {DB_NAME}")
        
        # Crear registros
        crear_registros_maestro(conn)
        
        conn.close()
        print(f"\n[OK] Conexión cerrada")
        
    except Exception as e:
        print(f"\n[ERROR] Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
