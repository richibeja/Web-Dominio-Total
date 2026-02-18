import os
import sys
import logging
from fanvue_mcp.server import create_mcp_server
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("FanvueMCPServer")

def run():
    """Inicia el servidor Fanvue MCP"""
    try:
        logger.info("Iniciando servidor Fanvue MCP...")
        mcp = create_mcp_server()
        
        # Obtener configuración de entorno o usar defaults
        host = os.getenv("MCP_SERVER_HOST", "127.0.0.1")
        port = int(os.getenv("MCP_SERVER_PORT", "8080"))
        
        logger.info(f"Servidor Fanvue MCP escuchando en http://{host}:{port}")
        mcp.run(transport="http", host=host, port=port)
        
    except Exception as e:
        logger.error(f"Error al iniciar el servidor Fanvue MCP: {e}")
        sys.exit(1)

if __name__ == "__main__":
    run()
