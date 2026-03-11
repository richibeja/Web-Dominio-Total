import os
import requests
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CANAL_ID = os.getenv("TELEGRAM_CHANNEL_ID", "@LuzDeAuroraOficial")
BOT_LINK = os.getenv("TELEGRAM_BOT_LINK", "https://t.me/utopiafincabot")

TEXTO = f"Mor... me desvelé, estoy dando vueltas en la cama y tengo un calorcito que no me deja dormir 🥺🔥.\n\n¿Hay alguno de mis amorcitos despierto que me quiera hacer compañía un ratico?\n\nEscríbanme al privado rapidito a ver quién me quita el insomnio... los leo a todos por acá, [👉 tóquenme aquí para chatear 👈]({BOT_LINK}) 😈"

def enviar_invitacion():
    print(f"📢 Enviando la invitación nocturna al canal {CANAL_ID}...")
    try:
        url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
        resp = requests.post(url, data={"chat_id": CANAL_ID, "text": TEXTO, "parse_mode": "Markdown"})
        
        if resp.status_code == 200:
            print(f"✅ ¡LA INVITACIÓN FUE ENVIADA EXITOSAMENTE AL CANAL!")
        else:
            print(f"⚠️ Error al enviar. Código: {resp.status_code}")
            
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    enviar_invitacion()
