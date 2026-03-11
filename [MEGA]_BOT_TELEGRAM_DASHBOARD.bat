@echo off
title [REINFORCED] CHERRY MEGA-SYSTEM
color 0B
cd /d "%~dp0"

echo --------------------------------------------------
echo [SYSTEM] INICIALIZANDO NUCLEO CHERRY...
echo [MODE] ELITE HACKER / PROGRAMMER ENFORCED
echo --------------------------------------------------

:: Detectar comando de Python de forma robusta
set PY_CMD=
python --version >nul 2>&1
if %errorlevel% equ 0 (
    set PY_CMD=python
) else (
    py --version >nul 2>&1
    if %errorlevel% equ 0 (
        set PY_CMD=py
    )
)

if "%PY_CMD%"=="" (
    echo [ERROR] Python no detectado. Por favorinstale Python o añádalo al PATH.
    pause
    exit
)

echo [DEBUG] Usando comando: %PY_CMD%

node --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Node.js no detectado. El Dashboard no funcionara.
    pause
    exit
)

:: Limpiar procesos previos
echo [CLEANUP] Cerrando instancias previas para evitar conflictos...
taskkill /f /im node.exe >nul 2>&1
taskkill /f /im python.exe >nul 2>&1
taskkill /f /im py.exe >nul 2>&1
timeout /t 2 >nul

:: Iniciar Dashboard
echo [SYSTEM] Lanzando Dashboard Web...
cd AURORA_APP
start /b node server.js

:: Iniciar Bot de Telegram
echo [SYSTEM] Lanzando Bot de Telegram...
%PY_CMD% telegram_bot.py

echo --------------------------------------------------
echo [CRITICAL] El sistema se detuvo. Revisa si hay errores arriba.
echo --------------------------------------------------
pause
