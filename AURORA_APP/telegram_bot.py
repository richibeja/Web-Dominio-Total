#!/usr/bin/env python3
"""
Bot de Telegram profesional para agencia de modelos.
- /start: bienvenida seductora + foto de la modelo principal + menú de botones.
- Botones: Ver Galería 📸 | Hablar en Privado 💬 | Acceso VIP (Fanvue) 💎
- Acceso VIP envía el link de Fanvue.
- Registra cada nuevo cliente en data/nuevos_clientes.json para el dashboard Streamlit.
- Sistema Espejo: mensajes de clientes se reenvían al grupo de operaciones; si un
  trabajador hace REPLY a ese mensaje, el bot envía la respuesta al cliente sin revelar
  la identidad del trabajador.
"""

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

# Asegurar que ai_models se encuentre (el script está en AURORA_APP)
_project_root = Path(__file__).resolve().parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from dotenv import load_dotenv
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)
from ai_models.voice_handler import VoiceHandler
import shutil

# Cargar .env: primero el de la raíz (unificado), luego el local (override)
load_dotenv(_project_root / ".env")
load_dotenv(Path(__file__).resolve().parent / ".env", override=True)

# Configuración desde .env
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
# Grupo de operaciones: TELEGRAM_OPERACIONES_ID o TELEGRAM_CHAT_ID (mismo ID del grupo de trabajadores).
# IMPORTANTE: En @BotFather → tu bot → Bot Settings → Group Privacy = DISABLED (Turn off).
# Si no, el bot no recibe los mensajes del grupo y los trabajadores no podrán usar replies.
TELEGRAM_OPERACIONES_ID = (
    os.getenv("TELEGRAM_OPERACIONES_ID", "").strip()
    or os.getenv("TELEGRAM_CHAT_ID", "").strip()
)
TELEGRAM_CHANNEL_ID = os.getenv("TELEGRAM_CHANNEL_ID", "").strip()
FANVUE_LINK = os.getenv("FANVUE_LINK", "https://www.fanvue.com/utopiafinca").strip()
FANVUE_REGALO_URL = os.getenv("FANVUE_REGALO_URL", "").strip() or FANVUE_LINK
# Link al bot para "Hablar conmigo" (ej: https://t.me/TuBot_bot)
TELEGRAM_BOT_LINK = os.getenv("TELEGRAM_BOT_LINK", "").strip() or os.getenv("LINK_VENTAS_TELEGRAM", "").strip()
MODEL_PHOTO_PATH = os.getenv("MODEL_PHOTO_PATH", "").strip()
MODEL_PHOTO_URL = os.getenv("MODEL_PHOTO_URL", "").strip()

# Admins que pueden usar /audio (IDs separados por comas). Si vacío, cualquiera en el grupo.
TELEGRAM_ADMIN_IDS = [x.strip() for x in os.getenv("TELEGRAM_ADMIN_IDS", "").split(",") if x.strip()]

# Mapeo (id_grupo, message_id_en_grupo) -> chat_id del cliente (para enviar la respuesta)
_reply_map: dict[tuple[int, int], int] = {}
_last_client_id: int = None  # Almacena el ID del último cliente que escribió por privado
_active_live_jobs = {} # chat_id -> list of jobs
# Rutas de datos
DATA_DIR = Path(__file__).resolve().parent / "data"
QUEUE_FILE = DATA_DIR / "voice_queue.json"
CLIENTES_LOG = DATA_DIR / "nuevos_clientes.json"
LIVE_CONFIG_FILE = DATA_DIR / "live_config.json"


def format_instagram_message_for_group(usuario_instagram: str, mensaje: str, traduccion: str) -> str:
    """
    Formato para reenviar mensajes de Instagram al grupo de operaciones.
    El puente Instagram (ej. monitor.py) debe enviar este texto al TELEGRAM_OPERACIONES_ID.
    """
    return (
        "📸 NUEVO MENSAJE DE INSTAGRAM\n"
        f"Usuario: {usuario_instagram}\n"
        f'Mensaje: "{mensaje}"\n'
        f"Traducción: {traduccion}"
    )


def _ensure_data_dir():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if not CLIENTES_LOG.exists():
        CLIENTES_LOG.write_text("[]", encoding="utf-8")


def _log_nuevo_cliente(user_id: int, username, first_name: str, last_name):
    """Registra un nuevo cliente en el log para el dashboard Streamlit."""
    _ensure_data_dir()
    entry = {
        "date": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "user_id": user_id,
        "username": username or "",
        "first_name": first_name or "",
        "last_name": last_name or "",
    }
    try:
        data = json.loads(CLIENTES_LOG.read_text(encoding="utf-8"))
        if not isinstance(data, list):
            data = []
        data.insert(0, entry)
        # Mantener últimas 500 entradas
        data = data[:500]
        CLIENTES_LOG.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception as e:
        print(f"[telegram_bot] Error escribiendo log: {e}")


def _get_main_photo():
    """Devuelve la foto de la modelo: archivo local o URL."""
    if MODEL_PHOTO_PATH and Path(MODEL_PHOTO_PATH).exists():
        return open(MODEL_PHOTO_PATH, "rb")
    if MODEL_PHOTO_URL and (MODEL_PHOTO_URL.startswith("http://") or MODEL_PHOTO_URL.startswith("https://")):
        return MODEL_PHOTO_URL
    return None


from config.utopia_finca_links import LINKS

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Bienvenida automática: mensaje seductor + foto de la modelo + menú de botones."""
    user = update.effective_user
    if user:
        _log_nuevo_cliente(
            user_id=user.id,
            username=user.username,
            first_name=user.first_name or "Usuario",
            last_name=user.last_name,
        )

    welcome = (
        "¡Hola mi amor! 💋 Soy Cherry.\n\n"
        "Me encanta que estés aquí. En Instagram me censuran todo, pero este es mi espacio 100% privado donde no hay reglas... 😈💦\n\n"
        "Si quieres ver de lo que soy capaz y tocar el paraíso conmigo hoy, entra a mi VIP o compra mi regalito especial 👇"
    )

    # BOTONES DE ORO (Funnel de Ventas)
    btn_fanvue = InlineKeyboardButton("🔞 MI VIP SIN CENSURA (Fanvue)", url=LINKS.get("fanvue"))
    btn_ebook = InlineKeyboardButton("📘 FOTOS PROHIBIDAS ($7 Hotmart)", url=LINKS.get("ebook_payment"))
    btn_canal = InlineKeyboardButton("📢 VER MUESTRAS GRATIS", url=LINKS.get("telegram"))
    btn_hablar = InlineKeyboardButton("💬 HABLAR PRIVADO", callback_data="hablar")
    btn_videos = InlineKeyboardButton("🎥 VIDEOS EXCLUSIVOS", callback_data="videos_exclusivos")

    # Diseño del teclado
    keyboard = [
        [btn_fanvue],       # Botón Principal (Fanvue)
        [btn_videos],       # NUEVO: Acceso a muestra de video
        [btn_ebook, btn_canal], # Secundarios
        [btn_hablar]        # Acción de chat
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    photo = _get_main_photo()
    if photo:
        try:
            await update.message.reply_photo(
                photo=photo,
                caption=welcome,
                reply_markup=reply_markup,
                parse_mode=None,
            )
        finally:
            if hasattr(photo, "close"):
                photo.close()
    else:
        await update.message.reply_text(welcome, reply_markup=reply_markup)


async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Responde a los clics en los botones."""
    query = update.callback_query
    await query.answer()

    data = query.data
    
    if data == "hablar":
        await query.message.reply_text(
            "¡Me encanta que quieras hablar! 💬\n\n"
            "Escribe aquí abajo lo que quieras decirme... soy toda oídos (y más) 😈👇"
        )
    elif data == "vip": # Fallback antiguo
        await query.message.reply_text(f"Entra aquí bebé: {LINKS.get('fanvue')}")
    elif data == "videos_exclusivos":
        await query.message.reply_text("¡Uy mor! 🫦 Te va a encantar lo que tengo preparado... Aquí tienes una pequeña muestra de lo que te espera en mi VIP. Si quieres videos personalizados solo para ti, ¡suscríbete ahora! 👇")
        
        # Ruta del video de muestra
        video_path = os.path.join(_project_root, "content", "videos", "grok-video-c11b00ec-b3b1-4994-a664-a985c4ed9f86.mp4")
        
        if os.path.exists(video_path):
            with open(video_path, "rb") as video_file:
                await query.message.reply_video(
                    video=video_file,
                    caption="🔞 ESTO ES SOLO EL PRINCIPIO... Entra a mi VIP para ver todo sin censura 🔥",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("💎 MI VIP SIN CENSURA", url=LINKS.get("fanvue"))],
                        [InlineKeyboardButton("🎁 VIDEOS PERSONALIZADOS", url=LINKS.get("sales_page"))]
                    ])
                )
        else:
            await query.message.reply_text(
                "¡Uy! Justo ahora estoy grabando uno nuevo... 🔥\nPero puedes ver todos mis videos aquí: " + LINKS.get("fanvue") + "\n\nO pide uno solo para ti aquí: " + LINKS.get("sales_page")
            )


async def _client_text_mirror(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Sistema Espejo: todo mensaje de texto de un cliente se reenvía al grupo de operaciones.
    Ahora también detecta comentarios en el canal y responde automáticamente.
    """
    if not TELEGRAM_OPERACIONES_ID:
        return
    try:
        group_id_ops = int(TELEGRAM_OPERACIONES_ID)
    except ValueError:
        return

    chat = update.effective_chat
    user = update.effective_user
    msg = update.message
    
    if not chat or not msg or not msg.text:
        return

    # 1. Detectar tipo de chat: Privado o Comentario en Grupo
    is_private = chat.type == "private"
    is_comment = False
    
    # Un comentario en Telegram es un reply a un post "automatic forward" del canal en el grupo de discusión
    if chat.type in ["group", "supergroup"] and msg.reply_to_message:
        if msg.reply_to_message.is_automatic_forward:
            is_comment = True
            # Evitar que el bot se responda a sí mismo o a otros bots en el grupo
            if user and user.is_bot:
                return

    if not (is_private or is_comment):
        return

    user_id = user.id if user else chat.id
    nombre = (user.first_name or "") if user else ""
    if user and user.last_name:
        nombre = f"{nombre} {user.last_name}".strip()
    nombre = nombre or "Cliente"
    texto = msg.text.strip()
    
    # Guardar como último cliente activo para envío de audios si es privado
    if is_private:
        global _last_client_id
        _last_client_id = user_id

    # Espejo al grupo de operaciones para DMs privados solamente (para no saturar el grupo con comentarios públicos)
    if is_private:
        msg_para_grupo = (
            "📥 NUEVO MENSAJE PRIVADO\n"
            f"ID: {user_id}\n"
            f"Cliente: {nombre}\n"
            f"Dice: {texto}\n"
            "-------------------------"
        )
        try:
            sent = await context.bot.send_message(chat_id=group_id_ops, text=msg_para_grupo)
            _reply_map[(group_id_ops, sent.message_id)] = chat.id
        except Exception as e:
            print(f"[telegram_bot] Error espejo: {e}")

    # --- RESPUESTA IA Automática ---
    try:
        # Acción de chat para naturalidad
        await context.bot.send_chat_action(chat_id=chat.id, action="typing")
        
        from ai_models.ai_handler import AIHandler
        ai = AIHandler()
        
        # Determinar plataforma para el prompt
        platform = "telegram_comment" if is_comment else "telegram"
        
        # Simular tiempo de escritura (2s a 5s)
        import asyncio
        import random
        await asyncio.sleep(random.uniform(2.0, 5.0))
        
        respuesta = await ai.get_response(texto, user_id=str(user_id), dialect="paisa", platform=platform)
        if respuesta:
            await msg.reply_text(respuesta)
            if is_private:
                # Avisar al grupo de operaciones que respondimos el privado
                await context.bot.send_message(chat_id=group_id_ops, text=f"🤖 Aurora respondió a {nombre}: {respuesta}")
            
    except Exception as e:
        print(f"[telegram_bot] Error en respuesta IA: {e}")

async def _client_voice_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Recibe nota de voz del cliente en privado, la transcribe y la responde con voz realista."""
    if update.effective_chat.type != "private":
        return

    user = update.effective_user
    if not update.message or not update.message.voice:
        return
        
    status_msg = await update.message.reply_text("Escuchando... 🎧")

    try:
        file = await context.bot.get_file(update.message.voice.file_id)
        import tempfile
        import os
        
        with tempfile.NamedTemporaryFile(suffix=".ogg", delete=False) as tmp:
            audio_path = tmp.name
            
        await file.download_to_drive(audio_path)
        
        # Transcribir
        from ai_models.ai_handler import AIHandler
        from ai_models.voice_handler import VoiceHandler
        
        ai = AIHandler()
        texto_transcrito = await ai.transcribe_audio(audio_path)
        
        if os.path.exists(audio_path):
            os.remove(audio_path)
            
        if not texto_transcrito:
            await status_msg.edit_text("Mor, no te entendí bien, se escuchaba un ruido raro 🙈")
            return
            
        await status_msg.edit_text("Pensando... 😏")
        
        global _last_client_id
        _last_client_id = user.id

        if TELEGRAM_OPERACIONES_ID:
            try:
                group_id = int(TELEGRAM_OPERACIONES_ID)
                msg_para_grupo = (
                    f"🔉 AUDIO DE: {user.first_name} (ID: {user.id})\n"
                    f"Transcipción:\n\"{texto_transcrito}\""
                )
                sent = await context.bot.send_message(chat_id=group_id, text=msg_para_grupo)
                _reply_map[(group_id, sent.message_id)] = update.effective_chat.id
            except Exception as e:
                print(f"[telegram_bot] Error espejo de audio: {e}")
                
        # IA Responde
        respuesta_texto = await ai.get_response(texto_transcrito, user_id=str(user.id), dialect="paisa")
        
        await status_msg.edit_text("Grabando nota de voz... 🎤")
        
        vh = VoiceHandler()
        timestamp = int(datetime.now().timestamp())
        filepath_mp3 = vh.generate_voice(respuesta_texto, user_id=f"auto_{timestamp}")
        
        if filepath_mp3 and os.path.exists(filepath_mp3):
            await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="record_voice")
            with open(filepath_mp3, "rb") as voice_file:
                await update.message.reply_voice(voice=voice_file)
            await status_msg.delete()
        else:
            await update.message.reply_text(respuesta_texto)
            await status_msg.delete()
            
    except Exception as e:
        print(f"[telegram_bot] Error procesando voz: {e}")
        await status_msg.edit_text("Ay mor, me entró una llamada y no te pude responder con voz 🙈")


async def _group_reply_to_client(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Si alguien en el grupo de operaciones hace REPLY a un mensaje que envió el bot,
    el bot toma ese texto y se lo envía al cliente original. El cliente solo ve
    el mensaje como si viniera de la modelo; nunca se revela el nombre del trabajador.
    """
    # Log del chat_id para que puedas encontrar el ID del grupo (ej: -1008317949623)
    if update.effective_chat:
        print(f"[telegram_bot] Mensaje recibido de ID: {update.effective_chat.id}")
    if not TELEGRAM_OPERACIONES_ID:
        return
    try:
        group_id = int(TELEGRAM_OPERACIONES_ID)
    except ValueError:
        return
    if update.effective_chat.id != group_id:
        return
    if not update.message or not update.message.reply_to_message:
        return
    reply_to = update.message.reply_to_message
    if not reply_to.from_user or not reply_to.from_user.is_bot:
        return
    key = (group_id, reply_to.message_id)
    client_chat_id = _reply_map.get(key)
    if client_chat_id is None:
        return

    # 1. Manejar RESPUESTA DE TEXTO
    if update.message.text:
        texto_respuesta = update.message.text.strip()
        try:
            await context.bot.send_message(chat_id=client_chat_id, text=texto_respuesta)
        except Exception as e:
            print(f"[telegram_bot] Error enviando texto al cliente: {e}")

    # 2. Manejar NOTA DE VOZ HUMANA (de la socia)
    elif update.message.voice:
        try:
            await context.bot.send_voice(
                chat_id=client_chat_id, 
                voice=update.message.voice.file_id,
                caption=update.message.caption
            )
            print(f"[telegram_bot] Nota de voz humana reenviada al cliente {client_chat_id}")
        except Exception as e:
            print(f"[telegram_bot] Error enviando voz humana al cliente: {e}")

    # 3. Manejar ARCHIVOS DE AUDIO / MP3
    elif update.message.audio:
        try:
            await context.bot.send_audio(
                chat_id=client_chat_id, 
                audio=update.message.audio.file_id,
                caption=update.message.caption
            )
        except Exception as e:
            print(f"[telegram_bot] Error enviando audio al cliente: {e}")


async def ir_telegram(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Comando /ir_telegram: cuando un trabajador responde a un mensaje de Instagram 
    con este comando, encola automáticamente la invitación oficial.
    """
    if not update.message or not update.message.reply_to_message:
        return
        
    reply_to = update.message.reply_to_message
    texto_mirrored = (reply_to.text or "").strip()
    
    # Intentar obtener el username de Instagram del formato del mensaje mirrored
    from shared.telegram_operaciones import parse_instagram_username_from_telegram_message, add_reply_to_queue, INVITATION_MESSAGE, record_invitado_telegram
    
    username_ig = parse_instagram_username_from_telegram_message(texto_mirrored)
    
    if username_ig:
        # Encolar el mensaje de invitación para que monitor.py lo envíe a IG
        add_reply_to_queue(username_ig, INVITATION_MESSAGE)
        record_invitado_telegram(username_ig)
        await update.message.reply_text(f"✅ Invitación a Telegram encolada para @{username_ig}")
        print(f"[telegram_bot] Comando /ir_telegram procesado para @{username_ig}")
    else:
        await update.message.reply_text("❌ No pude detectar el usuario de Instagram en el mensaje original.")

def _is_admin(user_id: int) -> bool:
    """True si el usuario está en TELEGRAM_ADMIN_IDS. Si la lista está vacía, cualquiera puede."""
    if not TELEGRAM_ADMIN_IDS:
        return True
    return str(user_id) in TELEGRAM_ADMIN_IDS


async def audio_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Comando /audio [texto]: Genera audio con voz femenina Medellín (edge-tts) y lo envía
    al grupo de Operaciones como nota de voz. Solo admins si TELEGRAM_ADMIN_IDS está configurado.
    """
    if not update.message or not update.message.text:
        return

    user = update.effective_user
    chat = update.effective_chat
    
    # Permitir si es admin O si el mensaje viene del grupo de operaciones
    es_grupo_ops = False
    if TELEGRAM_OPERACIONES_ID and chat:
        gid_env = str(TELEGRAM_OPERACIONES_ID).strip()
        cid_actual = str(chat.id).strip()
        # Comparar normal y con prefijo -100
        if cid_actual == gid_env or cid_actual == gid_env.replace("-100", "-") or ("-100" + cid_actual.lstrip("-")) == gid_env:
            es_grupo_ops = True

    if user and not _is_admin(user.id) and not es_grupo_ops:
        await update.message.reply_text("No tienes permiso para usar este comando fuera del grupo de operaciones.")
        return

    parts = update.message.text.split(maxsplit=1)
    if len(parts) < 2:
        await update.message.reply_text("Uso: /audio [texto para convertir a voz paisa]")
        return

    raw_text = parts[1].strip()
    
    # Extraer estilo si existe: /audio [Seductora] Hola amor o /audio Seductora] Hola amor (más flexible)
    import re
    # Busca algo como [Texto] o Texto] al principio
    style_match = re.search(r'^\[?([\w\d]+)\]\s*(.*)', raw_text, re.IGNORECASE)
    if style_match:
        style = style_match.group(1).strip().capitalize()
        texto_a_generar = style_match.group(2).strip()
        
        # Validar que el estilo sea uno de los conocidos (insensible a mayúsculas)
        estilos_validos = ["Sonrisa", "Seductora", "Susurro", "Alegre", "Bodega", "Mia", "Stella", "Englishbabe"]
        if style.capitalize() in [e.capitalize() for e in estilos_validos]:
            style = style.capitalize()
            # El texto ya es texto_a_generar (group 2)
        else:
            # Si el estilo no es válido, tratamos todo el raw_text como el mensaje
            style = "Default"
            texto_a_generar = raw_text
        
        os.environ["Qwen3_TEMP_STYLE"] = style
    else:
        texto_a_generar = raw_text

    print(f"[telegram_bot] Generando audio para: '{texto_a_generar}' con estilo: '{os.environ.get('Qwen3_TEMP_STYLE', 'Default')}'")

    status_msg = await update.message.reply_text("Invocando a Qwen3... espera un momentico, mor. 🤖✨")

    try:
        vh = VoiceHandler()
        timestamp = int(datetime.now().timestamp())
        filepath_mp3 = vh.generate_voice(texto_a_generar, user_id=f"manual_{timestamp}")

        if filepath_mp3 and os.path.exists(filepath_mp3):
            # Persistencia: guardar en generated_audios (raíz del proyecto)
            project_root = Path(__file__).resolve().parent.parent
            persist_dir = project_root / "generated_audios"
            persist_dir.mkdir(parents=True, exist_ok=True)
            persist_path = persist_dir / os.path.basename(filepath_mp3)
            shutil.copy(filepath_mp3, persist_path)

            # Enviar al grupo de Operaciones. Si falla (chat not found), enviar al chat actual.
            caption = texto_a_generar[:50] + "..." if len(texto_a_generar) > 50 else texto_a_generar
            chat_actual = update.effective_chat.id
            enviado = False

            # Probar grupo: -5180483988 o formato supergrupo -1005180483988
            ids_a_probar = []
            if TELEGRAM_OPERACIONES_ID:
                try:
                    gid = int(TELEGRAM_OPERACIONES_ID)
                    ids_a_probar.append(gid)
                    if gid < 0 and not str(gid).startswith("-100"):
                        ids_a_probar.append(int("-100" + str(gid).lstrip("-")))
                except (ValueError, TypeError):
                    pass

            with open(filepath_mp3, "rb") as voice_file:
                for chat_id in ids_a_probar:
                    try:
                        await context.bot.send_voice(chat_id=chat_id, voice=voice_file, caption=caption)
                        enviado = True
                        break
                    except Exception as e:
                        if "chat not found" in str(e).lower() or "400" in str(e):
                            voice_file.seek(0)
                            continue
                        raise

                if not enviado:
                    voice_file.seek(0)
                    await context.bot.send_voice(chat_id=chat_actual, voice=voice_file, caption=caption)

            await status_msg.delete()
        else:
            await status_msg.edit_text("Error al generar el audio. Los servidores de Qwen3 o el fallback de Salomé están saturados. Intenta de nuevo en un momento.")

    except Exception as e:
        print(f"[telegram_bot] Error en /audio: {e}")
        await status_msg.edit_text(f"Fallo: {str(e)}")


async def broadcast_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Comando /broadcast [mensaje]: Envía un mensaje o audio a todos los clientes.
    Si se hace REPLY a un audio con /broadcast, se envía ese audio a todos.
    """
    user = update.effective_user
    if not user or not _is_admin(user.id):
        await update.message.reply_text("No tienes permiso para difundir mensajes.")
        return

    # 1. Detectar si es un mensaje de texto o un REPLY a multimedia
    media_to_send = None
    media_type = None # 'voice', 'audio', 'text'
    broadcast_text = ""

    if update.message.reply_to_message:
        reply = update.message.reply_to_message
        if reply.voice:
            media_to_send = reply.voice.file_id
            media_type = 'voice'
        elif reply.video:
            media_to_send = reply.video.file_id
            media_type = 'video'
        elif reply.photo:
            media_to_send = reply.photo[-1].file_id # Tomar la de mayor resolución
            media_type = 'photo'
        elif reply.audio:
            media_to_send = reply.audio.file_id
            media_type = 'audio'
        elif reply.text:
            broadcast_text = reply.text
            media_type = 'text'
        
        # Mantener el caption original si hay uno
        caption = reply.caption if reply.caption else ""
    
    # Si no hay media de un reply, buscar texto en el comando
    if not media_type:
        parts = update.message.text.split(maxsplit=1)
        if len(parts) < 2:
            await update.message.reply_text("Uso: /broadcast [mensaje] o haz REPLY a un video/foto/audio con /broadcast")
            return
        broadcast_text = parts[1].strip()
        media_type = 'text'
        caption = ""

    if not CLIENTES_LOG.exists():
        await update.message.reply_text("No hay clientes registrados aún.")
        return

    try:
        with open(CLIENTES_LOG, "r", encoding="utf-8") as f:
            clientes = json.load(f)
        
        user_ids = list(set([c["user_id"] for c in clientes if "user_id" in c]))
        if not user_ids:
            await update.message.reply_text("No hay IDs de clientes válidos.")
            return

        status_msg = await update.message.reply_text(f"🚀 Difundiendo {media_type} a {len(user_ids)} clientes...")
        
        success_count = 0
        error_count = 0
        
        for uid in user_ids:
            try:
                if media_type == 'voice':
                    await context.bot.send_voice(chat_id=uid, voice=media_to_send, caption=caption)
                elif media_type == 'video':
                    await context.bot.send_video(chat_id=uid, video=media_to_send, caption=caption)
                elif media_type == 'photo':
                    await context.bot.send_photo(chat_id=uid, photo=media_to_send, caption=caption)
                elif media_type == 'audio':
                    await context.bot.send_audio(chat_id=uid, audio=media_to_send, caption=caption)
                else:
                    await context.bot.send_message(chat_id=uid, text=broadcast_text)
                success_count += 1
                # Evitar bloqueo por spam (1 mensaje por segundo es seguro para broadcasts pequeños)
                import asyncio
                await asyncio.sleep(1.0)
            except Exception as e:
                error_count += 1

        
        # 2. Enviar al Canal Público (Si está configurado)
        sent_to_channel = False
        if TELEGRAM_CHANNEL_ID:
            try:
                # Si empieza por @ es un username, si no es un ID numérico
                chan_target = TELEGRAM_CHANNEL_ID
                if TELEGRAM_CHANNEL_ID.startswith('-') or TELEGRAM_CHANNEL_ID.isdigit():
                    chan_target = int(TELEGRAM_CHANNEL_ID)
                
                if media_type == 'voice':
                    await context.bot.send_voice(chat_id=chan_target, voice=media_to_send, caption=caption)
                elif media_type == 'video':
                    await context.bot.send_video(chat_id=chan_target, video=media_to_send, caption=caption)
                elif media_type == 'photo':
                    await context.bot.send_photo(chat_id=chan_target, photo=media_to_send, caption=caption)
                elif media_type == 'audio':
                    await context.bot.send_audio(chat_id=chan_target, audio=media_to_send, caption=caption)
                else:
                    await context.bot.send_message(chat_id=chan_target, text=broadcast_text)
                sent_to_channel = True
            except Exception as ec:
                print(f"[broadcast] Error enviando al canal {TELEGRAM_CHANNEL_ID}: {ec}")

        # 3. Reporte final
        status_text = (
            f"✅ Difusión de {media_type} completada.\n"
            f"👤 Enviados por Privado: {success_count}\n"
            f"📢 Publicado en Canal: {'SÍ' if sent_to_channel else 'NO'}\n"
            f"❌ Errores: {error_count}"
        )
        await status_msg.edit_text(status_text)
        
    except Exception as e:
        await update.message.reply_text(f"Error en broadcast: {e}")


async def live_start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Inicia la secuencia automatizada de mensajes para un directo.
    Uso: /live_start [nombre_config o vacío para default]
    """
    user = update.effective_user
    if not user or not _is_admin(user.id):
        await update.message.reply_text("No tienes permiso para iniciar directos.")
        return

    chat_id = update.effective_chat.id
    args = context.args
    config_name = args[0] if args else "default_live"

    if not LIVE_CONFIG_FILE.exists():
        await update.message.reply_text("❌ Error: No se encontró el archivo live_config.json en data/")
        return

    try:
        with open(LIVE_CONFIG_FILE, "r", encoding="utf-8") as f:
            config = json.load(f)
        
        live_sequence = config.get(config_name)
        if not live_sequence:
            await update.message.reply_text(f"❌ No se encontró la configuración '{config_name}'")
            return

        # Limpiar jobs previos en este chat si existen
        if chat_id in _active_live_jobs:
            for job in _active_live_jobs[chat_id]:
                job.schedule_removal()
            _active_live_jobs[chat_id] = []

        await update.message.reply_text(f"🚀 **MODO LIVE ACTIVADO** ({config_name})\nIniciando secuencia de {len(live_sequence)} mensajes...")

        _active_live_jobs[chat_id] = []
        
        for step in live_sequence:
            delay = step.get("time_seconds", 0)
            text = step.get("message", "")
            
            # Programar el envío
            job = context.job_queue.run_once(
                _send_live_message, 
                when=delay, 
                data={"chat_id": chat_id, "text": text},
                name=f"live_{chat_id}_{delay}"
            )
            _active_live_jobs[chat_id].append(job)

    except Exception as e:
        await update.message.reply_text(f"Error al iniciar live: {e}")

async def _send_live_message(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Función auxiliar para enviar los mensajes programados del live con efecto humano."""
    job = context.job
    chat_id = job.data["chat_id"]
    text = job.data["text"]
    
    try:
        # Acción de 'Escribiendo...' para que no parezca un bot rígido
        await context.bot.send_chat_action(chat_id=chat_id, action="typing")
        
        # Simular tiempo de escritura: 1 segundo por cada 20 caracteres aprox (mínimo 2s, máximo 6s)
        import asyncio
        typing_time = min(max(len(text) / 20, 2), 6)
        await asyncio.sleep(typing_time)
        
        await context.bot.send_message(chat_id=chat_id, text=text, parse_mode=None)
        print(f"[live] Mensaje humano enviado a {chat_id}: {text[:30]}...")
    except Exception as e:
        print(f"[live] Error enviando mensaje programado: {e}")

async def live_stop_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Detiene cualquier secuencia de live activa en el chat actual."""
    user = update.effective_user
    if not user or not _is_admin(user.id):
        return

    chat_id = update.effective_chat.id
    if chat_id in _active_live_jobs and _active_live_jobs[chat_id]:
        count = len(_active_live_jobs[chat_id])
        for job in _active_live_jobs[chat_id]:
            job.schedule_removal()
        _active_live_jobs[chat_id] = []
        await update.message.reply_text(f"🛑 **MODO LIVE DETENIDO**. Se cancelaron {count} mensajes pendientes.")
    else:
        await update.message.reply_text("No hay ningún live activo en este chat.")

async def mi_id_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Responde con el ID del chat actual."""
    chat_id = update.effective_chat.id
    chat_type = update.effective_chat.type
    await update.message.reply_text(
        f"📍 INFO DE CONEXIÓN:\n\n"
        f"Tu ID de Chat es: `{chat_id}`\n"
        f"Tipo de chat: {chat_type}\n\n"
        f"Copia este número y ponlo en el campo TELEGRAM_OPERACIONES_ID de tu archivo .env"
    )


async def check_voice_queue(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Revisa si hay audios encolados por el Dashboard (Node) y los envía."""
    if not QUEUE_FILE.exists():
        return

    queue = []
    try:
        content = QUEUE_FILE.read_text(encoding="utf-8").strip()
        if not content or content == "[]":
            return
            
        queue = json.loads(content)
    except Exception as e:
        print(f"[telegram_bot] Error leyendo cola de voz: {e}")
        return

    if not queue:
        return

    # IMPORTANTE: Para evitar bucles infinitos si hay un error, 
    # limpiamos la cola ANTES de procesar o nos aseguramos de que no se repitan.
    # Aquí optamos por vaciar el archivo inmediatamente.
    try:
        QUEUE_FILE.write_text("[]", encoding="utf-8")
    except Exception as e:
        print(f"[telegram_bot] CRÍTICO: No se pudo vaciar la cola, abortando para evitar spam: {e}")
        return

    print(f"[telegram_bot] Procesando {len(queue)} audios encolados...")

    for item in queue:
        if item.get("sent"):
            continue

        audio_path = item.get("audio_path") or item.get("audioPath")
        caption = item.get("caption", "")
        to_channel = item.get("to_channel", False)
        
        if not audio_path or not os.path.exists(audio_path):
            print(f"[telegram_bot] Audio no encontrado: {audio_path}")
            continue

        try:
            print(f"[telegram_bot] Enviando audio: {audio_path}")
            
            # 1. Enviar al Grupo de Operaciones
            if TELEGRAM_OPERACIONES_ID:
                try:
                    gid = int(TELEGRAM_OPERACIONES_ID)
                    with open(audio_path, "rb") as voice:
                        await context.bot.send_voice(chat_id=gid, voice=voice, caption=caption)
                except Exception as ge:
                    print(f"[telegram_bot] Error enviando al grupo: {ge}")

            # 2. Enviar al Canal Público (SI se pidió)
            if to_channel and TELEGRAM_CHANNEL_ID:
                try:
                    target_chan = TELEGRAM_CHANNEL_ID
                    if TELEGRAM_CHANNEL_ID.replace('-', '').isdigit():
                        target_chan = int(TELEGRAM_CHANNEL_ID)
                    
                    with open(audio_path, "rb") as voice:
                        await context.bot.send_voice(chat_id=target_chan, voice=voice, caption=caption)
                except Exception as chan_e:
                    print(f"[telegram_bot] Error enviando al canal: {chan_e}")

            # 3. Enviar al Último Cliente (Solo si no es para el canal)
            if not to_channel and _last_client_id:
                try:
                    with open(audio_path, "rb") as voice:
                        await context.bot.send_voice(chat_id=_last_client_id, voice=voice, caption=caption)
                except Exception as ce:
                    print(f"[telegram_bot] Error enviando al cliente: {ce}")
            
            # Pequeño delay entre envíos para evitar bloqueos
            import asyncio
            await asyncio.sleep(1.0)

        except Exception as e:
            print(f"[telegram_bot] Error procesando item de la cola: {e}")
            # Continuamos con el siguiente item en lugar de morir


async def _post_init_sistema_aurora(application: Application) -> None:
    """Al arrancar, envía mensaje de conexión al grupo de operaciones."""
    if not TELEGRAM_OPERACIONES_ID:
        return
    raw_id = TELEGRAM_OPERACIONES_ID.strip()
    # Posibles formatos: tal cual, con -, con -100
    ids_to_try = []
    try:
        if raw_id.lstrip("-").isdigit():
            base_id = raw_id.lstrip("-")
            ids_to_try.append(int(raw_id))            # Exacto
            ids_to_try.append(int(f"-{base_id}"))     # Grupo normal
            ids_to_try.append(int(f"-100{base_id}"))  # Supergrupo/Canal
            ids_to_try = list(set(ids_to_try))        # Unicos
    except:
        pass

    success = False
    for gid in ids_to_try:
        try:
            await application.bot.send_message(
                chat_id=gid,
                text="✅ CONEXIÓN ESTABLECIDA. Soy el bot oficial (SociosAnbelClub). Operadores, prepárense para recibir clientes de Instagram.",
            )
            print(f"[telegram_bot] Mensaje de conexión enviado al grupo {gid}.")
            success = True
            break
        except Exception:
            continue
    
    if not success:
         print(f"[telegram_bot] ⚠️ NO SE PUDO CONECTAR AL GRUPO DE OPERACIONES. ID probado: {TELEGRAM_OPERACIONES_ID}. Verifica que el bot esté en el grupo y sea ADMIN.")


def main() -> None:
    if not TELEGRAM_BOT_TOKEN:
        print("ERROR: Define TELEGRAM_BOT_TOKEN en .env (obtén el token con @BotFather en Telegram).")
        return

    application = (
        Application.builder()
        .token(TELEGRAM_BOT_TOKEN)
        .post_init(_post_init_sistema_aurora)
        .build()
    )
    
    # Agregar tarea periódica para revisar la cola de audios (cada 1 segundo)
    if application.job_queue:
        application.job_queue.run_repeating(check_voice_queue, interval=1.0, first=1.0)
    else:
        print("[telegram_bot] ADVERTENCIA: JobQueue no disponible. No se procesarán audios del Dashboard.")

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("ir_telegram", ir_telegram))
    application.add_handler(CommandHandler("audio", audio_command))
    application.add_handler(CommandHandler("broadcast", broadcast_command))
    application.add_handler(CommandHandler("live_start", live_start_command))
    application.add_handler(CommandHandler("live_stop", live_stop_command))
    application.add_handler(CommandHandler("mi_id", mi_id_command))
    application.add_handler(CallbackQueryHandler(button_callback))

    # Sistema Espejo: reenvío de mensajes de clientes al grupo de operaciones
    application.add_handler(
        MessageHandler(
            filters.TEXT & filters.ChatType.PRIVATE & ~filters.COMMAND,
            _client_text_mirror,
        )
    )
    application.add_handler(
        MessageHandler(
            filters.VOICE & filters.ChatType.PRIVATE,
            _client_voice_handler,
        )
    )
    # Handler para GRUPOS (Operaciones vs Públicos)
    # 1. Si es grupo de Operaciones -> _group_reply_to_client (Sistema Espejo)
    application.add_handler(
        MessageHandler(
            filters.TEXT & (filters.ChatType.GROUPS | filters.ChatType.CHANNEL),
            _handle_all_groups, 
        )
    )

    # Handler para MENSAJES DE CANAL (Channel Posts)
    # Si el bot es admin en el canal, puede responder o más bien "comentar" si se pudiera,
    # pero los bots no pueden comentar posts de canales directamente salvo en el grupo de discusión.
    # Sin embargo, si escuchamos channel_post, podemos registrarlo o intentar algo.
    # Por ahora nos centramos en GRUPOS (que es donde la gente chatea).

    # Handler explícito para Channel Posts
    application.add_handler(
        MessageHandler(
            filters.ChatType.CHANNEL & filters.TEXT,
            _handle_all_groups, 
        )
    )

    print("Bot de Telegram en marcha con IA (Gemini Flash). Detén con Ctrl+C.")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


# --- Lógica Unificada de Grupos ---
from ai_models.ai_handler import AIHandler
_ai_handler = AIHandler()

async def _handle_all_groups(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Maneja mensajes en grupos. 
    - Si es el Grupo de Operaciones: Busca replies para enviarlos al cliente (Espejo).
    - Si es CUALQUIER OTRO GRUPO (Comunidad/Canal): Responde con IA.
    """
    msg = update.message or update.channel_post
    if not msg:
        return

    chat_id = update.effective_chat.id
    text = msg.text
    
    # 1. Verificar si es Grupo de Operaciones
    is_ops_group = False
    if TELEGRAM_OPERACIONES_ID:
        try:
            ops_id = int(TELEGRAM_OPERACIONES_ID)
            # Manejo de IDs con/sin prefijo -100 (Telegram quirk)
            if chat_id == ops_id:
                is_ops_group = True
        except:
            pass
            
    if is_ops_group:
        # Lógica de Espejo (Workers respondiendo a clientes)
        await _group_reply_to_client(update, context)
        return

    # 2. Si NO es operaciones, es un Grupo Público/Comunidad -> IA RESPONDE
    # Evitar bucles: no responder a otros bots
    # En canales, msg.from_user puede ser None (es el canal).
    user = msg.from_user
    if user and user.is_bot:
        return
        
    # Evitar responder a mensajes muy cortos o comandos (ya filtrados pero por si acaso)
    if not text or text.startswith("/"):
        return

    # Filtro anti-spam de "star"
    if text.lower().strip().startswith("star"):
        return

    try:
        # Acción de "Escribiendo..." para naturalidad
        await context.bot.send_chat_action(chat_id=chat_id, action="typing")
        
        # Detectar si es un comentario (Reply a un post del canal)
        is_comment = False
        if msg.reply_to_message and msg.reply_to_message.is_automatic_forward:
            is_comment = True

        # Determinar plataforma (prompt)
        # Si es comentario, usar estilo público. Si es un grupo normal, usar estilo Telegram estándar.
        platform = "telegram_comment" if is_comment else "telegram"
        
        # Simular tiempo de escritura (2s a 5s)
        import asyncio
        import random
        await asyncio.sleep(random.uniform(2.5, 5.0))
        
        uid = str(update.effective_user.id) if update.effective_user else str(chat_id)
        # Usar el handler de IA con la plataforma adecuada
        response = await _ai_handler.get_response(text, user_id=uid, dialect="paisa", platform=platform)
        
        if response:
            if msg:
                await msg.reply_text(response)
            else:
                await context.bot.send_message(chat_id=chat_id, text=response)
            
    except Exception as e:
        print(f"[telegram_bot] Error IA en grupo público/canal: {e}")


if __name__ == "__main__":
    main()
