"""
Funciones helper compartidas para scripts de actualización de precios.
Usa PostgreSQL vía DATABASE_URL.
"""
import sys
from pathlib import Path

# Permitir importar db desde la raíz del proyecto (update/direct/ -> update/ -> raíz)
_project_root = Path(__file__).resolve().parent.parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

import pandas as pd

from db.connection import execute_query, execute_query_single, execute_update, insert_dataframe


def insertar_en_bd_helper(
    db_name: str,
    id_variable: int,
    id_pais: int,
    df_precios: pd.DataFrame,
    preparar_datos_func=None
) -> None:
    """
    Inserta datos en maestro_precios (PostgreSQL vía DATABASE_URL).
    db_name se ignora (mantenido por compatibilidad).
    """
    print("\n[INFO] Insertando datos en la base de datos...")
    print(f"[INFO] Usando id_variable={id_variable}, id_pais={id_pais}")

    try:
        # Verificar que id_variable e id_pais existen en sus tablas de referencia
        row = execute_query_single("SELECT id_variable FROM variables WHERE id_variable = ?", (id_variable,))
        if not row:
            print(f"[ERROR] id_variable={id_variable} no existe en la tabla 'variables'.")
            print(f"[ERROR] Debes agregar este registro al Excel 'maestro_database.xlsx' y ejecutar la migración.")
            return

        row = execute_query_single("SELECT id_pais FROM pais_grupo WHERE id_pais = ?", (id_pais,))
        if not row:
            print(f"[ERROR] id_pais={id_pais} no existe en la tabla 'pais_grupo'.")
            print(f"[ERROR] Debes agregar este registro al Excel 'maestro_database.xlsx' y ejecutar la migración.")
            return

        # Verificar que el registro existe en maestro
        row = execute_query_single(
            "SELECT id_variable, id_pais FROM maestro WHERE id_variable = ? AND id_pais = ?",
            (id_variable, id_pais)
        )
        if not row:
            print(f"[ERROR] No existe registro en 'maestro' para id_variable={id_variable}, id_pais={id_pais}.")
            print(f"[ERROR] Debes agregar este registro al Excel 'maestro_database.xlsx' y ejecutar la migración.")
            return

        # Preparar datos con FKs si no están ya preparados
        if preparar_datos_func:
            df_precios = preparar_datos_func(df_precios, id_variable, id_pais)
        elif "id_variable" not in df_precios.columns or "id_pais" not in df_precios.columns:
            df_precios = df_precios.copy()
            df_precios["id_variable"] = id_variable
            df_precios["id_pais"] = id_pais
            if "FECHA" in df_precios.columns:
                df_precios = df_precios.rename(columns={"FECHA": "fecha", "VALOR": "valor"})
            df_precios = df_precios[["id_variable", "id_pais", "fecha", "valor"]]
            df_precios["valor"] = pd.to_numeric(df_precios["valor"], errors="coerce")
            df_precios = df_precios.dropna(subset=["valor"])

        # Contar registros a eliminar
        count_rows = execute_query(
            "SELECT COUNT(*) as cnt FROM maestro_precios WHERE id_variable = ? AND id_pais = ?",
            (id_variable, id_pais)
        )
        registros_eliminados = count_rows[0]["cnt"] if count_rows else 0

        # Eliminar registros existentes
        success, error, _ = execute_update(
            "DELETE FROM maestro_precios WHERE id_variable = ? AND id_pais = ?",
            (id_variable, id_pais)
        )
        if not success:
            raise RuntimeError(error or "Error al eliminar registros antiguos")
        if registros_eliminados > 0:
            print(f"[INFO] Se eliminaron {registros_eliminados} registros antiguos de 'maestro_precios' para id_variable={id_variable}, id_pais={id_pais}")

        # Insertar todos los precios nuevos
        if not df_precios.empty:
            print(f"[INFO] Insertando {len(df_precios)} registros en 'maestro_precios'...")
            insert_dataframe("maestro_precios", df_precios, if_exists="append", index=False)
            print(f"[OK] Insertados {len(df_precios)} registro(s) en tabla 'maestro_precios'")
        else:
            print(f"[WARN] No hay datos para insertar en maestro_precios")

        print(f"\n[OK] Datos insertados exitosamente")
    except Exception as exc:
        print(f"[ERROR] Error al insertar datos: {exc}")
        raise


def combinar_anio_mes_a_fecha(
    df: pd.DataFrame,
    col_anio: str = "AÑO",
    col_mes: str = "MES"
) -> pd.DataFrame:
    """
    Combina las columnas AÑO y MES para crear una fecha (primer día del mes).
    MES puede ser numérico (1-12) o texto (enero, febrero, etc.).
    
    Args:
        df: DataFrame con columnas AÑO y MES
        col_anio: Nombre de la columna de año (default: "AÑO")
        col_mes: Nombre de la columna de mes (default: "MES")
    
    Returns:
        DataFrame con columna FECHA agregada
    """
    print("\n[INFO] Combinando año y mes para crear fechas...")
    
    fechas = []
    fechas_invalidas = []
    
    for idx, row in df.iterrows():
        año = row[col_anio]
        mes = row[col_mes]
        
        try:
            # Convertir año a entero
            año_int = int(float(año))
            
            # Convertir mes a número
            mes_int = None
            
            # Si mes es numérico
            if pd.notna(mes):
                try:
                    mes_int = int(float(mes))
                    if mes_int < 1 or mes_int > 12:
                        fechas_invalidas.append((idx, año, mes, "Mes fuera de rango (1-12)"))
                        continue
                except (ValueError, TypeError):
                    # Si no es numérico, intentar interpretar como texto
                    mes_str = str(mes).strip().lower()
                    meses_texto = {
                        "enero": 1, "febrero": 2, "marzo": 3, "abril": 4,
                        "mayo": 5, "junio": 6, "julio": 7, "agosto": 8,
                        "septiembre": 9, "octubre": 10, "noviembre": 11, "diciembre": 12
                    }
                    mes_int = meses_texto.get(mes_str)
                    if mes_int is None:
                        fechas_invalidas.append((idx, año, mes, "Mes no reconocido"))
                        continue
            
            # Validar rango de año
            if not (1900 <= año_int <= 2100):
                fechas_invalidas.append((idx, año, mes, "Año fuera de rango"))
                continue
            
            # Crear fecha (primer día del mes)
            fecha = pd.Timestamp(year=año_int, month=mes_int, day=1)
            fechas.append(fecha)
            
        except Exception as exc:
            fechas_invalidas.append((idx, año, mes, str(exc)))
    
    if fechas_invalidas:
        print(f"[ERROR] Se encontraron {len(fechas_invalidas)} fechas inválidas:")
        for idx, año, mes, motivo in fechas_invalidas[:10]:
            print(f"   Fila {idx}: Año={año}, Mes={mes} - {motivo}")
        if len(fechas_invalidas) > 10:
            print(f"   ... y {len(fechas_invalidas) - 10} más")
        raise ValueError("Hay fechas inválidas. No se puede continuar.")
    
    df = df.copy()
    df["FECHA"] = fechas
    print(f"[OK] {len(fechas)} fechas creadas correctamente")
    return df


def validar_fechas_unificado(
    df: pd.DataFrame,
    columna_fecha: str = "FECHA",
    dayfirst: bool = False
) -> pd.DataFrame:
    """
    Valida que todas las fechas sean válidas.
    
    Args:
        df: DataFrame con columna de fechas
        columna_fecha: Nombre de la columna de fecha (default: "FECHA")
        dayfirst: Si True, interpreta fechas como día/mes/año (default: False)
    
    Returns:
        DataFrame con fechas validadas y parseadas
    """
    print("\n[INFO] Validando fechas...")
    
    fechas_invalidas = []
    fechas_validas = []
    
    for idx, fecha in enumerate(df[columna_fecha]):
        try:
            if pd.isna(fecha):
                fechas_invalidas.append((idx, fecha, "Fecha nula"))
            else:
                fecha_parseada = pd.to_datetime(fecha, errors="coerce", dayfirst=dayfirst)
                if pd.isna(fecha_parseada):
                    fechas_invalidas.append((idx, fecha, "No se pudo parsear"))
                else:
                    fechas_validas.append(fecha_parseada)
        except Exception as exc:
            fechas_invalidas.append((idx, fecha, str(exc)))
    
    if fechas_invalidas:
        print(f"[ERROR] Se encontraron {len(fechas_invalidas)} fechas inválidas:")
        for idx, fecha, motivo in fechas_invalidas[:10]:
            print(f"   Fila {idx}: {fecha} - {motivo}")
        if len(fechas_invalidas) > 10:
            print(f"   ... y {len(fechas_invalidas) - 10} más")
        raise ValueError("Hay fechas inválidas. No se puede continuar.")
    
    df = df.copy()
    df[columna_fecha] = pd.to_datetime(df[columna_fecha], dayfirst=dayfirst)
    print(f"[OK] Todas las {len(fechas_validas)} fechas son válidas")
    print(f"   Rango: {df[columna_fecha].min()} a {df[columna_fecha].max()}")
    return df


def completar_dias_faltantes(
    df: pd.DataFrame,
    columna_fecha: str = 'FECHA',
    columna_valor: str = 'VALOR',
    solo_lunes_a_viernes: bool = False
) -> pd.DataFrame:
    """
    Completa días faltantes en una serie diaria usando forward fill.
    Si solo_lunes_a_viernes=True: después de completar, elimina sábados y domingos.
    """
    print("\n[INFO] Completando días faltantes en serie diaria...")
    df = df.copy()
    df[columna_fecha] = pd.to_datetime(df[columna_fecha])
    df = df.sort_values(columna_fecha).reset_index(drop=True)

    fecha_min = df[columna_fecha].min()
    fecha_max = df[columna_fecha].max()
    rango_completo = pd.date_range(start=fecha_min, end=fecha_max, freq='D')
    df_completo = pd.DataFrame({columna_fecha: rango_completo})
    df_completo = df_completo.merge(
        df[[columna_fecha, columna_valor]], on=columna_fecha, how='left'
    )
    df_completo[columna_valor] = df_completo[columna_valor].ffill()

    dias_originales = len(df)
    dias_completados = len(df_completo)
    dias_agregados = dias_completados - dias_originales
    if dias_agregados > 0:
        print(f"[INFO] Se completaron {dias_agregados} días faltantes (de {dias_originales} a {dias_completados})")
    else:
        print(f"[OK] No había días faltantes ({dias_originales} días)")

    if solo_lunes_a_viernes:
        df_completo = filtrar_solo_lunes_a_viernes(df_completo, columna_fecha)
    return df_completo


def filtrar_solo_lunes_a_viernes(
    df: pd.DataFrame,
    columna_fecha: str = 'FECHA'
) -> pd.DataFrame:
    """
    Conserva solo fechas de lunes a viernes (elimina sábados y domingos).
    """
    df = df.copy()
    df[columna_fecha] = pd.to_datetime(df[columna_fecha])
    antes = len(df)
    df = df[df[columna_fecha].dt.weekday < 5]  # 0=Mon ... 4=Fri, 5=Sat, 6=Sun
    eliminados = antes - len(df)
    if eliminados > 0:
        print(f"[INFO] Eliminados {eliminados} fines de semana (solo lunes a viernes: {len(df)} días)")
    return df.reset_index(drop=True)


def validar_fechas_solo_nulas(
    df: pd.DataFrame,
    columna_fecha: str = "FECHA"
) -> pd.DataFrame:
    """
    Valida que no haya fechas nulas (para fechas ya parseadas).
    
    Args:
        df: DataFrame con columna de fechas ya parseadas
        columna_fecha: Nombre de la columna de fecha (default: "FECHA")
    
    Returns:
        DataFrame validado
    """
    print("\n[INFO] Validando fechas...")
    
    fechas_nulas = df[columna_fecha].isna().sum()
    
    if fechas_nulas > 0:
        print(f"[ERROR] Se encontraron {fechas_nulas} fechas nulas")
        raise ValueError("Hay fechas nulas. No se puede continuar.")
    
    print(f"[OK] Todas las {len(df)} fechas son válidas")
    print(f"   Rango: {df[columna_fecha].min()} a {df[columna_fecha].max()}")
    return df


def preparar_datos_maestro_precios_unificado(
    df: pd.DataFrame,
    id_variable: int,
    id_pais: int,
    col_fecha: str = "FECHA",
    col_valor: str = "VALOR"
) -> pd.DataFrame:
    """
    Prepara el DataFrame para maestro_precios.
    
    Args:
        df: DataFrame con columnas de fecha y valor
        id_variable: ID de la variable (FK a tabla variables)
        id_pais: ID del país (FK a tabla pais_grupo)
        col_fecha: Nombre de la columna de fecha (default: "FECHA")
        col_valor: Nombre de la columna de valor (default: "VALOR")
    
    Returns:
        DataFrame con columnas: id_variable, id_pais, fecha, valor
    """
    df_precios = df.copy()
    df_precios["id_variable"] = id_variable
    df_precios["id_pais"] = id_pais
    
    # Renombrar columnas si es necesario
    if col_fecha != "fecha":
        df_precios = df_precios.rename(columns={col_fecha: "fecha"})
    if col_valor != "valor":
        df_precios = df_precios.rename(columns={col_valor: "valor"})
    
    # Seleccionar solo las columnas necesarias
    df_precios = df_precios[["id_variable", "id_pais", "fecha", "valor"]]
    
    # Asegurar que valor sea numérico
    df_precios["valor"] = pd.to_numeric(df_precios["valor"], errors="coerce")
    
    # Eliminar filas con valor nulo
    df_precios = df_precios.dropna(subset=["valor"])
    return df_precios


def insertar_en_bd_unificado(
    id_variable: int,
    id_pais: int,
    df_precios: pd.DataFrame,
    db_name: str = None
) -> None:
    """
    Inserta los datos en maestro_precios (PostgreSQL vía DATABASE_URL).
    db_name se ignora; mantenido por compatibilidad.
    """
    insertar_en_bd_helper(
        db_name=db_name or "",
        id_variable=id_variable,
        id_pais=id_pais,
        df_precios=df_precios,
        preparar_datos_func=preparar_datos_maestro_precios_unificado
    )
