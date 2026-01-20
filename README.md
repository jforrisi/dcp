# DCP - Visualización de Precios

Sistema de visualización de series de tiempo de precios de productos y servicios.

## 🚀 Características

- Visualización de series de tiempo de precios
- Comparación de variaciones de precios
- API REST para consulta de datos
- Interfaz web moderna con React y TypeScript
- Backend con Flask

## 📋 Requisitos

- Python 3.11+
- Node.js 18+
- npm o yarn

## 🛠️ Instalación Local

Ver [README_SETUP.md](README_SETUP.md) para instrucciones detalladas.

### Quick Start

```bash
# Backend
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
python run.py

# Frontend (en otra terminal)
cd frontend
npm install
npm run dev
```

## 🚂 Deploy en Railway

Este proyecto está configurado para deploy automático en Railway.

Ver [RAILWAY_DEPLOY.md](RAILWAY_DEPLOY.md) para instrucciones completas.

### Pasos rápidos:

1. Conecta este repositorio a Railway
2. Railway detectará automáticamente la configuración
3. El build se ejecutará automáticamente
4. ¡Listo! Tu app estará disponible en la URL de Railway

## 📁 Estructura del Proyecto

```
.
├── backend/          # API Flask
│   ├── app/         # Aplicación Flask
│   └── requirements.txt
├── frontend/        # Frontend React + TypeScript
│   ├── src/         # Código fuente
│   └── package.json
├── precios/         # Scripts de actualización de precios
├── macro/           # Scripts de actualización de macro
└── data_raw/        # Datos en bruto
```

## 📝 Notas

- La base de datos SQLite (`series_tiempo.db`) debe estar presente para que la aplicación funcione
- Para producción, se recomienda migrar a PostgreSQL

## 📄 Licencia

[Especificar licencia si aplica]
