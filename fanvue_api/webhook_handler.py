"""
Handler de webhooks de Fanvue con integración de IA
Responde automáticamente a mensajes, nuevos suscriptores, compras, etc.
"""
import os
import sys
import logging
from flask import Flask, request, jsonify
from typing import Dict, Any

# Agregar el directorio raíz del proyecto al path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from dotenv import load_dotenv
from fanvue_api.fanvue_client import FanvueAPI
from fanvue_api.meta_pixel_tracking import MetaPixelTracker
from ai_models.ai_handler import AIHandler

load_dotenv()

logger = logging.getLogger(__name__)

app = Flask(__name__)
fanvue_api = FanvueAPI()
ai_handler = AIHandler()
pixel_tracker = MetaPixelTracker()

@app.route("/api/webhook/fanvue", methods=["POST"])
def handle_fanvue_webhook():
    """Maneja todos los webhooks de Fanvue"""
    try:
        # Verificar firma del webhook
        signature = request.headers.get("X-Fanvue-Signature", "")
        payload = request.get_data(as_text=True)
        
        if not fanvue_api.verify_webhook_signature(payload, signature):
            logger.warning("Webhook con firma inválida")
            return jsonify({"error": "Invalid signature"}), 401
        
        data = request.get_json()
        event_type = data.get("type")
        event_data = data.get("data", {})
        
        logger.info(f"Webhook recibido de Fanvue: {event_type}")
        
        # Procesar según el tipo de evento
        if event_type == "message.created":
            handle_new_message(event_data)
        elif event_type == "follower.created":
            handle_new_follower(event_data)
        elif event_type == "subscriber.created":
            handle_new_subscriber(event_data)
        elif event_type == "purchase.created":
            handle_new_purchase(event_data)
        elif event_type == "tip.created":
            handle_new_tip(event_data)
        else:
            logger.info(f"Evento no manejado: {event_type}")
        
        return jsonify({"status": "ok"}), 200
        
    except Exception as e:
        logger.error(f"Error procesando webhook de Fanvue: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500

def handle_new_message(event_data: Dict[str, Any]):
    """Responde automáticamente a nuevos mensajes en Fanvue con IA"""
    import asyncio
    try:
        # Según documentación, el evento puede tener diferentes estructuras
        chat_id = event_data.get("chatId") or event_data.get("chatUuid")
        message_text = event_data.get("text", "") or event_data.get("message", {}).get("text", "")
        sender_id = event_data.get("senderId") or event_data.get("senderUuid")
        sender_name = event_data.get("senderName") or event_data.get("user", {}).get("displayName", "Usuario")
        
        if not message_text or not chat_id:
            return
        
        logger.info(f"Nuevo mensaje en Fanvue de {sender_name}: {message_text[:50]}...")
        
        # Obtener respuesta de IA (síncrono)
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            ai_response = loop.run_until_complete(
                ai_handler.get_response(message_text, user_id=str(sender_id))
            )
            loop.close()
        except Exception as e:
            logger.error(f"Error obteniendo respuesta de IA: {e}")
            ai_response = f"Hola {sender_name}! 😊 Me encanta que me escribas... 💕"
        
        if not ai_response or "¡Ay! 😅 Algo salió mal" in ai_response:
            ai_response = f"Hola {sender_name}! 😊 Me encanta que me escribas... 💕"
        
        # Enviar respuesta automática en Fanvue
        success = fanvue_api.send_message(chat_id, ai_response)
        
        if success:
            logger.info(f"✅ Respuesta IA enviada a {sender_name} en Fanvue")
        else:
            logger.error(f"❌ Error enviando respuesta a {sender_name}")
            
    except Exception as e:
        logger.error(f"Error manejando nuevo mensaje: {e}", exc_info=True)

def handle_new_follower(event_data: Dict[str, Any]):
    """Envía mensaje de bienvenida a nuevos seguidores y rastrea lead"""
    try:
        fan_id = event_data.get("fanId")
        fan_name = event_data.get("fanName", "cariño")
        fan_email = event_data.get("fanEmail", "")
        
        logger.info(f"Nuevo seguidor en Fanvue: {fan_name}")
        
        # Rastrear lead en Meta Pixel
        if fan_email:
            pixel_tracker.track_lead(fan_email, "fanvue")
            logger.info(f"📊 Lead rastreado en Meta Pixel para {fan_name}")
        
        # Obtener o crear chat del seguidor
        chats_result = fanvue_api.get_chats()
        chats = chats_result.get("data", [])
        chat_id = None
        for chat in chats:
            user = chat.get("user", {})
            if user.get("uuid") == fan_id:
                # El chat_id puede estar en el objeto chat o necesitar construirse
                chat_id = chat.get("uuid") or chat.get("id")
                break
        
        # Si no existe chat, crear uno nuevo
        if not chat_id:
            logger.info(f"Creando nuevo chat con seguidor {fan_id}")
            if fanvue_api.create_chat(fan_id):
                # Obtener el chat recién creado
                chats_result = fanvue_api.get_chats()
                chats = chats_result.get("data", [])
                for chat in chats:
                    user = chat.get("user", {})
                    if user.get("uuid") == fan_id:
                        chat_id = chat.get("uuid") or chat.get("id")
                        break
        
        if chat_id:
            welcome_message = (
                f"¡Hola {fan_name}! 😊💕\n\n"
                f"Me encanta que me sigas... Gracias por estar aquí ✨\n\n"
                f"Tengo contenido especial que quiero compartir contigo... 😘"
            )
            fanvue_api.send_message(chat_id, welcome_message)
            logger.info(f"✅ Mensaje de bienvenida enviado a {fan_name}")
        
    except Exception as e:
        logger.error(f"Error manejando nuevo seguidor: {e}", exc_info=True)

def handle_new_subscriber(event_data: Dict[str, Any]):
    """Envía mensaje especial a nuevos suscriptores y rastrea conversión"""
    try:
        fan_id = event_data.get("fanId")
        fan_name = event_data.get("fanName", "cariño")
        plan_name = event_data.get("planName", "")
        fan_email = event_data.get("fanEmail", "")
        plan_price = event_data.get("planPrice", 0)
        
        logger.info(f"Nuevo suscriptor en Fanvue: {fan_name} - Plan: {plan_name} - ${plan_price}")
        
        # Rastrear conversión en Meta Pixel
        if fan_email:
            pixel_tracker.track_subscription(fan_email, plan_price)
            logger.info(f"📊 Suscripción rastreada en Meta Pixel para {fan_name}")
        
        # Obtener o crear chat del suscriptor
        chats_result = fanvue_api.get_chats()
        chats = chats_result.get("data", [])
        chat_id = None
        for chat in chats:
            user = chat.get("user", {})
            if user.get("uuid") == fan_id:
                chat_id = chat.get("uuid") or chat.get("id")
                break
        
        # Si no existe chat, crear uno nuevo
        if not chat_id:
            logger.info(f"Creando nuevo chat con suscriptor {fan_id}")
            if fanvue_api.create_chat(fan_id):
                # Obtener el chat recién creado
                chats_result = fanvue_api.get_chats()
                chats = chats_result.get("data", [])
                for chat in chats:
                    user = chat.get("user", {})
                    if user.get("uuid") == fan_id:
                        chat_id = chat.get("uuid") or chat.get("id")
                        break
        
        if chat_id:
            welcome_message = (
                f"¡Bienvenido, {fan_name}! 🎉💕\n\n"
                f"Me hace MUY feliz que te hayas suscrito... 😊✨\n\n"
                f"Ahora tienes acceso a TODO mi contenido exclusivo... 🔥\n\n"
                f"¿Hay algo especial que te gustaría ver? 😘"
            )
            fanvue_api.send_message(chat_id, welcome_message)
            logger.info(f"✅ Mensaje de bienvenida enviado a suscriptor {fan_name}")
        
    except Exception as e:
        logger.error(f"Error manejando nuevo suscriptor: {e}", exc_info=True)

def handle_new_purchase(event_data: Dict[str, Any]):
    """Procesa compras y envía contenido automáticamente"""
    try:
        fan_id = event_data.get("fanId")
        fan_name = event_data.get("fanName", "Usuario")
        fan_email = event_data.get("fanEmail", "")
        content_id = event_data.get("contentId")
        amount = event_data.get("amount", 0)
        content_type = event_data.get("contentType", "")
        
        logger.info(f"Nueva compra en Fanvue: {fan_name} compró {content_id} por ${amount}")
        
        # Rastrear compra en Meta Pixel
        if fan_email:
            pixel_tracker.track_purchase(fan_email, amount, "USD", content_type)
            logger.info(f"📊 Compra rastreada en Meta Pixel para {fan_name}")
        
        # Aquí puedes mapear content_id a archivos/URLs reales
        # Por ahora, enviar mensaje de confirmación
        
        chats_result = fanvue_api.get_chats()
        chats = chats_result.get("data", [])
        chat_id = None
        for chat in chats:
            user = chat.get("user", {})
            if user.get("uuid") == fan_id:
                chat_id = chat.get("uuid") or chat.get("id")
                break
        
        if chat_id:
            thank_you_message = (
                f"¡Gracias por tu compra, {fan_name}! 💕\n\n"
                f"Tu contenido está disponible en tu perfil... 😘\n\n"
                f"¿Te gustó? Me encantaría saber qué piensas... ✨"
            )
            fanvue_api.send_message(chat_id, thank_you_message)
            logger.info(f"✅ Confirmación de compra enviada a {fan_name}")
        
    except Exception as e:
        logger.error(f"Error manejando compra: {e}", exc_info=True)

def handle_new_tip(event_data: Dict[str, Any]):
    """Agradece propinas recibidas"""
    try:
        fan_id = event_data.get("fanId")
        fan_name = event_data.get("fanName", "cariño")
        amount = event_data.get("amount", 0)
        
        logger.info(f"Nueva propina en Fanvue: ${amount} de {fan_name}")
        
        chats_result = fanvue_api.get_chats()
        chats = chats_result.get("data", [])
        chat_id = None
        for chat in chats:
            user = chat.get("user", {})
            if user.get("uuid") == fan_id:
                chat_id = chat.get("uuid") or chat.get("id")
                break
        
        if chat_id:
            thank_you_message = (
                f"¡Muchas gracias por la propina, {fan_name}! 😊💕\n\n"
                f"Eres increíble... Me ayudas mucho con esto ✨\n\n"
                f"¿Hay algo especial que quieras ver? 😘"
            )
            fanvue_api.send_message(chat_id, thank_you_message)
            logger.info(f"✅ Agradecimiento enviado a {fan_name}")
        
    except Exception as e:
        logger.error(f"Error manejando propina: {e}", exc_info=True)

if __name__ == "__main__":
    # Configurar logging
    logging.basicConfig(
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        level=logging.INFO
    )
    
    port = int(os.getenv("FANVUE_WEBHOOK_PORT", 5003))
    
    print("\n" + "=" * 60)
    print("🤖 BOT DE IA AUTOMÁTICO PARA FANVUE")
    print("=" * 60)
    print(f"\n✅ Iniciando webhook server en puerto {port}")
    print(f"📡 Endpoint: http://localhost:{port}/api/webhook/fanvue")
    print("\n⚠️  IMPORTANTE:")
    print("   1. Expone este servidor con ngrok: ngrok http 5003")
    print("   2. Actualiza la URL del webhook en Fanvue")
    print("   3. El bot responderá automáticamente a todos los mensajes")
    print("\n" + "=" * 60 + "\n")
    
    # Verificar que el access token esté configurado
    access_token = os.getenv("FANVUE_ACCESS_TOKEN")
    if not access_token:
        print("⚠️  ADVERTENCIA: FANVUE_ACCESS_TOKEN no configurado")
        print("   El bot no podrá enviar mensajes hasta que configures el token")
        print("   Ejecuta: py fanvue_api\\oauth_helper.py\n")
    
    app.run(host="0.0.0.0", port=port, debug=False)
