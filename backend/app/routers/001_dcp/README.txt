================================================================================
DCP - Precios de Exportación en Pesos Uruguayos Constantes
================================================================================

ID Graph: 1
Nombre: Precios de Exportación en Pesos Uruguayos Constantes
Selector: Seleccione producto

DESCRIPCIÓN:
------------
Este módulo calcula índices DCP (Dominant Currency Paradigm) para productos y 
servicios de exportación. Los índices representan precios internacionales 
convertidos a pesos uruguayos constantes, ajustados por inflación.

FÓRMULA:
--------
Para variables NOMINALES:
  Índice = (Precio × Tipo de Cambio) / IPC

Para variables REALES:
  Índice = Precio × Tipo de Cambio

Donde:
  - Precio: Precio del producto en su moneda original (USD, EUR, o UYU)
  - Tipo de Cambio: TC USD/UYU o TC EUR/UYU según la moneda del producto
  - IPC: Índice de Precios al Consumidor de Uruguay (id_variable = 11)

ENDPOINTS:
----------
GET /api/dcp/variables
  Obtiene la lista de variables disponibles para PEPUC.
  Filtra por id_familia = 2 o id_familia = 3 con subfamilias específicas.

GET /api/dcp/products
  Obtiene la lista de productos y servicios para PEPUC.
  Filtra automáticamente por:
  - id_familia = 2 (todas las subfamilias)
  - O id_familia = 3 con id_subfamilia IN (5, 4, 3, 2) y id_pais = 858 (Uruguay)

GET /api/dcp/indices
  Calcula índices DCP para productos seleccionados.
  Parámetros:
    - product_ids[]: Lista de IDs de productos
    - fecha_desde: Fecha inicial (YYYY-MM-DD)
    - fecha_hasta: Fecha final (YYYY-MM-DD)
  Retorna índices normalizados a base 100.

GET /api/dcp/indices/export
  Exporta índices DCP a Excel con 3 hojas:
    - Índices Normalizados
    - Índices Originales
    - Precios Originales (con IPC y TC)

VARIABLES MACRO:
----------------
- TC_USD_ID = 6: Tipo de cambio USD/UYU
- TC_EUR_ID = 7: Tipo de cambio EUR/UYU
- IPC_ID = 11: IPC general de Uruguay

CARACTERÍSTICAS:
---------------
- Normaliza índices a base 100 (primer valor = 100)
- Maneja productos en USD, EUR y UYU
- Distingue entre variables nominales y reales
- Convierte automáticamente datos diarios/semanales a mensuales
- Calcula variaciones de precio, TC, IPC e índice real
- Valida fórmulas de variación

FILTROS:
--------
Los productos se filtran automáticamente según:
- Familia 2: Todas las subfamilias (sin restricciones)
- Familia 3: Solo subfamilias 5, 4, 3, 2 para Uruguay (id_pais = 858)
- Excluye IPC (id_variable != 9)
- Solo productos activos (activo = 1)
