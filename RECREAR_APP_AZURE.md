# Recrear la App Service en Azure (macrodata)

Eliminaste la app y la estás creando de nuevo. Sigue estos pasos en orden.

---

## 1. Crear la App Service en Azure Portal

1. Entrá a **[portal.azure.com](https://portal.azure.com)**.
2. **App Services** → **+ Create** / **+ Crear**.
3. **Basics**:
   - **Subscription**: la tuya.
   - **Resource group**: el mismo que tu otra app (para tener todo junto) o uno nuevo.
   - **Name**: **`macrodata`** (así el deploy de GitHub no requiere cambios).
   - **Publish**: **Code**.
   - **Runtime stack**: **Python 3.11** (o 3.10).
   - **Operating System**: **Linux**.
   - **Region**: la **misma** que tu otra app si querés usar el mismo App Service Plan.
4. **App Service Plan**:
   - Si querés pagar un solo plan: **Use existing** → elegí el plan de tu otra app (solo aparecen planes de esa región).
   - Si no: **Create new** y elegí tamaño (ej. B1 o B2).
5. **Review + create** → **Create**.

---

## 2. Comando de arranque (Startup Command)

1. En la nueva app **macrodata** → **Configuración** → **Configuración**.
2. Pestaña **Configuración general**.
3. **Comando de inicio** (Startup Command), poné exactamente:
   ```bash
   cd backend && gunicorn --bind 0.0.0.0:8000 --workers 2 --threads 2 --timeout 120 app.main:app
   ```
4. **Guardar** (arriba).

---

## 3. Variables de entorno

1. Misma app → **Configuración** → **Configuración** → pestaña **Configuración de la aplicación**.
2. **+ Nueva configuración de la aplicación** y agregá:

   | Nombre        | Valor |
   |---------------|--------|
   | `DATABASE_URL` | Tu cadena de conexión a PostgreSQL, ej. `postgresql://usuario:contraseña@servidor.postgres.database.azure.com:5432/nombredb?sslmode=require` |
   | `SECRET_KEY`   | Una clave secreta para sesiones (string aleatorio) |

3. **Guardar**.

Si tenías otras variables en la app anterior (por ejemplo para APIs externas), agregalas también.

---

## 4. Conectar GitHub (deploy automático)

El workflow de este repo usa **secretos** de Azure (service principal). Si la nueva app se llama **macrodata** y está en el mismo **resource group** y **suscripción** que antes, suele seguir funcionando sin tocar nada.

- **Opción A – Probar primero**: Hacé un push a `main` o en GitHub → **Actions** → workflow **"Build and deploy Python app to Azure Web App - macrodata"** → **Run workflow**. Si el deploy funciona, no hace falta más.
- **Opción B – Reconfigurar**:
  1. En Azure → App Service **macrodata** → **Deployment Center**.
  2. **Source**: GitHub → autorizá y elegí repo y rama `main`.
  3. Guardá. Azure puede crear un nuevo workflow o usar el existente; si pide reemplazar, podés usar el que ya tenés en el repo (`.github/workflows/main_macrodata.yml`).

Si el deploy falla por permisos, en **Deployment Center** volvé a conectar GitHub o revisá que el service principal de los secretos tenga acceso al resource group donde está **macrodata**.

---

## 5. Primera vez que arranca

- Después del primer deploy, la app puede tardar 1–2 minutos en responder.
- URL: `https://macrodata-XXXXX.<region>.azurewebsites.net` (la ves en Azure → Overview de la app).
- Si ves 503 o error, esperá un poco y revisá **Supervisión** → **Registro de secuencias** (log stream) para ver errores de arranque.

---

## Resumen rápido

| Paso | Dónde | Qué hacer |
|------|--------|-----------|
| 1 | Azure Portal | Crear App Service **macrodata**, misma región (y mismo plan si querés) |
| 2 | Configuración → Configuración general | Comando de inicio: `cd backend && gunicorn --bind 0.0.0.0:8000 --workers 2 --threads 2 --timeout 120 app.main:app` |
| 3 | Configuración → Configuración de la aplicación | Agregar `DATABASE_URL` y `SECRET_KEY` |
| 4 | GitHub | Push a `main` o Run workflow; si falla, reconectar en Deployment Center |
| 5 | Azure / navegador | Esperar 1–2 min y probar la URL de la app |

Si en el paso 1 usás **otro nombre** que no sea `macrodata`, después tenés que cambiar en el repo el `app-name` en `.github/workflows/main_macrodata.yml` por el nombre nuevo.
