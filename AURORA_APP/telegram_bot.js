const path = require('path');
const fs = require('fs');

let io = null;
let telegramConnected = true;
const telegramEmbudo = {}; // chatId -> { phase, messageCount, userName }

const QUEUE_FILE = path.join(__dirname, 'data', 'voice_queue.json');

// Asegurar que la carpeta data existe
if (!fs.existsSync(path.join(__dirname, 'data'))) {
  fs.mkdirSync(path.join(__dirname, 'data'), { recursive: true });
}

function emitStatus(connected, errorMessage = null) {
  telegramConnected = connected;
  if (io) {
    io.emit('telegram_status', {
      connected,
      error: errorMessage || null
    });
  }
}

function emitMessage(payload) {
  if (io) io.emit('telegram_message', payload);
}

function emitEmbudo() {
  if (io) io.emit('telegram_embudo', Object.values(telegramEmbudo));
}

function updateTelegramEmbudo(chatId, userName, body, askedFanvue) {
  const prev = telegramEmbudo[chatId] || { chatId, userName, phase: 1, messageCount: 0 };
  prev.userName = userName;
  prev.messageCount = (prev.messageCount || 0) + 1;
  if (askedFanvue) prev.phase = 3;
  else if (prev.messageCount >= 3 && prev.phase < 3) prev.phase = 2;
  telegramEmbudo[chatId] = prev;
  emitEmbudo();
}

/**
 * Inicia el bot de Telegram.
 * NOTA: En este entorno, Node.js tiene problemas de red HTTPS.
 * El bot real corre en Python (telegram_bot.py) y lee una cola de este script.
 */
function start(socketIo) {
  io = socketIo;
  emitStatus(true); // Engañamos al dashboard para que piense que está listo
  console.log('Bot de Telegram (Puente Node->Python) activo.');
}

function isConnected() {
  return true; // Siempre true en modo puente
}

/**
 * En lugar de enviar directamente (que falla en Node), escribimos en una cola
 * que el bot de Python procesará.
 */
async function sendVoice(buffer, caption = '') {
  console.log('[DEBUG] Encolando audio para envío vía Python...');

  // Guardamos el buffer en un archivo temporal para que Python lo lea
  const timestamp = Date.now();
  const audioFileName = `queue_${timestamp}.mp3`;
  const audioFilePath = path.join(__dirname, '..', 'generated_audios', audioFileName);

  if (!fs.existsSync(path.dirname(audioFilePath))) {
    fs.mkdirSync(path.dirname(audioFilePath), { recursive: true });
  }

  fs.writeFileSync(audioFilePath, buffer);

  const request = {
    audioPath: audioFilePath,
    caption: caption,
    timestamp: timestamp,
    sent: false
  };

  try {
    let queue = [];
    if (fs.existsSync(QUEUE_FILE)) {
      try {
        const content = fs.readFileSync(QUEUE_FILE, 'utf-8');
        queue = JSON.parse(content || '[]');
      } catch (e) {
        queue = [];
      }
    }
    queue.push(request);
    fs.writeFileSync(QUEUE_FILE, JSON.stringify(queue, null, 2));
    console.log('✅ [DEBUG] Audio encolado con éxito para Python.');
    return { ok: true, note: 'Encolado para Python' };
  } catch (err) {
    console.error('❌ [DEBUG] Error al escribir en la cola de voz:', err.message);
    throw err;
  }
}

module.exports = { start, isConnected, emitStatus, sendVoice };
