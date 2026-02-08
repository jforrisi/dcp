# Análisis de las Tablas `graph` y `filtros_graph_pais`

## Estructura de las Tablas

### Tabla `graph`
- **id_graph** (INTEGER, PK): Identificador único del gráfico/pantalla
- **nombre_graph** (VARCHAR(255)): Nombre descriptivo del gráfico
- **selector** (VARCHAR(100)): Tipo de selector ("Seleccione producto" o "Seleccione país")

### Tabla `filtros_graph_pais`
- **id_graph** (INTEGER, FK): Referencia a `graph.id_graph`
- **id_pais** (INTEGER, FK): Referencia a `pais_grupo.id_pais`

## Relación Encontrada

**Relación Muchos-a-Muchos:**
- Un `graph` puede tener múltiples países filtrados
- Un país puede estar disponible en múltiples `graph`

**Relación de Claves Foráneas:**
- `filtros_graph_pais.id_graph` → `graph.id_graph`
- `filtros_graph_pais.id_pais` → `pais_grupo.id_pais`

## Datos Actuales

### Graphs definidos:
1. **id_graph = 1**: "Precios de Exportación en Pesos Uruguayos Constantes"
   - Selector: "Seleccione producto"
   - Países filtrados: 0 (no aplica, usa productos)

2. **id_graph = 2**: "Cotizaciones de monedas"
   - Selector: "Seleccione país"
   - Países filtrados: 22 países

3. **id_graph = 3**: "Inflación en dólares"
   - Selector: "Seleccione país"
   - Países filtrados: 5 países (id_pais: 76, 152, 484, 604, 858)

4. **id_graph = 4**: "Precios de Exportación -corrientes-"
   - Selector: "Seleccione producto"
   - Países filtrados: 0 (no aplica, usa productos)

## Propósito

Esta estructura permite:
- **Configuración dinámica**: Definir qué países están disponibles para cada gráfico desde la base de datos
- **Filtrado automático**: El frontend puede consultar `filtros_graph_pais` para mostrar solo los países permitidos
- **Escalabilidad**: Agregar nuevos gráficos o países sin modificar código

## Uso Recomendado

Para el endpoint `/cotizaciones/products`:
- Consultar `filtros_graph_pais` donde `id_graph = 2` (Cotizaciones)
- Filtrar las cotizaciones por los `id_pais` permitidos
- Esto asegura que solo se muestren los países configurados para ese gráfico
