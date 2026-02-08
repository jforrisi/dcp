"""
Script para crear variables REALES de curva de pesos en la tabla variables
y sus correspondientes registros en maestro.
Basado en los plazos de la imagen: 3 meses, 6 meses, 1 año, 2 años, etc.
"""

import sqlite3
import os

# Configuración
DB_NAME = "series_tiempo.db"
ID_FAMILIA = 1
ID_SUB_FAMILIA = 10
NOMINAL_O_REAL = "r"  # real
MONEDA = "LC"

# Nombres de las variables según la foto (plazos)
NOMBRES_VARIABLES = [
    "3 meses",
    "6 meses",
    "1 año",
    "2 años",
    "3 años",
    "4 años",
    "5 años",
    "6 años",
    "7 años",
    "8 años",
    "9 años",
    "10 años",
    "15 años",
    "20 años",
    "25 años",
    "30 años"
]

# Configuración para maestro
ID_PAIS_URUGUAY = 858
FUENTE = "BEVSA"
PERIODICIDAD = "D"  # Diario
TIPO = None  # NULL (en blanco, no "M")
ACTIVO = 1


def verificar_familia_y_sub_familia(conn):
    """Verifica que existe familia 1 y sub_familia 10, y que sub_familia 10 pertenece a familia 1."""
    cursor = conn.cursor()
    
    # Verificar familia 1
    cursor.execute("SELECT id_familia, nombre_familia FROM familia WHERE id_familia = ?", (ID_FAMILIA,))
    familia = cursor.fetchone()
    if not familia:
        raise ValueError(f"No existe la familia con id_familia = {ID_FAMILIA}")
    print(f"[OK] Familia encontrada: {familia[0]} - {familia[1]}")
    
    # Verificar sub_familia 10
    cursor.execute("""
        SELECT sf.id_sub_familia, sf.nombre_sub_familia, sf.id_familia, f.nombre_familia
        FROM sub_familia sf
        LEFT JOIN familia f ON sf.id_familia = f.id_familia
        WHERE sf.id_sub_familia = ?
    """, (ID_SUB_FAMILIA,))
    sub_familia = cursor.fetchone()
    if not sub_familia:
        raise ValueError(f"No existe la sub_familia con id_sub_familia = {ID_SUB_FAMILIA}")
    
    print(f"[OK] Sub-familia encontrada: {sub_familia[0]} - {sub_familia[1]}")
    print(f"[INFO] Sub-familia pertenece a familia: {sub_familia[2]} - {sub_familia[3]}")
    
    # Verificar que sub_familia 10 pertenece a familia 1
    if sub_familia[2] != ID_FAMILIA:
        raise ValueError(
            f"La sub_familia {ID_SUB_FAMILIA} pertenece a familia {sub_familia[2]}, "
            f"no a familia {ID_FAMILIA}"
        )
    
    print(f"[OK] Verificación correcta: sub_familia {ID_SUB_FAMILIA} pertenece a familia {ID_FAMILIA}")
    return True


def obtener_siguiente_id_variable(conn):
    """Obtiene el siguiente id_variable disponible."""
    cursor = conn.cursor()
    cursor.execute("SELECT MAX(id_variable) FROM variables")
    max_id = cursor.fetchone()[0]
    return (max_id or 0) + 1


def verificar_variable_existe(conn, nombre, nominal_o_real):
    """Verifica si ya existe una variable con ese nombre y tipo (nominal/real)."""
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id_variable, id_nombre_variable, nominal_o_real 
        FROM variables 
        WHERE id_nombre_variable = ? AND nominal_o_real = ?
    """, (nombre, nominal_o_real))
    return cursor.fetchone()


def crear_variables(conn):
    """Crea las variables REALES en la tabla variables."""
    cursor = conn.cursor()
    
    # Verificar familia y sub_familia
    verificar_familia_y_sub_familia(conn)
    
    # Obtener siguiente ID
    siguiente_id = obtener_siguiente_id_variable(conn)
    print(f"\n[INFO] Siguiente id_variable disponible: {siguiente_id}")
    
    # Crear variables
    print(f"\n[INFO] Creando {len(NOMBRES_VARIABLES)} variables REALES...")
    variables_creadas = 0
    variables_omitidas = 0
    ids_variables_creadas = []
    
    for i, nombre in enumerate(NOMBRES_VARIABLES):
        # Verificar si ya existe una variable REAL con ese nombre
        existente = verificar_variable_existe(conn, nombre, NOMINAL_O_REAL)
        if existente:
            print(f"[SKIP] Variable REAL '{nombre}' ya existe (ID: {existente[0]}), omitiendo...")
            variables_omitidas += 1
            ids_variables_creadas.append(existente[0])
            continue
        
        # Crear variable
        id_variable = siguiente_id + i - variables_omitidas
        try:
            cursor.execute("""
                INSERT INTO variables (id_variable, id_nombre_variable, id_sub_familia, nominal_o_real, moneda)
                VALUES (?, ?, ?, ?, ?)
            """, (id_variable, nombre, ID_SUB_FAMILIA, NOMINAL_O_REAL, MONEDA))
            print(f"[OK] Variable REAL creada: ID {id_variable} - '{nombre}'")
            variables_creadas += 1
            ids_variables_creadas.append(id_variable)
        except sqlite3.IntegrityError as e:
            print(f"[ERROR] Error al crear variable '{nombre}': {e}")
            variables_omitidas += 1
    
    # Confirmar cambios
    conn.commit()
    
    print(f"\n[RESUMEN VARIABLES]")
    print(f"  Variables creadas: {variables_creadas}")
    print(f"  Variables omitidas: {variables_omitidas}")
    print(f"  Total procesadas: {len(NOMBRES_VARIABLES)}")
    
    if variables_creadas > 0:
        print(f"\n[OK] {variables_creadas} variables REALES creadas exitosamente")
    
    return ids_variables_creadas


def obtener_id_uruguay(conn):
    """Obtiene el ID de Uruguay en pais_grupo."""
    cursor = conn.cursor()
    
    # Verificar estructura de pais_grupo
    cursor.execute("PRAGMA table_info(pais_grupo)")
    columnas = [col[1] for col in cursor.fetchall()]
    
    # Determinar nombre de columnas
    id_col = 'id_pais' if 'id_pais' in columnas else 'id_pais_grupo'
    nombre_col = 'nombre_pais' if 'nombre_pais' in columnas else 'nombre_pais_grupo'
    
    # Buscar Uruguay
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
    tiene_id_variable = 'id_variable' in columnas
    tiene_id_pais = 'id_pais' in columnas
    
    if not tiene_id_variable:
        raise ValueError("La tabla maestro no tiene columna id_variable")
    
    if not tiene_id_pais:
        raise ValueError("La tabla maestro no tiene columna id_pais")
    
    return {
        'tiene_tipo': 'tipo' in columnas,
        'tiene_script_update': 'script_update' in columnas
    }


def verificar_registro_maestro_existe(conn, id_variable, id_pais):
    """Verifica si ya existe un registro maestro para esta variable y país."""
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id_variable, id_pais 
        FROM maestro 
        WHERE id_variable = ? AND id_pais = ?
    """, (id_variable, id_pais))
    return cursor.fetchone() is not None


def crear_registros_maestro(conn, ids_variables):
    """Crea los registros en maestro para las variables creadas."""
    cursor = conn.cursor()
    
    # Verificar estructura
    print("\n[INFO] Verificando estructura de maestro...")
    estructura = verificar_estructura_maestro(conn)
    
    # Obtener ID de Uruguay
    print("\n[INFO] Obteniendo ID de Uruguay...")
    id_uruguay = obtener_id_uruguay(conn)
    print(f"[OK] ID de Uruguay: {id_uruguay}")
    
    # Verificar registros existentes
    print(f"\n[INFO] Verificando registros existentes en maestro...")
    registros_existentes = []
    for id_var in ids_variables:
        if verificar_registro_maestro_existe(conn, id_var, id_uruguay):
            registros_existentes.append(id_var)
    
    if registros_existentes:
        print(f"[WARN] Se encontraron {len(registros_existentes)} registros existentes en maestro")
        print("[INFO] Se omitirán y solo se crearán los faltantes")
    
    # Crear registros
    print(f"\n[INFO] Creando registros en maestro para {len(ids_variables)} variables...")
    registros_creados = 0
    registros_omitidos = 0
    
    for id_var in ids_variables:
        # Verificar si ya existe
        if verificar_registro_maestro_existe(conn, id_var, id_uruguay):
            print(f"[SKIP] Registro maestro para variable {id_var} ya existe, omitiendo...")
            registros_omitidos += 1
            continue
        
        # Obtener nombre de la variable
        cursor.execute("SELECT id_nombre_variable FROM variables WHERE id_variable = ?", (id_var,))
        resultado = cursor.fetchone()
        nombre_var = resultado[0] if resultado else f"Variable {id_var}"
        
        # Construir query de inserción
        if estructura['tiene_tipo']:
            if estructura['tiene_script_update']:
                cursor.execute("""
                    INSERT INTO maestro (id_variable, id_pais, fuente, periodicidad, activo, tipo, script_update)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (id_var, id_uruguay, FUENTE, PERIODICIDAD, ACTIVO, TIPO, None))
            else:
                cursor.execute("""
                    INSERT INTO maestro (id_variable, id_pais, fuente, periodicidad, activo, tipo)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (id_var, id_uruguay, FUENTE, PERIODICIDAD, ACTIVO, TIPO))
        else:
            if estructura['tiene_script_update']:
                cursor.execute("""
                    INSERT INTO maestro (id_variable, id_pais, fuente, periodicidad, activo, script_update)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (id_var, id_uruguay, FUENTE, PERIODICIDAD, ACTIVO, None))
            else:
                cursor.execute("""
                    INSERT INTO maestro (id_variable, id_pais, fuente, periodicidad, activo)
                    VALUES (?, ?, ?, ?, ?)
                """, (id_var, id_uruguay, FUENTE, PERIODICIDAD, ACTIVO))
        
        print(f"[OK] Registro maestro creado: Variable {id_var} ({nombre_var}) - Uruguay")
        registros_creados += 1
    
    # Confirmar cambios
    conn.commit()
    
    print(f"\n[RESUMEN MAESTRO]")
    print(f"  Registros creados: {registros_creados}")
    print(f"  Registros omitidos: {registros_omitidos}")
    print(f"  Total procesados: {len(ids_variables)}")
    
    if registros_creados > 0:
        print(f"\n[OK] {registros_creados} registros creados exitosamente en maestro")
    else:
        print(f"\n[INFO] No se crearon nuevos registros (todos ya existían)")


def main():
    """Función principal."""
    print("=" * 80)
    print("CREACIÓN DE VARIABLES REALES DE CURVA DE PESOS".center(80))
    print("=" * 80)
    print(f"Base de datos: {DB_NAME}")
    print(f"Familia: {ID_FAMILIA}")
    print(f"Sub-familia: {ID_SUB_FAMILIA}")
    print(f"Nominal/Real: {NOMINAL_O_REAL} (REAL)")
    print(f"Moneda: {MONEDA}")
    print(f"Total de variables a crear: {len(NOMBRES_VARIABLES)}")
    print(f"Plazos: {', '.join(NOMBRES_VARIABLES)}")
    print("=" * 80)
    
    # Verificar que existe la base de datos
    if not os.path.exists(DB_NAME):
        print(f"[ERROR] No se encontró la base de datos: {DB_NAME}")
        print(f"[INFO] Asegúrate de ejecutar este script desde la raíz del proyecto")
        return
    
    # Conectar a la base de datos
    conn = None
    try:
        conn = sqlite3.connect(DB_NAME)
        print(f"\n[OK] Conectado a la base de datos: {DB_NAME}")
        
        # 1. Crear variables
        ids_variables = crear_variables(conn)
        
        if not ids_variables:
            print("\n[WARN] No se crearon variables, no hay nada que procesar en maestro")
            return
        
        # 2. Crear registros maestro
        crear_registros_maestro(conn, ids_variables)
        
        print("\n" + "=" * 80)
        print("[SUCCESS] Proceso completado exitosamente".center(80))
        print("=" * 80)
        
    except Exception as e:
        if conn:
            conn.rollback()
        print(f"\n[ERROR] Error durante el proceso: {e}")
        import traceback
        traceback.print_exc()
        raise
    finally:
        if conn:
            conn.close()
            print("\n[OK] Conexión cerrada")


if __name__ == "__main__":
    main()
