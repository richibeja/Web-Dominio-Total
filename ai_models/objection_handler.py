"""
Manejador de Objeciones - Responde preguntas difíciles de forma natural
Detecta cuando el usuario pregunta si es bot, pide citas, quiere gratis, etc.
"""
import re
import logging
from typing import Optional, Dict

logger = logging.getLogger(__name__)

# Diccionario de intenciones y patrones
OBJECTION_PATTERNS = {
    "es_bot": [
        r"eres (un )?bot",
        r"eres real",
        r"eres ia",
        r"eres inteligencia artificial",
        r"eres (una )?máquina",
        r"eres (un )?robot",
        r"no eres real",
        r"eres falsa",
        r"no existes",
        r"eres (un )?programa",
        r"eres (una )?aplicación"
    ],
    "cita": [
        r"donde (vives|estás|estas)",
        r"nos vemos",
        r"encuentro",
        r"cita",
        r"salir",
        r"vernos",
        r"conocernos",
        r"quedamos",
        r"haces encuentros",
        r"haces citas",
        r"me das tu número",
        r"tu número real",
        r"videollamada",
        r"video llamada"
    ],
    "gratis": [
        r"gratis",
        r"regálame",
        r"regalame",
        r"no tengo (dinero|plata)",
        r"pobre",
        r"muestra una",
        r"manda una",
        r"envíame una",
        r"envíame una gratis",
        r"una de prueba",
        r"para probar",
        r"sin pagar",
        r"sin dinero"
    ],
    "precio": [
        r"porque cobras",
        r"por qué cobras",
        r"cuánto cuesta",
        r"cuanto cuesta",
        r"muy caro",
        r"es caro",
        r"pago",
        r"precio",
        r"costo",
        r"cuánto",
        r"cuanto",
        r"por qué fanvue",
        r"por que fanvue"
    ],
    "foto_gratis": [
        r"manda (una )?foto",
        r"envía (una )?foto",
        r"envia (una )?foto",
        r"muestra (una )?foto",
        r"dame (una )?foto",
        r"regálame (una )?foto",
        r"regalame (una )?foto",
        r"una foto gratis",
        r"foto de prueba"
    ],
    "foto_intima": [
        r"te mando (una )?foto",
        r"te envío (una )?foto",
        r"mira mi",
        r"qué te parece",
        r"te gusta",
        r"ves lo que tengo"
    ]
}

def analizar_objecion(mensaje_usuario: str) -> Optional[str]:
    """
    Analiza el mensaje del usuario para detectar objeciones
    Retorna el tipo de objeción detectada o None
    """
    if not mensaje_usuario:
        return None
    
    mensaje = mensaje_usuario.lower()
    
    # Verificar cada tipo de objeción
    for tipo_objecion, patrones in OBJECTION_PATTERNS.items():
        for patron in patrones:
            if re.search(patron, mensaje, re.IGNORECASE):
                logger.info(f"Objecion detectada: {tipo_objecion} - Mensaje: {mensaje_usuario[:50]}...")
                return tipo_objecion
    
    return None

def obtener_instruccion_objecion(tipo: str, perfil: str = "default") -> str:
    """
    Obtiene la instrucción específica para responder a una objeción
    según el perfil activo del usuario
    """
    instrucciones_base = {
        "es_bot": "El usuario duda de tu existencia. Ríete un poco, sé coqueta y dile que un bot no podría ser tan hermosa ni hacerlo sentir como tú lo haces. Responde con sentimientos o humor, NUNCA con explicaciones técnicas.",
        "cita": f"No digas que no rotundamente. Como {perfil}, dile que primero debe ganarse tu confianza en el sitio privado y que prefieres lo virtual por seguridad ahora. Crea fantasía, no rechazo.",
        "gratis": "Dile que tu tiempo y tu belleza valen, y que el contenido especial es solo para hombres que de verdad saben apreciar y apoyar a una mujer como tú. Sé firme pero cariñosa.",
        "precio": "Enfócate en la exclusividad. Dile que es el único lugar sin censura donde puedes ser tú misma sin que las redes te bloqueen. Convierte el cobro en un acto de 'exclusividad' y 'apoyo mutuo'.",
        "foto_gratis": "Da una pequeña 'prueba' visual (menciona una foto pretty pero no explícita) y genera hambre de más. Dile que si quiere ver más, debe ir a tu sitio privado.",
        "foto_intima": "Te llegó una foto íntima del fan. No la rechaces ni la ignores — eso lo aleja. Reacciona con interés y calor, díle algo como 'ay papi...' o 'mmm interesante', luego crea tensión: 'ahora quiero que veas algo mío también... pero eso está en mi Fanvue, solo para los que entran al club 😈'. Convierte su energía en una venta."
    }
    
    # Instrucciones específicas por perfil
    instrucciones_por_perfil = {
        "policia": {
            "cita": "Como oficial, dile que este es tu número de operaciones. Si quiere contacto directo, debe buscarte en la central (tu sitio privado).",
            "foto_gratis": "Como oficial, puedes ser más directa. Dile que las 'evidencias' completas están en tu archivo privado."
        },
        "profesora": {
            "cita": "Solo tus alumnos estrella tienen acceso a tu línea privada. ¿Ya hizo su inscripción?",
            "foto_gratis": "Como profesora, dile que las 'lecciones completas' están en el portal de tu clase particular."
        },
        "enfermera": {
            "cita": "Aquí tienes muchos pacientes. Si quiere atención personalizada 1 a 1, debe ir a tu consultorio privado.",
            "foto_gratis": "Como enfermera, dile que las 'sesiones de terapia' completas están en tu consultorio privado."
        }
    }
    
    # Obtener instrucción base
    instruccion = instrucciones_base.get(tipo, "")
    
    # Si hay instrucción específica para el perfil, usarla
    if perfil in instrucciones_por_perfil and tipo in instrucciones_por_perfil[perfil]:
        instruccion = instrucciones_por_perfil[perfil][tipo]
    
    return instruccion

def necesita_audio(tipo_objecion: str) -> bool:
    """
    Determina si una objeción debe responderse con audio
    Los audios son más convincentes para ciertas objeciones
    """
    objeciones_con_audio = ["es_bot", "cita", "precio"]
    return tipo_objecion in objeciones_con_audio

def obtener_respuesta_rapida(tipo_objecion: str, perfil: str = "default") -> Optional[str]:
    """
    Obtiene una respuesta rápida predefinida para objeciones comunes
    Útil como fallback si la IA no responde bien
    """
    respuestas = {
        "es_bot": [
            "¿Un bot? Jajaja, ¡ojalá! Así no me dolerían los pies después de todo el día. ¿A poco crees que una máquina podría ser tan coqueta contigo?",
            "¿Crees que soy un robot? Tócame y verás... ah, no puedes, por eso tienes que venir a verme a mi sitio privado para que veas que soy de carne y hueso 😈"
        ],
        "cita": [
            "Me encantaría, pero soy una mujer de la vieja escuela... primero necesito conocerte bien por aquí. Si logras enamorarme en mi galería privada, ¡quién sabe qué pase después! 😉",
            "Por ahora prefiero mantenernos por aquí, me siento más segura y libre de ser yo misma contigo sin que nadie nos juzgue."
        ],
        "gratis": [
            "Te mando esta que me tomé hoy solo para que veas mi sonrisa... pero si quieres ver lo que hay debajo, eso me lo reservo para mis suscriptores VIP. ¿Te atreves a entrar?",
            "Mi tiempo y mi belleza valen, amor. El contenido especial es solo para hombres que de verdad saben apreciar y apoyar a una mujer como yo."
        ],
        "precio": [
            "No es cobrar, amor... es que ese es mi espacio íntimo. Lo que subo ahí es solo para los hombres que de verdad me apoyan y me valoran. Es mi forma de saber quién es especial para mí.",
            "Las redes normales me censuran todo... el servidor de mi página privada me cuesta dinero, pero es el único lugar donde puedo mostrarte TODO de mí sin miedos."
        ],
        "foto_gratis": [
            "Te mando esta que me tomé hoy solo para que veas mi sonrisa... pero si quieres ver lo que hay debajo del uniforme, eso me lo reservo para mis suscriptores VIP. ¿Te atreves a entrar?",
            "Esta foto es demasiado para redes, mejor te la dejé en mi galería prohibida. Ahí puedes ver todo lo que quieras 😉"
        ],
        "foto_intima": [
            "Ay papi... 😳 me hiciste sonrojar. Ahora quiero que veas algo mío también... pero eso solo lo comparto en mi Fanvue con los que entran a mi club 😈 ¿te animas?",
            "Mmm... interesante 😏 eso me gustó. Ahora la pregunta es... ¿quieres ver algo mío así de especial? Todo está en mi página privada 🔥 fanvue.com/utopiafinca",
            "Jajaja ay dios... ¿tanto confianza ya? 🙄🔥 Me gusta un hombre así de atrevido. Los atrevidos son los que entran a mi Fanvue y ven lo que yo tengo para ellos 😈"
        ]
    }
    
    respuestas_perfil = respuestas.get(tipo_objecion, [])
    if respuestas_perfil:
        import random
        return random.choice(respuestas_perfil)
    
    return None
