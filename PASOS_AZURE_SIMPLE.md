# Pasos para arreglar el despliegue en Azure (macrodata)

## Problema
El despliegue falla por:
1. **SCM container restart** – el contenedor se reinició durante el deploy
2. **pip install** – algo falla al instalar dependencias (el log no muestra el error exacto)

---

## Paso 1: Esperar y volver a desplegar

1. Espera **5–10 minutos** sin cambiar nada en Azure Portal.
2. No actualices configuración, no reinicies la app.
3. En GitHub: **Actions** → workflow de macrodata → **Re-run all jobs** (o vuelve a hacer push).

---

## Paso 2: Configurar el comando de arranque en Azure

1. Entra en [portal.azure.com](https://portal.azure.com).
2. Busca **macrodata** (tu App Service).
3. Menú izquierdo → **Configuración** → **Configuración**.
4. Pestaña **Configuración general**.
5. En **Comando de inicio**, escribe:
   ```
   cd backend && gunicorn --bind 0.0.0.0:8000 --workers 2 --timeout 120 app.main:app
   ```
6. **Guardar** (arriba).
7. Espera 1–2 minutos a que se aplique.

---

## Paso 3: Revisar variables de entorno

1. En la misma app **macrodata** → **Configuración** → **Configuración**.
2. Pestaña **Configuración de la aplicación**.
3. Comprueba que existan:
   - `DATABASE_URL` (conexión a PostgreSQL)
   - `SECRET_KEY` (clave secreta)
4. Si faltan, **+ Nueva configuración de la aplicación** y añádelas.
5. **Guardar**.

---

## Paso 4: Añadir retraso en el workflow de GitHub

Tu workflow está en el repo **dcp** (`jforrisi/dcp`):

1. Abre `.github/workflows/main_macrodata.yml` en el repo **dcp**.
2. Justo **antes** del paso `azure/webapps-deploy@v3`, añade este paso:

```yaml
- name: Wait before deploy
  run: sleep 30
```

Debería quedar algo así:

```yaml
- name: Wait before deploy
  run: sleep 30

- name: Deploy to Azure
  uses: azure/webapps-deploy@v3
  with:
    app-name: macrodata
    slot-name: Production
    package: .
```

3. Haz commit y push.
4. Espera 5 minutos y vuelve a ejecutar el workflow.

---

## Paso 5: Si sigue fallando – ver el error de pip

1. Entra en Kudu: `https://macrodata-caataybjguhcgxes.scm.chilecentral-01.azurewebsites.net`
2. Menú **Tools** → **Zip Push Deploy** o **Deployment** → **Deployments**.
3. En la lista de deployments, abre el último (el que falló).
4. Haz clic en **Log** para ver el log completo de `pip install` y el error concreto.

---

## Paso 6: Error "Exception in worker process" al arrancar

Si el log muestra `Exception in worker process` al cargar la app, haz **scroll hacia abajo** hasta ver la línea del error real (por ejemplo `ModuleNotFoundError: No module named 'db'`).

### Causa común: falta el módulo `db`

La app necesita la carpeta `db/` en la raíz del proyecto (al mismo nivel que `backend/`). Si el artifact en **dcp** solo incluye `backend/`, fallará.

**Revisar en el repo dcp** el job que crea el artifact `python-app`:

- Debe incluir **todo el proyecto**: `backend/`, `db/`, `requirements.txt`, `startup.txt`
- Ejemplo de `path` al subir artifact:
  ```yaml
  - name: Upload artifact
    uses: actions/upload-artifact@v4
    with:
      name: python-app
      path: .    # <-- debe ser "." (todo) o incluir backend + db
  ```

Si hoy subes solo `backend/`, hay que cambiar a `path: .` para incluir `db/` y el resto.

### Otra causa: falta DATABASE_URL

En Azure → **Configuración** → **Configuración de la aplicación**, verifica que exista `DATABASE_URL` con la cadena de conexión a PostgreSQL.

---

## Paso 7: Error "No module named 'flask_cors'"

Este error indica que el `requirements.txt` usado en el build **no incluye** `flask-cors`.

**Solución:** En el repo **dcp** (donde se construye el artifact), asegúrate de que el `requirements.txt` en la raíz incluya:

```
flask-cors>=4.0.0
```

Y que ese archivo forme parte del artifact que se sube a Azure. Si dcp usa el mismo código que gita, sincroniza o copia el `requirements.txt` de gita a dcp.

---

## Resumen rápido

| Paso | Qué hacer |
|------|-----------|
| 1 | Esperar 5–10 min y volver a desplegar |
| 2 | Poner comando de inicio en Azure (Configuración → Configuración general) |
| 3 | Verificar DATABASE_URL y SECRET_KEY |
| 4 | Añadir `sleep 30` antes del deploy en GitHub Actions |
| 5 | Si falla, revisar log en Kudu |
