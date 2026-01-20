# Guía de Instalación y Uso

## Requisitos Previos

- Python 3.8 o superior
- Node.js 18 o superior
- npm o yarn

## Backend (FastAPI)

### Instalación

1. Navega a la carpeta `backend`:
```bash
cd backend
```

2. Crea un entorno virtual (recomendado):
```bash
python -m venv venv
```

3. Activa el entorno virtual:
- Windows:
```bash
venv\Scripts\activate
```
- Linux/Mac:
```bash
source venv/bin/activate
```

4. Instala las dependencias:
```bash
pip install -r requirements.txt
```

### Ejecución

Desde la carpeta `backend`:
```bash
uvicorn app.main:app --reload --port 8000
```

El servidor estará disponible en `http://localhost:8000`
La documentación de la API estará disponible en `http://localhost:8000/docs`

## Frontend (React + Vite)

### Instalación

1. Navega a la carpeta `frontend`:
```bash
cd frontend
```

2. Instala las dependencias:
```bash
npm install
```

### Ejecución

Desde la carpeta `frontend`:
```bash
npm run dev
```

La aplicación estará disponible en `http://localhost:5173`

## Uso

1. Asegúrate de que el backend esté corriendo en el puerto 8000
2. Inicia el frontend en el puerto 5173
3. Abre tu navegador en `http://localhost:5173`

### Funcionalidades

#### Series de Tiempo
- Selecciona uno o más productos
- Elige un rango de fechas
- Haz clic en "Aplicar Filtros" para ver el gráfico
- Visualiza estadísticas (precio actual, variación, min/max)

#### Variaciones
- Selecciona un rango de fechas
- Elige el orden (Mayor a Menor / Menor a Mayor)
- Haz clic en "Aplicar Filtros" para ver las variaciones
- Visualiza gráfico de barras y lista detallada

## Notas

- La base de datos SQLite (`series_tiempo.db`) debe estar en la raíz del proyecto
- El backend busca la base de datos en `../series_tiempo.db` desde `backend/app/`
- Si cambias los puertos, actualiza la configuración en `frontend/vite.config.ts` y `backend/app/main.py`
