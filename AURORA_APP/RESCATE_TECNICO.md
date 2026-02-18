# Rescate Técnico — Que el bot arranque hoy

El proyecto usa **Baileys** para WhatsApp (sin navegador, más estable que whatsapp-web.js). La sesión se guarda en la carpeta **baileys_auth**. Si no funciona (no sale el QR, no conecta, no recibe/envía), sigue estos pasos en orden.

---

## 0. La sesión aparece **activa** en el teléfono pero el dashboard no pasa a "Conectado"

Si en WhatsApp (móvil) → **Dispositivos vinculados** ves la sesión como **Activa**, el enlace con WhatsApp está bien. A veces el servidor no llega a marcar "Conectado" aunque la sesión ya esté vinculada.

**Qué hacer:**

1. Abre el dashboard en **http://localhost:3000**.
2. Si ves el texto *"Sesión vinculada, cargando..."*, busca el aviso en verde: **"Si en el móvil la sesión sale Activa, pulsa: Marcar como conectado"**.
3. Pulsa **Marcar como conectado**. El dashboard pasará a "Conectado" y podrás enviar mensajes manuales y usar el Modo Automático.
4. Si después **los mensajes no envían** o no llegan en WhatsApp: espera 1–2 minutos y prueba de nuevo. Si sigue igual, reinicia el servidor (Ctrl+C y `node server.js`) y, cuando el dashboard vuelva a cargar, pulsa otra vez "Marcar como conectado" si la sesión sigue activa en el teléfono.

---

## 0.1. Se desconectó pero en el teléfono sigue vinculado

Si el dashboard pasa a **Desconectado** pero en WhatsApp (móvil) → Dispositivos vinculados la sesión sigue **Activa**:

1. El servidor **reconecta solo** a los 5 segundos usando la sesión en **baileys_auth** (no hace falta escanear el QR de nuevo). Si se cae el internet, el bot vuelve solo.
2. En el dashboard verás "Reconectando..." y luego "Conectado" o "Sesión vinculada, cargando..." (en ese caso pulsa **Marcar como conectado**).
3. Si no reconecta solo, aparece el aviso **"Si no reconecta solo, pulsa: Reconectar"**. Pulsa **Reconectar** para intentar de nuevo.

No borres la carpeta **baileys_auth** ni escanees un QR nuevo si la sesión sigue vinculada en el teléfono.

---

## 0.2. Si sigue el error 405 (Desconectado: 405)

**VPN = casi siempre el culpable.** WhatsApp bloquea conexiones desde VPN (IP compartida + bot = 405). Si usas VPN:

1. **Apaga el VPN por completo** (y comprueba que no quede en segundo plano).
2. Cierra la consola (Ctrl+C).
3. Borra la carpeta **baileys_auth** en el proyecto.
4. Borra la carpeta **baileys_store** si existe.
5. Reinicia el Wi‑Fi del PC (apágalo y enciéndelo).
6. Sin VPN, ejecuta: `node server.js`. Si el "Desconectado: 405" ya no sale, abre **http://localhost:3000** y escanea el QR.

---

Si no usas VPN o ya lo apagaste:

1. **Reiniciar el router** — Apaga el router 30 s y enciéndelo de nuevo (IP dinámica “fresca”).
2. **Cambiar DNS** — En la red de tu PC: DNS principal **8.8.8.8**, secundario **8.8.4.4**. En terminal: `ipconfig /flushdns`. Luego `node server.js`.
3. **Código** — En `server.js` ya se fuerza una versión de WhatsApp que suele evitar 405 (`version: [2, 3000, 1015901307]`, `connectTimeoutMs: 60000`). Borra **baileys_auth** y vuelve a iniciar.
4. **Firewall** — Desactiva temporalmente el firewall de Windows (red privada), prueba `node server.js` y vuelve a activarlo.

**Limpieza de “basura” de red (Protocolo de Emergencia):**  
Cierra el servidor (Ctrl+C). Borra la carpeta **baileys_auth** por completo. En la terminal ejecuta: `npm cache clean --force`. Luego inicia de nuevo con `node server.js`. En `server.js` está aplicado el “Protocolo de Emergencia” (versión [2, 2413, 1], logger silencioso, timeouts largos) para intentar saltarse el bloqueo 405.

**"Reset" eléctrico (si el 405 sigue "pegado" en el router):**  
1. Cierra Cursor y cualquier consola.  
2. Apaga el Wi‑Fi de tu PC.  
3. Desconecta el router de la pared, espera **15 segundos** y conéctalo de nuevo.  
4. Mientras el router enciende, borra la carpeta **baileys_auth** en AURORA_APP.  
5. Cuando vuelva el internet, activa el Wi‑Fi y ejecuta: `node server.js`.  
6. Abre **http://localhost:3000** — el QR sale **solo en el dashboard**, no en la consola (Baileys está en modo silencioso).

**Si sigue el 405:** En la terminal escribe: `ping web.whatsapp.com`. Si responde (ms), hay conexión. Si dice "Tiempo de espera agotado", tu internet puede estar bloqueando WhatsApp.

**Reset de red (antiaislante):** En CMD o PowerShell **como administrador** ejecuta en este orden: `ipconfig /flushdns`, `ipconfig /release`, `ipconfig /renew`, `netsh winsock reset`. Luego (ideal) reinicia la PC. Después: apaga VPN, borra **baileys_auth** y **baileys_store** (o archivos como baileys_store.json), y ejecuta `node server.js`.

**Último recurso — otro puerto:** Si el 3000 quedó asociado al VPN, en **.env** pon `PORT=4000`. Luego abre **http://localhost:4000** en lugar de 3000.

**Si nada funciona (405 sigue):**  
- **Opción A:** Router Hitron con Web Filtering/Security en Alto: entra a **192.168.10.1** y baja "Web Filtering" o "Security" a **Medium** o **Low**.  
- **Opción B:** La cuenta de WhatsApp puede estar marcada por intentos fallidos. Prueba vincular **otro número** (de prueba) para ver si el QR sale.  
- **Node.js:** Baileys va mejor con **Node 18 o 20 LTS**. Si usas Node 25.x (muy nuevo), prueba instalar Node 20 LTS desde [nodejs.org](https://nodejs.org) y ejecutar de nuevo `npm install` y `node server.js`.

---

## 0.3. Chequeos finales (PTT, Pino, lanzamiento)

**1. Verificación PTT (nota de voz)**  
El audio que genera **tts.py** (edge-tts) suele ser .mp3. En **server.js** se envía con `mimetype: 'audio/mp4'` y `ptt: true`, así WhatsApp lo muestra como nota de voz (con onda), no como archivo adjunto. Baileys encapsula correctamente. Si el audio no se envía, se puede añadir una conversión mp3→mp4 en el servidor; con la configuración actual debería funcionar.

**2. Log de Pino (caja negra)**  
Con **pino** verás mucho texto en la consola. Lo importante:
- **connection.update** → que el estado llegue a **open** (conectado).
- **creds.update** → Baileys está guardando la sesión en **baileys_auth**. No borres esa carpeta a menos que quieras volver a escanear el QR.

**3. Cómo lanzar ahora**
1. Abre la terminal (Cursor: Ctrl+` o PowerShell en la carpeta del proyecto).
2. Escribe: `node server.js`.
3. Abre **http://localhost:3000**.
4. Escanea el QR con WhatsApp (Dispositivos vinculados → Vincular dispositivo).

---

## 1. Limpieza de restos de Puppeteer (si usaste whatsapp-web.js antes)

Al pasar a Baileys ya no se usa Chrome/Puppeteer. Para evitar procesos "zombie" y conflictos:

1. Abre el **Administrador de tareas** (Ctrl+Shift+Esc).
2. Si ves procesos **Chrome** o **Chromium** abiertos por el bot, ciérralos.
3. En la carpeta del proyecto, **borra** las carpetas **.wwebjs_auth** y **.wwebjs_cache** si aún existen. Tu única carpeta de sesión ahora es **baileys_auth**.
4. Reinicia el servidor.

---

## 2. Limpieza de sesión "corrupta" (Baileys)

La carpeta **baileys_auth** guarda la sesión de WhatsApp. Si está corrupta o quieres vincular de nuevo, bórrala.

1. **Cierra** cualquier terminal donde corra el servidor (Ctrl+C).
2. Ve a la carpeta del proyecto.
3. **Borra** la carpeta **baileys_auth** (o ejecuta **NUEVO_QR.bat**, que borra también `.wwebjs_auth` y `baileys_auth`).
4. Vuelve a iniciar el servidor (`node server.js` o INICIAR.bat).

---

## 3. Baileys no usa navegador

Baileys se conecta por WebSocket directamente a WhatsApp. No hace falta Chrome ni Puppeteer. Si el QR no sale o da error al iniciar:

1. Asegúrate de tener **Node.js 18+**.
2. Instala dependencias (Baileys, pino para logs, libsignal-node): **INSTALAR_DEPENDENCIAS.bat** o en terminal:
   ```bash
   npm install @whiskeysockets/baileys pino libsignal-node
   ```
   (O simplemente `npm install` si ya están en package.json.)
3. Si sigue fallando, borra **baileys_auth** y reinicia (ver sección 1).

---

## 4. Ejecución paso a paso (modo debug)

No uses el .bat por ahora. Abre la **terminal en Cursor** (Ctrl+`) o PowerShell en la carpeta AURORA_APP:

1. **Instalar dependencias:**
   ```bash
   npm install
   ```

2. **Iniciar el servidor:**
   ```bash
   node server.js
   ```

3. **Mira la consola:**
   - Si sale **"QR recibido, enviando al dashboard..."** → Abre http://localhost:3000 y escanea el QR.
   - Si ves **connection.update** en los logs (pino), comprueba que llegue a **open**.
   - Si ves **creds.update** → la sesión se está guardando en **baileys_auth**.

---

## 5. Verificar el script de voz (Python)

Si el dashboard carga pero **el audio (TTS) falla**, puede que Python no esté en el PATH o que falte edge-tts.

En la terminal, desde la carpeta AURORA_APP:

```bash
py scripts/tts.py --text "Hola mor" --voice es-CO-SalomeNeural
```

(o `python scripts/tts.py` si usas `python`)

- Si devuelve **ImportError** o similar:
  ```bash
  py -m pip install edge-tts
  ```
  o
  ```bash
  pip install edge-tts
  ```

---

## 6. Si el QR sigue sin salir

- **Dashboard abre pero el cuadro del QR está vacío:**
  - Revisa si el **firewall de Windows** pide permiso para Node.js. Autoriza acceso a la red.
  - En la consola del servidor debe aparecer **"QR recibido, enviando al dashboard..."**. Si no aparece, borra **baileys_auth** y reinicia.
- **Dependencias:** El proyecto usa **@whiskeysockets/baileys**. Ejecuta `npm install` y borra **baileys_auth** si cambiaste de librería antes.

---

## Qué hacer ahora

1. Cierra el servidor (Ctrl+C).
2. Borra la carpeta **baileys_auth** (o ejecuta **NUEVO_QR.bat**).
3. En la terminal: `npm install` y luego `node server.js`.
4. Abre http://localhost:3000 y escanea el QR con WhatsApp (Dispositivos vinculados → Vincular dispositivo).
5. Si algo falla, copia el **error exacto** de la consola para poder indicar qué cambiar.
