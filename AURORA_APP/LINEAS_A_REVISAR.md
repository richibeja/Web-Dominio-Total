# Líneas de código a revisar — Qué puede estar mal

Estas son las líneas que afectan la conexión y el envío de mensajes. Si algo falla, revisa aquí.

---

## server.js

### Estado de conexión (líneas 41, 345–346, 372–373, 443, 535, 544–546)

| Línea | Código | Qué hace |
|-------|--------|----------|
| **41** | `let isClientReady = false;` | Arranca en false. Solo pasa a true cuando la librería emite `ready` (línea 346) o cuando pulsas "Marcar como conectado" (línea 545). |
| **345-348** | `client.on('ready', () => { isClientReady = true; io.emit('ready'); ...` | Cuando whatsapp-web.js emite `ready`, se marca conectado y se avisa al dashboard. **Si esta callback nunca se ejecuta**, el dashboard no pasa a "Conectado" (fallo conocido de la librería). |
| **372-373** | `client.on('disconnected', ...) { isClientReady = false;` | Si WhatsApp se desconecta, se vuelve a false. |
| **443** | `if (!isClientReady) { return res.status(503).json({ ok: false, error: 'WhatsApp no está conectado' }); }` | **API /api/send**: si no está "conectado", devuelve 503. Por eso no puedes enviar si `ready` no se disparó. |
| **535** | `if (isClientReady) socket.emit('ready');` | Al conectar un cliente nuevo al dashboard, si ya estaba listo, se le envía `ready`. |
| **544-546** | `socket.on('forceReady', () => { isClientReady = true; io.emit('ready'); }` | Workaround: al pulsar "Marcar como conectado" se fuerza conectado en el servidor y se notifica al dashboard. **Si la librería no ha terminado de cargar**, `client.sendMessage()` puede fallar aunque isClientReady sea true. |

### Envío de mensajes (líneas 451–452, 409, 412, 518)

| Línea | Código | Qué hace |
|-------|--------|----------|
| **451-452** | `await client.sendMessage(targetChatId, text.trim());` | Envía el mensaje manual. **Si aquí da error**, suele ser porque el cliente de whatsapp-web.js no está realmente listo (solo se forzó isClientReady en el servidor). |
| **409** | `await client.sendMessage(msg.from, reply);` | Respuesta automática de la IA. |
| **412** | `await client.sendMessage(msg.from, fanvueLink);` | Envío del link Fanvue en modo auto. |
| **518** | `await client.sendMessage(targetChatId, media, { sendAudioAsVoice: true });` | Envío de audio TTS. |

### Eventos de WhatsApp (líneas 334, 354, 360, 378)

| Línea | Código | Qué hace |
|-------|--------|----------|
| **334** | `client.on('qr', async (qr) => { ... io.emit('qr', qrImage);` | Cuando hay QR, se envía al dashboard. |
| **354** | `client.on('authenticated', () => { ... io.emit('authenticated');` | Tras escanear el QR, la librería emite `authenticated`. El dashboard muestra "Sesión vinculada, cargando...". |
| **360** | `if (!isClientReady && authenticatedAt)` | A los 2 min, si aún no hubo `ready`, se emite `stuck_loading` al dashboard. |
| **378** | `client.on('message', async (msg) => { ...` | Cada mensaje entrante: se emite al dashboard y, si modo auto, se responde con IA. **Si no recibes mensajes**, esta callback no se está ejecutando (cliente no listo). |

---

## public/index.html

### Conexión y botón "Marcar como conectado" (líneas 265–272, 275–279, 302–304)

| Línea | Código | Qué hace |
|-------|--------|----------|
| **265-272** | `socket.on('ready', () => { ... setStatus(true, 'Conectado'); sendManual.disabled = false; });` | Cuando el servidor emite `ready`, el dashboard muestra "Conectado" y habilita Enviar. |
| **275-279** | `socket.on('authenticated', () => { ... document.getElementById('forceReadyHint').classList.remove('hidden'); setStatus(false, 'Sesión vinculada, cargando...');` | Tras escanear, se muestra el aviso "Marcar como conectado". |
| **302-304** | `document.getElementById('forceReadyBtn').addEventListener('click', () => { socket.emit('forceReady'); ... });` | Al pulsar "Marcar como conectado" se envía `forceReady` al servidor. |

### Envío manual (líneas 349–363)

| Línea | Código | Qué hace |
|-------|--------|----------|
| **354** | `const r = await fetch('/api/send', { ... body: JSON.stringify({ chatId: lastChatId, text }) });` | Llama a la API de envío. |
| **356-357** | `if (data.ok) manualText.value = ''; else { ... alert(msg); }` | Si ok, limpia el texto; si no, muestra el error (incl. 503 "WhatsApp no está conectado"). |
| **363** | `if (r.status === 503 || /conectado|not connected|ready/i.test(msg)) msg += '...'` | Añade sugerencia de reiniciar si el error es de conexión. |

---

## Resumen: qué suele estar mal

1. **Línea 345–348 (server.js):** La librería whatsapp-web.js no ejecuta `client.emit('ready')` tras `authenticated`, así que `isClientReady` no pasa a true y el dashboard no muestra "Conectado". No es un error de tu código; es de la librería.
2. **Líneas 443 y 451 (server.js):** Si usas "Marcar como conectado", `isClientReady` se pone true pero `client.sendMessage()` puede fallar si el cliente interno no ha terminado de cargar. El fallo se ve en la consola del servidor (Node) al intentar enviar.
3. **Línea 378 (server.js):** Si no recibes mensajes en el dashboard, es que esta callback no se ejecuta porque el cliente no ha emitido `ready` y la librería no está lista para recibir.

Para depurar: abre la consola del servidor (donde corre `node server.js`) y mira si al enviar un mensaje sale algún error en rojo después de `client.sendMessage(...)`.
