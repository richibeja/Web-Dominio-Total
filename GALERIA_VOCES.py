import os
import sys
from pathlib import Path

# Agregar raíz del proyecto al path
PROJECT_ROOT = Path(os.getcwd())
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Forzar proveedor Qwen
os.environ["VOICE_PROVIDER"] = "qwen"

from ai_models.voice_handler import VoiceHandler
from gradio_client import Client

vh = VoiceHandler()
hf_token = os.getenv("HF_API_TOKEN")
space_url = os.getenv("Qwen3_SPACE_URL", "Qwen/Qwen3-TTS-Demo")

# Voces para probar
voces_demo = [
    "Sonrisa / 西班牙语拉美-索尼莎",
    "Bodega / 西班牙语-博德加",
    "Cherry / 芊悦" # Esta es la que suele sonar más joven y suave
]

test_text = "Hola, mi amor. Escuchá bien estas tres voces y decime cuál es la que más te gusta para tus modelos."

print(f"--- INICIANDO CASTEO DE VOCES ELITE ---")

for i, voz in enumerate(voces_demo):
    print(f"Probando Voz {i+1}: {voz}...")
    try:
        filename = f"DEMO_VOZ_{i+1}.mp3"
        out_path = Path(vh.output_dir) / filename
        
        client = Client(space_url, token=hf_token)
        result = client.predict(
            text=test_text,
            voice_display=voz,
            language_display="Auto / 自动",
            api_name="/tts_interface"
        )
        
        temp_path = result[0] if isinstance(result, tuple) else result
        if temp_path:
            import shutil
            shutil.copy(temp_path, str(out_path))
            print(f"✅ Generada Voz {i+1} en: {out_path}")
    except Exception as e:
        print(f"❌ Error en Voz {i+1}: {e}")

print("\nListo. Por favor escucha DEMO_VOZ_1, 2 y 3 en la carpeta voice_output.")
