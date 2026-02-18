import os
import sys
from pathlib import Path

# Agregar raíz del proyecto al path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from ai_models.voice_handler import VoiceHandler
from dotenv import load_dotenv

def test_qwen_generation():
    load_dotenv()
    print("Iniciando prueba de Qwen3-TTS...")
    
    # Asegurar que el proveedor es qwen
    os.environ["VOICE_PROVIDER"] = "qwen"
    
    vh = VoiceHandler()
    text = "Hola mor, ¿cómo estás? Esto es una prueba de la nueva IA Qwen Tres."
    
    print(f"Generando audio para: '{text}'")
    filepath = vh.generate_voice(text, user_id="test_qwen")
    
    if filepath and os.path.exists(filepath):
        print(f"✅ ÉXITO: Audio generado en {filepath}")
        print(f"Tamaño del archivo: {os.path.getsize(filepath)} bytes")
    else:
        print("❌ ERROR: No se generó el audio. Revisa los logs.")

if __name__ == "__main__":
    # Crear carpeta tests si no existe
    Path("tests").mkdir(exist_ok=True)
    test_qwen_generation()
