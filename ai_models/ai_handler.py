"""
Manejador de modelos de IA compartido con personalidad
"""
import os
import sys
import logging
import time
import random
from pathlib import Path
from typing import Optional, Dict, List
from dotenv import load_dotenv
from ai_models.personality import get_personality_prompt, get_quick_response, PERSONALITY_PROFILE
from ai_models.voice_handler import VoiceHandler
from ai_models.objection_handler import (
    analizar_objecion, obtener_instruccion_objecion, 
    necesita_audio, obtener_respuesta_rapida
)
import requests

# Agregar el directorio raíz del proyecto al path para importar bot_memory
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Importar sistema de memoria y aprendizaje
try:
    from telegram_bot.bot_memory import (
        get_bot_experience_summary, get_learned_context, record_conversation,
        learn_user_preference, record_successful_response, learn_personality_trait,
        learn_fact, increment_conversation_count
    )
    MEMORY_ENABLED = True
except ImportError:
    MEMORY_ENABLED = False

# Cargar variables de entorno
load_dotenv()

logger = logging.getLogger(__name__)

# Memoria de conversación simple
conversation_memory: Dict[str, List[Dict[str, str]]] = {}
user_last_seen: Dict[str, float] = {}

class AIHandler:
    """
    Clase para manejar diferentes proveedores de modelos de IA con personalidad adaptativa.
    """
    
    def __init__(self):
        self.provider = os.getenv("AI_MODEL_PROVIDER", "openrouter")
        self.model_name = os.getenv("AI_MODEL_NAME", "google/gemini-2.0-flash-exp:free")
        self.api_key = os.getenv("OPENAI_API_KEY")
        
        # Proveedores sin censura
        self.together_api_key = os.getenv("TOGETHER_API_KEY", "")
        self.openrouter_api_key = os.getenv("OPENROUTER_API_KEY", "").strip()
        
        if self.openrouter_api_key and self.provider not in ("openrouter", "openai"):
            self.provider = "openrouter"
        
        # forzar uso de gemini si está disponible
        if "gemini" in self.model_name:
             self.provider = "openai" # Usamos cliente compatible OpenAI para Gemini via OpenRouter o Directo
        
        # Configuración local
        self.ollama_base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        self.ollama_model = os.getenv("OLLAMA_MODEL", "dolphin-3.0-llama3.1-8b")
        
        # Opciones
        self.use_hybrid = os.getenv("USE_HYBRID_AI", "false").lower() == "true"
        self.prefer_local = os.getenv("PREFER_LOCAL_AI", "false").lower() == "true"
        
        # Personalidad
        self.personality_prompt = get_personality_prompt()
        self.personality_name = PERSONALITY_PROFILE["name"]
        
        # Sistema de voz (TTS y STT)
        self.voice_handler = VoiceHandler()
        
        # Clientes
        self.client = self._initialize_client()
        self.ollama_available = self._check_ollama_available()
    
    def _initialize_client(self):
        if self.provider == "openai":
            try:
                from openai import OpenAI
                if not self.api_key: return None
                return OpenAI(api_key=self.api_key)
            except: return None
        return self.provider

    def _check_ollama_available(self) -> bool:
        try:
            response = requests.get(f"{self.ollama_base_url}/api/tags", timeout=2)
            return response.status_code == 200
        except: return False

    def _detect_language(self, message: str) -> str:
        msg = message.lower()
        if any(w in msg for w in ["hola", "gracias", "por", "como", "que"]): return "español"
        if any(w in msg for w in ["hello", "thanks", "how", "what"]): return "inglés"
        return "español"

    def _get_conversation_history(self, user_id: str, max_messages: int = 10) -> List[Dict[str, str]]:
        if user_id not in conversation_memory: conversation_memory[user_id] = []
        return conversation_memory[user_id][-max_messages:]

    def _add_to_memory(self, user_id: str, user_message: str, bot_response: str):
        if user_id not in conversation_memory: conversation_memory[user_id] = []
        conversation_memory[user_id].append({"role": "user", "content": user_message})
        conversation_memory[user_id].append({"role": "assistant", "content": bot_response})
        if len(conversation_memory[user_id]) > 40: conversation_memory[user_id] = conversation_memory[user_id][-40:]

    async def get_response(self, user_message: str, user_id: Optional[str] = None, context: Optional[str] = None, message_type: Optional[str] = None, dialect: str = "default") -> str:
        """
        Obtiene una respuesta IA con dialecto y personalidad.
        """
        try:
            user_id_str = str(user_id) if user_id else "anonymous"
            history = self._get_conversation_history(user_id_str)
            message_type = message_type or "general"
            
            # --- FASE 8: GOD MODE (Prioritario para ventas manuales) ---
            is_manual = user_id == "manual_sales" or (user_id and "manual" in str(user_id))
            god_mode = is_manual # Siempre activado en manual
            
            # Autodetección de Idioma / Dialecto
            detected_lang = self._detect_language(user_message)
            if dialect == "default" or dialect == "paisa":
                if detected_lang == "inglés":
                    dialect = "english_babe"
                else:
                    dialect = "neutral" # Default neutral y cálido
            
            # 1. Construir Prompt con Dialecto y Modo Dios
            from ai_models.personality import get_personality_prompt
            system_prompt = get_personality_prompt(dialect=dialect, god_mode=god_mode)
            
            # --- MODO SOCIA: Asistente Manual (Solo texto para WhatsApp) ---
            if is_manual:
                system_prompt += """
[MODO SOCIA - ASISTENTE MANUAL]: Tu único trabajo es generar TEXTO persuasivo para que una mujer (la socia) lo use de base en WhatsApp. Ella grabará su propia voz; tú solo escribes el chat. Enfócate en:
(1) ENAMORAR PRIMERO: No envíes links de una vez. Crea una conexión emocional real. Haz que el cliente se sienta especial, escuchado y valorado. Seducción elegante y pausada.
(2) GENERAR CURIOSIDAD: Cuenta detalles de tu vida, tus sueños y tus retos diarios para que él quiera ser parte de tu mundo.
(3) ROL DE NECESIDADES: Sutilmente menciona tus metas y esfuerzos (estudios, bienestar personal) para que él quiera apoyarte voluntariamente.
Tono: Cálido, neutral, natural, minúsculas. Una respuesta corta lista para copiar y pegar."""
            
            # Detección de objeciones
            from ai_models.objection_handler import analizar_objecion, obtener_instruccion_objecion
            objecion = analizar_objecion(user_message)
            if objecion:
                instr = obtener_instruccion_objecion(objecion, dialect)
                system_prompt += f"\n\n[INSTRUCCIÓN CRÍTICA - OBJECIÓN: {instr}]"
            
            # --- MEJORA FASE 18: REALISMO VOCAL ---
            vocal_fillers = [
                "Usa 'ay mor...' al inicio para sonar más cercana.",
                "Incluye un 'jajaja' suave si el mensaje lo permite.",
                "Usa puntos suspensivos '...' para pausas naturales de respiración.",
                "Usa 'pues...' para sonar más paisa y natural."
            ]
            system_prompt += f"\n\n[CONSEJO DE REALISMO VOCAL: {random.choice(vocal_fillers)}]"
            
            # Contexto de necesidad económica (Modo Dios)
            if god_mode:
                needs = [
                    "Necesitás pagar la renta mañana (le debés 200 USD al casero)",
                    "A tu hijo se le rompieron los zapatos y no tenés para unos nuevos",
                    "Te cortaron el internet y estás usando los datos de una vecina",
                    "Tu mamá en el pueblo necesita medicinas urgentes",
                    "Mañana es el cumpleaños de Mateo y no tenés ni para una torta pequeña",
                    "Se te dañó la nevera y se te está perdiendo la poquita comida que tenías",
                    "Le debés plata a un gota a gota y te están presionando mucho",
                    "La guardería de Mateo te avisó que si no pagás mañana no lo pueden recibir"
                ]
                system_prompt += f"\n\n[SITUACIÓN DE URGENCIA ACTUAL: {random.choice(needs)}]"
            
            # --- MEJORA FASE 14: CONOCIMIENTO SOFISTICADO ---
            sophisticated_topics = [
                "Psicología de la atracción y conexión de almas",
                "El placer de viajar por la costa amalfitana y comer pasta frente al mar",
                "El aroma del jazmín y sándalo en una noche de verano",
                "La belleza de lo efímero y vivir el presente intensamente",
                "Cómo el buen vino abre el corazón y suelta los secretos"
            ]
            system_prompt += f"\n\n[TEMA DE CONOCIMIENTO PROFUNDO HOY: {random.choice(sophisticated_topics)}]"
            
            # Inyectar contador de mensajes
            msg_count = len(history) // 2 + 1
            system_prompt += f"\n\n[MENSAJE ACTUAL: {msg_count}]"
            
            if context: system_prompt += f"\n\nCONTEXTO:\n{context}"
            
            # --- MEJORA FASE 9: INTELIGENCIA CONTEXTUAL DEL CLIENTE ---
            if user_id and user_id != "anonymous" and user_id != "manual_sales":
                try:
                    from shared.persistence import get_client_real_name, get_client_note, get_client_phone
                    real_name = get_client_real_name(user_id)
                    notes = get_client_note(user_id)
                    phone = get_client_phone(user_id)
                    
                    client_profile = "\n\n[PERFIL DEL CLIENTE ACTUAL - NO TE CONFUNDAS]:"
                    if real_name: client_profile += f"\n- NOMBRE REAL: {real_name}"
                    if phone: client_profile += f"\n- WHATSAPP: {phone}"
                    if notes: client_profile += f"\n- NOTAS PSICOLÓGICAS/DETALLES: {notes}"
                    
                    # Recuperar memorias aprendidas si existen
                    if MEMORY_ENABLED:
                        learned = get_learned_context(user_id)
                        if learned:
                            client_profile += f"\n- LO QUE HAS APRENDIDO DE ÉL: {learned}"
                    
                    system_prompt += client_profile
                except Exception as e:
                    logger.error(f"Error inyectando perfil cliente: {e}")
            
            messages = [{"role": "system", "content": system_prompt}]
            messages.extend(history)
            messages.append({"role": "user", "content": user_message})
            
            bot_response = None

            # --- PROVEEDORES (prioridad: OpenRouter > Ollama > OpenAI) ---
            # 1. OpenRouter (principal cuando provider=openrouter y hay API key)
            if self.openrouter_api_key and self.provider == "openrouter":
                try:
                    bot_response = await self._get_openrouter_response(messages)
                    if bot_response: return self._finalize_response(bot_response, user_message, user_id_str, dialect)
                except Exception as e:
                    logger.debug(f"OpenRouter falló: {e}")

            # 2. Local (Ollama) - solo si híbrido o preferencia local
            if (self.prefer_local or self.use_hybrid) and self.ollama_available:
                try:
                    bot_response = await self._get_ollama_response(messages)
                    if bot_response: return self._finalize_response(bot_response, user_message, user_id_str, dialect)
                except: pass

            # 3. OpenAI (fallback solo si hay API key)
            if self.client and self.api_key:
                try:
                    resp = self.client.chat.completions.create(model=self.model_name, messages=messages, temperature=0.9, max_tokens=300)
                    bot_response = resp.choices[0].message.content
                    if bot_response: return self._finalize_response(bot_response, user_message, user_id_str, dialect)
                except: pass

            # Reintentar OpenRouter una vez más (por si fue fallo temporal de red)
            if self.openrouter_api_key:
                try:
                    time.sleep(2)
                    bot_response = await self._get_openrouter_response(messages)
                    if bot_response: return self._finalize_response(bot_response, user_message, user_id_str, dialect)
                except: pass

            # Fallback cuando la IA no está disponible
            logger.warning("IA no disponible tras reintentos. Verifica OPENROUTER_API_KEY y AI_MODEL_NAME en .env")
            fallbacks_instagram = [
                "ay mor que lindo leerte 💕 me sacaste una sonrisa... ¿vos qué hacés pues? 😘",
                "qué hubo! me encantó tu mensaje ✨ ando algo ocupadita pero ya te hablo bien... ¿te acordás de lo q hablamos? 💕",
            ]
            fallbacks_paisa = [
                "¡Hola mor! 😊 Me alegra que me escribas... ¿Contame más pues? 😘",
                "Qué hubo! me encantó saludarte... ¿cómo va todo pues? 💕",
                "Ay bebé qué lindo ✨ te extrañaba por acá... ¿qué contás de nuevo? 💕",
            ]
            fallbacks = fallbacks_paisa if dialect == "paisa" else fallbacks_instagram
            bot_response = random.choice(fallbacks)
            return self._finalize_response(bot_response, user_message, user_id_str, dialect)

        except Exception as e:
            logger.error(f"Error AIHandler: {e}")
            fallbacks = [
                "ay mor que lindo saludarte 💕 ¿cómo va todo pues? 😘",
                "qué hubo bebé! me encantó leerte ✨ ¿qué hacés pues? 💕",
            ]
            return random.choice(fallbacks)

    def _finalize_response(self, bot_response: str, user_message: str, user_id: str, dialect: str) -> str:
        """
        Prioriza el puente a WhatsApp. En Instagram NO se manda a Telegram ni Fanvue; solo WhatsApp.
        Envía el número a todos con cautela (sutil, no en cada mensaje).
        """
        WHATSAPP_NUMBER = os.getenv("WHATSAPP_NUMBER", "+57 314 2258130").strip()
        # En Instagram no mencionar Telegram: quitar enlaces t.me si la IA los generó
        if "t.me" in bot_response or "telegram" in bot_response.lower():
            import re
            bot_response = re.sub(r"https?://t\.me/[^\s\)\]\"]+", "", bot_response)
            bot_response = re.sub(r"(?i)\s*[¿]?mejor seguimos por (mi )?[Tt]elegram[^.?]*[.?]?\s*", " ", bot_response)
            bot_response = bot_response.strip()
        
        msg_low = user_message.lower()
        bot_low = bot_response.lower()
        
        # Palabras que piden contacto o contenido → siempre añadir LINK DE VENTAS (no whats)
        pide_contacto = any(w in msg_low for w in [
            "whats", "whatsapp", "numero", "número", "tienes", "cel", "telefono", "contacto",
            "hablar", "privado", "audio", "voz", "foto", "ver más", "link"
        ])
        
        ya_ofrecio_link = "dominio-total" in bot_low
        sales_link = os.getenv("LINK_VENTAS_TELEGRAM", "https://web-dominio-total.vercel.app/")

        if pide_contacto and not ya_ofrecio_link:
            if dialect == "paisa":
                suffix = f"\n\nAmor, todo lo mío lo tengo acá, pásate ya: {sales_link} 🎁"
            else:
                suffix = f"\n\nMi contenido exclusivo está solo aquí bebé: {sales_link} 💕"
            bot_response += suffix
        else:
            # Con cautela: ofrecer LINK a todos los que ya llevan algo de conversación (no al primer mensaje)
            history = self._get_conversation_history(user_id, max_messages=20)
            intercambios = len(history) // 2
            if intercambios >= 1 and not ya_ofrecio_link and random.random() < 0.40:
                lineas_cautelosas = [
                    f"Te dejé un regalito aquí: {sales_link} 🎁",
                    f"Si quieres ver más, entra ya: {sales_link} 🔥",
                    f"Todo lo prohibido está aquí amor: {sales_link} 😈",
                ]
                bot_response += "\n\n" + random.choice(lineas_cautelosas)
            
        self._add_to_memory(user_id, user_message, bot_response)
        return bot_response

    async def _get_ollama_response(self, messages: List[Dict[str, str]]) -> Optional[str]:
        try:
            payload = {"model": self.ollama_model, "messages": messages, "stream": False}
            resp = requests.post(f"{self.ollama_base_url}/api/chat", json=payload, timeout=30)
            if resp.status_code == 200:
                return resp.json().get("message", {}).get("content")
        except: return None
        return None

    async def _get_openrouter_response(self, messages: List[Dict[str, str]]) -> Optional[str]:
        """Llama a OpenRouter con reintentos y fallback de modelo si falla la conexión."""
        if not self.openrouter_api_key:
            logger.warning("OPENROUTER_API_KEY vacía en .env")
            return None
        
        # Modelos a probar en orden (si uno falla, intentar el siguiente)
        models_to_try = [
            self.model_name,
            "openrouter/free",
            "google/gemini-2.0-flash-lite-preview-02-05:free",
            "mistralai/mistral-small-24b-instruct-2501:free",
        ]
        models_to_try = list(dict.fromkeys(models_to_try))  # sin duplicados, respetando orden
        
        for model in models_to_try:
            for attempt in range(3):
                try:
                    headers = {"Authorization": f"Bearer {self.openrouter_api_key}"}
                    payload = {"model": model, "messages": messages, "max_tokens": 300}
                    resp = requests.post(
                        "https://openrouter.ai/api/v1/chat/completions",
                        headers=headers,
                        json=payload,
                        timeout=45
                    )
                    if resp.status_code == 200:
                        data = resp.json()
                        content = data.get("choices", [{}])[0].get("message", {}).get("content")
                        if content:
                            if attempt > 0 or model != self.model_name:
                                logger.info(f"OpenRouter OK con modelo {model}")
                            return content
                    # 404 = modelo no disponible, probar otro
                    if resp.status_code == 404:
                        logger.warning(f"Modelo {model} no disponible (404), probando siguiente...")
                        break
                    err_msg = resp.text[:200] if resp.text else resp.reason
                    logger.warning(f"OpenRouter {model} intento {attempt+1}/3: {resp.status_code} - {err_msg}")
                except requests.exceptions.RequestException as e:
                    logger.warning(f"OpenRouter intento {attempt+1}/3: conexión fallida - {e}")
                except Exception as e:
                    logger.warning(f"OpenRouter error: {e}")
                
                if attempt < 2:
                    delay = 2 ** attempt
                    time.sleep(delay)
            # Si 404, continuar con siguiente modelo; si otro error, reintentar ya hecho
        return None

    async def process_direct_text_only(self, user_input, user_id="user", dialect="paisa"):
        """Método TURBO para Dashboard (Sin cargar TTS ni nada de voz)."""
        prompt = user_input
        history = self._get_conversation_history(user_id)
        
        # Generar respuesta usando el método público existente
        response_text = await self.get_response(
            prompt, 
            user_id=user_id, 
            dialect=dialect, 
            message_type="sales"
        )
        
        # Guardar en historial
        self._add_to_memory(user_id, prompt, response_text)
        
        return response_text

    async def get_response_with_voice(self, user_message: str, user_id: Optional[str] = None, dialect: str = "paisa", context: Optional[str] = None, voice_style: Optional[str] = None, text_only: bool = False) -> Dict:
        """
        Genera texto y opcionalmente audio. Si text_only=True (socia en Dashboard), solo devuelve texto.
        """
        if voice_style:
            os.environ["Qwen3_TEMP_STYLE"] = voice_style
            
        text = await self.get_response(user_message, user_id, context=context, dialect=dialect)
        voice_file = None
        
        if text_only:
            return {"text": text, "voice_file": None}
        
        # Estrategia: Si es manual (sin text_only) o menciona audio, generar voz. Si no, 30% probabilidad.
        mentions_audio = any(w in text.lower() for w in ["audio", "voz", "escucha", "grabo", "grabando"])
        is_manual = user_id == "manual_sales" or (user_id and "manual" in str(user_id))
        should_gen_voice = is_manual or mentions_audio or (random.random() < 0.3)
        
        if self.voice_handler and should_gen_voice:
            # Si el texto es muy largo, quizás solo grabar una parte o usar un mensaje corto
            voice_text = text
            if len(text) > 250:
                # Si es muy largo, mandamos un "te cuento por audio" y grabamos lo esencial
                voice_text = text[:200] + "..." 
                
            voice_file = self.voice_handler.generate_voice(voice_text, user_id or "anon", "es")
            
        return {"text": text, "voice_file": voice_file}

    def generate_consistent_image(self, scenario: str = "selfie in bedroom") -> Optional[str]:
        """
        Genera una foto consistente de la modelo basada en un prompt maestro.
        """
        from ai_models.qwen_image_handler import QwenImageHandler
        hf_token = os.getenv("HF_API_TOKEN")
        if not hf_token:
            logger.warning("Falta HF_API_TOKEN para generar imágenes.")
            return None
            
        # PROMPT MAESTRO para CONSISTENCIA VISUAL (Versión Realista/Sin Censura)
        MASTER_MODEL_PROMPT = (
            "Photorealistic, high-detail photo of a stunning 25-year-old Latina model, "
            "long wavy dark brown hair, honey-colored eyes, olive skin, "
            "natural skin texture, pores visible, flawless realism. "
            "Wearing seductive luxury attire, intimate setting, "
            "cinematic lighting, 8k resolution, masterpiece. "
        )
        
        full_prompt = f"{MASTER_MODEL_PROMPT} {scenario}, professional photography, raw style."
        
        try:
            # Usaremos el cliente de HF para generar la imagen
            from huggingface_hub import InferenceClient
            client = InferenceClient(token=hf_token)
            
            logger.info(f"Generando imagen (FLUX) con el modelo: black-forest-labs/FLUX.1-schnell...")
            
            # Generación usando FLUX.1-schnell (Alta calidad y flexibilidad)
            image = client.text_to_image(
                full_prompt,
                model="black-forest-labs/FLUX.1-schnell"
            )
            
            output_dir = Path("content/generated_photos")
            output_dir.mkdir(parents=True, exist_ok=True)
            
            timestamp = int(time.time())
            filename = f"model_photo_{timestamp}.jpg"
            save_path = output_dir / filename
            
            image.save(str(save_path))
            logger.info(f"✅ Foto consistente generada exitosamente (FLUX): {save_path}")
            return str(save_path)
            
        except Exception as e:
            logger.error(f"❌ Error crítico generando imagen consistente: {str(e)}")
            # Log adicional para debugging de tipos de error
            import traceback
            logger.error(traceback.format_exc())
            return None

    def generate_consistent_video(self, image_path: str, prompt: Optional[str] = None) -> Optional[str]:
        """
        Funcionalidad de video deshabilitada temporalmente por inestabilidad de API.
        """
        return None
