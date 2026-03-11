import os
import json
import base64
import requests
import logging
from pathlib import Path
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

class FanvueUtils:
    def __init__(self):
        self.app_dir = Path(__file__).resolve().parent
        self.root_dir = self.app_dir.parent
        load_dotenv(self.app_dir / ".env")
        
        self.client_id = os.getenv("FANVUE_CLIENT_ID")
        self.client_secret = os.getenv("FANVUE_CLIENT_SECRET")
        self.token_path = self.app_dir / "data" / "fanvue_tokens.json"
        self.api_version = "2025-06-26"

    def load_tokens(self):
        if not self.token_path.exists():
            return None
        try:
            with open(self.token_path, "r") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error cargando tokens: {e}")
            return None

    def save_tokens(self, tokens):
        self.token_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            with open(self.token_path, "w") as f:
                json.dump(tokens, f, indent=2)
            return True
        except Exception as e:
            logger.error(f"Error guardando tokens: {e}")
            return False

    def refresh_token(self):
        tokens = self.load_tokens()
        if not tokens or "refresh_token" not in tokens:
            logger.error("No hay refresh_token disponible")
            return False

        url = "https://auth.fanvue.com/oauth2/token"
        
        auth_str = f"{self.client_id}:{self.client_secret}"
        encoded_auth = base64.b64encode(auth_str.encode()).decode()

        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "Authorization": f"Basic {encoded_auth}"
        }

        data = {
            "grant_type": "refresh_token",
            "refresh_token": tokens["refresh_token"]
        }

        try:
            response = requests.post(url, data=data, headers=headers)
            if response.status_code == 200:
                new_tokens = response.json()
                # Fanvue a veces no devuelve un nuevo refresh_token, mantenemos el viejo si es así
                if "refresh_token" not in new_tokens:
                    new_tokens["refresh_token"] = tokens["refresh_token"]
                self.save_tokens(new_tokens)
                logger.info("✅ Token de Fanvue refrescado exitosamente")
                return True
            else:
                logger.error(f"❌ Error al refrescar token: {response.status_code}")
                logger.error(response.text)
                return False
        except Exception as e:
            logger.error(f"Error crítico en refresh_token: {e}")
            return False

    def get_headers(self, force_refresh=False):
        tokens = self.load_tokens()
        if not tokens:
            return None
        
        access_token = tokens.get("access_token")
        return {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
            "X-Fanvue-API-Version": self.api_version
        }

    def api_request(self, method, endpoint, **kwargs):
        """Realiza una petición a la API con manejo de 401 automático."""
        url = f"https://api.fanvue.com{endpoint}" if not endpoint.startswith("http") else endpoint
        headers = self.get_headers()
        
        if not headers:
            logger.error(f"⚠️ HEADERS VACÍOS en {method} {endpoint}.load_tokens() probablemente falló.")
            return None

        try:
            response = requests.request(method, url, headers=headers, **kwargs)
            
            if response.status_code == 401:
                logger.info("Token expirado, intentando refrescar...")
                if self.refresh_token():
                    headers = self.get_headers()
                    response = requests.request(method, url, headers=headers, **kwargs)
                else:
                    return response # Devolvemos el 401 si falla el refresh
            
            return response
        except Exception as e:
            msg = f"❌ ERROR CRÍTICO en api_request {method} {endpoint}: {str(e)}"
            logger.error(msg)
            print(msg, flush=True) # Direct update to console
            import traceback
            traceback.print_exc()
            return None

if __name__ == "__main__":
    utils = FanvueUtils()
    if utils.refresh_token():
        print("Refresco exitoso")
    else:
        print("Fallo el refresco")
