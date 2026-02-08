"""
Script para crear variables de Índices de Precios de Exportación (IPE)
y sus registros maestro para Uruguay
"""

import sqlite3
import os

# Configuración
DB_NAME = "series_tiempo.db"
NOMBRE_FAMILIA = "Precios y salarios"
NOMBRE_SUB_FAMILIA = "Índices de Precios de Exportación"
NOMINAL_O_REAL = "n"  # nominal
MONEDA = "LC"
ID_PAIS_URUGUAY = 858  # Uruguay

# Nombres de las variables IPE
NOMBRES_VARIABLES = [
    "Trigo - IPE",
    "Soja - IPE",
    "Frutas - IPE",
    "Ganado - IPE",
    "Madera - IPE",
    "Industria cárnica - IPE",
    "Industria léctea - IPE",
    "Industria arroz - IPE",
    "Industria bebida - IPE",
    "Industria textil - IPE",
    "Industria cueros - IPE",
    "Industria papel - IPE",
    "Industria química - IPE",
    "Industria farmacéutica - IPE",
    "Industria producto limpieza - IPE",
    "Industria automotriz - IPE"
]

def obtener_id_familia(conn, nombre_familia):
    """Obtiene el id_familia por nombre."""
    cursor = conn.cursor()
    cursor.execute("SELECT id_familia FROM familia WHERE nombre_familia = ?", (nombre_familia,))
    resultado = cursor.fetchone()
    if not resultado:
        raise ValueError(f"No se encontró la familia '{nombre_familia}'")
    return resultado[0]

def obtener_o_crear_sub_familia(conn, nombre_sub_familia, id_familia):
    """Obtiene o crea la sub-familia."""
    cursor = conn.cursor()
    
    # Buscar si existe
    cursor.execute("""
        SELECT id_sub_familia FROM sub_familia 
        WHERE nombre_sub_familia = ? AND id_familia = ?
    """, (nombre_sub_familia, id_familia))
    resultado = cursor.fetchone()
    
    if resultado:
        return resultado[0]
    
    # Crear si no existe
    cursor.execute("SELECT MAX(id_sub_familia) FROM sub_familia")
    max_id = cursor.fetchone()[0]
    nuevo_id = (max_id or 0) + 1
    
    cursor.execute("""
        INSERT INTO sub_familia (id_sub_familia, nombre_sub_familia, id_familia)
        VALUES (?, ?, ?)
    """, (nuevo_id, nombre_sub_familia, id_familia))
    
    conn.commit()
    print(f"[OK] Sub-familia creada: ID {nuevo_id} - '{nombre_sub_familia}'")
    return nuevo_id

def verificar_pais(conn, id_pais):
    """Verifica que el país existe."""
    cursor = conn.cursor()
    cursor.execute("SELECT id_pais, nombre_pais_grupo FROM pais_grupo WHERE id_pais = ?", (id_pais,))
    resultado = cursor.fetchone()
    if not resultado:
        raise ValueError(f"No se encontró el país con id_pais = {id_pais}")
    print(f"[OK] País encontrado: ID {resultado[0]} - {resultado[1]}")
    return True

def obtener_siguiente_id_variable(conn):
    """Obtiene el siguiente id_variable disponible."""
    cursor = conn.cursor()
    cursor.execute("SELECT MAX(id_variable) FROM variables")
    max_id = cursor.fetchone()[0]
    return (max_id or 0) + 1

def crear_variables(conn, id_sub_familia):
    """Crea las variables en la tabla variables."""
    cursor = conn.cursor()
    
    siguiente_id = obtener_siguiente_id_variable(conn)
    print(f"\n[INFO] Siguiente id_variable disponible: {siguiente_id}")
    
    print(f"\n[INFO] Creando {len(NOMBRES_VARIABLES)} variables...")
    variables_creadas = 0
    variables_omitidas = 0
    ids_variables = []
    
    for i, nombre in enumerate(NOMBRES_VARIABLES):
        # Verificar si ya existe
        cursor.execute(
            "SELECT id_variable FROM variables WHERE id_nombre_variable = ?",
            (nombre,)
        )
        existente = cursor.fetchone()
        if existente:
            print(f"[SKIP] Variable '{nombre}' ya existe (ID: {existente[0]}), omitiendo...")
            variables_omitidas += 1
            ids_variables.append(existente[0])
            continue
        
        # Crear variable
        id_variable = siguiente_id + i - variables_omitidas
        try:
            cursor.execute("""
                INSERT INTO variables (id_variable, id_nombre_variable, id_sub_familia, nominal_o_real, moneda)
                VALUES (?, ?, ?, ?, ?)
            """, (id_variable, nombre, id_sub_familia, NOMINAL_O_REAL, MONEDA))
            print(f"[OK] Variable creada: ID {id_variable} - '{nombre}'")
            variables_creadas += 1
            ids_variables.append(id_variable)
        except sqlite3.IntegrityError as e:
            print(f"[ERROR] Error al crear variable '{nombre}': {e}")
            variables_omitidas += 1
    
    conn.commit()
    
    print(f"\n[RESUMEN VARIABLES]")
    print(f"  Variables creadas: {variables_creadas}")
    print(f"  Variables omitidas: {variables_omitidas}")
    print(f"  Total IDs: {len(ids_variables)}")
    
    return ids_variables

def crear_registros_maestro(conn, ids_variables, id_pais):
    """Crea registros maestro para Uruguay."""
    cursor = conn.cursor()
    
    print(f"\n[INFO] Creando registros maestro para Uruguay (id_pais={id_pais})...")
    
    # Configuración por defecto para maestro
    periodicidad = "M"  # Mensual (puedes cambiarlo si es necesario)
    activo = 1
    
    registros_creados = 0
    registros_omitidos = 0
    
    for id_variable in ids_variables:
        # Verificar si ya existe
        cursor.execute("""
            SELECT id_variable, id_pais FROM maestro 
            WHERE id_variable = ? AND id_pais = ?
        """, (id_variable, id_pais))
        if cursor.fetchone():
            print(f"[SKIP] Registro maestro ya existe para variable {id_variable} y país {id_pais}")
            registros_omitidos += 1
            continue
        
        # Obtener nombre de la variable
        cursor.execute("SELECT id_nombre_variable FROM variables WHERE id_variable = ?", (id_variable,))
        nombre_var = cursor.fetchone()[0]
        
        # Crear registro maestro
        try:
            cursor.execute("""
                INSERT INTO maestro (id_variable, id_pais, periodicidad, activo)
                VALUES (?, ?, ?, ?)
            """, (id_variable, id_pais, periodicidad, activo))
            print(f"[OK] Registro maestro creado: variable '{nombre_var}' (ID: {id_variable}) para Uruguay")
            registros_creados += 1
        except sqlite3.IntegrityError as e:
            print(f"[ERROR] Error al crear registro maestro para variable {id_variable}: {e}")
            registros_omitidos += 1
    
    conn.commit()
    
    print(f"\n[RESUMEN MAESTRO]")
    print(f"  Registros creados: {registros_creados}")
    print(f"  Registros omitidos: {registros_omitidos}")
    print(f"  Total procesados: {len(ids_variables)}")

def main():
    """Función principal."""
    print("=" * 80)
    print("CREACIÓN DE VARIABLES IPE Y REGISTROS MAESTRO")
    print("=" * 80)
    print(f"Base de datos: {DB_NAME}")
    print(f"Familia: {NOMBRE_FAMILIA}")
    print(f"Sub-familia: {NOMBRE_SUB_FAMILIA}")
    print(f"Nominal/Real: {NOMINAL_O_REAL}")
    print(f"Moneda: {MONEDA}")
    print(f"País: Uruguay (id_pais={ID_PAIS_URUGUAY})")
    print(f"Total de variables: {len(NOMBRES_VARIABLES)}")
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
        
        # Obtener id_familia
        print(f"\n[INFO] Buscando familia '{NOMBRE_FAMILIA}'...")
        id_familia = obtener_id_familia(conn, NOMBRE_FAMILIA)
        print(f"[OK] Familia encontrada: ID {id_familia}")
        
        # Obtener o crear sub-familia
        print(f"\n[INFO] Buscando/creando sub-familia '{NOMBRE_SUB_FAMILIA}'...")
        id_sub_familia = obtener_o_crear_sub_familia(conn, NOMBRE_SUB_FAMILIA, id_familia)
        print(f"[OK] Sub-familia: ID {id_sub_familia}")
        
        # Verificar país
        print(f"\n[INFO] Verificando país Uruguay...")
        verificar_pais(conn, ID_PAIS_URUGUAY)
        
        # Crear variables
        ids_variables = crear_variables(conn, id_sub_familia)
        
        # Crear registros maestro
        crear_registros_maestro(conn, ids_variables, ID_PAIS_URUGUAY)
        
        conn.close()
        print(f"\n[OK] Proceso completado. Conexión cerrada.")
        
    except Exception as e:
        print(f"\n[ERROR] Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
