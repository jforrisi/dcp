# Resumen: Scripts de Actualización Pendientes

## Estado Actual

### ✅ Scripts que YA funcionan (no necesitan cambios):
- `precios/update/servicios/software.py` - Usa `id_variable` e `id_pais` directamente
- `precios/update/servicios/bookkeeping.py` - Usa `id_variable` e `id_pais` directamente

### ❌ Scripts que FALLARÁN (necesitan actualización):

#### Scripts de Productos:
1. `precios/update/productos/carne_exportacion.py`
2. `precios/update/productos/celulosa_pulp.py`
3. `precios/update/productos/leche_polvo_entera.py`
4. `precios/update/productos/novillo_hacienda.py`
5. `precios/update/productos/precio_arroz_wb.py`
6. `precios/update/productos/precio_leche_productor.py`
7. `precios/update/productos/precio_soja_wb.py`
8. `precios/update/productos/precio_trigo_wb.py`
9. `precios/update/productos/queso_export.py`

#### Scripts de Servicios:
10. `precios/update/servicios/servicios_no_tradicionales.py`

#### Scripts de Macro:
11. `macro/update/combustibles_miem.py`
12. `macro/update/ipc.py`
13. `macro/update/ipc_multipais.py`
14. `macro/update/ipc_paraguay.py`
15. `macro/update/nxr_argy.py`
16. `macro/update/nxr_argy_cargar_historico.py`
17. `macro/update/nxr_bcch_multipais.py`
18. `macro/update/nxr_bra.py`
19. `macro/update/nxr_chile.py`
20. `macro/update/nxr_peru.py`
21. `macro/update/salario_real.py`
22. `macro/update/tipo_cambio_eur.py`
23. `macro/update/tipo_cambio_usd.py`

## Problema

Estos scripts intentan insertar en `maestro` usando columnas que ya no existen:
- `id` (ya no existe, ahora es PK compuesta `(id_variable, id_pais)`)
- `nombre` (ya no existe, está en `variables.id_nombre_variable`)
- `tipo` (ya no existe)
- `categoria` (ya no existe, está en `variables.categoria`)
- `unidad` (ya no existe)
- `moneda` (ya no existe, está en `variables.moneda`)
- `nominal_real` (ya no existe, está en `variables.nominal_o_real`)

## Solución

**IMPORTANTE**: La tabla `maestro` ahora debe estar sincronizada con el Excel `maestro_database.xlsx`. Los scripts NO deben insertar en `maestro` directamente.

### Cambios necesarios en cada script:

1. **Eliminar la inserción en `maestro`**: Los scripts no deben insertar en `maestro` usando `INSERT OR IGNORE INTO maestro`.

2. **Usar `id_variable` e `id_pais` directamente**: Los scripts deben tener estas constantes definidas al inicio (como `software.py`).

3. **Verificar que el registro existe en `maestro`**: Antes de insertar en `maestro_precios`, verificar que existe el registro en `maestro` con ese `(id_variable, id_pais)`.

4. **Solo insertar en `maestro_precios`**: Los scripts solo deben insertar/actualizar datos en `maestro_precios`.

### Ejemplo de función actualizada:

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
            return
        
        cursor.execute("SELECT id_pais FROM pais_grupo WHERE id_pais = ?", (id_pais,))
        if not cursor.fetchone():
            print(f"[ERROR] id_pais={id_pais} no existe en la tabla 'pais_grupo'.")
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

## Próximos Pasos

1. **Para usar el sistema ahora**: Los scripts modernos (`software.py`, `bookkeeping.py`) funcionarán correctamente. Los scripts antiguos fallarán si intentan ejecutarse.

2. **Para actualizar los scripts antiguos**: Se debe aplicar el patrón de `software.py` a todos los scripts listados arriba.

3. **Workflow recomendado**:
   - Si necesitas agregar una nueva serie, agrégalo al Excel `maestro_database.xlsx`
   - Ejecuta `migracion_maestro_simplificar.py` para actualizar la BD
   - Los scripts de actualización solo insertan en `maestro_precios`
