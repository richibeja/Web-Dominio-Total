import os, sys, hashlib, base64, secrets
from urllib.parse import urlencode
from dotenv import load_dotenv
from pathlib import Path

# Forzar codificación UTF-8 para evitar errores con emojis en Windows
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# Cargar .env
env_path = Path(__file__).parent / ".env"
load_dotenv(env_path)

CLIENT_ID = os.getenv("FANVUE_CLIENT_ID")
REDIRECT_URI = os.getenv("FANVUE_REDIRECT_URI", "http://localhost:4000/callback")

def generate_pkce():
    # Verifier: Código aleatorio seguro
    code_verifier = secrets.token_urlsafe(64)
    
    # Challenge: Hash SHA256 del verifier codificado en Base64URL
    sha256_hash = hashlib.sha256(code_verifier.encode('utf-8')).digest()
    code_challenge = base64.urlsafe_b64encode(sha256_hash).decode('utf-8').replace('=', '')
    
    # State: Código aleatorio para evitar ataques CSRF (Fanvue exige min 8 caracteres)
    state = secrets.token_urlsafe(16)
    
    return code_verifier, code_challenge, state

def get_auth_url(challenge, state):
    params = {
        "client_id": CLIENT_ID,
        "redirect_uri": REDIRECT_URI,
        "response_type": "code",
        "scope": "openid offline_access offline read:self read:chat write:chat write:post",
        "code_challenge": challenge,
        "code_challenge_method": "S256",
        "state": state
    }
    base_url = "https://auth.fanvue.com/oauth2/auth"
    # Usar urlencode para asegurar que todo esté codificado correctamente
    return f"{base_url}?{urlencode(params)}"

if __name__ == "__main__":
    if not CLIENT_ID:
        print("❌ ERROR: No se encontró FANVUE_CLIENT_ID en el archivo .env")
    else:
        verifier, challenge, state = generate_pkce()
        auth_url = get_auth_url(challenge, state)
        
        # Guardar el verifier y state temporalmente para el siguiente paso
        with open("fanvue_temp_verifier.txt", "w") as f:
            f.write(f"{verifier}\n{state}")

            
        print("-" * 60)
        print("CONEXION OFICIAL FANVUE x AURORA")
        print("-" * 60)
        print("\n1. Copia y pega este link en tu navegador:")
        print(f"\n{auth_url}")
        print("\n" + "-"*60)
        print("2. Dale a 'Autorizar' en Fanvue.")
        print("3. Serás redirigido a una página que dice 'No se puede conectar' (es normal).")
        print("4. COPIA LA URL de esa página y pégamela aquí.")
        print("="*60 + "\n")
