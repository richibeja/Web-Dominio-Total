@echo off
cd /d "%~dp0"
echo Verificando dependencias...
if not exist "node_modules\dotenv" (
    echo Instalando dependencias Node...
    call npm install
)
echo.
echo Iniciando servidor Aurora... Abriendo navegador en 4 s.
start /B cmd /c "timeout /t 4 /nobreak >nul && start http://localhost:3000"
echo.
node server.js
pause
