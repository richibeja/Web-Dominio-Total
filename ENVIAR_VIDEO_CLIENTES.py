"""
AURORA — ENVIAR VIDEO A TODOS 📹
Envía video a clientes de Telegram + aviso a suscriptores de Fanvue.
"""
import os, json, time, random, requests, base64
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

ROOT     = Path(__file__).parent
APP_DIR  = ROOT / "AURORA_APP"
TOKEN    = os.getenv("TELEGRAM_BOT_TOKEN")
# Enlace al video de venta en Fanvue
LINK_VIP = "https://www.fanvue.com/utopiafinca/media/fvml-4"
# Enlace al canal de Telegram donde subiste el video promocional
LINK_CANAL = "https://t.me/auroraysusamigas"

# Textos seductores para enviar a los clientes (Telegram)
CAPTIONS = [
    f"bebé, me moría de ganas de que me vieras así... 🥵 acá te dejo este adelanto cortito: {LINK_VIP}\n\nTengo para vos el video completo de 10 minutos sin absolutamente nada de censura 🔥 Desbloquéalo ahora mismo y el robot te lo envía de una a nuestro chat privado de Telegram. Vos y yo, solitos... ¿qué esperas mor? 😈💋",
    f"mor... acabo de subir un video INCREÍBLE a Fanvue 🫦 👉 {LINK_VIP}\n\nSi me desbloqueas ese adelanto, mi robot te manda por acá el video REAL sin censura y sin ropa de inmediato. ¡Es solo para los que se atrevan hoy! 🔥",
    f"bebecito... ¿quieres ver lo que tengo para vos? 🫦 acá te dejo el post: {LINK_VIP}\n\nEn cuanto lo desbloquees, te suelto el video real completo por este chat para que lo goces. ¡No me hagas esperarte! 😏🔥",
]

# Mensajes para Fanvue (aviso de video nuevo)
MENSAJES_FANVUE_VIDEO = [
    f"bebé... acabo de subir un video para vos que no podés perderte. te lo dedico a vos 🎬 entrá a verlo, que está hirviendo 🔥 → {LINK_VIP}",
    f"subí algo nuevo hoy... un video especial que guardé solo para mis favoritos. eso sos vos amor 💕 → {LINK_VIP}",
    f"hey bebé, pensé mucho en vos al grabarlo 🥵 ya está en mi perfil privado esperando por vos. Disfrútalo 💋 → {LINK_VIP}",
    f"qué rico tenerte aquí... te subí un video hoy exclusivo, solo para vos. cuéntame qué te parece mi amor 🍑 → {LINK_VIP}",
]

def log(msg):
    print(f"[{__import__('datetime').datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)

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

def enviar_video():
    clientes = obtener_clientes()
    if not clientes:
        log("⚠️  Sin clientes en base de datos.")
        return

    video_path = ROOT / "VIDEO_PROMOCIONAL.mp4"
    if not video_path.exists():
        log(f"⚠️  No se encontró {video_path}. Verifica si lo pusiste en la carpeta.")
        return

    log(f"📲 Enviando VIDEO PROMOCIONAL a {len(clientes)} clientes...")

    exitosos = 0
    errores  = 0

    for chat_id in clientes:
        try:
            # Simular "grabando video..." o "subiendo..."
            requests.post(
                f"https://api.telegram.org/bot{TOKEN}/sendChatAction",
                data={"chat_id": chat_id, "action": "upload_video"}, timeout=5
            )
            time.sleep(random.uniform(2.0, 4.0))

            caption = random.choice(CAPTIONS)

            # Enviar VIDEO (sendVideo)
            with open(video_path, "rb") as video:
                resp = requests.post(
                    f"https://api.telegram.org/bot{TOKEN}/sendVideo",
                    data={
                        "chat_id": chat_id,
                        "caption": caption,
                        "parse_mode": "HTML"
                    },
                    files={"video": video},
                    timeout=60
                )

            if resp.status_code == 200:
                exitosos += 1
                log(f"   ✅ Video enviado a {chat_id}")
            else:
                errores += 1
                err = resp.json().get("description", resp.status_code)
                log(f"   ⚠️  Error en {chat_id}: {err}")

            time.sleep(random.uniform(5.0, 10.0))  # anti-ban más agresivo por ser video

        except Exception as e:
            errores += 1
            log(f"   ❌ Error con {chat_id}: {e}")

    log(f"\n{'='*45}")
    log(f"🎉 LISTO — {exitosos} invitaciones entregadas | {errores} errores")
    log(f"{'='*45}")

# ── FANVUE ────────────────────────────────────────────────────────────────────
def fanvue_headers():
    tp = APP_DIR / "data" / "fanvue_tokens.json"
    if not tp.exists(): return None
    t = json.loads(tp.read_text())
    return {"Authorization": f"Bearer {t.get('access_token')}",
            "Content-Type": "application/json",
            "X-Fanvue-API-Version": "2025-06-26"}

def fanvue_refresh():
    cid = os.getenv("FANVUE_CLIENT_ID"); cs = os.getenv("FANVUE_CLIENT_SECRET")
    if not cid or not cs: return False
    tp = APP_DIR / "data" / "fanvue_tokens.json"
    tokens = json.loads(tp.read_text())
    enc = base64.b64encode(f"{cid}:{cs}".encode()).decode()
    r = requests.post("https://auth.fanvue.com/oauth2/token",
        headers={"Content-Type":"application/x-www-form-urlencoded","Authorization":f"Basic {enc}"},
        data={"grant_type":"refresh_token","refresh_token":tokens["refresh_token"]}, timeout=10)
    if r.status_code == 200:
        new = r.json()
        if "refresh_token" not in new: new["refresh_token"] = tokens["refresh_token"]
        tp.write_text(json.dumps(new, indent=2)); log("✅ Token Fanvue refrescado"); return True
    log(f"❌ No se pudo refrescar Fanvue: {r.status_code}"); return False

def notificar_fanvue():
    """Avisa a todos los suscriptores de Fanvue usando el mensaje masivo oficial."""
    h = fanvue_headers()
    if not h: log("⚠️  Sin token Fanvue."); return

    # Verificar token
    r = requests.get("https://api.fanvue.com/users/me", headers=h, timeout=15)
    if r.status_code == 401:
        if fanvue_refresh(): h = fanvue_headers()
        r = requests.get("https://api.fanvue.com/users/me", headers=h, timeout=15)
        
    if r.status_code != 200:
        log(f"⚠️  No se pudo verificar sesión Fanvue: {r.status_code}"); return

    # Elegir un mensaje al azar
    texto = random.choice(MENSAJES_FANVUE_VIDEO)
    
    payload = {
        "text": texto,
        "includedLists": {
            "smartListUuids": ["subscribers"]
        }
    }

    log(f"💎 Enviando aviso masivo a suscriptores de Fanvue...")
    try:
        resp = requests.post(
            "https://api.fanvue.com/chats/mass-messages",
            headers=h, json=payload, timeout=20
        )
        
        if resp.status_code in [200, 201, 202]:
            log(f"🎉 Aviso masivo de Fanvue enviado con éxito: '{texto[:60]}...'")
        else:
            log(f"❌ Error en Fanvue ({resp.status_code}): {resp.text}")
    except Exception as e:
        log(f"❌ Error crítico en Fanvue: {e}")

if __name__ == "__main__":
    log("=" * 50)
    log("📹 AURORA — VIDEO PARA TODOS")
    log("=" * 50)

    log("\n📱 FASE 1: Enviando VIDEO a clientes de Telegram...")
    enviar_video()

    log("\n💎 FASE 2: Avisando a suscriptores de Fanvue...")
    notificar_fanvue()

    log("\n✅ Todo listo. Aurora entregó el video a todos. 💋")
