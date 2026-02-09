"""
Script: indice_precios_exportacion_uruguay
-------------------------------------------
Actualiza la base de datos con los Índices de Precios de Exportación (IPE) de Uruguay.

Lee el archivo web_exp_ciiu_ip.xls desde update/historicos/ y procesa múltiples variables:
- Trigo - IPE (id_variable 53)
- Soja - IPE (id_variable 54)
- Frutas - IPE (id_variable 55)
- Ganado - IPE (id_variable 56)
- Madera - IPE (id_variable 57)
- Industria cárnica - IPE (id_variable 58)
- Industria léctea - IPE (id_variable 59)
- Industria arroz - IPE (id_variable 60)
- Industria bebida - IPE (id_variable 61)
- Industria textil - IPE (id_variable 62)
- Industria cueros - IPE (id_variable 63)
- Industria papel - IPE (id_variable 64)
- Industria química - IPE (id_variable 65)
- Industria farmacéutica - IPE (id_variable 66)
- Industria producto limpieza - IPE (id_variable 67)
- Industria automotriz - IPE (id_variable 68)

Estructura del archivo:
- Fila 7 (índice 7): Fechas (desde columna 4)
- Fila 13 (índice 12): Trigo - IPE
- Fila 14 (índice 13): Soja - IPE
- ... (ver MAPEO_FILAS_VARIABLES para el mapeo completo)
"""

import os
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from db.connection import execute_update, execute_query, insert_dataframe

# Configuración
ARCHIVO_EXCEL = "update/historicos/web_exp_ciiu_ip.xls"
ID_PAIS_URUGUAY = 858

# Mapeo de filas (índice) a id_variable
# Nota: Las filas en Excel empiezan en 1, pero pandas usa índice 0
# Fila 13 en Excel = índice 12 en pandas
MAPEO_FILAS_VARIABLES = {
    12: 53,  # Fila 13: Trigo - IPE
    13: 54,  # Fila 14: Soja - IPE
    14: 55,  # Fila 15: Frutas - IPE
    15: 56,  # Fila 16: Ganado - IPE
    16: 57,  # Fila 17: Madera - IPE
    18: 58,  # Fila 19: Industria cárnica - IPE
    20: 59,  # Fila 21: Industria léctea - IPE
    21: 60,  # Fila 22: Industria arroz - IPE
    23: 61,  # Fila 24: Industria bebida - IPE
    25: 62,  # Fila 26: Industria textil - IPE
    26: 63,  # Fila 27: Industria cueros - IPE
    28: 64,  # Fila 29: Industria papel - IPE
    31: 65,  # Fila 32: Industria química - IPE
    32: 66,  # Fila 33: Industria farmacéutica - IPE
    33: 67,  # Fila 34: Industria producto limpieza - IPE
    36: 68,  # Fila 37: Industria automotriz - IPE
}

FILA_FECHAS = 7  # Índice 7 (fila 8 en Excel)
COLUMNA_INICIO = 4  # Las fechas y valores empiezan desde la columna 4 (índice 4)


def leer_y_transponer():
    """Lee el Excel y transpone los datos."""
    base_dir = os.getcwd()
    ruta_archivo = os.path.join(base_dir, ARCHIVO_EXCEL)
    
    if not os.path.exists(ruta_archivo):
        raise FileNotFoundError(
            f"No se encontró el archivo: {ruta_archivo}. "
            "Asegúrate de que el archivo web_exp_ciiu_ip.xls esté en update/historicos/"
        )
    
    print(f"[INFO] Leyendo archivo: {ruta_archivo}")
    df = pd.read_excel(ruta_archivo, header=None, engine='xlrd')
    
    print(f"[OK] Archivo leído: {df.shape[0]} filas, {df.shape[1]} columnas")
    
    # Extraer fechas de la fila 7 (índice 7), desde columna 4
    fila_fechas = df.iloc[FILA_FECHAS, COLUMNA_INICIO:].copy()
    
    # Convertir fechas a datetime
    fechas = []
    for fecha_val in fila_fechas:
        if pd.notna(fecha_val):
            try:
                if isinstance(fecha_val, datetime):
                    fecha = fecha_val.date()
                else:
                    fecha = pd.to_datetime(fecha_val).date()
                fechas.append(fecha)
            except:
                continue
    
    print(f"[OK] Fechas extraídas: {len(fechas)} fechas")
    if fechas:
        print(f"      Rango: {fechas[0]} a {fechas[-1]}")
    
    # Procesar cada fila de datos
    datos_procesados = []
    
    for indice_fila, id_variable in MAPEO_FILAS_VARIABLES.items():
        if indice_fila >= len(df):
            print(f"[WARN] Fila {indice_fila + 1} no existe en el archivo, omitiendo...")
            continue
        
        fila_datos = df.iloc[indice_fila, COLUMNA_INICIO:].copy()
        
        # Obtener nombre de la variable para logging
        nombre_var = df.iloc[indice_fila, 3] if len(df.iloc[indice_fila]) > 3 else f"Variable {id_variable}"
        print(f"[INFO] Procesando fila {indice_fila + 1} (id_variable {id_variable}): {nombre_var}")
        
        # Crear registros para cada fecha
        valores_procesados = 0
        for i, valor in enumerate(fila_datos):
            if i >= len(fechas):
                break
            
            fecha = fechas[i]
            
            # Convertir valor a numérico
            if pd.notna(valor):
                try:
                    valor_num = pd.to_numeric(valor, errors='coerce')
                    if pd.notna(valor_num):
                        datos_procesados.append({
                            'id_variable': id_variable,
                            'id_pais': ID_PAIS_URUGUAY,
                            'fecha': fecha,
                            'valor': float(valor_num)
                        })
                        valores_procesados += 1
                except:
                    continue
        
        print(f"      Valores procesados: {valores_procesados}")
    
    # Crear DataFrame
    df_final = pd.DataFrame(datos_procesados)
    
    if df_final.empty:
        raise ValueError("No se procesaron datos")
    
    print(f"\n[OK] Total de registros procesados: {len(df_final)}")
    print(f"      Variables: {df_final['id_variable'].nunique()}")
    if not df_final.empty:
        print(f"      Rango de fechas: {df_final['fecha'].min()} a {df_final['fecha'].max()}")
    
    return df_final


def insertar_en_bd(df):
    """Inserta los datos en maestro_precios para todas las variables."""
    print("\n[INFO] Conectando a base de datos...")

    id_variables = df['id_variable'].unique().tolist()

    print(f"[INFO] Eliminando registros existentes para {len(id_variables)} variables...")

    placeholders = ','.join(['?'] * len(id_variables))
    success, error, _ = execute_update(
        f"DELETE FROM maestro_precios WHERE id_variable IN ({placeholders}) AND id_pais = ?",
        tuple(id_variables) + (ID_PAIS_URUGUAY,),
    )
    if not success:
        raise RuntimeError(error or "Error al eliminar registros")

    print(f"\n[INFO] Insertando {len(df)} registros en maestro_precios...")
    insert_dataframe("maestro_precios", df, if_exists="append", index=False)
    print(f"[OK] {len(df):,} registros insertados exitosamente")

    print("\n[INFO] Verificando inserción...")
    for id_var in sorted(id_variables):
        rows = execute_query(
            "SELECT COUNT(*) as cnt FROM maestro_precios WHERE id_variable = ? AND id_pais = ?",
            (id_var, ID_PAIS_URUGUAY),
        )
        count = rows[0]["cnt"] if rows else 0
        print(f"      id_variable {id_var}: {count} registros")


def main():
    """Función principal."""
    print("=" * 80)
    print("ÍNDICES DE PRECIOS DE EXPORTACIÓN - URUGUAY")
    print("=" * 80)
    print(f"Archivo origen: {ARCHIVO_EXCEL}")
    print("Base de datos: PostgreSQL (DATABASE_URL)")
    print(f"País: Uruguay (id_pais={ID_PAIS_URUGUAY})")
    print(f"Variables a procesar: {len(MAPEO_FILAS_VARIABLES)}")
    print("=" * 80)
    
    try:
        # 1. Leer y transponer datos
        df_procesado = leer_y_transponer()
        
        # 2. Insertar en base de datos
        insertar_en_bd(df_procesado)
        
        print("\n" + "=" * 80)
        print("[SUCCESS] Proceso completado exitosamente")
        print("=" * 80)
        print(f"Registros procesados: {len(df_procesado)}")
        print(f"Variables actualizadas: {df_procesado['id_variable'].nunique()}")
        
    except Exception as e:
        print(f"\n[ERROR] Error durante el proceso: {e}")
        import traceback
        traceback.print_exc()
        raise


if __name__ == "__main__":
    main()
