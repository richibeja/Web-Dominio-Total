from pathlib import Path
import asyncio

# Intentar importar edge_tts. Si falla, el usuario debe instalarlo manualmente donde use python.
try:
    import edge_tts
except ImportError:
    print("Por favor instala edge_tts: pip install edge-tts")
    edge_tts = None

OUTPUT_FILE = Path("c:/Users/ALP/Documents/modelos  ia para monitizar/content/audio_respiracion_478.mp3")
VOICE = "es-CO-SalomeNeural" # Voz colombiana suave

# TEXTO LIMPIO (Sin códigos, solo la voz de Aurora guiando)
TEXTO_GUIA = """
Hola, mi amor. Soy Aurora.
Quiero que te relajes ahora mismo. Suelta tus hombros.

Vamos a controlar esa energía juntos.
Cuando sientas que la temperatura sube demasiado, detente.
Ahora, inhala profundo por la nariz... uno... dos... tres... cuatro.
Sostén el aire... dos... tres... cuatro... cinco... seis... siete.
Y suelta suavemente por la boca... uno... dos... tres... cuatro... cinco... seis... siete... ocho.

Muy bien. Siente cómo tu cuerpo se calma. Tienes el control total.
Repite esto si lo necesitas. Tú mandas.
"""

async def generar_audio():
    if not edge_tts:
        return
    
    communicate = edge_tts.Communicate(TEXTO_GUIA, VOICE)
    # Generar el archivo limpio
    await communicate.save(str(OUTPUT_FILE))
    print(f"Audio generado exitosamente en: {OUTPUT_FILE}")

if __name__ == "__main__":
    if edge_tts:
        asyncio.run(generar_audio())
    else:
        print("No se pudo generar el audio por falta de librería edge-tts.")
