"""
AURORA — BUENOS DÍAS A TODOS 🌅
Saludo matutino natural e íntimo para clientes de Telegram y Fanvue.
"""
import os, json, asyncio, time, random, requests, base64, sys
from pathlib import Path
from dotenv import load_dotenv

# Forzar codificación UTF-8 para evitar errores con emojis en Windows
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

load_dotenv()

ROOT     = Path(__file__).parent
APP_DIR  = ROOT / "AURORA_APP"
TOKEN    = os.getenv("TELEGRAM_BOT_TOKEN")
LINK_VIP      = os.getenv("FANVUE_LINK", "https://www.fanvue.com/utopiafinca")
LINK_EBOOK    = "https://go.hotmart.com/D104419459E?ap=7c93"
LINK_CLICKBANK = "https://web-dominio-total-4iw4.vercel.app/protoflow.html"
VOICE         = os.getenv("VOICE_EDGE_CODE", "es-CO-SalomeNeural")

# Historial para no repetir
HISTORIAL_PATH = ROOT / "logs" / "historial_buenos_dias.json"

# ── Audios de buenos días para Telegram ────────────────────────────────────────
AUDIOS_MANANA = [
    "Hola amor, buenos días. Recién me desperté y lo primero que pensé fue en vos. Que tengas un día tan lindo como vos sos. Mua.",
    "Eyyy, buenos días bébé. ¿Cómo amaneciste? Yo acá, tomando tintico y pensando en vos. Espero que tu día esté buenísimo hoy.",
    "Buenos días mi vida. Amaneció hermoso por aquí y lo único que me faltaba era saludarte. ¿Cómo estás hoy?",
    "Hola papi, buenos días. Ojalá hayas dormido bien. Yo soñé cosas ricas y al despertarme pensé en mandarte este mensajito. Cuídate mucho hoy.",
    "Ey bébé, buenos días. Ya empezó el día y quería que supieras que me alegra mucho tenerte. Que hoy sea un día chévere para vos.",
]

# Captions variados para rotar productos
CAPTIONS_MANANA = [
    {"text": f"buenos días amor 🌅 pensé en vos apenas desperté\n{LINK_VIP}", "tipo": "fanvue"},
    {"text": f"que tengas un día tan lindo como vos 🌻 mira lo nuevo: {LINK_VIP}", "tipo": "fanvue"},
    {"text": f"mor, hoy quiero que aprendas a dominar mi mundo... mira esto: {LINK_EBOOK}", "tipo": "ebook"},
    {"text": f"¿quieres durar más conmigo? aquí te enseño cómo: {LINK_EBOOK} 🔥", "tipo": "ebook"},
    {"text": f"bebé, me pasaron un secreto para que andes como un toro hoy... pruébalo: {LINK_CLICKBANK}", "tipo": "clickbank"},
]

# ── Mensajes de texto para Fanvue (ya son suscriptores) ───────────────────────
MENSAJES_FANVUE_MANANA = [
    "buenos días bébé 🌅 recién me desperté y lo primero fue pensar en vos. ¿cómo amaneciste amor?",
    "ey, buenos días mi vida ☕ espero que hayas dormido bien. yo acá pensando en vos despiertita desde temprano.",
    "buenos días amor 🌻 ojalá tu día empiece tan lindo como el mío... que fue pensando en vos. cuéntame cómo estás.",
    "hola bébé, buenos días. sé que es temprano pero no me aguanté las ganas de saludarte. ¿qué planes tenés hoy?",
    "buenos días mi amor 😊 que hoy sea un día increíble para vos. acá te pienso y te mando buena energia desde tempranito.",
]

def log(msg):
    print(f"[{__import__('datetime').datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)

def cargar_historial() -> dict:
    HISTORIAL_PATH.parent.mkdir(exist_ok=True, parents=True)
    if HISTORIAL_PATH.exists():
        try:
            return json.loads(HISTORIAL_PATH.read_text(encoding="utf-8"))
        except: pass
    return {}

def guardar_historial(historial: dict):
    HISTORIAL_PATH.write_text(json.dumps(historial, indent=2), encoding="utf-8")

# ── TELEGRAM ──────────────────────────────────────────────────────────────────
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
        comm = edge_tts.Communicate(texto, VOICE, rate="+3%")
        await comm.save(str(archivo))
        return True
    except Exception as e:
        log(f"❌ Error generando audio: {e}")
        return False

def saludar_telegram():
    historial = cargar_historial()
    fecha_hoy = __import__('datetime').datetime.now().strftime('%Y-%m-%d')
    
    clientes = obtener_clientes()
    if not clientes:
        log("⚠️ Sin clientes en base de datos.")
        return

    log(f"Analizando {len(clientes)} clientes de Telegram...")
    exitosos = 0
    
    for chat_id in clientes:
        # Verificar si ya se le envió algo HOY
        if chat_id in historial and historial[chat_id].get("ultimo_saludo") == fecha_hoy:
            continue

        # Elegir un caption que no haya recibido recientemente (ej: rotar tipos)
        ultimo_tipo = historial.get(chat_id, {}).get("tipo", "")
        # Filtrar opciones para no repetir tipo si es posible
        opciones = [c for c in CAPTIONS_MANANA if c["tipo"] != ultimo_tipo]
        if not opciones: opciones = CAPTIONS_MANANA
        
        bundle = random.choice(opciones)
        texto_audio = random.choice(AUDIOS_MANANA)
        audio_path = ROOT / f"buenos_dias_{chat_id}.mp3"
        
        # Generar audio al vuelo (para que no sea el mismo archivo exacto)
        asyncio.run(generar_audio(texto_audio, audio_path))

        try:
            log(f"   ➡️ Enviando a {chat_id} (Tipo: {bundle['tipo']})")
            send_chat_action(chat_id, "record_voice")
            time.sleep(1.5)

            with open(audio_path, "rb") as audio:
                resp = requests.post(
                    f"https://api.telegram.org/bot{TOKEN}/sendVoice",
                    data={"chat_id": chat_id, "caption": bundle["text"]},
                    files={"voice": audio}, timeout=15
                )
            
            if resp.status_code == 200:
                exitosos += 1
                historial[chat_id] = {
                    "ultimo_saludo": fecha_hoy,
                    "tipo": bundle["tipo"],
                    "mensaje": texto_audio
                }
                guardar_historial(historial)
            
            if audio_path.exists(): os.remove(audio_path)
            time.sleep(random.uniform(2.0, 4.0))

        except Exception as e:
            log(f"   ❌ Error con {chat_id}: {e}")

    log(f"Telegram: {exitosos} saludos entregados hoy.")

def send_chat_action(chat_id, action):
    try:
        requests.post(f"https://api.telegram.org/bot{TOKEN}/sendChatAction", 
                     data={"chat_id": chat_id, "action": action}, timeout=5)
    except: pass

# ── FANVUE ────────────────────────────────────────────────────────────────────
def fanvue_headers():
    token_path = APP_DIR / "data" / "fanvue_tokens.json"
    if not token_path.exists(): return None
    tokens = json.loads(token_path.read_text())
    return {
        "Authorization": f"Bearer {tokens.get('access_token')}",
        "Content-Type": "application/json",
        "X-Fanvue-API-Version": "2025-06-26"
    }

def fanvue_refresh():
    cid = os.getenv("FANVUE_CLIENT_ID")
    cs  = os.getenv("FANVUE_CLIENT_SECRET")
    if not cid or not cs: return False
    token_path = APP_DIR / "data" / "fanvue_tokens.json"
    tokens = json.loads(token_path.read_text())
    encoded = base64.b64encode(f"{cid}:{cs}".encode()).decode()
    r = requests.post(
        "https://auth.fanvue.com/oauth2/token",
        headers={"Content-Type": "application/x-www-form-urlencoded", "Authorization": f"Basic {encoded}"},
        data={"grant_type": "refresh_token", "refresh_token": tokens["refresh_token"]}, timeout=10
    )
    if r.status_code == 200:
        new = r.json()
        if "refresh_token" not in new: new["refresh_token"] = tokens["refresh_token"]
        token_path.write_text(json.dumps(new, indent=2))
        log("✅ Token Fanvue refrescado")
        return True
    log(f"❌ No se pudo refrescar token Fanvue: {r.status_code}")
    return False

def saludar_fanvue():
    h = fanvue_headers()
    if not h: log("⚠️  Sin token Fanvue."); return

    # Verificar token
    r = requests.get("https://api.fanvue.com/users/me", headers=h, timeout=15)
    if r.status_code == 401:
        log("⚠️  Token vencido, refrescando...")
        if fanvue_refresh(): h = fanvue_headers()
    
    log("Enviando buenos dias masivo a suscriptores de Fanvue...")
    
    texto = random.choice(MENSAJES_FANVUE_MANANA)
    payload = {
        "text": texto,
        "includedLists": {
            "smartListUuids": ["subscribers"]
        }
    }
    
    try:
        resp = requests.post(
            "https://api.fanvue.com/chats/mass-messages",
            headers=h, json=payload, timeout=15
        )
        
        if resp.status_code in [200, 201, 202]:
            log(f"🎉 Saludo masivo de Fanvue enviado con exito: '{texto[:50]}...'")
        else:
            log(f"❌ Error enviando masivo a Fanvue ({resp.status_code}): {resp.text}")
    except Exception as e:
        log(f"❌ Error critico en Fanvue: {e}")

# ── MAIN ──────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    log("=" * 55)
    log("AURORA - BUENOS DIAS A TODOS LOS CLIENTES")
    log("=" * 55)

    log("\n[FASE 1] Telegram (audio de voz)...")
    saludar_telegram()

    log("\n[FASE 2] Fanvue (mensaje intimo de texto)...")
    saludar_fanvue()

    log("\n[OK] Todos los clientes saludados. Aurora esta activa.")
