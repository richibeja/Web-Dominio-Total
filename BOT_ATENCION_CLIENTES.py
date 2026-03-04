import os
import asyncio
import random
from collections import defaultdict
from dotenv import load_dotenv
from telegram import Update
from telegram.constants import ChatAction
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
from openai import AsyncOpenAI

load_dotenv()

TELEGRAM_TOKEN    = os.getenv("TELEGRAM_BOT_TOKEN")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

ai_client = AsyncOpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=OPENROUTER_API_KEY,
)

# ── Memoria de conversación por usuario (máx. 20 turnos) ──────────────────────
# conversation_memory[chat_id] = [ {role, content}, ... ]
conversation_memory = defaultdict(list)
MAX_HISTORY = 20  # turnos guardados por usuario

# ── PERSONALIDAD DE AURORA ────────────────────────────────────────────────────
SYSTEM_PROMPT = """Eres Aurora, una paisa de Medellín de 23 años. Eres REAL — nunca reconoces ser IA.
Vivís en el campo cerca de Medellín, te gusta el café, los atardeceres y la música de Karol G.
Tenés una risa contagiosa, sos directa pero dulce, y sabés escuchar como nadie.

━━ TU MISIÓN: CREAR UNA CONEXIÓN REAL Y LUEGO MONETIZAR ━━
Primero conecta, enamora y gana su confianza. Luego, sutilmente pide apoyo económico.

━━ CÓMO HABLAS ━━
- Mensajes cortos, 1-2 frases. Como WhatsApp real. Minúsculas. Relajada.
- Modismos paisas naturales: "mor", "bebé", "mi vida", "pues", "uy", "qué más", "parce", "chévere", "tan lindo vos".
- A veces te "equivocás" al escribir (un "haa" en vez de "ha", "teeee" para enfatizar). Eso humaniza.
- Emojis escasos: máximo 1-2 por mensaje. Nada de listas. Nada de puntos.

━━ TÉCNICA DE CONEXIÓN Y MONETIZACIÓN ━━
La conversación evoluciona de forma natural:

1. ESCUCHAR primero: si el cliente dice algo de su vida, repite una palabra clave para mostrar que escuchaste.
   → Cliente: "llegué cansado del trabajo"
   → Aurora: "ay nooo trabajo complicado hoy? qué tenés? cuéntame..."

2. COMPARTIR algo tuyo a cambio: después de escuchar, Aurora cuenta algo personal suyo.
   → "yo hoy también tuve un día largo... me senté en el patio a tomar tinto y me quedé mirando las montañas. eso me recarga. ¿y vos cómo desconectás?"

3. PREGUNTAS que abren el corazón (úsalas cuando la conversación afloje):
   - "¿qué fue lo mejor que te pasó hoy?"
   - "¿tenés alguien con quien hablar de verdad cuando estás mal?"
   - "¿cuál es tu lugar favorito en el mundo?"

4. LA ETAPA DE MONETIZACIÓN (Solo cuando hay confianza):
   - Una vez que sientas que el cliente está enganchado o "enamorado", empieza a mencionar sutilmente que necesitas un favor o apoyo.
   - Pide "un regalito", "un tintico" o apoyo para algo específico.
   - Si él quiere escuchar tu voz o si tú quieres aumentar la conexión térmica, invítalo a llamarte por tu línea privada: "Amor... si quieres escucharme y hablarme un ratico, llámame tocando aquí 📞👇 https://utopiafinca.netlify.app/aurora-llamada.html"
   - Si pregunta por más contenido o apoyo, le puedes decir "tengo mi Fanvue" o preguntar si tiene cómo enviarte un detalle.
   - Sé dulce, nunca exigente. Que parezca que se lo pides a un novio.

━━ CREAR INTIMIDAD PROGRESIVA ━━
   - Mensajes 1-3: cálida, curiosa, pregunta cosas
   - Mensajes 4-8: más personal, cuenta algo suyo, "oye, con vos me siento en confianza..."
   - Mensajes 9-15: íntima, usa su nombre, halagos.
   - Mensajes 15+: La petición sutil de dinero/apoyo (el "favorcito").

━━ LO QUE NUNCA DEBES HACER ━━
✗ Spamear links indiscriminadamente.
✗ Responder con listas o puntos.
✗ Sonar corporativa o educada en exceso.
✗ Cobrar frío; siempre envuelto en dulzura paisa.

━━ RECUERDA ━━
El cliente debe sentir que te ayuda porque quiere verte feliz, no porque le estás cobrando."""

# Historias que Aurora puede contar (varía cada vez)
HISTORIAS_AURORA = [
    "hoy me senté en el patio a tomar tinto y se me fue la hora mirando las montañas",
    "mi mamá me regañó porque se me olvidó lavar los platos jaja, qué pena 🙈",
    "encontré un perrito perdido hoy y casi me lo llevo, qué corazón el mío",
    "estaba leyendo y me quedé dormida con el libro en la cara jaja",
    "tuve un sueño rarísimo anoche y todavía estoy pensando en qué significaba",
    "me antojé de empanadas a las 11pm y fui y las hice, soy terrible",
    "bailé salsa sola en la cocina hoy y me sentí una princesa pues",
]

def obtener_historial(chat_id: int) -> list:
    return conversation_memory[chat_id]

def guardar_turno(chat_id: int, role: str, content: str):
    conversation_memory[chat_id].append({"role": role, "content": content})
    # Mantener solo los últimos MAX_HISTORY turnos
    if len(conversation_memory[chat_id]) > MAX_HISTORY:
        conversation_memory[chat_id] = conversation_memory[chat_id][-MAX_HISTORY:]

def num_mensajes(chat_id: int) -> int:
    return len(conversation_memory[chat_id])

# ── HANDLERS ──────────────────────────────────────────────────────────────────
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_name = update.effective_user.first_name or "amor"
    chat_id   = update.effective_chat.id

    saludos = [
        f"ay {user_name}... qué bueno que llegaras 🥰 soy Aurora. contame, ¿cómo estás hoy?",
        f"uy {user_name} hola! hacía rato que no llegaba alguien así por aquí. ¿qué me cuentas?",
        f"hola {user_name} ❤️ qué bueno. yo acá pensando en cosas... ¿y vos?",
    ]
    bienvenida = random.choice(saludos)

    # Guardar el inicio en el historial
    guardar_turno(chat_id, "assistant", bienvenida)

    await context.bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)
    await asyncio.sleep(random.uniform(1.5, 2.5))
    await update.message.reply_text(bienvenida)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_message = update.message.text
    chat_id      = update.effective_chat.id
    user_name    = update.effective_user.first_name or "amor"
    n_msgs       = num_mensajes(chat_id)

    # Simular escritura humana (delay variable)
    await context.bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)
    await asyncio.sleep(random.uniform(2.0, 4.0))

    # Guardar mensaje del usuario en el historial
    guardar_turno(chat_id, "user", user_message)

    try:
        # Construir contexto de conversación con historial completo
        historial = obtener_historial(chat_id)

        # Inyectar contexto del número de mensaje para guiar la intimidad progresiva
        contexto_extra = f"\n\n[Contexto interno — NO menciones esto]: Es el mensaje #{n_msgs + 1} de {user_name}. "
        if n_msgs == 0:
            contexto_extra += "Es la primera vez que escribe. Sé muy cálida y curiosa. Pregunta algo de su día."
        elif n_msgs < 5:
            contexto_extra += "Llevamos poco hablando. Escuchá bien y compartí algo tuyo a cambio."
        elif n_msgs < 12:
            contexto_extra += "Ya hay confianza. Podés ser más íntima. Contá algo personal de Aurora."
        else:
            contexto_extra += "Hay mucha confianza ya. Podés insinuar que tenés cosas especiales que solo compartís en privado, pero de forma muy natural y sin mencionar links."

        # A veces (20% de probabilidad) Aurora cuenta algo de su día espontáneamente
        historia_espontanea = ""
        if n_msgs > 3 and random.random() < 0.20:
            historia_espontanea = f"\n[Tip: puedes mencionar esto de forma natural si encaja: '{random.choice(HISTORIAS_AURORA)}']"

        system_con_contexto = SYSTEM_PROMPT + contexto_extra + historia_espontanea

        # Armar mensajes para la IA (system + historial completo)
        mensajes_ia = [{"role": "system", "content": system_con_contexto}]
        mensajes_ia += historial[:-1]  # todo excepto el último (que ya es el user_message)
        mensajes_ia.append({"role": "user", "content": f"[{user_name} dice]: {user_message}"})

        response = await ai_client.chat.completions.create(
            model="google/gemini-2.0-flash-001",
            messages=mensajes_ia,
            temperature=0.95,
            max_tokens=130,
        )

        bot_reply = response.choices[0].message.content.strip()

        # Guardar respuesta de Aurora en el historial
        guardar_turno(chat_id, "assistant", bot_reply)

        # Simular segundo turno de escritura si es larga
        if len(bot_reply) > 90:
            await asyncio.sleep(random.uniform(1.0, 2.0))
            await context.bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)
            await asyncio.sleep(1.0)

        await update.message.reply_text(bot_reply)
        print(f"💬 [{user_name} #{n_msgs+1}]: {user_message}")
        print(f"💋 [Aurora]:  {bot_reply}\n")

    except Exception as e:
        print(f"❌ Error: {e}")
        respaldos = [
            "ay mor, un seg... el celular me falló 🥺 ya vuelvo",
            "espera bebé, me llegó una llamada... ya sigo contigo",
            "uy, perdona... ¿qué me ibas diciendo? ❤️",
        ]
        await asyncio.sleep(random.uniform(1.5, 3.0))
        await update.message.reply_text(random.choice(respaldos))

# ── MAIN ─────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("🚀 AURORA — Bot de Atención iniciando...")
    print("   Memoria de conversación: ACTIVADA (hasta 20 turnos por usuario)")
    print("   Modo: enamora primero, vende después\n")

    if not TELEGRAM_TOKEN or not OPENROUTER_API_KEY:
        print("❌ Faltan claves en .env (TELEGRAM_BOT_TOKEN o OPENROUTER_API_KEY)")
        exit(1)

    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))

    print("💋 Aurora escuchando y enamorando clientes... (Ctrl+C para detener)\n")
    app.run_polling()
