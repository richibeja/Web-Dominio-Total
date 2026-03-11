import os
import logging
import base64
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class VoiceHandler:
    def __init__(self):
        self.project_root = Path(__file__).resolve().parent.parent
        load_dotenv(self.project_root / ".env")
        
        self.voice_provider = os.getenv("VOICE_PROVIDER", "gtts")
        self.output_dir = self.project_root / "voice_output"
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
    def _clean_text_for_tts(self, text):
        """Limpieza absoluta de símbolos y acotaciones para evitar que el robot los lea."""
        import re
        # 1. Eliminar TODO lo que esté entre asteriscos (stage directions como *suspiros*)
        text = re.sub(r'\*.*?\*', '', text)
        
        # 2. Eliminar acotaciones entre paréntesis, corchetes o llaves
        text = re.sub(r'\(.*?\)|\[.*?\]|\{.*?\}', '', text)
        
        # 3. Eliminar nombres de personajes y diálogos tipo "AURORA:"
        text = re.sub(r'^[A-ZÁÉÍÓÚÑa-z ]+[:：]', '', text, flags=re.MULTILINE)
        
        # 4. Eliminar TODO lo que no sea letra, número o puntuación básica
        # Solo dejamos pasar lo esencial para que el motor no se confunda
        text = re.sub(r'[^a-zA-ZáéíóúÁÉÍÓÚñÑ0-9\s.,!?;:¡¿]', ' ', text)
        
        # 5. Colapsar espacios
        text = re.sub(r'\s+', ' ', text).strip()
        
        return text

    def generate_voice(self, text, user_id="manual", fx_list=None):
        """Genera audio a partir del texto y opcionalmente mezcla efectos de ambiente."""
        clean_text = self._clean_text_for_tts(text)
        if not clean_text:
            return None
            
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"voice_{user_id}_{timestamp}.mp3"
        out_path = self.output_dir / filename
        
        if self.voice_provider not in {"edge-tts", "gtts", "qwen", "elevenlabs"}:
            raise ValueError(f"Proveedor TTS desconocido: {self.voice_provider}")
        provider = self.voice_provider
        
        # Si se especifica una voz de edge-tts via env (usado por tts.py)
        edge_voice = os.getenv("VOICE_EDGE_CODE", "es-CO-SalomeNeural")
        
        try:
            if provider == "qwen":
                # Motor de Nueva Generación Qwen3-TTS (Hugging Face)
                hf_token = os.getenv("HF_API_TOKEN")
                space_url = os.getenv("Qwen3_SPACE_URL", "Qwen/Qwen3-TTS-Demo")
                voice_name = os.getenv("Qwen3_VOICE_NAME", "Sonrisa / 西班牙语拉美-索尼莎")
                
                if hf_token:
                    try:
                        from gradio_client import Client
                        client = Client(space_url, token=hf_token)
                        result = client.predict(
                            text=clean_text,
                            voice_display=voice_name,
                            language_display="Auto / 自动",
                            api_name="/tts_interface"
                        )
                        # El resultado suele ser una tupla (audio_path, stats)
                        temp_path = result[0] if isinstance(result, tuple) else result
                        if temp_path and os.path.exists(temp_path):
                            import shutil
                            shutil.copy(temp_path, str(out_path))
                            print(f"💎 MOTOR ELITE ACTIVO: Usando voz '{voice_name}' via Hugging Face.")
                            return str(out_path)
                    except Exception as e:
                        print(f"⚠️ AVISO: Servidor Élite saturado. Usando motor de respaldo para no detener la producción.")
                        logger.error(f"Qwen3-TTS Elite Error: {e}. Cayendo a Edge-TTS...")
                
                # Fallback a Edge-TTS si falla Qwen o no hay Token
                import asyncio
                import edge_tts
                async def do_tts():
                    communicate = edge_tts.Communicate(clean_text, edge_voice, rate="-15%")
                    await communicate.save(str(out_path))
                asyncio.run(do_tts())
                print(f"🌬️ MOTOR DE RESPALDO: Usando voz colombiana estándar (Salome).")
                return str(out_path)

            elif provider == "edge-tts" or provider == "gtts":
                # Usamos edge-tts por ser el más confiable y gratuito con calidad
                import asyncio
                import edge_tts
                
                async def do_tts():
                    # Usamos una velocidad más lenta (-15%) para el toque sensual
                    communicate = edge_tts.Communicate(clean_text, edge_voice, rate="-15%", pitch="+0Hz")
                    await communicate.save(str(out_path))
                    
                asyncio.run(do_tts())
                return str(out_path)
                
            elif provider == "elevenlabs":
                # Implementación básica de ElevenLabs
                import requests
                api_key = os.getenv("ELEVENLABS_API_KEY")
                voice_id = os.getenv("ELEVENLABS_VOICE_ID", "pNInz6obpg8ndclQU7Nc") # Rachel
                
                url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
                headers = {"xi-api-key": api_key, "Content-Type": "application/json"}
                data = {"text": clean_text, "model_id": "eleven_multilingual_v2"}
                
                response = requests.post(url, json=data, headers=headers)
                if response.status_code == 200:
                    with open(out_path, "wb") as f:
                        f.write(response.content)
                    return str(out_path)
                else:
                    logger.error(f"ElevenLabs error: {response.text}")
                    return None
            else:
                logger.error(f"Proveedor desconocido: {provider}")
                return None
                
            if out_path and os.path.exists(out_path) and fx_list:
                self.mix_ambient(out_path, fx_list)
            
            return str(out_path) if out_path and os.path.exists(out_path) else None
                
        except Exception as e:
            logger.error(f"Error generando voz: {e}")
            return None

    def mix_ambient(self, voice_path, fx_list):
        """Mezcla la voz con sonidos de ambiente usando pydub. Seguro contra errores."""
        try:
            from pydub import AudioSegment
            voice = AudioSegment.from_file(voice_path)
            
            # Directorio de efectos
            fx_dir = self.project_root / "content" / "ambient_fx"
            
            # Mapa de efectos a archivos
            fx_map = {
                "🚿 Ducha / Agua": "ducha.mp3",
                "🎵 Música ASMR Suave": "musica.mp3",
                "🛏️ Sábanas / Roce": "sabanas.mp3"
            }
            
            mixed = voice
            any_fx = False
            
            for fx_name in fx_list:
                if fx_name in fx_map:
                    fx_file = fx_dir / fx_map[fx_name]
                    if fx_file.exists():
                        ambient = AudioSegment.from_file(str(fx_file))
                        # Bucle del sonido ambiente para cubrir toda la voz
                        if len(ambient) < len(voice):
                            ambient = ambient * (len(voice) // len(ambient) + 1)
                        ambient = ambient[:len(voice)] - 20 # Bajar volumen del ambiente
                        mixed = mixed.overlay(ambient)
                        any_fx = True
                    else:
                        print(f"ℹ️ Efecto '{fx_name}' saltado: Falta '{fx_map[fx_name]}' en content/ambient_fx")
            
            if any_fx:
                mixed.export(voice_path, format="mp3")
                print("🔊 MEZCLA DE AMBIENTE COMPLETADA: Audio enriquecido con efectos.")
                
        except Exception as e:
            print(f"⚠️ Error en mezcla de ambiente (saltando): {e}")
            # Si falla, no pasa nada, el archivo original ya existe

    def get_as_base64(self, file_path):
        """Lee un archivo y lo devuelve en base64."""
        if not file_path or not os.path.exists(file_path):
            return None
        with open(file_path, "rb") as f:
            return base64.b64encode(f.read()).decode('utf-8')
