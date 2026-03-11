"""
AURORA — BIENVENIDA A NUEVOS SUSCRIPTORES 🌸
Detecta clientes nuevos en Telegram que aún no han sido saludados
y les envía un audio de bienvenida personalizado.
Ejecutar una vez, o dejarlo en loop con --loop
"""
import os, sys, json, asyncio, time, random, requests
from pathlib import Path
from dotenv import load_dotenv
from datetime import datetime

# Forzar codificación UTF-8 para evitar errores con emojis en Windows
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

load_dotenv()

ROOT     = Path(__file__).parent
APP_DIR  = ROOT / "AURORA_APP"
TOKEN    = os.getenv("TELEGRAM_BOT_TOKEN")
LINK_VIP = os.getenv("FANVUE_LINK", "https://www.fanvue.com/utopiafinca")
VOICE    = os.getenv("VOICE_EDGE_CODE", "es-CO-SalomeNeural")

# Archivo donde guardamos a quién ya saludamos y qué mensaje se le envió
YA_SALUDADOS_PATH = ROOT / "logs" / "historial_bienvenida.json"

# ── Audios de bienvenida para NUEVOS ─────────────────────────────────────────
AUDIOS_BIENVENIDA = [
    "Hola amor, qué rico que llegaste. Soy Aurora. Me alegra mucho tenerte aquí. Escríbeme cuando quieras, que yo estoy. Mua.",
    "Ey hola, bienvenido. Soy Aurora, y ya me alegró el día que llegaras. ¿Cómo te llamas vos? Cuéntame algo.",
    "Hola mi vida, bienvenido a este espacio. Soy Aurora. Hacía falta alguien como vos por aquí. ¿Cómo estás?",
    "Qué sorpresa tan rica. Hola, soy Aurora. Me alegra que hayas llegado. Escríbeme, que me muero por conocerte.",
]

CAPTIONS_BIENVENIDA = [
    f"bienvenido amor 🌸 ya llegaste al lugar correcto\n{LINK_VIP}",
    f"qué bueno tenerte acá ❤️ soy Aurora, escríbeme\n{LINK_VIP}",
    f"hola 😊 bienvenido, ya estoy aquí para vos\n{LINK_VIP}",
]

def log(msg):
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}] {msg}", flush=True)

def cargar_historial_saludados() -> dict:
    YA_SALUDADOS_PATH.parent.mkdir(exist_ok=True, parents=True)
    if YA_SALUDADOS_PATH.exists():
        try:
            return json.loads(YA_SALUDADOS_PATH.read_text(encoding="utf-8"))
        except: pass
    return {}

def guardar_historial(historial: dict):
    YA_SALUDADOS_PATH.write_text(json.dumps(historial, indent=2), encoding="utf-8")

def obtener_todos_los_clientes() -> dict:
    """Retorna {chat_id: nombre} de todos los clientes conocidos."""
    clientes = {}

    # De bot_memory.json
    mem = ROOT / "bot_memory.json"
    if mem.exists():
        try:
            data = json.loads(mem.read_text(encoding="utf-8"))
            for uid in data.get("user_preferences_learned", {}).keys():
                clientes[str(uid)] = "amor"
        except: pass

    # De nuevos_clientes.json (tiene nombres)
    nuevos = APP_DIR / "data" / "nuevos_clientes.json"
    if nuevos.exists():
        try:
            data = json.loads(nuevos.read_text(encoding="utf-8"))
            for item in data:
                uid = item.get("user_id")
                nombre = item.get("first_name") or "amor"
                if uid: clientes[str(uid)] = nombre
        except: pass

    # Admin siempre incluido
    admin = os.getenv("TELEGRAM_ADMIN_IDS", "")
    for a in admin.split(","):
        if a.strip(): clientes[a.strip()] = "amor"

    return clientes

def obtener_updates_telegram() -> list:
    """Obtiene los últimos mensajes recibidos del bot para detectar nuevos usuarios."""
    try:
        r = requests.get(
            f"https://api.telegram.org/bot{TOKEN}/getUpdates",
            params={"limit": 100, "allowed_updates": ["message"]},
            timeout=10
        )
        if r.status_code == 200:
            return r.json().get("result", [])
    except Exception as e:
        log(f"⚠️ Error obteniendo updates: {e}")
    return []

async def generar_audio_bienvenida(texto: str, path: Path) -> bool:
    try:
        import edge_tts
        comm = edge_tts.Communicate(texto, VOICE, rate="+3%")
        await comm.save(str(path))
        return True
    except Exception as e:
        log(f"❌ Error generando audio: {e}")
        return False

def enviar_bienvenida(chat_id: str, nombre: str, audio_path: Path):
    """Envía audio de bienvenida a un cliente nuevo."""
    try:
        # Simular "grabando audio..."
        requests.post(
            f"https://api.telegram.org/bot{TOKEN}/sendChatAction",
            data={"chat_id": chat_id, "action": "record_voice"}, timeout=5
        )
        time.sleep(random.uniform(2.0, 3.5))

        with open(audio_path, "rb") as audio:
            resp = requests.post(
                f"https://api.telegram.org/bot{TOKEN}/sendVoice",
                data={"chat_id": chat_id, "caption": random.choice(CAPTIONS_BIENVENIDA)},
                files={"voice": audio},
                timeout=20
            )
        if resp.status_code == 200:
            log(f"   ✅ Bienvenida enviada a {nombre} (ID: {chat_id})")
            return True
        else:
            log(f"   ⚠️ Error {resp.status_code} con {chat_id}: {resp.json().get('description','')}")
            return False
    except Exception as e:
        log(f"   ❌ Error con {chat_id}: {e}")
        return False

def revisar_y_saludar():
    historial = cargar_historial_saludados()
    todos = obtener_todos_los_clientes()

    # También revisar updates recientes para usuarios muy nuevos
    updates = obtener_updates_telegram()
    for upd in updates:
        msg = upd.get("message", {})
        user = msg.get("from", {})
        uid  = str(user.get("id", ""))
        nombre = user.get("first_name") or "amor"
        if uid and uid not in todos:
            todos[uid] = nombre

    # Filtrar los que NO han sido saludados hoy o necesitan una frase distinta
    # Para la bienvenida, solo queremos saludarlos UNA VEZ con el mensaje inicial
    nuevos = {uid: nombre for uid, nombre in todos.items() if uid not in historial}

    if not nuevos:
        log(f"✅ No hay suscriptores nuevos. Total conocidos: {len(todos)} | Ya saludados: {len(historial)}")
        return

    log(f"🌸 {len(nuevos)} suscriptores NUEVOS detectados — enviando bienvenida...")

    for chat_id, nombre in nuevos.items():
        # Seleccionar frase sin repetir (aunque para bienvenida suele ser la primera vez)
        texto_audio = random.choice(AUDIOS_BIENVENIDA)
        audio_path  = ROOT / f"bienvenida_{chat_id}.mp3"
        
        log(f"🎙️ Generando bienvenida para {nombre}: '{texto_audio[:50]}...'")
        ok = asyncio.run(generar_audio_bienvenida(texto_audio, audio_path))

        if ok:
            if enviar_bienvenida(chat_id, nombre, audio_path):
                historial[chat_id] = {
                    "fecha": datetime.now().isoformat(),
                    "mensaje": texto_audio
                }
                guardar_historial(historial)
            
            # Limpiar audio temporal
            if audio_path.exists():
                os.remove(audio_path)
                
        time.sleep(random.uniform(2.0, 4.5))

    log(f"\n🎉 Bienvenidas procesadas.")

# ── MODO LOOP (--loop): revisa cada 5 minutos ─────────────────────────────────
if __name__ == "__main__":
    modo_loop = "--loop" in sys.argv

    log("=" * 50)
    log("🌸 AURORA — BIENVENIDA A NUEVOS SUSCRIPTORES")
    if modo_loop:
        log("   Modo: LOOP — revisa cada 5 minutos")
    log("=" * 50)

    if modo_loop:
        while True:
            revisar_y_saludar()
            log("⏳ Esperando 5 minutos para próxima revisión...")
            time.sleep(300)
    else:
        revisar_y_saludar()
        log("✅ Listo. 💋")
