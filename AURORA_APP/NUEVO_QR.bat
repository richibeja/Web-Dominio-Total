@echo off
cd /d "%~dp0"
echo.
echo === OBTENER NUEVO CODIGO QR ===
echo.
echo 1. CIERRA el servidor (en la ventana donde corre node server.js, pulsa Ctrl+C).
echo 2. Luego pulsa una tecla aqui para borrar la sesion y poder ver el nuevo QR.
echo.
pause
if exist ".wwebjs_auth" (
    rmdir /s /q ".wwebjs_auth"
    echo Sesion (.wwebjs_auth) borrada.
) else (
    echo No habia sesion wwebjs.
)
if exist "baileys_auth" (
    rmdir /s /q "baileys_auth"
    echo Sesion (baileys_auth) borrada.
) else (
    echo No habia sesion Baileys.
)
if exist "baileys_store" (
    rmdir /s /q "baileys_store"
    echo baileys_store borrada.
)
if exist ".wwebjs_cache" (
    rmdir /s /q ".wwebjs_cache"
    echo Cache (.wwebjs_cache) borrada.
)
echo.
echo Ahora ejecuta INICIAR.bat (o "node server.js") y abre http://localhost:3000
echo Veras el codigo QR de nuevo. Escanealo con WhatsApp.
echo.
pause
