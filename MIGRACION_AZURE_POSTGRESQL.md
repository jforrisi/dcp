# Migración a Azure PostgreSQL

## Resumen

El proyecto usa **PostgreSQL (Azure)** por defecto para todas las operaciones.

- **DATABASE_URL** (requerida): conexión a Azure PostgreSQL
- **SQLite** (`series_tiempo.db`): solo backup manual con `USE_SQLITE_BACKUP=1`

---

## Paso 1: Crear Azure PostgreSQL

1. En Azure Portal → Crear recurso → Azure Database for PostgreSQL
2. Elegir **Flexible server**
3. Configurar: nombre, región, usuario, contraseña
4. En **Networking**: agregar tu IP para acceso local
5. Copiar la cadena de conexión, ej:
   ```
   postgresql://usuario:contraseña@servidor.postgres.database.azure.com:5432/nombredb
   ```

---

## Paso 2: Crear el schema en PostgreSQL

Desde Azure Cloud Shell, psql o cualquier cliente:

```bash
psql "postgresql://usuario:contraseña@servidor.postgres.database.azure.com:5432/nombredb?sslmode=require" -f scripts/schema_postgresql.sql
```

O en Azure Portal: Query editor → pegar el contenido de `scripts/schema_postgresql.sql` → Ejecutar.

---

## Paso 3: Migrar los datos

```bash
# En PowerShell o CMD
set DATABASE_URL=postgresql://usuario:contraseña@servidor.postgres.database.azure.com:5432/nombredb?sslmode=require
python scripts/migrate_sqlite_to_postgres.py
```

---

## Paso 4: Configurar el proyecto

### Local (actualizar contra Azure)

Crear `.env` en la raíz del proyecto (o exportar en la terminal):

```
DATABASE_URL=postgresql://usuario:contraseña@servidor.postgres.database.azure.com:5432/nombredb?sslmode=require
```

### Azure (App Service / Container Apps)

En la configuración del servicio, agregar variable de entorno:

- **Nombre**: `DATABASE_URL`
- **Valor**: la misma cadena de conexión

---

## Paso 5: Probar

### Backend local

```bash
cd backend
python run.py
```

### Script de actualización local

```bash
# Con DATABASE_URL definida, los datos van a Azure PostgreSQL
python update/update_database.py
```

O un script individual:

```bash
python update/direct/007_precio_soja_wb.py
```

---

## Dependencias nuevas

```
psycopg2-binary>=2.9.0
sqlalchemy>=2.0.0
```

Ya están en `requirements.txt`.

---

## Estructura de archivos

- `db/connection.py` – Módulo de conexión (SQLite + PostgreSQL)
- `db/__init__.py` – Exportaciones
- `scripts/schema_postgresql.sql` – Schema para PostgreSQL
- `scripts/migrate_sqlite_to_postgres.py` – Script de migración
- `backend/app/database.py` – Usa el módulo db
- `update/direct/_helpers.py` – Usa el módulo db
