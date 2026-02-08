================================================================================
CURVA DE RENDIMIENTO - Yield Curve
================================================================================

ID Graph: 5
Nombre: Curva de Rendimiento
País: Uruguay (id_pais = 858)

DESCRIPCIÓN:
------------
Este módulo muestra la curva de rendimiento de Uruguay, que representa las tasas
de interés para diferentes plazos. El gráfico muestra las tasas en el eje vertical
y los plazos (1 mes, 2 meses, 3 meses, etc.) en el eje horizontal.

VARIABLES:
----------
Las siguientes variables representan los diferentes plazos de la curva:

ID 57: "1 mes" (id_variable = 37)
ID 58: "2 meses" (id_variable = 38)
ID 59: "3 meses" (id_variable = 39)
ID 60: "6 meses" (id_variable = 40)
ID 61: "9 meses" (id_variable = 41)
ID 62: "1 año" (id_variable = 42)
ID 63: "2 años" (id_variable = 43)
ID 64: "3 años" (id_variable = 44)
ID 65: "4 años" (id_variable = 45)
ID 66: "5 años" (id_variable = 46)
ID 67: "6 años" (id_variable = 47)
ID 68: "7 años" (id_variable = 48)
ID 69: "8 años" (id_variable = 49)
ID 70: "9 años" (id_variable = 50)
ID 71: "10 años" (id_variable = 51)

Todas las variables corresponden al país Uruguay (id_pais = 858).

ENDPOINTS:
----------
GET /api/yield-curve/dates
  Obtiene las fechas disponibles para la curva de rendimiento.
  Retorna:
    {
      "ultima_fecha": "YYYY-MM-DD",
      "fechas_disponibles": ["YYYY-MM-DD", ...]
    }

GET /api/yield-curve/data
  Obtiene los datos de la curva de rendimiento para una fecha específica.
  Parámetros:
    - fecha: Fecha en formato YYYY-MM-DD (opcional, por defecto usa la última fecha disponible)
  Retorna:
    {
      "fecha": "YYYY-MM-DD",
      "data": [
        {
          "id": 57,
          "nombre": "1 mes",
          "id_variable": 37,
          "valor": 5.25
        },
        ...
      ]
    }

GET /api/yield-curve/table
  Obtiene la tabla con las tasas, último valor y variaciones.
  Retorna:
    {
      "fecha_ultima": "YYYY-MM-DD",
      "data": [
        {
          "id": 57,
          "nombre": "1 mes",
          "id_variable": 37,
          "valor_ultimo": 5.25,
          "variacion_5_dias": 0.10,
          "variacion_30_dias": 0.25,
          "variacion_360_dias": 1.50,
          "variacion_anio_actual": 0.75
        },
        ...
      ]
    }

CARACTERÍSTICAS:
---------------
- Por defecto muestra la última fecha disponible
- El usuario puede seleccionar fechas desde el menú de la izquierda
- El gráfico muestra las tasas en el eje vertical y los plazos en el eje horizontal
- La tabla muestra:
  * Valor último: Último valor disponible para cada plazo
  * Variación 5 días: Diferencia en puntos porcentuales respecto a hace 5 días
  * Variación 30 días: Diferencia en puntos porcentuales respecto a hace 30 días
  * Variación 360 días: Diferencia en puntos porcentuales respecto a hace 360 días
  * Variación año actual: Diferencia en puntos porcentuales respecto al inicio del año

ESTRUCTURA DE DATOS:
--------------------
Cada punto de la curva tiene:
  - id: ID de la variable en la tabla variables (57-71)
  - nombre: Nombre del plazo (ej: "1 mes", "2 meses", etc.)
  - id_variable: ID de la variable en maestro_precios (37-51)
  - valor: Valor de la tasa para la fecha especificada

La tabla incluye además:
  - valor_ultimo: Último valor disponible
  - variacion_5_dias: Variación en puntos porcentuales (valor_actual - valor_hace_5_dias)
  - variacion_30_dias: Variación en puntos porcentuales (valor_actual - valor_hace_30_dias)
  - variacion_360_dias: Variación en puntos porcentuales (valor_actual - valor_hace_360_dias)
  - variacion_anio_actual: Variación en puntos porcentuales (valor_actual - valor_inicio_anio)

NOTAS TÉCNICAS:
---------------
- Si no se proporciona fecha en /data, se usa automáticamente la última fecha disponible
- Las variaciones se calculan como diferencia absoluta (no porcentual)
- Si no hay valor disponible para una fecha de referencia, la variación será None
- Se buscan valores en la fecha exacta o la más cercana anterior disponible
- Todas las variables corresponden al país Uruguay (id_pais = 858)
