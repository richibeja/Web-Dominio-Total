#!/usr/bin/env python3
"""
Script mejorado para generar audio con VoiceHandler (ElevenLabs/OpenAI/edge-tts).
Uso: python tts.py --text "Hola" --voice medellin
"""
import argparse
import base64
import json
import os
import sys
from pathlib import Path

# Añadir raíz del proyecto al path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--text", required=True, help="Texto a sintetizar")
    parser.add_argument("--voice", default="medellin", help="Voz (qwen, mexico, medellin, etc.)")
    parser.add_argument("--style", default=None, help="Estilo emocional (solo para Qwen3)")
    args = parser.parse_args()

    try:
        from ai_models.voice_handler import VoiceHandler
        from dotenv import load_dotenv
        
        # Cargar variables de entorno
        load_dotenv(PROJECT_ROOT / ".env")
        
        # Silenciar logs para que no ensucien el stdout (importante para server.js)
        import logging
        logging.basicConfig(level=logging.ERROR)
        logging.getLogger("ai_models.voice_handler").setLevel(logging.ERROR)
        logging.getLogger("gradio_client").setLevel(logging.ERROR)
        
        # Si se especifica estilo, pasarlo via entorno temporal
        if args.style and args.style != "Default":
            os.environ["Qwen3_TEMP_STYLE"] = args.style
            
        vh = VoiceHandler()
        
        # El VoiceHandler ya maneja Qwen3 si está configurado en .env o forzado aquí
        out_path = vh.generate_voice(args.text, user_id="web_manual")
        
        if out_path and os.path.exists(out_path):
            with open(out_path, "rb") as f:
                audio_b64 = base64.b64encode(f.read()).decode("utf-8")
            
            result = {
                "audio_base64": audio_b64, 
                "path": os.path.abspath(out_path),
                "provider": vh.voice_provider
            }
            # Prefijo para que server.js lo encuentre fácil
            print(f"JSON_OUTPUT:{json.dumps(result)}")
        else:
            # Fallback a edge-tts si falla ElevenLabs o no está configurado
            raise Exception("No se pudo generar audio con VoiceHandler")
            
    except Exception as e:
        # Prefijo para que server.js lo encuentre fácil
        print(f"JSON_OUTPUT:{json.dumps({'error': f'Error en generación de voz Qwen3: {str(e)}'})}")
        sys.exit(1)

if __name__ == "__main__":
    main()
