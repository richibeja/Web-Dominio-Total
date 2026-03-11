import os
from flask import Flask, request, abort
from dotenv import load_dotenv

# Cargar variables de entorno desde .env
load_dotenv()

app = Flask(__name__)

VERIFY_TOKEN = os.getenv("INSTAGRAM_WEBHOOK_VERIFY_TOKEN")
LOG_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "logs", "instagram_activity.log")

def log_activity(msg):
    from datetime import datetime
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}\n"
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(line)
    print(msg, flush=True)

@app.route("/webhook/instagram", methods=["GET", "POST"])
def instagram_webhook():
    if request.method == "GET":
        mode = request.args.get("hub.mode")
        token = request.args.get("hub.verify_token")
        challenge = request.args.get("hub.challenge")
        
        log_activity(f"🔍 Intento de verificación Meta: mode={mode}, token_recibido={token}, esperado={VERIFY_TOKEN}")
        
        if mode == "subscribe" and token == VERIFY_TOKEN:
            log_activity("✅ Meta verificó el webhook con éxito!")
            return challenge, 200
        else:
            log_activity("❌ Verificación fallida: Token incorrecto.")
            abort(403)
    # POST – evento recibido
    data = request.get_json()
    try:
        if data.get("object") == "instagram":
            for entry in data.get("entry", []):
                # Solo procesamos Mensajes Directos (DMs)
                if "messaging" in entry:
                    for messaging_event in entry["messaging"]:
                        sender_id = messaging_event.get("sender", {}).get("id")
                        message = messaging_event.get("message", {})
                        
                        # Solo procesamos si el mensaje tiene texto real (ignora reacciones/eventos técnicos)
                        if "text" in message:
                            text = message["text"]
                            # Por ahora usamos el ID como username si no tenemos mapeo directo
                            username = f"ID_{sender_id}"
                            
                            # Enviar a Telegram
                            from shared.telegram_operaciones import send_instagram_dm_to_telegram
                            send_instagram_dm_to_telegram(username, text)
                            log_activity(f"📩 DM recibido de {username}: {text[:80]}")

                # --- NUEVO: Procesar COMENTARIOS y responder con IA ---
                if "changes" in entry:
                    for change in entry["changes"]:
                        value = change.get("value", {})
                        if "text" in value:
                            comment_id = value.get("id")
                            comment_text = value.get("text")
                            from_user = value.get("from", {}).get("username", "usuario")
                            
                            log_activity(f"💬 Comentario de {from_user}: {comment_text}")
                            
                            # 1. Avisar a Telegram
                            from shared.telegram_operaciones import send_instagram_dm_to_telegram
                            send_instagram_dm_to_telegram(f"INSTAGRAM_COMMENT: [{from_user}]", comment_text)

                            # 2. Responder automáticamente con IA
                            try:
                                from ai_models.ai_handler import AIHandler
                                ai = AIHandler()
                                # Obtenemos respuesta humanizada (paisa)
                                reply_text = ai.get_response_sync(comment_text, user_id=from_user, platform="instagram_comment", dialect="paisa_comment")
                                
                                # Enviar respuesta a Instagram via Graph API
                                access_token = os.getenv("INSTAGRAM_ACCESS_TOKEN")
                                if access_token and comment_id:
                                    import requests
                                    # Endpoint para responder a un comentario específico
                                    url = f"https://graph.facebook.com/v19.0/{comment_id}/replies"
                                    params = {"message": reply_text, "access_token": access_token}
                                    r = requests.post(url, params=params)
                                    if r.status_code == 200:
                                        log_activity(f"✅ IA respondió al comentario de {from_user}: {reply_text}")
                                    else:
                                        log_activity(f"❌ Error respondiendo comentario: {r.text}")
                            except Exception as e:
                                print(f"⚠️ Error en respuesta automática de comentarios: {e}")

    except Exception as e:
        print(f"⚠️ Error procesando webhook: {e}")
    return "OK", 200

if __name__ == "__main__":
    # Ejecutar directamente para pruebas rápidas
    app.run(host="0.0.0.0", port=5000)
