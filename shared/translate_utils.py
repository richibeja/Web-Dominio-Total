"""
Internacionalización: detección de idioma y traducción natural.

- Detección cuando el mensaje NO está en español.
- Traducción al español para el trabajador (Operaciones).
- Traducción de la respuesta del trabajador al idioma del cliente.

Usa langdetect + deep-translator (sin API key) con fallback opcional a OpenAI
para que las traducciones suenen naturales y seductoras.
"""
import os
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# Códigos de idioma soportados para traducción
SUPPORTED_TARGETS = {"en", "es", "pt", "fr", "de", "it", "ru", "ja", "ko", "ar", "hi", "zh-CN", "tr"}


def detect_language(text: str) -> Optional[str]:
    """
    Detecta el idioma del texto. Devuelve código ISO (ej. 'en', 'es', 'pt').
    Si no se puede detectar o el texto es muy corto, devuelve None (se asume español).
    """
    if not text or not text.strip() or len(text.strip()) < 2:
        return None
    try:
        from langdetect import detect, LangDetectException
        lang = detect(text.strip())
        return lang if lang else None
    except Exception as e:
        logger.debug(f"Langdetect falló: {e}")
        return None


def _normalize_lang_for_translator(lang: str) -> str:
    """Mapea códigos a los que deep-translator acepta."""
    m = {"zh-cn": "zh-CN", "zh": "zh-CN", "pt-br": "pt", "pt-BR": "pt"}
    return m.get(lang.lower(), lang)


def translate_to_spanish(text: str) -> Optional[str]:
    """
    Traduce el texto al español. Para mostrar al trabajador en Operaciones.
    Si falla, devuelve None (se usa el texto original).
    """
    if not text or not text.strip():
        return None
    try:
        from deep_translator import GoogleTranslator
        t = GoogleTranslator(source="auto", target="es")
        out = t.translate(text.strip())
        return out if out else None
    except Exception as e:
        logger.warning(f"Traducción a español falló: {e}")
        return None


def translate_to(text: str, target_lang: str, source_lang: str = "es") -> Optional[str]:
    """
    Traduce el texto al idioma del cliente (ej. de español a inglés).
    Para enviar la respuesta del trabajador en el idioma del cliente.
    """
    if not text or not target_lang or target_lang.lower() == "es":
        return text
    target = _normalize_lang_for_translator(target_lang)
    try:
        from deep_translator import GoogleTranslator
        t = GoogleTranslator(source=source_lang, target=target)
        out = t.translate(text.strip())
        return out if out else text
    except Exception as e:
        logger.warning(f"Traducción a {target_lang} falló: {e}")
        return text


def translate_with_openai(text: str, target_lang: str, source_lang: str = "es") -> Optional[str]:
    """
    Traducción con OpenAI para tono más natural y seductor (fallback opcional).
    """
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return None
    lang_names = {"en": "inglés", "pt": "portugués", "fr": "francés", "de": "alemán", "it": "italiano"}
    target_name = lang_names.get(target_lang.lower(), target_lang)
    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key)
        prompt = (
            f"Traduce el siguiente mensaje del español al {target_name}. "
            "Mantén el tono natural, cercano y seductor; no suenes a traductor automático. "
            "Responde SOLO con la traducción, sin explicaciones.\n\nMensaje:\n{text}"
        ).format(text=text)
        r = client.chat.completions.create(
            model=os.getenv("AI_MODEL_NAME", "gpt-3.5-turbo"),
            messages=[{"role": "user", "content": prompt}],
            max_tokens=500,
        )
        if r.choices and r.choices[0].message and r.choices[0].message.content:
            return r.choices[0].message.content.strip()
    except Exception as e:
        logger.debug(f"OpenAI translate falló: {e}")
    return None


def translate_for_client(text: str, target_lang: str) -> str:
    """
    Traduce la respuesta (en español) al idioma del cliente.
    Intenta OpenAI para tono natural; si no, usa Google.
    """
    if not target_lang or target_lang.lower() == "es":
        return text
    out = translate_with_openai(text, target_lang, "es")
    if out:
        return out
    out = translate_to(text, target_lang, "es")
    return out if out else text
