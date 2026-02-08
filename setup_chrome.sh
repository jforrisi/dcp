#!/bin/bash
# Script para configurar Chrome/Chromium en Railway con Nixpacks

echo "=== Configurando Chrome/Chromium para Railway ==="

# Detectar Chromium
if command -v chromium &> /dev/null; then
    CHROME_PATH=$(command -v chromium)
    echo "✓ Chromium encontrado en: $CHROME_PATH"
    export CHROME_BIN=$CHROME_PATH
elif command -v chromium-browser &> /dev/null; then
    CHROME_PATH=$(command -v chromium-browser)
    echo "✓ Chromium encontrado en: $CHROME_PATH"
    export CHROME_BIN=$CHROME_PATH
elif command -v google-chrome &> /dev/null; then
    CHROME_PATH=$(command -v google-chrome)
    echo "✓ Chrome encontrado en: $CHROME_PATH"
    export CHROME_BIN=$CHROME_PATH
else
    echo "✗ Chrome/Chromium no encontrado"
    exit 1
fi

# Detectar ChromeDriver
if command -v chromedriver &> /dev/null; then
    DRIVER_PATH=$(command -v chromedriver)
    echo "✓ ChromeDriver encontrado en: $DRIVER_PATH"
    export CHROMEDRIVER_PATH=$DRIVER_PATH
else
    echo "✗ ChromeDriver no encontrado"
    exit 1
fi

# Verificar versiones
echo ""
echo "=== Verificando versiones ==="
$CHROME_BIN --version 2>/dev/null || echo "No se pudo obtener versión de Chrome"
$DRIVER_PATH --version 2>/dev/null || echo "No se pudo obtener versión de ChromeDriver"

echo ""
echo "=== Configuración completa ==="
echo "Exportar estas variables en Railway:"
echo "  CHROME_BIN=$CHROME_BIN"
echo "  CHROMEDRIVER_PATH=$DRIVER_PATH"
