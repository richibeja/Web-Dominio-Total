import os
from gradio_client import Client
from dotenv import load_dotenv
from pathlib import Path

load_dotenv(Path(__file__).resolve().parent.parent / ".env")
space_url = os.getenv("Qwen3_SPACE_URL", "Qwen/Qwen3-TTS-Demo")

print(f"Conectando a {space_url}...")
client = Client(space_url)

# Intentar obtener información del componente de selección de voz
# En Gradio, esto suele ser el primer componente o está en el config
print("\n--- Voces Disponibles en Qwen3-TTS ---")
try:
    # Esta es una forma de ver qué espera el API
    client.view_api()
except Exception as e:
    print(f"Error al ver API: {e}")
