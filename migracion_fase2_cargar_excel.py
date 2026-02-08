"""
Fase 2: Cargar Datos desde Excel
=================================
Carga los datos desde maestro_database.xlsx a las tablas de referencia creadas en Fase 1.
"""

import sqlite3
import os
import pandas as pd

DB_NAME = "series_tiempo.db"
EXCEL_FILE = "maestro_database.xlsx"


def cargar_datos_excel():
    """
    Carga datos desde maestro_database.xlsx a las tablas de referencia.
    """
    print("=" * 80)
    print("FASE 2: Cargar Datos desde Excel")
    print("=" * 80)
    
    # Verificar que existe el Excel
    if not os.path.exists(EXCEL_FILE):
        print(f"[ERROR] Archivo '{EXCEL_FILE}' no encontrado.")
        return False
    
    # Verificar que existe la BD
    if not os.path.exists(DB_NAME):
        print(f"[ERROR] Base de datos '{DB_NAME}' no encontrada.")
        print("Por favor, ejecuta primero 'migracion_fase1_crear_tablas.py'.")
        return False
    
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    try:
        # Leer todas las hojas del Excel
        print(f"\n[INFO] Leyendo '{EXCEL_FILE}'...")
        excel_data = pd.read_excel(EXCEL_FILE, sheet_name=None)
        print(f"[OK] Excel leído. Hojas encontradas: {list(excel_data.keys())}")
        
        # 1. Cargar pais_grupo
        print("\n[INFO] Cargando datos en 'pais_grupo'...")
        if 'pais_grupo' in excel_data:
            df_pais = excel_data['pais_grupo']
            # Estructura: columna 0 = nombre país, columna 'id_pais' = código
            # Usar índices de columna para evitar problemas con encoding
            col_nombre = df_pais.columns[0]  # Primera columna: nombre del país
            
            # Buscar columna id_pais (puede estar en diferentes posiciones)
            if 'id_pais' in df_pais.columns:
                col_id = 'id_pais'
            else:
                col_id = df_pais.columns[1]  # Segunda columna como fallback
            
            registros_pais = 0
            for _, row in df_pais.iterrows():
                try:
                    nombre_pais = str(row[col_nombre]).strip()
                    id_pais = int(row[col_id]) if pd.notna(row[col_id]) else None
                    
                    if id_pais is None:
                        continue
                    
                    cursor.execute("""
                        INSERT OR REPLACE INTO pais_grupo (id_pais, nombre_pais_grupo)
                        VALUES (?, ?)
                    """, (id_pais, nombre_pais))
                    registros_pais += 1
                except Exception as e:
                    print(f"[WARN] Error al insertar país {row.get(col_id, 'N/A')}: {e}")
            print(f"[OK] {registros_pais} registros insertados/actualizados en 'pais_grupo'")
        else:
            print("[WARN] Hoja 'pais_grupo' no encontrada en Excel")
        
        # 2. Cargar familia
        print("\n[INFO] Cargando datos en 'familia'...")
        if 'familia' in excel_data:
            df_familia = excel_data['familia']
            df_familia = df_familia[['id_familia', 'nombre_familia']].dropna()
            registros_familia = 0
            for _, row in df_familia.iterrows():
                try:
                    cursor.execute("""
                        INSERT OR REPLACE INTO familia (id_familia, nombre_familia)
                        VALUES (?, ?)
                    """, (int(row['id_familia']), str(row['nombre_familia']).strip()))
                    registros_familia += 1
                except Exception as e:
                    print(f"[WARN] Error al insertar familia {row['id_familia']}: {e}")
            print(f"[OK] {registros_familia} registros insertados/actualizados en 'familia'")
        else:
            print("[WARN] Hoja 'familia' no encontrada en Excel")
        
        # 3. Cargar sub_familia (con FK a familia)
        print("\n[INFO] Cargando datos en 'sub_familia'...")
        if 'sub_familia' in excel_data:
            df_sub_familia = excel_data['sub_familia']
            # Verificar si tiene id_familia, si no, intentar inferirlo
            if 'id_familia' not in df_sub_familia.columns:
                # Buscar en Sheet1_old la relación
                if 'Sheet1_old' in excel_data:
                    sheet1 = excel_data['Sheet1_old']
                    # Crear mapeo desde Sheet1_old si es posible
                    print("[INFO] Intentando inferir id_familia desde Sheet1_old...")
            
            df_sub_familia = df_sub_familia[['id_sub_familia', 'nombre_sub_familia']].dropna()
            registros_sub_familia = 0
            for _, row in df_sub_familia.iterrows():
                try:
                    # Intentar obtener id_familia desde Sheet1_old si existe
                    id_familia = None
                    if 'Sheet1_old' in excel_data:
                        sheet1 = excel_data['Sheet1_old']
                        match = sheet1[sheet1['id_sub_familia'] == row['id_sub_familia']]
                        if len(match) > 0 and 'id_familia' in match.columns:
                            id_familia_val = match.iloc[0]['id_familia']
                            if pd.notna(id_familia_val):
                                id_familia = int(id_familia_val)
                    
                    cursor.execute("""
                        INSERT OR REPLACE INTO sub_familia (id_sub_familia, nombre_sub_familia, id_familia)
                        VALUES (?, ?, ?)
                    """, (int(row['id_sub_familia']), str(row['nombre_sub_familia']).strip(), id_familia))
                    registros_sub_familia += 1
                except Exception as e:
                    print(f"[WARN] Error al insertar sub_familia {row['id_sub_familia']}: {e}")
            print(f"[OK] {registros_sub_familia} registros insertados/actualizados en 'sub_familia'")
        else:
            print("[WARN] Hoja 'sub_familia' no encontrada en Excel")
        
        # 4. Cargar variables (con FK a sub_familia)
        print("\n[INFO] Cargando datos en 'variables'...")
        if 'variables' in excel_data:
            df_variables = excel_data['variables']
            df_variables = df_variables[['id_variable', 'id_nombre_variable', 'id_sub_familia', 
                                       'nominal_o_real', 'moneda']].dropna(subset=['id_variable', 'id_nombre_variable'])
            registros_variables = 0
            for _, row in df_variables.iterrows():
                try:
                    cursor.execute("""
                        INSERT OR REPLACE INTO variables 
                        (id_variable, id_nombre_variable, id_sub_familia, nominal_o_real, moneda)
                        VALUES (?, ?, ?, ?, ?)
                    """, (
                        int(row['id_variable']),
                        str(row['id_nombre_variable']).strip(),
                        int(row['id_sub_familia']) if pd.notna(row['id_sub_familia']) else None,
                        str(row['nominal_o_real']).strip() if pd.notna(row['nominal_o_real']) else None,
                        str(row['moneda']).strip() if pd.notna(row['moneda']) else None
                    ))
                    registros_variables += 1
                except Exception as e:
                    print(f"[WARN] Error al insertar variable {row['id_variable']}: {e}")
            print(f"[OK] {registros_variables} registros insertados/actualizados en 'variables'")
        else:
            print("[WARN] Hoja 'variables' no encontrada en Excel")
        
        # 5. Cargar graph
        print("\n[INFO] Cargando datos en 'graph'...")
        if 'graph' in excel_data:
            df_graph = excel_data['graph']
            df_graph = df_graph[['id_graph', 'nombre_graph', 'selector']].dropna(subset=['id_graph'])
            registros_graph = 0
            for _, row in df_graph.iterrows():
                try:
                    cursor.execute("""
                        INSERT OR REPLACE INTO graph (id_graph, nombre_graph, selector)
                        VALUES (?, ?, ?)
                    """, (
                        int(row['id_graph']),
                        str(row['nombre_graph']).strip(),
                        str(row['selector']).strip() if pd.notna(row['selector']) else None
                    ))
                    registros_graph += 1
                except Exception as e:
                    print(f"[WARN] Error al insertar graph {row['id_graph']}: {e}")
            print(f"[OK] {registros_graph} registros insertados/actualizados en 'graph'")
        else:
            print("[WARN] Hoja 'graph' no encontrada en Excel")
        
        # 6. Cargar filtros_graph_pais
        print("\n[INFO] Cargando datos en 'filtros_graph_pais'...")
        if 'filtros_graph_pais' in excel_data:
            df_filtros = excel_data['filtros_graph_pais']
            # Estructura: id_graph, id_pais (FKs a graph.id_graph y pais_grupo.id_pais)
            if 'id_graph' not in df_filtros.columns or 'id_pais' not in df_filtros.columns:
                print("[ERROR] Columnas 'id_graph' o 'id_pais' no encontradas en filtros_graph_pais")
            else:
                # Limpiar tabla primero para reemplazar completamente
                cursor.execute("DELETE FROM filtros_graph_pais")
                registros_eliminados = cursor.rowcount
                if registros_eliminados > 0:
                    print(f"[INFO] Se eliminaron {registros_eliminados} registros antiguos de 'filtros_graph_pais'")
                
                df_filtros = df_filtros[['id_graph', 'id_pais']].dropna(subset=['id_graph', 'id_pais'])
                # Eliminar duplicados (mismo id_graph + id_pais)
                df_filtros = df_filtros.drop_duplicates(subset=['id_graph', 'id_pais'])
                
                registros_filtros = 0
                for _, row in df_filtros.iterrows():
                    try:
                        id_graph = int(row['id_graph']) if pd.notna(row['id_graph']) else None
                        id_pais = int(row['id_pais']) if pd.notna(row['id_pais']) else None
                        if id_graph and id_pais:
                            cursor.execute("""
                                INSERT INTO filtros_graph_pais (id_graph, id_pais)
                                VALUES (?, ?)
                            """, (id_graph, id_pais))
                            registros_filtros += 1
                    except Exception as e:
                        print(f"[WARN] Error al insertar filtro graph {row.get('id_graph', 'N/A')}: {e}")
                print(f"[OK] {registros_filtros} registros insertados/actualizados en 'filtros_graph_pais'")
        else:
            print("[WARN] Hoja 'filtros_graph_pais' no encontrada en Excel")
        
        conn.commit()
        
        # Verificar datos cargados
        print("\n" + "=" * 80)
        print("[VERIFICACIÓN] Resumen de datos cargados:")
        print("=" * 80)
        
        cursor.execute("SELECT COUNT(*) FROM pais_grupo")
        print(f"  pais_grupo: {cursor.fetchone()[0]} registros")
        
        cursor.execute("SELECT COUNT(*) FROM familia")
        print(f"  familia: {cursor.fetchone()[0]} registros")
        
        cursor.execute("SELECT COUNT(*) FROM sub_familia")
        print(f"  sub_familia: {cursor.fetchone()[0]} registros")
        
        cursor.execute("SELECT COUNT(*) FROM variables")
        print(f"  variables: {cursor.fetchone()[0]} registros")
        
        cursor.execute("SELECT COUNT(*) FROM graph")
        print(f"  graph: {cursor.fetchone()[0]} registros")
        
        cursor.execute("SELECT COUNT(*) FROM filtros_graph_pais")
        print(f"  filtros_graph_pais: {cursor.fetchone()[0]} registros")
        
        print("\n" + "=" * 80)
        print("[OK] FASE 2 COMPLETADA: Datos cargados exitosamente desde Excel")
        print("=" * 80)
        
        return True
        
    except Exception as e:
        conn.rollback()
        print(f"\n[ERROR] Error al cargar datos: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        conn.close()


if __name__ == "__main__":
    cargar_datos_excel()
