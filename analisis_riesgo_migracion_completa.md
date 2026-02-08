# Análisis de Riesgo: Migración Completa vs. Opción Híbrida

## 📊 Alcance del Cambio

### Scripts de Actualización que Necesitarían Modificación: **28 scripts**

#### Macro (13 scripts):
- `macro/update/combustibles_miem.py`
- `macro/update/ipc.py`
- `macro/update/ipc_multipais.py`
- `macro/update/ipc_paraguay.py`
- `macro/update/nxr_argy.py`
- `macro/update/nxr_argy_cargar_historico.py`
- `macro/update/nxr_bcch_multipais.py`
- `macro/update/nxr_bra.py`
- `macro/update/nxr_chile.py`
- `macro/update/nxr_peru.py`
- `macro/update/salario_real.py`
- `macro/update/tipo_cambio_eur.py`
- `macro/update/tipo_cambio_usd.py`

#### Precios - Productos (9 scripts):
- `precios/update/productos/carne_exportacion.py`
- `precios/update/productos/celulosa_pulp.py`
- `precios/update/productos/leche_polvo_entera.py`
- `precios/update/productos/novillo_hacienda.py`
- `precios/update/productos/precio_arroz_wb.py`
- `precios/update/productos/precio_leche_productor.py`
- `precios/update/productos/precio_soja_wb.py`
- `precios/update/productos/precio_trigo_wb.py`
- `precios/update/productos/queso_export.py`

#### Precios - Servicios (6 scripts):
- `precios/update/servicios/arquitectura.py`
- `precios/update/servicios/bookkeeping.py`
- `precios/update/servicios/contabilidad.py`
- `precios/update/servicios/ingenieria.py`
- `precios/update/servicios/servicios_no_tradicionales.py`
- `precios/update/servicios/software.py`

### Backend que Necesitaría Actualización: **4 routers**

1. **`backend/app/routers/prices.py`**
   - Queries: `SELECT ... FROM maestro WHERE ...`
   - JOINs: `JOIN maestro m ON mp.maestro_id = m.id`
   - Usa: `id`, `nombre`, `tipo`, `unidad`, `categoria`, `fuente`, `periodicidad`, `activo`

2. **`backend/app/routers/dcp.py`**
   - Query: `SELECT moneda FROM maestro WHERE id = ?`
   - Query: `SELECT id, nombre, periodicidad, fuente, moneda, nominal_real FROM maestro WHERE ...`
   - Usa: `id`, `moneda`, `nominal_real`

3. **`backend/app/routers/cotizaciones.py`**
   - Query: `SELECT id, nombre, fuente, unidad, categoria, pais FROM maestro WHERE ...`
   - Query: `SELECT id, nombre, fuente, unidad, categoria, periodicidad, pais FROM maestro WHERE ...`
   - Usa: `id`, `nombre`, `fuente`, `unidad`, `categoria`, `pais`, `periodicidad`, `activo`, `es_cotizacion`

4. **`backend/app/routers/inflacion_dolares.py`**
   - Queries indirectas a través de otros módulos

---

## ⚠️ RIESGOS DE MIGRACIÓN COMPLETA

### 1. **Riesgo de Ruptura del Sistema** 🔴 ALTO
- **28 scripts** deben modificarse simultáneamente
- Si **1 script falla**, puede romper el proceso de actualización automática
- **Backend** debe actualizarse al mismo tiempo
- Si backend y scripts no están sincronizados → **datos inconsistentes**

### 2. **Riesgo de Pérdida de Datos** 🔴 ALTO
- Migración de datos existentes requiere mapeo complejo:
  - `nombre` → `variables.id_nombre_variable` (búsqueda por texto)
  - `pais` → `pais_grupo.id_pais_grupo` (búsqueda por texto)
  - Si el mapeo falla → **datos huérfanos o perdidos**

### 3. **Riesgo de Testing Incompleto** 🟡 MEDIO
- **28 scripts** × múltiples escenarios = **cientos de casos de prueba**
- Difícil probar todos los casos antes de producción
- Un bug en un script puede pasar desapercibido hasta que se ejecute en producción

### 4. **Riesgo de Rollback Complejo** 🔴 ALTO
- Si algo falla, rollback requiere:
  - Revertir cambios en **28 scripts**
  - Revertir cambios en **4 routers**
  - Restaurar base de datos desde backup
  - **Tiempo de inactividad** del sistema

### 5. **Riesgo de Inconsistencias Temporales** 🟡 MEDIO
- Durante la migración:
  - Algunos scripts pueden usar estructura antigua
  - Otros pueden usar estructura nueva
  - **Datos inconsistentes** en la base de datos

### 6. **Riesgo de Complejidad de Mapeo** 🟡 MEDIO
- Cada script debe:
  1. Buscar `id_nombre_variable` en tabla `variables` (por nombre)
  2. Buscar `id_region` en tabla `pais_grupo` (por nombre)
  3. Si no existe, crear registros en tablas de referencia
  4. Insertar en `maestro` con FKs correctas
- **Lógica compleja** que puede fallar en casos edge

---

## ✅ VENTAJAS DE OPCIÓN HÍBRIDA

### 1. **Migración Gradual** 🟢
- Agregar tablas de referencia **sin tocar estructura actual**
- Agregar columnas opcionales a `maestro` (`id_nombre_variable`, `id_region`)
- **Llenar FKs gradualmente** cuando sea posible
- **Sistema sigue funcionando** con estructura antigua

### 2. **Testing Incremental** 🟢
- Probar migración de **1 script a la vez**
- Verificar que datos se migran correctamente
- **Rollback fácil** si algo falla (solo revertir 1 script)

### 3. **Compatibilidad Total** 🟢
- Backend puede usar **ambas estructuras**:
  - Si FKs existen → usar JOINs con nuevas tablas
  - Si FKs no existen → usar estructura antigua
- **No rompe funcionalidad existente**

### 4. **Menor Riesgo de Pérdida de Datos** 🟢
- Datos antiguos **no se tocan**
- Solo se agregan nuevas columnas (opcionales)
- Si migración falla → **datos originales intactos**

### 5. **Rollback Simple** 🟢
- Si algo falla:
  - Solo revertir cambios en scripts modificados
  - Columnas opcionales pueden quedar NULL
  - **Sistema sigue funcionando**

---

## 📋 PLAN RECOMENDADO: OPCIÓN HÍBRIDA

### Fase 1: Preparación (Sin Riesgo)
1. ✅ Crear nuevas tablas de referencia (`variables`, `pais_grupo`, `familia`, `sub_familia`)
2. ✅ Cargar datos desde Excel a tablas de referencia
3. ✅ Agregar columnas opcionales a `maestro`:
   - `id_nombre_variable INTEGER` (FK opcional)
   - `id_region INTEGER` (FK opcional)
   - `link VARCHAR(500)` (opcional)

**Riesgo**: ⚪ CERO - No toca datos existentes

### Fase 2: Migración de Datos Existentes (Riesgo Bajo)
1. Script de migración que:
   - Lee `maestro` actual
   - Busca `nombre` en `variables.id_nombre_variable`
   - Busca `pais` en `pais_grupo.nombre_pais_grupo`
   - Actualiza `id_nombre_variable` y `id_region` en `maestro`
   - **Si no encuentra match → deja NULL** (sistema sigue funcionando)

**Riesgo**: 🟡 BAJO - Solo lectura/escritura de columnas nuevas

### Fase 3: Actualización de Backend (Riesgo Medio)
1. Modificar queries para usar JOINs cuando FKs existan:
   ```sql
   SELECT m.*, v.moneda, v.nominal_o_real, pg.nombre_pais_grupo
   FROM maestro m
   LEFT JOIN variables v ON m.id_nombre_variable = v.id_variable
   LEFT JOIN pais_grupo pg ON m.id_region = pg.id_pais_grupo
   WHERE m.id = ?
   ```
2. Si FKs son NULL → usar valores antiguos de `maestro.moneda`, `maestro.nominal_real`

**Riesgo**: 🟡 MEDIO - Backend puede manejar ambos casos

### Fase 4: Migración de Scripts (Riesgo Alto, pero Gradual)
1. **Migrar 1 script a la vez** (empezar por los más simples)
2. Cada script:
   - Busca/crea en `variables` y `pais_grupo`
   - Inserta en `maestro` con FKs
   - **Mantiene compatibilidad**: también puede insertar sin FKs si falla
3. **Probar cada script** antes de pasar al siguiente

**Riesgo**: 🟡 MEDIO - Solo 1 script a la vez, rollback fácil

### Fase 5: Validación y Limpieza (Riesgo Bajo)
1. Verificar que todos los registros tienen FKs
2. Una vez validado → hacer FKs obligatorios (opcional)
3. Eliminar columnas antiguas si se desea (opcional, más adelante)

---

## 🎯 CONCLUSIÓN

### Migración Completa: 🔴 **MUY RIESGOSA**
- **28 scripts** + **4 routers** modificados simultáneamente
- Alto riesgo de ruptura del sistema
- Rollback complejo
- Testing exhaustivo requerido
- **Tiempo estimado**: 2-3 semanas de desarrollo + 1 semana de testing

### Opción Híbrida: 🟢 **RECOMENDADA**
- Migración gradual, script por script
- Sistema sigue funcionando durante migración
- Rollback simple
- Testing incremental
- **Tiempo estimado**: 1 semana de preparación + migración gradual según necesidad

### Recomendación Final: **OPCIÓN HÍBRIDA**

La opción híbrida permite:
- ✅ **Cero downtime**
- ✅ **Riesgo controlado**
- ✅ **Rollback fácil**
- ✅ **Testing incremental**
- ✅ **Compatibilidad total con sistema actual**

---

## 📝 PRÓXIMOS PASOS (Si Aceptas Opción Híbrida)

1. Crear script de migración de estructura (Fase 1)
2. Crear script de migración de datos existentes (Fase 2)
3. Actualizar backend para soportar ambas estructuras (Fase 3)
4. Crear template para migrar scripts gradualmente (Fase 4)

¿Procedemos con la opción híbrida?
