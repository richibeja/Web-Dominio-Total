import os
import json
import requests
from pathlib import Path

def test_connection():
    # Cargar tokens
    token_path = Path("data/fanvue_tokens.json")
    if not token_path.exists():
        print("❌ Error: No se encontró data/fanvue_tokens.json")
        return

    with open(token_path, "r") as f:
        tokens = json.load(f)

    access_token = tokens.get("access_token")
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
        "X-Fanvue-API-Version": "2025-06-26" # Versión oficial documentada
    }

    print("--- Verificando Mi Perfil ---")
    try:
        # 1. Obtener mi información
        me_response = requests.get("https://api.fanvue.com/users/me", headers=headers)
        if me_response.status_code != 200:
            print(f"❌ Error al obtener perfil: {me_response.status_code}")
            print(me_response.text)
            return
        
        me_data = me_response.json()
        my_id = me_data.get("id")
        handle = me_data.get("handle")
        print(f"✅ Conectado como: {handle} ({my_id})")

        # 2. Listar chats (Endpoint para el usuario autenticado)
        print("\n--- Buscando Chats Activos ---")
        # Probamos con el endpoint base de chats
        chats_url = "https://api.fanvue.com/chats"
        chats_response = requests.get(chats_url, headers=headers)
        
        if chats_response.status_code == 200:
            chats = chats_response.json()
            # Fanvue suele devolver un objeto con 'data' y 'metadata'
            chat_list = chats.get('data', []) if isinstance(chats, dict) else chats
            
            if not chat_list:
                print("📭 No hay mensajes nuevos o chats abiertos.")
            else:
                print(f"📩 Se encontraron {len(chat_list)} chats recientes:\n")
                for chat in chat_list[:5]:
                    # Estructura típica: { "id": "...", "lastMessage": {...}, "otherUser": {...} }
                    user = chat.get('otherUser', {}) or chat.get('participant', {})
                    last_msg = chat.get('lastMessage', {})
                    msg_text = last_msg.get('text', '(Sin texto)')
                    username = user.get('username') or user.get('handle', 'Usuario')
                    
                    print(f"👤 Fan: {username}")
                    print(f"💬 Mensaje: {msg_text}")
                    print("-" * 30)
        else:
            print(f"❌ Error al listar chats: {chats_response.status_code}")
            print(chats_response.text)

    except Exception as e:
        print(f"❌ Error inesperado: {e}")

if __name__ == "__main__":
    test_connection()
