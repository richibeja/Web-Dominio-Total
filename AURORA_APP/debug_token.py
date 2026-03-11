import os
import requests
import base64
from dotenv import load_dotenv
from pathlib import Path

# Cargar .env
env_path = Path(__file__).parent / ".env"
load_dotenv(env_path)

# IMPORTANTE: Estos deben ser los mismos que usaste en la AUTHORIZATION URL
CLIENT_ID = os.getenv("FANVUE_CLIENT_ID")
CLIENT_SECRET = os.getenv("FANVUE_CLIENT_SECRET")
REDIRECT_URI = "http://localhost:4000/callback"

def simple_exchange(auth_code):
    # Intentar obtener el code_verifier del archivo temporal
    if not os.path.exists("fanvue_temp_verifier.txt"):
        print("❌ ERROR: No se encontró fanvue_temp_verifier.txt")
        return

    with open("fanvue_temp_verifier.txt", "r") as f:
        code_verifier = f.readline().strip()

    print(f"DEBUG: CLIENT_ID={CLIENT_ID}")
    print(f"DEBUG: Using Verifier={code_verifier}")
    
    url = "https://auth.fanvue.com/oauth2/token"
    
    # Preparamos el Basic Auth header
    auth_str = f"{CLIENT_ID}:{CLIENT_SECRET}"
    encoded_auth = base64.b64encode(auth_str.encode()).decode()
    
    headers = {
        "Authorization": f"Basic {encoded_auth}",
        "Content-Type": "application/x-www-form-urlencoded"
    }

    data = {
        "grant_type": "authorization_code",
        "code": auth_code,
        "redirect_uri": REDIRECT_URI,
        "code_verifier": code_verifier,
        "client_id": CLIENT_ID # Algunos proveedores lo requieren aun con Basic Auth
    }
    
    print("Enviando POST a:", url)
    resp = requests.post(url, data=data, headers=headers)
    print("Status:", resp.status_code)
    print("Response:", resp.text)

if __name__ == "__main__":
    import sys
    code = sys.argv[1] if len(sys.argv) > 1 else "ory_ac_Njl-R5FHhF8aTjIkdnEV3_U4FMlbKTsjLWZxTaTyHZA.p-NX6Ny8Xde_3Ukf3JlZR84AnMgLrK1aKMGuvPj0tqg"
    simple_exchange(code)
