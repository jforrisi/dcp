# Instrucciones para Push a GitHub

Sigue estos pasos para subir tu código a GitHub:

## 1. Agregar el remoto de GitHub

```bash
git remote add origin https://github.com/jforrisi/dcp.git
```

## 2. Decidir sobre la base de datos

La base de datos `series_tiempo.db` tiene aproximadamente 3.7 MB. Tienes dos opciones:

### Opción A: Incluir la base de datos (recomendado para empezar)
Si quieres incluirla, descomenta la línea en `.gitignore`:
```bash
# Edita .gitignore y comenta o elimina esta línea:
# series_tiempo.db
```

### Opción B: Excluir la base de datos
Si prefieres no incluirla (está comentada por defecto en .gitignore), deberás:
- Subirla manualmente a Railway después del deploy
- O migrar a PostgreSQL (recomendado para producción)

## 3. Agregar archivos y hacer commit

```bash
# Agregar todos los archivos
git add .

# Hacer commit inicial
git commit -m "Initial commit: DCP project with Railway configuration"

# Cambiar a rama main (si es necesario)
git branch -M main

# Hacer push a GitHub
git push -u origin main
```

## 4. Conectar con Railway

1. Ve a [Railway](https://railway.app)
2. Inicia sesión
3. Haz clic en "New Project"
4. Selecciona "Deploy from GitHub repo"
5. Conecta tu cuenta de GitHub si es necesario
6. Selecciona el repositorio `jforrisi/dcp`
7. Railway detectará automáticamente la configuración y comenzará el deploy

## Notas

- Si excluyes la base de datos, asegúrate de tenerla disponible para Railway
- Railway usará el `nixpacks.toml` o `build.sh` para construir la aplicación
- El proceso de build puede tardar varios minutos la primera vez
