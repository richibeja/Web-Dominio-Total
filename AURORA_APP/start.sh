#!/bin/bash
# ══════════════════════════════════════════════
# AURORA - Script de inicio para Render
# Lanza: Bot Python (Telegram) + Servidor Node.js
# ══════════════════════════════════════════════

echo "🚀 Iniciando AURORA en Render..."

# Instalar dependencias Python
echo "📦 Instalando dependencias Python..."
pip install python-telegram-bot python-dotenv --quiet 2>/dev/null || true

# Iniciar el bot de Telegram (Python) en segundo plano
echo "🤖 Iniciando Bot de Telegram (Python)..."
python telegram_bot.py &
BOT_PID=$!
echo "   → Bot PID: $BOT_PID"

# Esperar 2 segundos para que el bot se inicialice
sleep 2

# Iniciar el servidor Node.js (proceso principal)
echo "🌐 Iniciando Servidor Node.js..."
node server.js

# Si Node muere, también mata el bot Python
kill $BOT_PID 2>/dev/null
