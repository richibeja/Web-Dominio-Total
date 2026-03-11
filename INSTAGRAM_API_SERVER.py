import os
import json
import logging
import requests
from flask import Flask, request, jsonify
from pathlib import Path
from dotenv import load_dotenv

# Cargar variables de entorno
PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")

# Configuración de logs
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("InstagramAPI")

app = Flask(__name__)

# Configuración desde .env
ACCESS_TOKEN = os.getenv("INSTAGRAM_ACCESS_TOKEN")
APP_SECRET = os.getenv("INSTAGRAM_APP_SECRET")
VERIFY_TOKEN = os.getenv("INSTAGRAM_VERIFY_TOKEN", "aurora_secreto_2026")
PAGE_ID = os.getenv("INSTAGRAM_ACCOUNT_ID") # IGSID o Page ID vinculado

# Directorio de datos
DATA_DIR = PROJECT_ROOT / "data" / "instagram"
DATA_DIR.mkdir(parents=True, exist_ok=True)
HISTORY_FILE = DATA_DIR / "chat_history.json"

def load_history():
    if not HISTORY_FILE.exists(): return {}
    try:
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except: return {}

def save_history(history):
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False, indent=2)

def get_ai_response(user_text, username):
    try:
        from ai_models.ai_handler import AIHandler
        handler = AIHandler()
        # Nota: AIHandler es asíncrono, pero tiene get_response_sync
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        # Determinar si es comentario o DM basado en una flag o el nombre del usuario
        platform = "instagram_comment" if username.startswith("comment_") else "instagram"
        response = loop.run_until_complete(handler.get_response(user_text, user_id=username, platform=platform))
        loop.close()
        return response
    except Exception as e:
        logger.error(f"Error AI: {e}")
        return "Ay mor, me distraje... ¿qué me decías? 🙈"

def send_message(recipient_id, text):
    url = f"https://graph.facebook.com/v19.0/me/messages?access_token={ACCESS_TOKEN}"
    payload = {
        "recipient": {"id": recipient_id},
        "message": {"text": text}
    }
    try:
        r = requests.post(url, json=payload, timeout=10)
        logger.info(f"Respuesta envío: {r.status_code} - {r.text}")
        return r.status_code == 200
    except Exception as e:
        logger.error(f"Error enviando DM: {e}")
        return False

def reply_comment(comment_id, text):
    """Responde a un comentario público en un post."""
    url = f"https://graph.facebook.com/v19.0/{comment_id}/replies?access_token={ACCESS_TOKEN}"
    payload = {"message": text}
    try:
        r = requests.post(url, json=payload, timeout=10)
        logger.info(f"Respuesta comentario: {r.status_code} - {r.text}")
        return r.status_code == 200
    except Exception as e:
        logger.error(f"Error respondiendo comentario {comment_id}: {e}")
        return False

@app.route("/webhook/instagram", methods=["GET"])
def verify():
    mode = request.args.get("hub.mode")
    token = request.args.get("hub.verify_token")
    challenge = request.args.get("hub.challenge")
    if mode == "subscribe" and token == VERIFY_TOKEN:
        logger.info("✅ Webhook verificado con éxito")
        return challenge, 200
    return "Error de verificación", 403

@app.route("/webhook/instagram", methods=["POST"])
def webhook():
    data = request.json
    if not data or "entry" not in data:
        return "OK", 200

    for entry in data["entry"]:
        # 1. Manejar DMs (messaging)
        for messaging_event in entry.get("messaging", []):
            if "message" in messaging_event:
                sender_id = messaging_event["sender"]["id"]
                message_text = messaging_event["message"].get("text")
                if not message_text: continue
                logger.info(f"📩 Nuevo DM de {sender_id}: {message_text}")
                
                try:
                    from shared.telegram_operaciones import send_instagram_dm_to_telegram
                    send_instagram_dm_to_telegram(f"ID_{sender_id}", message_text)
                except: pass

                ai_reply = get_ai_response(message_text, sender_id)
                if ai_reply:
                    send_message(sender_id, ai_reply)

        # 2. Manejar Comentarios (changes)
        for change in entry.get("changes", []):
            if change.get("field") == "comments":
                comment_value = change.get("value", {})
                comment_id = comment_value.get("id")
                comment_text = comment_value.get("text")
                from_user = comment_value.get("from", {})
                username = from_user.get("username", "user")

                if not comment_id or not comment_text: continue
                # Evitar responder a Aurora misma (si el webhook lo envía)
                my_id = os.getenv("INSTAGRAM_BUSINESS_USER_ID")
                sender_id_comment = from_user.get("id")
                
                if sender_id_comment == my_id:
                    continue # Es mi propio comentario, no respondo

                logger.info(f"💬 Nuevo comentario de @{username} (ID: {sender_id_comment}): {comment_text}")

                ai_reply = get_ai_response(comment_text, f"comment_{username}")
                if ai_reply:
                    logger.info(f"✍️ Respondiendo a comentario: {ai_reply}")
                    reply_comment(comment_id, ai_reply)

    return "OK", 200

if __name__ == "__main__":
    port = int(os.getenv("INSTAGRAM_BOT_PORT", 5002))
    logger.info(f"🚀 Servidor de Instagram API arrancando en puerto {port}...")
    app.run(host="0.0.0.0", port=port, debug=False)
