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

# Cargar .env unificado desde la raíz
_env_path = _project_root / ".env"
load_dotenv(_env_path)

# Configuración desde .env
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
# Grupo de operaciones: TELEGRAM_OPERACIONES_ID o TELEGRAM_CHAT_ID (mismo ID del grupo de trabajadores).
# IMPORTANTE: En @BotFather → tu bot → Bot Settings → Group Privacy = DISABLED (Turn off).
# Si no, el bot no recibe los mensajes del grupo y los trabajadores no podrán usar replies.
TELEGRAM_OPERACIONES_ID = (
    os.getenv("TELEGRAM_OPERACIONES_ID", "").strip()
    or os.getenv("TELEGRAM_CHAT_ID", "").strip()
)
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
# Rutas de datos
DATA_DIR = Path(__file__).resolve().parent / "data"
QUEUE_FILE = DATA_DIR / "voice_queue.json"
CLIENTES_LOG = DATA_DIR / "nuevos_clientes.json"


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
        "Hola, amor 💋\n\n"
        "Soy la modelo principal de la agencia. Aquí puedes verme más de cerca, hablar conmigo en privado "
        "o acceder al contenido exclusivo.\n\n"
        "Elige qué quieres hacer 👇"
    )

    # Tres botones de bienvenida (pretty): enlaces cuando estén en .env, si no callbacks
    btn_ver = InlineKeyboardButton("🔥 Ver Contenido Exclusivo", url=FANVUE_LINK) if FANVUE_LINK else InlineKeyboardButton("🔥 Ver Contenido Exclusivo", callback_data="vip")
    btn_hablar = InlineKeyboardButton("💬 Hablar conmigo", url=TELEGRAM_BOT_LINK) if TELEGRAM_BOT_LINK else InlineKeyboardButton("💬 Hablar conmigo", callback_data="privado")
    btn_regalo = InlineKeyboardButton("🎁 Regalo de Bienvenida", url=FANVUE_REGALO_URL) if FANVUE_REGALO_URL else InlineKeyboardButton("🎁 Regalo de Bienvenida", callback_data="vip")
    keyboard = [[btn_ver], [btn_hablar], [btn_regalo]]
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
    """Responde a los clics en Ver Galería, Hablar en Privado y Acceso VIP."""
    query = update.callback_query
    await query.answer()

    data = query.data
    if data == "vip":
        await query.message.reply_text(
            f"Aquí tienes tu acceso VIP 💎\n\n{FANVUE_LINK}\n\n"
            "Entra y disfruta del contenido exclusivo. Te espero dentro 😘"
        )
    elif data == "galeria":
        # Opción: enviar otra foto o mensaje. Si tienes MODEL_PHOTO_URL/PATH, puedes enviar la misma u otra.
        photo = _get_main_photo()
        if photo:
            try:
                await query.message.reply_photo(
                    photo=photo,
                    caption="Aquí tienes un adelanto 📸 Si quieres más, pásate por VIP 💎",
                )
            finally:
                if hasattr(photo, "close"):
                    photo.close()
        else:
            await query.message.reply_text(
                "La galería completa está en el contenido VIP 💎 Pulsa «Acceso VIP» para entrar."
            )
    elif data == "privado":
        await query.message.reply_text(
            "Para hablar en privado conmigo, escríbeme aquí mismo 💬 "
            "Responde a este mensaje y te leeré. Si quieres contenido exclusivo, usa Acceso VIP 💎"
        )


async def _client_text_mirror(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Sistema Espejo: todo mensaje de texto de un cliente (que no sea comando) se reenvía
    al grupo de operaciones con formato estándar. Se guarda el message_id para que un
    REPLY en el grupo se envíe de vuelta al cliente.
    """
    if not TELEGRAM_OPERACIONES_ID:
        return
    try:
        group_id = int(TELEGRAM_OPERACIONES_ID)
    except ValueError:
        return
    if update.effective_chat.type != "private" or not update.message or not update.message.text:
        return
    user = update.effective_user
    user_id = user.id if user else update.effective_chat.id
    nombre = (user.first_name or "") if user else ""
    if user and user.last_name:
        nombre = f"{nombre} {user.last_name}".strip()
    nombre = nombre or "Cliente"
    texto = (update.message.text or "").strip()
    if not texto:
        return
        
    # Guardar como último cliente activo para envío de audios
    global _last_client_id
    _last_client_id = user_id

    msg_para_grupo = (
        "📥 NUEVO MENSAJE\n"
        f"ID: {user_id}\n"
        f"Cliente: {nombre}\n"
        f"Dice: {texto}\n"
        "-------------------------"
    )
    try:
        sent = await context.bot.send_message(chat_id=group_id, text=msg_para_grupo)
        _reply_map[(group_id, sent.message_id)] = update.effective_chat.id
    except Exception as e:
        print(f"[telegram_bot] Error reenviando al grupo de operaciones: {e}")


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
    texto_respuesta = (update.message.text or "").strip()
    if not texto_respuesta:
        return
    try:
        await context.bot.send_message(chat_id=client_chat_id, text=texto_respuesta)
    except Exception as e:
        print(f"[telegram_bot] Error enviando respuesta al cliente: {e}")


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


async def check_voice_queue(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Revisa si hay audios encolados por el Dashboard (Node) y los envía."""
    if not QUEUE_FILE.exists():
        return

    try:
        content = QUEUE_FILE.read_text(encoding="utf-8").strip()
        if not content or content == "[]":
            return
            
        queue = json.loads(content)
        if not queue:
            return

        # Procesar solo los que no han sido enviados
        pending = [item for item in queue if not item.get("sent")]
        if not pending:
            # Si todos están marcados, podríamos limpiar el archivo
            QUEUE_FILE.write_text("[]", encoding="utf-8")
            return

        for item in pending:
            audio_path = item.get("audio_path") or item.get("audioPath")
            caption = item.get("caption", "")
            
            if audio_path and os.path.exists(audio_path):
                print(f"[telegram_bot] Procesando audio encolado: {audio_path}")
                
                # 1. Enviar al Grupo de Operaciones
                if TELEGRAM_OPERACIONES_ID:
                    try:
                        gid = int(TELEGRAM_OPERACIONES_ID)
                        with open(audio_path, "rb") as voice:
                            await context.bot.send_voice(chat_id=gid, voice=voice, caption=caption)
                        print(f"[telegram_bot] Audio enviado al grupo {gid}")
                    except Exception as ge:
                        print(f"[telegram_bot] Error enviando al grupo: {ge}")

                # 2. Enviar al Último Cliente
                if _last_client_id:
                    try:
                        with open(audio_path, "rb") as voice:
                            await context.bot.send_voice(chat_id=_last_client_id, voice=voice, caption=caption)
                        print(f"[telegram_bot] Audio enviado al cliente {_last_client_id}")
                    except Exception as ce:
                        print(f"[telegram_bot] Error enviando al cliente: {ce}")
            
            item["sent"] = True

        # Limpiar la cola (o vaciar el archivo si procesamos todo)
        QUEUE_FILE.write_text("[]", encoding="utf-8")

    except Exception as e:
        print(f"[telegram_bot] Error procesando cola de voz: {e}")

async def _post_init_sistema_aurora(application: Application) -> None:
    """Al arrancar, envía mensaje de conexión al grupo de operaciones."""
    if not TELEGRAM_OPERACIONES_ID:
        return
    try:
        group_id = int(TELEGRAM_OPERACIONES_ID)
        await application.bot.send_message(
            chat_id=group_id,
            text="✅ CONEXIÓN ESTABLECIDA. Soy el bot oficial (SociosAnbelClub). Operadores, prepárense para recibir clientes de Instagram.",
        )
        print("[telegram_bot] Mensaje de conexión enviado al grupo de operaciones.")
    except ValueError:
        print("[telegram_bot] TELEGRAM_OPERACIONES_ID o TELEGRAM_CHAT_ID no es un ID válido. Verifica tu .env")
    except Exception as e:
        print(f"[telegram_bot] No se pudo enviar al grupo de operaciones: {e}. ¿El ID del grupo en .env es correcto?")


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
    application.add_handler(CallbackQueryHandler(button_callback))

    # Sistema Espejo: reenvío de mensajes de clientes al grupo de operaciones
    application.add_handler(
        MessageHandler(
            filters.TEXT & filters.ChatType.PRIVATE & ~filters.COMMAND,
            _client_text_mirror,
        )
    )
    # Respuesta desde el grupo: REPLY a un mensaje del bot → se envía al cliente (sin revelar trabajador)
    application.add_handler(
        MessageHandler(
            filters.TEXT & filters.ChatType.GROUPS,
            _group_reply_to_client,
        )
    )

    print("Bot de Telegram en marcha. Detén con Ctrl+C.")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
