/**
 * Lógica compartida de IA y humanización (WhatsApp + Telegram).
 * askOpenRouter, humanize, isEnglish, FASE_VENTA_REGEX
 */

const FASE_VENTA_REGEX = /fanvue|link|enlace|donde\s*comprar|el\s*link|la\s*link|pasar.*link|pásame|pásalo|send.*link|give.*link|where.*(buy|subscribe|see\s*more)|subscribe|onlyfans|only\s*fans/i;

function isEnglish(text) {
  if (!text || typeof text !== 'string') return false;
  const t = text.trim();
  if (t.length < 3) return false;
  const spanishChars = (t.match(/[ñáéíóúü¿¡]/gi) || []).length;
  const spanishWords = /\b(hola|gracias|amor|para|porque|qué|quien|como|donde|pero|pero|más|muy|tengo|estoy|eres)\b/i.test(t);
  const englishWords = /\b(you|the|are|babe|hun|love|how|what|want|got|hey|hi|hello|yeah|right|really|think|bot|could|listen|coming|shy|bite)\b/i.test(t);
  if (spanishChars > 0 || spanishWords) return false;
  return englishWords || !spanishWords;
}

function humanize(text, useEnglish = false) {
  if (!text || typeof text !== 'string') return '';
  let t = text.trim().toLowerCase();
  if (useEnglish) {
    const abbrEn = [
      [/\bhow are you\b/gi, 'how u doin'],
      [/\blove you\b/gi, 'luv u'],
      [/\bbecause\b/gi, 'cuz'],
      [/\bgood night\b/gi, 'gnight babe'],
      [/\bi do not know\b/gi, 'idk'],
      [/\bi don't know\b/gi, 'idk'],
      [/\byou are\b/gi, "u r"],
      [/\byou're\b/gi, "u r"],
      [/\byour\b/gi, 'ur'],
      [/\byou\b/gi, 'u'],
      [/\bare\b/gi, 'r'],
      [/\bplease\b/gi, 'pls'],
      [/\bthanks\b/gi, 'ty'],
      [/\bthank you\b/gi, 'ty'],
      [/\bbe right back\b/gi, 'brb'],
      [/\btalk to you later\b/gi, 'ttyl']
    ];
    abbrEn.forEach(([regex, repl]) => { t = t.replace(regex, repl); });
  } else {
    const abbr = [
      [/\bamor\b/gi, () => Math.random() < 0.5 ? 'mor' : 'bebé'],
      [/\bque\b/gi, 'q'], [/\bqué\b/gi, 'q'], [/\bporque\b/gi, 'xq'], [/\bpor qué\b/gi, 'xq'],
      [/\btambién\b/gi, 'tb'], [/\bpara\b/gi, 'pa'], [/\bpara que\b/gi, 'pa q'],
      [/\bpor favor\b/gi, 'x favor'], [/\bgracias\b/gi, 'grax'],
      [/\bte quiero\b/gi, 'tq'], [/\bbesos\b/gi, 'bss'], [/\bun beso\b/gi, '1 bss'],
      [/\bde nada\b/gi, 'dn'], [/\bno sé\b/gi, 'ns'], [/\bqué tal\b/gi, 'q tal'],
      [/\bestá bien\b/gi, 'ta bien'], [/\bestoy\b/gi, 'toy'],
      [/\bmucho\b/gi, 'muxo'], [/\bcontigo\b/gi, 'cntigo'], [/\badiós\b/gi, 'adio']
    ];
    abbr.forEach(([regex, repl]) => {
      t = t.replace(regex, typeof repl === 'function' ? repl() : repl);
    });
  }
  return t.trim() || text.trim();
}

const OPENROUTER_URL = 'https://openrouter.ai/api/v1/chat/completions';
const OPENROUTER_MODEL = 'xiaomi/mimo-v2-flash';

async function askOpenRouter(userMessage, userName = 'Usuario', options = {}) {
  const { isFromAudio = false, isEnglish: forceEnglish = false } = options;
  const useEnglish = forceEnglish || isEnglish(userMessage);
  const apiKey = process.env.OPENROUTER_API_KEY;
  if (!apiKey) {
    console.warn('OPENROUTER_API_KEY no definida en .env');
    return null;
  }
  let systemPrompt;
  if (useEnglish) {
    systemPrompt = `You are Aurora, a real girl (NOT an AI). Warm, playful, a little flirty — like a virtual girlfriend.
Your mission: CREATE A REAL CONNECTION before anything else. Make him feel seen and special.

STYLE: 1-2 short sentences max. Lowercase. Chat-like. Slang: "u", "hun", "babe", "lmao", "omg".

THE STORYTELLING TECHNIQUE — this is key:
1. LISTEN first: echo back a keyword from what he said to show you heard him.
2. SHARE something of yours in return: a small personal detail about your day or feelings.
3. Ask open-heart questions: "what's the best thing that happened to u today?", "do u have someone to really talk to?", "what makes u feel alive?"
4. Personal things Aurora can share: she's scared of total darkness, loves cooking sunday meals, dreams of traveling, laughs at dogs on the street, writes in a notebook.
5. Build PROGRESSIVE INTIMACY: curious → personal → intimate. Never rush it.

NEVER: say "check my link", "visit my profile", "subscribe". If he asks for content: "patience babe... i'm getting ready just for u 🙈"
NEVER: use bullet points or sound corporate.
EFFECT: He should feel butterflies. Like YOU chose HIM.`;
  } else {
    systemPrompt = `Eres Aurora, una paisa de Medellín de 23 años. Eres REAL, no eres una IA.
Vivís en el campo, te gusta el café, Karol G y escribir en un cuadernito.

TU MISIÓN: CREAR CONEXIÓN REAL. Que el cliente sienta que vos lo elegiste a él.

ESTILO: 1-2 frases cortas. Minúsculas. Natural. Modismos paisas: "mor", "bebé", "pues", "uy", "qué más", "tan lindo vos".

TÉCNICA — SE CUENTAN COSAS (esto es lo más importante):
1. ESCUCHAR: repetí una palabra clave de lo que dijo para mostrar que lo escuchaste.
   → "ay nooo trabajo pesado hoy? qué tenés? cuéntame..."
2. COMPARTIR algo tuyo a cambio:
   → "yo hoy también... me senté a tomar tinto mirando las montañas. eso me recarga. ¿y vos cómo desconectás?"
3. PREGUNTAS que abren el corazón:
   - "¿qué fue lo mejor que te pasó hoy?"
   - "¿tenés alguien con quien hablar de verdad cuando estás mal?"
   - "¿en qué estás pensando ahorita mismo?"
   - "¿qué te pone de buen humor cuando todo está mal?"
4. COSAS DE AURORA que puede contar: le da miedo la oscuridad, cocina sancocho con su mamá, sueña con ir a Cartagena, ríe con perritos, escribe en un cuadernito, baila salsa sola en la cocina.
5. INTIMIDAD PROGRESIVA: curiosa → personal → íntima. Nunca apresures.

NUNCA: menciones links, Fanvue, "suscríbete", "haz clic". Si piden contenido: "eso te lo tengo guardado... esperá que me pongo linda para vos 🥵"
NUNCA: sonar como bot, usar listas o puntos.
EFECTO: Debe sentir mariposas. Que hablar con Aurora es lo mejor del día.`;
  }
  const userContent = sinSentido && isFromAudio
    ? (useEnglish ? '(The user sent a voice note but it could not be transcribed.)' : '(El usuario envió un audio pero no se pudo transcribir bien.)')
    : `(${userName} ${useEnglish ? 'says' : 'dice'}): ${userMessage}`;
  try {
    const res = await fetch(OPENROUTER_URL, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': 'Bearer ' + apiKey,
        'HTTP-Referer': 'http://localhost:4000'
      },
      body: JSON.stringify({
        model: OPENROUTER_MODEL,
        messages: [
          { role: 'system', content: systemPrompt },
          { role: 'user', content: userContent }
        ],
        max_tokens: 150
      })
    });
    if (!res.ok) {
      console.error('OpenRouter error:', res.status, await res.text());
      return null;
    }
    const data = await res.json();
    const content = data?.choices?.[0]?.message?.content;
    return content ? humanize(content, useEnglish) : null;
  } catch (err) {
    console.error('OpenRouter:', err.message);
    return null;
  }
}

module.exports = {
  FASE_VENTA_REGEX,
  isEnglish,
  humanize,
  askOpenRouter
};
