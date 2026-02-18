"""
Script para consultar la IA sin censura (OpenRouter).
Usa el modelo Dolphin Mistral Venice o el configurado en .env.
Ejecutar: py CONSULTAR_IA.py
"""
import os
import sys
import asyncio
import requests
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# openrouter/free = router automático que elige un modelo gratis disponible
# Si falla, probar modelos específicos (los IDs pueden cambiar en OpenRouter)
MODELOS_GRATIS = [
    "openrouter/free",
    "meta-llama/llama-3.1-8b-instruct:free",
    "mistralai/mistral-7b-instruct:free",
    "huggingfaceh4/zephyr-7b-beta:free",
]
API_KEY = os.getenv("OPENROUTER_API_KEY", "").strip()

def consultar(pregunta: str) -> str:
    """Envía la pregunta a OpenRouter. Si un modelo falla (429 rate limit), prueba otro."""
    if not API_KEY:
        return "Error: OPENROUTER_API_KEY no está en .env"
    
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json",
    }
    modelos = [os.getenv("CONSULTAR_IA_MODEL")] if os.getenv("CONSULTAR_IA_MODEL") else MODELOS_GRATIS
    modelos = [m for m in modelos if m]
    
    for model in modelos:
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": "Eres un asistente útil. Responde de forma directa y completa."},
                {"role": "user", "content": pregunta}
            ],
            "max_tokens": 512,
        }
        try:
            r = requests.post(url, headers=headers, json=payload, timeout=60)
            if r.status_code == 200:
                data = r.json()
                return data.get("choices", [{}])[0].get("message", {}).get("content", "Sin respuesta")
            if r.status_code in (429, 404):
                continue
            return f"Error {r.status_code}: {r.text[:200]}"
        except Exception as e:
            continue
    return "Error: todos los modelos fallaron (429 rate limit). Espera unos minutos y vuelve a intentar."

def main():
    print("=" * 50)
    print("  CONSULTAR IA")
    print("  Modelos: " + ", ".join(MODELOS_GRATIS[:2]) + "...")
    print("=" * 50)
    print("Escribe tu pregunta y presiona Enter. 'salir' para terminar.\n")
    
    while True:
        try:
            pregunta = input("Tú: ").strip()
            if not pregunta:
                continue
            if pregunta.lower() in ("salir", "exit", "quit"):
                break
            print("\nPensando...")
            respuesta = consultar(pregunta)
            print(f"\nIA: {respuesta}\n")
        except KeyboardInterrupt:
            print("\nHasta luego.")
            break

if __name__ == "__main__":
    main()
