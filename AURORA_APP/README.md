# Novia Virtual — Dashboard WhatsApp

Dashboard local para controlar el bot de WhatsApp "Novia Virtual": QR, chat en vivo, **Modo Automático** con IA (OpenRouter MiMo-V2-Flash), **transcripción de audios** (Whisper), respuestas manuales y envío de audio con TTS (edge-tts).

---

## Todo aquí — Archivos del proyecto

| Archivo | Uso |
|---------|-----|
| **server.js** | Backend: Express, WhatsApp (Baileys), OpenRouter, Whisper, TTS |
| **public/index.html** | Dashboard: estado, QR, chat en vivo, embudo, envío manual, TTS |
| **scripts/tts.py** | Generar audio con edge-tts (Python) |
| **package.json** | Dependencias Node (@whiskeysockets/baileys = WhatsApp sin navegador) |
| **requirements.txt** | Dependencias Python (edge-tts) |
| **.env** | Tus claves (OPENROUTER_API_KEY, OPENAI_API_KEY, FANVUE_LINK). No subir a git. |
| **.env.example** | Plantilla de variables de entorno |

**Scripts (doble clic):**

| Script | Uso |
|--------|-----|
| **INICIAR.bat** | Inicia el servidor y abre el navegador en http://localhost:3000 |
| **INICIAR.ps1** | Igual que INICIAR.bat pero en PowerShell |
| **INICIAR_DESDE_CERO.bat** | Borra la sesión de WhatsApp, luego inicia (para escanear QR de nuevo) |
| **NUEVO_QR.bat** | Solo borra la sesión (.wwebjs_auth). Luego ejecuta INICIAR.bat |
| **NUEVO_QR.ps1** | Igual que NUEVO_QR.bat en PowerShell |
| **INSTALAR_DEPENDENCIAS.bat** | Ejecuta `npm install` (solo si faltan dependencias) |
| **DIAGNOSTICO.bat** | Comprueba Node, .env, Python, FFmpeg |
| **INICIAR_TELEGRAM.bat** | Inicia el bot de Telegram (agencia de modelos) |
| **INICIAR_DASHBOARD.bat** | Abre el dashboard Streamlit en http://localhost:8501 (log de nuevos clientes) |

**Reiniciar:** Cierra la ventana del servidor (Ctrl+C) y vuelve a ejecutar **INICIAR.bat** o **INICIAR.ps1**.

### Bot de Telegram (agencia de modelos)

| Archivo | Uso |
|---------|-----|
| **telegram_bot.py** | Bot con python-telegram-bot: /start con foto + botones (Galería, Hablar en Privado, Acceso VIP) |
| **dashboard_streamlit.py** | Dashboard Streamlit en puerto **8501**: muestra el log de **Nuevos Clientes** |
| **data/nuevos_clientes.json** | Log generado por el bot (cada /start se registra para el dashboard) |

**Flujo:** Instagram → enlace al bot de Telegram → bot calienta con foto y botones → Acceso VIP envía link Fanvue.  
**Token:** En Telegram busca @BotFather → /newbot → pega el API TOKEN en `.env` como `TELEGRAM_BOT_TOKEN`. Opcional: `MODEL_PHOTO_PATH` o `MODEL_PHOTO_URL` para la foto de bienvenida.

**Grupo de operaciones:** Define `TELEGRAM_OPERACIONES_ID` o `TELEGRAM_CHAT_ID` en `.env` con el ID del grupo donde están tus trabajadores (número tipo `-100XXXXXXXXX`). Al arrancar, el bot envía *"Sistema Aurora Online"* a ese grupo. Si no llega el mensaje, revisa que el ID coincida con el de tu grupo (obtén el ID con `https://api.telegram.org/botTU_TOKEN/getUpdates`).  
**Privacy Mode:** En @BotFather → tu bot → Bot Settings → **Group Privacy** = **DISABLED** (Turn off). Si está activado, el bot no recibe los mensajes del grupo y los trabajadores no podrán usar replies; el sistema no funcionará.

**Bienvenida (clientes):** Tres botones: 🔥 Ver Contenido Exclusivo (Fanvue), 💬 Hablar conmigo (link del bot), 🎁 Regalo de Bienvenida. Configura `TELEGRAM_BOT_LINK` y `FANVUE_REGALO_URL` en `.env` para que los botones abran esos enlaces.

**Instagram → grupo:** Cuando tengas el puente Instagram, los mensajes pueden enviarse al grupo con el formato `telegram_bot.format_instagram_message_for_group(usuario, mensaje, traduccion)` y enviando ese texto al `TELEGRAM_OPERACIONES_ID`.

---

## Requisitos

- **Node.js** 18+
- **Python** 3.7+ (para "Enviar Audio" con edge-tts)
- **FFmpeg** instalado y en el PATH (para convertir audios .ogg → .mp3 antes de transcribir)
- **OpenRouter API Key** (para Modo Automático): [openrouter.ai/keys](https://openrouter.ai/keys)
- **OpenAI API Key** (para transcribir audios con Whisper): [platform.openai.com/api-keys](https://platform.openai.com/api-keys)

## Instalación

### 1. Dependencias Node

```bash
npm install
```

(Incluye `@whiskeysockets/baileys`, `pino` para logs y `libsignal-node`. Si prefieres instalarlos explícitamente: `npm install @whiskeysockets/baileys pino libsignal-node`.)

### 2. Dependencias Python (para TTS)

```bash
pip install -r requirements.txt
```

### 3. FFmpeg (para audios entrantes)

Descarga FFmpeg desde [ffmpeg.org](https://ffmpeg.org) y añádelo al PATH de tu sistema. Sin FFmpeg, los mensajes de voz no se transcriben.

### 4. Variables de entorno

Copia `.env.example` a `.env` y configura:

```bash
OPENROUTER_API_KEY=sk-or-v1-xxxxxxxxxxxxxxxx   # IA (MiMo-V2-Flash)
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxx             # Transcripción de audios (Whisper)
FANVUE_LINK=https://www.fanvue.com/utopiafinca
```

## Uso

1. Iniciar el servidor: `npm start`
2. Abrir **http://localhost:3000**
3. Escanear el QR con WhatsApp (Dispositivos vinculados → Vincular dispositivo). La sesión se guarda en **baileys_auth** (no hace falta escanear cada vez).
4. **Modo Automático**: activa el interruptor "Modo Automático". Cuando llegue un mensaje **de texto o de voz**, el servidor: (1) si es audio, descarga el .ogg, lo convierte a .mp3 con FFmpeg y lo transcribe con Whisper; (2) pasa el texto (o la transcripción con la nota "[El usuario envió este audio]") a MiMo-V2-Flash, aplica humanización y envía la respuesta. Si piden link/Fanvue, además envía el link en automático.
5. La IA responde a audios con frases naturales tipo "Ay mor, qué voz tan linda tienes...". Si la transcripción falla o está vacía, responde "Uy bebé, no te escuché bien... ¿me repites o me escribes?".
6. **Enviar imagen con caption**: `POST /api/send-image` con `{ "chatId": "opcional", "imagePath": "ruta/a/foto.jpg", "caption": "Me acabo de despertar... ¿te gusta mi pijama? 🙈" }` o `imageUrl` (http/https) en lugar de `imagePath`. No bloquea el bot.

## Clientes en inglés (Baddie / British Babe)

No hace falta cambiar nada manualmente. Si el mensaje o la transcripción del audio está en **inglés**, la IA responde automáticamente en inglés con la misma personalidad coqueta y slang (u, r, lmao, hun, babe). Ganchos de venta en inglés: duda si es bot → "u really think a bot could sound this sweet? listen closely babe..."; pide Fanvue → "i've got some spicy clips waiting for u..."; se pone difícil → "don't be a shy boy... i don't bite (unless u want me to)". Para enviar audios con acento nativo a gringos/británicos, elige en el selector de voz **USA (Baddie)** — en-US-AnaNeural — o **UK (British Babe)** — en-GB-SoniaNeural.

## Limpieza de archivos temporales

Cada audio generado (TTS) se guarda temporalmente. El servidor:
- **Borra el .mp3** después de enviarlo al chat con "Enviar Audio al chat".
- **Borra archivos antiguos** (más de 15 min) en la carpeta temporal del sistema cada vez que generas un nuevo audio y cada 10 min en segundo plano.

Así se evita que la carpeta del proyecto crezca con gigas de .mp3.

## Estructura

- `server.js` — Express, Socket.IO, Baileys (WhatsApp), OpenRouter (MiMo-V2-Flash), Whisper (STT), fluent-ffmpeg (ogg→mp3), humanización, APIs (send, send-audio, send-image) y limpieza de temporales
- `public/index.html` — Interfaz con Tailwind CSS, Modo Automático y Embudo
- `scripts/tts.py` — Generación de audio con edge-tts (Python)
- `.env` — `OPENROUTER_API_KEY`, `OPENAI_API_KEY`, `FANVUE_LINK` (no subir a git)

## Checklist final antes de lanzar

1. **Vincular WhatsApp**: Escanea el QR desde el Dashboard.
2. **Prueba de voz**: Genera un audio con el texto "hola mor, me extrañaste?" (voz Medellín) y verifica que suene bien.
3. **Prueba de IA**: Escribe desde otro número y verifica que responda con las abreviaturas (muxo, cntigo, mor/bebé, etc.).
4. **Prueba de audio**: Envía una nota de voz desde otro número; el bot debe transcribirla (Whisper), mostrarla en el Dashboard y responder con algo tipo "Ay mor, qué voz tan linda tienes...".
5. **Prueba de link**: Pídele el link de Fanvue (por texto o por audio); la IA responde tipo "te lo paso en un ratito" y el bot envía el link en automático.

## Por qué no funciona — Comprobar paso a paso

| Síntoma | Causa más probable | Qué hacer |
|--------|---------------------|-----------|
| **"Cannot find module 'dotenv'"** o el servidor no arranca | No has ejecutado `npm install` o lo ejecutaste en otra carpeta | Abre una terminal **en la carpeta AURORA_APP** y ejecuta: `npm install`. Luego `node server.js` o doble clic en **INICIAR.bat**. |
| **"ERR_CONNECTION_REFUSED"** en el navegador | El servidor no está corriendo | Inicia el servidor desde **la carpeta del proyecto**: `node server.js` o **INICIAR.bat**. No cierres la ventana. |
| **No sale el QR** / se queda en "Autenticando..." o "Conectando..." | Sesión de WhatsApp vieja o atascada | Cierra el servidor (Ctrl+C). Ejecuta **NUEVO_QR.bat** (borra la sesión). Vuelve a iniciar con **INICIAR.bat** y espera 30–60 s. Si quieres forzar siempre un QR nuevo al iniciar, pon `FORCE_QR=1` en `.env` (luego quítalo). |
| **La IA no responde** en Modo Automático | `OPENROUTER_API_KEY` vacía, de ejemplo o incorrecta | En `.env` pon tu clave real de [openrouter.ai/keys](https://openrouter.ai/keys). Sin espacios ni comillas. Reinicia el servidor. |
| **Los audios entrantes no se transcriben** | Falta `OPENAI_API_KEY` o FFmpeg | Añade `OPENAI_API_KEY` en `.env` (clave de [platform.openai.com](https://platform.openai.com/api-keys)). Instala FFmpeg y añádelo al PATH. |
| **"Generar y escuchar" (TTS) falla** | Python o edge-tts no instalados | En una terminal: `py -m pip install edge-tts` (o `python -m pip install edge-tts`). Comprueba que `py -V` o `python -V` funcione. |
| **Ejecuté desde otra carpeta** | Node busca `server.js` donde estás, no en AURORA_APP | Siempre abre la terminal en `C:\Users\ALP\Documents\AURORA_APP` o usa **INICIAR.bat** (que entra en la carpeta correcta). |
| **"Falta una expresión después de ','"** en PowerShell | Escribiste `node server.js,` con coma al final | El comando correcto es **`node server.js`** (sin coma). |

**Diagnóstico rápido:** ejecuta **DIAGNOSTICO.bat** en la carpeta del proyecto. Te dirá si falta Node, `.env`, dependencias, Python o FFmpeg.

## Nota

WhatsApp no permite clientes no oficiales; el uso de bots puede suponer riesgo de bloqueo de cuenta.
