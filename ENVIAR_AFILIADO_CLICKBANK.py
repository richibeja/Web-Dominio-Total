import os
import json
import asyncio
import random
import time
import requests
import edge_tts
from dotenv import load_dotenv
from pathlib import Path

# Cargar configuración
load_dotenv()
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
VOICE = os.getenv("VOICE_EDGE_CODE", "es-CO-SalomeNeural")

# LINK MÁGICO DE AFILIADO CAMUFLADO (SPARTAMAX)
LINK_AFILIADO = "https://web-dominio-total-4iw4.vercel.app/protoflow.html"
AUDIO_FILE = "promo_spartamax.mp3"

TEXTO_PROMO = "Hola mi deito, uy perdoname no haberte saludado hoy pero he tenido un día de locos. Oye, me acordé de ti hace un rato... ¿Tú sabrosura sigues yendo al gimnasio? Es que el hermano de una amiga probó algo natural, se llama Spartamax, y dice que ahora anda con mil de energía, rindiendo como una bestia y enfocado en todo. El pobre andaba súper agotado y esto le cambió la vida. Ella me pasó el link secreto, ahí te lo dejo por si te sirve pa' que andes como un toro. Mua, un besito lindo."

def log(msg):
    try:
        print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)
    except UnicodeEncodeError:
        # Fallback if the terminal doesn't support some characters
        print(f"[{time.strftime('%H:%M:%S')}] {msg.encode('ascii', 'replace').decode('ascii')}", flush=True)

async def generar_audio_promocional():
    if not os.path.exists(AUDIO_FILE):
        log(f"AURORA: Grabando voz para Spartamax...")
        communicate = edge_tts.Communicate(TEXTO_PROMO, VOICE, rate="+3%")
        await communicate.save(AUDIO_FILE)
        log(f"Listo: Audio guardado como {AUDIO_FILE}")
    else:
        log(f"✅ El audio {AUDIO_FILE} ya estaba grabado y listo para disparar.")

def obtener_todos_los_clientes():
    """Extrae todos los IDs únicos de la base de datos."""
    ids = set()
    try:
        if os.path.exists('bot_memory.json'):
            with open('bot_memory.json', 'r', encoding='utf-8') as f:
                data = json.load(f)
                for uid in data.get("user_preferences_learned", {}).keys():
                    ids.add(uid)
    except Exception as e:
        log(f"⚠️ Error leyendo bot_memory.json: {e}")

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
        log(f"⚠️ Error leyendo nuevos_clientes.json: {e}")

    # Añadir admin para prueba siempre
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

def disparar_bombardeo_clickbank():
    clientes = obtener_todos_los_clientes()
    if not clientes:
        log("❌ No se encontraron clientes para bombardear.")
        return

    log(f"🔥 INICIANDO BOMBARDEO MASIVO A {len(clientes)} CLIENTES 🔥")
    log(f"Link destino: {LINK_AFILIADO}")
    
    success = 0
    errors = 0

    for chat_id in clientes:
        try:
            log(f"➡️ Disparando a ID {chat_id}...")
            
            # Simular grabación de voz
            send_chat_action(chat_id, "record_voice")
            time.sleep(2)
            
            url = f"https://api.telegram.org/bot{TOKEN}/sendVoice"
            with open(AUDIO_FILE, "rb") as audio:
                caption = f"aquí te dejo el secretito del que te hablé en el audio... mírame eso y me cuentas si te sirve 🔥👇\n\n{LINK_AFILIADO}"
                resp = requests.post(url, data={"chat_id": chat_id, "caption": caption}, files={"voice": audio}, timeout=15)
                
                if resp.status_code == 200:
                    log(f"✅ Entregado a {chat_id}")
                    success += 1
                else:
                    log(f"❌ Error en {chat_id}: {resp.status_code} - {resp.text}")
                    errors += 1
            
            # Delay anti-ban para no saturar los servidores de Telegram
            time.sleep(2.5)
            
        except Exception as e:
            log(f"💥 Error crítico con {chat_id}: {e}")
            errors += 1

    log(f"\n--- REPORTE FINAL DE BOMBARDEO CLICKBANK ---")
    log(f"✅ Entregas Exitosas (Compradores potenciales): {success}")
    log(f"❌ Errores: {errors}")
    log(f"-----------------------------------------------")

if __name__ == "__main__":
    import sys
    
    log("=" * 60)
    log("SISTEMA DE VENTAS CLICKBANK - AURORA (SPARTAMAX)")
    log("=" * 60)
    
    # Pre-generar el audio siempre al correr el script
    asyncio.run(generar_audio_promocional())
    
    # Comprobar seguridad para no disparar por error
    if len(sys.argv) > 1 and sys.argv[1] == "--disparar":
        log("⚠️ ORDEN DE DISPARO CONFIRMADA. Fuego a discreción.")
        disparar_bombardeo_clickbank()
    else:
        log("⚠️ MODO SEGURO: El audio está grabado y listo en tu carpeta.")
        log("Para disparar el ataque masivo a todos los clientes, ejecuta el script con el comando:")
        log("py ENVIAR_AFILIADO_CLICKBANK.py --disparar")
