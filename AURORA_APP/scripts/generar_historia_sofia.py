#!/usr/bin/env python3
import os
import sys
from pathlib import Path

# Añadir raíz del proyecto al path para importar VoiceHandler
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

def generar_audio_historia():
    try:
        from ai_models.voice_handler import VoiceHandler
        from dotenv import load_dotenv
        
        load_dotenv(PROJECT_ROOT / ".env")
        
        vh = VoiceHandler()
        
        # El guion para el audio de Aurora con más picante
        guion = """
        Ay no, papi... ¡es que yo no puedo con la rabia, fueputa! Es que uno cree que se las sabe todas, pero no. 
        Mi amiga Sofía me llamó llorando, deshecha... y lo peor mor, es que la niña estaba era tragada, porque según ella, el tipo era un BUEN POLVO, de esos que te dejan las piernas temblando y no te dejan pensar en nada más.
        
        El berraco la tenía engatusada con ese cuento, la atendía como a una reina en la cama... ¡pero de resto un malparido! 
        Imagínese que la niña le pilló un segundo celular escondido por allá en la llanta de repuesto del carro. ¿Ustedes pueden creer ese nivel de perversión? 
        ¡En la llanta, mor! El tipo tenía toda una vida armada en otra ciudad, con otra mujer oficial y hasta planes de boda. 
        
        O sea, el tipo repartiendo bala por todos lados y una aquí creyendo que el hombre es un santo porque la hace sentir rico. 
        A lo bien... ¿Ustedes por qué son tan perros? ¿Es que no les basta con tener una mujer que los quiera y se los goce bien rico? 
        
        Yo sé que aquí hay mucho hombre que se cree muy lince, pero a ver... cuéntenme la verdad aquí abajo: 
        ¿Ustedes también tienen el celular escondido o son de los que dan la cara? 
        Porque si me siguen emputando, voy a soltar los detalles más cochinos de este chisme en el Podcast Prohibido, para que aprendan que con una mujer como nosotras no se juega.
        
        ¡Los leo pues, y no me salgan con cuentos chimbos!
        """
        
        print("🎙️ Iniciando generación de voz para la historia de Sofía...")
        
        # Generar el audio
        # Usamos user_id="historia_sofia" para identificar el archivo fácilmente
        ruta_audio = vh.generate_voice(guion, user_id="historia_sofia")
        
        if ruta_audio and os.path.exists(ruta_audio):
            print(f"\n✅ ¡AUDIO GENERADO CON ÉXITO!")
            print(f"📍 Ubicación: {os.path.abspath(ruta_audio)}")
            
            # --- ENVÍO AUTOMÁTICO A TELEGRAM ---
            token = os.getenv("TELEGRAM_BOT_TOKEN")
            channel_id = os.getenv("TELEGRAM_CHANNEL_ID")
            
            if token and channel_id:
                print(f"📤 Enviando automáticamente al canal {channel_id}...")
                import requests
                
                texto_post = (
                    "Mor... a lo bien estoy indignada. 😤 Lo que le pasó a mi amiga Sofía no tiene nombre. "
                    "¿Será que la fidelidad ya no existe o es que los hombres se volvieron muy profesionales para la mentira? "
                    "Escuchen esto y me cuentan abajo. 👇"
                )
                
                url = f"https://api.telegram.org/bot{token}/sendVoice"
                with open(ruta_audio, 'rb') as voice_file:
                    files = {'voice': voice_file}
                    data = {'chat_id': channel_id, 'caption': texto_post}
                    response = requests.post(url, files=files, data=data)
                
                if response.status_code == 200:
                    print("🚀 ¡PUBLICADO EN TELEGRAM AUTOMÁTICAMENTE!")
                else:
                    print(f"❌ Error al enviar a Telegram: {response.text}")
            else:
                print("⚠️ No se encontró TOKEN o CHANNEL_ID en el .env. Súbelo manualmente.")
                print("\nInstrucciones para Telegram:")
                print("1. Sube este archivo a tu canal de Telegram.")
                print("2. Acompáñalo con el mensaje de texto sugerido.")
        else:
            print("❌ Error: No se pudo generar el archivo de audio.")
            
    except Exception as e:
        print(f"❌ Error fatal: {str(e)}")

if __name__ == "__main__":
    generar_audio_historia()
