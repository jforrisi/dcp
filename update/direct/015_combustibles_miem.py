"""
Actualiza series de combustibles MIEM:
- Gasoil (id_variable=7, id_pais=858)
- Propano/Súpergas (si está en maestro_database.xlsx)

1) Leer Excel desde data_raw.
2) Validar fechas.
3) Actualizar automáticamente la base de datos.
"""

import os

import pandas as pd
from _helpers import (
    combinar_anio_mes_a_fecha,
    validar_fechas_solo_nulas,
    insertar_en_bd_unificado
)


# Configuración
EXCEL_PATH = os.path.join("data_raw", "miem_derivados", "precios medios de derivados de petroleo con y sin impuestos.xls")
DB_NAME = "series_tiempo.db"

# Configuración de IDs (desde maestro_database.xlsx Sheet1_old)
ID_VARIABLE_GASOIL = 7  # Gasoil
ID_PAIS_GASOIL = 858  # Uruguay

# NOTA: Propano no está en maestro_database.xlsx. Si se agrega, configurar aquí:
ID_VARIABLE_PROPANO = None  # Configurar cuando esté en maestro_database.xlsx
ID_PAIS_PROPANO = None  # Configurar cuando esté en maestro_database.xlsx


def leer_excel():
    """
    Lee el Excel principal usando:
    - Gasoil desde 'Hoja1' (columna 'gas oil - $/litro')
    - Propano industrial sin impuestos desde 'precio medio comb' columna CA
    """
    if not os.path.exists(EXCEL_PATH):
        raise FileNotFoundError(f"No se encuentra el Excel: {EXCEL_PATH}")

    # Gasoil desde Hoja1
    hoja1 = pd.read_excel(EXCEL_PATH, sheet_name="Hoja1", header=1)
    for col in ["fecha", "gas oil - $/litro"]:
        if col not in hoja1.columns:
            raise ValueError(f"Falta columna '{col}' en hoja Hoja1")
    
    # Renombrar columnas al leerlas
    df_g = hoja1[["fecha", "gas oil - $/litro"]].copy()
    df_g = df_g.rename(columns={"gas oil - $/litro": "gasoil", "fecha": "FECHA"})
    
    # Convertir tipos
    df_g["FECHA"] = pd.to_datetime(df_g["FECHA"], errors="coerce")
    df_g["gasoil"] = pd.to_numeric(df_g["gasoil"], errors="coerce")
    
    # Eliminar filas con valores nulos
    df_g = df_g.dropna(subset=["FECHA", "gasoil"])
    
    # Verificar que las columnas existen antes de acceder
    if "FECHA" not in df_g.columns:
        raise ValueError(f"La columna 'FECHA' no existe después del procesamiento. Columnas disponibles: {list(df_g.columns)}")
    
    # Renombrar gasoil a VALOR
    df_g = df_g.rename(columns={"gasoil": "VALOR"})
    df_g = df_g[["FECHA", "VALOR"]]

    # Propano industrial sin impuestos desde 'precio medio comb' (CA = índice 78 con header en fila 3)
    comb = pd.read_excel(EXCEL_PATH, sheet_name="precio medio comb", header=2)
    # Columnas base
    col_anio = comb.columns[0]
    col_mes = comb.columns[1]
    col_ca = comb.columns[78]  # CA (0-index)

    df_p = comb[[col_anio, col_mes, col_ca]].copy()
    df_p.columns = ["AÑO", "MES", "propano"]
    df_p["AÑO"] = pd.to_numeric(df_p["AÑO"], errors="coerce")
    df_p["MES"] = pd.to_numeric(df_p["MES"], errors="coerce")
    df_p["propano"] = pd.to_numeric(df_p["propano"], errors="coerce")
    df_p = df_p.dropna(subset=["AÑO", "MES", "propano"])
    
    # Combinar año y mes para crear fechas
    df_p = combinar_anio_mes_a_fecha(df_p)
    df_p = df_p.rename(columns={"propano": "VALOR"})
    df_p = df_p[["FECHA", "VALOR"]]
    
    return {"gasoil": df_g, "propano": df_p}


def main():
    print("=" * 60)
    print("ACTUALIZACION DE DATOS: COMBUSTIBLES MIEM (Gasoil, Propano)")
    print("=" * 60)
    
    df_raw = leer_excel()
    
    print(f"\n[INFO] Registros crudos:")
    print(f"  Gasoil: {len(df_raw['gasoil'])} registros")
    print(f"  Propano: {len(df_raw['propano'])} registros")
    
    # Procesar Gasoil
    print("\n[INFO] Procesando Gasoil...")
    df_gasoil = df_raw["gasoil"].copy()
    df_gasoil = validar_fechas_solo_nulas(df_gasoil)
    
    if ID_VARIABLE_GASOIL is None or ID_PAIS_GASOIL is None:
        print("[ERROR] ID_VARIABLE_GASOIL e ID_PAIS_GASOIL deben estar configurados.")
    else:
        print(f"[INFO] Actualizando Gasoil (id_variable={ID_VARIABLE_GASOIL}, id_pais={ID_PAIS_GASOIL})...")
        insertar_en_bd_unificado(ID_VARIABLE_GASOIL, ID_PAIS_GASOIL, df_gasoil, DB_NAME)
    
    # Procesar Propano (si está configurado)
    if ID_VARIABLE_PROPANO is not None and ID_PAIS_PROPANO is not None:
        print("\n[INFO] Procesando Propano...")
        df_propano = df_raw["propano"].copy()
        df_propano = validar_fechas_solo_nulas(df_propano)
        
        print(f"[INFO] Actualizando Propano (id_variable={ID_VARIABLE_PROPANO}, id_pais={ID_PAIS_PROPANO})...")
        insertar_en_bd_unificado(ID_VARIABLE_PROPANO, ID_PAIS_PROPANO, df_propano, DB_NAME)
    else:
        print("\n[INFO] Propano no está configurado. Agregar ID_VARIABLE_PROPANO e ID_PAIS_PROPANO cuando esté en maestro_database.xlsx")
    
    print(f"\n[OK] Proceso completado")


if __name__ == "__main__":
    main()
