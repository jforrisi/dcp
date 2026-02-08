"""
Script para crear las 15 variables de curva de pesos en la tabla variables
con familia=1 y sub_familia=10
"""

import sqlite3
import os

# Configuración
DB_NAME = "series_tiempo.db"
ID_FAMILIA = 1
ID_SUB_FAMILIA = 10
NOMINAL_O_REAL = "n"  # nominal
MONEDA = "LC"

# Nombres de las variables (en orden de la imagen)
NOMBRES_VARIABLES = [
    "1 mes",
    "2 meses",
    "3 meses",
    "6 meses",
    "9 meses",
    "1 año",
    "2 años",
    "3 años",
    "4 años",
    "5 años",
    "6 años",
    "7 años",
    "8 años",
    "9 años",
    "10 años"
]

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

def verificar_variables_existentes(conn):
    """Verifica si ya existen variables con esos nombres."""
    cursor = conn.cursor()
    variables_existentes = []
    
    for nombre in NOMBRES_VARIABLES:
        cursor.execute(
            "SELECT id_variable, id_nombre_variable FROM variables WHERE id_nombre_variable = ?",
            (nombre,)
        )
        existente = cursor.fetchone()
        if existente:
            variables_existentes.append((existente[0], existente[1]))
    
    return variables_existentes

def obtener_siguiente_id_variable(conn):
    """Obtiene el siguiente id_variable disponible."""
    cursor = conn.cursor()
    cursor.execute("SELECT MAX(id_variable) FROM variables")
    max_id = cursor.fetchone()[0]
    return (max_id or 0) + 1

def crear_variables(conn):
    """Crea las 15 variables en la tabla variables."""
    cursor = conn.cursor()
    
    # Verificar familia y sub_familia
    verificar_familia_y_sub_familia(conn)
    
    # Verificar variables existentes
    print(f"\n[INFO] Verificando variables existentes...")
    variables_existentes = verificar_variables_existentes(conn)
    if variables_existentes:
        print(f"[WARN] Se encontraron {len(variables_existentes)} variables existentes:")
        for id_var, nombre in variables_existentes:
            print(f"  - ID {id_var}: {nombre}")
        respuesta = input("\n¿Deseas continuar y crear solo las que no existen? (s/n): ")
        if respuesta.lower() != 's':
            print("[INFO] Operación cancelada")
            return
    else:
        print("[OK] No se encontraron variables duplicadas")
    
    # Obtener siguiente ID
    siguiente_id = obtener_siguiente_id_variable(conn)
    print(f"\n[INFO] Siguiente id_variable disponible: {siguiente_id}")
    
    # Crear variables
    print(f"\n[INFO] Creando {len(NOMBRES_VARIABLES)} variables...")
    variables_creadas = 0
    variables_omitidas = 0
    
    for i, nombre in enumerate(NOMBRES_VARIABLES):
        # Verificar si ya existe
        cursor.execute(
            "SELECT id_variable FROM variables WHERE id_nombre_variable = ?",
            (nombre,)
        )
        if cursor.fetchone():
            print(f"[SKIP] Variable '{nombre}' ya existe, omitiendo...")
            variables_omitidas += 1
            continue
        
        # Crear variable
        id_variable = siguiente_id + i - variables_omitidas
        try:
            cursor.execute("""
                INSERT INTO variables (id_variable, id_nombre_variable, id_sub_familia, nominal_o_real, moneda)
                VALUES (?, ?, ?, ?, ?)
            """, (id_variable, nombre, ID_SUB_FAMILIA, NOMINAL_O_REAL, MONEDA))
            print(f"[OK] Variable creada: ID {id_variable} - '{nombre}'")
            variables_creadas += 1
        except sqlite3.IntegrityError as e:
            print(f"[ERROR] Error al crear variable '{nombre}': {e}")
            variables_omitidas += 1
    
    # Confirmar cambios
    conn.commit()
    
    print(f"\n[RESUMEN]")
    print(f"  Variables creadas: {variables_creadas}")
    print(f"  Variables omitidas: {variables_omitidas}")
    print(f"  Total procesadas: {len(NOMBRES_VARIABLES)}")
    
    if variables_creadas > 0:
        print(f"\n[OK] {variables_creadas} variables creadas exitosamente")
    else:
        print(f"\n[INFO] No se crearon nuevas variables (todas ya existían)")

def main():
    """Función principal."""
    print("=" * 80)
    print("CREACIÓN DE VARIABLES DE CURVA DE PESOS")
    print("=" * 80)
    print(f"Base de datos: {DB_NAME}")
    print(f"Familia: {ID_FAMILIA}")
    print(f"Sub-familia: {ID_SUB_FAMILIA}")
    print(f"Nominal/Real: {NOMINAL_O_REAL}")
    print(f"Moneda: {MONEDA}")
    print(f"Total de variables a crear: {len(NOMBRES_VARIABLES)}")
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
        
        # Crear variables
        crear_variables(conn)
        
        conn.close()
        print(f"\n[OK] Conexión cerrada")
        
    except Exception as e:
        print(f"\n[ERROR] Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
