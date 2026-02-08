# Análisis: Integración de maestro_database.xlsx al Sistema

## Estructura Actual del Sistema

### Tabla `maestro` (actual)
- `id` (PK) - Identificador único
- `nombre` - Nombre descriptivo
- `tipo` (P/S/M) - Producto/Servicio/Macro
- `fuente` - Origen de datos
- `periodicidad` (D/W/M) - Diario/Semanal/Mensual
- `unidad` - Unidad de medida
- `categoria` - Clasificación temática
- `activo` - Boolean
- `moneda` (adicional) - Código de moneda
- `nominal_real` (adicional) - n/r
- `es_cotizacion` (adicional) - Boolean

### Tabla `maestro_precios` (actual)
- `id` (PK, auto)
- `maestro_id` (FK) - Referencia a maestro.id
- `fecha` - Fecha de observación
- `valor` - Valor numérico

---

## Nueva Estructura (maestro_database.xlsx)

### Tablas Normalizadas

#### 1. **maestro** (nueva estructura)
- `id_nombre_variable` (FK) - Referencia a variables.id_nombre_variable
- `id_region` (FK) - Referencia a pais_grupo.id_pais_grupo
- `fuente` - Origen de datos
- `periodicidad` (D/W/M)
- `activo` - Boolean
- `link` - URL opcional

#### 2. **variables** (nueva tabla)
- `id_variable` (PK)
- `id_nombre_variable` - Nombre único de la variable (ej: "Arroz", "Servicios de arquitectura")
- `id_sub_familia` (FK) - Referencia a sub_familia
- `nominal_o_real` (n/r)
- `moneda` - Código de moneda

#### 3. **pais_grupo** (nueva tabla)
- `id_pais_grupo` (PK)
- `nombre_pais_grupo` - Nombre del país/región

#### 4. **familia** (nueva tabla)
- `id_familia` (PK)
- `nombre_familia` - Ej: "Financiero", "Precio Internacional", "Precios y salarios"

#### 5. **sub_familia** (nueva tabla)
- `id_sub_familia` (PK)
- `nombre_sub_familia` - Ej: "Materias primas", "Precio de exportación", "Servicios"

#### 6. **graph** (nueva tabla - para frontend)
- `id_graph` (PK)
- `nombre_graph` - Nombre del gráfico/vista
- `selector` - Tipo de selector ("Seleccione producto", "Seleccione país")

#### 7. **filtros_graph_pais** (nueva tabla - para frontend)
- `id_graph` (FK)
- `id_pais_region` (FK)

---

## Diferencias Clave

### 1. **Normalización**
- **Actual**: Todo en una tabla `maestro` (estructura plana)
- **Nueva**: Estructura normalizada con múltiples tablas relacionadas

### 2. **Identificación de Series**
- **Actual**: `id` único por serie
- **Nueva**: `id_nombre_variable` + `id_region` = serie única
  - Ejemplo: "Arroz" (id_nombre_variable=2) en "Uruguay" (id_region=12)

### 3. **Clasificación**
- **Actual**: `categoria` (texto libre)
- **Nueva**: `familia` → `sub_familia` (jerarquía estructurada)

### 4. **País/Región**
- **Actual**: `pais` (columna opcional en maestro)
- **Nueva**: `pais_grupo` (tabla separada con FK)

### 5. **Metadatos de Variables**
- **Actual**: `moneda` y `nominal_real` en `maestro`
- **Nueva**: `moneda` y `nominal_o_real` en `variables` (compartido por todas las regiones)

---

## Relaciones Correctas Identificadas

### Relación Principal
- **`maestro.id_nombre_variable`** (numérico) → **`variables.id_variable`** (numérico)
- **`variables.id_nombre_variable`** es el NOMBRE descriptivo (texto)
- **`maestro.id_region`** (numérico) → **`pais_grupo.id_pais_grupo`** (numérico)

### Ejemplo de Relación Completa
```
maestro:
  id_nombre_variable = 12
  id_region = 12
  
variables:
  id_variable = 12
  id_nombre_variable = "Precio hacienda - INAC"
  moneda = "usd"
  nominal_o_real = "n"
  id_sub_familia = 3
  
pais_grupo:
  id_pais_grupo = 12
  nombre_pais_grupo = "Uruguay"
  
sub_familia:
  id_sub_familia = 3
  nombre_sub_familia = "Precio interno de cadena transable"
```

**Resultado**: "Precio hacienda - INAC" en Uruguay, en USD, nominal

---

## Cómo Integrar al Sistema

### Opción 1: Migración Completa (Recomendada)

#### Paso 1: Crear nuevas tablas en SQLite
```sql
-- Tabla variables
CREATE TABLE variables (
    id_variable INTEGER PRIMARY KEY,
    id_nombre_variable VARCHAR(255) UNIQUE NOT NULL,  -- Nombre descriptivo
    id_sub_familia INTEGER,
    nominal_o_real CHAR(1),
    moneda VARCHAR(10),
    FOREIGN KEY (id_sub_familia) REFERENCES sub_familia(id_sub_familia)
);

-- NOTA: La relación es maestro.id_nombre_variable -> variables.id_variable

-- Tabla pais_grupo
CREATE TABLE pais_grupo (
    id_pais_grupo INTEGER PRIMARY KEY,
    nombre_pais_grupo VARCHAR(100) NOT NULL
);

-- Tabla familia
CREATE TABLE familia (
    id_familia INTEGER PRIMARY KEY,
    nombre_familia VARCHAR(255) NOT NULL
);

-- Tabla sub_familia
CREATE TABLE sub_familia (
    id_sub_familia INTEGER PRIMARY KEY,
    nombre_sub_familia VARCHAR(255) NOT NULL,
    id_familia INTEGER,
    FOREIGN KEY (id_familia) REFERENCES familia(id_familia)
);

-- Tabla graph (para frontend)
CREATE TABLE graph (
    id_graph INTEGER PRIMARY KEY,
    nombre_graph VARCHAR(255) NOT NULL,
    selector VARCHAR(100)
);

-- Tabla filtros_graph_pais
CREATE TABLE filtros_graph_pais (
    id_graph INTEGER,
    id_pais_region INTEGER,
    FOREIGN KEY (id_graph) REFERENCES graph(id_graph),
    FOREIGN KEY (id_pais_region) REFERENCES pais_grupo(id_pais_grupo)
);

-- Modificar tabla maestro existente
ALTER TABLE maestro ADD COLUMN id_nombre_variable INTEGER;  -- FK a variables.id_variable
ALTER TABLE maestro ADD COLUMN id_region INTEGER;  -- FK a pais_grupo.id_pais_grupo
ALTER TABLE maestro ADD COLUMN link VARCHAR(500);
-- NOTA: id_sub_familia se obtiene de variables.id_sub_familia (no se duplica en maestro)
```

#### Paso 2: Migrar datos desde Excel
1. Cargar datos de tablas de referencia (pais_grupo, familia, sub_familia, variables)
2. Mapear datos actuales de `maestro` a nueva estructura:
   - Extraer `nombre` → buscar en `variables.id_nombre_variable`
   - Extraer `pais` → buscar en `pais_grupo.nombre_pais_grupo`
   - Mapear `categoria` → `sub_familia`

#### Paso 3: Actualizar backend
- Modificar queries para hacer JOINs con nuevas tablas
- Actualizar endpoints para usar nueva estructura
- Mantener compatibilidad con `maestro_precios` (no cambia)

### Opción 2: Híbrida (Más Simple)

Mantener estructura actual pero agregar tablas de referencia:

1. **Agregar tablas de referencia** (pais_grupo, familia, sub_familia, variables)
2. **Mantener `maestro` actual** pero agregar FKs opcionales:
   - `id_nombre_variable` (opcional, para vincular con variables)
   - `id_region` (opcional, para vincular con pais_grupo)
3. **Migración gradual**: Llenar FKs cuando sea posible

---

## Ventajas de la Nueva Estructura

1. **Normalización**: Evita duplicación de datos
   - Una variable (ej: "Arroz") puede estar en múltiples países sin duplicar metadatos

2. **Clasificación Estructurada**: 
   - Jerarquía clara: Familia → Sub-familia
   - Facilita filtros y agrupaciones

3. **Gestión de Países**:
   - Tabla centralizada de países/regiones
   - Fácil agregar nuevos países

4. **Metadatos Compartidos**:
   - `moneda` y `nominal_o_real` definidos una vez por variable
   - Se aplica a todas las regiones donde existe esa variable

5. **Soporte para Frontend**:
   - Tablas `graph` y `filtros_graph_pais` permiten configurar vistas dinámicamente

---

## Desafíos de Integración

1. **Mapeo de Datos Existentes**:
   - Necesita mapear `nombre` actual → `id_nombre_variable`
   - Necesita mapear `pais` actual → `id_region`

2. **Compatibilidad con Backend**:
   - Endpoints actuales esperan `maestro.id`
   - Nueva estructura usa `id_nombre_variable + id_region`
   - Necesita crear `id` compuesto o mantener `id` actual

3. **Scripts de Actualización**:
   - Todos los scripts que insertan en `maestro` necesitan actualizarse
   - Deben usar nueva estructura con FKs

4. **Frontend**:
   - Si usa `graph` y `filtros_graph_pais`, necesita actualizarse
   - Si no, puede ignorar esas tablas inicialmente

---

## Recomendación

**Opción Híbrida** es la más práctica:

1. Agregar nuevas tablas de referencia
2. Agregar columnas opcionales a `maestro` actual
3. Migrar datos gradualmente
4. Actualizar backend para usar JOINs cuando FKs estén disponibles
5. Mantener compatibilidad con estructura actual

Esto permite:
- ✅ No romper el sistema actual
- ✅ Migración gradual
- ✅ Probar nueva estructura sin riesgo
- ✅ Rollback fácil si hay problemas
