import os
import sys
import time
import json
import logging
from pathlib import Path
from datetime import datetime

# Añadir el raíz del proyecto al path
project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from ai_models.ai_handler import AIHandler
from ai_models.voice_handler import VoiceHandler
from fanvue_utils import FanvueUtils
try:
    from shared.telegram_operaciones import send_instagram_dm_to_telegram 
except ImportError:
    logger.warning("No se pudo importar shared.telegram_operaciones")

# Configurar logging
log_dir = project_root / "logs"
log_dir.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_dir / "fanvue_automation.log", encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("FanvueAutomation")

class FanvueAutomation:
    def __init__(self):
        self.utils = FanvueUtils()
        self.ai = AIHandler()
        self.processed_messages_file = project_root / "data" / "fanvue_processed_messages.json"
        self.processed_messages = self._load_processed_messages()
        self.processed_notifications_file = project_root / "data" / "fanvue_processed_notifications.json"
        self.processed_notifications = self._load_processed_notifications()
        self.my_user_id = None
        self.vh = VoiceHandler()

    def _load_processed_messages(self):
        if self.processed_messages_file.exists():
            try:
                with open(self.processed_messages_file, "r") as f:
                    return json.load(f)
            except:
                return {}
        return {}

    def _save_processed_messages(self):
        self.processed_messages_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.processed_messages_file, "w") as f:
            json.dump(self.processed_messages, f, indent=2)

    def _load_processed_notifications(self):
        if self.processed_notifications_file.exists():
            try:
                with open(self.processed_notifications_file, "r") as f:
                    return json.load(f)
            except:
                return []
        return []

    def _save_processed_notifications(self):
        self.processed_notifications_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.processed_notifications_file, "w") as f:
            json.dump(self.processed_notifications, f, indent=2)

    def get_my_info(self):
        response = self.utils.api_request("GET", "/users/me")
        if response and response.status_code == 200:
            data = response.json()
            self.my_user_id = data.get("id")
            logger.info(f"✅ Automatización iniciada para: {data.get('handle')}")
            return data
        return None

    async def run(self):
        if not self.get_my_info():
            logger.error("No se pudo obtener información del usuario. ¿Tokens válidos?")
            return

        print("\n🚀 FANVUE AUTOMATION ACTIVA - Aurora está vigilando...")
        
        while True:
            try:
                response = self.utils.api_request("GET", "/chats")
                if response and response.status_code == 200:
                    chats = response.json()
                    chat_list = chats.get('data', []) if isinstance(chats, dict) else (chats if isinstance(chats, list) else [])
                    
                    for chat in chat_list:
                        if not chat or not isinstance(chat, dict): continue
                        
                        chat_id = chat.get('user', {}).get('uuid') or chat.get('id')
                        if not chat_id: continue
                        
                        last_message = chat.get('lastMessage')
                        if not last_message or not isinstance(last_message, dict): continue
                        
                        msg_id = last_message.get('uuid') or last_message.get('id')
                        sender_id = last_message.get('senderUuid') or last_message.get('sentByUserId')
                        
                        # Si el mensaje es nuevo y no es mío
                        if sender_id and sender_id != self.my_user_id:
                            if chat_id not in self.processed_messages or self.processed_messages[chat_id] != msg_id:
                                 await self.process_new_message(chat, last_message, chat_id, msg_id, sender_id)
                                 await asyncio.sleep(3) # Pausa para no quemar la IA y parecer real
                
                # Revisar Notificaciones (Tips/Suscripciones)
                await self.check_notifications()

                time.sleep(30) # Poll cada 30 segundos
            except Exception as e:
                logger.error(f"Error en el loop principal: {e}")
                time.sleep(10)

    async def process_new_message(self, chat, message, chat_id, msg_id, sender_id):
        text = message.get('text', '')
        
        # Obtener info del fan
        other_user = chat.get('user', {})
        fan_username = other_user.get('handle') or other_user.get('displayName') or 'Fan'
        fan_uuid = other_user.get('uuid')
        
        logger.info(f"📩 Nuevo mensaje de @{fan_username}: {text}")

        # Notificar a Telegram
        try:
            # Reutilizamos send_instagram_dm_to_telegram adaptando el prefijo
            telegram_text = f"🫦 FANVUE: [{fan_username}] dice: {text}"
            # Nota: la función original de shared espera un formato específico para parsear
            # pero aquí solo queremos notificar.
            from shared.telegram_operaciones import send_instagram_dm_to_telegram
            # Creamos una versión adaptada o usamos requests directo
            requests.post(f"https://api.telegram.org/bot{os.getenv('TELEGRAM_BOT_TOKEN')}/sendMessage", 
                         json={"chat_id": os.getenv("TELEGRAM_OPERACIONES_ID"), "text": telegram_text})
        except:
            pass

        # Generar respuesta con Aurora
        ai_response = await self.ai.get_response(text, user_id=fan_username, platform="fanvue")
        
        logger.info(f"🤖 Aurora responde: {ai_response}")

        # Enviar respuesta a Fanvue
        send_url = f"/chats/{fan_uuid}/messages"
        payload = {"text": ai_response}
        logger.info(f"📤 Enviando a Fanvue: {send_url} | Payload: {payload}")
        
        send_res = self.utils.api_request("POST", send_url, json=payload)
        
        if send_res and send_res.status_code in [200, 201]:
            logger.info(f"✅ Respuesta enviada a @{fan_username}")
            # Marcar como procesado
            self.processed_messages[chat_id] = msg_id
            self._save_processed_messages()
            
            # Notificar respuesta a Telegram
            try:
                requests.post(f"https://api.telegram.org/bot{os.getenv('TELEGRAM_BOT_TOKEN')}/sendMessage", 
                             json={"chat_id": os.getenv("TELEGRAM_OPERACIONES_ID"), "text": f"✅ Aurora respondió a @{fan_username}: {ai_response}"})
            except:
                pass
        else:
            logger.error(f"❌ Falló el envío de respuesta: {send_res.status_code if send_res else 'No res'}")
            if send_res: logger.error(send_res.text)

    async def check_notifications(self):
        """Revisa notificaciones de Fanvue para detectar Tips y Suscripciones."""
        response = self.utils.api_request("GET", "/notifications")
        if not response or response.status_code != 200:
            return

        notifications = response.json().get('data', [])
        new_found = False

        for nt in notifications:
            nt_id = nt.get('id') or nt.get('uuid')
            if nt_id in self.processed_notifications:
                continue

            nt_type = nt.get('type')
            actor = nt.get('actor', {})
            username = actor.get('handle') or actor.get('displayName') or "Fan"
            
            # Tip detectado
            if nt_type == "tip_received":
                amount = nt.get('amount', 0) / 100 # Centavos a Dólares
                logger.info(f"💰 ¡TIP RECIBIDO! @{username} envió ${amount}")
                await self.notify_telegram(f"💰 ¡TIP DE ${amount}! De @{username} en Fanvue. ¡Aurora, dale las gracias!")
                await self.send_auto_voice_thanks(username, f"¡Ay gracias amor por esos {amount} dolaritos! Me encantaron... ¿qué quieres que haga por ti ahora?")
            
            # Nueva Suscripción
            elif nt_type == "new_subscription":
                logger.info(f"💎 NUEVA SUSCRIPCIÓN: @{username}")
                await self.notify_telegram(f"💎 NUEVA SUSCRIPCIÓN: @{username} se unió al VIP. ¡Bienvenido!")
                await self.send_auto_voice_thanks(username, f"¡Hola mi amor! Ya vi que te suscribiste a mi canal privado... qué rico tenerte aquí. Prepárate para lo que viene 😈")

            # Desbloqueo de Post / Compra de Media
            elif nt_type in ["post_unlocked", "unlock_received", "media_purchase_received"]:
                subject_uuid = nt.get('subjectUuid')
                logger.info(f"🔥 COMPRA DETECTADA: @{username} desbloqueó {subject_uuid}")
                await self.notify_telegram(f"🔥 ¡VENTA! @{username} acaba de comprar el video en Fanvue. Aurora está preparando el envío...")
                # Aquí llamaremos a la función de entrega automática que configuraremos
                await self.entregar_video_premium(username, subject_uuid)

            self.processed_notifications.append(nt_id)
            new_found = True

        if new_found:
            self.processed_notifications = self.processed_notifications[-200:] # Mantener últimos 200
            self._save_processed_notifications()

    async def entregar_video_premium(self, fan_username, subject_uuid):
        """Busca al usuario en Telegram y le entrega el video largo."""
        logger.info(f"🔎 Buscando a @{fan_username} en el registro de clientes...")
        
        target_chat_id = None
        # Buscar en nuevos_clientes.json
        clientes_path = project_root / "AURORA_APP" / "data" / "nuevos_clientes.json"
        
        if clientes_path.exists():
            try:
                with open(clientes_path, "r", encoding="utf-8") as f:
                    clientes = json.load(f)
                    # Tomar únicos por user_id
                    vistos = set()
                    for c in clientes:
                        uid = c.get("user_id")
                        if uid in vistos: continue
                        vistos.add(uid)
                        
                        # Buscamos por username de Telegram (si coinciden con el de Fanvue)
                        if str(c.get("username", "")).lower() == str(fan_username).lower():
                            target_chat_id = uid
                            break
                        # O por nombre si lo tenemos registrado
                        if str(c.get("first_name", "")).lower() == str(fan_username).lower():
                            target_chat_id = uid
                            break
            except Exception as e:
                logger.error(f"Error leyendo clientes: {e}")

        video_path = project_root / "VIDEO_PREMIUM_LARGO.mp4"
        caption = "¡Bebé! Aquí tienes tu premio completo... 🫦 Me puse muy traviesa solo para vos. Disfrútalo mucho y dime qué tal te pareció 😏🔥"

        if target_chat_id and video_path.exists():
            logger.info(f"🚀 Enviando video premium a @{fan_username} (ID: {target_chat_id})")
            
            # Telegram Bot API tiene límite de 50MB para subida directa.
            url = f"https://api.telegram.org/bot{os.getenv('TELEGRAM_BOT_TOKEN')}/sendVideo"
            try:
                with open(video_path, "rb") as v:
                    r = requests.post(url, data={"chat_id": target_chat_id, "caption": caption}, files={"video": v}, timeout=120)
                
                if r.status_code in [200, 201]:
                    await self.notify_telegram(f"✅ Video entregado AUTOMÁTICAMENTE a @{fan_username} en Telegram.")
                else:
                    logger.error(f"Respuesta Telegram: {r.text}")
                    await self.notify_telegram(f"⚠️ El video es muy pesado (149MB) para el bot. @{fan_username} ya pagó, ¡envíaselo manual mor! 👄")
            except Exception as e:
                logger.error(f"Error en envío: {e}")
                await self.notify_telegram(f"❌ Error al enviar video a @{fan_username}. Hazlo manual mor.")
        else:
            await self.notify_telegram(f"⚠️ @{fan_username} compró el video pero no lo encontré en mi base de datos de Telegram o el video no existe en el PC. ¡Atiéndelo manual! 🫦")

    async def notify_telegram(self, text):
        """Envía notificación al grupo de operaciones."""
        try:
            requests.post(f"https://api.telegram.org/bot{os.getenv('TELEGRAM_BOT_TOKEN')}/sendMessage", 
                         json={"chat_id": os.getenv("TELEGRAM_OPERACIONES_ID"), "text": text})
        except:
            pass

    async def send_auto_voice_thanks(self, username, text):
        """Genera un audio con IA y lo encola para que el bot de Telegram lo envíe al grupo."""
        try:
            # Generar el audio con la voz de Aurora (VoiceHandler)
            filepath = self.vh.generate_voice(text, user_id=f"fanvue_{username}")
            if filepath:
                logger.info(f"🎙️ Audio de agradecimiento generado para @{username}: {filepath}")
                
                # Encolar para que el bot de Telegram lo envíe
                queue_file = project_root / "AURORA_APP" / "data" / "voice_queue.json"
                queue_file.parent.mkdir(parents=True, exist_ok=True)
                
                new_item = {
                    "audioPath": str(filepath),
                    "caption": f"🎁 Audio para @{username} (Fanvue): {text[:50]}...",
                    "sent": False,
                    "timestamp": datetime.now().isoformat()
                }
                
                queue = []
                if queue_file.exists():
                    try:
                        with open(queue_file, "r") as f:
                            queue = json.load(f)
                    except:
                        queue = []
                
                queue.append(new_item)
                with open(queue_file, "w") as f:
                    json.dump(queue, f, indent=2)
                
                logger.info(f"✅ Audio encolado en voice_queue.json")
        except Exception as e:
            logger.error(f"Error generando/encolando audio auto: {e}")

if __name__ == "__main__":
    import asyncio
    automation = FanvueAutomation()
    asyncio.run(automation.run())
