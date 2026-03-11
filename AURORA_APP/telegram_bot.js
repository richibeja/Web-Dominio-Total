const { Telegraf } = require('telegraf');
const path = require('path');
const fs = require('fs');

// Configuración de Telegram
const botToken = process.env.TELEGRAM_BOT_TOKEN;
const operacionesId = process.env.TELEGRAM_OPERACIONES_ID || process.env.TELEGRAM_CHAT_ID;

if (!botToken) {
    console.error('[telegram_bot] ERROR: TELEGRAM_BOT_TOKEN no definido en .env');
}

const bot = new Telegraf(botToken);
let ioInstance = null;

// Mapa de audios generados recientemente para el dashboard
const audioCache = new Map();

/**
 * Inicia el bot de Telegram y permite la interacción con el Dashboard (Socket.io)
 */
function start(io) {
    ioInstance = io;

    if (!botToken) return;

    bot.on('voice', async (ctx) => {
        // Si el mensaje viene del grupo de operaciones, ignorar para este bot simple
        if (ctx.chat.id.toString() === operacionesId) return;

        // Si viene de un chat privado, notificar al grupo de operaciones
        try {
            if (operacionesId) {
                await ctx.telegram.forwardMessage(operacionesId, ctx.chat.id, ctx.message.message_id);
            }
        } catch (e) {
            console.error('[telegram_bot] Error reenviando audio:', e.message);
        }
    });

    bot.on('message', async (ctx) => {
        // Evitar que el bot se responda a sí mismo o procese cosas del grupo
        if (ctx.chat.id.toString() === operacionesId) return;

        // Si es un mensaje privado, reenviar al grupo de operaciones (Espejo)
        try {
            if (operacionesId && ctx.message.text) {
                await ctx.telegram.sendMessage(operacionesId, `💬 Mensaje de ${ctx.from.first_name || 'Usuario'} (@${ctx.from.username || 'n/a'}):\n${ctx.message.text}`);
            }
        } catch (e) {
            console.error('[telegram_bot] Error en espejo Telegram:', e.message);
        }
    });

    // bot.launch() omitido para evitar conflicto 409 con telegram_bot.py
    // El bot JS solo se usa para enviar audios, no para recibir.
    console.log('[telegram_bot] Funciones de envío activadas (Polling deshabilitado para JS)');

    // Manejo de cierre gracioso
    process.once('SIGINT', () => bot.stop('SIGINT'));
    process.once('SIGTERM', () => bot.stop('SIGTERM'));
}

/**
 * Envía un archivo de voz (buffer) al grupo de operaciones o al último chat activo
 */
async function sendVoice(buffer, chatId = null) {
    const targetId = chatId || operacionesId;
    if (!targetId || !botToken) {
        throw new Error('No hay ID de destino o token de bot');
    }

    return bot.telegram.sendVoice(targetId, { source: buffer });
}

module.exports = {
    start,
    sendVoice
};
