================================================================================
COTIZACIONES - Cotizaciones de Monedas
================================================================================

ID Graph: 2
Nombre: Cotizaciones de monedas
Selector: Seleccione país

DESCRIPCIÓN:
------------
Este módulo maneja las cotizaciones diarias de tipos de cambio para países 
de LATAM. Permite consultar, visualizar y exportar datos de tipos de cambio 
entre monedas locales y USD/EUR.

ENDPOINTS:
----------
GET /api/cotizaciones/products
  Obtiene la lista de cotizaciones disponibles.
  Filtra por países configurados en filtros_graph_pais para id_graph=2.
  Solo muestra cotizaciones con periodicidad diaria (periodicidad = 'D').

GET /api/cotizaciones
  Obtiene cotizaciones diarias de tipos de cambio LATAM.
  Parámetros:
    - product_ids[]: Lista de IDs de productos (cotizaciones)
    - fecha_desde: Fecha inicial (YYYY-MM-DD)
    - fecha_hasta: Fecha final (YYYY-MM-DD)
  Retorna datos diarios con resumen de variación.

GET /api/cotizaciones/export
  Exporta cotizaciones a Excel.
  Parámetros: iguales a /cotizaciones
  Retorna archivo Excel con:
    - Hoja "Cotizaciones": Datos diarios
    - Hoja "Metadatos": Información del export

CARACTERÍSTICAS:
---------------
- Filtra automáticamente por países permitidos en filtros_graph_pais
- Solo muestra cotizaciones activas (activo = 1)
- Periodicidad diaria (periodicidad = 'D')
- Calcula variación porcentual entre fecha inicial y final
- Normaliza fechas (maneja timestamps de SQLite)
- Usa DISTINCT para evitar duplicados por país

FILTROS:
--------
- Países configurados en filtros_graph_pais para id_graph = 2
- Periodicidad = 'D' (diaria)
- activo = 1
- Evita duplicados por país usando DISTINCT

ESTRUCTURA DE DATOS:
--------------------
Cada cotización tiene:
  - id: ID sintético (id_variable * 10000 + id_pais)
  - nombre: Nombre de la variable (ej: "Tipo de cambio USD/ARS")
  - pais: Nombre del país
  - fuente: Origen de los datos
  - data: Array de {fecha, valor}
  - summary: {precio_inicial, precio_final, variacion, fechas}
