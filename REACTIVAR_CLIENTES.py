import os
import json
import asyncio
import time
import random
import requests
import edge_tts
from dotenv import load_dotenv
from pathlib import Path

# Cargar configuración
load_dotenv()
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
VOICE = os.getenv("VOICE_EDGE_CODE", "es-CO-SalomeNeural")
LINK_VIP = os.getenv("FANVUE_LINK", "https://www.fanvue.com/utopiafinca")

# Guiones de reactivación — el efecto "ella pensó en mí"
GUIONES_REACTIVACION = [
    "Hola amor. Qué perdido me tenís... andaba por aquí y me acordé de vos de la nada. Me pusiste a sonreír. Te dejé algo guardado en mi espacio privado, algo que sé que te va a gustar. Pasaé a verme. Mua.",
    "Ey bebé, hace rato que no sé nada de vos y ya te extrao de verdad. Pasoé un rato pensando en vos y decidí mandarte esta nota. Hay algo especial esperando por vos, solo para vos. Ya sabés dónde encontrarme.",
    "Mi vida, no me abandones así pues. Acá sigo yo, pensando en vos. Te tengo preparada una sorpresita en mi espacito privado. Ven que me muero por saber cómo estás.",
    "Papi, me preocupé porque no supe nada tuyo. ¿Estás bien? Mandame un mensajito dandoé yo soy. Y miré que te dejé algo rico en mi página privada... hecho con mucho cariño. Solo para vos.",
]
GUION_REACTIVACION = random.choice(GUIONES_REACTIVACION)

AUDIO_FILE = "reactivacion_clientes.mp3"

async def generar_audio_reactivacion():
    print(f"AURORA: Generando nota de voz de reactivacion con la voz {VOICE}...")
    communicate = edge_tts.Communicate(GUION_REACTIVACION, VOICE, rate="+5%")
    await communicate.save(AUDIO_FILE)
    print(f"Listo: Audio generado: {AUDIO_FILE}")

def obtener_clientes():
    """Obtiene clientes únicos de bot_memory.json y nuevos_clientes.json"""
    ids = set()
    
    # De bot_memory.json
    try:
        if os.path.exists('bot_memory.json'):
            with open('bot_memory.json', 'r', encoding='utf-8') as f:
                data = json.load(f)
                learned = data.get("user_preferences_learned", {})
                for uid in learned.keys():
                    ids.add(uid)
    except Exception as e:
        print(f"⚠️ Error leyendo bot_memory.json: {e}")

    # De nuevos_clientes.json
    try:
        path_nuevos = Path("AURORA_APP/data/nuevos_clientes.json")
        if path_nuevos.exists():
            with open(path_nuevos, 'r', encoding='utf-8') as f:
                data = json.load(f)
                for item in data:
                    uid = item.get("user_id")
                    if uid:
                        ids.add(str(uid))
    except Exception as e:
        print(f"⚠️ Error leyendo nuevos_clientes.json: {e}")
        
    # Añadir admin para prueba si está configurado
    admin_ids = os.getenv("TELEGRAM_ADMIN_IDS", "").split(",")
    for aid in admin_ids:
        if aid.strip():
            ids.add(aid.strip())
            
    return list(ids)

def send_chat_action(chat_id, action="record_voice"):
    url = f"https://api.telegram.org/bot{TOKEN}/sendChatAction"
    try:
        requests.post(url, data={'chat_id': chat_id, 'action': action}, timeout=5)
    except:
        pass

def enviar_reactivacion():
    clientes = obtener_clientes()
    if not clientes:
        print("❌ No se encontraron clientes para reactivar.")
        return

    print(f"AURORA: Iniciando reactivacion para {len(clientes)} clientes...")
    
    success = 0
    errors = 0

    for chat_id in clientes:
        try:
            print(f"➡️ Procesando ID {chat_id}...")
            
            # 1. Simular grabación
            send_chat_action(chat_id, "record_voice")
            time.sleep(2)
            
            # 2. Enviar audio
            url = f"https://api.telegram.org/bot{TOKEN}/sendVoice"
            with open(AUDIO_FILE, "rb") as audio:
                captions_reac = [
                    f"te extrao mor 🥰 no te me pierdas... ahí te espero\n{LINK_VIP}\n\nO si quieres charlar un ratico conmigo, llámame tocando aquí 📞👇\nhttps://web-dominio-total-4iw4.vercel.app/aurora-llamada.html",
                    f"pensé en vos hoy y tuve que mandarte esto ❤️\n{LINK_VIP}\n\n¿Tienes 1 minutico? Llámame por acá, me encantaría escucharte 📞👇\nhttps://web-dominio-total-4iw4.vercel.app/aurora-llamada.html",
                    f"ya tenís rato sin venir a verme... vuelve bebé 💋\n{LINK_VIP}\n\nSi prefieres podemos hablar por teléfono un ratico, toca aquí y llámame 📞👇\nhttps://web-dominio-total-4iw4.vercel.app/aurora-llamada.html",
                ]
                caption = random.choice(captions_reac)
                resp = requests.post(url, data={
                    "chat_id": chat_id, 
                    "caption": caption
                }, files={"voice": audio}, timeout=10)
                
                if resp.status_code == 200:
                    print(f"✅ Enviado con éxito a {chat_id}")
                    success += 1
                else:
                    print(f"❌ Error en {chat_id}: {resp.status_code} - {resp.text}")
                    errors += 1
            
            # 3. Delay anti-ban (importante)
            time.sleep(1.5)
            
        except Exception as e:
            print(f"💥 Error crítico con {chat_id}: {e}")
            errors += 1

    print(f"\n--- REPORTE FINAL ---")
    print(f"✅ Exitos: {success}")
    print(f"❌ Errores: {errors}")
    print(f"---------------------")

if __name__ == "__main__":
    asyncio.run(generar_audio_reactivacion())
    enviar_reactivacion()
