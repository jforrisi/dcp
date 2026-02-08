# Análisis Detallado: Pendiente de Migración

## 🔍 RESUMEN EJECUTIVO

**Estado General**: La migración de estructura está completa, pero hay **2 áreas críticas** que requieren atención:

1. **Scripts de actualización**: ~15 scripts tienen llamadas incorrectas a `preparar_datos_maestro_precios()` en `main()`
2. **Backend**: 15+ queries en 5 archivos que aún usan `maestro_id`

---

## 📋 PARTE 1: SCRIPTS DE ACTUALIZACIÓN

### Problema Identificado

**Doble problema en ~15 scripts**:

1. **Llamadas incorrectas en `main()`**: Pasan `maestro_id` a `preparar_datos_maestro_precios()` cuando deberían pasar el DataFrame sin procesar
2. **`insertar_en_bd()` no actualizada**: Todavía usa `WHERE maestro_id = ?` en lugar de obtener FKs y usar `id_variable` e `id_pais`

```python
# ❌ INCORRECTO (actual en main()):
df_precios = preparar_datos_maestro_precios(df_raw, MAESTRO_XXX["id"])

# ✅ CORRECTO (debe ser):
df_precios = df_raw  # Pasar sin procesar

# ❌ INCORRECTO (actual en insertar_en_bd()):
cursor.execute("SELECT fecha FROM maestro_precios WHERE maestro_id = ?", (maestro_id,))

# ✅ CORRECTO (debe ser):
# 1. Obtener FKs
cursor.execute("SELECT id_variable, id_pais FROM maestro WHERE id = ?", (maestro_id,))
row = cursor.fetchone()
id_variable, id_pais = row[0], row[1]

# 2. Preparar datos
df_precios_final = preparar_datos_maestro_precios(df_precios, id_variable, id_pais)

# 3. Usar FKs en queries
cursor.execute("SELECT fecha FROM maestro_precios WHERE id_variable = ? AND id_pais = ?", 
               (id_variable, id_pais))
```

### Scripts Afectados

#### precios/update/productos/ (7 archivos)
1. ✅ `novillo_hacienda.py` - **YA CORREGIDO**
2. ❌ `carne_exportacion.py` - Línea 380
3. ❌ `celulosa_pulp.py` - Línea 482
4. ❌ `leche_polvo_entera.py` - Línea 560
5. ❌ `precio_arroz_wb.py` - Línea 650
6. ❌ `precio_leche_productor.py` - Línea 534
7. ❌ `precio_soja_wb.py` - Línea 652
8. ❌ `precio_trigo_wb.py` - Línea 650
9. ❌ `queso_export.py` - Línea 559

#### precios/update/servicios/ (6 archivos)
1. ❌ `arquitectura.py` - Línea 495
2. ❌ `bookkeeping.py` - Línea 495
3. ❌ `contabilidad.py` - Línea 495
4. ❌ `ingenieria.py` - Línea 495
5. ❌ `servicios_no_tradicionales.py` - Línea 414
6. ❌ `software.py` - Línea 496

#### macro/update/ (12 archivos)
1. ✅ `ipc_multipais.py` - **YA CORREGIDO**
2. ❌ `ipc.py` - Línea 666
3. ❌ `ipc_paraguay.py` - Línea 587
4. ❌ `nxr_argy.py` - Línea 635
5. ❌ `nxr_argy_cargar_historico.py` - Línea 368
6. ❌ `nxr_bcch_multipais.py` - Línea 498 (dentro de loop)
7. ❌ `nxr_bra.py` - Línea 445
8. ❌ `nxr_chile.py` - Línea 511
9. ❌ `nxr_peru.py` - Línea 476
10. ❌ `salario_real.py` - Línea 557
11. ❌ `tipo_cambio_eur.py` - Línea 608
12. ❌ `tipo_cambio_usd.py` - Línea 669

**Total**: 15 scripts necesitan corrección en `main()`

### Solución

Para cada script, hacer **2 cambios**:

#### Cambio 1: En `main()` - Pasar DataFrame sin procesar
```python
# ANTES:
df_precios = preparar_datos_maestro_precios(df_raw, MAESTRO_XXX["id"])

# DESPUÉS:
df_precios = df_raw  # Pasar sin procesar, insertar_en_bd() lo procesará
```

#### Cambio 2: En `insertar_en_bd()` - Obtener FKs y usarlas
```python
# Después de insertar en maestro, agregar:
# Obtener id_variable e id_pais desde maestro
cursor.execute("SELECT id_variable, id_pais FROM maestro WHERE id = ?", (maestro_id,))
row = cursor.fetchone()
if not row or not row[0] or not row[1]:
    print(f"[ERROR] maestro.id={maestro_id} no tiene id_variable e id_pais. No se pueden insertar precios.")
    return

id_variable = row[0]
id_pais = row[1]
print(f"[INFO] Obtenidas FKs: id_variable={id_variable}, id_pais={id_pais}")

# Preparar datos con FKs si no están ya preparados
if "id_variable" not in df_precios.columns or "id_pais" not in df_precios.columns:
    df_precios = preparar_datos_maestro_precios(df_precios, id_variable, id_pais)

# Cambiar query de verificación:
# ANTES:
cursor.execute("SELECT fecha FROM maestro_precios WHERE maestro_id = ?", (maestro_id,))

# DESPUÉS:
cursor.execute("SELECT fecha FROM maestro_precios WHERE id_variable = ? AND id_pais = ?", 
               (id_variable, id_pais))
```

---

## 📋 PARTE 2: BACKEND - QUERIES PENDIENTES

### backend/app/routers/prices.py

#### Función: `get_price_variation()` (Línea ~250)
**Queries a actualizar:**
- Línea 298: `WHERE maestro_id = ? AND fecha <= ?`
- Línea 318: `WHERE maestro_id = ?` (última fecha)

**Impacto**: ALTO - Endpoint crítico para variaciones de precios

**Patrón de actualización:**
```python
# Obtener FKs primero
query_fks = "SELECT id_variable, id_pais FROM maestro WHERE id = ?"
fks_result = execute_query_single(query_fks, (product_id,))
if not fks_result or not fks_result.get('id_variable') or not fks_result.get('id_pais'):
    # Manejar error o continuar sin este producto
    continue

# Usar FKs en queries
query_prices = """
    SELECT fecha, valor
    FROM maestro_precios
    WHERE id_variable = ? AND id_pais = ? AND fecha <= ?
    ORDER BY fecha ASC
"""
params = (fks_result['id_variable'], fks_result['id_pais'], fecha_hasta)
```

#### Función: `export_variations_dcp()` (Línea ~500)
**Queries a actualizar:**
- Línea 543: `WHERE maestro_id = ? AND fecha <= ?`

**Impacto**: MEDIO - Exportación a Excel

#### Función: `get_product_stats()` (Línea ~956)
**Queries a actualizar:**
- Línea 969: `where_clause = "WHERE maestro_id = ?"`
- Línea 987: `WHERE maestro_id = ?` (subquery para precio_actual)
- Línea 1010: `WHERE maestro_id = ? AND fecha >= ? AND fecha <= ?` (first query)
- Línea 1015: `WHERE maestro_id = ? AND fecha >= ? AND fecha <= ?` (last query)

**Impacto**: MEDIO - Estadísticas de productos

#### Función: `export_multiple_products_prices()` (Línea ~1020)
**Queries a actualizar:**
- Líneas 1061-1096: Múltiples queries con `JOIN maestro m ON mp.maestro_id = m.id` y `WHERE mp.maestro_id IN (...)`

**Impacto**: MEDIO - Exportación a Excel

**Total en prices.py**: ~8 queries en 4 funciones

---

### backend/app/routers/dcp.py

#### Función: `get_macro_series()` (Línea 152)
**Query a actualizar:**
- Línea 177: `WHERE maestro_id = ? AND fecha >= ? AND fecha <= ?`

**Impacto**: CRÍTICO - Usado por múltiples funciones (get_dcp_products, get_dcp_indices, etc.)

**Nota**: Esta función es llamada con `maestro_id` de series macro (TC_USD_ID, TC_EUR_ID, IPC_ID). Necesita obtener FKs primero.

#### Función: `get_dcp_products()` (Línea ~214)
**Query a actualizar:**
- Línea 325: `WHERE maestro_id = ? AND fecha <= ?`

**Impacto**: ALTO - Endpoint principal de DCP

#### Función: `export_dcp_indices()` (Línea ~600)
**Query a actualizar:**
- Línea 675: `WHERE maestro_id = ? AND fecha <= ?`

**Impacto**: MEDIO - Exportación a Excel

**Total en dcp.py**: 3 queries en 3 funciones

---

### backend/app/routers/cotizaciones.py

#### Función: `get_cotizaciones()` (Línea 24)
**Query a actualizar:**
- Línea 112: `WHERE maestro_id = ? AND DATE(fecha) >= DATE(?) AND DATE(fecha) <= DATE(?)`

**Impacto**: ALTO - Endpoint principal de cotizaciones

**Nota**: Esta función itera sobre múltiples productos. Necesita obtener FKs para cada uno.

#### Función: `get_cotizaciones_products()` (Línea ~300)
**Query a actualizar:**
- Línea 353: `WHERE maestro_id = ? AND fecha >= ? AND fecha <= ?`

**Impacto**: MEDIO - Exportación a Excel

**Total en cotizaciones.py**: 2 queries en 2 funciones

---

### backend/app/routers/inflacion_dolares.py

#### Función: `get_ipc_by_country()` (Línea ~40)
**Query a actualizar:**
- Línea 63: `WHERE maestro_id = ? AND fecha >= ? AND fecha <= ?`

**Impacto**: ALTO - Usado para cálculos de inflación

#### Función: `get_tc_by_country()` (Línea 98)
**Query a actualizar:**
- Línea 123: `WHERE maestro_id = ? AND DATE(fecha) >= DATE(?) AND DATE(fecha) <= DATE(?)`

**Impacto**: ALTO - Usado para cálculos de inflación

**Total en inflacion_dolares.py**: 2 queries en 2 funciones

---

### backend/app/routers/admin/maestro.py

#### Función: `delete_maestro()` (Línea 275)
**Query a actualizar:**
- Línea 284: `SELECT COUNT(*) as count FROM maestro_precios WHERE maestro_id = ?`

**Impacto**: BAJO - Solo para admin, verificación antes de eliminar

**Total en admin/maestro.py**: 1 query en 1 función

---

## 📊 RESUMEN DE QUERIES PENDIENTES

| Archivo | Funciones | Queries | Impacto |
|---------|-----------|---------|---------|
| `prices.py` | 4 | ~8 | ALTO |
| `dcp.py` | 3 | 3 | CRÍTICO |
| `cotizaciones.py` | 2 | 2 | ALTO |
| `inflacion_dolares.py` | 2 | 2 | ALTO |
| `admin/maestro.py` | 1 | 1 | BAJO |
| **TOTAL** | **12** | **~16** | - |

---

## 🎯 PRIORIZACIÓN

### Prioridad CRÍTICA (hacer primero)
1. ✅ `dcp.py` - `get_macro_series()` - Usado por múltiples endpoints
2. ✅ `prices.py` - `get_price_variation()` - Endpoint principal
3. ✅ `cotizaciones.py` - `get_cotizaciones()` - Endpoint principal
4. ✅ `inflacion_dolares.py` - Ambas funciones - Cálculos críticos

### Prioridad ALTA
5. `dcp.py` - `get_dcp_products()` - Endpoint principal
6. `prices.py` - `get_product_stats()` - Estadísticas
7. `prices.py` - `export_variations_dcp()` - Exportación

### Prioridad MEDIA
8. `prices.py` - `export_multiple_products_prices()` - Exportación
9. `dcp.py` - `export_dcp_indices()` - Exportación
10. `cotizaciones.py` - `get_cotizaciones_products()` - Exportación

### Prioridad BAJA
11. `admin/maestro.py` - `delete_maestro()` - Solo admin

---

## 🔧 PATRÓN DE ACTUALIZACIÓN ESTÁNDAR

### Para queries simples (un producto):
```python
# 1. Obtener FKs
query_fks = "SELECT id_variable, id_pais FROM maestro WHERE id = ?"
fks_result = execute_query_single(query_fks, (product_id,))

if not fks_result or not fks_result.get('id_variable') or not fks_result.get('id_pais'):
    # Manejar error: retornar vacío, continuar, o abortar según contexto
    return jsonify([])  # o continue, o abort(404)

id_variable = fks_result['id_variable']
id_pais = fks_result['id_pais']

# 2. Usar FKs en query
query = """
    SELECT fecha, valor
    FROM maestro_precios
    WHERE id_variable = ? AND id_pais = ? AND fecha BETWEEN ? AND ?
    ORDER BY fecha ASC
"""
params = (id_variable, id_pais, fecha_desde, fecha_hasta)
results = execute_query(query, params)
```

### Para queries con múltiples productos:
```python
# 1. Obtener FKs para todos
placeholders = ",".join("?" * len(product_ids))
query_fks = f"SELECT id, id_variable, id_pais FROM maestro WHERE id IN ({placeholders})"
fks_results = execute_query(query_fks, tuple(product_ids))

# 2. Crear mapeo
fks_map = {}
for row in fks_results:
    if row.get('id_variable') and row.get('id_pais'):
        fks_map[row['id']] = (row['id_variable'], row['id_pais'])

# 3. Construir condiciones WHERE
fks_conditions = []
fks_params = []
for id_var, id_pais in fks_map.values():
    fks_conditions.append("(id_variable = ? AND id_pais = ?)")
    fks_params.extend([id_var, id_pais])

fks_where = " OR ".join(fks_conditions)

# 4. Query final
query = f"""
    SELECT mp.id_variable, mp.id_pais, mp.fecha, mp.valor, m.id, m.nombre
    FROM maestro_precios mp
    JOIN maestro m ON mp.id_variable = m.id_variable AND mp.id_pais = m.id_pais
    WHERE ({fks_where}) AND mp.fecha BETWEEN ? AND ?
    ORDER BY m.id, mp.fecha ASC
"""
params = tuple(fks_params) + (fecha_desde, fecha_hasta)
```

### Para loops sobre productos:
```python
for product in products:
    product_id = product['id']
    
    # Obtener FKs para este producto
    query_fks = "SELECT id_variable, id_pais FROM maestro WHERE id = ?"
    fks_result = execute_query_single(query_fks, (product_id,))
    
    if not fks_result or not fks_result.get('id_variable') or not fks_result.get('id_pais'):
        continue  # Saltar este producto
    
    # Query con FKs
    query = "SELECT fecha, valor FROM maestro_precios WHERE id_variable = ? AND id_pais = ? AND ..."
    params = (fks_result['id_variable'], fks_result['id_pais'], ...)
    results = execute_query(query, params)
```

---

## ⚠️ CONSIDERACIONES ESPECIALES

### 1. Compatibilidad Híbrida
- Si un `maestro.id` no tiene `id_variable` e `id_pais`, el sistema debe manejar esto gracefully
- Opciones:
  - Retornar `[]` o `{}` vacío
  - Continuar con el siguiente producto
  - Retornar error 404/400 según contexto

### 2. Performance
- Para queries con múltiples productos, obtener todas las FKs en una sola query (usar `IN`)
- Evitar loops de queries individuales cuando sea posible

### 3. Validación
- Siempre verificar que `fks_result` no sea `None`
- Verificar que ambos `id_variable` e `id_pais` no sean `None`
- Manejar casos donde el producto existe pero no tiene FKs

---

## 📝 CHECKLIST DE IMPLEMENTACIÓN

### Scripts de Actualización
- [ ] Corregir 15 scripts: cambiar llamadas en `main()` para pasar DataFrame sin procesar
- [ ] Verificar que `insertar_en_bd()` en cada script obtiene FKs correctamente
- [ ] Probar al menos 2-3 scripts para validar el patrón

### Backend - Prioridad Crítica
- [ ] `dcp.py` - `get_macro_series()` (línea 177)
- [ ] `prices.py` - `get_price_variation()` (líneas 298, 318)
- [ ] `cotizaciones.py` - `get_cotizaciones()` (línea 112)
- [ ] `inflacion_dolares.py` - `get_ipc_by_country()` (línea 63)
- [ ] `inflacion_dolares.py` - `get_tc_by_country()` (línea 123)

### Backend - Prioridad Alta
- [ ] `dcp.py` - `get_dcp_products()` (línea 325)
- [ ] `prices.py` - `get_product_stats()` (líneas 969, 987, 1010, 1015)

### Backend - Prioridad Media/Baja
- [ ] `prices.py` - `export_variations_dcp()` (línea 543)
- [ ] `prices.py` - `export_multiple_products_prices()` (líneas 1061-1096)
- [ ] `dcp.py` - `export_dcp_indices()` (línea 675)
- [ ] `cotizaciones.py` - `get_cotizaciones_products()` (línea 353)
- [ ] `admin/maestro.py` - `delete_maestro()` (línea 284)

---

## 🚀 ESTIMACIÓN DE ESFUERZO

- **Scripts**: ~2-3 horas (cambios simples y repetitivos)
- **Backend crítico**: ~2-3 horas (4 funciones)
- **Backend resto**: ~3-4 horas (8 funciones)
- **Testing**: ~2 horas
- **Total estimado**: ~9-12 horas

---

## 💡 RECOMENDACIÓN

1. **Empezar con backend crítico** (dcp.py, prices.py variaciones, cotizaciones.py) - estos son los endpoints más usados
2. **Luego scripts** - son cambios simples pero numerosos
3. **Finalmente backend restante** - exportaciones y funciones menos críticas
