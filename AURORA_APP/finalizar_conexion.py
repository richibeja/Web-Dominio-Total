import os
import requests
from dotenv import load_dotenv
from pathlib import Path

# Cargar .env
env_path = Path(__file__).parent / ".env"
load_dotenv(env_path)

CLIENT_ID = os.getenv("FANVUE_CLIENT_ID")
CLIENT_SECRET = os.getenv("FANVUE_CLIENT_SECRET")
REDIRECT_URI = "http://localhost:4000/callback"

def exchange_code_for_token(auth_code):
    # Leer el verifier guardado en el paso anterior
    if not os.path.exists("fanvue_temp_verifier.txt"):
        print("❌ ERROR: No se encontró el verifier temporal. Ejecuta conectar_fanvue.py primero.")
        return

    with open("fanvue_temp_verifier.txt", "r") as f:
        lines = f.readlines()
        code_verifier = lines[0].strip()

    print("Intercambiando codigo por tokens...")
    
    url = "https://auth.fanvue.com/oauth2/token"
    
    import base64
    auth_str = f"{CLIENT_ID}:{CLIENT_SECRET}"
    encoded_auth = base64.b64encode(auth_str.encode()).decode()

    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "Authorization": f"Basic {encoded_auth}"
    }

    data = {
        "grant_type": "authorization_code",
        "code": auth_code,
        "redirect_uri": REDIRECT_URI,
        "code_verifier": code_verifier,
    }
    
    try:
        response = requests.post(url, data=data, headers=headers)

        if response.status_code == 200:
            tokens = response.json()
            # Guardar tokens de forma segura
            token_path = Path(__file__).parent / "data" / "fanvue_tokens.json"
            token_path.parent.mkdir(parents=True, exist_ok=True)
            
            import json
            with open(token_path, "w") as tf:
                json.dump(tokens, tf, indent=2)
            
            print("\n" + "="*60)
            print("CONEXION EXITOSA CON FANVUE!")
            print("="*60)
            print(f"Los tokens se han guardado en: {token_path}")
            print("Ahora Aurora puede leer tus mensajes y actuar en tu nombre.")
            print("="*60 + "\n")

            
            # Limpiar archivo temporal
            os.remove("fanvue_temp_verifier.txt")
        else:
            print(f"❌ ERROR en el intercambio: {response.status_code}")
            print(response.text)
    except Exception as e:
        print(f"❌ Error crítico: {e}")

if __name__ == "__main__":
    import sys
    # Extraer el código de la URL si se pasa la URL completa
    query = sys.argv[1] if len(sys.argv) > 1 else ""
    if "code=" in query:
        from urllib.parse import urlparse, parse_qs
        parsed = urlparse(query)
        auth_code = parse_qs(parsed.query).get('code', [None])[0]
    else:
        auth_code = query

    if not auth_code:
        print("Uso: py finalizar_conexion.py [CODIGO_O_URL_COMPLETA]")
    else:
        exchange_code_for_token(auth_code)
