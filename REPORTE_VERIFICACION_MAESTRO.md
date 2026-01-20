# REPORTE DE VERIFICACIÓN: Scripts vs Tabla Maestro

**Fecha:** $(date)  
**Total Scripts Analizados:** 12  
**Total Registros en BD:** 11

---

## RESUMEN EJECUTIVO

### Estado General
- ✅ **Scripts OK:** 7 scripts coinciden correctamente con la BD
- ⚠️ **Problemas Encontrados:** 5 scripts con discrepancias
- 🔴 **IDs Duplicados:** 2 IDs usados por múltiples scripts
- ⚠️ **IDs en BD sin Script:** 2 registros

---

## TABLA COMPARATIVA COMPLETA

| ID BD | Nombre en BD | Script | ID Script | Nombre en Script | Estado |
|-------|--------------|--------|-----------|-----------------|--------|
| 1 | Precio novillo hacienda (INAC) – USD/4ta balanza | `novillo_hacienda.py` | 1 | Precio novillo hacienda (INAC) – USD/4ta balanza | ✅ OK |
| 2 | Exportación leche en polvo entera – INALE | `leche_polvo_entera.py` | 2 | Exportación leche en polvo entera – INALE | ✅ OK |
| 2 | Exportación leche en polvo entera – INALE | `carne_exportacion.py` | 2 | Carne | 🔴 **CONFLICTO** |
| 3 | Exportación queso – INALE | `queso_export.py` | 3 | Exportación queso – INALE | ✅ OK |
| 4 | Precio al productor de leche – INALE | - | - | - | ⚠️ **SIN SCRIPT** |
| 5 | Precio exportacion carne (INAC) | `precio_leche_productor.py` | 5 | Precio al productor de leche – INALE | 🔴 **CONFLICTO** |
| 5 | Precio exportacion carne (INAC) | `celulosa_pulp.py` | 5 | Índice de precios de celulosa (INSEE - Francia) | 🔴 **CONFLICTO** |
| 5 | Precio exportacion carne (INAC) | `ipc.py` | 5 | IPC general - Total País (Base Octubre 2022=100) | 🔴 **CONFLICTO** |
| 6 | Tipo de cambio USD/UYU (promedio compra-venta) | `tipo_cambio_usd.py` | 6 | Tipo de cambio USD/UYU (promedio compra-venta) | ✅ OK |
| 7 | Tipo de cambio EUR/UYU (promedio compra-venta) | `tipo_cambio_eur.py` | 7 | Tipo de cambio EUR/UYU (promedio compra-venta) | ✅ OK |
| 8 | Precio soja - Banco Mundial (CMO Historical Data) | `precio_soja_wb.py` | 8 | Precio soja - Banco Mundial (CMO Historical Data) | ✅ OK |
| 9 | Precio arroz - Banco Mundial (CMO Historical Data) | `precio_arroz_wb.py` | 9 | Precio arroz - Banco Mundial (CMO Historical Data) | ✅ OK |
| 10 | Precio trigo - Banco Mundial (CMO Historical Data) | `precio_trigo_wb.py` | 10 | Precio trigo - Banco Mundial (CMO Historical Data) | ✅ OK |
| 11 | IPC | - | - | - | ⚠️ **SIN SCRIPT** |

---

## PROBLEMAS DETECTADOS

### 1. IDs DUPLICADOS EN SCRIPTS

#### ID 2 - Duplicado
- **Scripts afectados:**
  - `leche_polvo_entera.py` (ID 2) ✅ Correcto
  - `carne_exportacion.py` (ID 2) 🔴 Incorrecto

- **Problema:** `carne_exportacion.py` usa ID 2, pero en la BD el ID 2 corresponde a "Exportación leche en polvo entera – INALE"

- **Recomendación:** 
  - Cambiar `carne_exportacion.py` para usar **ID 5** (que corresponde a "Precio exportacion carne (INAC)" en la BD)
  - Actualizar el nombre en el script de "Carne" a "Precio exportacion carne (INAC)"

#### ID 5 - Triplicado
- **Scripts afectados:**
  - `precio_leche_productor.py` (ID 5) 🔴 Debería ser ID 4
  - `celulosa_pulp.py` (ID 5) 🔴 No corresponde a ningún registro en BD
  - `ipc.py` (ID 5) 🔴 Debería ser ID 11

- **Problemas:**
  1. `precio_leche_productor.py`: El script dice "Precio al productor de leche – INALE" pero usa ID 5, cuando en BD el ID 5 es "Precio exportacion carne (INAC)" y el ID 4 es "Precio al productor de leche – INALE"
  2. `celulosa_pulp.py`: No existe registro en BD para celulosa. El script debería usar un ID nuevo o el registro debe crearse en BD.
  3. `ipc.py`: El script dice "IPC general..." pero usa ID 5, cuando en BD el ID 11 es "IPC"

- **Recomendaciones:**
  1. Cambiar `precio_leche_productor.py` para usar **ID 4**
  2. Para `celulosa_pulp.py`: 
     - Opción A: Asignar un nuevo ID (ej: 12) y crear el registro en BD
     - Opción B: Si no se usa, eliminar o desactivar el script
  3. Cambiar `ipc.py` para usar **ID 11** y actualizar el nombre a "IPC" (o mantener el nombre completo si es preferido)

---

### 2. REGISTROS EN BD SIN SCRIPT CORRESPONDIENTE

#### ID 4: Precio al productor de leche – INALE
- **Estado:** Existe en BD pero no tiene script correspondiente
- **Observación:** El script `precio_leche_productor.py` debería usar este ID
- **Recomendación:** Cambiar `precio_leche_productor.py` para usar ID 4

#### ID 11: IPC
- **Estado:** Existe en BD pero el script `ipc.py` usa ID 5
- **Recomendación:** Cambiar `ipc.py` para usar ID 11

---

## RECOMENDACIONES DE CORRECCIÓN

### Prioridad ALTA (Correcciones Críticas)

1. **`carne_exportacion.py`**
   ```python
   # Cambiar de:
   "id": 2,
   "nombre": "Carne",
   
   # A:
   "id": 5,
   "nombre": "Precio exportacion carne (INAC)",
   ```

2. **`precio_leche_productor.py`**
   ```python
   # Cambiar de:
   "id": 5,
   
   # A:
   "id": 4,
   ```

3. **`ipc.py`**
   ```python
   # Cambiar de:
   "id": 5,
   "nombre": "IPC general - Total País (Base Octubre 2022=100)",
   
   # A:
   "id": 11,
   "nombre": "IPC",  # O mantener el nombre completo si se prefiere
   ```

### Prioridad MEDIA (Decisión Requerida)

4. **`celulosa_pulp.py`**
   - **Opción A:** Asignar nuevo ID (ej: 12) y crear registro en BD
   - **Opción B:** Si no se usa, eliminar o comentar el script
   - **Recomendación:** Verificar si este script se está utilizando actualmente

---

## SCRIPTS QUE ESTÁN CORRECTOS (No Requieren Cambios)

✅ `novillo_hacienda.py` (ID 1)  
✅ `leche_polvo_entera.py` (ID 2)  
✅ `queso_export.py` (ID 3)  
✅ `tipo_cambio_usd.py` (ID 6)  
✅ `tipo_cambio_eur.py` (ID 7)  
✅ `precio_soja_wb.py` (ID 8)  
✅ `precio_arroz_wb.py` (ID 9)  
✅ `precio_trigo_wb.py` (ID 10)  

---

## CHECKLIST DE CORRECCIÓN

- [ ] Actualizar `carne_exportacion.py`: ID 2 → ID 5, nombre "Carne" → "Precio exportacion carne (INAC)"
- [ ] Actualizar `precio_leche_productor.py`: ID 5 → ID 4
- [ ] Actualizar `ipc.py`: ID 5 → ID 11, nombre a "IPC" (o mantener completo)
- [ ] Decidir qué hacer con `celulosa_pulp.py` (asignar nuevo ID o eliminar)
- [ ] Ejecutar verificación nuevamente después de las correcciones

---

## NOTAS ADICIONALES

1. **Nombres con caracteres especiales:** Algunos nombres tienen guiones largos (—) que pueden aparecer como caracteres especiales. Verificar que los nombres coincidan exactamente.

2. **Fuentes:** Algunos scripts pueden tener diferencias menores en el campo "fuente" que no se verificaron en este reporte. Se recomienda una revisión adicional.

3. **Campo "mercado":** Los scripts actualizados recientemente (soja, arroz, trigo) ya incluyen el campo "mercado". Los scripts más antiguos pueden necesitar actualización.

---

**Fin del Reporte**
