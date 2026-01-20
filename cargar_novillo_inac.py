"""
Script para cargar datos de precios de novillo hacienda desde INAC
Siguiendo el flujo obligatorio del README:
1. Estructurar datos
2. Validar fechas
3. Generar Excel de prueba
4. Solicitar confirmación
5. Insertar en BD solo si confirma
"""

import pandas as pd
import sqlite3
from datetime import datetime
import os

# Configuración
URL_EXCEL_INAC = "https://www.inac.uy/innovaportal/file/10953/1/precios-hacienda-mensual.xlsx"
DB_NAME = "series_tiempo.db"
EXCEL_PRUEBA_NAME = "prueba_novillo_hacienda.xlsx"

# Datos del maestro según especificación del usuario
MAESTRO_NOVILLO = {
    "id": 1,
    "nombre": "Precio novillo hacienda (INAC) – USD/4ta balanza",
    "tipo": "P",
    "fuente": "INAC – serie mensual precios de hacienda",
    "periodicidad": "W",  # Usuario especificó "W" aunque los datos son mensuales
    "unidad": "USD/kg",
    "categoria": None,
    "activo": True
}


def crear_base_datos():
    """Crea la base de datos SQLite y las tablas según el esquema del README"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # Crear tabla maestro
    cursor.execute("""
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
    """)
    
    # Crear tabla maestro_precios
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS maestro_precios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            maestro_id INTEGER NOT NULL,
            fecha DATE NOT NULL,
            valor NUMERIC(18, 6) NOT NULL,
            FOREIGN KEY (maestro_id) REFERENCES maestro(id)
        )
    """)
    
    # Crear índices recomendados
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_maestro_precios_maestro_id 
        ON maestro_precios (maestro_id)
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_maestro_precios_fecha 
        ON maestro_precios (fecha)
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_maestro_precios_maestro_fecha 
        ON maestro_precios (maestro_id, fecha)
    """)
    
    conn.commit()
    conn.close()
    print(f"✓ Base de datos '{DB_NAME}' creada/verificada con éxito")


def descargar_y_procesar_excel():
    """Descarga el Excel de INAC y crea el DataFrame novillo_hacienda"""
    print(f"\n📥 Descargando Excel de INAC...")
    
    try:
        # Leer Excel: hoja NOVILLO, columna A (fecha) y Q (precio), desde fila 13
        novillo_hacienda = pd.read_excel(
            URL_EXCEL_INAC,
            sheet_name="NOVILLO",
            skiprows=12,  # Para que la fila 13 de Excel sea la primera
            usecols="A,Q",  # Columna A (fecha) y Q (precio)
            header=None
        )
        
        # Renombrar columnas
        novillo_hacienda.columns = ["FECHA", "NOVILLO_HACIENDA"]
        
        # Eliminar filas con fecha nula (comunes al final de archivos Excel)
        novillo_hacienda = novillo_hacienda.dropna(subset=["FECHA"])
        
        print(f"✓ Datos descargados: {len(novillo_hacienda)} registros")
        print(f"\n📊 Primeros datos:")
        print(novillo_hacienda.head())
        print(f"\n📊 Últimos datos:")
        print(novillo_hacienda.tail())
        
        return novillo_hacienda
        
    except Exception as e:
        print(f"❌ Error al descargar/procesar Excel: {e}")
        raise


def validar_fechas(df):
    """Valida que todas las fechas sean válidas (OBLIGATORIO según README)"""
    print(f"\n🔍 Validando fechas...")
    
    # Intentar convertir fechas
    fechas_invalidas = []
    fechas_validas = []
    
    for idx, fecha in enumerate(df["FECHA"]):
        try:
            # Intentar parsear como fecha
            if pd.isna(fecha):
                fechas_invalidas.append((idx + 13, fecha, "Fecha nula"))
            else:
                fecha_parseada = pd.to_datetime(fecha, errors='coerce')
                if pd.isna(fecha_parseada):
                    fechas_invalidas.append((idx + 13, fecha, "No se pudo parsear"))
                else:
                    fechas_validas.append(fecha_parseada)
        except Exception as e:
            fechas_invalidas.append((idx + 13, fecha, str(e)))
    
    if fechas_invalidas:
        print(f"❌ Se encontraron {len(fechas_invalidas)} fechas inválidas:")
        for fila_excel, fecha, motivo in fechas_invalidas[:10]:  # Mostrar solo las primeras 10
            print(f"   Fila Excel {fila_excel}: {fecha} - {motivo}")
        if len(fechas_invalidas) > 10:
            print(f"   ... y {len(fechas_invalidas) - 10} más")
        raise ValueError("Hay fechas inválidas. No se puede continuar.")
    
    # Convertir todas las fechas a datetime
    df["FECHA"] = pd.to_datetime(df["FECHA"])
    
    print(f"✓ Todas las {len(fechas_validas)} fechas son válidas")
    print(f"   Rango: {df['FECHA'].min()} a {df['FECHA'].max()}")
    
    return df


def preparar_datos_maestro_precios(df_novillo, maestro_id):
    """Prepara el DataFrame para maestro_precios"""
    df_precios = df_novillo.copy()
    df_precios["maestro_id"] = maestro_id
    df_precios = df_precios[["maestro_id", "FECHA", "NOVILLO_HACIENDA"]]
    df_precios.columns = ["maestro_id", "fecha", "valor"]
    
    # Eliminar filas con valor nulo
    df_precios = df_precios.dropna(subset=["valor"])
    
    return df_precios


def generar_excel_prueba(df_maestro, df_precios):
    """Genera el archivo Excel de prueba (OBLIGATORIO según README)"""
    print(f"\n📝 Generando archivo Excel de prueba...")
    
    excel_path = os.path.join(os.getcwd(), EXCEL_PRUEBA_NAME)
    
    with pd.ExcelWriter(excel_path, engine='openpyxl') as writer:
        df_maestro.to_excel(writer, sheet_name="maestro", index=False)
        df_precios.to_excel(writer, sheet_name="maestro_precios", index=False)
    
    print(f"✓ Archivo Excel generado: {excel_path}")
    print(f"   - Hoja 'maestro': {len(df_maestro)} fila(s)")
    print(f"   - Hoja 'maestro_precios': {len(df_precios)} fila(s)")
    
    return excel_path


def mostrar_resumen(df_maestro, df_precios):
    """Muestra resumen de los datos que se van a insertar"""
    print("\n" + "="*60)
    print("RESUMEN DE DATOS A INSERTAR")
    print("="*60)
    
    print("\n📋 TABLA: maestro")
    print("-" * 60)
    print(df_maestro.to_string(index=False))
    
    print(f"\n📊 TABLA: maestro_precios")
    print("-" * 60)
    print(f"Total de registros: {len(df_precios)}")
    print(f"\nPrimeros 5 registros:")
    print(df_precios.head().to_string(index=False))
    print(f"\nÚltimos 5 registros:")
    print(df_precios.tail().to_string(index=False))
    print(f"\nRango de fechas: {df_precios['fecha'].min()} a {df_precios['fecha'].max()}")
    print(f"Valores: min={df_precios['valor'].min():.2f}, max={df_precios['valor'].max():.2f}, promedio={df_precios['valor'].mean():.2f}")
    print("="*60)


def insertar_en_bd(df_maestro, df_precios):
    """Inserta los datos en la base de datos SQLite"""
    print(f"\n💾 Insertando datos en la base de datos...")
    
    conn = sqlite3.connect(DB_NAME)
    
    try:
        # Insertar en maestro
        df_maestro.to_sql("maestro", conn, if_exists="append", index=False)
        print(f"✓ Insertados {len(df_maestro)} registro(s) en tabla 'maestro'")
        
        # Insertar en maestro_precios
        df_precios.to_sql("maestro_precios", conn, if_exists="append", index=False)
        print(f"✓ Insertados {len(df_precios)} registro(s) en tabla 'maestro_precios'")
        
        conn.commit()
        print(f"\n✅ Datos insertados exitosamente en '{DB_NAME}'")
        
    except Exception as e:
        conn.rollback()
        print(f"❌ Error al insertar datos: {e}")
        raise
    finally:
        conn.close()


def main():
    """Función principal que ejecuta el flujo completo"""
    print("="*60)
    print("CARGA DE DATOS: NOVILLO HACIENDA (INAC)")
    print("="*60)
    
    # Paso 1: Crear base de datos
    crear_base_datos()
    
    # Paso 2: Descargar y procesar Excel
    novillo_hacienda = descargar_y_procesar_excel()
    
    # Paso 3: Validar fechas (OBLIGATORIO)
    novillo_hacienda = validar_fechas(novillo_hacienda)
    
    # Paso 4: Preparar datos para maestro
    df_maestro = pd.DataFrame([MAESTRO_NOVILLO])
    
    # Paso 5: Preparar datos para maestro_precios
    df_precios = preparar_datos_maestro_precios(novillo_hacienda, MAESTRO_NOVILLO["id"])
    
    # Paso 6: Generar Excel de prueba (OBLIGATORIO)
    excel_path = generar_excel_prueba(df_maestro, df_precios)
    
    # Paso 7: Mostrar resumen
    mostrar_resumen(df_maestro, df_precios)
    
    # Paso 8: Solicitar confirmación (OBLIGATORIO)
    print(f"\n⚠️  IMPORTANTE: Revisá el archivo Excel generado antes de continuar:")
    print(f"   {excel_path}")
    
    respuesta = input("\n¿Confirmás que los datos son correctos y querés insertarlos en la BD? (sí/no): ").strip().lower()
    
    if respuesta in ["sí", "si", "yes", "y", "s"]:
        # Paso 9: Insertar en BD solo si confirma
        insertar_en_bd(df_maestro, df_precios)
    else:
        print("\n❌ Inserción cancelada por el usuario. Los datos NO fueron insertados en la BD.")
        print("   Podés revisar el Excel y ejecutar el script nuevamente cuando estés listo.")


if __name__ == "__main__":
    main()
