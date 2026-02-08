================================================================================
ANÁLISIS DE LICITACIONES LRM
================================================================================

ID Graph: 7
Nombre: Análisis de Licitaciones LRM
País: Uruguay (id_pais = 858)

DESCRIPCIÓN:
------------
Este módulo permite analizar las licitaciones LRM (Letras de Regulación Monetaria)
del BCU (Banco Central del Uruguay). El usuario selecciona una fecha y el sistema
muestra información detallada sobre esa licitación, incluyendo comparación con
tasas BEVSA y estadísticas de las últimas 5 licitaciones.

VARIABLES LRM:
--------------
Las licitaciones LRM se procesan para 4 plazos diferentes (30, 90, 180, 360 días).
Para cada plazo hay 3 variables:

Plazo 30 días:
  - Licitación: id_variable = 33
  - Adjudicado: id_variable = 29
  - Tasa de corte: id_variable = 25

Plazo 90 días:
  - Licitación: id_variable = 34
  - Adjudicado: id_variable = 30
  - Tasa de corte: id_variable = 26

Plazo 180 días:
  - Licitación: id_variable = 35
  - Adjudicado: id_variable = 31
  - Tasa de corte: id_variable = 27

Plazo 360 días:
  - Licitación: id_variable = 36
  - Adjudicado: id_variable = 32
  - Tasa de corte: id_variable = 28

MAPEO PLAZO LRM → BEVSA:
-------------------------
Cada plazo de licitación se mapea a una variable de la curva BEVSA nominal:

  - 30 días → "1 mes" (id_variable = 37)
  - 90 días → "3 meses" (id_variable = 39)
  - 180 días → "6 meses" (id_variable = 40)
  - 360 días → "1 año" (id_variable = 42)

ENDPOINTS:
----------
GET /api/licitaciones-lrm/dates
  Obtiene las fechas disponibles para licitaciones LRM.
  Retorna:
    {
      "ultima_fecha": "YYYY-MM-DD",
      "fechas_disponibles": ["YYYY-MM-DD", ...]
    }

GET /api/licitaciones-lrm/data
  Obtiene los datos de una licitación específica.
  Parámetros:
    - fecha: Fecha en formato YYYY-MM-DD (requerido)
  Retorna:
    {
      "fecha": "YYYY-MM-DD",
      "plazo": 30|90|180|360,
      "monto_licitado": 1234567.89,
      "adjudicado": 0.85,  // Formato decimal (0.85 = 85%)
      "tasa_corte": 5.25
    }

GET /api/licitaciones-lrm/bevsa-rate
  Obtiene la tasa BEVSA para un plazo específico.
  Parámetros:
    - plazo: 30, 90, 180, o 360 (requerido)
    - fecha_limite: Fecha límite en formato YYYY-MM-DD (opcional)
  Retorna:
    {
      "plazo": 30,
      "nombre": "1 mes",
      "id_variable": 37,
      "ultima_fecha": "YYYY-MM-DD",
      "ultimo_valor": 5.25,
      "min_5_dias": 5.20,
      "max_5_dias": 5.30
    }

GET /api/licitaciones-lrm/stats
  Obtiene estadísticas de las últimas 5 licitaciones.
  Parámetros:
    - plazo: 30, 90, 180, o 360 (requerido)
    - fecha_limite: Fecha límite en formato YYYY-MM-DD (requerido)
  Retorna:
    {
      "total_licitado": 12345678.90,
      "total_adjudicado": 10493925.07,
      "porcentaje_adjudicacion": 85.0,
      "licitaciones": [
        {
          "fecha": "YYYY-MM-DD",
          "monto_licitado": 1234567.89,
          "adjudicado": 0.85,
          "monto_adjudicado": 1049382.71,
          "porcentaje_adjudicacion": 85.0
        },
        ...
      ]
    }

GET /api/licitaciones-lrm/curve
  Obtiene la última curva BEVSA nominal disponible.
  Retorna:
    {
      "fecha": "YYYY-MM-DD",
      "data": [
        {
          "nombre": "1 mes",
          "id_variable": 37,
          "valor": 5.25
        },
        ...
      ]
    }

CÁLCULO DE % ADJUDICACIÓN PONDERADO:
------------------------------------
Para las últimas 5 licitaciones, se calcula el porcentaje de adjudicación ponderado:

1. Para cada licitación i:
   monto_adjudicado_i = monto_licitado_i * adjudicado_i
   (donde adjudicado_i está en formato decimal: 0.85 = 85%)

2. Total adjudicado = Σ(monto_adjudicado_i) para i = 1 a 5
3. Total licitado = Σ(monto_licitado_i) para i = 1 a 5

4. % adjudicación ponderado = (total_adjudicado / total_licitado) * 100

Esto pondera el porcentaje de adjudicación de cada licitación por su monto licitado,
dando más peso a las licitaciones con mayor monto.
