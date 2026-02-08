# Estado de Migración: maestro_precios a id_variable + id_pais

## ✅ COMPLETADO

### Fases 1-4: Migración de Base de Datos y Helpers
- ✅ **Fase 1**: Script `migracion_maestro_precios_fase1_renombrar_columna.py` creado para renombrar `id_nombre_variable` a `id_variable`
- ✅ **Fase 2**: Script `migracion_maestro_precios_fase2_actualizar_estructura.py` creado para nueva estructura de `maestro_precios`
- ✅ **Fase 3**: Script `migracion_maestro_precios_fase3_actualizar_maestro.py` creado para actualizar `maestro` desde Excel
- ✅ **Fase 4**: `helpers/maestro_helper.py` actualizado:
  - Agregada función `obtener_fks_desde_maestro(maestro_id)`
  - `insertar_maestro_con_fks()` ahora usa `id_variable` en lugar de `id_nombre_variable`

### Fase 5: Actualización de CREATE TABLE en Scripts
- ✅ **26 de 28 scripts** actualizados con nueva estructura de `maestro_precios`:
  - Todos los scripts en `precios/update/productos/` (9 archivos)
  - Todos los scripts en `precios/update/servicios/` (6 archivos)
  - La mayoría de scripts en `macro/update/` (11 archivos)
- ✅ Índices actualizados: `idx_maestro_precios_id_variable`, `idx_maestro_precios_id_pais`, `idx_maestro_precios_variable_pais_fecha`

### Fase 6-7: Actualización de Funciones en Scripts
- ✅ **1 script completo** (`macro/update/ipc_multipais.py`):
  - `preparar_datos_maestro_precios()` actualizado para usar `id_variable` e `id_pais`
  - `insertar_en_bd()` actualizado para obtener FKs desde `maestro` y usarlas
- ⚠️ **27 scripts pendientes** de actualizar funciones `preparar_datos_maestro_precios()` e `insertar_en_bd()`

### Fase 12-13: Scripts de Migración
- ✅ `migracion_fase4_migrar_datos.py` actualizado para usar `id_variable`
- ✅ `migracion_fase6_template_script.py` actualizado con ejemplos de nueva estructura

### Backend - Parcial
- ✅ `backend/app/routers/prices.py`:
  - `get_products()` actualizado: `id_nombre_variable` → `id_variable`
  - `get_product_prices()` actualizado para usar `id_variable` e `id_pais`
- ⚠️ `get_multiple_products_prices()` y otras funciones en `prices.py` aún pendientes
- ⚠️ `backend/app/routers/dcp.py` pendiente
- ⚠️ `backend/app/routers/cotizaciones.py` pendiente (parcialmente actualizado por usuario)
- ⚠️ `backend/app/routers/inflacion_dolares.py` pendiente

## ⚠️ PENDIENTE

### Scripts de Actualización (27 archivos)
Necesitan actualizar:
1. **`preparar_datos_maestro_precios()`**: Cambiar parámetro de `maestro_id: int` a `id_variable: int, id_pais: int`
2. **`insertar_en_bd()`**: 
   - Obtener `id_variable` e `id_pais` desde `maestro` antes de insertar
   - Cambiar DELETE query: `WHERE maestro_id = ?` → `WHERE id_variable = ? AND id_pais = ?`
   - Llamar `preparar_datos_maestro_precios()` con las FKs

**Archivos pendientes:**
- `precios/update/productos/*.py` (9 archivos)
- `precios/update/servicios/*.py` (6 archivos)
- `macro/update/*.py` (12 archivos, excluyendo `ipc_multipais.py`)

**Patrón a seguir (ver `macro/update/ipc_multipais.py` como ejemplo):**

```python
# 1. Actualizar función preparar_datos_maestro_precios
def preparar_datos_maestro_precios(df: pd.DataFrame, id_variable: int, id_pais: int) -> pd.DataFrame:
    df_precios = df.copy()
    df_precios["id_variable"] = id_variable
    df_precios["id_pais"] = id_pais
    df_precios = df_precios[["id_variable", "id_pais", "Fecha", "Valor"]]
    df_precios.columns = ["id_variable", "id_pais", "fecha", "valor"]
    return df_precios

# 2. Actualizar función insertar_en_bd
def insertar_en_bd(...):
    # ... insertar en maestro ...
    
    # Obtener FKs desde maestro
    cursor.execute("SELECT id_variable, id_pais FROM maestro WHERE id = ?", (maestro_id,))
    row = cursor.fetchone()
    if not row or not row[0] or not row[1]:
        print("[ERROR] maestro.id no tiene id_variable e id_pais")
        return False
    
    id_variable = row[0]
    id_pais = row[1]
    
    # Eliminar registros existentes
    cursor.execute("DELETE FROM maestro_precios WHERE id_variable = ? AND id_pais = ?", 
                   (id_variable, id_pais))
    
    # Preparar datos con FKs
    df_precios_final = preparar_datos_maestro_precios(df_precios_raw, id_variable, id_pais)
    
    # Insertar
    df_precios_final.to_sql("maestro_precios", conn, if_exists="append", index=False)
```

### Backend - Queries Pendientes

**`backend/app/routers/prices.py`:**
- `get_multiple_products_prices()`: Actualizar para usar `id_variable` e `id_pais`
- `get_price_variation()`: Actualizar queries de `maestro_precios`
- `get_price_summary()`: Actualizar queries de `maestro_precios`
- Todas las demás funciones que usan `maestro_precios`

**`backend/app/routers/dcp.py`:**
- `get_product_currency()`: Ya actualizado para usar `id_variable` (verificar)
- `get_macro_series()`: Actualizar queries de `maestro_precios`
- Todas las queries que usan `maestro_precios`

**`backend/app/routers/cotizaciones.py`:**
- Ya parcialmente actualizado por usuario
- Verificar que todas las queries usen `id_variable` e `id_pais`

**`backend/app/routers/inflacion_dolares.py`:**
- Actualizar todas las queries de `maestro_precios`

**Patrón para queries en backend:**

```python
# ANTES:
query = """
    SELECT fecha, valor
    FROM maestro_precios
    WHERE maestro_id = ? AND fecha BETWEEN ? AND ?
"""

# DESPUÉS:
# Primero obtener FKs
query_fks = "SELECT id_variable, id_pais FROM maestro WHERE id = ?"
fks_result = execute_query_single(query_fks, (product_id,))
if not fks_result or not fks_result.get('id_variable') or not fks_result.get('id_pais'):
    return jsonify([])  # No tiene FKs

query = """
    SELECT fecha, valor
    FROM maestro_precios
    WHERE id_variable = ? AND id_pais = ? AND fecha BETWEEN ? AND ?
"""
params = (fks_result['id_variable'], fks_result['id_pais'], fecha_desde, fecha_hasta)
```

## 📋 PRÓXIMOS PASOS

1. **Ejecutar scripts de migración** (en orden):
   ```bash
   python migracion_maestro_precios_fase1_renombrar_columna.py
   python migracion_maestro_precios_fase2_actualizar_estructura.py
   python migracion_maestro_precios_fase3_actualizar_maestro.py
   ```

2. **Actualizar scripts de actualización restantes** (27 archivos):
   - Usar `macro/update/ipc_multipais.py` como plantilla
   - Actualizar `preparar_datos_maestro_precios()` e `insertar_en_bd()` en cada script

3. **Completar actualización del backend**:
   - Actualizar todas las queries en `prices.py`
   - Actualizar `dcp.py`
   - Verificar/completar `cotizaciones.py`
   - Actualizar `inflacion_dolares.py`

4. **Pruebas**:
   - Verificar que los scripts pueden insertar datos
   - Verificar que el backend puede leer datos
   - Probar endpoints del API

## 📝 NOTAS

- La migración es **híbrida**: el sistema puede funcionar con registros que tienen FKs y los que no las tienen
- Si un `maestro.id` no tiene `id_variable` e `id_pais`, los scripts y el backend deben manejar esto gracefully (retornar vacío o error)
- Los datos existentes en `maestro_precios` se perderán al ejecutar Fase 2 (por diseño)
- Después de ejecutar Fase 3, los registros en `maestro` deberían tener `id_variable` e `id_pais` desde el Excel
