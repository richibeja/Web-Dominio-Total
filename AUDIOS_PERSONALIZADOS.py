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
LINK_VIP = os.getenv("FANVUE_LINK", "https://www.fanvue.com/utopiafinca")

# Táctica Cero Basura: Archivo temporal único que se sobrescribe y luego se borra.
AUDIO_FILE = "audio_temporal.mp3"

def log(msg):
    try:
        print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)
    except UnicodeEncodeError:
        print(f"[{time.strftime('%H:%M:%S')}] {msg.encode('ascii', 'replace').decode('ascii')}", flush=True)

def obtener_clientes():
    """Extrae clientes con su respectivo nombre de la base de datos."""
    clientes = {}
    
    # Intentar sacar de bot_memory.json (si tiene información de perfiles)
    try:
        p = Path("bot_memory.json")
        if p.exists():
            data = json.load(open(p, "r", encoding="utf-8"))
            if "user_preferences_learned" in data:
                for uid, prefs in data["user_preferences_learned"].items():
                    # Aquí asumo que podrías tener el nombre almacenado de alguna manera.
                    # Si no, se asigna "amor" por defecto hasta saberlo.
                    nombre = prefs.get('name', '')
                    clientes[uid] = nombre
    except Exception as e:
        log(f"⚠️ Error leyendo bot_memory.json: {e}")

    # También de nuevos_clientes.json (Suele tener el first_name)
    try:
        path_nuevos = Path("AURORA_APP/data/nuevos_clientes.json")
        if path_nuevos.exists():
            data = json.load(open(path_nuevos, "r", encoding="utf-8"))
            for item in data:
                uid = str(item.get("user_id"))
                nombre = item.get("first_name", "")
                if uid:
                    clientes[uid] = nombre
    except Exception as e:
        log(f"⚠️ Error leyendo nuevos_clientes.json: {e}")

    # Lista final filtrada, sacando los que tienen el nombre.
    return {uid: nombre for uid, nombre in clientes.items()}

async def generar_audio_personalizado(nombre):
    """Genera un audio con el nombre de pila de la persona."""
    nombre = nombre or "amor"
    # Diferentes guiones posibles para no sonar siempre igual.
    guiones = [
        f"Hola {nombre}, mi amor, hace rato no me hablas, aquí te espero... Mua.",
        f"Uy {nombre}, cómo estás mi vida? justito estaba pensando en vos.",
        f"Ey {nombre}, papi, ¿qué cuentas? Ya te extraño de verdad.",
        f"Qué milagro pues {nombre}... ya me tenías en el olvido. Espero escucharte pronto."
    ]
    texto = random.choice(guiones)
    
    # Genera el audio y pisa el anterior (Cero Basura)
    communicate = edge_tts.Communicate(texto, VOICE, rate="+3%")
    await communicate.save(AUDIO_FILE)
    return texto

def send_chat_action(chat_id, action="record_voice"):
    url = f"https://api.telegram.org/bot{TOKEN}/sendChatAction"
    try:
        requests.post(url, data={'chat_id': chat_id, 'action': action}, timeout=5)
    except:
        pass

async def procesar_envios():
    clientes = obtener_clientes()
    if not clientes:
        log("❌ No se encontraron clientes para personalizar.")
        return

    log(f"🚀 Iniciando envío PERSONALIZADO a {len(clientes)} clientes...")
    
    success, errors = 0, 0

    for chat_id, nombre in clientes.items():
        try:
            log(f"➡️ Procesando a: {nombre if nombre else 'Desconocido'} (ID {chat_id})")
            
            # 1. Generar audio temp para esta persona
            texto_generado = await generar_audio_personalizado(nombre)
            
            # 2. Enviar "grabando voz..."
            send_chat_action(chat_id, "record_voice")
            await asyncio.sleep(len(texto_generado) / 20) # Simula tiempo de grabacion aprox
            
            # 3. Enviar
            url = f"https://api.telegram.org/bot{TOKEN}/sendVoice"
            with open(AUDIO_FILE, "rb") as audio:
                caption = f"un mensajito solo para vos 💋\n{LINK_VIP}"
                resp = requests.post(url, data={"chat_id": chat_id, "caption": caption}, files={"voice": audio}, timeout=15)
                
                if resp.status_code == 200:
                    log(f"✅ ¡Entregado a {nombre}!")
                    success += 1
                else:
                    log(f"❌ Error enviando a {nombre} ({chat_id}): {resp.status_code}")
                    errors += 1
            
            await asyncio.sleep(random.uniform(2.0, 4.0)) # Anti-ban
            
        except Exception as e:
            log(f"💥 Error con {chat_id}: {e}")
            errors += 1

    # 4. LIMPIEZA CERO BASURA (Borrar el archivo temporal al final)
    if os.path.exists(AUDIO_FILE):
        os.remove(AUDIO_FILE)
        log("🧹 Limpieza: Archivo de audio temporal eliminado con éxito.")

    log(f"\n--- REPORTE FINAL DE AUDIOS PERSONALIZADOS ---")
    log(f"✅ Éxitos: {success} | ❌ Errores: {errors}")

if __name__ == "__main__":
    if not TOKEN:
        log("❌ Falta el token de Telegram en .env")
        exit(1)
    
    log("=" * 60)
    log("AURORA - MENSAJES DE VOZ PERSONALIZADOS POR NOMBRE")
    log("=" * 60)
    asyncio.run(procesar_envios())
    log("✅ Finalizado. Máquina limpia.")
