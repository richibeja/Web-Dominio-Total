@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo.
echo ===== DIAGNÓSTICO AURORA =====
echo.

echo [1] Node.js
node -v 2>nul
if errorlevel 1 (
    echo     ERROR: Node no está instalado o no está en el PATH.
    echo     Instala desde https://nodejs.org
) else (
    echo     OK
)
echo.

echo [2] Dependencias (node_modules)
if exist "node_modules\dotenv" (
    echo     OK - dotenv encontrado
) else (
    echo     ERROR: Falta npm install. Ejecuta: npm install
)
if exist "node_modules\whatsapp-web.js" (
    echo     OK - whatsapp-web.js encontrado
) else (
    echo     ERROR: Falta npm install
)
echo.

echo [3] Archivo .env
if not exist ".env" (
    echo     ERROR: No existe .env. Copia .env.example a .env y pon tus claves.
) else (
    echo     OK - .env existe
    findstr /b "OPENROUTER_API_KEY=sk-" .env >nul 2>&1 && echo     OK - OPENROUTER_API_KEY parece configurada || echo     AVISO: OPENROUTER_API_KEY puede estar vacía o de ejemplo
    findstr /b "OPENAI_API_KEY=sk-" .env >nul 2>&1 && echo     OK - OPENAI_API_KEY parece configurada || echo     AVISO: OPENAI_API_KEY puede estar vacía (necesaria para transcribir audios)
)
echo.

echo [4] Python (para TTS / enviar voz)
py -V 2>nul
if errorlevel 1 (
    python -V 2>nul
    if errorlevel 1 (
        echo     ERROR: Python no encontrado. Instala Python y añádelo al PATH.
    ) else (
        echo     OK - python
    )
) else (
    echo     OK - py
)
echo.

echo [5] FFmpeg (para transcribir audios entrantes)
ffmpeg -version 2>nul | findstr /i "ffmpeg" >nul
if errorlevel 1 (
    echo     AVISO: FFmpeg no encontrado en PATH. Los audios entrantes no se transcribirán.
) else (
    echo     OK
)
echo.

echo [6] Carpeta del proyecto
echo     Estás en: %CD%
echo     Para iniciar: node server.js
echo     O doble clic en INICIAR.bat
echo.
echo ===== FIN DIAGNÓSTICO =====
pause
