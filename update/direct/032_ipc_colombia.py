"""
Script: ipc_colombia
--------------------
Procesa el Excel de IPC de Colombia del DANE y lo inserta en maestro_precios.
Lee update/historicos/ipc_colombia.xlsx, transforma a formato tidy e inserta en BD.
"""

import os
import pandas as pd
from datetime import datetime
from _helpers import insertar_en_bd_unificado

# Configuración
ARCHIVO_ENTRADA = "update/historicos/ipc_colombia.xlsx"
ID_VARIABLE = 9
ID_PAIS = 170

# Mapeo de meses en español a números
MESES_ES = {
    'enero': 1,
    'febrero': 2,
    'marzo': 3,
    'abril': 4,
    'mayo': 5,
    'junio': 6,
    'julio': 7,
    'agosto': 8,
    'septiembre': 9,
    'octubre': 10,
    'noviembre': 11,
    'diciembre': 12
}


def leer_excel():
    """Lee el Excel sin header para tener control total sobre las filas."""
    ruta_entrada = os.path.join(os.getcwd(), ARCHIVO_ENTRADA)
    
    if not os.path.exists(ruta_entrada):
        raise FileNotFoundError(f"No se encontró el archivo: {ruta_entrada}")
    
    print(f"[INFO] Leyendo archivo: {ruta_entrada}")
    df = pd.read_excel(ruta_entrada, header=None)
    
    print(f"[OK] Archivo leído: {df.shape[0]} filas, {df.shape[1]} columnas")
    return df


def extraer_anios(df):
    """Extrae los años de la fila 8 (índice 8), desde columna 1 en adelante."""
    fila_anios = df.iloc[8, 1:].values  # Fila 8, desde columna 1
    
    # Convertir a numérico y filtrar NaN
    anios = []
    for val in fila_anios:
        try:
            anio = int(float(val)) if pd.notna(val) else None
            if anio:
                anios.append(anio)
        except (ValueError, TypeError):
            continue
    
    print(f"[INFO] Años encontrados: {len(anios)} años")
    print(f"       Rango: {min(anios)} - {max(anios)}")
    return anios


def extraer_meses(df):
    """Extrae los meses de las filas 9-20 (índices 9-20), columna 0."""
    meses = []
    for idx in range(9, 21):  # Filas 9-20
        mes_nombre = df.iloc[idx, 0]
        if pd.notna(mes_nombre):
            mes_str = str(mes_nombre).strip().lower()
            if mes_str in MESES_ES:
                meses.append((idx, mes_str, MESES_ES[mes_str]))
    
    print(f"[INFO] Meses encontrados: {len(meses)} meses")
    return meses


def transformar_a_tidy(df, anios, meses):
    """
    Transforma el DataFrame de formato ancho a largo (tidy).
    Crea un DataFrame con columnas: fecha, valor
    """
    print("\n[INFO] Transformando datos a formato tidy...")
    
    registros = []
    
    # Para cada mes
    for idx_fila, mes_nombre, mes_num in meses:
        # Para cada año
        for col_idx, anio in enumerate(anios, start=1):  # start=1 porque columna 0 es el mes
            # Obtener el valor en la intersección
            valor = df.iloc[idx_fila, col_idx]
            
            # Convertir a numérico
            if pd.notna(valor):
                try:
                    valor_num = float(valor)
                    # Crear fecha (primer día del mes)
                    fecha = datetime(int(anio), mes_num, 1).date()
                    
                    registros.append({
                        'fecha': fecha,
                        'valor': valor_num
                    })
                except (ValueError, TypeError):
                    continue
    
    df_tidy = pd.DataFrame(registros)
    
    # Ordenar por fecha
    df_tidy = df_tidy.sort_values('fecha').reset_index(drop=True)
    
    print(f"[OK] Datos transformados: {len(df_tidy)} registros")
    print(f"     Rango de fechas: {df_tidy['fecha'].min()} a {df_tidy['fecha'].max()}")
    print(f"     Valores únicos: {df_tidy['valor'].nunique()}")
    
    return df_tidy


def preparar_datos_para_bd(df_tidy):
    """
    Prepara el DataFrame para inserción en BD.
    Convierte fecha a formato date y renombra columnas.
    """
    df_bd = df_tidy.copy()
    
    # Asegurar que fecha sea date (no datetime)
    if df_bd['fecha'].dtype == 'object':
        df_bd['fecha'] = pd.to_datetime(df_bd['fecha']).dt.date
    elif hasattr(df_bd['fecha'].iloc[0], 'date'):
        df_bd['fecha'] = df_bd['fecha'].apply(lambda x: x.date() if hasattr(x, 'date') else x)
    
    # Renombrar columnas para el formato esperado por el helper
    df_bd = df_bd.rename(columns={'fecha': 'FECHA', 'valor': 'VALOR'})
    
    return df_bd


def main():
    """Función principal."""
    print("=" * 80)
    print("PROCESAMIENTO DE IPC COLOMBIA - DANE")
    print("=" * 80)
    print(f"Archivo entrada: {ARCHIVO_ENTRADA}")
    print("Base de datos: PostgreSQL (DATABASE_URL)")
    print(f"ID Variable: {ID_VARIABLE}")
    print(f"ID País: {ID_PAIS}")
    print("=" * 80)
    
    try:
        # 1. Leer Excel
        df = leer_excel()
        
        # 2. Extraer años
        anios = extraer_anios(df)
        if not anios:
            raise ValueError("No se encontraron años en el archivo")
        
        # 3. Extraer meses
        meses = extraer_meses(df)
        if not meses:
            raise ValueError("No se encontraron meses en el archivo")
        
        # 4. Transformar a formato tidy
        df_tidy = transformar_a_tidy(df, anios, meses)
        
        if df_tidy.empty:
            raise ValueError("No se generaron registros válidos")
        
        # 5. Preparar datos para BD
        df_bd = preparar_datos_para_bd(df_tidy)
        
        # 6. Insertar en base de datos
        print(f"\n[INFO] Insertando {len(df_bd)} registros en maestro_precios...")
        insertar_en_bd_unificado(
            ID_VARIABLE,
            ID_PAIS,
            df_bd
        )
        
        print("\n[SUCCESS] Proceso completado exitosamente")
        
    except Exception as e:
        print(f"\n[ERROR] Error durante el proceso: {e}")
        import traceback
        traceback.print_exc()
        raise


if __name__ == "__main__":
    main()
