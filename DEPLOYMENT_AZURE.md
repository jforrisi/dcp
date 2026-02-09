# Despliegue en Azure App Service (macrodata)

## Cambios realizados para corregir el fallo de despliegue

### 1. `requirements.txt` simplificado

El `requirements.txt` raíz se redujo a las dependencias **necesarias solo para la web app**:

- Eliminados: `selenium`, `webdriver-manager`, `bcchapi`, `html5lib`, `lxml`, `beautifulsoup4`, `pillow`
- Estas dependencias suelen causar fallos en `pip install` durante el build de Oryx (más pesadas o con compilación nativa).

Para desarrollo local y scripts de update, usa:

```bash
pip install -r requirements-full.txt
```

### 2. Comando de arranque (Startup Command)

En Azure Portal:

1. App Service **macrodata** → **Configuración** → **Configuración**
2. Pestaña **Configuración general**
3. **Comando de inicio** (Startup Command):

   ```
   startup.txt
   ```

   O directamente el comando:

   ```
   cd backend && gunicorn --bind 0.0.0.0:8000 --workers 2 --threads 2 --timeout 120 app.main:app
   ```

4. **Guardar**

### 3. Variables de entorno requeridas

En **Configuración** → **Configuración** → **Configuración de la aplicación**:

| Nombre      | Valor              |
|------------|---------------------|
| DATABASE_URL | `postgresql://...` (conexión a Azure PostgreSQL) |
| SECRET_KEY | Clave secreta para sesiones    |

### 4. Recomendaciones ante “SCM container restart”

Si aparece:

> Deployment has been stopped due to SCM container restart

- Evita hacer cambios en la app (por ejemplo, reiniciar o escalar) mientras se despliega.
- Añade un pequeño retraso entre deploy y otras operaciones (por ejemplo, en GitHub Actions).
- Vuelve a intentar el despliegue cuando el contenedor esté estable.

### 5. Logs y diagnóstico

- **Log de despliegue**: Kudu → `https://macrodata-caataybjguhcgxes.scm.chilecentral-01.azurewebsites.net/api/deployments/...`
- **Logs en tiempo real**: Azure Portal → App Service → **Supervisión** → **Registro de secuencias**
- **Errores de pip**: en el log de despliegue, buscar la salida completa de `pip install`

### 6. Ejecutar scripts de update en Azure

Los scripts de update (`update_database.py`, etc.) no se ejecutan en el contenedor web. Opciones:

- Ejecutarlos localmente contra la misma `DATABASE_URL`.
- Usar un **Azure Function** o **GitHub Actions** programados para correr los scripts con acceso a PostgreSQL.
