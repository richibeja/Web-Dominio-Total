"""
🤖 BOT ESPEJO DE INSTAGRAM — Versión Anti-Detección v3
Solución al cierre de página: calentamiento del navegador + 
parche de fingerprint más agresivo + espera adaptativa post-login.
"""
import time
import random
import sys
import os
from pathlib import Path

# Forzar UTF-8 en Windows para evitar errores con emojis en prints
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='ignore', line_buffering=True)
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='ignore', line_buffering=True)

sys.path.append(str(Path(__file__).resolve().parent))
from shared.telegram_operaciones import send_instagram_dm_to_telegram, consume_next_reply
from ai_models.ai_handler import AIHandler
import asyncio

# ── CONFIGURACIÓN ─────────────────────────────────────────────────────────────
HEADLESS            = False   # False = ventana visible
CICLO_REVISION_MIN  = 5       # Mínimo minutos entre revisiones
CICLO_REVISION_MAX  = 10      # Máximo minutos entre revisiones
ESPERA_429_SEG      = 1200    # Si hay error 429: esperar 20 minutos

# ── STEALTH JAVASCRIPT (oculta todas las huellas de automatización) ───────────
STEALTH_SCRIPT = """
// 1. Eliminar el flag webdriver (con delete primero para evitar TypeError)
try { delete Object.getPrototypeOf(navigator).webdriver; } catch(e) {}
try {
    Object.defineProperty(navigator, 'webdriver', {
        get: () => undefined,
        configurable: true,
        enumerable: false
    });
} catch(e) {}

// 2. Reparar el toString del chrome headless
window.navigator.chrome = { runtime: {}, app: {}, csi: () => {}, loadTimes: () => {} };

// 3. Simular plugins reales de Chrome
Object.defineProperty(navigator, 'plugins', {
    get: () => {
        return Object.assign([], {
            0: {name:'Chrome PDF Plugin', filename:'internal-pdf-viewer'},
            1: {name:'Chrome PDF Viewer', filename:'mhjfbmdgcfjbbpaeojofohoefgiehjai'},
            2: {name:'Native Client', filename:'internal-nacl-plugin'},
            length: 3
        });
    }
});

// 4. Idiomas normales colombianos
Object.defineProperty(navigator, 'languages', { get: () => ['es-CO','es','en-US','en'] });

// 5. Ocultar automation en el permiso de notificaciones
const originalQuery = window.navigator.permissions.query;
window.navigator.permissions.query = (parameters) =>
    parameters.name === 'notifications'
        ? Promise.resolve({ state: Notification.permission })
        : originalQuery(parameters);

// 6. Falsificar resolución de pantalla realista
Object.defineProperty(screen, 'width', { get: () => 1366 });
Object.defineProperty(screen, 'height', { get: () => 768 });

// 7. Ocultar que se está usando CDP (Chrome DevTools Protocol)
delete window.cdc_adoQpoasnfa76pfcZLmcfl_Array;
delete window.cdc_adoQpoasnfa76pfcZLmcfl_Promise;
delete window.cdc_adoQpoasnfa76pfcZLmcfl_Symbol;
"""

def human_sleep(mi=2.0, ma=5.0):
    time.sleep(random.uniform(mi, ma))

def mover_mouse(page):
    try:
        for _ in range(random.randint(2, 4)):
            x = random.randint(300, 1100)
            y = random.randint(150, 650)
            page.mouse.move(x, y, steps=random.randint(8, 20))
            time.sleep(random.uniform(0.05, 0.2))
    except:
        pass

def scroll_natural(page):
    """Scroll arriba y abajo como lo haría una persona real."""
    try:
        page.mouse.wheel(0, random.randint(150, 400))
        time.sleep(random.uniform(0.3, 0.8))
        page.mouse.wheel(0, -random.randint(50, 200))
    except:
        pass

def comportamiento_humano_extra(page):
    """Acciones aleatorias para despistar a Instagram."""
    try:
        acciones = ["home", "scroll", "nada", "stories"]
        accion = random.choice(acciones)
        
        if accion == "home":
            print("🏠 Navegando al Home para parecer humano...")
            page.goto("https://www.instagram.com/", wait_until="domcontentloaded")
            human_sleep(3, 7)
            scroll_natural(page)
        elif accion == "stories":
            print("🤳 Viendo historias al azar...")
            stories = page.locator('div[role="menuitem"]')
            if stories.count() > 0:
                stories.nth(random.randint(0, min(3, stories.count()-1))).click()
                human_sleep(4, 10)
                page.keyboard.press("Escape")
        elif accion == "scroll":
            scroll_natural(page)
    except:
        pass

def escribir_como_humano(element, text):
    """Escribe texto con velocidad variable y errores ocasionales."""
    for char in text:
        element.type(char, delay=random.randint(50, 250))
        if random.random() < 0.05: # 5% de chance de pausa larga
            human_sleep(0.5, 1.5)

def esperar_pagina_estable(page, timeout=10):
    """Espera a que la página deje de cargar cosas."""
    try:
        page.wait_for_load_state("networkidle", timeout=timeout * 1000)
    except:
        pass
    time.sleep(random.uniform(1.0, 2.0))

def run_instagram_bot():
    from playwright.sync_api import sync_playwright

    user_data_dir = str(Path(__file__).resolve().parent / "data" / "ig_profile")
    Path(user_data_dir).mkdir(parents=True, exist_ok=True)

    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            user_data_dir,
            headless=HEADLESS,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-infobars",
                "--disable-dev-shm-usage",
                "--disable-extensions",
                "--disable-plugins-discovery",
                "--disable-gpu-sandbox",
                "--no-first-run",
                "--no-default-browser-check",
                "--password-store=basic",
                f"--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            ],
            viewport={"width": 1366, "height": 768},
            locale="es-CO",
            timezone_id="America/Bogota",
            color_scheme="light",
            ignore_https_errors=True,
        )

        # Inyectar stealth en TODAS las páginas nuevas, antes de cargar nada
        context.add_init_script(STEALTH_SCRIPT)

        page = context.new_page()

        # ── CALENTAMIENTO: Visitar Google primero para construir historial ────
        print("[CALENTAMIENTO] Simulando usuario real...")
        page.goto("https://www.google.com/search?q=instagram+login", wait_until="domcontentloaded")
        esperar_pagina_estable(page, 5)
        mover_mouse(page)
        scroll_natural(page)
        human_sleep(2, 4)

        # ── IR A INSTAGRAM ────────────────────────────────────────────────────
        print("[Navegación] Entrando a Instagram...")
        page.goto("https://www.instagram.com/", wait_until="domcontentloaded")
        esperar_pagina_estable(page, 8)
        human_sleep(2, 4)

        # ── IR AL INBOX ───────────────────────────────────────────────────────
        page.goto("https://www.instagram.com/direct/inbox/", wait_until="domcontentloaded")
        esperar_pagina_estable(page, 10)

        print("\n" + "="*55)
        print("⏳ ACCIÓN REQUERIDA: Si Instagram pide login, hazlo ahora.")
        print("   Tenés hasta 5 minutos antes de que el bot arranque.")
        print("="*55 + "\n")

        # Esperar señal de login exitoso (hasta 5 minutos)
        logged_in = False
        try:
            page.wait_for_selector(
                'svg[aria-label="Mensajero"], svg[aria-label="Messenger"], '
                'a[href="/direct/inbox/"], div[role="listbox"]',
                timeout=300_000
            )
            logged_in = True
            print("[OK] Dentro del inbox. Bot de espejo activo!\n")
        except:
            print("[ADVERTENCIA] No se detectó el inbox. Intentando continuar igual...\n")

        human_sleep(3, 5)

        # ── BUCLE PRINCIPAL ───────────────────────────────────────────────────
        ciclo = 0
        while True:
            ciclo += 1
            try:
                # Cada 5 ciclos: mover mouse para mantener actividad humana
                if ciclo % 5 == 0:
                    mover_mouse(page)

                bandejas = [
                    "https://www.instagram.com/direct/inbox/",
                    "https://www.instagram.com/direct/requests/",
                ]

                for url_bandeja in bandejas:
                    page.goto(url_bandeja, wait_until="domcontentloaded")
                    esperar_pagina_estable(page, 6)
                    human_sleep(2, 3)
                    scroll_natural(page)

                    # Detectar mensajes no leídos (Selectores ultra-agresivos)
                    unread = page.locator(
                        'div[aria-label*="No leí"], div[aria-label*="Unread"], div[aria-label*="No leido"], '
                        'span[aria-label*="No leí"], span[aria-label*="Unread"], span[aria-label*="No leido"]'
                    )
                    cantidad = unread.count()

                    if cantidad > 0:
                        print(f"[NUEVO] {cantidad} mensajes sin leer en {url_bandeja.split('/')[-2]}...")
                        for i in range(cantidad):
                            try:
                                item = page.locator(
                                    'div[aria-label*="No leí"], div[aria-label*="Unread"], div[aria-label*="No leido"], '
                                    'span[aria-label*="No leí"], span[aria-label*="Unread"], span[aria-label*="No leido"]'
                                ).nth(i)
                                item.click()
                                esperar_pagina_estable(page, 5)
                                human_sleep(2, 4)

                                # Extraer username
                                u_loc = page.locator("header a, div[role='button'] span").first
                                username = (
                                    u_loc.text_content(timeout=3000).strip()
                                    if u_loc.count() > 0 else "Desconocido"
                                )

                                # Extraer último mensaje
                                msgs = page.locator('div[role="row"]')
                                if msgs.count() > 0:
                                    ultimo = (msgs.last.text_content() or "").strip()
                                    if ultimo:
                                        print(f"   📨 @{username}: {ultimo[:80]}")
                                        send_instagram_dm_to_telegram(username, ultimo)
                                        print("   ✅ Reenviado a Telegram.")
                                        
                                        # --- RESPUESTA AUTOMÁTICA PROFESIONAL ---
                                        try:
                                            print(f"   ✍️ Generando respuesta profesional para @{username}...")
                                            ai = AIHandler()
                                            # Ejecutar asíncrono en modo síncrono
                                            loop = asyncio.new_event_loop()
                                            asyncio.set_event_loop(loop)
                                            respuesta = loop.run_until_complete(ai.get_response(ultimo, user_id=username, platform="instagram"))
                                            loop.close()
                                            
                                            if respuesta:
                                                print(f"   🤖 Aurora (Pro): {respuesta}")
                                                box = page.locator('div[role="textbox"]')
                                                if box.count() > 0:
                                                    box.click()
                                                    escribir_como_humano(box, respuesta)
                                                    human_sleep(1, 2)
                                                    box.press("Enter")
                                                    print(f"   ✅ Respuesta enviada automáticamente.")
                                        except Exception as e_ai:
                                            print(f"   ⚠️ Error en IA: {e_ai}")

                                page.goto(url_bandeja, wait_until="domcontentloaded")
                                esperar_pagina_estable(page, 5)
                                human_sleep(2, 3)

                            except Exception as e_chat:
                                print(f"   ⚠️ Error en chat #{i}: {e_chat}")
                                page.goto(url_bandeja, wait_until="domcontentloaded")
                                human_sleep(2, 3)

                # Enviar respuestas desde la cola de Telegram
                reply = consume_next_reply()
                if reply:
                    target = reply.get("username", "")
                    texto  = reply.get("text", "")
                    if target and texto:
                        print(f"✍️  Respondiendo a @{target}...")
                        page.goto(
                            f"https://www.instagram.com/direct/t/{target}/",
                            wait_until="domcontentloaded"
                        )
                        esperar_pagina_estable(page, 5)
                        human_sleep(1, 3)

                        box = page.locator('div[role="textbox"]')
                        if box.count() > 0:
                            box.click()
                            box.fill("")
                            escribir_como_humano(box, texto)
                            human_sleep(0.8, 1.5)
                            box.press("Enter")
                            print(f"   ✅ Enviado a @{target}")

                # Comportamiento humano antes de la siguiente revisión
                if ciclo % 3 == 0:
                    comportamiento_humano_extra(page)

                # Pausa LARGA para evitar detección (5 a 10 minutos)
                pausa_minutos = random.randint(CICLO_REVISION_MIN, CICLO_REVISION_MAX)
                pausa_segundos = pausa_minutos * 60 + random.randint(0, 60)
                print(f"[REPOSO] Ciclo #{ciclo} completo. Descansando {pausa_minutos} minutos...")
                time.sleep(pausa_segundos)

            except Exception as e_ciclo:
                err_str = str(e_ciclo)
                print(f"⚠️ Error en ciclo #{ciclo}: {err_str[:120]}")

                # Detectar error 429 (demasiadas solicitudes) — esperar largo
                if "429" in err_str or "Too Many" in err_str:
                    print(f"🚫 Instagram bloqueó temporalmente (429). Esperando {ESPERA_429_SEG//60} minutos...")
                    time.sleep(ESPERA_429_SEG)
                else:
                    human_sleep(20, 35)

                try:
                    page.goto(
                        "https://www.instagram.com/",
                        wait_until="domcontentloaded"
                    )
                    esperar_pagina_estable(page, 8)
                    human_sleep(3, 6)
                    page.goto(
                        "https://www.instagram.com/direct/inbox/",
                        wait_until="domcontentloaded"
                    )
                    esperar_pagina_estable(page, 8)
                except:
                    print("🔴 No se pudo recuperar la página. Reiniciando sesión...")
                    raise

        context.close()

# ── AUTO-REINICIO ─────────────────────────────────────────────────────────────
if __name__ == "__main__":
    intento = 0
    while True:
        intento += 1
        print(f"\n{'='*55}")
        print(f"[REINICIO] INICIO #{intento} - Bot Espejo Instagram")
        print(f"{'='*55}\n")
        try:
            run_instagram_bot()
        except KeyboardInterrupt:
            print("\n🛑 Detenido manualmente.")
            break
        except Exception as crash:
            espera = random.uniform(12, 22)
            print(f"\n💥 Caída: {crash}")
            print(f"⏳ Reiniciando en {espera:.0f}s...")
            time.sleep(espera)

