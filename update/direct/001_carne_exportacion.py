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

import pandas as pd
from _helpers import (
    validar_fechas_unificado,
    insertar_en_bd_unificado
)

# Configuración de origen de datos
DATA_RAW_DIR = "data_raw"
LOCAL_EXCEL_NAME = "serie_semanal_ingreso_medio_exportacion_inac.xlsx"

# Configuración de base de datos y archivos de salida
# Configuración de base de datos
# NOTA: Estos valores deben existir en maestro_database.xlsx
# Si no existen, agregar el registro al Excel y ejecutar migracion_maestro_simplificar.py
ID_VARIABLE = 11  # Ingreso medio exportacion carne - INAC
ID_PAIS = 858  # Uruguay

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

# Funciones antiguas eliminadas - ahora se usan los helpers unificados de _helpers.py

def main():
    print("=" * 60)
    print("ACTUALIZACION DE DATOS: CARNE EXPORTACION (INAC)")
    print("=" * 60)
    carne_exportacion = obtener_carne_exportacion()
    
    # Mostrar primeros y últimos datos de la serie cruda
    print("\n[INFO] Datos de la serie cruda:")
    print("\nPrimeros datos:")
    print(carne_exportacion.head())
    print("\nÚltimos datos:")
    print(carne_exportacion.tail())
    
    # Renombrar columna para que coincida con el formato esperado
    df_precios = carne_exportacion.rename(columns={"CARNE_EXPORTACION": "VALOR"})
    
    # Validar fechas usando helper unificado
    df_precios = validar_fechas_unificado(df_precios)

    # Verificar que ID_VARIABLE e ID_PAIS están configurados
    if ID_VARIABLE is None or ID_PAIS is None:
        print("\n[ERROR] ID_VARIABLE e ID_PAIS deben estar configurados en el script.")
        print("   Consulta maestro_database.xlsx o la base de datos para obtener los valores correctos.")
        return

    print("\n[INFO] Actualizando base de datos automáticamente...")
    
    # Insertar automáticamente usando helper unificado
    insertar_en_bd_unificado(ID_VARIABLE, ID_PAIS, df_precios)

if __name__ == "__main__":
    main()
