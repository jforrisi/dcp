# Guía de Migración: Integración de maestro_database.xlsx

Esta guía documenta el proceso de migración híbrida para integrar la estructura normalizada de `maestro_database.xlsx` al sistema existente.

## Resumen

La migración implementa una estructura normalizada con tablas de referencia (`variables`, `pais_grupo`, `familia`, `sub_familia`) mientras mantiene compatibilidad total con la estructura actual. Esto permite una migración gradual y segura sin downtime.

## Arquitectura

### Estructura Actual
- `maestro`: Tabla plana con todos los metadatos
- `maestro_precios`: Observaciones de series de tiempo

### Nueva Estructura (Híbrida)
- `maestro`: Mantiene columnas existentes + nuevas columnas opcionales (FKs)
- `variables`: Metadatos compartidos por variable (moneda, nominal_o_real, sub_familia)
- `pais_grupo`: Países/regiones centralizados
- `familia` → `sub_familia`: Clasificación jerárquica
- `graph` + `filtros_graph_pais`: Configuración para frontend

### Compatibilidad
- Sistema funciona con estructura antigua (sin FKs)
- Sistema funciona con estructura nueva (con FKs)
- Backend usa LEFT JOINs para soportar ambos casos

## Fases de Migración

### Fase 1: Crear Tablas de Referencia ✅
**Archivo**: `migracion_fase1_crear_tablas.py`

Crea las nuevas tablas de referencia sin modificar `maestro`.

**Ejecutar**:
```bash
python migracion_fase1_crear_tablas.py
```

**Validación**: Verificar que todas las tablas se crearon correctamente.

---

### Fase 2: Cargar Datos desde Excel ✅
**Archivo**: `migracion_fase2_cargar_excel.py`

Carga datos desde `maestro_database.xlsx` a las tablas de referencia.

**Ejecutar**:
```bash
python migracion_fase2_cargar_excel.py
```

**Validación**: Verificar que todos los datos del Excel se cargaron.

---

### Fase 3: Agregar Columnas Opcionales ✅
**Archivo**: `migracion_fase3_agregar_columnas.py`

Agrega columnas opcionales a `maestro`:
- `id_nombre_variable` (FK a `variables.id_variable`)
- `id_region` (FK a `pais_grupo.id_pais_grupo`)
- `link` (URL opcional)

**Ejecutar**:
```bash
python migracion_fase3_agregar_columnas.py
```

**Validación**: Verificar que columnas se agregaron y queries existentes siguen funcionando.

---

### Fase 4: Migrar Datos Existentes ✅
**Archivo**: `migracion_fase4_migrar_datos.py`

Migra datos existentes de `maestro` buscando matches en las nuevas tablas.

**Ejecutar**:
```bash
python migracion_fase4_migrar_datos.py
```

**Validación**: 
- Revisar reporte generado (`migracion_fase4_reporte.txt`)
- Verificar que datos migrados son correctos

**Nota**: Los registros sin match mantienen NULL en las FKs (sistema sigue funcionando).

---

### Fase 5: Actualizar Backend ✅
**Archivos modificados**:
- `backend/app/routers/prices.py`
- `backend/app/routers/dcp.py`
- `backend/app/routers/cotizaciones.py`

**Cambios**:
- Queries actualizadas para usar LEFT JOINs
- `COALESCE()` para usar valores de nuevas tablas si existen, sino valores antiguos
- Compatibilidad total con ambos casos

**Validación**: Probar todos los endpoints con datos que tienen FKs y datos que no tienen FKs.

---

### Fase 6: Crear Helpers y Template ✅
**Archivos creados**:
- `helpers/maestro_helper.py`: Funciones reutilizables
- `migracion_fase6_template_script.py`: Template de ejemplo

**Funciones helper**:
- `obtener_o_crear_variable()`: Busca/crea variable
- `obtener_o_crear_pais_grupo()`: Busca/crea país
- `insertar_maestro_con_fks()`: Inserta en maestro con FKs opcionales

**Uso**: Ver `migracion_fase6_template_script.py` para ejemplo completo.

---

### Fase 7: Migración Gradual de Scripts
**Archivo**: `migracion_fase7_checklist.md`

Migrar scripts de actualización uno por uno usando los helpers.

**Proceso**:
1. Hacer backup del script
2. Modificar `insertar_en_bd()` usando helpers
3. Probar localmente
4. Verificar datos en BD
5. Probar endpoints
6. Marcar como completado en checklist

**Orden sugerido**:
1. Scripts simples (tipo_cambio_usd.py)
2. Scripts de productos
3. Scripts de servicios
4. Scripts multipaís complejos

---

## Uso de Helpers

### Ejemplo Básico

```python
from helpers.maestro_helper import (
    obtener_o_crear_variable,
    obtener_o_crear_pais_grupo,
    insertar_maestro_con_fks
)

# Obtener o crear variable
id_variable = obtener_o_crear_variable(
    nombre_variable="Precio hacienda - INAC",
    id_sub_familia=3,
    nominal_o_real="n",
    moneda="usd"
)

# Obtener o crear país
id_pais = obtener_o_crear_pais_grupo(nombre_pais="Uruguay")

# Insertar en maestro con FKs
insertar_maestro_con_fks(
    maestro_id=1,
    nombre="Precio hacienda - INAC",
    tipo="P",
    fuente="INAC",
    periodicidad="M",
    unidad="USD/kg",
    categoria="Precios Internacionales",
    activo=1,
    id_nombre_variable=id_variable,
    id_region=id_pais
)
```

### Compatibilidad Hacia Atrás

Si no se pueden obtener las FKs, el helper inserta sin ellas:

```python
# Si obtener_o_crear_variable falla, id_variable será None
# insertar_maestro_con_fks() insertará sin FK (comportamiento antiguo)
```

---

## Validación y Testing

### Verificar Estructura

```sql
-- Verificar tablas creadas
SELECT name FROM sqlite_master WHERE type='table' AND name IN 
('variables', 'pais_grupo', 'familia', 'sub_familia', 'graph', 'filtros_graph_pais');

-- Verificar columnas nuevas en maestro
PRAGMA table_info(maestro);

-- Verificar datos migrados
SELECT COUNT(*) FROM maestro WHERE id_nombre_variable IS NOT NULL;
SELECT COUNT(*) FROM maestro WHERE id_region IS NOT NULL;
```

### Probar Backend

1. **Con FKs**: Verificar que endpoints retornan datos correctos
2. **Sin FKs**: Verificar que endpoints siguen funcionando con datos antiguos

### Probar Scripts Migrados

1. Ejecutar script migrado
2. Verificar que datos se insertan correctamente
3. Verificar que FKs se crean (si aplica)
4. Probar endpoints relevantes

---

## Rollback Plan

Si algo falla en cualquier fase:

1. **Fase 1-3**: Columnas nuevas son opcionales, no afectan sistema actual
2. **Fase 4**: NULLs en FKs no rompen nada, sistema sigue funcionando
3. **Fase 5**: Backend puede revertirse a queries antiguas
4. **Fase 6-7**: Scripts individuales pueden revertirse sin afectar otros

---

## Troubleshooting

### Error: "Tabla no existe"
**Solución**: Ejecutar `migracion_fase1_crear_tablas.py` primero

### Error: "Columna no existe"
**Solución**: Ejecutar `migracion_fase3_agregar_columnas.py`

### No se encuentran matches en Fase 4
**Solución**: Revisar reporte y crear registros faltantes manualmente o ajustar lógica de búsqueda

### Backend retorna datos incorrectos
**Solución**: Verificar que queries usan `COALESCE()` correctamente

---

## Próximos Pasos

1. Completar migración de scripts según `migracion_fase7_checklist.md`
2. Validar que todos los scripts migrados funcionan correctamente
3. (Opcional) Hacer FKs obligatorias una vez todos los registros tengan FKs
4. (Opcional) Eliminar columnas antiguas si se desea (más adelante)

---

## Contacto y Soporte

Para dudas o problemas durante la migración, revisar:
- `analisis_integracion_maestro_database.md`: Análisis detallado
- `analisis_riesgo_migracion_completa.md`: Análisis de riesgos
- `migracion_fase6_template_script.py`: Ejemplo de migración
