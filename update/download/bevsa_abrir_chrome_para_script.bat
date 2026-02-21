@echo off
REM Abre Chrome en modo depuracion para que puedas pasar el CAPTCHA de BEVSA
REM sin el mensaje "Un software automatizado esta controlando Chrome".
REM Despues ejecuta: set BEVSA_USE_EXISTING_CHROME=1 ^&^& python curva_pesos_uyu_temp.py

cd /d "%~dp0"

set CHROME=
if exist "C:\Program Files\Google\Chrome\Application\chrome.exe" set CHROME=C:\Program Files\Google\Chrome\Application\chrome.exe
if exist "C:\Program Files (x86)\Google\Chrome\Application\chrome.exe" set CHROME=C:\Program Files (x86)\Google\Chrome\Application\chrome.exe
if exist "%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe" set CHROME=%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe

if "%CHROME%"=="" (
  echo No se encontro Chrome. Instalalo o edita este .bat con la ruta correcta.
  pause
  exit /b 1
)

set PROF=%CD%\.chrome_profile_bevsa
echo Usando perfil: %PROF%
echo.
echo 1. En este Chrome entra a: https://web.bevsa.com.uy
echo 2. Pasa el CAPTCHA (Verifica que eres un ser humano).
echo 3. Deja esta ventana abierta y en la consola ejecuta:
echo    set BEVSA_USE_EXISTING_CHROME=1 ^&^& python curva_pesos_uyu_temp.py
echo.
start "" "%CHROME%" --remote-debugging-port=9222 --user-data-dir="%PROF%"
