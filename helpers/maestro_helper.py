"""
Helper functions para migración de scripts a nueva estructura normalizada.
Proporciona funciones reutilizables para trabajar con las nuevas tablas de referencia.
"""

import sqlite3
import unicodedata

DB_NAME = "series_tiempo.db"


def normalizar_texto(texto):
    """
    Normaliza texto para comparación: lowercase, trim, elimina acentos.
    """
    if texto is None:
        return ""
    texto = str(texto).strip().lower()
    # Eliminar acentos
    texto = unicodedata.normalize('NFD', texto)
    texto = ''.join(c for c in texto if unicodedata.category(c) != 'Mn')
    return texto


def obtener_o_crear_variable(nombre_variable: str, id_sub_familia: int = None, 
                            nominal_o_real: str = None, moneda: str = None) -> int:
    """
    Busca variable por nombre en la tabla variables.
    Si no existe, la crea con los parámetros proporcionados.
    
    Args:
        nombre_variable: Nombre de la variable (debe coincidir con id_nombre_variable en variables)
        id_sub_familia: ID de sub_familia (opcional, solo si se crea nueva variable)
        nominal_o_real: 'n' o 'r' (opcional, solo si se crea nueva variable)
        moneda: Código de moneda (opcional, solo si se crea nueva variable)
    
    Returns:
        id_variable (int) - ID de la variable encontrada o creada
    
    Raises:
        ValueError: Si la variable no existe y no se proporcionan datos para crearla
    """
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    try:
        # Buscar variable por nombre (normalizado)
        nombre_norm = normalizar_texto(nombre_variable)
        cursor.execute("""
            SELECT id_variable, id_nombre_variable 
            FROM variables
        """)
        variables = cursor.fetchall()
        
        for id_var, nombre_var in variables:
            if normalizar_texto(nombre_var) == nombre_norm:
                return id_var
        
        # Si no existe, crear nueva variable
        if id_sub_familia is None or nominal_o_real is None or moneda is None:
            raise ValueError(
                f"Variable '{nombre_variable}' no encontrada. "
                "Se requieren id_sub_familia, nominal_o_real y moneda para crearla."
            )
        
        # Obtener próximo ID disponible
        cursor.execute("SELECT MAX(id_variable) FROM variables")
        max_id = cursor.fetchone()[0]
        nuevo_id = (max_id or 0) + 1
        
        cursor.execute("""
            INSERT INTO variables (id_variable, id_nombre_variable, id_sub_familia, nominal_o_real, moneda)
            VALUES (?, ?, ?, ?, ?)
        """, (nuevo_id, nombre_variable, id_sub_familia, nominal_o_real, moneda))
        
        conn.commit()
        return nuevo_id
        
    finally:
        conn.close()


def obtener_o_crear_pais_grupo(nombre_pais: str) -> int:
    """
    Busca país por nombre en la tabla pais_grupo.
    Si no existe, lo crea.
    
    Args:
        nombre_pais: Nombre del país/región
    
    Returns:
        id_pais (int) - ID del país encontrado o creado
    """
    if not nombre_pais or nombre_pais.strip() == "":
        return None
    
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    try:
        # Buscar país por nombre (normalizado)
        nombre_norm = normalizar_texto(nombre_pais)
        cursor.execute("""
            SELECT id_pais, nombre_pais_grupo 
            FROM pais_grupo
        """)
        paises = cursor.fetchall()
        
        for id_pais, nombre_pais_db in paises:
            if normalizar_texto(nombre_pais_db) == nombre_norm:
                return id_pais
        
        # Si no existe, crear nuevo país
        cursor.execute("SELECT MAX(id_pais) FROM pais_grupo")
        max_id = cursor.fetchone()[0]
        nuevo_id = (max_id or 0) + 1
        
        cursor.execute("""
            INSERT INTO pais_grupo (id_pais, nombre_pais_grupo)
            VALUES (?, ?)
        """, (nuevo_id, nombre_pais.strip()))
        
        conn.commit()
        return nuevo_id
        
    finally:
        conn.close()


def obtener_fks_desde_maestro(maestro_id: int) -> tuple:
    """
    Obtiene id_variable e id_pais desde maestro.id.
    
    Args:
        maestro_id: ID del registro en maestro
    
    Returns:
        (id_variable, id_pais) o (None, None) si no existen
    """
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    try:
        cursor.execute("SELECT id_variable, id_pais FROM maestro WHERE id = ?", (maestro_id,))
        row = cursor.fetchone()
        if row:
            return (row[0], row[1])
        return (None, None)
    finally:
        conn.close()


def insertar_maestro_con_fks(maestro_id: int, nombre: str, tipo: str, 
                              fuente: str, periodicidad: str, unidad: str = None,
                              categoria: str = None, activo: int = 1,
                              id_variable: int = None,
                              id_pais: int = None,
                              link: str = None,
                              moneda: str = None,
                              nominal_real: str = None,
                              es_cotizacion: int = 0,
                              mercado: str = None) -> bool:
    """
    Inserta o actualiza registro en maestro con FKs si están disponibles.
    Si FKs son None, inserta sin ellas (compatibilidad hacia atrás).
    
    Args:
        maestro_id: ID del registro en maestro
        nombre: Nombre de la serie
        tipo: 'P', 'S', o 'M'
        fuente: Fuente de datos
        periodicidad: 'D', 'W', o 'M'
        unidad: Unidad de medida (opcional)
        categoria: Categoría (opcional)
        activo: 1 o 0 (default: 1)
        id_variable: FK a variables.id_variable (opcional)
        id_pais: FK a pais_grupo.id_pais (opcional)
        link: URL opcional
        moneda: Moneda (opcional, para compatibilidad)
        nominal_real: 'n' o 'r' (opcional, para compatibilidad)
        es_cotizacion: 1 o 0 (opcional, default: 0)
        mercado: Mercado (opcional)
    
    Returns:
        True si fue exitoso, False en caso contrario
    """
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    try:
        # Verificar qué columnas existen en maestro
        cursor.execute("PRAGMA table_info(maestro)")
        columnas = [col[1] for col in cursor.fetchall()]
        
        # Construir query dinámicamente según columnas disponibles
        campos = ['id', 'nombre', 'tipo', 'fuente', 'periodicidad', 'activo']
        valores = [maestro_id, nombre, tipo, fuente, periodicidad, activo]
        
        if unidad is not None and 'unidad' in columnas:
            campos.append('unidad')
            valores.append(unidad)
        
        if categoria is not None and 'categoria' in columnas:
            campos.append('categoria')
            valores.append(categoria)
        
        # Usar id_variable (nuevo nombre) en lugar de id_nombre_variable
        if id_variable is not None:
            # Verificar si existe id_variable o id_nombre_variable
            if 'id_variable' in columnas:
                campos.append('id_variable')
                valores.append(id_variable)
            elif 'id_nombre_variable' in columnas:
                campos.append('id_nombre_variable')
                valores.append(id_variable)
        
        if id_pais is not None and 'id_pais' in columnas:
            campos.append('id_pais')
            valores.append(id_pais)
        
        if link is not None and 'link' in columnas:
            campos.append('link')
            valores.append(link)
        
        if moneda is not None and 'moneda' in columnas:
            campos.append('moneda')
            valores.append(moneda)
        
        if nominal_real is not None and 'nominal_real' in columnas:
            campos.append('nominal_real')
            valores.append(nominal_real)
        
        if 'es_cotizacion' in columnas:
            campos.append('es_cotizacion')
            valores.append(es_cotizacion)
        
        if mercado is not None and 'mercado' in columnas:
            campos.append('mercado')
            valores.append(mercado)
        
        # Construir query INSERT OR REPLACE
        campos_str = ', '.join(campos)
        placeholders = ', '.join(['?'] * len(campos))
        
        query = f"""
            INSERT OR REPLACE INTO maestro ({campos_str})
            VALUES ({placeholders})
        """
        
        cursor.execute(query, tuple(valores))
        conn.commit()
        return True
        
    except Exception as e:
        conn.rollback()
        print(f"[ERROR] Error al insertar en maestro: {e}")
        return False
    finally:
        conn.close()
