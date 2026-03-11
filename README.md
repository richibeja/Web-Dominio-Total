# Aurora AI Sales Suite

## 🎯 Objetivo
Este repositorio contiene la **suite completa** de scripts y recursos para el proyecto **Aurora**, una plataforma de automatización de ventas y generación de contenido con IA. Incluye:
- Bots de Telegram y Instagram
- Generación de voz (Edge‑TTS, Qwen‑3‑TTS, ElevenLabs)
- Gestión de usuarios y medios
- Front‑end público y landing pages
- Herramientas de marketing y afiliación (ClickBank, Fanvue)

## 📦 Estructura del proyecto
```
modelos  ia para monitizar/
├─ AURORA_APP/                 # Aplicación web y scripts de voz
├─ ai_models/                  # Handlers de IA (voice, chat)
├─ shared/                     # Utilidades comunes (persistencia, telegram)
├─ content/                    # PDFs, ebooks y assets de marketing
├─ WEB_PARA_PUBLICAR/          # Página pública de promoción
├─ requirements.txt            # Dependencias Python
├─ .env.example                # Variables de entorno (ejemplo)
└─ README.md                   # Este archivo
```

## 🛠️ Instalación
1. **Clonar el repositorio**
   ```bash
   git clone <repo-url>
   cd "modelos  ia para monitizar"
   ```
2. **Crear entorno virtual** (recomendado)
   ```bash
   python -m venv .venv
   .venv\Scripts\activate   # Windows
   ```
3. **Instalar dependencias**
   ```bash
   pip install -r requirements.txt
   ```
4. **Configurar variables de entorno**
   - Copia el archivo de ejemplo:
     ```bash
     copy .env.example .env
     ```
   - Edita `.env` con tus credenciales (API keys, tokens, etc.).

## 🚀 Uso rápido
### Generar voz
```bash
python AURORA_APP/scripts/tts.py "Texto a convertir" --user-id test_user
```
### Ejecutar bot de Telegram
```bash
python AURORA_APP/telegram_bot.py
```
### Enviar mensaje masivo a clientes
```bash
python ENVIAR_VIDEO_CLIENTES.py
```

## 📚 Documentación interna
- **VoiceHandler** (`ai_models/voice_handler.py`): gestiona varios proveedores TTS, limpieza de texto y mezcla de efectos.
- **VaultHandler** (`shared/vault_handler.py`): indexa fotos y videos generados.
- **Telegram Operaciones** (`shared/telegram_operaciones.py`): wrappers para la API de Telegram con colas y rate‑limit.

## 🧪 Tests
Se incluyen pruebas unitarias básicas con `pytest`. Ejecuta:
```bash
pytest tests/
```

## ⚙️ CI / CD
El proyecto incluye un workflow de GitHub Actions (`.github/workflows/ci.yml`) que ejecuta linting (`ruff`), formateo (`black`) y tests en cada push.

## 🔐 Seguridad
- **Credenciales** nunca deben versionarse. Añade cualquier archivo sensible a `.gitignore`.
- Se recomienda usar **variables de entorno** y **Secretos** en CI.

## 🎨 Diseño premium (frontend)
Los archivos HTML (`secreto.html`, `WEB_PARA_PUBLICAR/index.html`) usan una paleta oscura, tipografía `Inter` y animaciones sutiles. Revisa los comentarios `<!-- TODO: mejorar SEO -->` para añadir meta‑tags.

---
*© 2026 Aurora – Todos los derechos reservados.*
