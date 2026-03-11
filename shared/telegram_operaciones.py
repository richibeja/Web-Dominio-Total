"""
Integración Instagram DMs <-> Grupo de Telegram Operaciones.

- Envía nuevos DMs de Instagram al grupo TELEGRAM_OPERACIONES_ID.
- Cola de respuestas desde Telegram para enviar por Instagram (puente humano).
- Estado 'pending human' para pausar la IA mientras se espera respuesta humana.
"""
import os
import re
import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)

# Directorio de datos (compartido con instagram_bot)
DATA_DIR = Path(__file__).resolve().parent.parent / "data"
PENDING_HUMAN_FILE = DATA_DIR / "instagram_pending_human.json"
REPLY_QUEUE_FILE = DATA_DIR / "telegram_to_instagram_replies.json"
INVITADOS_TELEGRAM_FILE = DATA_DIR / "instagram_invitados_telegram.json"
CLIENT_LANG_FILE = DATA_DIR / "instagram_client_languages.json"

# Mensaje fijo de invitación a Telegram (comando /ir_telegram)
INVITATION_MESSAGE = (
    "Cielo, Instagram se ha puesto muy aburrido y me borra los mensajes más traviesos... 🔥 "
    "No quiero que nos corten la charla. Escríbeme a mi Telegram personal para que podamos hablar sin filtros "
    "y te pueda enviar cositas que aquí no puedo: https://t.me/SociosAnbelClub_bot. "
    "¡Te espero allí ahora mismo! 💖"
)

# Segundos que el monitor espera respuesta humana antes de usar IA
WAIT_FOR_HUMAN_SECONDS = int(os.getenv("INSTAGRAM_WAIT_FOR_HUMAN_SECONDS", "15"))


def _ensure_data_dir():
    DATA_DIR.mkdir(parents=True, exist_ok=True)


def _load_json(path: Path, default):
    if not path.exists():
        return default
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.warning(f"Error leyendo {path}: {e}")
        return default


def _save_json(path: Path, data):
    _ensure_data_dir()
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"Error guardando {path}: {e}")


# --- Idioma del cliente (para traducir respuestas de vuelta) ---

def save_client_language(username: str, lang: str) -> None:
    """Guarda el idioma detectado del cliente para traducir la respuesta al enviar."""
    data = _load_json(CLIENT_LANG_FILE, {})
    if not isinstance(data, dict):
        data = {}
    data[username] = {"lang": lang, "updated": datetime.utcnow().isoformat() + "Z"}
    _save_json(CLIENT_LANG_FILE, data)


def get_client_language(username: str) -> Optional[str]:
    """Devuelve el idioma guardado del cliente (ej. 'en', 'pt') o None si es español/no guardado."""
    data = _load_json(CLIENT_LANG_FILE, {})
    if not isinstance(data, dict):
        return None
    entry = data.get(username)
    if not entry or not isinstance(entry, dict):
        return None
    lang = (entry.get("lang") or "").strip().lower()
    return lang if lang and lang != "es" else None


# --- Envío al grupo de Telegram ---

def send_instagram_dm_to_telegram(username: str, message_text: str) -> bool:
    """
    Envía el contenido del DM de Instagram al grupo de Operaciones.
    Si el mensaje NO está en español: detecta idioma, traduce a español y envía ambos.
    Formato con traducción: 📸 INSTAGRAM: [Username] Mensaje Original: [texto] Traducción: [español] -------------------------
    """
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_OPERACIONES_ID")
    if not token or not chat_id:
        logger.debug("TELEGRAM_BOT_TOKEN o TELEGRAM_OPERACIONES_ID no configurados, omitiendo envío a Operaciones")
        return False

    text_to_send = message_text or ""
    try:
        from shared.translate_utils import detect_language, translate_to_spanish
        detected = detect_language(text_to_send)
        if detected and detected.lower() != "es":
            translation = translate_to_spanish(text_to_send)
            if translation:
                text_to_send = (
                    f"📸 INSTAGRAM_DM: [{username}]\n"
                    f"Mensaje Original: [{message_text}]\n"
                    f"Traducción: [{translation}]\n-------------------------"
                )
                save_client_language(username, detected)
                logger.info(f"🌐 Idioma detectado para @{username}: {detected}, traducción incluida.")
            else:
                text_to_send = f"📸 INSTAGRAM_DM: [{username}]\nMensaje: [{message_text}]\n-------------------------"
        else:
            text_to_send = f"📸 INSTAGRAM_DM: [{username}]\nMensaje: [{message_text}]\n-------------------------"
    except Exception as e:
        logger.warning(f"Traducción para Operaciones falló: {e}, enviando mensaje original.")
        text_to_send = f"📸 INSTAGRAM: [{username}] Mensaje: [{message_text}]\n-------------------------"

    try:
        import urllib.request
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        body = json.dumps({
            "chat_id": chat_id.strip(),
            "text": text_to_send,
            "disable_web_page_preview": True,
        }).encode("utf-8")
        req = urllib.request.Request(url, data=body, method="POST", headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=10) as r:
            if 200 <= r.status < 300:
                logger.info(f"✅ DM de Instagram enviado a Telegram Operaciones: @{username}")
                return True
    except Exception as e:
        # Si el bot fue expulsado del grupo, capturamos el error para que NO CRASHEE
        if "kicked" in str(e) or "Forbidden" in str(e):
            logger.error(f"⚠️ EL BOT FUE EXPULSADO DEL GRUPO DE OPERACIONES. Revisa TELEGRAM_OPERACIONES_ID.")
        else:
            logger.warning(f"Error enviando DM a Telegram Operaciones: {e}")
    return False
    return False


# --- Pending human (pausar IA) ---

def set_pending_human(username: str, message_preview: str = ""):
    data = _load_json(PENDING_HUMAN_FILE, {})
    data[username] = {"since": datetime.utcnow().isoformat() + "Z", "message_preview": (message_preview or "")[:80]}
    _save_json(PENDING_HUMAN_FILE, data)


def get_pending_human(username: str) -> Optional[dict]:
    data = _load_json(PENDING_HUMAN_FILE, {})
    return data.get(username)


def clear_pending_human(username: str):
    data = _load_json(PENDING_HUMAN_FILE, {})
    if username in data:
        del data[username]
        _save_json(PENDING_HUMAN_FILE, data)


def is_waiting_for_human(username: str) -> bool:
    return get_pending_human(username) is not None


# --- Cola de respuestas Telegram -> Instagram ---

def add_reply_to_queue(username: str, text: str):
    """Añade una respuesta desde Telegram para enviar a Instagram."""
    _ensure_data_dir()
    item = {"username": username, "text": text, "timestamp": datetime.utcnow().isoformat() + "Z"}
    data = _load_json(REPLY_QUEUE_FILE, [])
    if not isinstance(data, list):
        data = []
    data.append(item)
    _save_json(REPLY_QUEUE_FILE, data)
    logger.info(f"📥 Respuesta para Instagram encolada: @{username}")


def get_all_pending_replies():
    """Devuelve todos los ítems de la cola (copia)."""
    data = _load_json(REPLY_QUEUE_FILE, [])
    return list(data) if isinstance(data, list) else []


def consume_reply(username: str) -> Optional[str]:
    """
    Consume y devuelve la primera respuesta en cola para `username`, o None.
    Elimina ese ítem de la cola.
    """
    data = _load_json(REPLY_QUEUE_FILE, [])
    if not isinstance(data, list):
        return None
    for i, item in enumerate(data):
        if isinstance(item, dict) and item.get("username") == username:
            text = item.get("text", "")
            data.pop(i)
            _save_json(REPLY_QUEUE_FILE, data)
            return text
    return None


def consume_next_reply() -> Optional[dict]:
    """
    Consume y devuelve el primer ítem de la cola (cualquier usuario), o None.
    Elimina ese ítem de la cola.
    """
    data = _load_json(REPLY_QUEUE_FILE, [])
    if not isinstance(data, list) or not data:
        return None
    item = data.pop(0)
    _save_json(REPLY_QUEUE_FILE, data)
    return item if isinstance(item, dict) else None


def parse_instagram_username_from_telegram_message(text: str) -> Optional[str]:
    """
    Parsea el username del mensaje que enviamos al grupo.
    Formato: 📸 INSTAGRAM_DM: [Username] Mensaje: ... o 📸 INSTAGRAM_COMMENT: [Username] ...
    """
    if not text or "INSTAGRAM_" not in text:
        return None
    # Busca el contenido dentro de los primeros corchetes [] después de INSTAGRAM_
    m = re.search(r"INSTAGRAM_(?:DM|COMMENT):\s*\[([^\]]+)\]", text, re.IGNORECASE)
    if m:
        return m.group(1).strip()
    return None


# --- Invitados a Telegram (para /ir_telegram y Dashboard) ---

def record_invitado_telegram(username: str) -> None:
    """Marca al usuario como 'Invitado a Telegram' para que el Dashboard lo registre."""
    _ensure_data_dir()
    data = _load_json(INVITADOS_TELEGRAM_FILE, [])
    if not isinstance(data, list):
        data = []
    entry = {
        "username": username,
        "invited_at": datetime.utcnow().isoformat() + "Z",
        "source": "ir_telegram",
    }
    data.append(entry)
    _save_json(INVITADOS_TELEGRAM_FILE, data)
    logger.info(f"📋 Usuario @{username} marcado como Invitado a Telegram.")


def get_invitados_telegram(ultimos: int = 100):
    """Devuelve la lista de invitados a Telegram (para el Dashboard)."""
    data = _load_json(INVITADOS_TELEGRAM_FILE, [])
    if not isinstance(data, list):
        return []
    return data[-ultimos:][::-1]
