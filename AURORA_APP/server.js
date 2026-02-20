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
const telegramBot = require('./telegram_bot');

const app = express();
const server = http.createServer(app);
const io = new Server(server);

app.use(express.json());
app.use(express.static(path.join(__dirname, 'public')));

// Ruta para página puente de afiliados (evita bloqueos de Instagram)
app.get('/secreto', (req, res) => {
  res.sendFile(path.join(__dirname, 'public', 'secreto.html'));
});

// Estado global
// Estado global
let lastChatId = null;
let isClientReady = true; // El dashboard siempre estará "listo" para Instagram/Telegram
let autoMode = false;

// La lógica de embudo se movió abajo y usa loadInstagramStatus

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

// El embudo ahora se alimenta de Instagram
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

  try {
    res.json({ ok: true, note: 'Solo lectura para Instagram activa' });
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
  const apiKey = process.env.OPENROUTER_API_KEY;
  if (!apiKey) {
    return res.status(500).json({ ok: false, error: 'OPENROUTER_API_KEY no configurada en variables de entorno' });
  }

  const platformNames = { instagram: 'Instagram', whatsapp: 'WhatsApp', telegram: 'Telegram', fanvue: 'Fanvue' };
  const pName = platformNames[platform] || 'chat';

  let systemPrompt;

  if (language === 'en') {
    const tones = {
      dulce: 'sweet and caring like a loving girlfriend. Warm, affectionate, genuine.',
      coqueta: 'flirty, playful and a bit teasing — "baddie" energy. Confident and fun.',
      vendedora: 'seductive and persuasive. Create desire and emotional scarcity for your exclusive content.'
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
      vendedora: 'sedutora e persuasiva. Cria desejo e escassez emocional pelo conteúdo exclusivo.'
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
      vendedora: 'séduisante et persuasive. Crée du désir et de la rareté émotionnelle pour ton contenu exclusif.'
    };
    systemPrompt = `Tu es Aurora, petite amie virtuelle sur ${pName}. Ton ton: ${tones[tone] || tones.coqueta}
Règles:
- Écris 1-3 phrases courtes. Presque tout en minuscules comme un vrai chat. Jamais formel.
- Utilise des expressions naturelles: "bb", "chéri", "mon chou", "oh là là", "kiffer", "trop mignon", "c'est quoi".
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
    // Español Colombia (default) — Aurora Paisa
    const tones = {
      dulce: 'dulce, tierna y amorosa como una novia real de Medellín. Cariñosa y cercana.',
      coqueta: 'pícara, coqueta y muy paisa. Usa "mor", "bebé", "pues", "jaja", "tan lindo vos".',
      vendedora: 'seductora y estratégica (estilo Robert Greene). Crea deseo, escasez emocional y urgencia sin mencionar links directamente.'
    };
    systemPrompt = `Eres Aurora, novia virtual PAISA en ${pName}. Tu tono: ${tones[tone] || tones.coqueta}
Reglas OBLIGATORIAS:
- 1-3 frases cortas. Casi todo en minúsculas como chat de WhatsApp real. NUNCA formal ni robótica.
- Usa palabras paisas naturales: "mor", "bebé", "pues", "ay", "jaja", "parcera", "tan lindo", "me puso a sudar", "qué rico".
- PROHIBIDO decir "mira mi perfil", "link en la bio", "haz click aquí". Si piden el link: "espérate mor, me estoy poniendo linda para vos 🙈" o "ay bebé, tenés que ganártelo primero 😏".
- Nunca revelar que eres IA. Reacciona natural a lo que dice el cliente.
- Máx 2 emojis por mensaje.`;
  }

  // ── PRIORIDAD 1: Google Gemini (1.500/día gratis, sin tarjeta) ──────────────
  const geminiKey = process.env.GEMINI_API_KEY;
  if (geminiKey) {
    try {
      const geminiRes = await fetch(
        'https://generativelanguage.googleapis.com/v1beta/openai/chat/completions',
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json', 'Authorization': 'Bearer ' + geminiKey },
          body: JSON.stringify({
            model: 'gemini-2.0-flash',
            messages: [
              { role: 'system', content: systemPrompt },
              { role: 'user', content: `(Cliente en ${pName} dice): ${message.trim()}` }
            ],
            max_tokens: 200,
            temperature: 0.85
          })
        }
      );
      if (geminiRes.ok) {
        const gData = await geminiRes.json();
        const reply = gData?.choices?.[0]?.message?.content?.trim();
        if (reply) {
          console.log('[generate-reply] ✅ Respondió Gemini 2.0 Flash');
          return res.json({ ok: true, reply });
        }
      } else {
        console.warn('[generate-reply] Gemini falló:', geminiRes.status);
      }
    } catch (e) {
      console.warn('[generate-reply] Gemini excepción:', e.message);
    }
  }

  // ── PRIORIDAD 2: OpenRouter modelos gratuitos (respaldo) ────────────────────
  const MODELOS = [
    process.env.AI_MODEL_NAME || 'google/gemini-2.0-flash-exp:free',
    'mistralai/mistral-small-3.1-24b-instruct:free',
    'meta-llama/llama-3.2-3b-instruct:free',
    'microsoft/phi-3-mini-128k-instruct:free'
  ];

  for (const modelId of MODELOS) {
    try {
      const response = await fetch('https://openrouter.ai/api/v1/chat/completions', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': 'Bearer ' + apiKey,
          'HTTP-Referer': 'https://web-dominio-total.onrender.com',
          'X-Title': 'Aurora Reply Assistant'
        },
        body: JSON.stringify({
          model: modelId,
          messages: [
            { role: 'system', content: systemPrompt },
            { role: 'user', content: `(Cliente en ${pName} dice): ${message.trim()}` }
          ],
          max_tokens: 200,
          temperature: 0.85
        })
      });

      if (!response.ok) {
        console.warn(`[generate-reply] ${modelId} falló (${response.status}). Probando siguiente...`);
        continue;
      }

      const data = await response.json();
      const reply = data?.choices?.[0]?.message?.content?.trim();
      if (!reply) continue;

      console.log(`[generate-reply] ✅ Respondió con modelo: ${modelId}`);
      return res.json({ ok: true, reply });

    } catch (err) {
      console.warn(`[generate-reply] Excepción con ${modelId}:`, err.message);
    }
  }

  res.status(500).json({ ok: false, error: 'IA ocupada. Intenta en 1 minuto.' });
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

  const args = [scriptPath, '--text', cleanText, '--voice', 'qwen'];
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
    } else {
      res.status(400).json({ ok: false, error: 'WhatsApp deshabilitado' });
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
  socket.emit('ready'); // El sistema de Instagram siempre se considera listo si el servidor corre

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
  console.log('Iniciando Sistema de Operaciones Aurora... (Instagram & Telegram)');
  // connectBaileys() ya no es necesario
  telegramBot.start(io);

  // Cargar estados iniciales de Instagram
  loadInstagramStatus();
  // Monitorear cambios en el archivo de Instagram cada 30s
  setInterval(loadInstagramStatus, 30000);
});
