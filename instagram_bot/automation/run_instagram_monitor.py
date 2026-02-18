"""
Script principal para monitorear Instagram (comentarios y DMs).
Solo Instagram: automatización, traducción y espejo a Telegram.
Fanvue lo manejan los trabajadores manualmente en otra pestaña.
"""
import asyncio
import logging
import sys
import os
from pathlib import Path

# Agregar el directorio raíz del proyecto al path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from instagram_bot.automation.monitor import run_monitor

# Configurar logging
log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
logging.basicConfig(
    level=logging.INFO,
    format=log_format,
    handlers=[
        logging.FileHandler("instagram_monitor.log", encoding='utf-8'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

if __name__ == "__main__":
    """
    Ejecuta solo el monitor de Instagram (comentarios y DMs).
    - Comentarios en posts: responde con IA y enlaces a Telegram/Fanvue.
    - DMs: espejo a Telegram Operaciones, espera humano o IA, traduce al idioma del cliente.
    - Fanvue: no se abre ni se automatiza; los trabajadores lo usan en otra pestaña.
    Para detener: Ctrl+C
    """
    try:
        logger.info("Iniciando monitor de Instagram (solo Instagram, sin Fanvue)...")
        logger.info("  - Comentarios y DMs con puente a Telegram Operaciones")
        logger.info("  - Primera vez: inicia sesion manualmente en Instagram en la ventana que se abrira")
        # Limpieza previa para optimizar
        try:
            logger.info("🧹 Limpiando caché y temporales antiguos...")
            for f in Path("data").glob("*.json"):
                if f.name not in ["instagram_dms_processed.json", "instagram_comments_processed.json"]:
                     # No borrar persistencia crítica
                     pass
            
            # Borrar carpetas de cache de navegador
            import shutil
            for d in Path(".").glob("user_data_*"):
                if d.is_dir():
                    # shutil.rmtree(d, ignore_errors=True) # Opcional: solo si da problemas
                    pass
        except: pass

        asyncio.run(run_monitor())
    except KeyboardInterrupt:
        logger.info("Monitor de Instagram detenido por el usuario")
    except Exception as e:
        logger.error(f"Error fatal: {e}", exc_info=True)
    finally:
        # Reducir avisos de "unclosed transport" / "I/O operation on closed pipe" al salir con Ctrl+C (Windows)
        import warnings
        warnings.filterwarnings("ignore", category=ResourceWarning, message="unclosed")
