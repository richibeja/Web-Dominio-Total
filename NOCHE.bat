@echo off
title 🌙 AURORA — GUARDIA NOCTURNA
color 05
cd /d "%~dp0"

echo.
echo  ╔══════════════════════════════════════════════════╗
echo  ║   🌙  AURORA — GUARDIA NOCTURNA                 ║
echo  ║   Telegram + Fanvue activos toda la noche       ║
echo  ║   Audio de reactivacion cada 2 horas            ║
echo  ╚══════════════════════════════════════════════════╝
echo.

:: Matar procesos viejos
taskkill /f /im python.exe >nul 2>&1
taskkill /f /im py.exe >nul 2>&1
timeout /t 3 >nul

:: Detectar Python
set PY=
python --version >nul 2>&1
if %errorlevel% equ 0 (set PY=python) else (
    py --version >nul 2>&1
    if %errorlevel% equ 0 (set PY=py)
)
if "%PY%"=="" (
    echo [ERROR] Python no encontrado.
    pause & exit /b
)

echo  Iniciando sistema... los bots se gestionan solos.
echo  Esta ventana debe quedar ABIERTA toda la noche.
echo  (Minimizala, no la cierres)
echo.

:: Lanzar bienvenida automática a nuevos suscriptores (en paralelo)
start "🌸 BIENVENIDA NUEVOS" cmd /k "cd /d "%~dp0" && %PY% BIENVENIDA_NUEVOS.py --loop"



%PY% GUARDIA_NOCTURNA.py

echo.
echo  Sistema detenido.
pause
