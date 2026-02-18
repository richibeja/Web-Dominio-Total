"""
Sistema para leer comentarios de Instagram y responder automáticamente en Fanvue
Usa Antigravity para controlar el ordenador y leer comentarios
"""
import os
import sys
import logging
import requests
import asyncio
from datetime import datetime
from pathlib import Path

# Agregar el directorio raíz del proyecto al path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from dotenv import load_dotenv
from config.utopia_finca_links import LINKS as UTOPIA_FINCA_LINKS
from ai_models.ai_handler import AIHandler

load_dotenv()

logger = logging.getLogger(__name__)

# Archivo para guardar comentarios procesados
COMMENTS_FILE = Path("data/instagram_comments_processed.json")

# Inicializar manejador de IA
ai_handler = AIHandler()

def send_to_fanvue_via_api(user_id: str, message: str):
    """
    Envía mensaje a Fanvue usando su API (si está disponible)
    O prepara el mensaje para que Antigravity lo envíe
    """
    # Si tienes API de Fanvue, úsala aquí
    # Por ahora, esta función prepara el mensaje para Antigravity
    logger.info(f"Preparando mensaje para Fanvue: {message[:50]}...")
    return {
        "user_id": user_id,
        "message": message,
        "timestamp": datetime.now().isoformat()
    }

async def generate_response_for_comment(comment_text: str, username: str, platform: str = "instagram") -> str:
    """
    Genera respuesta automática para un comentario de Instagram
    platform: "instagram" (respuesta sutil) o "fanvue" (respuesta más directa)
    """
    fanvue_link = UTOPIA_FINCA_LINKS.get('fanvue', 'https://www.fanvue.com/luzdeaurorafeyamor')
    
    if platform == "instagram":
        # Respuesta SUTIL para Instagram (evitar bloqueos)
        context = (
            f"Eres una modelo de contenido. Alguien comentó en tu Instagram: '{comment_text}' (usuario: @{username}). "
            f"Genera una respuesta NATURAL, SUTIL y MUY HUMANA que: "
            f"1. Agradezca el comentario con picardía y estilo paisa ('mor', 'tan lindo', 'que chimba'). "
            f"2. Sea 100% conversacional, como si hablaras con un pretendiente. "
            f"3. NO parezcas un bot vendiendo. Evita frases como 'mira mi link', 'en mi perfil está'. "
            f"4. PUEDES sugerir que te encanta hablar en privado pero de forma natural: 'ay mor, ¿me vas a dejar con las ganas de decirte algo más por el privado? 🙈'. "
            f"5. SIEMPRE termina con una pregunta coqueta. "
            f"6. Máximo 1-2 líneas, estilo chat relajado."
        )
    else:
        # Respuesta DIRECTA para Fanvue (estrategia novia virtual)
        context = (
            f"Eres una novia virtual en Fanvue. Alguien comentó en tu Instagram: '{comment_text}' (usuario: @{username}). "
            f"Genera una respuesta SEDUCTORA y PERSONALIZADA que: "
            f"1. Agradezca el comentario como si fueras su novia virtual "
            f"2. Mencione que tienes contenido exclusivo y personalizado para él "
            f"3. Invite a suscribirse GRATIS (menciona que es gratis varias veces) "
            f"4. Sea íntima, coqueta y persuasiva (estrategia de novia virtual) "
            f"5. Mencione que puedes hacer contenido personalizado "
            f"6. INCLUYE SIEMPRE el link de Fanvue: {fanvue_link} "
            f"7. MENCIONA QUE ES GRATIS: 'Es gratis suscribirte', 'No cuesta nada', 'Suscripción gratuita', 'Entra gratis' "
            f"8. USA FRASES COMO: 'Entra gratis y hablamos', 'Es gratis, no cuesta nada', 'Suscripción gratuita para ti' "
        )
    
    try:
        response = await ai_handler.get_response(comment_text, user_id=username, context=context)
        return response
    except Exception as e:
        logger.error(f"Error generando respuesta: {e}")
        # Fallback diversificado según plataforma
        import random
        if platform == "instagram":
            fallbacks = [
                f"Ay @{username} tan lindo que me escribís... ¿me vas a dejar con las ganas de hablar más por el privado? 🙈",
                f"Pues @{username} qué chimba ese mensaje... ¿qué más me contás pues? 😘",
                f"Me dejaste pensando @{username}... ¿será que hablamos más tranqui por el privado? 😈",
                f"Tan especial @{username}! ¿Y qué hacés pues por acá tan solo? Jeje",
                f"Ay mor @{username} me encantó... ¿qué te parece si seguimos la charla donde no nos vean? ✨",
            ]
            return random.choice(fallbacks)
        else:
            fallbacks = [
                f"Ay mor @{username}! 🥰 Me encantó tu mensaje... te tengo una sorpresita esperándote aquí gratis: {fanvue_link} 😘 ¿Vienes?",
                f"Bebé @{username}! 🔥 Me dejaste con ganas de más... vení a mi chat privado que es GRATIS entrar: {fanvue_link} 💋 ¿Qué te parece?",
                f"Hola hermoso @{username} 😘 Te espero en mi lugar favorito, es gratis suscribirte y charlamos rico: {fanvue_link} 🔥 No te lo pierdas!",
            ]
            return random.choice(fallbacks)

async def process_instagram_comment(comment_text: str, username: str, post_url: str = "", comment_id: str = ""):
    """
    Procesa un comentario de Instagram:
    1. Genera respuesta con IA
    2. Envía a Fanvue
    3. Responde automáticamente
    
    Retorna la respuesta generada para que se use en Instagram
    """
    try:
        # Verificar si ya fue procesado
        if is_comment_processed(comment_id):
            logger.info(f"Comentario {comment_id} ya procesado, saltando...")
            return None
        
        logger.info(f"Procesando comentario de @{username}: {comment_text[:50]}...")
        
        # Generar respuesta con IA para Instagram (sutil)
        instagram_response = await generate_response_for_comment(comment_text, username, platform="instagram")
        
        # Generar respuesta para Fanvue (directa, estrategia novia virtual)
        fanvue_response = await generate_response_for_comment(comment_text, username, platform="fanvue")
        
        # Asegurar que fanvue_response tenga el link SIEMPRE
        fanvue_link = UTOPIA_FINCA_LINKS.get('fanvue', 'https://www.fanvue.com/luzdeaurorafeyamor')
        SUBSCRIPTION_FREE_MSG = "es GRATIS suscribirte, no cuesta nada"
        
        if fanvue_link not in fanvue_response:
            # Agregar link con mensaje de suscripción gratis
            fanvue_response += f"\n\n🔥 {SUBSCRIPTION_FREE_MSG}: {fanvue_link}\n💕 Entra gratis y hablamos 😘"
        
        # Estandarizar menciones de precio (asegurar que dice gratis)
        if "$3.99" in fanvue_response or "VIP" in fanvue_response:
             import re
             fanvue_response = re.sub(r'\$3\.99|VIP \$3\.99', 'GRATIS', fanvue_response)
        
        # Usar respuesta de Instagram para responder en Instagram
        response = instagram_response
        # SIEMPRE incluir número de WhatsApp en la respuesta al comentario (para que lleguen a la socia)
        whatsapp_num = os.getenv("WHATSAPP_NUMBER", "+57 322 719 8007").strip()
        # Formatear link de WhatsApp limpio
        whatsapp_link = f"https://wa.me/{whatsapp_num.replace('+', '').replace(' ', '')}"
        
        if whatsapp_num not in response and "wa.me" not in response:
            response = response.rstrip() + f"\n\nMe escribes al WhatsApp {whatsapp_link} y ahí te contesto mejor 😘"
        
        # Guardar para que el sistema lo envíe a Fanvue (usar respuesta de Fanvue mejorada)
        save_comment_for_fanvue(username, comment_text, fanvue_response, post_url, comment_id)
        
        # Guardar como procesado
        save_processed_comment(comment_id, username, comment_text, response)
        
        logger.info(f"✅ Comentario procesado y respuesta generada")
        
        # Retornar la respuesta para usarla en Instagram
        return response
        
    except Exception as e:
        logger.error(f"Error procesando comentario: {e}", exc_info=True)
        return None

def save_comment_for_fanvue(username: str, comment_text: str, response: str, post_url: str, comment_id: str):
    """
    Guarda comentario para que el sistema lo envíe a Fanvue automáticamente
    """
    import json
    
    fanvue_file = Path("data/comentarios_para_fanvue.json")
    fanvue_file.parent.mkdir(parents=True, exist_ok=True)
    
    # Cargar comentarios pendientes
    pending = []
    if fanvue_file.exists():
        try:
            with open(fanvue_file, 'r', encoding='utf-8') as f:
                pending = json.load(f)
        except:
            pending = []
    
    # Agregar nuevo comentario
    pending.append({
        "comment_id": comment_id,
        "username": username,
        "comment": comment_text,
        "response": response,
        "post_url": post_url,
        "created_at": datetime.now().isoformat(),
        "status": "pending"  # pending, sent, responded
    })
    
    # Guardar
    try:
        with open(fanvue_file, 'w', encoding='utf-8') as f:
            json.dump(pending, f, indent=2, ensure_ascii=False)
        logger.info(f"✅ Comentario guardado para enviar a Fanvue")
    except Exception as e:
        logger.error(f"Error guardando comentario para Fanvue: {e}")

def save_processed_comment(comment_id: str, username: str, comment_text: str, response: str = ""):
    """
    Guarda comentario procesado
    """
    import json
    
    COMMENTS_FILE.parent.mkdir(parents=True, exist_ok=True)
    
    processed = {}
    if COMMENTS_FILE.exists():
        try:
            with open(COMMENTS_FILE, 'r', encoding='utf-8') as f:
                processed = json.load(f)
        except:
            processed = {}
    
    processed[comment_id] = {
        "username": username,
        "comment": comment_text,
        "response": response,
        "processed_at": datetime.now().isoformat(),
        "platform": "fanvue"
    }
    
    try:
        with open(COMMENTS_FILE, 'w', encoding='utf-8') as f:
            json.dump(processed, f, indent=2, ensure_ascii=False)
    except Exception as e:
        logger.error(f"Error guardando comentario: {e}")

def is_comment_processed(comment_id: str) -> bool:
    """
    Verifica si un comentario ya fue procesado
    """
    if not COMMENTS_FILE.exists():
        return False
    
    try:
        import json
        with open(COMMENTS_FILE, 'r', encoding='utf-8') as f:
            processed = json.load(f)
            return comment_id in processed
    except:
        return False

# Ejemplo de uso
if __name__ == "__main__":
    """
    Ejemplo de cómo usar esta función
    """
    # Cuando Antigravity detecte un comentario nuevo:
    process_instagram_comment(
        comment_text="Hola, me encanta tu contenido",
        username="usuario123",
        post_url="https://instagram.com/p/ABC123",
        comment_id="comment_123"
    )
