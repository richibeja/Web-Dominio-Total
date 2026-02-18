"""
Sistema de voz femenina (Text-to-Speech) para el bot
"""
import os
import logging
from typing import Optional
from pathlib import Path
import tempfile

logger = logging.getLogger(__name__)

class VoiceHandler:
    """Maneja la generación de voz femenina desde texto"""
    
    def __init__(self):
        self.voice_provider = os.getenv("VOICE_PROVIDER", "gtts")  # gtts, pyttsx3, elevenlabs, openai, qwen
        self.output_dir = os.getenv("VOICE_OUTPUT_DIR", "voice_output")
        self.language = os.getenv("VOICE_LANGUAGE", "es")
        
        # Transcripción (STT)
        self.stt_provider = os.getenv("STT_PROVIDER", "openai")  # openai es el único por ahora
        
        # Crear directorio de salida si no existe
        Path(self.output_dir).mkdir(parents=True, exist_ok=True)
    
    def generate_voice(self, text: str, user_id: Optional[str] = None, language: Optional[str] = None) -> Optional[str]:
        """
        Genera un archivo de audio con voz femenina desde texto
        
        Args:
            text: Texto a convertir a voz
            user_id: ID del usuario (para nombres de archivo únicos)
            language: Idioma del texto (es, en, pt, fr, etc.)
        
        Returns:
            Ruta al archivo de audio generado, o None si falla
        """
        try:
            lang = language or self.language
            
            if self.voice_provider == "gtts":
                return self._generate_gtts(text, user_id, lang)
            elif self.voice_provider == "pyttsx3":
                return self._generate_pyttsx3(text, user_id, lang)
            elif self.voice_provider == "elevenlabs":
                return self._generate_elevenlabs(text, user_id, lang)
            elif self.voice_provider == "qwen":
                # Si el estilo es "Clon Paisa", forzar F5
                style = os.environ.get("Qwen3_TEMP_STYLE", "Default")
                if style == "Clon Paisa":
                    return self._generate_f5_clon(text, user_id, lang)
                return self._generate_qwen3(text, user_id, lang)
            elif self.voice_provider == "f5":
                return self._generate_f5_clon(text, user_id, lang)
            else:
                logger.warning(f"Proveedor de voz desconocido: {self.voice_provider}")
                return None
        except Exception as e:
            logger.error(f"Error al generar voz: {e}", exc_info=True)
            return None
    
    def _generate_gtts(self, text: str, user_id: Optional[str], lang: str) -> Optional[str]:
        """Genera voz usando Google Text-to-Speech (gTTS) o edge-tts (preferido por calidad)"""
        try:
            import uuid
            import asyncio
            
            # Intentar usar edge-tts (mejor calidad, gratuito) si está disponible
            try:
                import edge_tts
                voice = os.getenv("VOICE_EDGE_CODE", "es-CO-SalomeNeural")
                
                filename = f"{user_id or 'temp'}_{uuid.uuid4().hex[:8]}.mp3"
                filepath = os.path.join(self.output_dir, filename)
                
                # Usar texto limpio directamente (SSML causaba lectura de etiquetas)
                clean_text = self._clean_text_for_tts(text)
                
                # Velocidad ligeramente reducida para sonar más "paisita" de forma natural
                # Nota: edge-tts por defecto no acepta parámetros de velocidad sin SSML, 
                # así que usamos texto plano que es más seguro.
                communicate = edge_tts.Communicate(clean_text, voice)
                
                # Arreglo robusto para bucle de eventos (especialmente con Playwright)
                try:
                    loop = asyncio.get_event_loop()
                except RuntimeError:
                    loop = None
                
                if loop and loop.is_running():
                    # Si ya hay un bucle corriendo (como en el bot de Telegram o monitor.py)
                    # Ejecutamos en un hilo separado para evitar conflictos de re-entrada de asyncio
                    from concurrent.futures import ThreadPoolExecutor
                    with ThreadPoolExecutor() as executor:
                        future = executor.submit(asyncio.run, communicate.save(filepath))
                        future.result()
                else:
                    asyncio.run(communicate.save(filepath))
                
                logger.info(f"Voz generada con edge-tts (Salomé/Medellín): {filepath}")
                return filepath
            except (ImportError, Exception) as e:
                logger.warning(f"Error o falta edge-tts, usando gTTS como fallback: {e}")
                from gtts import gTTS
                
                # Limpiar texto
                clean_text = self._clean_text_for_tts(text)
                
                # Crear TTS con gTTS
                tts = gTTS(text=clean_text, lang=lang, slow=False)
                
                # Generar nombre de archivo único
                filename = f"{user_id or 'temp'}_{uuid.uuid4().hex[:8]}.mp3"
                filepath = os.path.join(self.output_dir, filename)
                
                # Guardar archivo
                tts.save(filepath)
                
                logger.info(f"Voz generada con gTTS: {filepath}")
                return filepath
        except Exception as e:
            logger.error(f"Error con generador gratuito: {e}")
            return None
    
    def _generate_pyttsx3(self, text: str, user_id: Optional[str], lang: str) -> Optional[str]:
        """Genera voz usando pyttsx3 (offline, menos natural)"""
        try:
            import pyttsx3
            import uuid
            
            engine = pyttsx3.init()
            
            # Configurar voz femenina
            voices = engine.getProperty('voices')
            for voice in voices:
                if 'female' in voice.name.lower() or 'mujer' in voice.name.lower() or 'woman' in voice.name.lower():
                    engine.setProperty('voice', voice.id)
                    break
            
            # Configurar velocidad y tono
            engine.setProperty('rate', 150)  # Velocidad
            engine.setProperty('volume', 0.9)  # Volumen
            
            # Limpiar texto
            clean_text = self._clean_text_for_tts(text)
            
            # Generar archivo
            filename = f"{user_id or 'temp'}_{uuid.uuid4().hex[:8]}.mp3"
            filepath = os.path.join(self.output_dir, filename)
            
            engine.save_to_file(clean_text, filepath)
            engine.runAndWait()
            
            logger.info(f"Voz generada: {filepath}")
            return filepath
        except ImportError:
            logger.error("pyttsx3 no instalado. Ejecuta: pip install pyttsx3")
            return None
        except Exception as e:
            logger.error(f"Error con pyttsx3: {e}")
            return None
    
    def _generate_elevenlabs(self, text: str, user_id: Optional[str], lang: str) -> Optional[str]:
        """Genera voz usando ElevenLabs (alta calidad, requiere API key)"""
        try:
            import requests
            import uuid
            
            api_key = os.getenv("ELEVENLABS_API_KEY")
            if not api_key:
                logger.error("ELEVENLABS_API_KEY no configurada")
                return None
            
            # Voice ID de voz femenina (puedes cambiarlo)
            voice_id = os.getenv("ELEVENLABS_VOICE_ID", "21m00Tcm4TlvDq8ikWAM")  # Voz femenina por defecto
            
            url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
            headers = {
                "Accept": "audio/mpeg",
                "Content-Type": "application/json",
                "xi-api-key": api_key
            }
            
            data = {
                "text": self._clean_text_for_tts(text),
                "model_id": "eleven_multilingual_v2",
                "voice_settings": {
                    "stability": 0.5,
                    "similarity_boost": 0.75
                }
            }
            
            response = requests.post(url, json=data, headers=headers)
            
            if response.status_code == 200:
                filename = f"{user_id or 'temp'}_{uuid.uuid4().hex[:8]}.mp3"
                filepath = os.path.join(self.output_dir, filename)
                
                with open(filepath, 'wb') as f:
                    f.write(response.content)
                
                logger.info(f"Voz generada: {filepath}")
                return filepath
            else:
                logger.error(f"Error ElevenLabs: {response.status_code} - {response.text}")
                return None
        except Exception as e:
            logger.error(f"Error con ElevenLabs: {e}")
            return None
    
    def transcribe_audio(self, filepath: str) -> Optional[str]:
        """
        Transcribe un archivo de audio a texto usando OpenAI Whisper
        
        Args:
            filepath: Ruta al archivo de audio (.mp3, .ogg, .wav, etc.)
            
        Returns:
            Texto transcrito o None si falla
        """
        try:
            if not os.path.exists(filepath):
                logger.error(f"Archivo de audio no encontrado para transcripción: {filepath}")
                return None
            
            if self.stt_provider == "openai":
                return self._transcribe_openai_whisper(filepath)
            else:
                logger.warning(f"Proveedor de STT desconocido: {self.stt_provider}")
                return None
        except Exception as e:
            logger.error(f"Error al transcribir audio: {e}", exc_info=True)
            return None

    def _transcribe_openai_whisper(self, filepath: str) -> Optional[str]:
        """Transcribe audio usando OpenAI Whisper API"""
        try:
            from openai import OpenAI
            
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                logger.error("OPENAI_API_KEY no configurada para transcripción")
                return None
            
            client = OpenAI(api_key=api_key)
            
            with open(filepath, "rb") as audio_file:
                transcript = client.audio.transcriptions.create(
                    model="whisper-1", 
                    file=audio_file,
                    response_format="text"
                )
            
            logger.info(f"Audio transcrito correctamente: {transcript[:50]}...")
            return transcript
        except ImportError:
            logger.error("OpenAI no instalado. Ejecuta: pip install openai")
            return None
        except Exception as e:
            logger.error(f"Error con OpenAI Whisper: {e}")
            return None

    def _generate_openai_tts(self, text: str, user_id: Optional[str], lang: str) -> Optional[str]:
        """Genera voz usando OpenAI TTS (buena calidad, requiere API key)"""
        try:
            from openai import OpenAI
            import uuid
            
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                logger.error("OPENAI_API_KEY no configurada")
                return None
            
            client = OpenAI(api_key=api_key)
            
            # Voz femenina (alloy, echo, fable, onyx, nova, shimmer)
            voice = os.getenv("OPENAI_TTS_VOICE", "nova")  # Voz femenina por defecto
            
            response = client.audio.speech.create(
                model="tts-1",
                voice=voice,
                input=self._clean_text_for_tts(text)
            )
            
            filename = f"{user_id or 'temp'}_{uuid.uuid4().hex[:8]}.mp3"
            filepath = os.path.join(self.output_dir, filename)
            
            response.stream_to_file(filepath)
            
            logger.info(f"Voz generada: {filepath}")
            return filepath
        except ImportError:
            logger.error("OpenAI no instalado. Ejecuta: pip install openai")
            return None
        except Exception as e:
            logger.error(f"Error con OpenAI TTS: {e}")
            return None

    def _generate_qwen3(self, text: str, user_id: Optional[str], lang: str) -> Optional[str]:
        """Genera voz usando Qwen3-TTS via Gradio Client (Alta calidad, Baja latencia)"""
        try:
            from gradio_client import Client
            import uuid
            
            # Lista de Spaces candidatos para Qwen3 (Solo públicos verificados)
            spaces = [
                os.getenv("Qwen3_SPACE_URL", "Qwen/Qwen3-TTS-Demo"),
                "Qwen/Qwen3-TTS" # Mirror oficial secundario
            ]
            
            result = None
            last_error = ""
            hf_token = os.getenv("HF_API_TOKEN")
            
            for space_url in spaces:
                try:
                    logger.info(f"Probando Space de Qwen3: {space_url} (Auth: {'Sí' if hf_token else 'No'})...")
                    client = Client(space_url, token=hf_token)
            
                    # Map languages to Qwen3 format
                    lang_map = {
                        "es": "Spanish / 西班牙语",
                        "en": "English / 英文",
                        "pt": "Portuguese / 葡萄牙语",
                        "fr": "French / 法语"
                    }
                    qwen_lang = lang_map.get(lang, "Auto / 自动")
                    
                    from langdetect import detect
                    try:
                        detected_lang = detect(text)
                        if detected_lang == 'en':
                            qwen_lang = "English / 英文"
                        else:
                            qwen_lang = lang_map.get(lang, "Auto / 自动")
                    except:
                        qwen_lang = lang_map.get(lang, "Auto / 自动")
                    
                    # Voice design info if provided in env or user context
                    style = os.environ.get("Qwen3_TEMP_STYLE", "Default")
                    
                    # Mapping from UI styles to Qwen3 exact voice names (VERIFIED)
                    qwen_voices = {
                        "Default": "Sonrisa / 西班牙语拉美-索尼莎",
                        "Sonrisa": "Sonrisa / 西班牙语拉美-索尼莎",
                        "Bodega": "Bodega / 西班牙语-博德加",
                        "Mia": "Mia / 精品百人-乖小妹",
                        "Nini": "Nini / 精品百人-邻家妹妹",
                        "Stella": "Stella / 精品百人-美少女阿月",
                        "Seductora": "Mia / 精品百人-乖小妹", # Mapeamos seductora a Mia (Alta calidad)
                        "Alegre": "Sonrisa / 西班牙语拉美-索尼莎",
                        "EnglishBabe": "Jennifer / 詹妮弗"
                    }
                    
                    voice_name = qwen_voices.get(style, "Sonrisa / 西班牙语拉美-索尼莎")
                    
                    # For Spanish voices, force Spanish language
                    if "西班牙语" in voice_name:
                        qwen_lang = "Spanish / 西班牙语"
                    elif "Jennifer" in voice_name or qwen_lang == "English / 英文":
                        qwen_lang = "English / 英文"
                    else:
                        qwen_lang = "Auto / 自动"
                    
                    # El estilo se limpia después del bucle
                    
                    logger.info(f"Generando voz con Qwen3-TTS ({space_url}) usando estilo: {style} -> {voice_name}...")
                    
                    import time
                    max_retries = 2
                    for attempt in range(max_retries):
                        try:
                            # Llamada al API
                            result = client.predict(
                                text=self._clean_text_for_tts(text),
                                voice_display=voice_name,
                                language_display=qwen_lang,
                                api_name="/tts_interface"
                            )
                            if result: break
                        except Exception as e:
                            err_msg = str(e).lower()
                            if "queue is full" in err_msg:
                                logger.warning(f"Cola llena en {space_url}, saltando al siguiente space.")
                                break # Saltar al siguiente space en el bucle exterior
                            if attempt < max_retries - 1:
                                time.sleep(3)
                            else:
                                raise e
                    
                    if result:
                        logger.info(f"Éxito con el Space: {space_url}")
                        break # Salir del bucle de spaces
                        
                except Exception as e:
                    last_error = str(e)
                    logger.warning(f"Fallo en Space {space_url}: {e}")
                    continue # Probar el siguiente space
            
            # Limpiar para la próxima vez tras intentar todos los spaces
            os.environ.pop("Qwen3_TEMP_STYLE", None)
            
            if not result:
                logger.warning(f"Todos los intentos con Qwen3 fallaron. Iniciando EMERGENCIA con Edge-TTS (Salomé)...")
                # Fallback de emergencia a Salomé para no dejar al bot mudo
                edge_voice = os.getenv("VOICE_EDGE_CODE", "es-CO-SalomeNeural")
                return self._generate_gtts(text, user_id, edge_voice)
            
            # El resultado es una tupla o string con la ruta del archivo temporal
            if isinstance(result, (list, tuple)):
                audio_path = result[0]
            else:
                audio_path = result
                
            if audio_path and os.path.exists(audio_path):
                filename = f"qwen_{user_id or 'temp'}_{uuid.uuid4().hex[:8]}.mp3"
                dest_path = os.path.join(self.output_dir, filename)
                
                # Mover el archivo generado a nuestra carpeta de salida
                import shutil
                shutil.copy(audio_path, dest_path)
                
                logger.info(f"Voz Qwen3 generada: {dest_path}")
                return dest_path
            
            return None
        except Exception as e:
            logger.error(f"Error crítico con Qwen3-TTS: {e}")
            return None

    def _generate_f5_clon(self, text: str, user_id: Optional[str], lang: str) -> Optional[str]:
        """Genera voz usando F5-TTS (Zero-Shot Cloning) via Gradio Client"""
        try:
            from gradio_client import Client
            import uuid
            import shutil
            
            # Provider de F5-TTS (Zero-Shot)
            space_url = os.getenv("F5_TTS_SPACE_URL", "mrfakename/F5-TTS")
            hf_token = os.getenv("HF_API_TOKEN")
            
            # Configuración del clon
            # Por ahora solo tenemos "Clon Paisa", pero se puede extender
            ref_audio = "voices/clon_paisa.mp3"
            ref_text = "Mor venga pa acá! Venga yo le digo una cosa"
            
            if not os.path.exists(ref_audio):
                logger.warning(f"Audio de referencia no encontrado: {ref_audio}. Usando Qwen Default.")
                return self._generate_qwen3(text, user_id, lang)
            
            logger.info(f"Generando CLON de voz con F5-TTS ({space_url})...")
            
            client = Client(space_url, token=hf_token)
            
            # predict(ref_audio, ref_text, gen_text, remove_silence, api_name="/predict")
            result = client.predict(
                ref_audio=os.path.abspath(ref_audio),
                ref_text=ref_text,
                gen_text=self._clean_text_for_tts(text),
                remove_silence=True,
                api_name="/predict"
            )
            
            if result and os.path.exists(result):
                filename = f"f5_clon_{user_id or 'temp'}_{uuid.uuid4().hex[:8]}.mp3"
                dest_path = os.path.join(self.output_dir, filename)
                shutil.copy(result, dest_path)
                logger.info(f"Voz Clonada F5 generada: {dest_path}")
                return dest_path
            
            return self._generate_qwen3(text, user_id, lang) # Fallback
        except Exception as e:
            logger.error(f"Error en F5-TTS Cloning: {e}")
            return self._generate_qwen3(text, user_id, lang) # Fallback
    
    def _clean_text_for_tts(self, text: str) -> str:
        """Limpia el texto para mejor pronunciación en TTS, eliminando emojis"""
        import re
        
        # Reemplazos específicos para lectura natural
        text = text.replace("/", " ") # mejor espacio que "barra"
        text = text.replace("\\", " ")
        text = text.replace("_", " ")
        text = text.replace("-", " ")
        text = text.replace("*", "") # eliminar asteriscos
        text = text.replace("#", "") # eliminar hash
        text = text.replace("http", "") # evitar leer links
        text = text.replace("www", "") # evitar leer links
        text = text.replace("{", "")
        text = text.replace("}", "")
        text = text.replace("[", "")
        text = text.replace("]", "")

        
        # Remover todos los emojis de forma robusta
        # Este regex cubre la mayoría de los rangos de emojis comunes
        emoji_pattern = re.compile(
            "["
            "\U0001f600-\U0001f64f"  # emoticons
            "\U0001f300-\U0001f5ff"  # symbols & pictographs
            "\U0001f680-\U0001f6ff"  # transport & map symbols
            "\U0001f1e6-\U0001f1ff"  # flags (iOS)
            "\U00002702-\U000027b0"
            "\U000024c2-\U0001f251"
            "]+", flags=re.UNICODE
        )
        
        clean_text = emoji_pattern.sub('', text)
        
        # Limpiar espacios múltiples y caracteres extraños
        clean_text = re.sub(r'\s+', ' ', clean_text).strip()
        
        return clean_text
