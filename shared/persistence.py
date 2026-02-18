"""
Persistencia de datos: conversations_map, thread_ids, reengagement_log.
Mejoras de seguridad según informe Antigravity.
"""
import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
CONVERSATIONS_MAP_FILE = DATA_DIR / "conversations_map.json"
REENGAGEMENT_LOG_FILE = DATA_DIR / "reengagement_log.json"


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


# --- conversations_map.json: IDs Telegram <-> Instagram (persistencia) ---

def get_conversation_map() -> Dict[str, Dict[str, Any]]:
    """Devuelve el mapa de conversaciones: username -> {telegram_id, instagram_thread_id, updated}."""
    data = _load_json(CONVERSATIONS_MAP_FILE, {})
    return data if isinstance(data, dict) else {}


def get_instagram_thread_id(username: str) -> Optional[str]:
    """Devuelve el thread_id de Instagram guardado para este username, o None."""
    data = get_conversation_map()
    entry = data.get(username)
    if not entry or not isinstance(entry, dict):
        return None
    return (entry.get("instagram_thread_id") or "").strip() or None


def get_telegram_id_for_instagram(username: str) -> Optional[str]:
    """Devuelve el ID de Telegram asociado a este username de Instagram, o None."""
    data = get_conversation_map()
    entry = data.get(username)
    if not entry or not isinstance(entry, dict):
        return None
def get_message_count(username: str) -> int:
    """Devuelve el contador de mensajes para este usuario."""
    data = get_conversation_map()
    entry = data.get(username)
    if not entry or not isinstance(entry, dict):
        return 0
    return entry.get("msg_count", 0)


def increment_message_count(username: str) -> int:
    """Incrementa y devuelve el nuevo contador de mensajes."""
    data = get_conversation_map()
    entry = data.get(username) or {}
    count = entry.get("msg_count", 0) + 1
    entry["msg_count"] = count
    data[username] = entry
    _save_json(CONVERSATIONS_MAP_FILE, data)
    return count


def get_lead_score(username: str) -> Dict:
    """
    Calcula un score de interés para un cliente.
    Retorna {'score': int, 'label': str, 'color': str}
    """
    data = get_conversation_map()
    entry = data.get(username, {})
    
    if not isinstance(entry, dict):
        return {"score": 0, "label": "Bajo", "color": "grey"}
        
    history = entry.get("history", [])
    msg_count = entry.get("msg_count", 0)
    
    score = 0
    keywords_high = ["fanvue", "link", "comprar", "pago", "vip", "sub", "suscribir", "video", "precio"]
    keywords_med = ["hermosa", "amor", "quiero", "donde", "ver", "mas"]
    
    # Analizar últimos 10 mensajes
    text_content = " ".join([m.get("content", "").lower() for m in history[-10:]])
    
    for k in keywords_high:
        if k in text_content: score += 5
        
    for k in keywords_med:
        if k in text_content: score += 2
        
    if msg_count > 30: score += 5
    elif msg_count > 10: score += 2
    
    if score >= 15:
        return {"score": score, "label": "HOT 🔥", "color": "red"}
    elif score >= 5:
        return {"score": score, "label": "Interesado 💎", "color": "orange"}
    else:
        return {"score": score, "label": "Frio ❄️", "color": "blue"}


def save_conversation_mapping(
    username: str,
    *,
    instagram_thread_id: Optional[str] = None,
    telegram_user_id: Optional[str] = None,
    last_responder: Optional[str] = None, # 'AI_RESPONSE' o 'HUMAN_RESPONSE'
) -> None:
    """
    Guarda o actualiza el mapeo username -> {instagram_thread_id, telegram_user_id, last_responder}.
    Persiste para que no se pierda al reiniciar.
    """
    data = get_conversation_map()
    entry = data.get(username) or {}
    if not isinstance(entry, dict):
        entry = {}
    
    # Asegurar que msg_count existe
    if "msg_count" not in entry:
        entry["msg_count"] = 0
        
    if instagram_thread_id:
        entry["instagram_thread_id"] = instagram_thread_id.strip()
    if telegram_user_id is not None:
        entry["telegram_user_id"] = str(telegram_user_id).strip()
    if last_responder:
        entry["last_responder"] = last_responder
        
    entry["updated"] = datetime.utcnow().isoformat() + "Z"
    data[username] = entry
    _save_json(CONVERSATIONS_MAP_FILE, data)
    logger.debug(f"Conversation map actualizado: @{username} (Responder: {last_responder})")


# --- reengagement_log.json: no enviar el mismo recordatorio dos veces al mismo cliente ---

def did_send_reengagement(username: str) -> bool:
    """
    Devuelve True si ya enviamos un mensaje de re-engagement a este usuario.
    Evita enviar dos veces el mismo recordatorio al mismo cliente.
    """
    data = _load_json(REENGAGEMENT_LOG_FILE, {})
    if not isinstance(data, dict):
        return False
    entry = data.get(username)
    if not entry:
        return False
    # entry puede ser {"sent_at": "iso", "message_preview": "..."} o simplemente True
    return bool(entry)


def record_reengagement_sent(username: str, message_preview: str = "") -> None:
    """
    Registra que se envió un mensaje de re-engagement a este usuario.
    Así nunca le enviamos dos veces el mismo tipo de recordatorio.
    """
    data = _load_json(REENGAGEMENT_LOG_FILE, {})
    if not isinstance(data, dict):
        data = {}
    data[username] = {
        "sent_at": datetime.utcnow().isoformat() + "Z",
        "message_preview": (message_preview or "")[:80],
    }
    _save_json(REENGAGEMENT_LOG_FILE, data)
    logger.info(f"📋 Re-engagement registrado para @{username} (no se repetirá).")


# --- WhatsApp Leads: rastrear quién ha recibido el número ---

def mark_as_whatsapp_lead(username: str) -> None:
    """Registra que este usuario ya recibió el número de WhatsApp."""
    data = get_conversation_map()
    entry = data.get(username) or {}
    entry["is_whatsapp_lead"] = True
    entry["whatsapp_lead_at"] = datetime.utcnow().isoformat() + "Z"
    data[username] = entry
    _save_json(CONVERSATIONS_MAP_FILE, data)
    logger.info(f"💎 @{username} marcado como LEAD de WhatsApp.")


def is_whatsapp_lead(username: str) -> bool:
    """Consulta si el usuario es un lead de WhatsApp."""
    data = get_conversation_map()
    return data.get(username, {}).get("is_whatsapp_lead", False)


# --- Notas y Links Personalizados: Memoria compartida con el socio ---

def save_client_note(username: str, note: str) -> None:
    """Guarda una nota psicológica o detalle del cliente."""
    data = get_conversation_map()
    entry = data.get(username) or {}
    entry["notes"] = note
    data[username] = entry
    _save_json(CONVERSATIONS_MAP_FILE, data)


def get_client_note(username: str) -> str:
    """Recupera la nota guardada para el cliente."""
    data = get_conversation_map()
    return data.get(username, {}).get("notes", "")


def save_client_phone(username: str, phone: str) -> None:
    """Guarda el número de WhatsApp real del cliente."""
    data = get_conversation_map()
    entry = data.get(username) or {}
    entry["phone"] = phone
    data[username] = entry
    _save_json(CONVERSATIONS_MAP_FILE, data)


def get_client_phone(username: str) -> str:
    """Recupera el teléfono guardado para el cliente."""
    data = get_conversation_map()
    return data.get(username, {}).get("phone", "")


def save_client_real_name(username: str, name: str) -> None:
    """Guarda el nombre real del cliente."""
    data = get_conversation_map()
    entry = data.get(username) or {}
    entry["real_name"] = name
    data[username] = entry
    _save_json(CONVERSATIONS_MAP_FILE, data)


def get_client_real_name(username: str) -> str:
    """Recupera el nombre real guardado para el cliente."""
    data = get_conversation_map()
    return data.get(username, {}).get("real_name", "")


def save_client_link(username: str, link: str) -> None:
    """Guarda un link personalizado de Fanvue para este cliente."""
    data = get_conversation_map()
    entry = data.get(username) or {}
    entry["sales_link"] = link
    data[username] = entry
    _save_json(CONVERSATIONS_MAP_FILE, data)


def get_client_link(username: str) -> str:
    """Recupera el link de venta para el cliente."""
    data = get_conversation_map()
    return data.get(username, {}).get("sales_link", "")
