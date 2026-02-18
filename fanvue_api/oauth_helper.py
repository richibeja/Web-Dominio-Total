"""
Helper para obtener Access Token de Fanvue OAuth
Facilita el proceso de autenticación
"""
import os
import sys
import webbrowser
import requests
from urllib.parse import urlparse, parse_qs

# Configurar encoding para Windows
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Agregar el directorio raíz del proyecto al path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from dotenv import load_dotenv
load_dotenv()

# Configuración OAuth según documentación oficial de Fanvue
OAUTH_ISSUER_BASE_URL = os.getenv("OAUTH_ISSUER_BASE_URL", "https://auth.fanvue.com")
API_BASE_URL = os.getenv("API_BASE_URL", "https://api.fanvue.com")
CLIENT_ID = os.getenv("FANVUE_CLIENT_ID", "71ae72fa-e081-4ea7-b04e-3f6c1b40e7b8")
REDIRECT_URI = os.getenv("FANVUE_REDIRECT_URI", "https://neaped-rhomboidally-briella.ngrok-free.dev/oauth/fanvue/callback")
SCOPES = "read:chat write:chat read:creator read:fan read:insights read:media read:post read:self write:creator write:media write:post"

def get_authorization_url():
    """Genera la URL de autorización OAuth según documentación oficial"""
    # Según la documentación, la URL base es auth.fanvue.com
    base_url = f"{OAUTH_ISSUER_BASE_URL}/oauth/authorize"
    params = {
        "client_id": CLIENT_ID,
        "redirect_uri": REDIRECT_URI,
        "response_type": "code",
        "scope": SCOPES
    }
    
    url = f"{base_url}?client_id={CLIENT_ID}&redirect_uri={REDIRECT_URI}&response_type=code&scope={SCOPES}"
    return url

def exchange_code_for_token(authorization_code: str, client_secret: str):
    """Intercambia el código de autorización por un access token"""
    # Según la documentación, el token endpoint está en auth.fanvue.com
    token_url = f"{OAUTH_ISSUER_BASE_URL}/oauth/token"
    
    data = {
        "grant_type": "authorization_code",
        "code": authorization_code,
        "redirect_uri": REDIRECT_URI,
        "client_id": CLIENT_ID,
        "client_secret": client_secret
    }
    
    try:
        response = requests.post(token_url, data=data, timeout=10)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"❌ Error obteniendo token: {e}")
        if hasattr(e, 'response') and e.response:
            print(f"Response: {e.response.text}")
        return None

def main():
    print("=" * 60)
    print("🔐 OBTENER ACCESS TOKEN DE FANVUE")
    print("=" * 60)
    print()
    
    # Paso 1: Obtener Client Secret
    client_secret = os.getenv("FANVUE_CLIENT_SECRET")
    if not client_secret:
        print("⚠️  FANVUE_CLIENT_SECRET no encontrado en .env")
        print()
        client_secret = input("Ingresa tu Client Secret de Fanvue: ").strip()
        if not client_secret:
            print("❌ Client Secret requerido")
            return
    
    # Paso 2: Generar URL de autorización
    auth_url = get_authorization_url()
    print("📋 Paso 1: Autorizar aplicación")
    print(f"URL: {auth_url}")
    print()
    print("¿Quieres abrir esta URL en el navegador? (s/n): ", end="")
    respuesta = input().strip().lower()
    
    if respuesta == 's':
        webbrowser.open(auth_url)
        print("✅ URL abierta en navegador")
    else:
        print("📋 Copia esta URL y ábrela en tu navegador:")
        print(auth_url)
    
    print()
    print("=" * 60)
    print("📋 Paso 2: Obtener código de autorización")
    print("=" * 60)
    print()
    print("Después de autorizar, serás redirigido a una URL como:")
    print(f"{REDIRECT_URI}?code=ABC123...")
    print()
    print("Copia el código de la URL (la parte después de 'code=')")
    print()
    
    authorization_code = input("Pega el código de autorización aquí: ").strip()
    
    if not authorization_code:
        print("❌ Código de autorización requerido")
        return
    
    # Paso 3: Intercambiar código por token
    print()
    print("🔄 Intercambiando código por access token...")
    token_data = exchange_code_for_token(authorization_code, client_secret)
    
    if token_data and "access_token" in token_data:
        access_token = token_data["access_token"]
        refresh_token = token_data.get("refresh_token", "")
        expires_in = token_data.get("expires_in", 3600)
        
        print()
        print("=" * 60)
        print("✅ TOKEN OBTENIDO EXITOSAMENTE")
        print("=" * 60)
        print()
        print(f"Access Token: {access_token[:50]}...")
        print(f"Expira en: {expires_in} segundos")
        print()
        print("📝 Agrega esto a tu archivo .env:")
        print()
        print(f"FANVUE_ACCESS_TOKEN={access_token}")
        if refresh_token:
            print(f"FANVUE_REFRESH_TOKEN={refresh_token}")
        print()
        print("✅ ¡Listo! Ahora puedes usar el bot de Fanvue")
        
    else:
        print()
        print("❌ Error obteniendo token")
        print("Verifica:")
        print("  1. Que el código de autorización sea correcto")
        print("  2. Que el Client Secret sea correcto")
        print("  3. Que la redirect_uri coincida con la configurada en Fanvue")

if __name__ == "__main__":
    main()
