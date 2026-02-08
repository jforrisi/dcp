# Instrucciones: Actualización Automática de Base de Datos

## Descripción

El script `update_database.py` ejecuta automáticamente todos los scripts de actualización en el orden correcto:

1. **FASE 1**: Descarga archivos Excel (scripts en `precios/download/`)
2. **FASE 2**: Actualiza la base de datos (scripts en `precios/update/` y `macro/update/`)

## Características

- ✅ **Detección automática**: Encuentra todos los scripts sin configuración manual
- ✅ **Modo automático**: Responde "sí" automáticamente a todas las confirmaciones
- ✅ **Reporte de errores**: Genera `update_database.txt` con detalles de errores
- ✅ **Robusto**: Si un script falla, continúa con los demás
- ✅ **Timeout**: Máximo 1 hora por script

## Scripts Separados

El sistema ahora tiene dos scripts:

1. **`update_database.py`**: Ejecuta scripts normales (rápidos)
   - Excluye scripts complicados como `servicios_no_tradicionales.py`
   - Timeout: 1 hora por script

2. **`update_database_complicados.py`**: Ejecuta solo scripts complicados
   - Solo `servicios_no_tradicionales.py` y otros similares
   - Timeout: 2 horas por script (más tiempo)

## Prueba Local

### 1. Ejecutar scripts normales

```bash
python update_database.py
```

### 2. Ejecutar scripts complicados (después de los normales)

```bash
python update_database_complicados.py
```

El script mostrará:
- Qué scripts detectó en FASE 1 (descargas)
- Qué scripts detectó en FASE 2 (actualizaciones)
- Ejecutará cada uno en orden
- Generará el reporte `update_database.txt`

### 2. Revisar el reporte

Después de la ejecución, revisa el archivo `update_database.txt`:

```bash
# En Windows
type update_database.txt

# En Linux/Mac
cat update_database.txt
```

El reporte incluye:
- Resumen general (total, exitosos, fallidos)
- Lista de scripts exitosos por fase
- Detalles de errores (si los hay)

## Estructura del Reporte

```
================================================================================
REPORTE DE ACTUALIZACIÓN DE BASE DE DATOS
================================================================================
Fecha/Hora de ejecución: 2025-01-15 02:00:15

RESUMEN GENERAL
--------------------------------------------------------------------------------
Total de scripts ejecutados: 15
  - FASE 1 (Descargas): 2
  - FASE 2 (Actualizaciones): 13

Exitosos: 13
  - FASE 1: 2
  - FASE 2: 11

Fallidos: 2
  - FASE 1: 0
  - FASE 2: 2

Tiempo total: 1245.67 segundos (20.76 minutos)

FASE 1 - SCRIPTS DE DESCARGA EJECUTADOS EXITOSAMENTE
--------------------------------------------------------------------------------
  ✅ precios_productos/carne_exportacion.py (45.23s)
  ✅ precios_productos/novillo_hacienda.py (32.11s)

FASE 2 - SCRIPTS DE ACTUALIZACIÓN EJECUTADOS EXITOSAMENTE
--------------------------------------------------------------------------------
  ✅ precios_productos/novillo_hacienda.py (12.45s)
  ...

ERRORES EN FASE 2 (ACTUALIZACIONES)
================================================================================

ERROR #1: macro/tipo_cambio_usd.py
--------------------------------------------------------------------------------
Tiempo de ejecución: 12.45s

Detalle del error:
Error: El script terminó con código 1
[ERROR] No se pudo leer el Excel desde la URL
Connection timeout after 30 seconds
...
```

## Configuración en Railway

### Opción 1: Railway Cron (si está disponible)

1. En Railway, crear un servicio cron
2. Configurar para ejecutar diariamente a las 2:00 AM (o la hora deseada)
3. Comando: `python update_database.py`

### Opción 2: Servicio Web con Endpoint

Crear un endpoint en el backend que ejecute el script:

```python
# En backend/app/routers/update.py
@bp.route('/update/run', methods=['POST'])
def run_update():
    # Verificar autenticación/token si es necesario
    import subprocess
    result = subprocess.run(['python', 'update_database.py'], 
                          capture_output=True, text=True)
    return jsonify({
        'status': 'completed',
        'returncode': result.returncode,
        'output': result.stdout
    })
```

Luego usar un servicio externo (cron-job.org, etc.) para llamar a este endpoint.

### Opción 3: Script de Railway

Crear un script que Railway ejecute periódicamente:

```bash
#!/bin/bash
cd /app
python update_database.py
```

## Consideraciones para Railway

### Selenium en Railway

Los scripts de descarga usan Selenium. En Railway necesitarás:

1. **Chrome/Chromium headless**: Instalar en el contenedor
2. **ChromeDriver**: Configurar correctamente
3. **Variables de entorno**: Puede ser necesario configurar `CHROME_BIN`, etc.

Ejemplo de configuración en Railway:

```dockerfile
# Dockerfile o configuración
RUN apt-get update && apt-get install -y \
    chromium-browser \
    chromium-chromedriver
```

O usar variables de entorno en Railway:
- `CHROME_BIN=/usr/bin/chromium-browser`
- `CHROMEDRIVER_PATH=/usr/bin/chromedriver`

### Persistencia de data_raw/

En Railway, los archivos en `data_raw/` pueden perderse entre reinicios. Considera:

1. **Volumen persistente**: Configurar un volumen para `data_raw/`
2. **Almacenamiento externo**: Usar S3 o similar para archivos descargados
3. **Regeneración**: Los scripts pueden volver a descargar si no encuentran el archivo

## Códigos de Salida

- `0`: Todo OK, todos los scripts se ejecutaron exitosamente
- `1`: Hubo errores en uno o más scripts

Útil para monitoreo y alertas.

## Troubleshooting

### Script no detecta archivos

Verifica que:
- Los scripts estén en las carpetas correctas
- Los scripts tengan extensión `.py`
- No estén excluidos (scripts con "historico" o "cargar" en el nombre)

### Timeout en scripts

Si un script tarda más de 1 hora, se cancela automáticamente. Ajusta `TIMEOUT_SCRIPT` en el código si es necesario.

### Errores de Selenium

En Railway, asegúrate de:
- Tener Chrome/Chromium instalado
- Configurar correctamente ChromeDriver
- Usar modo headless: `--headless=new`

## Próximos Pasos

1. ✅ Probar localmente: `python update_database.py`
2. ✅ Revisar reporte: `update_database.txt`
3. ✅ Configurar en Railway según opción elegida
4. ✅ Monitorear ejecuciones automáticas
