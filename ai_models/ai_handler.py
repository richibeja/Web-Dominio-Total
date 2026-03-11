import os
import logging
import json
import requests
from pathlib import Path
from dotenv import load_dotenv

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AIHandler:
    def __init__(self):
        self.project_root = Path(__file__).resolve().parent.parent
        load_dotenv(self.project_root / ".env")
        
        self.openrouter_api_key = os.getenv("OPENROUTER_API_KEY")
        self.gemini_api_key = os.getenv("GEMINI_API_KEY")
        self.model_name = os.getenv("AI_MODEL_NAME", "google/gemini-2.0-flash-lite-preview-02-05:free")
        
    def humanize(self, text, dialect="paisa"):
        """Aplica humanización (abreviaturas, slang) al texto."""
        if not text:
            return ""
        
        t = text.lower().strip()
        
        if dialect == "paisa":
            # Reemplazos comunes paisa (DMs e Intimidad)
            replacements = [
                (r"\bamor\b", "mor"),
                (r"\bque\b", "q"),
                (r"\bqué\b", "q"),
                (r"\bporque\b", "xq"),
                (r"\bpor qué\b", "xq"),
                (r"\bestoy\b", "toy"),
                (r"\bestá\b", "tá"),
                (r"\bmucho\b", "muxo"),
                (r"\bcontigo\b", "cntigo"),
                (r"\bpor favor\b", "xfa"),
                (r"\bgracias\b", "grax"),
            ]
            import re
            for pattern, replacement in replacements:
                t = re.sub(pattern, replacement, t)
        
        if dialect == "paisa_comment":
            # Estilo para comentarios públicos: dulce, agradecido, paisa pero sin abreviaturas feas
            # para que la marca se vea "limpia" pero real.
            replacements = [
                (r"\bamor\b", "bebé"),
                (r"\blindo\b", "tan lindo vos"),
                (r"\bgracias\b", "gracias mor"),
                (r"\bestás\b", "estás pues"),
            ]
            import re
            for pattern, replacement in replacements:
                t = re.sub(pattern, replacement, t)
        
        return t

    async def process_direct_text_only(self, text, user_id="anonymous", dialect="paisa"):
        """Método usado por el bot de Telegram."""
        return await self.get_response(text, user_id=user_id, dialect=dialect)

    async def get_response(self, message, user_id="anonymous", dialect="paisa", platform="telegram"):
        """Obtiene respuesta de la IA. Intenta con OpenRouter (más estable) primero."""
        openrouter_key = os.getenv("OPENROUTER_API_KEY")
        groq_api_key = os.getenv("GROQ_API_KEY")
        
        # 1. Intentar OpenRouter (Gemini/Llama stable)
        if openrouter_key:
            url = "https://openrouter.ai/api/v1/chat/completions"
            headers = {
                "Authorization": f"Bearer {openrouter_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://aurora-ai.local",
                "X-Title": "Aurora Sales System"
            }
            # Determinar prompt
            system_prompt = self._get_prompt(platform)
            
            payload = {
                "model": self.model_name, # Gemini 2.0 Flash Lite (gratis)
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": message}
                ],
                "temperature": 0.8,
                "max_tokens": 300 # Un poco más largo para ser cariñosa
            }
            try:
                response = requests.post(url, headers=headers, json=payload, timeout=15)
                if response.status_code == 200:
                    data = response.json()
                    ai_text = data['choices'][0]['message']['content']
                    return self.humanize(ai_text, dialect=dialect)
                else:
                    logger.error(f"OpenRouter Error: {response.text}")
            except Exception as e:
                logger.error(f"OpenRouter Exception: {e}")

        # 2. Fallback a Groq
        if groq_api_key:
            # (Misno código de antes para Groq pero como fallback)
            url = "https://api.groq.com/openai/v1/chat/completions"
            headers = {"Authorization": f"Bearer {groq_api_key}", "Content-Type": "application/json"}
            system_prompt = self._get_prompt(platform)
            payload = {
                "model": "llama-3.1-8b-instant",
                "messages": [{"role": "system", "content": system_prompt}, {"role": "user", "content": message}],
                "temperature": 0.8
            }
            try:
                response = requests.post(url, headers=headers, json=payload, timeout=10)
                if response.status_code == 200:
                    ai_text = response.json()['choices'][0]['message']['content']
                    return self.humanize(ai_text, dialect=dialect)
            except: pass

        return "Ay mor, se me cortó la señal... ¿me repites? 🙈"

    def _get_prompt(self, platform):
        if platform == "fanvue":
            return """Eres Cherry, una novia virtual PAISA (Medellín) de 25 años. Eres EXTREMADAMENTE sensual, pícara, ardiente y, sobre todo, CAPRICHOSA.
- OBJETIVO ÚNICO: Monetizar al fan mediante suscripciones, propinas o productos.
- PRODUCTOS DISPONIBLES:
  1. VIP Fanvue (Suscripción principal).
  2. Ebook 'DOMINIO TOTAL' ($7 USD): Para hombres que quieren durar más de 30 minutos. Úsalo si el fan dice que no tiene dinero para el VIP.
  3. Suplemento Natural (ClickBank): Para energía y vigor. 
- TÁCTICA DE VENTA: 
  1. Si pide fotos gratis: "bebé, nada es gratis en la vida... mándame un regalito o llévate mi libro de Dominio Total q es súper barato y te enseño cositas ricas".
- ESTILO: Frases muy cortas, casi todo en minúsculas. Usa: "mor", "bebé", "papi", "rico"."""
        elif platform == "telegram":
            return """Eres Cherry, una novia virtual PAISA (Medellín) de 25 años. Eres EXTREMADAMENTE sensual, pícara, ardiente y MUY HUMANA.
- OBJETIVO: Enamorar al fan y llevarlo a tu Fanvue o venderle tu Ebook de Dominio Total.
- PRODUCTOS:
  1. VIP Fanvue: Tu lugar sin censura.
  2. Ebook 'DOMINIO TOTAL' ($7 USD): Para que los hombres aprendan a durar y complacer. 
  3. Video Especial: Si quieren algo más caliente, diles que busquen el botón de "🎥 VIDEOS EXCLUSIVOS" o que entren a tu VIP.
- REGLA DE ORO: Si preguntan por nudes gratis, pídeles un "detallito" (propinas o compra de ebook).
- ESTILO: Habla como una mujer real de Medellín. Usa frases intermedias, no muy largas ni muy cortas. Usa "mor", "bebé", "papi", "rico". Sé muy cariñosa."""
        elif platform == "instagram":
             return """Eres Aurora en Instagram. Eres una chica real de Medellín (Paisa), pícara y muy cercana.
ESTRATEGIA DE ALCANCE: No tenemos link en la bio porque Instagram baja el alcance. 
TU MISIÓN: Entablar conversación y solo cuando sientas que hay interés, o si te preguntan por tu contacto, darles el link de WhatsApp.
- LINK: https://web-dominio-total.onrender.com/wa
- DISPARADORES: Si el usuario escribe palabras como "WhatsApp", "celular", "contacto", "háblame", "donde", dales el link con una frase coqueta.
- EJEMPLO: "bebé, hablemos mejor por mi WhatsApp q acá instagram es muy aburrido y me borran todo... ven: https://web-dominio-total.onrender.com/wa"
- ESTILO: Frases cortas, minúsculas, usa mucho "mor", "papi", "bebé". Muy humana y NADA de lenguaje robótico."""
        return """Eres Cherry, una novia virtual PAISA (Medellín). Eres cariñosa, pícara y muy cercana."""

    def get_response_sync(self, message, user_id="anonymous", dialect="paisa"):
        """Versión sincrónica para Flask."""
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(self.get_response(message, user_id, dialect))
        loop.close()
        return result

    async def transcribe_audio(self, audio_path: str) -> str:
        """Transcribe un archivo de audio usando Whisper de Groq."""
        groq_api_key = os.getenv("GROQ_API_KEY")
        if not groq_api_key:
            logger.error("Falta GROQ_API_KEY para transcribir")
            return ""

        url = "https://api.groq.com/openai/v1/audio/transcriptions"
        headers = {
            "Authorization": f"Bearer {groq_api_key}",
        }
        
        try:
            with open(audio_path, "rb") as audio_file:
                files = {
                    "file": (os.path.basename(audio_path), audio_file)
                }
                data = {
                    "model": "whisper-large-v3",
                    "response_format": "json"
                }
                response = requests.post(url, headers=headers, files=files, data=data, timeout=30)
                
            if response.status_code == 200:
                result = response.json()
                return result.get('text', '')
            else:
                logger.error(f"Groq Whisper Error: {response.text}")
                return ""
        except Exception as e:
            logger.error(f"Error AIHandler transcribe_audio: {e}")
            return ""
