"""
Cliente de API de Fanvue con OAuth 2.0
Integración completa para automatizar respuestas y gestionar contenido
"""
import os
import sys
import logging
import requests
from typing import Optional, Dict, List, Any
from datetime import datetime, timedelta
import json

# Agregar el directorio raíz del proyecto al path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from dotenv import load_dotenv
load_dotenv()

logger = logging.getLogger(__name__)

class FanvueAPI:
    """Cliente para interactuar con la API de Fanvue"""
    
    # Según documentación oficial: https://api.fanvue.com
    BASE_URL = os.getenv("API_BASE_URL", "https://api.fanvue.com")
    MCP_URL = os.getenv("MCP_SERVER_URL", "http://127.0.0.1:8080")
    API_VERSION = "2025-06-26"  # Versión de API actualizada
    
    def __init__(self):
        self.client_id = os.getenv("FANVUE_CLIENT_ID", "71ae72fa-e081-4ea7-b04e-3f6c1b40e7b8")
        self.client_secret = os.getenv("FANVUE_CLIENT_SECRET", "")
        self.access_token = None
        self.token_expires_at = None
        self.webhook_secret = os.getenv("FANVUE_WEBHOOK_SECRET", "")
        self.use_mcp = os.getenv("USE_FANVUE_MCP", "true").lower() == "true"
        
    def get_access_token(self) -> Optional[str]:
        """Obtiene o renueva el token de acceso OAuth"""
        # Si usamos MCP, el token lo gestiona el servidor MCP
        if self.use_mcp:
            return "MCP_MANAGED"

        # Si tenemos un token válido, usarlo
        if self.access_token and self.token_expires_at:
            if datetime.now() < self.token_expires_at:
                return self.access_token
        
        # Obtener nuevo token
        try:
            token = os.getenv("FANVUE_ACCESS_TOKEN")
            if token:
                self.access_token = token
                self.token_expires_at = datetime.now() + timedelta(hours=1)
                return token
            
            logger.warning("FANVUE_ACCESS_TOKEN no configurado. Intentando usar MCP...")
            self.use_mcp = True
            return "MCP_MANAGED"
            
        except Exception as e:
            logger.error(f"Error obteniendo token de Fanvue: {e}")
            return None
    
    def _make_request(self, method: str, endpoint: str, data: Optional[Dict] = None, params: Optional[Dict] = None) -> Optional[Dict]:
        """Hace una petición a la API de Fanvue o vía MCP"""
        token = self.get_access_token()
        
        if self.use_mcp:
            # Redirigir al servidor MCP
            url = f"{self.MCP_URL}{endpoint}"
            headers = {
                "Content-Type": "application/json",
                "X-Fanvue-API-Version": self.API_VERSION
            }
        else:
            if not token:
                logger.error("No se pudo obtener token de acceso")
                return None
            url = f"{self.BASE_URL}{endpoint}"
            headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
                "X-Fanvue-API-Version": self.API_VERSION
            }
        
        try:
            if method == "GET":
                response = requests.get(url, headers=headers, params=params, timeout=10)
            elif method == "POST":
                response = requests.post(url, headers=headers, json=data, timeout=10)
            elif method == "PUT":
                response = requests.put(url, headers=headers, json=data, timeout=10)
            elif method == "DELETE":
                response = requests.delete(url, headers=headers, timeout=10)
            else:
                logger.error(f"Método HTTP no soportado: {method}")
                return None
            
            response.raise_for_status()
            return response.json() if response.content else {}
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error en petición a Fanvue API: {e}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"Response: {e.response.text}")
            return None
    
    # ========== CHAT / MENSAJES ==========
    
    def send_message(self, chat_id: str, text: str, media_url: Optional[str] = None) -> bool:
        """
        Envía un mensaje en un chat de Fanvue
        
        Args:
            chat_id: UUID del chat o del usuario
            text: Texto del mensaje
            media_url: URL opcional de media
        
        Returns:
            True si se envió correctamente
        """
        # Según documentación, el endpoint puede ser /chats/{chatId}/messages
        # o /messages con chatId en el body
        data = {
            "text": text
        }
        if media_url:
            data["mediaUrl"] = media_url
        
        # Intentar endpoint con chat_id en la URL
        result = self._make_request("POST", f"/chats/{chat_id}/messages", data=data)
        if not result:
            # Fallback: intentar con endpoint alternativo
            data["chatId"] = chat_id
            result = self._make_request("POST", "/messages", data=data)
        
        if result:
            logger.info(f"Mensaje enviado a chat {chat_id} en Fanvue")
            return True
        return False
    
    def get_chat_messages(self, chat_id: str, limit: int = 50) -> List[Dict]:
        """Obtiene mensajes de un chat"""
        result = self._make_request("GET", f"/chat/{chat_id}/messages", params={"limit": limit})
        return result.get("messages", []) if result else []
    
    def get_chat_media(self, user_uuid: str, cursor: Optional[str] = None, 
                       media_type: Optional[str] = None, limit: int = 20) -> Dict[str, Any]:
        """
        Obtiene media compartida en un chat con un usuario específico
        
        Args:
            user_uuid: UUID del usuario con quien se compartió el media
            cursor: Cursor para paginación (obtener de nextCursor de respuesta anterior)
            media_type: Filtrar por tipo (image, video, audio, document)
            limit: Número de items a retornar (1-50, default: 20)
        
        Returns:
            Dict con:
            - data: Lista de items de media
            - nextCursor: Cursor para la siguiente página (None si no hay más)
        """
        params = {
            "limit": min(max(limit, 1), 50)  # Asegurar entre 1 y 50
        }
        
        if cursor:
            params["cursor"] = cursor
        
        if media_type:
            params["mediaType"] = media_type
        
        result = self._make_request("GET", f"/chats/{user_uuid}/media", params=params)
        if result:
            return {
                "data": result.get("data", []),
                "nextCursor": result.get("nextCursor")
            }
        return {"data": [], "nextCursor": None}
    
    def create_chat(self, user_uuid: str) -> bool:
        """
        Crea un nuevo chat con un usuario
        
        Args:
            user_uuid: UUID del usuario con quien crear el chat
        
        Returns:
            True si se creó correctamente
        """
        data = {
            "userUuid": user_uuid
        }
        
        result = self._make_request("POST", "/chats", data=data)
        if result:
            logger.info(f"Chat creado con usuario {user_uuid} en Fanvue")
            return True
        return False
    
    def update_chat(self, user_uuid: str, is_read: Optional[bool] = None, 
                    is_muted: Optional[bool] = None, nickname: Optional[str] = None) -> bool:
        """
        Actualiza propiedades de un chat (marcar como leído, silenciar, cambiar apodo)
        
        Args:
            user_uuid: UUID del usuario con quien es el chat
            is_read: Marcar chat como leído (True) o no leído (False)
            is_muted: Silenciar chat (True) o activar notificaciones (False)
            nickname: Apodo personalizado para el usuario (máximo 30 caracteres)
        
        Returns:
            True si se actualizó correctamente
        
        Nota: Puedes actualizar una o más propiedades a la vez.
        """
        data = {}
        
        if is_read is not None:
            data["isRead"] = is_read
        
        if is_muted is not None:
            data["isMuted"] = is_muted
        
        if nickname is not None:
            # Limitar a 30 caracteres según documentación
            if len(nickname) > 30:
                logger.warning(f"Nickname truncado de {len(nickname)} a 30 caracteres")
                nickname = nickname[:30]
            data["nickname"] = nickname
        
        if not data:
            logger.warning("No se proporcionaron propiedades para actualizar")
            return False
        
        # El endpoint retorna 204 No Content, así que verificamos el status code
        token = self.get_access_token()
        if not token:
            logger.error("No se pudo obtener token de acceso")
            return False
        
        url = f"{self.BASE_URL}/chats/{user_uuid}"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "X-Fanvue-API-Version": self.API_VERSION
        }
        
        try:
            response = requests.patch(url, headers=headers, json=data, timeout=10)
            response.raise_for_status()
            logger.info(f"Chat actualizado para usuario {user_uuid} en Fanvue")
            return True
        except requests.exceptions.RequestException as e:
            logger.error(f"Error actualizando chat en Fanvue API: {e}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"Response: {e.response.text}")
            return False
    
    def get_chats(self, page: int = 1, size: int = 15, filter_types: Optional[List[str]] = None, 
                  search: Optional[str] = None, sort_by: Optional[str] = None) -> Dict[str, Any]:
        """
        Obtiene lista de chats con paginación y filtros
        
        Args:
            page: Número de página (default: 1)
            size: Tamaño de página 1-50 (default: 15)
            filter_types: Lista de filtros (unread, online, subscribed_to, etc.)
            search: Término de búsqueda por nombre/handle
            sort_by: Ordenamiento (most_recent_messages, online_now, most_unanswered_chats)
        
        Returns:
            Dict con 'data' (lista de chats) y 'pagination'
        """
        params = {
            "page": page,
            "size": size
        }
        
        if filter_types:
            for filter_type in filter_types:
                params["filter"] = filter_type  # Se puede repetir el parámetro
        
        if search:
            params["search"] = search
        
        if sort_by:
            params["sortBy"] = sort_by
        
        result = self._make_request("GET", "/chats", params=params)
        if result:
            return {
                "data": result.get("data", []),
                "pagination": result.get("pagination", {})
            }
        return {"data": [], "pagination": {}}
    
    def get_unread_counts(self) -> Optional[Dict[str, Any]]:
        """
        Obtiene conteo de chats no leídos, mensajes no leídos y notificaciones
        
        Returns:
            Dict con:
            - unreadChatsCount: Número de conversaciones con mensajes no leídos
            - unreadMessagesCount: Total de mensajes no leídos en todos los chats
            - unreadNotifications: Dict con conteos por tipo de notificación
                - newFollower, newPostComment, newPostLike, newPurchase,
                  newSubscriber, newTip, newPromotion
        """
        result = self._make_request("GET", "/chats/unread")
        if result:
            return {
                "unreadChatsCount": result.get("unreadChatsCount", 0),
                "unreadMessagesCount": result.get("unreadMessagesCount", 0),
                "unreadNotifications": result.get("unreadNotifications", {})
            }
        return None
    
    def get_online_statuses(self, user_uuids: List[str]) -> Dict[str, Dict[str, Any]]:
        """
        Obtiene el estado en línea y última vez visto de múltiples usuarios
        
        Args:
            user_uuids: Lista de UUIDs de usuarios (máximo 100)
        
        Returns:
            Dict donde las claves son los UUIDs y los valores contienen:
            - isOnline: bool - Si el usuario está en línea
            - lastSeenAt: str o None - Última vez que se vio en línea (UTC)
        
        Nota: Usuarios que deshabilitaron visibilidad en línea siempre aparecerán
        como offline sin timestamp de última vez visto.
        """
        # Limitar a máximo 100 UUIDs
        if len(user_uuids) > 100:
            logger.warning(f"Se recibieron {len(user_uuids)} UUIDs, limitando a 100")
            user_uuids = user_uuids[:100]
        
        data = {
            "userUuids": user_uuids
        }
        
        result = self._make_request("POST", "/chats/statuses", data=data)
        if result:
            return result
        return {}
    
    def get_current_user(self) -> Optional[Dict]:
        """Obtiene información del usuario actual autenticado"""
        return self._make_request("GET", "/users/me")
    
    # ========== CREATOR / CREADOR ==========
    
    def get_creator_info(self) -> Optional[Dict]:
        """Obtiene información del creador (usando endpoint de usuario actual)"""
        # Según documentación, usar /users/me para obtener info del creador
        user_info = self.get_current_user()
        if user_info and user_info.get("isCreator"):
            return user_info
        return user_info
    
    def get_earnings(self, period: str = "24h") -> Optional[Dict]:
        """Obtiene ganancias (24h, 7d, 30d, all)"""
        return self._make_request("GET", f"/creator/earnings", params={"period": period})
    
    # ========== FANS / SEGUIDORES ==========
    
    def get_subscribers(self) -> List[Dict]:
        """Obtiene lista de suscriptores"""
        result = self._make_request("GET", "/fan/subscribers")
        return result.get("subscribers", []) if result else []
    
    def get_followers(self) -> List[Dict]:
        """Obtiene lista de seguidores"""
        result = self._make_request("GET", "/fan/followers")
        return result.get("followers", []) if result else []
    
    # ========== MEDIA / CONTENIDO ==========
    
    def upload_media(self, file_path: str, caption: Optional[str] = None) -> Optional[Dict]:
        """Sube un archivo de media a Fanvue"""
        token = self.get_access_token()
        if not token:
            return None
        
        url = f"{self.BASE_URL}/media/upload"
        headers = {"Authorization": f"Bearer {token}"}
        
        try:
            with open(file_path, 'rb') as f:
                files = {'file': f}
                data = {}
                if caption:
                    data['caption'] = caption
                
                response = requests.post(url, headers=headers, files=files, data=data, timeout=30)
                response.raise_for_status()
                return response.json()
        except Exception as e:
            logger.error(f"Error subiendo media a Fanvue: {e}")
            return None
    
    def create_post(self, text: str, media_ids: Optional[List[str]] = None) -> Optional[Dict]:
        """Crea un post en Fanvue"""
        data = {"text": text}
        if media_ids:
            data["mediaIds"] = media_ids
        
        return self._make_request("POST", "/post", data=data)
    
    # ========== WEBHOOKS ==========
    
    def verify_webhook_signature(self, payload: str, signature_header: str) -> bool:
        """
        Verifica la firma del webhook según la documentación 2025:
        Formato: t=<timestamp>,v0=<signature>
        HMAC-SHA256(secret, timestamp + "." + body)
        """
        if not signature_header:
            logger.warning("No se recibió header X-Fanvue-Signature")
            return False

        secret = os.getenv("FANVUE_WEBHOOK_SECRET") or self.webhook_secret
        if not secret:
            logger.warning("FANVUE_WEBHOOK_SECRET no configurado. Permitiendo paso por ahora.")
            return True

        try:
            # Parsear header: t=12345678,v0=abcdef...
            parts = {}
            for part in signature_header.split(','):
                if '=' in part:
                    k, v = part.split('=', 1)
                    parts[k.strip()] = v.strip()
            
            timestamp = parts.get('t')
            received_signature = parts.get('v0')

            if not timestamp or not received_signature:
                return False

            # Verificar tolerancia de tiempo (5 minutos)
            import time
            current_time = int(time.time())
            if abs(current_time - int(timestamp)) > 300:
                logger.warning("Webhook timestamp fuera de tolerancia")
                return False

            # Calcular firma esperada: {timestamp}.{body}
            import hmac
            import hashlib
            signed_payload = f"{timestamp}.{payload}"
            expected_signature = hmac.new(
                secret.encode('utf-8'),
                signed_payload.encode('utf-8'),
                hashlib.sha256
            ).hexdigest()

            # Comparación segura
            return hmac.compare_digest(expected_signature, received_signature)
            
        except Exception as e:
            logger.error(f"Error verificando firma de webhook: {e}")
            return False
