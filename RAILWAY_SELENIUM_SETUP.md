# Configuración de Selenium/Chrome en Railway

## Variables de entorno necesarias en Railway

Después del próximo deploy, Railway debería detectar automáticamente las rutas de Chrome/Chromium. Sin embargo, si los scripts siguen fallando, agregá estas variables manualmente en Railway:

### Opción 1: Detección automática (recomendado)
Railway ejecutará `setup_chrome.sh` durante el build y mostrará las rutas en los logs. Buscá en los logs de build:

```
=== Configurando Chrome/Chromium para Railway ===
✓ Chromium encontrado en: /nix/store/.../bin/chromium
✓ ChromeDriver encontrado en: /nix/store/.../bin/chromedriver
```

### Opción 2: Configuración manual
Si necesitás configurar manualmente, agregá estas variables en Railway → Settings → Variables:

```bash
CHROME_BIN=/nix/store/[hash]/bin/chromium
CHROMEDRIVER_PATH=/nix/store/[hash]/bin/chromedriver
```

Reemplazá `[hash]` con el valor real que aparece en los logs del build.

### Opción 3: Rutas estándar (fallback)
Si las rutas de Nix no funcionan, probá con rutas estándar:

```bash
CHROME_BIN=/usr/bin/chromium
CHROMEDRIVER_PATH=/usr/bin/chromedriver
```

## Scripts que requieren Selenium

Los siguientes scripts requieren Chrome/Chromium para funcionar:

### Fase 1 - Descargas:
- `update/download/curva_pesos_uyu_temp.py` - BEVSA nominales
- `update/download/curva_pesos_uyu_ui_temp.py` - BEVSA UI
- `update/download/ipc_paraguay.py` - IPC Paraguay

### Fase 2 - Actualizaciones:
- `update/direct/015_combustibles_miem.py` - Precios combustibles MIEM
- `update/direct/016_ipc.py` - IPC Uruguay
- `update/direct/018_ipc_paraguay.py` - IPC Paraguay
- `update/direct/019_nxr_argy.py` - Tipo de cambio Argentina
- `update/direct/025_salario_real.py` - Salario real
- `update/direct/026_tipo_cambio_eur.py` - Tipo de cambio EUR
- `update/direct/027_tipo_cambio_usd.py` - Tipo de cambio USD
- `update/direct/028_indice_precios_exportacion_uruguay.py` - Índice precios exportación

## Verificación

Para verificar que Chrome está funcionando correctamente en Railway, ejecutá:

```bash
curl -X POST "https://dcp-production.up.railway.app/api/update/run" \
  -H "Content-Type: application/json" \
  -d "{}"
```

Luego verificá el status:

```bash
curl "https://dcp-production.up.railway.app/api/update/status"
```

Si los scripts con Selenium ya no muestran errores, ¡está funcionando! 🎉

## Troubleshooting

### Error: "chrome not found" o "chromedriver not found"
1. Verificá que `chromium` y `chromedriver` estén en `nixpacks.toml` → `nixPkgs`
2. Revisá los logs del build para ver las rutas detectadas
3. Agregá manualmente las variables `CHROME_BIN` y `CHROMEDRIVER_PATH` en Railway

### Error: "DevToolsActivePort file doesn't exist"
Agregá estas opciones en los scripts de Selenium (ya deberían estar):
```python
chrome_options.add_argument("--headless=new")
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-dev-shm-usage")
```

### Error: "Session not created: This version of ChromeDriver only supports Chrome version X"
Nixpacks debería instalar versiones compatibles. Si el error persiste, puede ser necesario actualizar la versión de `chromium` o `chromedriver` en nixPkgs.

## Logs de actualización

Los logs de cada ejecución se guardan en:
- Directorio: `update/logs/`
- Formato: `update_YYYYMMDD_HHMMSS.txt`

Para ver los logs:
```bash
curl "https://dcp-production.up.railway.app/api/update/logs"
curl "https://dcp-production.up.railway.app/api/update/logs/update_20260208_202456.txt"
```
