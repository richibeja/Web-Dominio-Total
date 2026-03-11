@echo off
title 💋 AURORA - CONECTAR WHATSAPP (MIRROR BOT)
color 0B
cd /d "%~dp0\AURORA_APP"

echo.
echo  ╔══════════════════════════════════════════════════════════╗
10: echo  ║   💬  A U R O R A  —  CONEXIÓN WHATSAPP (BAILEYS)     ║
11: echo  ║      Escanea el QR para activar el Espejo a Telegram  ║
12: echo  ╚══════════════════════════════════════════════════════════╝
echo.

echo [1/3] Limpiando procesos antiguos de Node...
taskkill /F /IM node.exe /T 2>nul
timeout /t 2 >nul

echo [2/3] Instalando dependencias necesarias (solo si faltan)...
npm install @whiskeysockets/baileys pino qrcode socket.io express --no-fund --no-audit

echo [3/3] Iniciando Servidor Aurora con WhatsApp...
echo.
echo ⚠️  MIRA EL NAVEGADOR EN: http://localhost:4000
echo 📱 ABRE WHATSAPP > DISPOSITIVOS VINCULADOS > VINCULAR DISPOSITIVO.
echo.

node server.js

pause
