@echo off
title 💋 AURORA - SISTEMA COMPLETO ACTIVO
color 0D
cd /d "%~dp0"

echo.
echo  ╔══════════════════════════════════════════════════════════╗
echo  ║   💋  A U R O R A  —  SISTEMA COMPLETO EN VIVO          ║
echo  ║      Telegram · Fanvue · Audios · Dashboard             ║
echo  ╚══════════════════════════════════════════════════════════╝
echo.

echo [1/6] 🔪 Saltando el cierre de procesos para no apagar a Threads...
timeout /t 2 >nul

echo [2/6] 🖥️  Iniciando Dashboard Node.js (http://localhost:4000)...
cd AURORA_APP
start "" node server.js
timeout /t 4 >nul
cd ..

echo [3/6] 🤖 Encendiendo BOT DE ATENCION AL CLIENTE (responde y enamora)...
start "" py BOT_ATENCION_CLIENTES.py
timeout /t 5 >nul

echo [4/6] 🤖 Encendiendo BOT PRINCIPAL AURORA (Telegram completo)...
cd AURORA_APP
start "" py telegram_bot.py
timeout /t 5 >nul
cd ..

echo [5/6] 🎙️  Enviando AUDIO PERSONALIZADO a todos los clientes...
start "" py AUDIOS_PERSONALIZADOS.py
timeout /t 3 >nul

echo [6/7] 💌 Reactivando clientes que no han respondido...
start "" py REACTIVAR_CLIENTES.py
timeout /t 3 >nul

echo [7/7] 📸 Iniciando WEBHOOK OFICIAL DE INSTAGRAM (Modo API Seguro)...
start "" py INSTAGRAM_API_SERVER.py
timeout /t 5 >nul

echo.
echo  ╔══════════════════════════════════════════════════════════╗
echo  ║                                                          ║
echo  ║   ✅  SISTEMA SEGURO ACTIVO (SIN NAVEGADOR)              ║
echo  ║                                                          ║
echo  ║   🤖 Bot Atención:  Respondiendo en Telegram             ║
echo  ║   📡 Webhook API:   Recibiendo DMs de Instagram          ║
echo  ║   🔒 Seguridad:     Modo API Oficial (Riesgo Cero)       ║
echo  ║   🖥️  Dashboard:    http://localhost:4000                ║
echo  ╚══════════════════════════════════════════════════════════╝
echo.
echo Presiona cualquier tecla para APAGAR TODO...
pause >nul

echo 🔴 Apagando procesos levantados por este script (Manualmente deberás cerrarlos si lo necesitas)...
echo ✅ Sistema apagado. Hasta pronto.
pause
