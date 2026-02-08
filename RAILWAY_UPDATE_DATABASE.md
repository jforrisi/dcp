# Configuración de `update_database.py` en Railway

Este documento explica cómo configurar y ejecutar `update_database.py` en Railway para actualizar automáticamente la base de datos.

## ✅ Requisitos Cumplidos

El proyecto ya está configurado para funcionar en Railway:

1. **Chrome/Chromium**: Agregado a `nixpacks.toml`
2. **Selenium Headless**: Los scripts de descarga detectan automáticamente Railway y usan modo headless
3. **Dependencias**: Todas las dependencias necesarias están en `backend/requirements.txt`
4. **Detección de Entorno**: Los scripts detectan `RAILWAY_ENVIRONMENT` o `RAILWAY`
5. **Router de Update**: Endpoint HTTP creado para ejecutar el script automáticamente

## 🚀 Configuración en Railway

### Paso 1: Variables de Entorno

Configurar en Railway Dashboard las siguientes variables de entorno:

1. **`UPDATE_TOKEN`** (OBLIGATORIO): Token secreto para autenticar las llamadas al endpoint
   - Generar un token seguro y largo (ej: usar `openssl rand -hex 32` o similar)
   - Ejemplo: `UPDATE_TOKEN=tu-token-secreto-muy-largo-y-seguro-aqui`

2. **`RAILWAY_ENVIRONMENT`**: Railway lo configura automáticamente como `production`

3. **Opcionales** (para debugging):
   - `CHROME_BIN=/usr/bin/chromium-browser`
   - `CHROMEDRIVER_PATH=/usr/bin/chromedriver`

### Paso 2: Verificar Deploy

1. Hacer push a GitHub para trigger automático en Railway
2. Verificar que el build se complete exitosamente
3. Verificar que el servicio web esté corriendo
4. Probar endpoint `/health` para verificar que la app responde:
   ```bash
   curl https://tu-proyecto.railway.app/health
   ```

## 🔧 Endpoints Disponibles

### POST `/api/update/run`

Ejecuta `update_database.py` en background.

**Autenticación**: Requiere header `Authorization` con el valor de `UPDATE_TOKEN`

**Ejemplo de uso**:
```bash
curl -X POST https://tu-proyecto.railway.app/api/update/run \
  -H "Authorization: tu-token-secreto-muy-largo-y-seguro-aqui"
```

**Respuesta exitosa**:
```json
{
  "status": "started",
  "message": "Update script started in background",
  "started_at": "2025-01-21T10:30:00.123456"
}
```

**Códigos de respuesta**:
- `200`: Script iniciado correctamente
- `401`: Token inválido o no proporcionado
- `409`: Ya hay una ejecución en progreso
- `500`: `UPDATE_TOKEN` no configurado

### GET `/api/update/status`

Obtiene el estado de la última ejecución.

**Ejemplo de uso**:
```bash
curl https://tu-proyecto.railway.app/api/update/status
```

**Respuesta**:
```json
{
  "running": false,
  "started_at": "2025-01-21T10:30:00.123456",
  "completed_at": "2025-01-21T11:15:30.789012",
  "returncode": 0,
  "output": "...últimos 10KB de output...",
  "error": null
}
```

## ⏰ Configurar Cron Externo

Railway no tiene cron jobs nativos, por lo que usaremos un servicio externo.

### Opción 1: cron-job.org (Recomendado)

1. **Registrarse en** [cron-job.org](https://cron-job.org) (gratis)

2. **Crear nuevo cron job**:
   - **URL**: `https://tu-proyecto.railway.app/api/update/run`
   - **Método**: POST
   - **Headers**: 
     - Key: `Authorization`
     - Value: `tu-token-secreto-muy-largo-y-seguro-aqui`
   - **Frecuencia**: Diaria a las 2:00 AM UTC (o la hora deseada)
   - **Timeout**: Configurar para al menos 3 horas (el script puede tardar)

3. **Guardar y activar**

### Opción 2: EasyCron

1. **Registrarse en** [EasyCron](https://www.easycron.com) (gratis)

2. **Configurar similar a cron-job.org**

### Opción 3: GitHub Actions (Alternativa)

Si prefieres no usar servicio externo, puedes usar GitHub Actions:

```yaml
# .github/workflows/update-database.yml
name: Update Database

on:
  schedule:
    - cron: '0 2 * * *'  # Diario a las 2 AM UTC
  workflow_dispatch:  # Permite ejecución manual

jobs:
  update:
    runs-on: ubuntu-latest
    steps:
      - name: Trigger Railway Update
        run: |
          curl -X POST https://tu-proyecto.railway.app/api/update/run \
            -H "Authorization: ${{ secrets.UPDATE_TOKEN }}"
```

**Nota**: Necesitarás agregar `UPDATE_TOKEN` como secret en GitHub.

## 🧪 Testing

### 1. Probar Endpoint Manualmente

Antes de configurar el cron, probar el endpoint manualmente:

```bash
# Ejecutar update
curl -X POST https://tu-proyecto.railway.app/api/update/run \
  -H "Authorization: tu-token-secreto"

# Verificar estado
curl https://tu-proyecto.railway.app/api/update/status
```

### 2. Verificar Logs en Railway

1. Ir a Railway Dashboard
2. Seleccionar el servicio
3. Ver logs en tiempo real
4. Buscar mensajes de `update_database.py`

### 3. Verificar Reporte

El script genera un reporte en `update_database.txt` en la raíz del proyecto. En Railway, este archivo puede no ser accesible directamente, pero los logs mostrarán el contenido.

### 4. Testing del Cron

Inicialmente, configurar el cron para ejecutar cada hora para testing:
- Verificar que se ejecute correctamente
- Revisar logs
- Una vez verificado, cambiar a ejecución diaria

## 📝 Monitoreo

### Verificar Ejecuciones

1. **Desde Railway Dashboard**:
   - Ver logs del servicio
   - Buscar mensajes relacionados con `update_database.py`

2. **Desde el Endpoint**:
   ```bash
   curl https://tu-proyecto.railway.app/api/update/status
   ```

3. **Desde el Servicio de Cron**:
   - La mayoría de servicios de cron tienen logs de ejecuciones
   - Verificar que las llamadas HTTP sean exitosas (código 200)

### Alertas

Configurar alertas en el servicio de cron (si está disponible):
- Alertar si el endpoint retorna error
- Alertar si no se ejecuta en el horario esperado

## ⚠️ Consideraciones Importantes

### Persistencia de Datos

**SQLite en Railway**: Los archivos pueden perderse entre reinicios. Opciones:

1. **PostgreSQL en Railway** (Recomendado para producción):
   - Agregar servicio PostgreSQL en Railway
   - Migrar scripts para usar PostgreSQL cuando detecten `RAILWAY_ENVIRONMENT`
   - Usar variable de entorno `DATABASE_URL` que Railway proporciona automáticamente

2. **Volumen Persistente**:
   - Configurar un volumen persistente en Railway para `series_tiempo.db`
   - Los archivos en `data_raw/` pueden regenerarse automáticamente

### Timeouts

- **Script individual**: 1 hora máximo por script (configurado en `update_database.py`)
- **Endpoint**: 3 horas máximo para la ejecución completa
- **Cron Service**: Configurar timeout de al menos 3 horas

### Recursos

- **Memoria**: Selenium con Chrome puede consumir mucha memoria
- Verificar que Railway tenga suficientes recursos asignados
- Considerar aumentar recursos si hay problemas de memoria durante la ejecución

### Ejecuciones Simultáneas

El endpoint previene ejecuciones simultáneas:
- Si se intenta ejecutar mientras otra está en progreso, retorna error 409
- El estado se puede consultar con `/api/update/status`

## 🔍 Troubleshooting

### Error: "UPDATE_TOKEN not configured"

- Verificar que la variable de entorno `UPDATE_TOKEN` esté configurada en Railway
- Verificar que el valor sea correcto

### Error: "Unauthorized"

- Verificar que el token en el header `Authorization` coincida con `UPDATE_TOKEN`
- Verificar que el header se esté enviando correctamente

### Error: "Script not found"

- Verificar que `update_database.py` esté en la raíz del proyecto
- Verificar que el proyecto se haya desplegado correctamente

### Timeout en la Ejecución

- Verificar logs en Railway para ver qué script está causando el timeout
- Considerar aumentar el timeout en `update_database.py` si es necesario
- Verificar que los scripts de descarga no estén bloqueados

### Problemas con Selenium

- Verificar que Chromium y ChromeDriver estén instalados (en `nixpacks.toml`)
- Verificar logs para ver errores específicos de Selenium
- Los scripts detectan automáticamente Railway y usan modo headless

### Base de Datos no se Actualiza

- Verificar que los scripts se ejecuten correctamente (revisar logs)
- Verificar que la base de datos tenga permisos de escritura
- Considerar usar PostgreSQL en lugar de SQLite para mejor persistencia

## 📚 Referencias

- [Railway Documentation](https://docs.railway.app/)
- [Selenium Headless Chrome](https://www.selenium.dev/documentation/webdriver/browsers/chrome/)
- [cron-job.org](https://cron-job.org)
- [EasyCron](https://www.easycron.com)

## ✅ Checklist de Implementación

- [x] Router de update creado (`backend/app/routers/008_update/`)
- [x] Router registrado en `backend/app/main.py`
- [x] `update_database.py` ajustado para usar Python del venv en Railway
- [x] Dependencias agregadas a `backend/requirements.txt`
- [ ] Variables de entorno configuradas en Railway (`UPDATE_TOKEN`)
- [ ] Endpoint probado manualmente
- [ ] Servicio de cron configurado
- [ ] Primera ejecución automática verificada
- [ ] Monitoreo configurado
