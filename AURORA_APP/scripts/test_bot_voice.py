import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Path configuration
_project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_project_root))

# Load .env exactly as the corrected bot does
_env_path = _project_root / ".env"
load_dotenv(_env_path)

print(f"--- DIAGNÓSTICO DE VOZ ---")
print(f"VOICE_PROVIDER: {os.getenv('VOICE_PROVIDER')}")
print(f"HF_API_TOKEN: {'Configurado' if os.getenv('HF_API_TOKEN') else 'FALTA'}")
print(f"Qwen3_SPACE_URL: {os.getenv('Qwen3_SPACE_URL')}")

try:
    from ai_models.voice_handler import VoiceHandler
    vh = VoiceHandler()
    print(f"VoiceHandler initialized with provider: {vh.voice_provider}")
    
    test_text = "Hello my love, I am testing the new English voice model for our club."
    print(f"Generando voz para: '{test_text}'...")
    
    # Force style if needed for test
    os.environ["Qwen3_TEMP_STYLE"] = "Mia"
    
    filepath = vh.generate_voice(test_text, user_id="diag_test")
    
    if filepath and os.path.exists(filepath):
        print(f"✅ ÉXITO: Audio generado en {filepath}")
        print(f"Tamaño: {os.path.getsize(filepath)} bytes")
    else:
        print(f"❌ FALLO: generate_voice devolvió {filepath}")
except Exception as e:
    print(f"❌ ERROR CRÍTICO: {str(e)}")
    import traceback
    traceback.print_exc()
