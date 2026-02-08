import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent / "series_tiempo.db"

conn = sqlite3.connect(str(DB_PATH))
cursor = conn.cursor()

try:
    # 1. Crear tabla tipo_serie
    print("[INFO] Creando tabla 'tipo_serie'...")
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tipo_serie (
            id_tipo_serie INTEGER PRIMARY KEY,
            nombre_tipo_serie VARCHAR(50) NOT NULL UNIQUE
        )
    """)
    print("[OK] Tabla 'tipo_serie' creada/verificada")
    
    # 2. Poblar tabla con los tipos
    print("[INFO] Poblando tabla 'tipo_serie'...")
    tipos = [
        (1, 'Original'),
        (2, 'Desestacionalizada'),
        (3, 'Tendencia - Ciclo')
    ]
    
    for id_tipo, nombre in tipos:
        cursor.execute("""
            INSERT OR IGNORE INTO tipo_serie (id_tipo_serie, nombre_tipo_serie)
            VALUES (?, ?)
        """, (id_tipo, nombre))
    
    print(f"[OK] {len(tipos)} tipos de serie insertados")
    
    # 3. Agregar columna id_tipo_serie a variables
    print("[INFO] Agregando columna 'id_tipo_serie' a tabla 'variables'...")
    try:
        cursor.execute("""
            ALTER TABLE variables 
            ADD COLUMN id_tipo_serie INTEGER DEFAULT 1
        """)
        print("[OK] Columna 'id_tipo_serie' agregada")
    except sqlite3.OperationalError as e:
        if "duplicate column" in str(e).lower():
            print("[INFO] Columna 'id_tipo_serie' ya existe")
        else:
            raise
    
    # 4. Actualizar todos los registros existentes a 'Original' (id_tipo_serie = 1)
    cursor.execute("UPDATE variables SET id_tipo_serie = 1 WHERE id_tipo_serie IS NULL")
    updated = cursor.rowcount
    print(f"[OK] {updated} registros actualizados a tipo_serie = 1 (Original)")
    
    # 5. Agregar FK constraint (SQLite no soporta ADD CONSTRAINT, pero podemos crear índice)
    print("[INFO] Creando índice para id_tipo_serie...")
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_variables_id_tipo_serie
        ON variables(id_tipo_serie)
    """)
    print("[OK] Índice creado")
    
    conn.commit()
    print("\n[OK] Proceso completado exitosamente")
    
except Exception as e:
    conn.rollback()
    print(f"\n[ERROR] Error: {str(e)}")
    raise
finally:
    conn.close()
