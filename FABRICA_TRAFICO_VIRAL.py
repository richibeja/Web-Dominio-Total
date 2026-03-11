import os
import random
import asyncio
import edge_tts
from datetime import datetime

# =======================================================================
# FABRICA DE TRÁFICO VIRAL (TIKTOK / REELS / SHORTS) - AURORA 💋
# =======================================================================
# Objetivo: Generar audios hiper-virales de 5 a 10 segundos diseñados 
# psicológicamente con curvas de retención y "ganchos" para llevar 
# tráfico masónico (hombres) al embudo de Telegram.
# -----------------------------------------------------------------------

VOICE = os.getenv("VOICE_EDGE_CODE", "es-CO-SalomeNeural")
OUTPUT_DIR = "generated_audios/tiktok_reels"

# Crear directorio si no existe
os.makedirs(OUTPUT_DIR, exist_ok=True)

# -----------------------------------------------------------------------
# EL ARSENAL: Ganchos Psicológicos (Hooks) comprobados
# -----------------------------------------------------------------------
GUIONES_VIRALES = [
    # Guion 1: La Confidencia (Genera curiosidad extrema)
    {
        "nombre": "la_confidencia",
        "texto": "Hay algo que los hombres hacen que me vuelve loca... pero me da demasiada pena decirlo por aquí. Si eres hombre y quieres saberlo... entra al link de mi perfil, te lo mandé por nota de voz."
    },
    
    # Guion 2: El Desafío (Toca el ego masculino)
    {
        "nombre": "el_desafio",
        "texto": "Papi, apuesto a que no aguantas ni 5 minutos hablando conmigo en privado... Si crees que sí, tócala el link de mi perfil y demuéstralo. Te estoy esperando bebé."
    },
    
    # Guion 3: La Novia de Bolsillo (Ataca la soledad)
    {
        "nombre": "novia_de_bolsillo",
        "texto": "¿Sabes qué es lo mejor de tener una novia paisa? Que siempre que estés aburrido o estresado, puedes llamarme. Amor, te dejé un regalito esperándote en el link de mi perfil... ve a verlo."
    },
    
    # Guion 4: La Pregunta Íntima (Retención altísima)
    {
        "nombre": "pregunta_intima",
        "texto": "Hombres, tengo una duda muy seria... ¿Por qué les gusta tanto cuando nosotras tomamos la iniciativa? Si tienes la respuesta, dímela al privado. El link está arriba... mua."
    },
    
    # Guion 5: Oferta Flash (Para meter urgencia al embudo)
    {
        "nombre": "oferta_flash",
        "texto": "Solamente a los primeros cien hombres que toquen el link de mi perfil hoy... les voy a mandar una cosita muy rica por Telegram. Corre porque me arrepiento... mua."
    }
]

def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)

async def generar_audio(guion):
    """
    Genera el audio en MP3 basándose en uno de los guiones letales.
    """
    nombre_archivo = f"{OUTPUT_DIR}/viral_{guion['nombre']}.mp3"
    log(f"🎙️ Grabando audio viral: {guion['nombre']}")
    
    # Rate ligeramente más rápido para TikTok/Reels (+5% a +8% funciona excelente)
    communicate = edge_tts.Communicate(guion['texto'], VOICE, rate="+8%")
    await communicate.save(nombre_archivo)
    
    log(f"✅ Guardado con éxito: {nombre_archivo}")
    return nombre_archivo

async def fabrica_de_trafico():
    log("======================================================")
    log("🚀 INICIANDO FÁBRICA DE TRÁFICO: CREADOR DE AUDIOS VIRALES")
    log("======================================================")
    
    # Puedes elegir si generar uno al azar o TODOS. En este caso, haremos todos.
    log(f"Cargando {len(GUIONES_VIRALES)} guiones diseñados psicológicamente...")
    time.sleep(1)
    
    archivos_cerrados = 0
    for guion in GUIONES_VIRALES:
        await generar_audio(guion)
        archivos_cerrados += 1
        # Pausa pequeñita para no abrumar al servidor TTS
        time.sleep(1.5)
        
    log("======================================================")
    log(f"💣 {archivos_cerrados} ARMAMENTOS AUDITIVOS LISTOS EN: {OUTPUT_DIR}")
    log("======================================================")
    log("INSTRUCCIONES DE USO:")
    log("1. Entra a la carpeta 'generated_audios/tiktok_reels'")
    log("2. Toma el MP3 y envíatelo al celular.")
    log("3. En CapCut, únelo con una foto o video de Aurora caminando o posando.")
    log("4. ¡Súbelo a TikTok/Reels y mira cómo estalla tu Telegram!")

if __name__ == "__main__":
    import time
    asyncio.run(fabrica_de_trafico())
