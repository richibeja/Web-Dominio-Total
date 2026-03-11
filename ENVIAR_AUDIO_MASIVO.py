import os, json, asyncio, time, random, requests, sys
import edge_tts
from dotenv import load_dotenv

# Forzar codificación UTF-8 para evitar errores con emojis en Windows
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# Cargar configuración
load_dotenv()
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
VOICE = os.getenv("VOICE_EDGE_CODE", "es-CO-SalomeNeural")
LINK_VIP = os.getenv("FANVUE_LINK", "https://www.fanvue.com/utopiafinca")

# Varios audios de saludo — se elige uno al azar para sonar más natural
GUIONES_SALUDO = [
    "Hola amor. Andé pensando en vos hoy y me dieron unas ganas locas de mandarte este mensajito. Te extrao un poquito. En serio. Mua.",
    "Ey, papi. Sólo quiero que sepas que me alegra mucho tenerte aquí. Te dejé algo rico en mi espacio privado, lo hice pensando en vos. No te lo pierdas bebé.",
    "Qué rico saludarte hoy... ando ocupada pero me acordé de vos y tuve que mandarte esto. Tengo una sorpresita guardada para vos allá, te va a encantar. Múa.",
    "Hola mi vida. No te haba escrito en un rato y ya te extrao... qué raro que me hagas falta así. Pasoéte por mi espacio privado que te dejé algo especial.",
    "Ee papi, deje de trabajar un momento y léame esto. No me gusta que pase mucho tiempo sin saber de vos. Tengo algo para vos en mi perfil privado. Te va a gustar, te lo juro."
]
TEXTO_AUDIO = random.choice(GUIONES_SALUDO)

async def generar_audio_paisa():
    print(f"🎙️ Generando la nota de voz paisa realista con la voz {VOICE}...")
    communicate = edge_tts.Communicate(TEXTO_AUDIO, VOICE, rate="+5%")
    await communicate.save("saludo_masivo.mp3")
    print("✅ Nota de voz generada con éxito (saludo_masivo.mp3)!")

def enviar_a_todos():
    print("🔍 Buscando clientes en la base de datos (bot_memory.json)...")
    try:
        with open('bot_memory.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Extraemos los IDs de las personas que han chateado con el bot
        clientes = list(data.get("user_preferences_learned", {}).keys())
        # Y también los telegram_admin_ids para que te llegue a ti también
        admin_id = os.getenv("TELEGRAM_ADMIN_IDS")
        if admin_id and admin_id not in clientes:
            clientes.append(admin_id)
            
        print(f"📲 Se han encontrado {len(clientes)} clientes para enviar la nota de voz.")
        
        for chat_id in clientes:
            print(f"⏳ Grabando y enviando audio a {chat_id}...")
            
            # 1. Simular que el bot está "grabando un audio"
            requests.post(f"https://api.telegram.org/bot{TOKEN}/sendChatAction", 
                          data={'chat_id': chat_id, 'action': 'record_voice'})
            time.sleep(3) # Pausa dramática para que el cliente vea "grabando audio..."
            
            # 2. Enviar la nota de voz como archivo real (Audio/Voice)
            url = f"https://api.telegram.org/bot{TOKEN}/sendVoice"
            with open("saludo_masivo.mp3", "rb") as audio:
                captions = [
                    f"te pensé hoy bebé 🥰 ...allá te espero\n{LINK_VIP}",
                    f"esto es sólo para vos amor 💋\n{LINK_VIP}",
                    f"te dejé algo rico... ábrelo cuando estés solo 😏\n{LINK_VIP}",
                ]
                caption_text = random.choice(captions)
                resp = requests.post(url, data={"chat_id": chat_id, "caption": caption_text}, files={"voice": audio})
                
                if resp.status_code == 200:
                    print(f"✅ ¡Entregado perfectamente a ID {chat_id}!")
                else:
                    print(f"⚠️ Error al enviar a {chat_id}. (Quizás bloqueó el bot)")
                    
    except Exception as e:
        print(f"❌ Error leyendo la base de datos: {e}")

if __name__ == "__main__":
    print("🚀 INICIANDO SISTEMA DE ENVÍO DE AUDIO MASIVO (MANUS COLOMBIA) 🚀")
    asyncio.run(generar_audio_paisa())
    enviar_a_todos()
    print("🎉 CAMPAÑA MASIVA FINALIZADA. Revisa tu Telegram.")
