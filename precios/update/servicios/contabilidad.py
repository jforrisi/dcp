"""
Script: contabilidad
--------------------
Actualiza la base de datos con la serie PPI (Producer Price Index) 
para Accounting Services (CPA) (NAICS 541211) del BLS,
siguiendo el flujo del README:

1) Obtener datos desde la API de BLS v2 (sin registro requerido).
2) Validar fechas.
3) Generar Excel de prueba.
4) Actualizar automáticamente la base de datos.

Serie BLS: PCU541211541211
Descripción: Producer Price Index for Accounting Services (CPA)
Base: Dec 2000 = 100
Periodicidad: Mensual (M)

NOTA: Usa API v2 sin registro (funciona para rangos de hasta 10 años).
Para obtener datos desde 2010, se hacen múltiples consultas si es necesario.
"""

import os
import sqlite3
import sys
from datetime import datetime

import pandas as pd
import requests

# Configuración de origen de datos
BLS_API_URL_V2 = "https://api.bls.gov/publicAPI/v2/timeseries/data/"
BLS_API_KEY = "f13f1d4aa9b947ca80fa0d8d063ac94f"  # API Key para aumentar límite a 500 consultas/día
BLS_SERIES_ID = "PCU541211541211"
BLS_START_YEAR = 2010
BLS_END_YEAR = datetime.now().year

# Configuración de base de datos y archivos de salida
DB_NAME = "series_tiempo.db"
EXCEL_PRUEBA_NAME = "prueba_contabilidad_bls.xlsx"

# Datos del maestro según especificación del usuario
MAESTRO_CONTABILIDAD = {
    "id": 16,
    "nombre": "Contabilidad (CPA)",
    "tipo": "S",  # servicio
    "fuente": "BLS",
    "periodicidad": "M",  # mensual
    "unidad": "Indice",
    "categoria": None,
    "activo": True,
    "mercado": "E",  # Exportación
    "link": "https://data.bls.gov/dataViewer/view/timeseries/PCU541211541211",
}


def crear_base_datos():
    """Crea la base de datos SQLite y las tablas según el esquema del README."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS maestro (
            id INTEGER PRIMARY KEY,
            nombre VARCHAR(255) NOT NULL,
            tipo CHAR(1) NOT NULL CHECK (tipo IN ('P', 'S', 'M')),
            fuente VARCHAR(255) NOT NULL,
            periodicidad CHAR(1) NOT NULL CHECK (periodicidad IN ('D', 'W', 'M')),
            unidad VARCHAR(100),
            categoria VARCHAR(255),
            activo BOOLEAN NOT NULL DEFAULT 1
        )
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS maestro_precios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            maestro_id INTEGER NOT NULL,
            fecha DATE NOT NULL,
            valor NUMERIC(18, 6) NOT NULL,
            FOREIGN KEY (maestro_id) REFERENCES maestro(id)
        )
        """
    )

    cursor.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_maestro_precios_maestro_id
        ON maestro_precios (maestro_id)
        """
    )
    cursor.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_maestro_precios_fecha
        ON maestro_precios (fecha)
        """
    )
    cursor.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_maestro_precios_maestro_fecha
        ON maestro_precios (maestro_id, fecha)
        """
    )

    # Agregar columna 'link' si no existe
    cursor.execute("PRAGMA table_info(maestro)")
    columnas = [col[1] for col in cursor.fetchall()]
    if "link" not in columnas:
        try:
            cursor.execute("ALTER TABLE maestro ADD COLUMN link VARCHAR(500)")
            print("[INFO] Columna 'link' agregada a la tabla 'maestro'")
        except sqlite3.OperationalError as e:
            if "duplicate column" not in str(e).lower():
                print(f"[WARN] No se pudo agregar columna 'link': {e}")

    conn.commit()
    conn.close()
    print(f"[OK] Base de datos '{DB_NAME}' creada/verificada con exito")


def obtener_datos_bls_v2():
    """
    Obtiene datos desde la API de BLS v2 con API key (permite hasta 20 años por consulta).
    Con API key, el límite diario aumenta de 25 a 500 consultas.
    Devuelve un DataFrame con columnas AÑO, MES, VALOR.
    Obtiene datos desde enero 2010 hasta el último disponible.
    """
    print("\n[INFO] Obteniendo datos desde la API de BLS v2 (con API key)...")
    print(f"   Serie: {BLS_SERIES_ID}")
    print(f"   Rango deseado: Enero {BLS_START_YEAR} - {BLS_END_YEAR}")
    
    # Con API key, la API v2 permite hasta 20 años por consulta
    # Dividir en chunks de 20 años si es necesario
    todos_registros = []
    
    año_inicio = BLS_START_YEAR
    while año_inicio <= BLS_END_YEAR:
        año_fin = min(año_inicio + 19, BLS_END_YEAR)  # Máximo 20 años (inclusive)
        
        print(f"\n[INFO] Consultando años {año_inicio} - {año_fin}...")
        
        # Preparar request a la API v2 (POST request) con API key
        payload = {
            "seriesid": [BLS_SERIES_ID],
            "startyear": str(año_inicio),
            "endyear": str(año_fin),
            "registrationkey": BLS_API_KEY
        }
        
        try:
            response = requests.post(
                BLS_API_URL_V2,
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=30
            )
            response.raise_for_status()
            
            data = response.json()
            
            # Verificar si hay errores en la respuesta
            if data.get("status") != "REQUEST_SUCCEEDED":
                error_msg = data.get("message", ["Error desconocido"])
                raise ValueError(f"Error en API BLS: {error_msg}")
            
            # Extraer datos de la serie
            series_data = data.get("Results", {}).get("series", [])
            if not series_data:
                print(f"[WARN] No se encontraron datos para años {año_inicio} - {año_fin}")
                año_inicio = año_fin + 1
                continue
            
            # Procesar los datos
            for serie in series_data:
                for dato in serie.get("data", []):
                    año = int(dato.get("year"))
                    periodo = dato.get("period")  # Formato: M01, M02, ..., M12
                    valor_str = dato.get("value")
                    
                    # Parsear periodo (M01 -> 1, M02 -> 2, etc.)
                    if periodo and periodo.startswith("M"):
                        mes = int(periodo[1:])
                        if 1 <= mes <= 12:
                            # Convertir valor a float
                            try:
                                valor = float(valor_str) if valor_str != "" else None
                                if valor is not None:
                                    # Filtrar: solo desde enero 2010 en adelante
                                    if año > BLS_START_YEAR or (año == BLS_START_YEAR and mes >= 1):
                                        todos_registros.append({
                                            "AÑO": año,
                                            "MES": mes,
                                            "VALOR": valor
                                        })
                            except (ValueError, TypeError):
                                continue
            
            print(f"[OK] Obtenidos datos para años {año_inicio} - {año_fin}")
            
            # Avanzar al siguiente chunk
            año_inicio = año_fin + 1
            
        except requests.exceptions.RequestException as e:
            raise Exception(f"Error al conectar con la API de BLS: {e}")
        except Exception as e:
            raise Exception(f"Error al procesar datos de la API: {e}")
    
    if not todos_registros:
        raise ValueError("No se pudieron extraer datos válidos de la API")
    
    df = pd.DataFrame(todos_registros)
    # Eliminar duplicados por si acaso (puede haber solapamiento)
    df = df.drop_duplicates(subset=["AÑO", "MES"])
    # Filtrar explícitamente desde enero 2010
    df = df[(df["AÑO"] > BLS_START_YEAR) | ((df["AÑO"] == BLS_START_YEAR) & (df["MES"] >= 1))]
    # Ordenar por año y mes
    df = df.sort_values(["AÑO", "MES"]).reset_index(drop=True)
    
    print(f"\n[OK] Total obtenidos: {len(df)} registros válidos desde Enero {BLS_START_YEAR}")
    return df


def combinar_anio_mes_a_fecha(df: pd.DataFrame) -> pd.DataFrame:
    """
    Combina las columnas AÑO y MES para crear una fecha (primer día del mes).
    """
    print("\n[INFO] Combinando año y mes para crear fechas...")
    
    fechas = []
    fechas_invalidas = []
    
    for idx, row in df.iterrows():
        año = row["AÑO"]
        mes = row["MES"]
        
        try:
            año_int = int(año)
            mes_int = int(mes)
            
            if not (1900 <= año_int <= 2100):
                fechas_invalidas.append((idx, año, mes, "Año fuera de rango"))
                continue
            
            if not (1 <= mes_int <= 12):
                fechas_invalidas.append((idx, año, mes, "Mes fuera de rango (1-12)"))
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
    
    df["FECHA"] = fechas
    print(f"[OK] {len(fechas)} fechas creadas correctamente")
    return df


def validar_fechas(df: pd.DataFrame) -> pd.DataFrame:
    """Valida que todas las fechas sean válidas (OBLIGATORIO según README)."""
    print("\n[INFO] Validando fechas...")
    
    fechas_nulas = df["FECHA"].isna().sum()
    
    if fechas_nulas > 0:
        print(f"[ERROR] Se encontraron {fechas_nulas} fechas nulas")
        raise ValueError("Hay fechas nulas. No se puede continuar.")
    
    # Verificar que la primera fecha sea enero 2010
    primera_fecha = df["FECHA"].min()
    if primera_fecha.year != BLS_START_YEAR or primera_fecha.month != 1:
        print(f"[WARN] La primera fecha es {primera_fecha}, se esperaba Enero {BLS_START_YEAR}")
    
    print(f"[OK] Todas las {len(df)} fechas son válidas")
    print(f"   Rango: {df['FECHA'].min()} a {df['FECHA'].max()}")
    return df


def preparar_datos_maestro_precios(df_ppi: pd.DataFrame, maestro_id: int) -> pd.DataFrame:
    """Prepara el DataFrame para maestro_precios."""
    df_precios = df_ppi.copy()
    df_precios["maestro_id"] = maestro_id
    df_precios = df_precios[["maestro_id", "FECHA", "VALOR"]]
    df_precios.columns = ["maestro_id", "fecha", "valor"]
    
    # Asegurar que valor sea numérico
    df_precios["valor"] = pd.to_numeric(df_precios["valor"], errors="coerce")
    
    # Eliminar filas con valor nulo
    df_precios = df_precios.dropna(subset=["valor"])
    return df_precios


def generar_excel_prueba(df_maestro: pd.DataFrame, df_precios: pd.DataFrame) -> str:
    """Genera el archivo Excel de prueba (OBLIGATORIO según README)."""
    print("\n[INFO] Generando archivo Excel de prueba...")

    excel_path = os.path.join(os.getcwd(), EXCEL_PRUEBA_NAME)
    
    # Si el archivo existe y está abierto, intentar eliminarlo o usar nombre alternativo
    if os.path.exists(excel_path):
        try:
            os.remove(excel_path)
        except PermissionError:
            # Si no se puede eliminar (está abierto), usar nombre con timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            base_name = EXCEL_PRUEBA_NAME.replace(".xlsx", "")
            excel_path = os.path.join(os.getcwd(), f"{base_name}_{timestamp}.xlsx")
            print(f"[WARN] Archivo original está abierto, usando nombre alternativo: {excel_path}")
    
    try:
        with pd.ExcelWriter(excel_path, engine="openpyxl") as writer:
            df_maestro.to_excel(writer, sheet_name="maestro", index=False)
            df_precios.to_excel(writer, sheet_name="maestro_precios", index=False)
    except PermissionError:
        # Si aún falla, usar nombre con timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        base_name = EXCEL_PRUEBA_NAME.replace(".xlsx", "")
        excel_path = os.path.join(os.getcwd(), f"{base_name}_{timestamp}.xlsx")
        with pd.ExcelWriter(excel_path, engine="openpyxl") as writer:
            df_maestro.to_excel(writer, sheet_name="maestro", index=False)
            df_precios.to_excel(writer, sheet_name="maestro_precios", index=False)

    print(f"[OK] Archivo Excel generado: {excel_path}")
    print(f"   - Hoja 'maestro': {len(df_maestro)} fila(s)")
    print(f"   - Hoja 'maestro_precios': {len(df_precios)} fila(s)")
    return excel_path


def mostrar_resumen(df_maestro: pd.DataFrame, df_precios: pd.DataFrame) -> None:
    """Muestra resumen de los datos que se van a insertar."""
    print("\n" + "=" * 60)
    print("RESUMEN DE DATOS A INSERTAR")
    print("=" * 60)

    print("\nTABLA: maestro")
    print("-" * 60)
    print(df_maestro.to_string(index=False))

    print("\nTABLA: maestro_precios")
    print("-" * 60)
    print(f"Total de registros: {len(df_precios)}")
    print("\nPrimeros 5 registros:")
    print(df_precios.head().to_string(index=False))
    print("\nÚltimos 5 registros:")
    print(df_precios.tail().to_string(index=False))
    print(f"\nRango de fechas: {df_precios['fecha'].min()} a {df_precios['fecha'].max()}")
    print(
        f"Valores: min={df_precios['valor'].min():.2f}, "
        f"max={df_precios['valor'].max():.2f}, "
        f"promedio={df_precios['valor'].mean():.2f}"
    )
    print("=" * 60)


def insertar_en_bd(df_maestro: pd.DataFrame, df_precios: pd.DataFrame) -> None:
    """Inserta los datos en la base de datos SQLite."""
    print("\n[INFO] Insertando datos en la base de datos...")

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    try:
        # Insertar en maestro usando INSERT OR IGNORE para evitar duplicados
        maestro_id = int(df_maestro.iloc[0]["id"])
        maestro_row = df_maestro.iloc[0]
        
        # Verificar qué columnas existen
        cursor.execute("PRAGMA table_info(maestro)")
        columnas = [col[1] for col in cursor.fetchall()]
        tiene_mercado = "mercado" in columnas
        tiene_link = "link" in columnas
        
        # Construir la query dinámicamente según las columnas disponibles
        campos = ["id", "nombre", "tipo", "fuente", "periodicidad", "unidad", "categoria", "activo"]
        valores = [
            maestro_id,
            maestro_row["nombre"],
            maestro_row["tipo"],
            maestro_row["fuente"],
            maestro_row["periodicidad"],
            maestro_row["unidad"],
            maestro_row.get("categoria", None),
            maestro_row["activo"],
        ]
        
        if tiene_mercado:
            campos.append("mercado")
            valores.append(maestro_row.get("mercado", None))
        
        if tiene_link:
            campos.append("link")
            valores.append(maestro_row.get("link", None))
        
        campos_str = ", ".join(campos)
        placeholders = ", ".join(["?"] * len(campos))
        
        cursor.execute(
            f"""
            INSERT OR IGNORE INTO maestro ({campos_str})
            VALUES ({placeholders})
            """,
            tuple(valores)
        )
        
        if cursor.rowcount > 0:
            print(f"[OK] Insertado 1 registro en tabla 'maestro' (id={maestro_id})")
        else:
            print(f"[INFO] El registro con id={maestro_id} ya existe en 'maestro'")
            # Actualizar el registro existente, especialmente el link si existe
            if tiene_link:
                cursor.execute(
                    """
                    UPDATE maestro 
                    SET link = ?
                    WHERE id = ?
                    """,
                    (maestro_row.get("link", None), maestro_id)
                )
                if cursor.rowcount > 0:
                    print(f"[OK] Link actualizado en registro id={maestro_id}")

        # Verificar qué precios ya existen para evitar duplicados
        cursor.execute(
            """
            SELECT fecha FROM maestro_precios 
            WHERE maestro_id = ?
            """,
            (maestro_id,)
        )
        fechas_existentes = {row[0] for row in cursor.fetchall()}
        
        # Filtrar precios que ya existen
        df_precios_nuevos = df_precios[
            ~df_precios["fecha"].astype(str).isin([str(f) for f in fechas_existentes])
        ]
        
        if len(df_precios_nuevos) == 0:
            print(f"[INFO] Todos los precios ya existen en la base de datos, no se insertan nuevos registros")
        else:
            print(f"[INFO] Se insertarán {len(df_precios_nuevos)} nuevos registros (de {len(df_precios)} totales)")
            df_precios_nuevos.to_sql("maestro_precios", conn, if_exists="append", index=False)
            print(f"[OK] Insertados {len(df_precios_nuevos)} registro(s) en tabla 'maestro_precios'")

        conn.commit()
        print(f"\n[OK] Datos insertados exitosamente en '{DB_NAME}'")
    except Exception as exc:
        conn.rollback()
        print(f"[ERROR] Error al insertar datos: {exc}")
        raise
    finally:
        conn.close()


def main():
    print("=" * 60)
    print("ACTUALIZACION DE DATOS: CONTABILIDAD (CPA) (BLS)")
    print("=" * 60)

    crear_base_datos()

    ppi_df = obtener_datos_bls_v2()
    
    # Mostrar primeros y últimos datos de la serie cruda
    print("\n[INFO] Datos de la serie cruda:")
    print("\nPrimeros datos:")
    print(ppi_df.head())
    print("\nÚltimos datos:")
    print(ppi_df.tail())
    
    # Combinar año y mes para crear fechas
    ppi_df = combinar_anio_mes_a_fecha(ppi_df)
    ppi_df = validar_fechas(ppi_df)

    df_maestro = pd.DataFrame([MAESTRO_CONTABILIDAD])
    df_precios = preparar_datos_maestro_precios(ppi_df, MAESTRO_CONTABILIDAD["id"])

    excel_path = generar_excel_prueba(df_maestro, df_precios)
    mostrar_resumen(df_maestro, df_precios)

    print("\n[INFO] Actualizando base de datos automáticamente...")
    print(f"[INFO] Archivo Excel generado: {excel_path}")
    insertar_en_bd(df_maestro, df_precios)


if __name__ == "__main__":
    main()
