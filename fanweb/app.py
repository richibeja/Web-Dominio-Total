"""
FanWeb - Plataforma web para gestión y monetización
"""
import os
import sys
import logging

# Agregar el directorio raíz del proyecto al path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from flask import Flask, render_template, request, jsonify, session, send_from_directory
from flask_cors import CORS
from dotenv import load_dotenv
from ai_models.ai_handler import AIHandler
import base64

# Cargar variables de entorno
load_dotenv()

# Configurar logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Inicializar Flask app
app = Flask(__name__, static_folder='static')
CORS(app) # Habilitar CORS para permitir widgets externos
app.secret_key = os.getenv("FANWEB_SECRET_KEY", "default-secret-key-change-in-production")

# Inicializar manejador de IA
ai_handler = AIHandler()

@app.route("/")
def index():
    """Página principal"""
    return render_template("index.html")

@app.route("/chat", methods=["GET", "POST"])
def chat():
    """Página de chat con IA"""
    if request.method == "POST":
        data = request.get_json()
        user_message = data.get("message", "")
        user_id = session.get("user_id", "anonymous")
        
        try:
            # Obtener respuesta del modelo de IA
            ai_response = ai_handler.get_response_sync(user_message, user_id=user_id)
            
            return jsonify({
                "status": "success",
                "response": ai_response
            })
        except Exception as e:
            logger.error(f"Error en chat: {e}")
            return jsonify({
                "status": "error",
                "message": "Error al procesar el mensaje"
            }), 500
    
    return render_template("chat.html")

@app.route("/api/voice-chat", methods=["POST"])
def api_voice_chat():
    """API endpoint para chat de voz en el widget"""
    data = request.get_json()
    user_message = data.get("message", "")
    user_id = data.get("user_id", "anonymous_web")
    
    try:
        # Ejecutar async desde Flask sincrónico
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        # Llamar a AIHandler para texto + voz
        result = loop.run_until_complete(ai_handler.get_response_with_voice(
            user_message, 
            user_id=user_id, 
            dialect="paisa", 
            voice_style="Sonrisa"
        ))
        loop.close()
        
        text = result.get("text", "")
        voice_file = result.get("voice_file")
        audio_base64 = None
        
        if voice_file and os.path.exists(voice_file):
            with open(voice_file, "rb") as f:
                audio_base64 = base64.b64encode(f.read()).decode('utf-8')
                
        return jsonify({
            "status": "success",
            "text": text,
            "audio": audio_base64
        })
    except Exception as e:
        logger.error(f"Error en voice chat: {e}")
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

@app.route("/static/<path:path>")
def send_static(path):
    return send_from_directory('static', path)

@app.route("/api/chat", methods=["POST"])
def api_chat():
    """API endpoint para chat"""
    data = request.get_json()
    user_message = data.get("message", "")
    user_id = data.get("user_id", "anonymous")
    
    try:
        ai_response = ai_handler.get_response_sync(user_message, user_id=user_id)
        
        return jsonify({
            "status": "success",
            "response": ai_response
        })
    except Exception as e:
        logger.error(f"Error en API chat: {e}")
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

@app.route("/dashboard")
def dashboard():
    """Dashboard de administración"""
    return render_template("dashboard.html")

@app.route("/api/stats")
def api_stats():
    """API para estadísticas"""
    # TODO: Implementar estadísticas reales
    return jsonify({
        "total_users": 0,
        "total_messages": 0,
        "revenue": 0
    })

@app.route("/health", methods=["GET"])
def health_check():
    """Endpoint de salud"""
    return jsonify({"status": "healthy", "service": "fanweb"}), 200

def main():
    """Función principal para iniciar el servidor (puerto 3000 por defecto)."""
    port = int(os.getenv("FANWEB_PORT", 5000))
    host = os.getenv("FANWEB_HOST", "0.0.0.0")
    
    logger.info(f"Iniciando FanWeb en {host}:{port}")
    app.run(host=host, port=port, debug=True)

if __name__ == "__main__":
    main()
