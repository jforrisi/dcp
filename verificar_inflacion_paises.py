"""Verificar datos de inflación (IPC) para Perú, Brasil y México."""
import sqlite3
from datetime import datetime

conn = sqlite3.connect('series_tiempo.db')
cursor = conn.cursor()

print("=" * 80)
print("VERIFICACIÓN DE DATOS DE INFLACIÓN (IPC)")
print("=" * 80)

# Buscar series de inflación/IPC para Perú, Brasil y México
paises_buscar = ['Perú', 'Peru', 'Brasil', 'Brazil', 'México', 'Mexico', 'MXN', 'BRL', 'PEN']

print("\nBuscando series de inflación/IPC en la base de datos...")
print("-" * 80)

# Buscar en el nombre o categoría
query = """
    SELECT id, nombre, tipo, periodicidad, activo, fuente, categoria, unidad
    FROM maestro
    WHERE (
        nombre LIKE '%inflación%' 
        OR nombre LIKE '%inflacion%'
        OR nombre LIKE '%IPC%'
        OR nombre LIKE '%índice de precios%'
        OR nombre LIKE '%indice de precios%'
        OR categoria LIKE '%inflación%'
        OR categoria LIKE '%inflacion%'
        OR categoria LIKE '%IPC%'
    )
    AND (
        nombre LIKE '%Perú%' OR nombre LIKE '%Peru%' OR nombre LIKE '%PEN%'
        OR nombre LIKE '%Brasil%' OR nombre LIKE '%Brazil%' OR nombre LIKE '%BRL%'
        OR nombre LIKE '%México%' OR nombre LIKE '%Mexico%' OR nombre LIKE '%MXN%'
    )
    ORDER BY nombre
"""

cursor.execute(query)
resultados = cursor.fetchall()

if resultados:
    print(f"\n✓ Se encontraron {len(resultados)} series de inflación:")
    print("=" * 80)
    
    for row in resultados:
        product_id = row[0]
        nombre = row[1]
        tipo = row[2]
        periodicidad = row[3]
        activo = row[4]
        fuente = row[5]
        categoria = row[6]
        unidad = row[7] if len(row) > 7 else None
        
        print(f"\nID {product_id}: {nombre}")
        print(f"  Tipo: {tipo}, Periodicidad: {periodicidad}, Activo: {activo}")
        if fuente:
            print(f"  Fuente: {fuente}")
        if categoria:
            print(f"  Categoría: {categoria}")
        if unidad:
            print(f"  Unidad: {unidad}")
        
        # Verificar datos en maestro_precios
        cursor.execute("SELECT COUNT(*) FROM maestro_precios WHERE maestro_id = ?", (product_id,))
        count = cursor.fetchone()[0]
        
        if count > 0:
            cursor.execute("""
                SELECT MIN(fecha) as primera, MAX(fecha) as ultima, COUNT(*) as total
                FROM maestro_precios 
                WHERE maestro_id = ?
            """, (product_id,))
            fecha_info = cursor.fetchone()
            print(f"  ✓ Datos: {fecha_info[2]} registros")
            print(f"  ✓ Rango: {fecha_info[0]} a {fecha_info[1]}")
            
            # Mostrar algunos valores recientes
            cursor.execute("""
                SELECT fecha, valor 
                FROM maestro_precios 
                WHERE maestro_id = ? 
                ORDER BY fecha DESC 
                LIMIT 3
            """, (product_id,))
            recent = cursor.fetchall()
            print(f"  Últimos 3 valores:")
            for f, v in recent:
                print(f"    {f}: {v}")
        else:
            print(f"  ❌ Sin datos en maestro_precios")
else:
    print("\n❌ No se encontraron series de inflación para Perú, Brasil o México")

# Buscar también todas las series de inflación/IPC sin filtrar por país
print("\n" + "=" * 80)
print("TODAS LAS SERIES DE INFLACIÓN/IPC EN LA BASE DE DATOS")
print("=" * 80)

query_todas = """
    SELECT id, nombre, tipo, periodicidad, activo, fuente, categoria
    FROM maestro
    WHERE (
        nombre LIKE '%inflación%' 
        OR nombre LIKE '%inflacion%'
        OR nombre LIKE '%IPC%'
        OR nombre LIKE '%índice de precios%'
        OR nombre LIKE '%indice de precios%'
        OR categoria LIKE '%inflación%'
        OR categoria LIKE '%inflacion%'
        OR categoria LIKE '%IPC%'
    )
    ORDER BY nombre
"""

cursor.execute(query_todas)
todas = cursor.fetchall()

if todas:
    print(f"\nTotal de series de inflación/IPC: {len(todas)}")
    for row in todas:
        product_id = row[0]
        nombre = row[1]
        activo = row[4]
        
        cursor.execute("SELECT COUNT(*) FROM maestro_precios WHERE maestro_id = ?", (product_id,))
        count = cursor.fetchone()[0]
        
        status = "✓" if count > 0 else "❌"
        print(f"  {status} ID {product_id}: {nombre[:70]}... | activo={activo} | registros={count}")
else:
    print("\nNo se encontraron series de inflación/IPC en la base de datos")

conn.close()
print("\n" + "=" * 80)
print("VERIFICACIÓN COMPLETA")
print("=" * 80)
