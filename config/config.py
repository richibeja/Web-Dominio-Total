"""
Configuración centralizada del proyecto
"""
import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    """Configuración base"""
    
    # Telegram Office
    TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
    TELEGRAM_ADMIN_IDS = os.getenv("TELEGRAM_ADMIN_IDS", "").strip()  # IDs separados por comas
    
    # AI Models (OpenRouter + Grok por defecto)
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
    AI_MODEL_PROVIDER = os.getenv("AI_MODEL_PROVIDER", "openai")
    AI_MODEL_NAME = os.getenv("AI_MODEL_NAME", "gpt-3.5-turbo")
    
    # FanWeb
    FANWEB_SECRET_KEY = os.getenv("FANWEB_SECRET_KEY", "change-this-in-production")
    FANWEB_HOST = os.getenv("FANWEB_HOST", "0.0.0.0")
    FANWEB_PORT = int(os.getenv("FANWEB_PORT", 5000))
    
    # Database
    DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./database.db")
    
    # Monetization
    PAYMENT_PROVIDER = os.getenv("PAYMENT_PROVIDER", "stripe")
    STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY", "")
    STRIPE_PUBLIC_KEY = os.getenv("STRIPE_PUBLIC_KEY", "")
    
    # Fanvue
    FANVUE_API_KEY = os.getenv("FANVUE_API_KEY", "6C/wYuCc/g5L7Sv")
    FANVUE_URL = os.getenv("FANVUE_URL", "https://www.fanvue.com/utopiafinca")
