# Instrucciones para Completar la Actualización de Scripts

## Estado Actual

✅ **Scripts automáticos completados**: 22 scripts fueron actualizados automáticamente con cambios básicos (se comentaron las líneas problemáticas).

✅ **Scripts ya actualizados manualmente**:
- `precios/update/servicios/software.py` - ✅ Completo
- `precios/update/servicios/bookkeeping.py` - ✅ Completo  
- `precios/update/productos/carne_exportacion.py` - ✅ Completo

## Scripts que Necesitan Revisión Manual

Los siguientes scripts fueron actualizados automáticamente pero necesitan completarse manualmente:

### Productos (8 scripts):
1. `precios/update/productos/celulosa_pulp.py`
2. `precios/update/productos/leche_polvo_entera.py`
3. `precios/update/productos/novillo_hacienda.py`
4. `precios/update/productos/precio_arroz_wb.py`
5. `precios/update/productos/precio_leche_productor.py`
6. `precios/update/productos/precio_soja_wb.py`
7. `precios/update/productos/precio_trigo_wb.py`
8. `precios/update/productos/queso_export.py`

### Servicios (1 script):
9. `precios/update/servicios/servicios_no_tradicionales.py`

### Macro (13 scripts):
10. `macro/update/combustibles_miem.py`
11. `macro/update/ipc.py`
12. `macro/update/ipc_multipais.py`
13. `macro/update/ipc_paraguay.py`
14. `macro/update/nxr_argy.py`
15. `macro/update/nxr_argy_cargar_historico.py`
16. `macro/update/nxr_bcch_multipais.py`
17. `macro/update/nxr_bra.py`
18. `macro/update/nxr_chile.py`
19. `macro/update/nxr_peru.py`
20. `macro/update/salario_real.py`
21. `macro/update/tipo_cambio_eur.py`
22. `macro/update/tipo_cambio_usd.py`

## Pasos para Completar Cada Script

Para cada script, sigue estos pasos:

### 1. Agregar ID_VARIABLE e ID_PAIS al inicio

Busca la sección de configuración (después de los imports) y agrega:

```python
# Configuración de base de datos
# NOTA: Estos valores deben existir en maestro_database.xlsx
# Si no existen, agregar el registro al Excel y ejecutar migracion_maestro_simplificar.py
ID_VARIABLE = None  # TODO: Obtener desde maestro_database.xlsx
ID_PAIS = None  # TODO: Obtener desde maestro_database.xlsx
```

**Para obtener los valores**:
- Consulta el Excel `maestro_database.xlsx`
- Busca el registro correspondiente a este script
- Anota los valores de `id_variable` e `id_pais`

### 2. Actualizar la función `insertar_en_bd()`

Reemplaza la función completa con esta versión (o usa el helper):

**Opción A: Usar el helper (recomendado)**

```python
from precios.update._helpers import insertar_en_bd_helper

def insertar_en_bd(id_variable: int, id_pais: int, df_precios: pd.DataFrame) -> None:
    """Inserta los datos en la base de datos SQLite."""
    insertar_en_bd_helper(
        db_name=DB_NAME,
        id_variable=id_variable,
        id_pais=id_pais,
        df_precios=df_precios,
        preparar_datos_func=preparar_datos_maestro_precios  # Si tienes esta función
    )
```

**Opción B: Implementación completa (si necesitas personalización)**

```python
def insertar_en_bd(id_variable: int, id_pais: int, df_precios: pd.DataFrame) -> None:
    """Inserta los datos en la base de datos SQLite.
    
    Args:
        id_variable: ID de la variable (FK a tabla variables)
        id_pais: ID del país (FK a tabla pais_grupo)
        df_precios: DataFrame con columnas FECHA y VALOR
    """
    print("\n[INFO] Insertando datos en la base de datos...")
    print(f"[INFO] Usando id_variable={id_variable}, id_pais={id_pais}")

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    try:
        # Verificar que id_variable e id_pais existen en sus tablas de referencia
        cursor.execute("SELECT id_variable FROM variables WHERE id_variable = ?", (id_variable,))
        if not cursor.fetchone():
            print(f"[ERROR] id_variable={id_variable} no existe en la tabla 'variables'.")
            print(f"[ERROR] Debes agregar este registro al Excel 'maestro_database.xlsx' y ejecutar la migración.")
            return
        
        cursor.execute("SELECT id_pais FROM pais_grupo WHERE id_pais = ?", (id_pais,))
        if not cursor.fetchone():
            print(f"[ERROR] id_pais={id_pais} no existe en la tabla 'pais_grupo'.")
            print(f"[ERROR] Debes agregar este registro al Excel 'maestro_database.xlsx' y ejecutar la migración.")
            return

        # Verificar que el registro existe en maestro
        cursor.execute(
            "SELECT id_variable, id_pais FROM maestro WHERE id_variable = ? AND id_pais = ?",
            (id_variable, id_pais)
        )
        if not cursor.fetchone():
            print(f"[ERROR] No existe registro en 'maestro' para id_variable={id_variable}, id_pais={id_pais}.")
            print(f"[ERROR] Debes agregar este registro al Excel 'maestro_database.xlsx' y ejecutar la migración.")
            return

        # Preparar datos con FKs
        df_precios = preparar_datos_maestro_precios(df_precios, id_variable, id_pais)

        # Eliminar registros existentes para esta id_variable y id_pais
        cursor.execute(
            "DELETE FROM maestro_precios WHERE id_variable = ? AND id_pais = ?",
            (id_variable, id_pais)
        )
        registros_eliminados = cursor.rowcount
        if registros_eliminados > 0:
            print(f"[INFO] Se eliminaron {registros_eliminados} registros antiguos de 'maestro_precios'")

        # Insertar todos los precios nuevos
        if not df_precios.empty:
            print(f"[INFO] Insertando {len(df_precios)} registros en 'maestro_precios'...")
            df_precios.to_sql("maestro_precios", conn, if_exists="append", index=False)
            print(f"[OK] Insertados {len(df_precios)} registro(s) en tabla 'maestro_precios'")
        else:
            print(f"[WARN] No hay datos para insertar en maestro_precios")

        conn.commit()
        print(f"\n[OK] Datos insertados exitosamente en '{DB_NAME}'")
    except Exception as exc:
        conn.rollback()
        print(f"[ERROR] Error al insertar datos: {exc}")
        raise
    finally:
        conn.close()
```

### 3. Actualizar la función `main()`

Busca la llamada a `insertar_en_bd()` y actualízala:

**Antes:**
```python
df_maestro = pd.DataFrame([MAESTRO_DATA])
insertar_en_bd(df_maestro, df_precios)
```

**Después:**
```python
# Verificar que ID_VARIABLE e ID_PAIS están configurados
if ID_VARIABLE is None or ID_PAIS is None:
    print("\n[ERROR] ID_VARIABLE e ID_PAIS deben estar configurados en el script.")
    print("   Consulta maestro_database.xlsx o la base de datos para obtener los valores correctos.")
    return

insertar_en_bd(ID_VARIABLE, ID_PAIS, df_precios)
```

### 4. Eliminar referencias a `df_maestro` y `MAESTRO_DATA`

- Elimina o comenta el diccionario `MAESTRO_*` si existe
- Actualiza funciones que usan `df_maestro` para que no lo requieran
- Actualiza `generar_excel_prueba()` y `mostrar_resumen()` si es necesario

## Ejemplo Completo

Ver `precios/update/productos/carne_exportacion.py` como referencia completa.

## Verificación

Después de actualizar cada script:

1. ✅ Verifica que `ID_VARIABLE` e `ID_PAIS` están configurados
2. ✅ Verifica que `insertar_en_bd()` acepta `id_variable` e `id_pais` como parámetros
3. ✅ Verifica que `main()` pasa `ID_VARIABLE` e `ID_PAIS` a `insertar_en_bd()`
4. ✅ Ejecuta el script y verifica que funciona correctamente

## Notas Importantes

- **NO** insertes en `maestro` desde los scripts. La tabla `maestro` debe estar sincronizada con `maestro_database.xlsx`.
- Si un registro no existe en `maestro`, agrégalo al Excel y ejecuta `migracion_maestro_simplificar.py`.
- Los backups de los scripts originales están en archivos `.backup` (puedes eliminarlos después de verificar que todo funciona).
