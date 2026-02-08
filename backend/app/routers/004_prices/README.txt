================================================================================
PRECIOS CORRIENTES - Precios de Exportación -corrientes-
================================================================================

ID Graph: 4
Nombre: Precios de Exportación -corrientes-
Selector: Seleccione producto

DESCRIPCIÓN:
------------
Este módulo maneja los precios corrientes (nominales) de productos y servicios 
de exportación. Permite consultar precios históricos, calcular variaciones y 
exportar datos. Usa los mismos filtros que DCP para mantener consistencia 
en la selección de productos.

ENDPOINTS:
----------
GET /api/products
  Obtiene todos los productos activos para Precios Corrientes.
  Usa los mismos filtros que DCP:
    - id_familia = 2 (todas las subfamilias)
    - O id_familia = 3 con id_subfamilia IN (5, 4, 3, 2) y id_pais = 858

GET /api/products/<product_id>/prices
  Obtiene precios de un producto específico.
  Parámetros opcionales:
    - fecha_desde: Fecha inicial (YYYY-MM-DD)
    - fecha_hasta: Fecha final (YYYY-MM-DD)

GET /api/products/prices
  Obtiene precios de múltiples productos.
  Parámetros:
    - product_ids[]: Lista de IDs de productos
    - fecha_desde: Fecha inicial (opcional)
    - fecha_hasta: Fecha final (opcional)
  Retorna datos agrupados por producto con resumen.

GET /api/variations
  Calcula variaciones de índices DCP para todos los productos.
  Parámetros:
    - fecha_desde: Fecha inicial (YYYY-MM-DD)
    - fecha_hasta: Fecha final (YYYY-MM-DD)
    - order_by: 'asc' o 'desc' (default: 'desc')
  Retorna lista ordenada por variación porcentual.

GET /api/variations/export
  Exporta variaciones a Excel con 5 hojas:
    - Resumen Variaciones
    - Índices Calculados
    - Índices Originales
    - Precios Originales (con IPC y TC)
    - Metadatos

GET /api/products/prices/export
  Exporta precios de múltiples productos a Excel.
  Parámetros: iguales a /products/prices

GET /api/stats/<product_id>
  Obtiene estadísticas de un producto.
  Parámetros opcionales:
    - fecha_desde: Fecha inicial
    - fecha_hasta: Fecha final
  Retorna: precio actual, variación, min/max del período

CARACTERÍSTICAS:
---------------
- Usa los mismos filtros que DCP para consistencia
- Calcula índices DCP para variaciones (precio × TC / IPC)
- Maneja productos en USD, EUR y UYU
- Convierte datos diarios/semanales a mensuales
- Calcula variaciones porcentuales
- Exporta a Excel con múltiples hojas
- Identifica productos omitidos y razones

FILTROS:
--------
Los productos se filtran igual que en DCP:
- Familia 2: Todas las subfamilias (sin restricciones)
- Familia 3: Solo subfamilias 5, 4, 3, 2 para Uruguay (id_pais = 858)
- Excluye IPC (id_variable != 9)
- Solo productos activos (activo = 1)

DIFERENCIAS CON DCP:
--------------------
- Este módulo muestra precios CORRIENTES (nominales)
- DCP muestra precios CONSTANTES (ajustados por inflación)
- Ambos usan los mismos filtros de productos
- Ambos calculan índices, pero con diferentes propósitos

ESTRUCTURA DE DATOS:
--------------------
Producto:
  - id: ID sintético (id_variable * 10000 + id_pais)
  - nombre: Nombre de la variable
  - pais: Nombre del país
  - fuente: Origen de datos
  - periodicidad: D/W/M
  - data: Array de {fecha, valor}
  - summary: {precio_inicial, precio_final, variacion, fechas}
