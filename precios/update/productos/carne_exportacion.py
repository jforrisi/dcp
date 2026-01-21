"""
Script: carne_exportacion_update
--------------------------------
Actualiza la base de datos con la serie de ingreso medio de exportación de carne (INAC),
siguiendo el flujo del README:

NOTA: Esta serie requiere Selenium para descargar el Excel (da error 404 con pandas).
Por lo tanto, este script lee únicamente desde data_raw/ generado por el script de descarga.

1) Leer el Excel local desde data_raw/.
2) Validar fechas.
3) Generar Excel de prueba (maestro + maestro_precios).
4) Solicitar confirmación del usuario.
5) Insertar en SQLite solo si el usuario confirma.
"""

import os
import sqlite3

import pandas as pd


# Configuración de origen de datos
DATA_RAW_DIR = "data_raw"
LOCAL_EXCEL_NAME = "serie_semanal_ingreso_medio_exportacion_inac.xlsx"

# Configuración de base de datos y archivos de salida
DB_NAME = "series_tiempo.db"
EXCEL_PRUEBA_NAME = "prueba_carne_exportacion_inac.xlsx"


# Datos del maestro según especificación del usuario
MAESTRO_CARNE_EXPORTACION = {
    "id": 5,  # correlativo siguiente al novillo (id=1)
    "nombre": "Precio exportacion carne (INAC)",
    "tipo": "P",
    "fuente": "INAC",
    "periodicidad": "W",
    "unidad": None,
    "categoria": None,
    "activo": True,
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

    conn.commit()
    conn.close()
    print(f"[OK] Base de datos '{DB_NAME}' creada/verificada con exito")


def leer_excel_desde_data_raw():
    """
    Lee el Excel local desde data_raw/. Busca primero el nombre estándar,
    si no lo encuentra busca archivos que empiecen con "evolucion-semanal"
    y los renombra al nombre correcto.
    """
    base_dir = os.getcwd()
    data_raw_path = os.path.join(base_dir, DATA_RAW_DIR)
    ruta_local = os.path.join(data_raw_path, LOCAL_EXCEL_NAME)

    # Si el archivo con el nombre correcto no existe, buscar alternativos
    if not os.path.exists(ruta_local):
        print(f"[INFO] Archivo '{LOCAL_EXCEL_NAME}' no encontrado, buscando alternativos...")
        
        # Buscar archivos que empiecen con "evolucion-semanal"
        archivos_candidatos = [
            f for f in os.listdir(data_raw_path)
            if f.lower().startswith("evolucion-semanal") and f.lower().endswith((".xls", ".xlsx"))
        ]
        
        if not archivos_candidatos:
            raise FileNotFoundError(
                f"No se encontró el archivo local esperado: {ruta_local}. "
                "Ejecutá primero el script de descarga (carne_exportacion)."
            )
        
        # Usar el más reciente si hay varios
        if len(archivos_candidatos) > 1:
            candidatos_paths = [os.path.join(data_raw_path, f) for f in archivos_candidatos]
            archivo_encontrado = max(candidatos_paths, key=os.path.getmtime)
            archivo_encontrado = os.path.basename(archivo_encontrado)
        else:
            archivo_encontrado = archivos_candidatos[0]
        
        ruta_encontrada = os.path.join(data_raw_path, archivo_encontrado)
        print(f"[INFO] Archivo encontrado: {archivo_encontrado}, renombrando a '{LOCAL_EXCEL_NAME}'...")
        
        # Renombrar al nombre correcto
        os.replace(ruta_encontrada, ruta_local)
        print(f"[OK] Archivo renombrado correctamente")

    print(f"\n[INFO] Leyendo Excel local desde: {ruta_local}")
    # Columna A (índice 0) = FECHA, Columna D (índice 3) = Precios
    # Los datos empiezan en la fila 7 (skiprows=6)
    carne_exportacion = pd.read_excel(
        ruta_local,
        sheet_name="INAC",
        skiprows=6,  # Para empezar desde la fila 7 que tiene los datos reales
        usecols=[0, 3],  # Columna A (índice 0) = FECHA, Columna D (índice 3) = Precios
        header=None,
    )
    carne_exportacion.columns = ["FECHA", "CARNE_EXPORTACION"]
    
    # Eliminar filas que tienen headers como "Producto" o "Semana al..."
    carne_exportacion = carne_exportacion[
        ~carne_exportacion["FECHA"].astype(str).str.contains("Producto|Semana", case=False, na=False)
    ]
    
    carne_exportacion = carne_exportacion.dropna(subset=["FECHA"])
    print(f"[OK] Leido desde archivo local: {len(carne_exportacion)} registros")
    return carne_exportacion


def obtener_carne_exportacion():
    """
    Lee el Excel desde data_raw/.
    Esta serie requiere Selenium (da error 404 con pandas), por lo que
    el archivo debe ser descargado previamente con el script de descarga.
    """
    return leer_excel_desde_data_raw()


def validar_fechas(df: pd.DataFrame) -> pd.DataFrame:
    """Valida que todas las fechas sean válidas (OBLIGATORIO según README)."""
    print("\n[INFO] Validando fechas...")

    fechas_invalidas = []
    fechas_validas = []

    for idx, fecha in enumerate(df["FECHA"]):
        try:
            if pd.isna(fecha):
                fechas_invalidas.append((idx + 7, fecha, "Fecha nula"))  # skiprows=6, entonces fila 0 del DF = fila 7 del Excel
            else:
                fecha_parseada = pd.to_datetime(fecha, errors="coerce")
                if pd.isna(fecha_parseada):
                    fechas_invalidas.append((idx + 7, fecha, "No se pudo parsear"))
                else:
                    fechas_validas.append(fecha_parseada)
        except Exception as exc:
            fechas_invalidas.append((idx + 7, fecha, str(exc)))

    if fechas_invalidas:
        print(f"[ERROR] Se encontraron {len(fechas_invalidas)} fechas invalidas:")
        for fila_excel, fecha, motivo in fechas_invalidas[:10]:
            print(f"   Fila Excel {fila_excel}: {fecha} - {motivo}")
        if len(fechas_invalidas) > 10:
            print(f"   ... y {len(fechas_invalidas) - 10} mas")
        raise ValueError("Hay fechas invalidas. No se puede continuar.")

    df["FECHA"] = pd.to_datetime(df["FECHA"])
    print(f"[OK] Todas las {len(fechas_validas)} fechas son validas")
    print(f"   Rango: {df['FECHA'].min()} a {df['FECHA'].max()}")
    return df


def preparar_datos_maestro_precios(df_carne: pd.DataFrame, maestro_id: int) -> pd.DataFrame:
    """Prepara el DataFrame para maestro_precios."""
    df_precios = df_carne.copy()
    df_precios["maestro_id"] = maestro_id
    df_precios = df_precios[["maestro_id", "FECHA", "CARNE_EXPORTACION"]]
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
        
        # Verificar si existe la columna mercado
        cursor.execute("PRAGMA table_info(maestro)")
        columnas = [col[1] for col in cursor.fetchall()]
        tiene_mercado = "mercado" in columnas
        
        if tiene_mercado:
            cursor.execute(
                """
                INSERT OR IGNORE INTO maestro (id, nombre, tipo, fuente, periodicidad, unidad, categoria, activo, mercado)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    maestro_id,
                    maestro_row["nombre"],
                    maestro_row["tipo"],
                    maestro_row["fuente"],
                    maestro_row["periodicidad"],
                    maestro_row["unidad"],
                    maestro_row.get("categoria", None),
                    maestro_row["activo"],
                    maestro_row.get("mercado", None),
                )
            )
        else:
            cursor.execute(
                """
                INSERT OR IGNORE INTO maestro (id, nombre, tipo, fuente, periodicidad, unidad, categoria, activo)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    maestro_id,
                    maestro_row["nombre"],
                    maestro_row["tipo"],
                    maestro_row["fuente"],
                    maestro_row["periodicidad"],
                    maestro_row["unidad"],
                    maestro_row.get("categoria", None),
                    maestro_row["activo"],
                )
            )
        
        if cursor.rowcount > 0:
            print(f"[OK] Insertado 1 registro en tabla 'maestro' (id={maestro_id})")
        else:
            print(f"[INFO] El registro con id={maestro_id} ya existe en 'maestro', se omite la inserción")

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
    print("ACTUALIZACION DE DATOS: CARNE EXPORTACION (INAC)")
    print("=" * 60)

    crear_base_datos()

    carne_exportacion = obtener_carne_exportacion()
    
    # Mostrar primeros y últimos datos de la serie cruda
    print("\n[INFO] Datos de la serie cruda:")
    print("\nPrimeros datos:")
    print(carne_exportacion.head())
    print("\nÚltimos datos:")
    print(carne_exportacion.tail())
    
    carne_exportacion = validar_fechas(carne_exportacion)

    df_maestro = pd.DataFrame([MAESTRO_CARNE_EXPORTACION])
    df_precios = preparar_datos_maestro_precios(carne_exportacion, MAESTRO_CARNE_EXPORTACION["id"])

    excel_path = generar_excel_prueba(df_maestro, df_precios)
    mostrar_resumen(df_maestro, df_precios)

    print("\n[INFO] Actualizando base de datos automáticamente...")
    print(f"[INFO] Archivo Excel generado: {excel_path}")
    
    # Insertar automáticamente sin pedir confirmación
    insertar_en_bd(df_maestro, df_precios)


if __name__ == "__main__":
    main()
