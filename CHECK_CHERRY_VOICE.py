import os
import sys
from pathlib import Path

# Agregar raíz del proyecto al path
PROJECT_ROOT = Path(os.getcwd())
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from ai_models.voice_handler import VoiceHandler

vh = VoiceHandler()

test_text = "Hola, soy Cherry. Estoy haciendo una prueba para confirmar que mi voz elite funciona perfectamente."

print("🔍 VERIFICANDO VOCES...")
print(f"Motor configurado: {os.getenv('VOICE_PROVIDER')}")
print(f"Voz configurada: {os.getenv('Qwen3_VOICE_NAME')}")

path = vh.generate_voice(test_text, user_id="CHECK_CHERRY")

if path and os.path.exists(path):
    print(f"✅ Audio generado en: {path}")
else:
    print("❌ Error en la generación.")
