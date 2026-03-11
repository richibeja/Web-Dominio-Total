@echo off
title [DEBUG] REPARADOR DE BOT CHERRY
color 0E
cd /d "%~dp0"

echo --------------------------------------------------
echo [LIMPIEZA] CERRANDO INSTANCIAS PREVIAS...
echo --------------------------------------------------
taskkill /f /im python.exe /t >nul 2>&1
taskkill /f /im py.exe /t >nul 2>&1
timeout /t 2 >nul

echo --------------------------------------------------
echo [DEBUG] VERIFICANDO INSTALACION DE CHERRY...
echo --------------------------------------------------

echo [INFO] Detectando Python...
set PY_CMD=py
py --version >nul 2>&1
if %errorlevel% neq 0 (
    set PY_CMD=python
    python --version >nul 2>&1
    if %errorlevel% neq 0 (
        echo [ERROR] No se pudo encontrar Python correctamente.
        echo [INFO] Intentando usar ruta directa...
        if exist "C:\Users\ALP\AppData\Local\Microsoft\WindowsApps\py.exe" (
            set PY_CMD="C:\Users\ALP\AppData\Local\Microsoft\WindowsApps\py.exe"
        ) else (
            echo [!] Por favor abre una terminal y escribe 'python' para verificar.
            pause
            exit
        )
    )
)
echo [OK] Usando comando: %PY_CMD%

:: 2. Instalar dependencias CRITICAS
echo [INFO] Instalando dependencias necesarias (pydub, requests, dotenv)...
%PY_CMD% -m pip install pydub requests python-dotenv python-telegram-bot --upgrade

:: 3. Intentar correr el bot y capturar error
echo --------------------------------------------------
echo [INFO] Intentando lanzar el Bot... Si falla, veras el error abajo.
echo --------------------------------------------------

cd AURORA_APP
%PY_CMD% telegram_bot.py

if %errorlevel% neq 0 (
    echo.
    echo --------------------------------------------------
    echo [ERROR] El bot se detuvo con codigo %errorlevel%
    echo --------------------------------------------------
)

pause
