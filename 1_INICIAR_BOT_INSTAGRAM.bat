@echo off
echo ===================================================
echo    AURORA BOT - SOLO INSTAGRAM
echo    (Respuestas automaticas y enlace a pagina de ventas)
echo ===================================================
echo.
echo Iniciando monitoreo...
echo Manten esta ventana abierta.
echo.
py instagram_bot/automation/run_instagram_monitor.py
if %errorlevel% neq 0 (
    echo.
    echo [ERROR] El bot se cerro inesperadamente.
    pause
)
