"""
Script de migración de tabla maestro desde Excel.
Lee maestro_completo.xlsx, mapea columnas y actualiza la base de datos.
"""

import pandas as pd
import sqlite3
from datetime import datetime

DB_NAME = "series_tiempo.db"
EXCEL_PATH = "maestro_completo.xlsx"


def mapear_grupo_a_categoria(grupo):
    """
    Mapea el campo 'grupo' del Excel a la categoría funcional en BD.
    
    Args:
        grupo: Valor del campo 'grupo' del Excel
        
    Returns:
        Categoría funcional (str)
    """
    if pd.isna(grupo):
        return None
    
    grupo_str = str(grupo).strip()
    
    # Mapeo de grupos a categorías
    if "Precio Internacional" in grupo_str or "Precios Internacionales" in grupo_str:
        return "Precios Internacionales"
    elif "Tipo de cambio" in grupo_str:
        return "Macro - Tipo de cambio"
    elif "IPC" in grupo_str:
        return "Macro - IPC"
    elif "Local Uruguay" in grupo_str or "Expor Uruguay" in grupo_str:
        return "Precios Transables"
    elif "Precios" in grupo_str:
        return "Precios"
    else:
        # Si no hay match, usar el grupo original o None
        return grupo_str if grupo_str else None


def limpiar_pais(pais_region):
    """
    Limpia el valor de pais-region del Excel.
    
    Args:
        pais_region: Valor del campo 'pais-region' del Excel
        
    Returns:
        País limpio (str) o None
    """
    if pd.isna(pais_region):
        return None
    
    pais_str = str(pais_region).strip()
    
    # Limpiar valores comunes
    if pais_str in ["Precios transables", "Precios Transables"]:
        return "Uruguay"  # Asumir Uruguay para precios transables
    
    return pais_str if pais_str else None


def validar_datos(df):
    """
    Valida los datos del DataFrame antes de migrar.
    
    Args:
        df: DataFrame con datos del Excel
        
    Returns:
        Tuple (es_valido, errores)
    """
    errores = []
    
    # Validar IDs únicos
    if df['id'].duplicated().any():
        ids_duplicados = df[df['id'].duplicated()]['id'].tolist()
        errores.append(f"IDs duplicados encontrados: {ids_duplicados}")
    
    # Validar valores de tipo (desde categoría del Excel)
    if 'categoría' in df.columns:
        valores_tipo = df['categoría'].dropna().unique()
        valores_validos = ['P', 'S', 'M']
        valores_invalidos = [v for v in valores_tipo if v not in valores_validos]
        if valores_invalidos:
            errores.append(f"Valores de tipo inválidos: {valores_invalidos}")
    
    # Validar periodicidad
    if 'periodicidad' in df.columns:
        valores_periodicidad = df['periodicidad'].dropna().unique()
        valores_validos = ['D', 'W', 'M']
        valores_invalidos = [v for v in valores_periodicidad if v not in valores_validos]
        if valores_invalidos:
            errores.append(f"Valores de periodicidad inválidos: {valores_invalidos}")
    
    return len(errores) == 0, errores


def leer_y_mapear_excel():
    """
    Lee el Excel y mapea las columnas al formato de BD.
    
    Returns:
        DataFrame mapeado
    """
    print(f"[INFO] Leyendo Excel: {EXCEL_PATH}")
    df = pd.read_excel(EXCEL_PATH)
    
    print(f"[INFO] Registros en Excel: {len(df)}")
    print(f"[INFO] Columnas encontradas: {list(df.columns)}")
    
    # Crear DataFrame mapeado
    df_mapeado = pd.DataFrame()
    
    # Mapear columnas directas
    if 'id' in df.columns:
        df_mapeado['id'] = df['id']
    if 'nombre' in df.columns:
        df_mapeado['nombre'] = df['nombre']
    if 'fuente' in df.columns:
        df_mapeado['fuente'] = df['fuente']
    if 'periodicidad' in df.columns:
        df_mapeado['periodicidad'] = df['periodicidad']
    if 'unidad' in df.columns:
        df_mapeado['unidad'] = df['unidad']
    if 'activo' in df.columns:
        df_mapeado['activo'] = df['activo']
    if 'moneda' in df.columns:
        df_mapeado['moneda'] = df['moneda']
    if 'nominal_real' in df.columns:
        df_mapeado['nominal_real'] = df['nominal_real']
    
    # Mapear pais-region -> pais
    if 'pais-region' in df.columns:
        df_mapeado['pais'] = df['pais-region'].apply(limpiar_pais)
    elif 'pais/region' in df.columns:
        df_mapeado['pais'] = df['pais/region'].apply(limpiar_pais)
    else:
        print("[WARN] No se encontró columna 'pais-region' o 'pais/region'")
        df_mapeado['pais'] = None
    
    # Mapear categoría (con tilde) -> tipo (BD) - contiene P/S/M
    if 'categoría' in df.columns:
        df_mapeado['tipo'] = df['categoría']
    else:
        print("[WARN] No se encontró columna 'categoría'")
        df_mapeado['tipo'] = None
    
    # Mapear grupo -> categoria (BD) - valores temáticos como "Precios Internacionales"
    # Si grupo contiene "Precio Internacional", usar "Precios Internacionales"
    # Si grupo contiene "Tipo de cambio", usar "Macro - Tipo de cambio"
    # Si grupo contiene "IPC", usar "Macro - IPC"
    # Para otros casos, si hay categoría (P/S), mantenerla, sino usar el grupo mapeado
    if 'grupo' in df.columns:
        def determinar_categoria(row):
            grupo_val = row.get('grupo') if 'grupo' in df.columns else None
            cat_val = row.get('categoría') if 'categoría' in df.columns else None
            
            if pd.notna(grupo_val):
                grupo_str = str(grupo_val).strip()
                if "Precio Internacional" in grupo_str:
                    return "Precios Internacionales"
                elif "Tipo de cambio" in grupo_str:
                    return "Macro - Tipo de cambio"
                elif "IPC" in grupo_str:
                    return "Macro - IPC"
                elif "Local Uruguay" in grupo_str or "Expor Uruguay" in grupo_str:
                    # Para estos, mantener el valor funcional P/S si existe
                    return cat_val if pd.notna(cat_val) else "Precios Transables"
                elif "Precios" in grupo_str:
                    return cat_val if pd.notna(cat_val) else "Precios"
            
            # Si no hay grupo, usar categoría funcional (P/S/M)
            return cat_val if pd.notna(cat_val) else None
        
        df_mapeado['categoria'] = df.apply(determinar_categoria, axis=1)
    else:
        print("[WARN] No se encontró columna 'grupo'")
        # Si no hay grupo, usar categoría como categoria
        if 'categoría' in df.columns:
            df_mapeado['categoria'] = df['categoría']
        else:
            df_mapeado['categoria'] = None
    
    # Mantener es_cotizacion si existe (para compatibilidad)
    if 'es_cotizacion' in df.columns:
        df_mapeado['es_cotizacion'] = df['es_cotizacion']
    else:
        df_mapeado['es_cotizacion'] = 0
    
    return df_mapeado


def actualizar_esquema_bd(conn):
    """
    Actualiza el esquema de la BD agregando columnas si no existen.
    
    Args:
        conn: Conexión a la BD
    """
    cursor = conn.cursor()
    
    # Verificar columnas existentes
    cursor.execute("PRAGMA table_info(maestro)")
    columnas_existentes = [col[1] for col in cursor.fetchall()]
    
    print("\n[INFO] Verificando esquema de BD...")
    
    # Agregar columna pais si no existe
    if 'pais' not in columnas_existentes:
        try:
            cursor.execute("ALTER TABLE maestro ADD COLUMN pais VARCHAR(100)")
            print("[OK] Columna 'pais' agregada")
        except sqlite3.OperationalError as e:
            print(f"[WARN] Error al agregar columna 'pais': {e}")
    else:
        print("[INFO] Columna 'pais' ya existe")
    
    # Verificar otras columnas críticas
    columnas_requeridas = ['tipo', 'categoria', 'moneda', 'nominal_real', 'activo']
    for col in columnas_requeridas:
        if col not in columnas_existentes:
            print(f"[WARN] Columna '{col}' no existe en BD")
        else:
            print(f"[OK] Columna '{col}' existe")
    
    conn.commit()


def migrar_datos(df_mapeado):
    """
    Migra los datos del DataFrame a la base de datos.
    
    Args:
        df_mapeado: DataFrame con datos mapeados
    """
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    try:
        # Actualizar esquema primero
        actualizar_esquema_bd(conn)
        
        print("\n[INFO] Iniciando migración de datos...")
        
        registros_actualizados = 0
        registros_nuevos = 0
        
        for idx, row in df_mapeado.iterrows():
            # Preparar valores (manejar NaN como None)
            valores = {
                'id': int(row['id']) if pd.notna(row['id']) else None,
                'nombre': str(row['nombre']) if pd.notna(row['nombre']) else None,
                'tipo': str(row['tipo']) if pd.notna(row['tipo']) else None,
                'fuente': str(row['fuente']) if pd.notna(row['fuente']) else None,
                'periodicidad': str(row['periodicidad']) if pd.notna(row['periodicidad']) else None,
                'unidad': str(row['unidad']) if pd.notna(row['unidad']) else None,
                'categoria': str(row['categoria']) if pd.notna(row['categoria']) else None,
                'pais': str(row['pais']) if pd.notna(row['pais']) else None,
                'activo': int(row['activo']) if pd.notna(row['activo']) else 1,
                'moneda': str(row['moneda']).lower() if pd.notna(row['moneda']) else None,
                'nominal_real': str(row['nominal_real']).lower() if pd.notna(row['nominal_real']) else None,
                'es_cotizacion': int(row['es_cotizacion']) if pd.notna(row['es_cotizacion']) else 0,
            }
            
            # Verificar si el registro ya existe
            cursor.execute("SELECT id FROM maestro WHERE id = ?", (valores['id'],))
            existe = cursor.fetchone() is not None
            
            if existe:
                # UPDATE
                cursor.execute("""
                    UPDATE maestro SET
                        nombre = ?,
                        tipo = ?,
                        fuente = ?,
                        periodicidad = ?,
                        unidad = ?,
                        categoria = ?,
                        pais = ?,
                        activo = ?,
                        moneda = ?,
                        nominal_real = ?,
                        es_cotizacion = ?
                    WHERE id = ?
                """, (
                    valores['nombre'],
                    valores['tipo'],
                    valores['fuente'],
                    valores['periodicidad'],
                    valores['unidad'],
                    valores['categoria'],
                    valores['pais'],
                    valores['activo'],
                    valores['moneda'],
                    valores['nominal_real'],
                    valores['es_cotizacion'],
                    valores['id']
                ))
                registros_actualizados += 1
            else:
                # INSERT
                cursor.execute("""
                    INSERT INTO maestro (
                        id, nombre, tipo, fuente, periodicidad, unidad,
                        categoria, pais, activo, moneda, nominal_real, es_cotizacion
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    valores['id'],
                    valores['nombre'],
                    valores['tipo'],
                    valores['fuente'],
                    valores['periodicidad'],
                    valores['unidad'],
                    valores['categoria'],
                    valores['pais'],
                    valores['activo'],
                    valores['moneda'],
                    valores['nominal_real'],
                    valores['es_cotizacion']
                ))
                registros_nuevos += 1
        
        conn.commit()
        
        print(f"\n[OK] Migración completada:")
        print(f"   - Registros actualizados: {registros_actualizados}")
        print(f"   - Registros nuevos: {registros_nuevos}")
        print(f"   - Total procesados: {len(df_mapeado)}")
        
    except Exception as e:
        conn.rollback()
        print(f"\n[ERROR] Error durante la migración: {e}")
        raise
    finally:
        conn.close()


def generar_reporte(df_mapeado):
    """
    Genera un reporte de los datos mapeados.
    
    Args:
        df_mapeado: DataFrame con datos mapeados
    """
    print("\n" + "=" * 80)
    print("REPORTE DE MIGRACIÓN")
    print("=" * 80)
    
    print(f"\nTotal de registros: {len(df_mapeado)}")
    
    print("\nDistribución por tipo:")
    if 'tipo' in df_mapeado.columns:
        print(df_mapeado['tipo'].value_counts().to_string())
    
    print("\nDistribución por categoría:")
    if 'categoria' in df_mapeado.columns:
        print(df_mapeado['categoria'].value_counts().to_string())
    
    print("\nDistribución por país:")
    if 'pais' in df_mapeado.columns:
        print(df_mapeado['pais'].value_counts().to_string())
    
    print("\nPrimeros 10 registros mapeados:")
    print(df_mapeado.head(10).to_string())


def main():
    """Función principal."""
    print("=" * 80)
    print("MIGRACIÓN DE TABLA MAESTRO DESDE EXCEL")
    print("=" * 80)
    
    # Leer y mapear Excel
    df_mapeado = leer_y_mapear_excel()
    
    # Validar datos
    print("\n[INFO] Validando datos...")
    es_valido, errores = validar_datos(df_mapeado)
    
    if not es_valido:
        print("\n[ERROR] Errores de validación encontrados:")
        for error in errores:
            print(f"   - {error}")
        print("\n[ERROR] Migración cancelada. Corrija los errores en el Excel.")
        return
    
    print("[OK] Validación exitosa")
    
    # Generar reporte
    generar_reporte(df_mapeado)
    
    # Confirmar con usuario (modo automático si no hay input disponible)
    print("\n" + "=" * 80)
    try:
        respuesta = input("¿Desea proceder con la migración? (s/n): ").strip().lower()
        if respuesta != 's':
            print("[INFO] Migración cancelada por el usuario")
            return
    except (EOFError, KeyboardInterrupt):
        # Modo no interactivo: proceder automáticamente
        print("[INFO] Modo no interactivo detectado. Procediendo automáticamente...")
    
    # Migrar datos
    migrar_datos(df_mapeado)
    
    print("\n" + "=" * 80)
    print("MIGRACIÓN COMPLETADA")
    print("=" * 80)


if __name__ == "__main__":
    main()
