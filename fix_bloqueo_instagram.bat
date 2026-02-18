@echo off
echo ===================================================
echo   FIX BLOQUEO INSTAGRAM - MATANDO PROCESOS CHROME
echo ===================================================
echo.
echo CUIDADO: Esto cerrara TODOS los navegadores Chrome/Chromium abiertos.
echo Si tienes otras cosas abiertas en Chrome, guardalas ahora.
echo.
pause
echo.
echo Matando chrome.exe...
taskkill /F /IM chrome.exe /T 2>nul
taskkill /F /IM msedge.exe /T 2>nul
echo.
echo Eliminando locks de sesion...
del /F /Q "data\instagram_session_v3\SingletonLock" 2>nul
del /F /Q "data\browser_session_v2\SingletonLock" 2>nul
echo.
echo Listo. Ahora intenta iniciar el bot de nuevo.
pause
