@echo off
title AURORA - REINICIO COMPLETO
color 0A
echo.
echo ================================================
echo   AURORA LUZ - REINICIANDO SISTEMA COMPLETO
echo ================================================
echo.

:: Matar procesos viejos si quedan
echo [1/4] Limpiando procesos anteriores...
taskkill /F /IM node.exe /T >nul 2>&1
taskkill /F /IM ngrok.exe /T >nul 2>&1
timeout /t 2 /nobreak >nul

:: Iniciar AURORA_APP (Node.js - Puerto 4000)
echo [2/4] Iniciando AURORA_APP (puerto 4000)...
cd /d "%~dp0AURORA_APP"
start "AURORA SERVER" cmd /k "node server.js"
timeout /t 4 /nobreak >nul

:: Iniciar ngrok apuntando al puerto 4000
echo [3/4] Iniciando tunel NGROK (puerto 4000)...
start "NGROK TUNNEL" cmd /k "ngrok http 4000"
timeout /t 5 /nobreak >nul

:: Mostrar URL publica de ngrok
echo [4/4] Obteniendo URL publica...
timeout /t 3 /nobreak >nul
curl -s http://localhost:4040/api/tunnels 2>nul | findstr "public_url"

echo.
echo ================================================
echo  LISTO! Revisa la ventana de NGROK para
echo  ver tu URL publica actualizada.
echo ================================================
echo.
pause
