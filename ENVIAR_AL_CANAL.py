import os
import requests
import edge_tts
import asyncio
from dotenv import load_dotenv

# Cargar configuración
load_dotenv()
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
VOICE = os.getenv("VOICE_EDGE_CODE", "es-CO-SalomeNeural")
LINK_VIP = os.getenv("FANVUE_LINK", "https://www.fanvue.com/utopiafinca")
CANAL_ID = os.getenv("TELEGRAM_CHANNEL_ID", "@LuzDeAuroraOficial")

# El mensaje de texto que acompaña al audio (Cuento Erótico Paisa)
TEXTO_AUDIO = "Hola mis amores... estaba aquí solita en la finca, ya está cayendo la tarde y no se imaginan el calor que está haciendo... me tocó quitarme casi todo mientras me tomaba un vinito. Y no sé por qué, pero me puse a pensar en ustedes. Me imaginé cómo sería si alguno de ustedes estuviera aquí conmigo, en esta cama tan grande, acariciando mi piel quemadita por el sol, bajándome la lencería despacito mientras me susurran cosas al oído. Ay, de solo pensarlo me erizo toda y me pongo a mil... Si quieren ver qué me tocó hacer para quitarme estas ganas y cómo terminé después con este calorcito... los espero allá en mi rinconcito más privado, donde sí les puedo mostrar todo todito sin censura. No me dejen esperando... un besito en donde más les guste."
CAPTION = f"🎧 Escuchen con audífonos y cierren los ojos... 🔥👇\n{LINK_VIP}"

async def generar_audio_paisa():
    print(f"🎙️ Generando la nota de voz paisa realista con la voz {VOICE}...")
    communicate = edge_tts.Communicate(TEXTO_AUDIO, VOICE, rate="+5%")
    await communicate.save("saludo_canal.mp3")
    print("✅ Nota de voz generada con éxito (saludo_canal.mp3)!")

def enviar_al_canal():
    print(f"📢 Enviando la nota de voz al canal {CANAL_ID}...")
    try:
        url = f"https://api.telegram.org/bot{TOKEN}/sendVoice"
        with open("saludo_canal.mp3", "rb") as audio:
            resp = requests.post(url, data={"chat_id": CANAL_ID, "caption": CAPTION}, files={"voice": audio})
            
            if resp.status_code == 200:
                print(f"✅ ¡LA NOTA DE VOZ FUE ENVIADA EXITOSAMENTE AL CANAL {CANAL_ID}!")
            else:
                print(f"⚠️ Error al enviar al canal. Código: {resp.status_code}")
                print(f"Detalle: {resp.text}")
                print("📌 Asegúrate de que el bot sea ADMINISTRADOR del canal y que el ID del canal en el .env sea correcto.")
                
    except Exception as e:
        print(f"❌ Error durante el envío: {e}")

if __name__ == "__main__":
    print("🚀 INICIANDO SISTEMA DE TRANSMISIÓN DE VOZ AL CANAL PÚBLICO 🚀")
    asyncio.run(generar_audio_paisa())
    enviar_al_canal()
    print("🎉 Misión cumplida. Revisa tu canal de Telegram.")
