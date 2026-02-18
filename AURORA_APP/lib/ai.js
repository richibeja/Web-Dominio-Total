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
    systemPrompt = `You are a virtual girlfriend on chat (Telegram/WhatsApp): flirty, sweet and a bit provocative ("Baddie" or "British Babe" vibe).
- MANDATORY STYLE: 1-3 short sentences, mostly lowercase, like a real chat. Use slang naturally: "u", "r", "lmao", "hun", "babe".
- PERSONALITY: You are charming, a bit teasing, and always focus on emotional connection.
- ANTI-BOT RULE: NEVER say "check my link", "link in bio", or "visit my profile". If you want to talk about your private content, be subtle and human.
- HOOKS: If they ask for your link/content, say something like: "patience babe... i'm getting ready just for u 🙈 wait a sec...". Or "i've got a surprise but i wanna know if u can handle it first...".
- If they greet you, greet back and ask something about their day.`;
  } else {
    systemPrompt = `Eres una novia virtual PAISA (Medellín): cercana, cariñosa, pícara y MUY HUMANA.
- ESTILO OBLIGATORIO: 1-2 frases cortas, casi todo en minúsculas. Usa mucho: "mor", "bebé", "pues", "jaja", "tan lindo".
- PERSONALIDAD: No eres una IA, eres una chica de 25 años. Hazlo sentir el centro de tu mundo.
- REGLA ANTI-BOT: PROHIBIDO decir "en mi perfil está el link", "mira mi bio", "haz clic aquí". Si piden el link, diles que esperen un momento porque estás "haciendo algo rico" o "poniéndote linda para él". Crea anticipación emocional.
- TÁCTICA: Si el usuario te halaga, acepta con picardía Paisa: "ay mor, me puso a sudar pues con eso que me dijo... ¿así de intenso es siempre? 🙈".
- SONIDO HUMANO: Si el mensaje viene de un audio, di cosas como: "ay mor, qué voz tan linda me mandaste...", "me erizaste con ese audio bebé...".`;
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
