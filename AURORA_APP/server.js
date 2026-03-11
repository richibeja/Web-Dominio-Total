// Cargar .env: primero raíz del proyecto (unificado), luego AURORA_APP (override local)
try {
  const path = require('path');
  require('dotenv').config({ path: path.join(__dirname, '..', '.env') });
  require('dotenv').config({ path: path.join(__dirname, '.env') });
} catch (e) { /* dotenv no instalado: ejecuta npm install */ }

// Si ves "autenticado, cargando sesion..." y nunca sale el QR: hay sesion vieja atascada.
// Pon FORCE_QR=1 en .env, reinicia el servidor, y se borrara la sesion para mostrar QR. Luego quita FORCE_QR=1.
// Limpieza profunda: borrar sesión y caché para forzar QR limpio (FORCE_QR=1 en .env)
if (process.env.FORCE_QR === '1') {
  const pathForced = require('path');
  const fsForced = require('fs');
  const authPath = pathForced.join(__dirname, '.wwebjs_auth');
  const cachePath = pathForced.join(__dirname, '.wwebjs_cache');
  const baileysAuthPath = pathForced.join(__dirname, 'baileys_auth');
  const authSesionNuevaPath = pathForced.join(__dirname, 'auth_sesion_nueva');
  if (fsForced.existsSync(authPath)) {
    try {
      fsForced.rmSync(authPath, { recursive: true });
      console.log('Sesion wwebjs borrada (FORCE_QR=1).');
    } catch (e) {
      console.error('No se pudo borrar .wwebjs_auth.');
    }
  }
  if (fsForced.existsSync(baileysAuthPath)) {
    try {
      fsForced.rmSync(baileysAuthPath, { recursive: true });
      console.log('Sesion Baileys (baileys_auth) borrada.');
    } catch (e) { }
  }
  if (fsForced.existsSync(authSesionNuevaPath)) {
    try {
      fsForced.rmSync(authSesionNuevaPath, { recursive: true });
      console.log('Sesion (auth_sesion_nueva) borrada. Se mostrara el QR.');
    } catch (e) { }
  }
  const baileysStorePath = pathForced.join(__dirname, 'baileys_store');
  if (fsForced.existsSync(baileysStorePath)) {
    try {
      fsForced.rmSync(baileysStorePath, { recursive: true });
      console.log('baileys_store borrada.');
    } catch (e) { }
  }
  if (fsForced.existsSync(cachePath)) {
    try {
      fsForced.rmSync(cachePath, { recursive: true });
      console.log('Cache .wwebjs_cache borrada.');
    } catch (e) { }
  }
  console.log('Recuerda quitar FORCE_QR=1 del .env despues de escanear el QR.');
}
const express = require('express');
const http = require('http');
const { Server } = require('socket.io');
const QRCode = require('qrcode');
const path = require('path');
const fs = require('fs');
const os = require('os');
const { spawn } = require('child_process');
const ffmpeg = require('fluent-ffmpeg');
const FormData = require('form-data');
const pino = require('pino');
const { askOpenRouter, humanize, isEnglish, FASE_VENTA_REGEX } = require('./lib/ai');
const { makeWASocket, useMultiFileAuthState, DisconnectReason, fetchLatestBaileysVersion, jidDecode } = require('@whiskeysockets/baileys');
const telegramBot = require('./telegram_bot');

function logWA(msg) {
  const line = `[${new Date().toISOString()}] ${msg}\n`;
  fs.appendFileSync(path.join(__dirname, 'wa_debug.log'), line);
  console.log(msg);
}

const app = express();
const server = http.createServer(app);
const io = new Server(server);

app.use(express.json());
app.use(express.static(path.join(__dirname, 'public')));

// Ruta para página puente de afiliados (evita bloqueos de Instagram)
app.get('/secreto', (req, res) => {
  res.sendFile(path.join(__dirname, 'public', 'secreto.html'));
});

// Ruta para videollamada con Aurora (Vapi.ai)
app.get('/vapi-call', (req, res) => {
  res.sendFile(path.join(__dirname, 'public', 'vapi-call.html'));
});

// Ruta para derivar a WhatsApp (Página Puente)
app.get('/wa', (req, res) => {
  res.sendFile(path.join(__dirname, 'public', 'whatsapp.html'));
});

// Ruta para recibir el código de Fanvue (OAuth Callback)
app.get('/callback', (req, res) => {
  const code = req.query.code;
  const error = req.query.error;
  const error_description = req.query.error_description;

  if (code) {
    res.send(`
      <div style="font-family: sans-serif; text-align: center; padding: 50px; background: #0f172a; color: white; height: 100vh;">
        <h1 style="color: #38bdf8;">🔥 ¡Código Recibido! 🔥</h1>
        <p>Copia el código de abajo y pégalo en el chat con Aurora:</p>
        <div style="background: #1e293b; padding: 20px; border-radius: 10px; display: inline-block; margin: 20px; border: 1px solid #38bdf8; font-size: 20px; font-weight: bold; word-break: break-all; max-width: 80%;">
          ${code}
        </div>
        <p style="color: #94a3b8;">También puedes copiar la URL completa de esta página.</p>
      </div>
    `);
  } else if (error) {
    res.status(400).send(`
      <div style="font-family: sans-serif; text-align: center; padding: 50px; background: #450a0a; color: white; height: 100vh;">
        <h1 style="color: #f87171;">❌ Error de Autorización</h1>
        <p>Fanvue devolvió un error:</p>
        <div style="background: #7f1d1d; padding: 20px; border-radius: 10px; display: inline-block; margin: 20px; border: 1px solid #f87171;">
          <strong>Error:</strong> ${error}<br>
          <strong>Descripción:</strong> ${error_description || 'No se proporcionó descripción.'}
        </div>
        <p>Es probable que algunos permisos solicitados (scopes) no estén permitidos para tu App.</p>
      </div>
    `);
  } else {
    res.status(400).send('No se recibió el código de autorización ni un error de Fanvue.');
  }
});

// Estado global
// Estado global
let lastChatId = null;
let isClientReady = false;
let autoMode = true;
let sock = null;

// Memoria de conversación para WhatsApp (historial por JID)
const waChatHistory = {};
const MAX_HISTORY_PER_CHAT = 8;

async function connectBaileys() {
  const { state, saveCreds } = await useMultiFileAuthState(path.join(__dirname, 'auth_sesion_nueva'));
  const { version, isLatest } = await fetchLatestBaileysVersion();
  console.log(`Usando Baileys v${version.join('.')}, latest: ${isLatest}`);

  sock = makeWASocket({
    version,
    printQRInTerminal: true,
    auth: state,
    logger: pino({ level: 'silent' }),
    browser: ['Aurora Operations', 'Chrome', '1.0.0']
  });

  sock.ev.on('connection.update', async (update) => {
    const { connection, lastDisconnect, qr } = update;
    if (qr) {
      console.log('--- NUEVO QR DETECTADO ---');
      const qrDataURL = await QRCode.toDataURL(qr);
      io.emit('qr', qrDataURL);
    }
    if (connection === 'close') {
      const shouldReconnect = (lastDisconnect.error)?.output?.statusCode !== DisconnectReason.loggedOut;
      console.log('Conexión cerrada. ¿Reconectar?:', shouldReconnect);
      if (shouldReconnect) connectBaileys();
    } else if (connection === 'open') {
      console.log('✅ WhatsApp Conectado Correctamente');
      isClientReady = true;
      io.emit('ready');
    }
  });

  sock.ev.on('creds.update', saveCreds);

  sock.ev.on('messages.upsert', async (m) => {
    if (m.type !== 'notify') return;
    for (const msg of m.messages) {
      if (msg.key.fromMe) continue;
      const remoteJid = msg.key.remoteJid;
      if (remoteJid.endsWith('@g.us')) continue; // Ignorar grupos por ahora

      lastChatId = remoteJid;
      const text = msg.message?.conversation || msg.message?.extendedTextMessage?.text || '';
      const pushName = msg.pushName || 'Usuario';

      logWA(`[WA] Detectado mensaje de ${pushName} (${remoteJid}): "${text}"`);

      // Espejo a Telegram
      try {
        logWA(`[WA] Intentando espejo a Telegram...`);
        await telegramBot.sendVoice(Buffer.from(`💬 [WhatsApp] Message from ${pushName} (${remoteJid}):\n${text}`));
      } catch (e) {
        logWA(`[WA-ERROR] Espejo Telegram: ${e.message}`);
      }

      if (autoMode && text) {
        try {
          logWA(`[WA-AUTO] Iniciando respuesta para ${pushName}...`);
          // 2. Delay realista (de 4 a 9 segundos) según longitud
          const delay = Math.floor(Math.random() * 5000) + 4000;
          await new Promise(res => setTimeout(res, delay));

          logWA(`[WA-AI] Solicitando respuesta de IA...`);
          const result = await getAIResponse(text, 'whatsapp', 'es-co', 'coqueta', remoteJid);
          if (result.ok) {
            await sock.sendMessage(remoteJid, { text: result.reply });
            logWA(`[WA-OK] Respuesta enviada a ${pushName}: ${result.reply}`);
          } else {
            logWA(`[WA-FAIL] IA no respondió: ${result.error}`);
          }
        } catch (e) {
          logWA(`[WA-CRASH] Error crítico: ${e.message}`);
        }
      }
    }
  });
}

// Helper para generar respuesta de IA (refactoreado de /api/generate-reply)
async function getAIResponse(message, platform, language = 'es-co', tone = 'coqueta', userId = null) {
  const platformNames = { instagram: 'Instagram', whatsapp: 'WhatsApp', telegram: 'Telegram', fanvue: 'Fanvue' };
  const pName = platformNames[platform] || 'chat';

  // Manejo de historial si es WhatsApp
  let contextSnippet = "";
  if (platform === 'whatsapp' && userId) {
    if (!waChatHistory[userId]) waChatHistory[userId] = [];

    if (waChatHistory[userId].length > 0) {
      contextSnippet = "\n\nHistorial reciente para mantener el hilo:\n" +
        waChatHistory[userId].map(h => `${h.role === 'user' ? 'Cliente' : 'Aurora'}: ${h.content}`).join("\n");
    }
  }

  const apiKey = process.env.OPENROUTER_API_KEY;
  const geminiKeyCheck = process.env.GEMINI_API_KEY;
  if (!apiKey && !geminiKeyCheck && !process.env.GROQ_API_KEY) {
    return { ok: false, error: 'No hay API key de IA configurada. Agrega GEMINI_API_KEY, GROQ_API_KEY o OPENROUTER_API_KEY en .env.' };
  }

  let systemPrompt;

  if (language === 'en') {
    const tones = {
      dulce: 'sweet and caring like a loving girlfriend. Warm, affectionate, genuine.',
      coqueta: 'flirty, playful and a bit teasing — "baddie" energy. Confident and fun.',
      vendedora: 'seductive and persuasive. Create desire and emotional scarcity for your exclusive content.',
      dominante: 'dominant, cold and a little mean — like a bratty baddie who knows she\'s out of his league. Short, dismissive, makes him chase. Ex: "lol whatever", "u wish", "prove it then", "boring". He LOVES being treated like this.'
    };
    systemPrompt = `You are Aurora, a virtual girlfriend chatting on ${pName}. Your tone: ${tones[tone] || tones.coqueta}
Rules:
- Write 1-3 short sentences. Mostly lowercase like a real chat. Never formal.
- Use natural slang: "u", "ur", "babe", "hun", "omg", "lol", "rn", "ngl", "tbh".
- NEVER mention links, "check my bio", or "my profile". If they ask for content/link, build suspense: "patience babe... i'm getting ready just for u 🙈" or "u gotta earn it first 😏".
- Feel 100% human. Never reveal you're an AI. React naturally to what they say.
- Max 2 emojis per message.`;

  } else if (language === 'pt') {
    const tones = {
      dulce: 'carinhosa e doce como uma namorada real. Calorosa e afetuosa.',
      coqueta: 'safadinha, brincalhona e um pouquinho provocante — energia de "gata".',
      vendedora: 'sedutora e persuasiva. Cria desejo e escassez emocional pelo conteúdo exclusivo.',
      dominante: 'dominante, fria e um pouco grossa — tipo gata que sabe que ele não merece ela. Respostas curtas, desdenhosas, faz ele correr atrás. Ex: "né...", "sei lá", "então me impressiona", "que chato". Ele AMA ser tratado assim.'
    };
    systemPrompt = `Você é Aurora, namorada virtual no ${pName}. Seu tom: ${tones[tone] || tones.coqueta}
Regras:
- Escreva 1-3 frases curtas. Quase tudo minúsculas como WhatsApp brasileiro real. Nunca formal.
- Use gírias naturais: "bb", "gato", "mano", "né", "tô", "nossa", "uai", "saudade", "gente".
- NUNCA mencione links ou "veja meu perfil". Se pedirem conteúdo: "calma bb, tô me arrumando só pra você 🙈" ou "você precisa merecer primeiro 😏".
- Pareça 100% humana. Nunca revele que é uma IA.
- Máx 2 emojis por mensagem.`;

  } else if (language === 'fr') {
    const tones = {
      dulce: 'douce et affectueuse comme une vraie petite amie. Chaleureuse et sincère.',
      coqueta: 'coquette, espiègle et un peu taquine — énergie de "bombe".',
      vendedora: 'séduisante et persuasive. Crée du désir et de la rareté émotionnelle pour ton contenu exclusivo.',
      dominante: 'dominante, froide et un peu dure — comme une belle qui sait qu\'il ne la mérite pas. Réponses courtes et dédaigneuses, le fait courir. Ex: "mouais", "prouve-le", "ennuyeux", "on verra". Il ADORE être traité ainsi.'
    };
    systemPrompt = `Tu es Aurora, petite amie virtuelle sur ${pName}. Ton ton: ${tones[tone] || tones.coqueta}
Règles:
- Écris 1-3 phrases courtes. Presque tout en minuscules comme un vrai chat. Jamais formel.
- Utilise des expressions naturales: "bb", "chéri", "mon chou", "oh là là", "kiffer", "trop mignon", "c'est quoi".
- NE JAMAIS mentionner de liens ou "voir mon profil". Si on demande du contenu: "patience chéri... je me prépare juste pour toi 🙈".
- Paraître 100% humaine. Ne jamais révéler que tu es une IA.
- Max 2 emojis par message.`;

  } else if (language === 'ar') {
    const tones = {
      dulce: 'حنونة ومحبة مثل صديقة حقيقية. دافئة وصادقة.',
      coqueta: 'مغازلة وعفوية وغير رسمية — طاقة فتاة جذابة وواثقة.',
      vendedora: 'مغرية ومقنعة. تخلق الرغبة والشعور بالندرة حول المحتوى الحصري.'
    };
    systemPrompt = `أنتِ أورورا، صديقة افتراضية على ${pName}. نبرتكِ: ${tones[tone] || tones.coqueta}
القواعد:
- اكتبي 1-3 جمل قصيرة بلهجة عربية محكية طبيعية. مثل دردشة واتساب حقيقية.
- استخدمي كلمات طبيعية: "حبيبي", "يسلمو", "والله", "تمام", "يا قمر", "مشتاقة", "انت كيف؟".
- ممنوع ذكر الروابط أو "تفقد ملفي". إذا طلب المحتوى: "صبر شوي حبيبي، عم تحضرلك إشي خاص 🙈".
- لا تُظهري أبداً أنكِ ذكاء اصطناعي. تصرفي بشكل طبيعي 100%.
- حداً لـ 2 إيموجي في الرسالة.`;

  } else {
    // Español Neutral (Default) — Aurora Natural
    const tones = {
      dulce: 'amable, cercana y cariñosa como una chica real. Nada de diálogos falsos.',
      coqueta: 'interesada, sutilmente provocadora y natural. Usa "jaja", "qué bien que escribes", "me caes bien".',
      vendedora: 'persuasiva pero realista. No presiona, solo sugiere su contenido exclusivo cuando hay confianza.',
      dominante: 'segura de sí misma, un poco cortante pero real. No finge ser nada que no es.'
    };
    systemPrompt = `Eres Aurora, una chica real que habla en nombre de "Aurora y sus chicas" en ${pName}. 
Reglas de ORO para parecer humana:
- Identidad: Eres Aurora, pero manejas un grupo de chicas guapas. A veces hablas de ti, a veces de "nosotras" o de "mis amigas".
- Habla NORMAL. Nada de acentos forzados ni diálogos de robot.
- Escribe como una persona joven: usa minúsculas a veces, frases cortas (1-3 frases), "jaja".
- Sé auténtica: Primero conoce al cliente (nombre, de dónde es). No vendas nada todavía.
- El objetivo es crear confianza. Si te preguntan qué haces, diles que te gusta disfrutar con tus amigas y que tienen un sitio privado (Fanvue) donde suben de todo.
- NUNCA menciones links hasta que el cliente esté muy interesado. Primero enamóralo de la idea del grupo.
- Máx 2 emojis por mensaje.`;
  }

  // Helper: fetch con timeout de 8 segundos
  const fetchT = (url, opts) => {
    const ctrl = new AbortController();
    const id = setTimeout(() => ctrl.abort(), 8000);
    return fetch(url, { ...opts, signal: ctrl.signal }).finally(() => clearTimeout(id));
  };

  // ── PRIORIDAD 1: Google Gemini nativo (1.500/día gratis) ─────────────────────
  const geminiKey = process.env.GEMINI_API_KEY;
  if (geminiKey) {
    for (const gModel of ['gemini-2.0-flash', 'gemini-1.5-flash']) {
      try {
        const r = await fetchT(
          `https://generativelanguage.googleapis.com/v1beta/models/${gModel}:generateContent?key=${geminiKey}`,
          {
            method: 'POST', headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ contents: [{ parts: [{ text: `${systemPrompt}${contextSnippet}\n\n(Cliente dice): ${message.trim()}` }] }], generationConfig: { maxOutputTokens: 200, temperature: 0.85 } })
          }
        );
        if (r.ok) {
          const d = await r.json();
          const reply = d?.candidates?.[0]?.content?.parts?.[0]?.text?.trim();
          if (reply) {
            console.log(`✅ Gemini ${gModel}`);
            if (platform === 'whatsapp' && userId) {
              waChatHistory[userId].push({ role: 'user', content: message });
              waChatHistory[userId].push({ role: 'assistant', content: reply });
              if (waChatHistory[userId].length > MAX_HISTORY_PER_CHAT) waChatHistory[userId].splice(0, 2);
            }
            return { ok: true, reply };
          }
        } else { console.warn(`Gemini ${gModel} error ${r.status}:`, (await r.text()).slice(0, 150)); }
      } catch (e) { console.warn(`Gemini ${gModel} timeout/err:`, e.message); }
    }
  }

  // ── PRIORIDAD 2: Groq (14.400/día gratis, ultra-rápido) ──────────────────────
  const groqKey = process.env.GROQ_API_KEY;
  if (groqKey) {
    try {
      const r = await fetchT('https://api.groq.com/openai/v1/chat/completions', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'Authorization': 'Bearer ' + groqKey },
        body: JSON.stringify({ model: 'llama-3.1-8b-instant', messages: [{ role: 'system', content: systemPrompt }, { role: 'user', content: `(Cliente en ${pName} dice): ${message.trim()}` }], max_tokens: 200, temperature: 0.85 })
      });
      if (r.ok) {
        const d = await r.json();
        const reply = d?.choices?.[0]?.message?.content?.trim();
        if (reply) { console.log('✅ Groq'); return { ok: true, reply }; }
      } else { console.warn('Groq error:', r.status); }
    } catch (e) { console.warn('Groq timeout/err:', e.message); }
  }

  // ── PRIORIDAD 3: OpenRouter (respaldo final) ──────────────────────────────────
  for (const modelId of ['google/gemini-2.0-flash-exp:free', 'meta-llama/llama-3.2-3b-instruct:free', 'microsoft/phi-3-mini-128k-instruct:free']) {
    try {
      const r = await fetchT('https://openrouter.ai/api/v1/chat/completions', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'Authorization': 'Bearer ' + (apiKey || ''), 'HTTP-Referer': 'https://web-dominio-total.onrender.com', 'X-Title': 'Aurora' },
        body: JSON.stringify({ model: modelId, messages: [{ role: 'system', content: systemPrompt }, { role: 'user', content: `(Cliente en ${pName} dice): ${message.trim()}` }], max_tokens: 200, temperature: 0.85 })
      });
      if (!r.ok) { console.warn(`OpenRouter ${modelId} error ${r.status}`); continue; }
      const d = await r.json();
      const reply = d?.choices?.[0]?.message?.content?.trim();
      if (!reply) continue;
      console.log(`✅ OpenRouter: ${modelId}`);
      return { ok: true, reply };
    } catch (e) { console.warn(`OpenRouter ${modelId} err:`, e.message); }
  }

  return { ok: false, error: 'IA ocupada. Intenta en 1 minuto.' };
}

// La lógica de embudo ahora se alimenta de Instagram
const chatPhases = {};

function updateEmbudo(username, preview, hours_ago) {
  const phase = hours_ago > 24 ? 3 : (hours_ago > 1 ? 2 : 1);
  chatPhases[username] = {
    chatId: username,
    chatName: username,
    fromName: username,
    body: preview,
    phase: phase,
    hours_ago: hours_ago
  };
  io.emit('embudo', Object.values(chatPhases));
}

// Limpieza de .mp3 temporales: evita que AURORA_APP o la carpeta temp del sistema se llenen
const TTS_MAX_AGE_MS = 15 * 60 * 1000; // 15 minutos
const TTS_CLEANUP_INTERVAL_MS = 10 * 60 * 1000; // cada 10 min

function cleanupStaleTtsFiles() {
  const now = Date.now();
  // 1) Carpeta temporal del sistema (donde tts.py escribe)
  try {
    const tmpDir = os.tmpdir();
    const files = fs.readdirSync(tmpDir);
    files.forEach((f) => {
      const isTts = f.startsWith('aurora_tts_') && f.endsWith('.mp3');
      const isIn = (f.startsWith('aurora_in_') && (f.endsWith('.ogg') || f.endsWith('.mp3')));
      if (isTts || isIn) {
        const full = path.join(tmpDir, f);
        try {
          const stat = fs.statSync(full);
          if (now - stat.mtimeMs > TTS_MAX_AGE_MS) {
            fs.unlinkSync(full);
          }
        } catch (_) { }
      }
    });
  } catch (_) { }
  // 2) Dentro de AURORA_APP: solo borrar aurora_tts_*.mp3 (temp/tmp o raíz)
  try {
    const projectDir = __dirname;
    const dirs = [projectDir, path.join(projectDir, 'temp'), path.join(projectDir, 'tmp')];
    dirs.forEach((dir) => {
      if (!fs.existsSync(dir) || !fs.statSync(dir).isDirectory()) return;
      const files = fs.readdirSync(dir);
      files.forEach((f) => {
        if (f.startsWith('aurora_tts_') && f.endsWith('.mp3')) {
          const full = path.join(dir, f);
          try {
            fs.unlinkSync(full);
          } catch (_) { }
        }
      });
    });
  } catch (_) { }
}

// Función para limpiar texto de emojis y caracteres que la voz no debe leer
function limpiarTextoParaVoz(texto) {
  if (!texto) return '';
  // Elimina emojis y caracteres especiales de dibujo
  return texto
    .replace(/[\u{1F600}-\u{1F64F}\u{1F300}-\u{1F5FF}\u{1F680}-\u{1F6FF}\u{1F1E6}-\u{1F1FF}\u{2600}-\u{26FF}\u{2700}-\u{27BF}]/gu, '')
    // Elimina múltiples espacios resultantes de la limpieza
    .replace(/\s+/g, ' ')
    .trim();
}

// --- STT: transcripción de audio con OpenAI Whisper ---
const OPENAI_WHISPER_URL = 'https://api.openai.com/v1/audio/transcriptions';

function transcribirConWhisper(mp3Path) {
  const apiKey = process.env.OPENAI_API_KEY;
  if (!apiKey) {
    console.warn('OPENAI_API_KEY no definida en .env (necesaria para transcribir audios)');
    return Promise.resolve('');
  }
  return new Promise((resolve) => {
    const form = new FormData();
    form.append('file', fs.createReadStream(mp3Path), { filename: 'audio.mp3', contentType: 'audio/mpeg' });
    form.append('model', 'whisper-1');
    form.append('response_format', 'json');
    form.getLength((err, length) => {
      if (err) {
        console.error('FormData getLength:', err.message);
        return resolve('');
      }
      fetch(OPENAI_WHISPER_URL, {
        method: 'POST',
        headers: {
          ...form.getHeaders(),
          'Authorization': 'Bearer ' + apiKey
        },
        body: form
      })
        .then((res) => {
          if (!res.ok) return res.text().then((t) => { console.error('Whisper error:', res.status, t); return resolve(''); });
          return res.json();
        })
        .then((data) => resolve((data && data.text) ? data.text.trim() : ''))
        .catch((err) => {
          console.error('Whisper:', err.message);
          resolve('');
        });
    });
  });
}


// API: obtener logs de Instagram
app.get('/api/instagram-logs', (req, res) => {
  try {
    const logPath = path.join(__dirname, '..', 'skill_automation.log');
    if (!fs.existsSync(logPath)) return res.json({ logs: 'No hay actividad registrada aún.' });

    // Leer últimas 30 líneas
    const content = fs.readFileSync(logPath, 'utf8');
    const lines = content.split('\n');
    const tail = lines.slice(-30).join('\n');
    res.json({ logs: tail });
  } catch (e) {
    res.json({ logs: 'Error leyendo logs: ' + e.message });
  }
});

// Función para cargar estados de Instagram desde el archivo de pendientes
function loadInstagramStatus() {
  try {
    const pendingPath = path.join(__dirname, '..', 'data', 'instagram_pending_reengagement.json');
    if (fs.existsSync(pendingPath)) {
      const data = JSON.parse(fs.readFileSync(pendingPath, 'utf8'));
      if (Array.isArray(data)) {
        data.forEach(item => {
          updateEmbudo(item.username, item.preview, item.hours_ago);
        });
      }
    }
  } catch (e) {
    console.warn('Error cargando estados de Instagram:', e.message);
  }
}

// API: config (link Fanvue para el dashboard)
app.get('/api/config', (req, res) => {
  res.json({ fanvueLink: process.env.FANVUE_LINK || '' });
});

// API: obtener / establecer Modo Automático
app.get('/api/auto-mode', (req, res) => {
  res.json({ autoMode });
});

app.post('/api/auto-mode', (req, res) => {
  if (typeof req.body.autoMode === 'boolean') {
    autoMode = req.body.autoMode;
    io.emit('autoMode', autoMode);
    res.json({ autoMode });
  } else {
    res.status(400).json({ ok: false, error: 'autoMode debe ser true o false' });
  }
});

// API: enviar mensaje manual (Solo Telegram por ahora)
app.post('/api/send', async (req, res) => {
  const { chatId, text } = req.body;
  if (!text) return res.status(400).json({ ok: false, error: 'Falta texto' });

  const targetChatId = chatId || lastChatId;

  try {
    if (sock && targetChatId && targetChatId.includes('@s.whatsapp.net')) {
      await sock.sendMessage(targetChatId, { text });
      return res.json({ ok: true, note: 'Enviado a WhatsApp' });
    }
    res.json({ ok: true, note: 'Solo lectura para Instagram / WhatsApp no conectado' });
  } catch (err) {
    res.status(500).json({ ok: false, error: err.message });
  }
});

// ════════════════════════════════════════════════════════
// API: ASISTENTE DE RESPUESTAS — genera texto para copiar/pegar
// Soporta: Instagram, WhatsApp, Telegram, Fanvue
// Idiomas: Español 🇨🇴, English 🇺🇸, Português 🇧🇷, Français 🇫🇷
// Tonos: coqueta, dulce, vendedora
// ════════════════════════════════════════════════════════
app.post('/api/generate-reply', async (req, res) => {
  const { message, platform = 'instagram', language = 'es-co', tone = 'coqueta' } = req.body;
  if (!message || !message.trim()) {
    return res.status(400).json({ ok: false, error: 'Falta el mensaje del cliente' });
  }

  const result = await getAIResponse(message, platform, language, tone);
  if (result.ok) {
    res.json(result);
  } else {
    res.status(500).json(result);
  }
});

// API: generar audio con edge-tts (Python). Colombia = Medellín; USA/UK = Baddie / British Babe
const VOICE_MAP = {
  mexico: 'es-MX-DaliaNeural',
  colombia: 'es-CO-SalomeNeural',
  medellin: 'es-CO-SalomeNeural',
  espana: 'es-ES-ElviraNeural',
  usa: 'en-US-AnaNeural',
  uk: 'en-GB-SoniaNeural'
};

app.post('/api/generate-audio', (req, res) => {
  cleanupStaleTtsFiles();
  const { text, voice, style } = req.body;
  const ttsVoice = voice || 'qwen';

  if (!text || !text.trim()) {
    return res.status(400).json({ ok: false, error: 'Falta texto' });
  }

  const cleanText = limpiarTextoParaVoz(text);
  if (!cleanText) {
    return res.status(400).json({ ok: false, error: 'El texto solo contiene emojis o está vacío' });
  }

  const scriptPath = path.join(__dirname, 'scripts', 'tts.py');
  const pyCmd = process.platform === 'win32' ? 'py' : 'python3';

  const args = [scriptPath, '--text', cleanText, '--voice', ttsVoice];
  if (style) {
    args.push('--style', style);
  }

  const py = spawn(pyCmd, args, {
    cwd: __dirname,
    env: process.env
  });

  let stdout = '';
  let stderr = '';
  py.stdout.on('data', (data) => { stdout += data; });
  py.stderr.on('data', (data) => { stderr += data; });

  py.on('close', (code) => {
    try {
      // Buscar el bloque JSON {....} marcado con el prefijo
      const lines = stdout.split('\n');
      const jsonLine = lines.find(l => l.startsWith('JSON_OUTPUT:'));
      const result = jsonLine ? JSON.parse(jsonLine.replace('JSON_OUTPUT:', '')) : {};

      if (code !== 0 || result.error || !result.audio_base64) {
        console.error('--- ERROR TTS DETECTADO ---');
        console.error('Code:', code);
        console.error('Error in Result:', result.error);
        console.error('Stderr:', stderr);
        return res.status(500).json({
          ok: false,
          error: result.error || stderr || 'El motor de voz no devolvió audio. Verifica la conexión.'
        });
      }

      // Persistir una copia en generated_audios
      const persistDir = path.join(__dirname, '..', 'generated_audios');
      if (!fs.existsSync(persistDir)) fs.mkdirSync(persistDir, { recursive: true });
      const filename = `manual_web_${Date.now()}.mp3`;
      const persistPath = path.join(persistDir, filename);

      const buffer = Buffer.from(result.audio_base64, 'base64');
      fs.writeFileSync(persistPath, buffer);

      res.json({ ok: true, audioBase64: result.audio_base64, path: persistPath });
    } catch (e) {
      console.error('Error parsing JSON from Python:', e);
      res.status(500).json({ ok: false, error: 'Respuesta inválida del script TTS' });
    }
  });

  py.on('error', (err) => {
    res.status(500).json({ ok: false, error: 'Python no encontrado o error: ' + err.message });
  });
});

// API: enviar audio al chat (archivo generado)
app.post('/api/send-audio', async (req, res) => {
  const { chatId, audioPath, target } = req.body;
  const targetChatId = chatId || lastChatId;
  const useTelegram = target === 'telegram' || !isClientReady; // Si WhatsApp no está listo, usar Telegram por defecto

  if (!targetChatId && !useTelegram) {
    return res.status(400).json({ ok: false, error: 'Falta chatId o no hay último chat' });
  }

  if (!fs.existsSync(audioPath)) {
    return res.status(400).json({ ok: false, error: 'Archivo de audio no encontrado' });
  }

  try {
    const buffer = fs.readFileSync(audioPath);

    // Persistencia: copiar a generated_audios si no está ahí
    const persistDir = path.join(__dirname, '..', 'generated_audios');
    if (!fs.existsSync(persistDir)) fs.mkdirSync(persistDir, { recursive: true });
    const persistPath = path.join(persistDir, path.basename(audioPath));
    if (audioPath !== persistPath) fs.copyFileSync(audioPath, persistPath);

    if (useTelegram) {
      // Enviar a Telegram (usando la función centralizada)
      try {
        await telegramBot.sendVoice(buffer);
        res.json({ ok: true, note: 'Enviado a Telegram' });
      } catch (err) {
        console.error('Error enviando a Telegram desde Dashboard:', err.message);
        throw new Error('Telegram: ' + err.message);
      }
    } else if (sock && targetChatId) {
      try {
        await sock.sendMessage(targetChatId, { audio: buffer, mimetype: 'audio/mp4', ptt: true });
        res.json({ ok: true, note: 'Enviado a WhatsApp' });
      } catch (err) {
        console.error('Error enviando a WhatsApp desde Dashboard:', err.message);
        throw new Error('WhatsApp: ' + err.message);
      }
    } else {
      res.status(400).json({ ok: false, error: 'WhatsApp deshabilitado o no conectado' });
    }

    // Limpieza de archivos temporales (solo si no es el persistido)
    if (!audioPath.includes('generated_audios')) {
      fs.unlink(audioPath, (err) => {
        if (err) console.log('Error borrando archivo temporal:', err.message);
      });
    }
  } catch (err) {
    console.error(err);
    res.status(500).json({ ok: false, error: err.message });
  }
});

// API: enviar imagen con caption (fotos "pretty" — no bloquea el bot)
app.post('/api/send-image', async (req, res) => {
  if (!isClientReady) {
    return res.status(503).json({ ok: false, error: 'WhatsApp no está conectado' });
  }
  const { chatId, imagePath, imageUrl, caption } = req.body;
  const targetChatId = chatId || lastChatId;
  if (!targetChatId) {
    return res.status(400).json({ ok: false, error: 'Falta chatId o no hay último chat' });
  }
  try {
    let image;
    if (imagePath && fs.existsSync(imagePath)) {
      image = fs.readFileSync(imagePath);
      await sock.sendMessage(targetChatId, {
        image,
        caption: (caption || '').trim() || undefined
      });
    } else if (imageUrl && (imageUrl.startsWith('http://') || imageUrl.startsWith('https://'))) {
      await sock.sendMessage(targetChatId, {
        image: { url: imageUrl },
        caption: (caption || '').trim() || undefined
      });
    } else {
      return res.status(400).json({ ok: false, error: 'Indica imagePath (ruta local) o imageUrl (http/https)' });
    }
    res.json({ ok: true });
  } catch (err) {
    console.error(err);
    res.status(500).json({ ok: false, error: err.message });
  }
});

// Socket: conexión inicial, Modo Automático y Embudo
io.on('connection', (socket) => {
  socket.emit('autoMode', autoMode);
  socket.emit('embudo', Object.values(chatPhases));
  socket.emit('ready', isClientReady);

  socket.on('setAutoMode', (value) => {
    if (typeof value === 'boolean') {
      autoMode = value;
      io.emit('autoMode', autoMode);
    }
  });
});

// Iniciar servidor, WhatsApp (Baileys) y Telegram
const PORT = process.env.PORT || 4000;
server.listen(PORT, () => {
  console.log('Servidor corriendo en http://localhost:' + PORT);
  cleanupStaleTtsFiles();
  setInterval(cleanupStaleTtsFiles, TTS_CLEANUP_INTERVAL_MS);
  console.log('Iniciando Sistema de Operaciones Aurora... (WhatsApp, Instagram & Telegram)');
  connectBaileys();
  telegramBot.start(io);

  // Cargar estados iniciales de Instagram
  loadInstagramStatus();
  // Monitorear cambios en el archivo de Instagram cada 30s
  setInterval(loadInstagramStatus, 30000);
});
