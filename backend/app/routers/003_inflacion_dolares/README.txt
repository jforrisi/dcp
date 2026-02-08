================================================================================
INFLACIÓN EN DÓLARES - Inflación en dólares
================================================================================

ID Graph: 3
Nombre: Inflación en dólares
Selector: Seleccione país

DESCRIPCIÓN:
------------
Este módulo calcula la inflación en dólares para diferentes países de LATAM.
La fórmula combina el IPC (Índice de Precios al Consumidor) de cada país con 
su tipo de cambio USD/LC (moneda local) para obtener un índice que representa 
la inflación medida en dólares.

FÓRMULA:
--------
Índice = IPC mensual / TC USD/LC mensual

Donde:
  - IPC: Índice de Precios al Consumidor del país (id_variable = 9)
  - TC: Tipo de cambio USD/LC (cotización diaria convertida a mensual) con (id_variable = 20)

El índice se normaliza a base 100 (primer valor = 100).

ENDPOINTS:
----------
GET /api/inflacion-dolares/products
  Obtiene la lista de países disponibles con cotización e IPC (o sea tiene id_variable = 9 e id_variable = 20).
  Filtra por países configurados en filtros_graph_pais para id_graph=3.


GET /api/inflacion-dolares
  Calcula la inflación en dólares para países seleccionados.
  Parámetros:
    - product_ids[]: Lista de IDs de cotizaciones (países)
    - fecha_desde: Fecha inicial (YYYY-MM-DD)
    - fecha_hasta: Fecha final (YYYY-MM-DD)
  Retorna índices normalizados a base 100 con variaciones.

CARACTERÍSTICAS:
---------------
- Filtra por países permitidos en filtros_graph_pais (id_graph = 3)
- Busca IPC por id_variable = 9 y periodicidad = 'M'
- Convierte cotizaciones diarias a mensuales (promedio por mes)
- Normaliza índices a base 100
- Calcula variaciones de índice, TC e IPC
- Incluye IPC incluso si activo = 0 (si tiene datos)
- Evita duplicados por país

FILTROS:
--------
Países permitidos:
  - Configurados en filtros_graph_pais para id_graph = 3
  - Deben tener cotización diaria activa (periodicidad = 'D', activo = 1)
  - Deben tener IPC mensual con datos (id_variable = 9, periodicidad = 'M')

ESTRUCTURA DE DATOS:
--------------------
Cada país tiene:
  - product_id: ID sintético de la cotización
  - product_name: Nombre de la cotización
  - pais: Nombre del país
  - data: Array de {fecha, valor} (índice normalizado)
  - summary: {
      indice_inicial, indice_final,
      variacion_indice, variacion_tc, variacion_ipc,
      fecha_inicial, fecha_final
    }

NOTAS TÉCNICAS:
---------------
- El IPC se busca por id_pais e id_variable = 9, no por nombre
- El USD/LC se busca por id_pais e id_variable = 20, no por nombre
- Se incluyen IPC inactivos si tienen datos en maestro_precios
- Las cotizaciones se agrupan por mes (promedio) para coincidir con IPC mensual
- Se usa LIMIT 1 para evitar duplicados de cotización por país
