import json
import os
from pathlib import Path

def queue_audio_for_telegram(audio_path, caption="", to_channel=False):
    """Encola un audio para que el bot de Telegram lo envíe."""
    project_root = Path(__file__).resolve().parent.parent
    queue_file = project_root / "AURORA_APP" / "data" / "voice_queue.json"
    
    # Asegurar que el directorio existe
    queue_file.parent.mkdir(parents=True, exist_ok=True)
    
    # Cargar cola actual
    queue = []
    if queue_file.exists():
        try:
            with open(queue_file, "r", encoding="utf-8") as f:
                queue = json.load(f)
        except:
            queue = []
            
    # Agregar nuevo item
    queue.append({
        "audio_path": str(audio_path),
        "caption": caption,
        "to_channel": to_channel,
        "sent": False
    })
    
    # Guardar cola
    try:
        with open(queue_file, "w", encoding="utf-8") as f:
            json.dump(queue, f, ensure_ascii=False, indent=2)
    except IOError as e:
        logger.error(f"Error al guardar la cola de audio: {e}")
        return False
    
    return True
