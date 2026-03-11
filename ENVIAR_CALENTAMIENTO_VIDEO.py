import os
import json
import asyncio
import time
from pathlib import Path
from dotenv import load_dotenv
import requests

# Forzar codificación UTF-8
import sys
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

load_dotenv()

ROOT = Path(__file__).parent
APP_DIR = ROOT / "AURORA_APP"
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
VIDEO_PATH = ROOT / "content" / "videos" / "grok-video-c11b00ec-b3b1-4994-a664-a985c4ed9f86.mp4"
FANVUE_LINK = os.getenv("FANVUE_LINK", "https://www.fanvue.com/utopiafinca")

def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)

def obtener_clientes():
    ids = set()
    nuevos = APP_DIR / "data" / "nuevos_clientes.json"
    if nuevos.exists():
        try:
            data = json.loads(nuevos.read_text(encoding="utf-8"))
            for item in data:
                uid = item.get("user_id")
                if uid: ids.add(str(uid))
        except: pass
    
    # También admins
    admin = os.getenv("TELEGRAM_ADMIN_IDS", "")
    for a in admin.split(","):
        if a.strip(): ids.add(a.strip())
    return list(ids)

def enviar_teaser():
    if not TOKEN:
        log("❌ No se encontró TELEGRAM_BOT_TOKEN en .env")
        return

    if not VIDEO_PATH.exists():
        log(f"❌ No se encontró el video en {VIDEO_PATH}")
        return

    clientes = obtener_clientes()
    if not clientes:
        log("⚠️ No hay clientes registrados para calentar.")
        return

    log(f"🔥 Iniciando 'CALENTAMIENTO' con video exclusivo para {len(clientes)} clientes...")

    caption = (
        "¡Mor! 🫦 Te dejé un regalito por acá...\n\n"
        "Este es solo un adelanto de lo que tengo en mi VIP. Si quieres ver el video completo sin censura y que hablemos rico, ¡suscríbete ahora! 👇\n\n"
        f"💎 MI VIP: {FANVUE_LINK}\n\n"
        "Muaaa 😘"
    )

    exitosos = 0
    for chat_id in clientes:
        try:
            log(f"   🎥 Enviando teaser a {chat_id}...")
            url = f"https://api.telegram.org/bot{TOKEN}/sendVideo"
            
            with open(VIDEO_PATH, "rb") as video:
                files = {"video": video}
                data = {"chat_id": chat_id, "caption": caption}
                resp = requests.post(url, data=data, files=files, timeout=30)
            
            if resp.status_code == 200:
                exitosos += 1
                log(f"   ✅ Éxito con {chat_id}")
            else:
                log(f"   ❌ Error {resp.status_code}: {resp.text}")
            
            # Delay para no ser baneado por spam
            time.sleep(random.uniform(1.5, 3.0))
        except Exception as e:
            log(f"   ❌ Error crítico con {chat_id}: {e}")

    log(f"\n🎉 ¡Calentamiento completado! {exitosos} videos enviados con éxito.")

if __name__ == "__main__":
    import random
    enviar_teaser()
