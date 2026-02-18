"""
Integración de Meta Pixel para tracking de conversiones en Fanvue
Rastrea suscripciones, compras y conversiones desde anuncios de Facebook/Instagram
"""
import os
import sys
import logging
import requests
from typing import Dict, Optional

# Agregar el directorio raíz del proyecto al path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from dotenv import load_dotenv
load_dotenv()

logger = logging.getLogger(__name__)

class MetaPixelTracker:
    """Rastrea eventos de conversión en Meta Pixel"""
    
    def __init__(self):
        self.pixel_id = os.getenv("META_PIXEL_ID", "")
        self.capi_token = os.getenv("META_CAPI_TOKEN", "")
        self.api_version = "v18.0"
        
    def track_event(self, event_name: str, user_data: Dict, event_data: Optional[Dict] = None) -> bool:
        """
        Envía evento a Meta Pixel Conversions API
        
        Args:
            event_name: Nombre del evento (Purchase, Subscribe, Lead, etc.)
            user_data: Datos del usuario (email, phone, fbc, fbp, etc.)
            event_data: Datos adicionales del evento (value, currency, etc.)
        """
        if not self.pixel_id or not self.capi_token:
            logger.warning("Meta Pixel no configurado (META_PIXEL_ID o META_CAPI_TOKEN faltantes)")
            return False
        
        url = f"https://graph.facebook.com/{self.api_version}/{self.pixel_id}/events"
        
        payload = {
            "data": [{
                "event_name": event_name,
                "event_time": int(__import__("time").time()),
                "user_data": user_data,
                "event_source_url": "https://www.fanvue.com/utopiafinca",
                "action_source": "website"
            }]
        }
        
        if event_data:
            payload["data"][0].update(event_data)
        
        headers = {
            "Authorization": f"Bearer {self.capi_token}",
            "Content-Type": "application/json"
        }
        
        try:
            response = requests.post(url, json=payload, headers=headers, timeout=10)
            response.raise_for_status()
            result = response.json()
            
            if result.get("events_received", 0) > 0:
                logger.info(f"✅ Evento {event_name} rastreado en Meta Pixel")
                return True
            else:
                logger.warning(f"⚠️ Evento {event_name} no fue recibido por Meta Pixel")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error rastreando evento en Meta Pixel: {e}")
            return False
    
    def track_subscription(self, email: str, value: float, currency: str = "USD") -> bool:
        """Rastrea una suscripción nueva"""
        user_data = {
            "em": self._hash_email(email) if email else None
        }
        
        event_data = {
            "value": value,
            "currency": currency
        }
        
        return self.track_event("Subscribe", user_data, event_data)
    
    def track_purchase(self, email: str, value: float, currency: str = "USD", content_type: Optional[str] = None) -> bool:
        """Rastrea una compra"""
        user_data = {
            "em": self._hash_email(email) if email else None
        }
        
        event_data = {
            "value": value,
            "currency": currency
        }
        
        if content_type:
            event_data["content_type"] = content_type
        
        return self.track_event("Purchase", user_data, event_data)
    
    def track_lead(self, email: str, source: str = "fanvue") -> bool:
        """Rastrea un lead (nuevo seguidor/interés)"""
        user_data = {
            "em": self._hash_email(email) if email else None
        }
        
        event_data = {
            "content_name": source
        }
        
        return self.track_event("Lead", user_data, event_data)
    
    def _hash_email(self, email: str) -> str:
        """Hashea el email para privacidad (SHA256)"""
        import hashlib
        return hashlib.sha256(email.lower().encode()).hexdigest()
