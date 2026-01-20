# Guía de Deployment en Railway

Este proyecto está configurado para ser desplegado en Railway.

## Configuración Incluida

### Archivos de Configuración

- **`Procfile`**: Define el comando para iniciar la aplicación
- **`railway.json`**: Configuración específica de Railway
- **`nixpacks.toml`**: Configuración de build para Nixpacks (usado por Railway)
- **`build.sh`**: Script de build para Linux/Mac
- **`build.bat`**: Script de build para Windows (desarrollo local)

### Cambios Realizados

1. **`backend/run.py`**: Actualizado para usar el puerto dinámico de Railway (`PORT` env var)
2. **`backend/app/main.py`**: Configurado para servir el frontend construido y manejar rutas de React Router
3. **`frontend/vite.config.ts`**: Configurado para producción con rutas relativas
4. **`frontend/src/services/api.ts`**: Actualizado para usar rutas relativas en producción

## Pasos para Deployar en Railway

### 1. Preparar el Repositorio

Asegúrate de que todos los archivos estén commiteados:

```bash
git add .
git commit -m "Configure Railway deployment"
git push
```

### 2. Crear Proyecto en Railway

1. Ve a [Railway](https://railway.app)
2. Inicia sesión o crea una cuenta
3. Haz clic en "New Project"
4. Selecciona "Deploy from GitHub repo"
5. Conecta tu repositorio y selecciona este proyecto

### 3. Configurar Variables de Entorno (Opcional)

Railway detectará automáticamente la configuración, pero puedes agregar variables de entorno si es necesario:

- `PORT`: Railway lo configura automáticamente
- `FLASK_ENV`: `production` (por defecto) o `development`
- `VITE_API_URL`: Solo necesario si quieres usar una URL específica para la API

### 4. Deploy

Railway automáticamente:
1. Detectará que es un proyecto Python/Node.js
2. Ejecutará el build usando `nixpacks.toml` o `build.sh`
3. Iniciará la aplicación usando el `Procfile`

### 5. Verificar el Deploy

Una vez desplegado:
- Railway te dará una URL pública (ej: `https://tu-proyecto.railway.app`)
- Visita `/health` para verificar que el backend funciona
- Visita la raíz `/` para ver el frontend

## Estructura del Build

El proceso de build:
1. Instala dependencias de Node.js en `frontend/`
2. Instala dependencias de Python en `backend/`
3. Compila el frontend React con `npm run build`
4. Copia los archivos compilados de `frontend/dist/` a `backend/app/static/`
5. Inicia el servidor Flask que sirve tanto la API como el frontend

## Base de Datos

**Importante**: La aplicación usa SQLite (`series_tiempo.db`). 

En Railway:
- El sistema de archivos es efímero, por lo que la base de datos se perderá en cada redeploy
- **Recomendación**: Migrar a PostgreSQL usando el servicio de Railway o usar un volumen persistente

Para usar PostgreSQL:
1. Agrega un servicio PostgreSQL en Railway
2. Railway te dará la variable `DATABASE_URL`
3. Actualiza `backend/app/database.py` para usar PostgreSQL en lugar de SQLite

## Troubleshooting

### El frontend no se muestra
- Verifica que el build se completó correctamente
- Revisa los logs de Railway para ver errores de build
- Asegúrate de que `backend/app/static/` contenga los archivos del frontend

### La API no responde
- Verifica que el puerto esté configurado correctamente (Railway usa `PORT`)
- Revisa los logs para ver errores de conexión a la base de datos
- Asegúrate de que `series_tiempo.db` esté presente o migra a PostgreSQL

### Errores de CORS
- El backend ya tiene CORS configurado para permitir todos los orígenes
- Si persisten problemas, verifica la configuración en `backend/app/main.py`

## Desarrollo Local vs Producción

### Desarrollo Local
```bash
# Terminal 1: Backend
cd backend
python run.py

# Terminal 2: Frontend
cd frontend
npm run dev
```

### Producción (Railway)
- Un solo proceso sirve tanto el backend como el frontend
- El frontend se compila y se sirve como archivos estáticos desde Flask
- Las rutas de React Router se manejan automáticamente
