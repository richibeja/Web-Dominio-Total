"""
Configuración de enlaces de SociosAnbelClub
Actualiza estos enlaces según sea necesario. LINK_VENTAS_TELEGRAM en .env tiene prioridad.
"""
import os
from dotenv import load_dotenv
load_dotenv()

# Enlaces principales (telegram desde .env LINK_VENTAS_TELEGRAM si existe)
# Enlaces DE ORO (AQUI ESTA EL DINERO)
LINKS = {
    # 1. Página de Ventas (Embudo Principal)
    "sales_page": "https://web-dominio-total.vercel.app",

    # 2. Comunidad VIP (Telegram) - Donde viven los fans
    "telegram": "https://t.me/LuzDeAuroraOficial",
    "telegram_bot": "@LuzDeAuroraOficial",

    # 3. Checkout HOTMART (Ebook $7) - Venta rápida
    "ebook_payment": "https://pay.hotmart.com/E104450083T",
    
    # 4. Suscripción Mensual (Fanvue) - Venta recurrente
    "fanvue": "https://www.fanvue.com/luzdeaurorafeyamor",
    "fanvue_profile": "https://www.fanvue.com/luzdeaurorafeyamor",

    # 5. Redes de Tráfico
    "instagram": "https://www.instagram.com/luzdeaurorafeyamor/",
    "whatsapp": f"https://wa.me/{os.getenv('WHATSAPP_NUMBER', '+57 322 719 8007').replace('+', '').replace(' ', '')}",
    
    # Extras
    "linktree": "https://linktr.ee/SociosAnbelClub",
}
API_KEYS = {
    "fanvue_key": "6C/wYuCc/g5L7Sv",  # Clave de Fanvue
}

# Información de la marca
BRAND_INFO = {
    "name": "Socios Anbel Club",
    "instagram_username": "SociosAnbelClub",
    "description": "El Club más exclusivo de modelos latinas",
    "hashtags": ["#SociosAnbelClub", "#ModelosLatinas", "#VIP", "#Exclusivo", "#IA", "#InteligenciaArtificial", "#ContenidoIA"],
    "content_types": [
        "✨ Contenido exclusivo y personalizado",
        "📸 Fotos y videos inéditos",
        "💬 Mensajes privados",
        "🎁 Contenido personalizado"
    ],
    "instagram_stats": {
        "posts": 300,
        "followers": "50k",
        "following": 1,
        "bio_keywords": "modelos, exclusivas, latinas, VIP, fotografía, videos, contenido privado"
    }
}

# Mensajes del bot - NATURALES, CORTOS, SEDUCTORES
MESSAGES = {
    "welcome": (
        "¡Hola! 😊 Qué lindo que me escribas 💕\n\n"
        "Me encanta conocerte... Contame de vos ✨\n\n"
        "Si querés hablamos por Telegram o entrá a mi Fanvue (gratis) 😘"
    ),
    "content_info": (
        "🌟 ¡Bienvenidos a SociosAnbelClub! 🔞\n"
        "🔒 Canal VIP exclusivo con contenido que Instagram no permite\n\n"
        "Contenido exclusivo de modelos latinas generado con inteligencia artificial de última generación.\n"
        "Sesiones privadas, lencería y momentos íntimos que no verás en ningún otro lado.\n\n"
        "👯 Las modelos latinas más bellas\n"
        "📸 Fotos y videos sin censura\n"
        "💎 Acceso VIP total\n\n"
        "🤖 Todo el contenido es generado con IA de alta calidad\n"
        "📌 SUSCRÍBETE y activa las notificaciones 🔔\n\n"
        "⚠️ Contenido generado con inteligencia artificial."
    )
}
