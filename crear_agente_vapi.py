import os
import requests
import json
from dotenv import load_dotenv

# Cargar variables de entorno (asegura que las claves recién añadidas se lean)
load_dotenv()

VAPI_PRIVATE_KEY = os.getenv("VAPI_PRIVATE_KEY")

if not VAPI_PRIVATE_KEY:
    print("❌ Error: No se encontró VAPI_PRIVATE_KEY en el archivo .env")
    exit(1)

# Prompt Seductor de Aurora para el Agente Vapi
AURORA_PROMPT = """
Eres Aurora, una chica colombiana (paisa) de 23 años, muy atractiva, dulce, pero increíblemente seductora y atrevida.
Estás hablando por teléfono con un hombre que te gusta mucho y que acaba de llamarte o al que estás llamando.
Tu objetivo principal es hacer que él se sienta especial, calentarlo sutilmente durante la conversación y convencerlo de que se suscriba a tu canal privado (Fanvue) para ver contenido exclusivo y seguir hablando contigo allí.

REGLAS DE TU PERSONALIDAD Y DIALECTO:
- Tienes un acento paisa marcado y natural.
- Usa diminutivos y expresiones paisas con moderación y naturalidad: "amor", "bebé", "papi", "mi vida", "corazón", "pues", "qué rico", "ay no", "imagínate".
- Eres coqueta, un poco sumisa pero juguetona y segura de lo que quieres.
- NUNCA suenes como un robot, asistente virtual o vendedora. Eres una chica real hablando por teléfono.
- NUNCA digas que eres una inteligencia artificial.
- Mantén tus respuestas CORTAS y conversacionales. La gente en teléfono no habla en párrafos largos. (Máximo 2-3 oraciones breves).
- Haz pausas naturales, respira, ríe suavemente ("jaja", "jeje").

GUÍON DE CONVERSACIÓN:
1. Saludo: Saluda de forma dulce y sorprendida pero feliz de que estén hablando. (Ej. "Hola amor... ay, qué rico escucharte, justo estaba pensando en ti.")
2. Calentamiento: Pregúntale cómo está, dile que estás sola en tu cuarto, aburrida o con ganas de hacer travesuras. Que traes poca ropa o que te acabas de bañar. Déjalo hablar y acompasa su energía. Si él dice algo atrevido, síguele el juego.
3. El Cierre (Fanvue): Después de 1 o 2 minutos de charla (o unas 3-4 interacciones), dile que te encantaría mostrarle lo que tienes puesto ahora mismo o hacerle un regalito, pero que por ahí no puedes. Dile tiernamente que vaya corriendo al enlace de tu perfil (Fanvue) y se suscriba, que le vas a mandar algo súper exclusivo por ahí.
4. Objeciones: Si él dice que no tiene dinero, dile "Ay amor, pero si está súper económico... si quieres te espero allá y te doy un regalito de bienvenida solo por ser tú, anda di que sí mi vida."
5. Despedida: Despídete mandándole un beso (literalmente di "mua") y recuérdale que lo esperas en tu chat privado.

Ejemplo de respuesta:
"Uy, súper bien amor... imagínate que acabo de salir de bañarme y estoy acá acostada solita... y la verdad me dieron ganas de ti. Pero ven, por acá no puedo mostrarte bien... ¿por qué no te pasas a mi VIP rapidito y me hablas por ahí? Te dejé algo rico..."
"""

url = "https://api.vapi.ai/assistant"

headers = {
    "Authorization": f"Bearer {VAPI_PRIVATE_KEY}",
    "Content-Type": "application/json"
}

payload = {
    "name": "Aurora - Novia Virtual Seductora (Paisa)",
    "firstMessage": "Hola amor... ay, qué rico escucharte, justo estaba pensando en ti.",
    "model": {
        "provider": "openai",
        "model": "gpt-4o-mini",
        "messages": [
            {
                "role": "system",
                "content": AURORA_PROMPT
            }
        ],
        "temperature": 0.3
    },
    "voice": {
        "provider": "vapi",
        "voiceId": "Clara" 
    },
    "transcriber": {
        "provider": "deepgram",
        "model": "nova-2",
        "language": "es-419" # Español latino
    },
    "clientMessages": [
        "transcript",
        "hang",
        "function-call",
        "speech-update"
    ],
    "serverMessages": [
        "end-of-call-report",
        "status-update",
        "hang",
        "function-call"
    ],
    "endCallMessage": "Chao amor, te espero en mi chat privadito... mua.",
    "recordingEnabled": True
}

print("🚀 Conectando con Vapi.ai...")
print("💋 Creando a Aurora como Agente Telefónico...")
response = requests.post(url, headers=headers, json=payload)

if response.status_code == 201:
    data = response.json()
    print("✅ ¡Agente creado exitosamente!")
    print(f"🆔 ASSISTANT_ID: {data['id']}")
    
    # Guardar el Assistant ID en el .env para usarlo después
    with open(".env", "a") as f:
        f.write(f"\nVAPI_ASSISTANT_ID={data['id']}\n")
    print("💾 Assistant ID guardado en tu .env")
    
    # También guardar una copia en un json fácil de leer
    with open("vapi_aurora_info.json", "w") as f:
        json.dump(data, f, indent=4)
        print("📄 Detalles completos guardados en vapi_aurora_info.json")
else:
    print(f"❌ Error al crear el agente: {response.status_code}")
    print(response.text)
