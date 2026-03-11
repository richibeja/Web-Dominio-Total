@echo off
title 💋 AURORA — IMPERIO DE VENTAS TOTAL
color 0D
cd /d "%~dp0"

echo.
echo  ╔══════════════════════════════════════════════════════════╗
echo  ║   💋  A U R O R A  —  SISTEMA DE VENTAS COMPLETO       ║
echo  ║      Telegram + Instagram + Threads + Dashboard         ║
echo  ╚══════════════════════════════════════════════════════════╝
echo.

echo [1/7] 🧹 Limpiando procesos antiguos...
taskkill /f /im node.exe >nul 2>&1
taskkill /f /im python.exe >nul 2>&1
taskkill /f /im py.exe >nul 2>&1
timeout /t 2 >nul

echo [2/7] 🖥️  Lanzando Dashboard Web (Control Maestro)...
echo (Nota: El Dashboard ahora incluye la conexión de WhatsApp)
cd AURORA_APP
start "🖥️ DASHBOARD" node server.js
timeout /t 3 >nul
cd ..

echo [3/7] 🤖 Lanzando Bot Principal Aurora (Telegram)...
cd AURORA_APP
start "💋 BOT TELEGRAM" py telegram_bot.py
timeout /t 4 >nul
cd ..

echo [4/7] 💬 Lanzando Bot de Atencion al Cliente (IA Inteligente)...
start "💬 ATENCION CLIENTES" py BOT_ATENCION_CLIENTES.py
timeout /t 4 >nul

echo [5/7] 📱 Lanzando Espejo de WhatsApp (Baileys)...
echo ⚠️  IMPORTANTE: Escanea el QR en http://localhost:4000 si no estás conectado.
cd AURORA_APP
start "📱 WHATSAPP" node server.js
timeout /t 5 >nul
cd ..

echo [6/7] 📡 Lanzando Servidor API de Instagram (Webhook)...
start "📡 INSTAGRAM API" py INSTAGRAM_API_SERVER.py
timeout /t 4 >nul

echo [7/8] 📸 Lanzando Respondedor de Instagram (Navegador)...
start "📸 INSTAGRAM BROWSER" py -u INSTAGRAM_BOT.py
timeout /t 5 >nul

echo [8/8] 🕷️ Lanzando Bot de Threads (Trafico Viral)...
start "🕷️ THREADS BOT" py THREADS_BOT.py cuenta_esclava_1
timeout /t 3 >nul

echo.
echo  ╔══════════════════════════════════════════════════════════╗
echo  ║                                                          ║
echo  ║   ✅  ¡EL IMPERIO ESTA VIVO!                             ║
echo  ║                                                          ║
echo  ║   🚀 Dashboard:    http://localhost:4000                ║
echo  ║   💋 Telegram:     Activo                               ║
echo  ║   📱 WhatsApp:     Activo (Espejo)                      ║
echo  ║   📸 Instagram:    Activo (Navegador + API)             ║
echo  ║   🕷️ Threads:      Activo                               ║
echo  ║                                                          ║
echo  ╚══════════════════════════════════════════════════════════╝
echo.
echo No cierres esta ventana a menos que quieras detener el monitoreo.
pause
