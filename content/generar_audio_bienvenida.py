from pathlib import Path
import asyncio

# Intentar importar edge_tts. Si falla, el usuario debe instalarlo manualmente donde use python.
try:
    import edge_tts
except ImportError:
    print("Por favor instala edge_tts: pip install edge-tts")
    edge_tts = None

OUTPUT_FILE = Path("c:/Users/ALP/Documents/modelos  ia para monitizar/content/audio_bienvenida_ebook.mp3")
VOICE = "es-CO-SalomeNeural" # Voz colombiana suave

# TEXTO LIMPIO PARA AUDIO DE BIENVENIDA
TEXTO_GUIA = """
Hola, guapo. Sabía que llegarías hasta aquí.
La mayoría de los hombres tienen miedo de admitir lo que realmente quieren. Pero tú no. Tú tienes hambre de más.

En las siguientes páginas, no vas a encontrar teorías aburridas de psicología. Vas a encontrar la verdad cruda sobre lo que nosotras pensamos en la cama y que JAMÁS te diríamos a la cara.

Pero te advierto una cosa...
Una vez que sepas cómo controlarnos... no podrás volver atrás.
Tu 'problema' de terminar rápido se convertirá en tu mayor arma si me haces caso.

Lee con atención. No te saltes la página 4, porque ahí te dejé un regalo especial que cambiará tu noche hoy mismo.

Nos vemos dentro.
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
