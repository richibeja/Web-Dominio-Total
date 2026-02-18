
import os
import sys

# Agregar la raíz del proyecto al path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.append(project_root)

from ai_models.voice_handler import VoiceHandler

def generar_audio_seduccion():
    print("Iniciando generación de audio Paisa Seductor...")
    
    texto = "Mijo, venga le digo una cosa aquí cerquita... A nosotras no nos importan tanto los carros lujosos como usted cree. Lo que de verdad nos vuelve locas y hace que nos enamoremos... es que usted sepa controlar su cuerpo y nos haga ver estrellas por más de 30 minutos sin parar. Pero la mayoría no dura ni 5... ¡Qué pecado! 🙈 Si usted quiere aprender el truco prohibido para ser inolvidable, le dejé el secreto en el link de mi perfil. Pero corra, que eso lo borran rápido."
    
    try:
        vh = VoiceHandler()
        # Forzar voz clonada PAISA
        vh.voice_provider = "cloned" 
        
        output_path = vh.generate_voice(texto)
        
        if output_path and os.path.exists(output_path):
            print(f"✅ Audio generado exitosamente en: {output_path}")
            # Reproducir el audio (opcional, solo en Windows)
            os.startfile(output_path)
        else:
            print("❌ Error: No se pudo generar el archivo de audio.")
            
    except Exception as e:
        print(f"❌ Error crítico: {str(e)}")

if __name__ == "__main__":
    generar_audio_seduccion()
