"""
AURORA - GUARDIA NOCTURNA 🌙
Mantiene todos los bots corriendo TODA la noche.
- Auto-reinicia Telegram bot y Fanvue si se caen
- Envía audios de reactivación cada 2 horas
- Logs de todo lo que pasa
"""
import subprocess
import time
import os
import sys
import asyncio
import random
import requests
import json
import base64
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

# Forzar codificación UTF-8 para evitar errores con emojis en Windows
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

load_dotenv()

# ── Configuración ──────────────────────────────────────────────────────────────
ROOT       = Path(__file__).parent
APP_DIR    = ROOT / "AURORA_APP"
TOKEN      = os.getenv("TELEGRAM_BOT_TOKEN")
LINK_VIP   = os.getenv("FANVUE_LINK", "https://www.fanvue.com/utopiafinca")
VOICE      = os.getenv("VOICE_EDGE_CODE", "es-CO-SalomeNeural")

# Cada cuántos minutos enviar audio de reactivación (2 horas = 120 min)
INTERVALO_REACTIVACION_MIN = 120

# Mensajes nocturnos especiales — más íntimos a esta hora
MENSAJES_NOCTURNOS = [
    "Hola amor. ¿Todavía despierto? Yo también estoy aquí pensando en vos. Te dejé algo especial en mi espacio privado... ábrelo cuando puedas. Mua.",
    "Ey bebé. Son las {} y me acordé de vos. Tengo algo rico guardado para vos allá, solo para vos. No te lo pierdas.",
    "No me puedo dormir y apareciste en mi cabeza. Te dejé una sorpresita en mi sitio privado. Pásate, que te extraño.",
    "Mor, ¿cómo estás? Andaba despierta y pensé en vos. Tengo contenido nuevo que me muero porque lo veas. Solo pa' mis favoritos.",
]

# Mensajes directos para Fanvue — tono más íntimo (ya son suscriptores pagos)
MENSAJES_FANVUE_NOCHE = [
    "hola bebé... acabo de publicar algo nuevo que guardé especialmente para vos. ábrelo cuando estés solo 😚",
    "ey amor, son las {} y me acordé de vos. tengo algo ricísimo nuevo, solo para mis suscriptores especiales como tú 🔥",
    "no me podía dormir sin mandarte algo... subié contenido nuevo hoy pensando en vos. espero que te guste bebecito",
    "qué rico tenerte aquí en mi círculo privado... te dejé una sorpresa nueva, hecha con mucho cariño para vos 💕",
    "pensé en vos hoy, en serio. por eso subí algo especial que solo pueden ver mis favoritos. eso sos vos amor 🥰",
]

LOG_FILE = ROOT / "logs" / "guardia_nocturna.log"
LOG_FILE.parent.mkdir(exist_ok=True)

procesos = {}  # nombre -> subprocess

# ── FANVUE API ────────────────────────────────────────────────────────────────
def fanvue_headers():
    """Carga el access token de Fanvue."""
    token_path = APP_DIR / "data" / "fanvue_tokens.json"
    if not token_path.exists():
        return None
    tokens = json.loads(token_path.read_text())
    return {
        "Authorization": f"Bearer {tokens.get('access_token')}",
        "Content-Type": "application/json",
        "X-Fanvue-API-Version": "2025-06-26"
    }

def fanvue_refresh():
    """Refresca el token de Fanvue si está vencido."""
    client_id     = os.getenv("FANVUE_CLIENT_ID")
    client_secret = os.getenv("FANVUE_CLIENT_SECRET")
    if not client_id or not client_secret:
        log("⚠️ FANVUE_CLIENT_ID o FANVUE_CLIENT_SECRET no están en .env")
        return False
    token_path = APP_DIR / "data" / "fanvue_tokens.json"
    tokens = json.loads(token_path.read_text())
    encoded = base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()
    try:
        r = requests.post(
            "https://auth.fanvue.com/oauth2/token",
            headers={"Content-Type": "application/x-www-form-urlencoded", "Authorization": f"Basic {encoded}"},
            data={"grant_type": "refresh_token", "refresh_token": tokens["refresh_token"]},
            timeout=10
        )
        if r.status_code == 200:
            new = r.json()
            if "refresh_token" not in new:
                new["refresh_token"] = tokens["refresh_token"]
            token_path.write_text(json.dumps(new, indent=2))
            log("✅ Token Fanvue refrescado")
            return True
        log(f"❌ No se pudo refrescar token Fanvue: {r.status_code}")
        return False
    except Exception as e:
        log(f"❌ Error refrescando token Fanvue: {e}")
        return False

def obtener_chats_fanvue():
    """Retorna lista de chats (suscriptores) de Fanvue."""
    headers = fanvue_headers()
    if not headers:
        return []
    r = requests.get("https://api.fanvue.com/chats", headers=headers, timeout=15)
    if r.status_code == 401:
        log("⚠️ Token Fanvue vencido, refrescando...")
        if fanvue_refresh():
            headers = fanvue_headers()
            r = requests.get("https://api.fanvue.com/chats", headers=headers, timeout=15)
    if r.status_code == 200:
        data = r.json()
        return data.get("data", []) if isinstance(data, dict) else data
    log(f"⚠️ No se pudo obtener chats Fanvue: {r.status_code}")
    return []

def enviar_mensaje_fanvue(fan_uuid: str, texto: str) -> bool:
    """Envía un mensaje de texto a un suscriptor de Fanvue."""
    headers = fanvue_headers()
    if not headers:
        return False
    r = requests.post(
        f"https://api.fanvue.com/chats/{fan_uuid}/messages",
        headers=headers,
        json={"text": texto},
        timeout=15
    )
    if r.status_code == 401:
        if fanvue_refresh():
            headers = fanvue_headers()
            r = requests.post(f"https://api.fanvue.com/chats/{fan_uuid}/messages", headers=headers, json={"text": texto}, timeout=15)
    return r.status_code in [200, 201]

def despertar_suscriptores_fanvue():
    """Envía mensaje nocturno a todos los suscriptores de Fanvue."""
    hora = hora_actual()
    chats = obtener_chats_fanvue()
    if not chats:
        log("⚠️ No se encontraron suscriptores en Fanvue (o token vencido).")
        return

    log(f"💎 Despertando {len(chats)} suscriptores de Fanvue...")
    exitosos = 0
    for chat in chats:
        fan = chat.get("user", {})
        fan_uuid = fan.get("uuid")
        fan_name = fan.get("handle") or fan.get("displayName") or "amor"
        if not fan_uuid:
            continue
        texto = random.choice(MENSAJES_FANVUE_NOCHE).format(hora)
        ok = enviar_mensaje_fanvue(fan_uuid, texto)
        if ok:
            log(f"   ✅ Fanvue: mensaje enviado a @{fan_name}")
            exitosos += 1
        else:
            log(f"   ⚠️ Fanvue: no se pudo enviar a @{fan_name}")
        time.sleep(random.uniform(2.0, 4.0))  # anti-spam

    log(f"💬 Fanvue nocturno: {exitosos}/{len(chats)} mensajes entregados.")

def log(msg):
    ts  = datetime.now().strftime("%H:%M:%S")
    linea = f"[{ts}] {msg}"
    try:
        print(linea, flush=True)
    except UnicodeEncodeError:
        print(linea.encode('ascii', 'replace').decode('ascii'), flush=True)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(linea + "\n")

def hora_actual():
    return datetime.now().strftime("%H:%M")

def esta_vivo(nombre):
    p = procesos.get(nombre)
    return p is not None and p.poll() is None

def lanzar(nombre, cmd, cwd):
    if esta_vivo(nombre):
        return
    log(f"▶️  Iniciando {nombre}...")
    p = subprocess.Popen(
        cmd,
        cwd=str(cwd),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=subprocess.CREATE_NEW_CONSOLE
    )
    procesos[nombre] = p
    log(f"✅ {nombre} corriendo (PID {p.pid})")

def vigilar():
    """Revisa que cada proceso esté vivo, si no lo reinicia."""
    if not esta_vivo("telegram_bot"):
        log("⚠️  Bot Telegram caído — reiniciando...")
        lanzar("telegram_bot", [sys.executable, "telegram_bot.py"], APP_DIR)

    if not esta_vivo("fanvue"):
        log("⚠️  Fanvue caído — reiniciando...")
        lanzar("fanvue", [sys.executable, "fanvue_automation.py"], APP_DIR)

    if not esta_vivo("instagram_api"):
        log("⚠️  Instagram API caído — reiniciando...")
        lanzar("instagram_api", [sys.executable, "shared/webhook.py"], ROOT)

    if not esta_vivo("bienvenida"):
        log("⚠️  Bienvenida Nuevos caído — reiniciando...")
        lanzar("bienvenida", [sys.executable, "BIENVENIDA_NUEVOS.py", "--loop"], ROOT)

def obtener_clientes():
    ids = set()
    mem = ROOT / "bot_memory.json"
    if mem.exists():
        try:
            data = json.loads(mem.read_text(encoding="utf-8"))
            for uid in data.get("user_preferences_learned", {}).keys():
                ids.add(str(uid))
        except: pass

    nuevos = APP_DIR / "data" / "nuevos_clientes.json"
    if nuevos.exists():
        try:
            data = json.loads(nuevos.read_text(encoding="utf-8"))
            for item in data:
                uid = item.get("user_id")
                if uid: ids.add(str(uid))
        except: pass

    admin = os.getenv("TELEGRAM_ADMIN_IDS", "")
    for a in admin.split(","):
        if a.strip(): ids.add(a.strip())

    return list(ids)

async def generar_audio(texto, archivo):
    try:
        import edge_tts
        comm = edge_tts.Communicate(texto, VOICE, rate="+5%")
        await comm.save(str(archivo))
        return True
    except Exception as e:
        log(f"❌ Error generando audio: {e}")
        return False

def enviar_audio_reactivacion():
    hora = hora_actual()
    texto = random.choice(MENSAJES_NOCTURNOS).format(hora)
    audio_path = ROOT / "audio_nocturno.mp3"

    log(f"🎙️  Generando audio nocturno: '{texto[:50]}...'")
    ok = asyncio.run(generar_audio(texto, audio_path))
    if not ok:
        return

    clientes = obtener_clientes()
    if not clientes:
        log("⚠️  Sin clientes en base de datos — omitiendo audio masivo.")
        return

    log(f"📲 Enviando audio nocturno a {len(clientes)} clientes...")
    exitosos = 0
    for chat_id in clientes:
        try:
            url_action = f"https://api.telegram.org/bot{TOKEN}/sendChatAction"
            requests.post(url_action, data={"chat_id": chat_id, "action": "record_voice"}, timeout=5)
            time.sleep(random.uniform(1.5, 3.0))

            captions = [
                f"pensé en vos a esta hora 🌙 ...te espero allá\n{LINK_VIP}",
                f"no me podía dormir sin saludarte ❤️\n{LINK_VIP}",
                f"algo rico te dejé guardado bébé 😏\n{LINK_VIP}",
            ]
            url_voice = f"https://api.telegram.org/bot{TOKEN}/sendVoice"
            with open(audio_path, "rb") as audio:
                resp = requests.post(
                    url_voice,
                    data={"chat_id": chat_id, "caption": random.choice(captions)},
                    files={"voice": audio},
                    timeout=15
                )
            if resp.status_code == 200:
                exitosos += 1
            else:
                log(f"  ⚠️ No se pudo enviar a {chat_id}: {resp.status_code}")

            time.sleep(random.uniform(1.5, 2.5))  # anti-ban
        except Exception as e:
            log(f"  ❌ Error con {chat_id}: {e}")

    log(f"✅ Audio nocturno entregado a {exitosos}/{len(clientes)} clientes.")

# ── MAIN LOOP ──────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    log("=" * 55)
    log("🌙 AURORA — GUARDIA NOCTURNA INICIADA")
    log(f"   Hora de inicio: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    log(f"   Reactivación cada {INTERVALO_REACTIVACION_MIN} minutos")
    log("=" * 55)

    # Arrancar bots desde el inicio
    lanzar("telegram_bot", [sys.executable, "telegram_bot.py"], APP_DIR)
    time.sleep(5)
    lanzar("fanvue", [sys.executable, "fanvue_automation.py"], APP_DIR)
    time.sleep(3)
    lanzar("instagram_api", [sys.executable, "shared/webhook.py"], ROOT)
    time.sleep(3)
    lanzar("bienvenida", [sys.executable, "BIENVENIDA_NUEVOS.py", "--loop"], ROOT)
    time.sleep(3)

    # Primer saludo nocturno — Telegram + Fanvue
    log("📣 Enviando primer saludo nocturno a Telegram...")
    enviar_audio_reactivacion()
    log("💎 Enviando primer mensaje nocturno a suscriptores Fanvue...")
    despertar_suscriptores_fanvue()

    ultimo_envio = time.time()
    ciclo = 0

    while True:
        ciclo += 1
        time.sleep(60)  # revisar cada minuto

        # Vigilar que los bots sigan vivos
        vigilar()

        # Mostrar estado cada 10 minutos
        if ciclo % 10 == 0:
            tg  = "✅" if esta_vivo("telegram_bot") else "❌"
            fv  = "✅" if esta_vivo("fanvue")       else "❌"
            ig_api = "✅" if esta_vivo("instagram_api") else "❌"
            bn  = "✅" if esta_vivo("bienvenida")   else "❌"
            
            mins = int((time.time() - ultimo_envio) / 60)
            log(f"📊 Estado — TG:{tg} | FV:{fv} | IG_API:{ig_api} | BN:{bn} | Audio en: {INTERVALO_REACTIVACION_MIN - mins} min")

        # Enviar reactivación cada 2 horas — Telegram + Fanvue
        mins_desde_envio = (time.time() - ultimo_envio) / 60
        if mins_desde_envio >= INTERVALO_REACTIVACION_MIN:
            log(f"⏰ {INTERVALO_REACTIVACION_MIN} minutos — enviando reactivación...")
            enviar_audio_reactivacion()       # 🎙️ Audio a clientes Telegram
            despertar_suscriptores_fanvue()   # 💎 Texto a suscriptores Fanvue
            ultimo_envio = time.time()
