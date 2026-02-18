import asyncio
import os
import sys
from pathlib import Path

# Agregar el directorio raíz del proyecto al path para permitir ejecución independiente
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

import logging
import re
import random
import time
import json
import os
from pathlib import Path
from playwright.async_api import Page, BrowserContext
from instagram_bot.automation.browser_utils import get_browser_context, random_sleep, human_type
from instagram_bot.comentarios_a_fanvue import process_instagram_comment, is_comment_processed
try:
    from config.utopia_finca_links import LINKS as UTOPIA_FINCA_LINKS
except (ImportError, ModuleNotFoundError):
    UTOPIA_FINCA_LINKS = {
        "telegram": os.getenv("LINK_VENTAS_TELEGRAM", "https://t.me/SociosAnbelClub_bot"),
        "fanvue": os.getenv("FANVUE_LINK", "https://www.fanvue.com/luzdeaurorafeyamor")
    }


# Integración Telegram Operaciones: captura DMs al grupo, pausa IA si responde humano, puente de respuesta
try:
    from shared.telegram_operaciones import (
        send_instagram_dm_to_telegram,
        set_pending_human,
        clear_pending_human,
        consume_reply,
        consume_next_reply,
        get_client_language,
        WAIT_FOR_HUMAN_SECONDS,
    )
    TELEGRAM_OPERACIONES_ENABLED = True
except ImportError:
    TELEGRAM_OPERACIONES_ENABLED = False
    def send_instagram_dm_to_telegram(*args, **kwargs): return False
    def set_pending_human(*args, **kwargs): pass
    def clear_pending_human(*args, **kwargs): pass
    def consume_reply(*args, **kwargs): return None
    def consume_next_reply(*args, **kwargs): return None
    def get_client_language(*args, **kwargs): return None
    WAIT_FOR_HUMAN_SECONDS = 15

# Flujo automático: cuando true, el bot usa IA SIEMPRE para responder (no espera solo a humanos)
AUTO_RESPONDER_ACTIVE = os.getenv("AUTO_RESPONDER_ACTIVE", "false").lower() in ("true", "1", "yes")

# Traducción para el cliente (respuesta en su idioma)
try:
    from shared.translate_utils import translate_for_client
except ImportError:
    def translate_for_client(text, _lang): return text

logger = logging.getLogger(__name__)

# Intervalo de monitoreo en segundos (15 minutos por defecto)
MONITOR_INTERVAL = int(os.getenv("MONITOR_INTERVAL", "900"))  # 900 = 15 minutos

# --- Límites para EVITAR BLOQUEOS (ajustar en .env) ---
# Pausa entre ciclos completos (revisar posts + DMs). Más alto = más seguro.
CYCLE_SLEEP = int(os.getenv("INSTAGRAM_CYCLE_SLEEP", "30"))  # 30 = 30 seg entre ciclos (MÁS RÁPIDO)
# Máximo de respuestas a comentarios por ciclo (más generoso para cobertura total)
MAX_COMMENTS_PER_CYCLE = int(os.getenv("INSTAGRAM_MAX_COMMENTS_PER_CYCLE", "30"))
# Máximo de comentarios a los que responder por post
MAX_COMMENTS_PER_POST = int(os.getenv("INSTAGRAM_MAX_COMMENTS_PER_POST", "10"))
# Máximo de DMs a los que responder por ciclo
MAX_DMS_PER_CYCLE = int(os.getenv("INSTAGRAM_MAX_DMS_PER_CYCLE", "40"))
# Pausa mínima entre envío de un mensaje y el siguiente (segundos)
MIN_DELAY_BETWEEN_ACTIONS = float(os.getenv("INSTAGRAM_MIN_DELAY_ACTIONS", "5"))

# Persistence system for DMs (simple json)
DM_PROCESSED_FILE = Path("data/instagram_dms_processed.json")
# Lista de pendientes de re-engagement (para Dashboard: "Pendientes de responder")
PENDING_REENGAGEMENT_FILE = Path("data/instagram_pending_reengagement.json")

# Persistencia (Antigravity): conversations_map, reengagement_log
try:
    from shared.persistence import (
        get_instagram_thread_id,
        save_conversation_mapping,
        did_send_reengagement,
        record_reengagement_sent,
    )
except ImportError:
    def get_instagram_thread_id(_): return None
    def save_conversation_mapping(*args, **kwargs): pass
    def did_send_reengagement(_): return False
    def record_reengagement_sent(*args, **kwargs): pass

# Re-engagement: mensaje desde .env (Mensaje Maestro) o por defecto
# Re-engagement: mensaje desde .env (Mensaje Maestro) o por defecto
whatsapp_num_clean = os.getenv('WHATSAPP_NUMBER', '573227198007').replace('+', '').replace(' ', '')
RE_ENGAGEMENT_MSG_ES = (

    os.getenv("INSTAGRAM_RE_ENGAGEMENT_MESSAGE", "").strip()
    or f"hola amor, ¡perdóname! tenía esto colapsado 🙈 mejor entra aquí que te tengo un regalito secreto: {os.getenv('LINK_VENTAS_TELEGRAM', 'https://web-dominio-total.vercel.app/')} 🎁"
)
RE_ENGAGEMENT_MSG_EN = (
    f"Hey babe, so sorry! My inbox was crazy and I didn't see your message. 🙈 Better talk on my WhatsApp for hot chat and new pics: https://wa.me/{whatsapp_num_clean}"
)
RE_ENGAGEMENT_HOURS_MIN = int(os.getenv("INSTAGRAM_REENGAGE_HOURS_MIN", "1"))
RE_ENGAGEMENT_HOURS_MAX = int(os.getenv("INSTAGRAM_REENGAGE_HOURS_MAX", "48"))
RE_ENGAGEMENT_DELAY_MIN = int(os.getenv("INSTAGRAM_REENGAGE_DELAY_MIN", "40"))
RE_ENGAGEMENT_DELAY_MAX = int(os.getenv("INSTAGRAM_REENGAGE_DELAY_MAX", "60"))

# In-memory cache to prevent immediate re-replying if UI lags. 
# Stores username -> last_preview_text
last_processed_text = {} 


def parse_timestamp_to_hours(timestamp_str: str) -> float:
    """
    Parsea el texto del timestamp de Instagram (ej. '2h', '1d', '5 min', 'ahora') a horas atrás.
    Devuelve 0 si es 'ahora'/'now', o un valor aproximado en horas.
    """
    if not timestamp_str or not timestamp_str.strip():
        return 0.0
    s = timestamp_str.strip().lower()
    # "ahora", "now", "just now"
    if "ahora" in s or s == "now" or "just now" in s:
        return 0.0
    # minutos: "5 min", "5m", "10 min"
    m = re.search(r"(\d+)\s*m\b", s)
    if m:
        return int(m.group(1)) / 60.0
    m = re.search(r"(\d+)\s*min", s)
    if m:
        return int(m.group(1)) / 60.0
    # horas: "2h", "2 h", "23h"
    m = re.search(r"(\d+)\s*h\b", s)
    if m:
        return float(int(m.group(1)))
    # días: "1d", "2 d", "1d"
    m = re.search(r"(\d+)\s*d\b", s)
    if m:
        return float(int(m.group(1))) * 24
    # semanas
    m = re.search(r"(\d+)\s*(sem|w)\b", s)
    if m:
        return float(int(m.group(1))) * 24 * 7
    return 0.0


def save_pending_reengagement(pending_list: list) -> None:
    """Guarda la lista de pendientes de responder para el Dashboard."""
    try:
        PENDING_REENGAGEMENT_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(PENDING_REENGAGEMENT_FILE, "w", encoding="utf-8") as f:
            json.dump(pending_list, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.warning(f"Error guardando pendientes re-engagement: {e}")


def _get_reengagement_message(client_lang: str | None) -> str:
    """Mensaje de reconexión (magia colombiana) en el idioma del cliente. Siempre incluye WhatsApp."""
    whatsapp_num = os.getenv("WHATSAPP_NUMBER", "+57 322 719 8007").strip()
    if not client_lang or client_lang.lower() in ("es", "spa"):
        msg = RE_ENGAGEMENT_MSG_ES
    elif client_lang.lower() in ("en", "eng"):
        msg = RE_ENGAGEMENT_MSG_EN
    else:
        try:
            msg = translate_for_client(RE_ENGAGEMENT_MSG_ES, client_lang) or RE_ENGAGEMENT_MSG_ES
        except Exception:
            msg = RE_ENGAGEMENT_MSG_ES
    # A todos los mensajes antiguos también: asegurar que lleve el número (por si el .env no lo incluyó)
    num_limpio = whatsapp_num.replace(" ", "").replace("+", "")
    whatsapp_link = f"https://wa.me/{num_limpio}"
    
    if num_limpio not in msg.replace(" ", "").replace("+", "") and "wa.me" not in msg:
        if client_lang and client_lang.lower() in ("en", "eng"):
            msg += f"\n\nMy WhatsApp: {whatsapp_link} — text me there and I'll reply 💕"
        else:
            msg += f"\n\nMe escribes al WhatsApp {whatsapp_link} y ahí te respondo mejor 😘"
    return msg


def is_message_processed(msg_hash: str) -> bool:
    if not DM_PROCESSED_FILE.exists(): return False
    try:
        with open(DM_PROCESSED_FILE, 'r') as f:
            data = json.load(f)
            return msg_hash in data
    except: return False

def save_processed_message(msg_hash: str):
    data = []
    if DM_PROCESSED_FILE.exists():
        try:
            with open(DM_PROCESSED_FILE, 'r') as f: data = json.load(f)
        except: pass
    data.append(msg_hash)
    # Keep last 1000
    if len(data) > 1000: data = data[-1000:]
    try:
        DM_PROCESSED_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(DM_PROCESSED_FILE, 'w') as f:
            json.dump(data, f)
    except Exception as e:
        logger.error(f"Error saving processed message: {e}")


INSTAGRAM_URL = "https://www.instagram.com/luzdeaurorafeyamor/"


async def close_instagram_popups(page: Page) -> None:
    """
    Busca y cierra pop-ups típicos al loguearse: 'Ahora no', 'Guardar información', 'Not now', 'Save info'.
    Reduce interferencia para que el bot "vea" bien el inbox.
    """
    popup_buttons = [
        # Español
        'button:has-text("Ahora no")',
        'button:has-text("Guardar información")',
        'div[role="button"]:has-text("Ahora no")',
        'a[href="#"]:has-text("Ahora no")',
        # Inglés
        'button:has-text("Not Now")',
        'button:has-text("Save Info")',
        'button:has-text("Not now")',
        'div[role="button"]:has-text("Not Now")',
        'div[role="button"]:has-text("Not now")',
        # Notificaciones
        'button:has-text("Cancel")',
        'button:has-text("Cancelar")',
    ]
    for selector in popup_buttons:
        try:
            btn = page.locator(selector).first
            if await btn.is_visible(timeout=1500):
                await btn.click()
                logger.info(f"🔕 Pop-up cerrado: {selector[:50]}...")
                await random_sleep(1, 2)
                break
        except Exception:
            pass


async def reply_to_comment(page: Page, comment_element, response_text: str):
    """Responde directamente a un comentario en Instagram."""
    try:
        # Buscar el botón "Reply" cerca del comentario
        # Buscar el botón "Reply" cerca del comentario (Robustecidos selectores)
        reply_button = comment_element.locator(
            'button:has-text("Reply"), button:has-text("Responder"), '
            'div[role="button"]:has-text("Reply"), div[role="button"]:has-text("Responder"), '
            'span:has-text("Reply"), span:has-text("Responder"), '
            'svg[aria-label*="Reply"], svg[aria-label*="Responder"]'
        ).first
        
        if await reply_button.is_visible():
            await reply_button.click()
            await random_sleep(1, 2)
            
            # Buscar el campo de texto para responder (Robustecidos selectores para respuestas anidadas)
            # Instagram usa textarea o div contenteditable con role="textbox"
            textarea = comment_element.locator(
                'form textarea, '
                'textarea[placeholder*="Reply"], textarea[placeholder*="Responder"], '
                'textarea[aria-label*="Reply"], textarea[aria-label*="Responder"], '
                'div[role="textbox"][contenteditable="true"], '
                'textarea[placeholder*="Add a comment"], textarea[placeholder*="Agrega un comentario"]'
            ).first
            
            if await textarea.is_visible():
                await textarea.click()
                await random_sleep(0.5, 1)
                
                # Escribir la respuesta con typing humano
                await human_type(page, textarea, response_text)
                await random_sleep(1, 2)
                
                # Buscar el botón de enviar (Post/Publicar) - Robustecido
                # A veces es un botón, a veces un div con role="button"
                post_button = comment_element.locator(
                   'button:has-text("Post"), button:has-text("Publicar"), '
                   'div[role="button"]:has-text("Post"), div[role="button"]:has-text("Publicar")'
                ).first

                if not await post_button.is_visible():
                     # Intentar buscarlo en la página global si no está dentro del elemento comentario
                     post_button = page.locator(
                        'button:has-text("Post"), button:has-text("Publicar"), '
                        'div[role="button"]:has-text("Post"), div[role="button"]:has-text("Publicar")'
                     ).first
                
                if await post_button.is_visible():
                    await post_button.click()
                    logger.info(f"✅ Respuesta enviada en Instagram: {response_text[:50]}...")
                    await random_sleep(2, 3)
                    return True
                else:
                    logger.warning("No se encontró botón para publicar respuesta")
            else:
                logger.warning("No se encontró campo de texto para responder")
        else:
            logger.warning("No se encontró botón Reply")
            
    except Exception as e:
        logger.error(f"Error respondiendo en Instagram: {e}")
    
    return False

async def scroll_page(page: Page, times: int = 3):
    """Scrolls down the page to load more content."""
    for _ in range(times):
        await page.mouse.wheel(0, 1000)
        await random_sleep(1, 2)

async def get_latest_posts(page: Page):
    """Gets links to the latest posts. Navega al perfil si hace falta."""
    logger.info("Getting latest posts...")
    # Si no estamos en el perfil, ir
    if INSTAGRAM_URL not in page.url and "/p/" not in page.url:
        await page.goto(INSTAGRAM_URL, wait_until="domcontentloaded", timeout=30000)
        await random_sleep(3, 5)
    
    # Asegurar que estamos en la pestaña Posts (Instagram puede mostrar Reels/Tagged primero)
    for tab_text in ["Posts", "Publicaciones", "POSTS", "PUBLICACIONES"]:
        try:
            tab = page.get_by_text(tab_text, exact=True).first
            if await tab.is_visible(timeout=3000):
                await tab.click()
                await random_sleep(2, 4)
                break
        except Exception:
            pass
    
    # Scroll para cargar la cuadrícula de posts (Instagram carga lazy)
    await random_sleep(2, 3)
    for _ in range(3):
        await page.mouse.wheel(0, 600)
        await random_sleep(1, 2)
    
    # Wait for the grid (30s) — probar varios selectores
    for selector in ['a[href^="/p/"]', 'a[href*="/p/"]', 'a[href^="/reel/"]', 'a[href*="/reel/"]']:
        try:
            await page.wait_for_selector(selector, timeout=15000)
            break
        except Exception:
            continue
    else:
        logger.warning("Timeout waiting for post links (p/ or reel/). Comprueba que estés logueado y que el perfil tenga publicaciones.")
    
    links = await page.locator('a[href^="/p/"], a[href^="/reel/"]').all()
    if len(links) == 0:
        links = await page.locator('a[href*="/p/"], a[href*="/reel/"]').all()
    
    post_urls = []
    seen = set()
    for link in links:
        href = await link.get_attribute('href')
        if href and ("/p/" in href or "/reel/" in href) and href not in seen:
            seen.add(href)
            post_urls.append(href)
            # AUMENTADO A 50 PARA REVISAR POSTS ANTIGUOS
            if len(post_urls) >= 50:
                break
    logger.info(f"Found {len(post_urls)} posts (Deep Scan): {post_urls[:5]}...")
    return post_urls

async def process_post_comments(page: Page, post_url: str, max_replies_this_post: int = None) -> int:
    """Opens a post and processes its comments. Returns number of replies sent (public)."""
    max_replies_this_post = max_replies_this_post or MAX_COMMENTS_PER_POST
    replies_sent = 0
    
    full_url = f"https://www.instagram.com{post_url}" if post_url.startswith("/") else post_url
    logger.info(f"Checking post: {full_url}")
    
    await page.goto(full_url)
    await random_sleep(3, 5)
    
    # Intentar cargar todos los comentarios
    try:
        # Esperar un poco más para asegurar carga
        await random_sleep(3, 5)
        
        # Click en "Ver todos" o iconos de comentarios si existen
        buttons_to_expand = page.locator('button:has-text("View all"), button:has-text("Ver todos"), span:has-text("View all comments"), div[role="button"][aria-label*="Comment"], svg[aria-label="Comment"]').all()
        for btn in await buttons_to_expand:
            if await btn.is_visible():
                try:
                    await btn.click()
                    await random_sleep(1, 2)
                except: pass

        # Scroll para cargar
        for _ in range(3): 
            await page.mouse.wheel(0, 800)
            await random_sleep(0.5, 1)

    except:
        pass
    
    list_items = []
    try:
        # Estrategia MEJORADA: Buscar SOLO en contenedores de contenido (Main, Dialog, Article)
        # Evita la barra lateral (Nav)
        content_locators = [
            page.locator('div[role="dialog"]'), # Modal de Reel/Post
            page.locator('article'),            # Post en feed
            page.locator('main'),               # Página de post único
        ]
        
        container = None
        for loc in content_locators:
            if await loc.count() > 0 and await loc.first.is_visible():
                container = loc.first
                break
        
        if container:
            # Buscar ULs dentro del contenedor válido
            list_items = await container.locator('ul li').all()
            
            # Si no hay ULs, buscar divs con rol listitem
            if len(list_items) == 0:
                list_items = await container.locator('div[role="listitem"]').all()
                
            # Estrategia de respaldo: divs que parecen comentarios (con usuario y texto)
            if len(list_items) == 0:
                 list_items = await container.locator('div:has(a[href^="/"]):has-text("h"):not(:has-text("View all"))').all()
        else:
             # Si no encuentra contenedor principal (raro), usar estrategia defensiva
             # Excluir ULs que estén en NAV
             list_items = await page.locator('main ul li, article ul li, div[role="dialog"] ul li').all()

    except Exception as e:
        logger.warning(f"Error buscando comentarios: {e}")
    
    if len(list_items) == 0:
        logger.warning(f"⚠️ AÚN NO VEO COMENTARIOS en {full_url}. (Buris692/Jaimecedeno51 deberían estar ahí). Revisando captura de pantalla si falla mucho.")
        return replies_sent
    
    users_to_dm = [] 
    
    for i, item in enumerate(list_items):
        if replies_sent >= max_replies_this_post:
            break
        try:
            # Staleness check
            if not await item.is_visible():
                continue

            text = await item.inner_text()
            # Limpieza básica de texto para evitar errores de split
            if not text: continue
            
            # --- MEJORA: Obtener username del HREF (más seguro que texto) ---
            username = ""
            try:
                # Buscar cualquier enlace interno que parezca de perfil
                # Normalmente es el primer <a> con href="/username/"
                user_link = item.locator('a[href^="/"]').first
                if await user_link.count() > 0:
                    href = await user_link.get_attribute("href")
                    # href suele ser "/nomeusuario/" o "/longurl"
                    parts = [p for p in href.split('/') if p]
                    if parts:
                         username = parts[0]
            except: pass

            lines = [line.strip() for line in text.split('\n') if line.strip()]
            if len(lines) < 2:
                continue
            
            if not username or "explore" in username or "p" in username and len(username) < 2:
                 # Fallback a texto si href falló
                 username = lines[0]

            # Si el username parece basura (dígitos cortos o timestamps), intentar siguiente línea
            if (username.isdigit() or "hace" in username.lower() or len(username) < 2) and len(lines) > 1:
                username = lines[1] # A veces la línea 0 es "2h" y la 1 es el user

            comment_text = lines[1] if lines[1] != username else lines[-1]
            
            # Evitar respondernos a nosotros mismos
            my_user = _extract_thread_id_from_url(page.url) or "SociosAnbelClub"
            if username.lower() in [my_user.lower(), "luzdeaurorafeyamor", "sociosanbelclub"]:
                continue
            
            # Verificar si ya tiene respuesta
            has_reply = False
            try:
                reply_indicator = item.locator('text=/.*SociosAnbelClub.*/i, text=/.*Reply.*/i, text=/.*Responder.*/i').first
                if await reply_indicator.is_visible():
                    has_reply = True
            except:
                pass
            if has_reply:
                continue
                
            comment_id = f"{username}_{comment_text[:10]}_{post_url[-10:]}"
            if is_comment_processed(comment_id):
                continue
            
            # --- ESTRATEGIA: RESPONDER PÚBLICO + ENCOLAR DM ---
            
            # 1. Definir mensaje DM (pero no enviarlo todavía)
            # 1. Definir mensaje DM (pero no enviarlo todavía) - ROTACIÓN AMPLIADA PARA EVITAR SPAM
            invitacion_msg = random.choice([
                # Variaciones Directas con Link
                "Hola! 💕 Vi tu comentario. Aquí te dejo el acceso a mi espacio privado: https://web-dominio-total.vercel.app/ ✨",
                "Hola corazón, gracias por escribir. Te invito a mi club exclusivo aquí: https://web-dominio-total.vercel.app/ 🤫",
                "Hey! ✨ Si quieres ver más, te espero en mi círculo interno: https://web-dominio-total.vercel.app/",
                "Hola guapo, te comparto mi secreto aquí: https://web-dominio-total.vercel.app/ 💋",
                "Vi que comentaste... creo que esto te va a interesar: https://web-dominio-total.vercel.app/ 🔥",
                # Variaciones Misteriosas
                "Shh... 🤫 Lo que buscas está aquí: https://web-dominio-total.vercel.app/ Te espero dentro.",
                "Hola amor, para hablar más tranqui entra aquí: https://web-dominio-total.vercel.app/ Besitos 😘",
                "¿Quieres ver más? Tengo un regalo para ti en este link: https://web-dominio-total.vercel.app/ 🎁",
                # Variaciones "Club"
                "Bienvenido al club VIP. Tu acceso está listo: https://web-dominio-total.vercel.app/ Disfrútalo 😈",
                "Hola! Pásate por mi página privada, te va a encantar: https://web-dominio-total.vercel.app/ 💕",
                "Hey, por aquí no puedo mostrar mucho... mejor mira esto: https://web-dominio-total.vercel.app/ 🔥"
            ])
            
            # 2. Definir respuesta pública - ROTACIÓN AMPLIADA PARA EVITAR SPAM
            # 2. Definir respuesta pública - MÁS NATURAL Y SIN NÚMEROS RAROS
            public_reply = random.choice([
                f"@{username} Hola amor, revisa tu mensaje privado ✨",
                f"@{username} Te escribí al DM corazón 💌",
                f"@{username} Hola! Te dejé la info en el privado 🤫",
                f"@{username} Revisa tu inbox, te envié algo especial 💕",
                f"@{username} Hola guapo, mira tus solicitudes de mensaje 👀",
                f"@{username} Te acabo de escribir, revisa porfa 😘",
                f"@{username} Tienes un mensajito mío 😈",
                f"@{username} Hola! Te envié lo que pediste al DM 🔥",
                f"@{username} Revisa el privado ✨",
                f"@{username} Hola! Te dejé un regalito en el DM 🎁",
                f"@{username} Mira tus mensajes, te escribí algo 🔥",
                f"@{username} Te dejé un mensajito secreto 🤫",
                f"@{username} Hola! Revisa tu bandeja de entrada 💕",
                f"@{username} Te envié la info por privado corazón ✨",
                f"@{username} Hola! Checa tus mensajes 💌"
            ])
            
            # 3. Intentar responder PÚBLICAMENTE primero (sin salir de la página)
            success = await reply_to_comment(page, item, public_reply)
            
            if success:
                replies_sent += 1
                logger.info(f"✅ Respuesta pública enviada a @{username}. Encolando DM.")
                
                # Guardar como procesado
                from instagram_bot.comentarios_a_fanvue import save_processed_comment
                save_processed_comment(comment_id, username, comment_text, public_reply)
                
                # Agregar a la cola de DMs
                users_to_dm.append((username, invitacion_msg))
                
                await asyncio.sleep(max(0, MIN_DELAY_BETWEEN_ACTIONS - 2))
            else:
                await random_sleep(2, 3)

        except Exception as e:
            logger.error(f"Error procesando comentario {i}: {e}")
            continue
            
    # --- PROCESAR COLA DE DMs (Fuera del loop de comentarios) ---
    if users_to_dm:
        logger.info(f"📬 Iniciando envío de {len(users_to_dm)} DMs en cola...")
        for user, msg in users_to_dm:
            try:
                sent = await send_dm_to_user(page, user, msg)
                if sent:
                    logger.info(f"✅ DM enviado correctamente a @{user}")
                else:
                    logger.warning(f"❌ Falló DM a @{user}")
                await random_sleep(5, 10) # Pausa generosa entre DMs para seguridad
            except Exception as e:
                logger.error(f"Error fatal enviando DM a cola @{user}: {e}")
    
    return replies_sent

async def send_dm_to_user(page: Page, username: str, message: str) -> bool:
    """Intenta enviar un Mensaje Directo a un usuario."""
    try:
        logger.info(f"💌 Enviando DM a @{username}")
        # Navegar directo al perfil
        await page.goto(f"https://www.instagram.com/{username}/", timeout=15000)
        await random_sleep(2, 3)
        
        # Click mensaje
        msg_btn = page.locator('div[role="button"]:has-text("Message"), div[role="button"]:has-text("Enviar mensaje"), button:has-text("Message")').first
        if await msg_btn.is_visible():
            await msg_btn.click()
            await random_sleep(4, 6)
            
            # Escribir
            tb = page.locator('div[role="textbox"][contenteditable="true"]').last
            if await tb.is_visible(timeout=8000):
                await human_type(page, tb, message)
                await random_sleep(1, 2)
                await page.keyboard.press("Enter")
                return True
    except Exception as e:
        logger.error(f"Error DM @{username}: {e}")
    return False

async def check_for_notifications(page: Page):
    """Alternatives: check notifications page."""
    await page.goto("https://www.instagram.com/accounts/activity/")
    await random_sleep(3, 5)
    # Scraping notifications is also viable
    pass

# Fanvue: no se registran conversiones desde el bot; los trabajadores manejan Fanvue manualmente.

try:
    from instagram_bot.automation.responder import get_ai_reply
except ImportError:
    async def get_ai_reply(msg, user, platform="instagram"):
        return f"Hola amor, esto es un club privado. Si quieres entrar, escríbeme al DM y vemos si hay cupo ✨"

def _extract_thread_id_from_url(url: str) -> str | None:
    """Extrae el thread_id de una URL de Instagram direct: /direct/t/123456/"""
    if not url or "/direct/t/" not in url:
        return None
    import re
    m = re.search(r"/direct/t/([^/?#]+)", url)
    return m.group(1).strip() if m else None


async def open_instagram_chat_by_username(page: Page, username: str) -> bool:
    """
    Navega al chat de Instagram. Optimización: si tenemos thread_id guardado, entra directo.
    Si no, busca por nombre como antes.
    Usado por el puente Telegram -> Instagram (respuestas de operaciones).
    """
    try:
        # Optimización: entrar directo si tenemos thread_id guardado
        thread_id = get_instagram_thread_id(username)
        if thread_id:
            direct_url = f"https://www.instagram.com/direct/t/{thread_id}/"
            await page.goto(direct_url, wait_until="domcontentloaded", timeout=15000)
            await random_sleep(2, 4)
            if "/direct/" in page.url and thread_id in page.url:
                logger.debug(f"✅ Chat abierto directo por thread_id para @{username}")
                return True
            # Si falló, continuar con búsqueda por nombre

        await page.goto("https://www.instagram.com/direct/inbox/")
        await random_sleep(2, 4)
        try:
            await page.wait_for_selector('text=Primary', timeout=12000)
        except Exception:
            pass
        # Buscar campo de búsqueda en el inbox
        search_input = page.locator('input[placeholder*="Search"], input[placeholder*="Buscar"], input[aria-label*="Search"], input[type="search"]').first
        if await search_input.is_visible(timeout=5000):
            await search_input.click()
            await random_sleep(0.5, 1)
            await search_input.fill("")
            await random_sleep(0.3, 0.5)
            await search_input.fill(username)
            await random_sleep(2, 4)
            # Clic en primera conversación que contenga el username
            conv_link = page.locator(f'a[href*="/direct/t/"]').first
            if await conv_link.is_visible(timeout=5000):
                await conv_link.click()
                await random_sleep(2, 4)
                if "/direct/" in page.url:
                    # Guardar thread_id para la próxima vez
                    tid = _extract_thread_id_from_url(page.url)
                    if tid:
                        save_conversation_mapping(username, instagram_thread_id=tid)
                    return True
        # Fallback: scroll y buscar texto del username
        for _ in range(5):
            row = page.get_by_text(username, exact=False).first
            if await row.is_visible(timeout=2000):
                await row.click()
                await random_sleep(2, 4)
                if "/direct/" in page.url:
                    tid = _extract_thread_id_from_url(page.url)
                    if tid:
                        save_conversation_mapping(username, instagram_thread_id=tid)
                    return True
            await page.mouse.wheel(0, 400)
            await random_sleep(0.5, 1)
    except Exception as e:
        logger.warning(f"Error abriendo chat de @{username}: {e}")
    return False


async def process_telegram_reply_queue(page: Page):
    """
    Procesa la cola de respuestas desde Telegram Operaciones: abre cada chat en Instagram
    y envía el texto con la instancia de Playwright actual (no cierra sesión).
    """
    if not TELEGRAM_OPERACIONES_ENABLED:
        return
    from shared.telegram_operaciones import consume_next_reply, get_client_language
    sent = 0
    while True:
        item = consume_next_reply()
        if not item:
            break
        username = (item.get("username") or "").strip()
        text = (item.get("text") or "").strip()
        if not username or not text:
            continue
        # Traducir respuesta del trabajador al idioma del cliente si está guardado
        try:
            client_lang = get_client_language(username)
            if client_lang:
                text = translate_for_client(text, client_lang) or text
                logger.info(f"🌐 Puente: respuesta traducida a {client_lang} para @{username}.")
        except Exception as e:
            logger.debug(f"Traducción en puente falló: {e}")
        if await open_instagram_chat_by_username(page, username):
            try:
                textbox = page.locator('div[role="textbox"][contenteditable="true"]').last
                if await textbox.is_visible(timeout=5000):
                    await textbox.fill(text)
                    await random_sleep(1, 2)
                    await page.keyboard.press("Enter")
                    logger.info(f"✅ Puente Telegram->Instagram: respuesta enviada a @{username}")
                    sent += 1
            except Exception as e:
                logger.warning(f"Error enviando puente a @{username}: {e}")
        await random_sleep(1, 2)
    if sent:
        logger.info(f"📤 Puente: {sent} respuesta(s) de Telegram enviadas a Instagram.")


async def check_instagram_inbox(page: Page):
    """
    Checks Instagram Inbox for unread messages and replies.
    Uses robust text-based selectors to avoid brittle class names.
    Integración Telegram Operaciones: envía DMs al grupo, espera respuesta humana antes de IA.
    """
    logger.info("📩 Checking Instagram Inbox...")
    try:
        await page.goto("https://www.instagram.com/direct/inbox/")
        # Wait for inbox to load (look for 'Primary' or 'General' tabs)
        try:
            await page.wait_for_selector('text=Primary', timeout=12000)
        except:
            logger.warning("Could not verify Inbox load (Primary tab not found). Skipping.")
            return

        await random_sleep(2, 4)
        await close_instagram_popups(page)
        await random_sleep(1, 2)

        # 1. SCROLL DOWN TO LOAD MORE MESSAGES (más profundo para chats 24–48h)
        logger.info("Scrolling down to reveal more conversations (deep scroll for 24–48h chats)...")
        try:
            inbox_list = page.locator('div[aria-label="Direct messages list"], div[aria-label="Lista de mensajes directos"]').first
            if await inbox_list.is_visible():
                for _ in range(25):  # Más veces para cargar chats de hace 24–48h
                    await inbox_list.evaluate('el => el.scrollTop += 1000')
                    await random_sleep(0.4, 1.0)
            else:
                for _ in range(18):  # Fallback: más scroll con rueda
                    await page.mouse.wheel(0, 2000)
                    await random_sleep(0.8, 1.5)
        except Exception as e:
            logger.warning(f"Scroll failed: {e}")

        await random_sleep(2, 3)

        # 2. FIND UNREPLIED CONVERSATIONS
        # Strategy: 
        # A) Look for unread dots (svg/div often with specific aria-label or color)
        # B) Look for bold text (font-weight: 600+)
        # C) Check if "Tú:"/"You:" is NOT in preview (fallback)
        
        # Get elements matching timestamp as anchor points
        # Fixing regex for localization and including "now/ahora"
        timestamp_regex = re.compile(r"^(\d+\s*(min|h|d|sem|w|y|s|m)|ahora|now|just now)$", re.IGNORECASE)
        time_elements = await page.get_by_text(timestamp_regex).all()
        logger.info(f"Found {len(time_elements)} potential conversations with timestamps.")
        
        # Lista de pendientes de responder (1h–48h) para el Dashboard
        pending_list = []
        conversations_checked = 0
        MAX_CHECKS = 100 # Increased from 50 for full catch-up
        
        for i, time_el in enumerate(time_elements):
            if conversations_checked >= MAX_DMS_PER_CYCLE:
                logger.info(f"Límite de DMs por ciclo ({MAX_DMS_PER_CYCLE}) alcanzado.")
                break
            if conversations_checked >= MAX_CHECKS:
                break
            if not await time_el.is_visible():
                continue

            try:
                # Encontrar la fila clicable: selectores simples uno por uno (sin XPath con |).
                row_candidate = None
                try:
                    cand = time_el.locator("xpath=./ancestor::div[@role='button']").first
                    if await cand.count() > 0:
                        row_candidate = cand
                except Exception:
                    pass
                if not row_candidate or await row_candidate.count() == 0:
                    try:
                        cand = time_el.locator('xpath=./ancestor::a[contains(@href,"/direct/t/")]').first
                        if await cand.count() > 0:
                            row_candidate = cand
                    except Exception:
                        pass
                if not row_candidate or await row_candidate.count() == 0:
                    try:
                        cand = time_el.locator("xpath=./ancestor::a[contains(@href,'/direct/')]").first
                        if await cand.count() > 0:
                            row_candidate = cand
                    except Exception:
                        pass
                if not row_candidate or await row_candidate.count() == 0:
                    try:
                        cand = time_el.locator("xpath=..").locator("xpath=..").locator("xpath=..").first
                        if await cand.count() > 0:
                            row_candidate = cand
                    except Exception:
                        pass
                
                if not row_candidate or await row_candidate.count() == 0:
                    continue

                # Leer texto de la fila: inner_text, text_content o evaluación (para que detecte bien el preview)
                raw_preview = ""
                try:
                    raw_preview = await row_candidate.inner_text()
                except Exception:
                    pass
                if not (raw_preview and raw_preview.strip()):
                    try:
                        raw_preview = await row_candidate.evaluate('el => el.textContent || ""')
                    except Exception:
                        pass
                if not (raw_preview and raw_preview.strip()):
                    try:
                        raw_preview = await row_candidate.locator('span, div').first.inner_text()
                    except Exception:
                        pass
                preview_text = (raw_preview or "").replace('\n', ' ').strip()
                # Ignorar mensajes del sistema de Instagram (no son DMs de usuarios)
                system_message_patterns = [
                    "te has perdido un chat", "you missed a video chat", "video chat",
                    "llamada perdida", "missed call", "chat de vídeo", "video call",
                    "empezó una llamada", "started a call", "solicitud de llamada",
                ]
                lower_raw = (raw_preview or "").lower()
                if any(p in lower_raw for p in system_message_patterns):
                    logger.info(f"⏭️ Skipping system message (not a user DM): '{preview_text[:50]}...'")
                    continue
                # Timestamp para filtro re-engagement (1h–48h)
                try:
                    timestamp_text = (await time_el.inner_text()).strip()
                except Exception:
                    timestamp_text = ""
                if not timestamp_text:
                    try:
                        timestamp_text = (await time_el.text_content()).strip() or ""
                    except Exception:
                        pass
                hours_ago = parse_timestamp_to_hours(timestamp_text)
                
                # DETECTION LOGIC:
                unread_indicator = row_candidate.locator('div[style*="background-color: rgb(0, 149, 246)"], div[style*="background-color: var(--ig-primary-button)"], svg[aria-label="Unread"], svg[aria-label="Sin leer"]').first
                is_unread = await unread_indicator.is_visible()
                if not is_unread:
                    try:
                        bold_el = row_candidate.locator("span[style*='font-weight: 600'], span[style*='font-weight: 700'], div[style*='font-weight: 600'], div[style*='font-weight: 700']").first
                        is_unread = await bold_el.is_visible()
                    except Exception:
                        pass

                # Quién envió el último mensaje: Tú/You (nosotros) vs cliente
                is_from_us = False
                lower_preview = preview_text.lower()
                # Indicadores de "último mensaje nuestro" (español, inglés y variantes)
                from_us_indicators = [
                    "tú:", "you:", "enviado", "sent",
                    "tú ", "you ", "tú:", "you:",
                    "sent ", "enviado ", "enviados ", "sent.",
                ]
                for indicator in from_us_indicators:
                    if indicator in lower_preview or lower_preview.startswith(indicator.strip()):
                        is_from_us = True
                        break
                # Detección por "You:" / "Tú:" en el preview (último mensaje nuestro)
                if not is_from_us and re.search(r"\b(you|tú|tu)\s*:\s*", lower_preview, re.IGNORECASE):
                    is_from_us = True
                
                if is_from_us and not is_unread:
                    # Detailed reason
                    # logger.info(f"Skipping {i}: Replied (preview: '{preview_text[:20]}...') and not marked unread.")
                    continue
                
                # Pendientes para Dashboard: último mensaje del cliente, sin responder
                row_username = (raw_preview.split('\n')[0].strip() or "Usuario")[:50]
                pending_list.append({
                    "username": row_username,
                    "hours_ago": round(hours_ago, 1),
                    "preview": preview_text[:80],
                })
                # Filtro de tiempo: solo procesar mensajes entre 1h y RE_ENGAGEMENT_HOURS_MAX para re-engagement
                if hours_ago > RE_ENGAGEMENT_HOURS_MAX:
                    logger.info(f"⏭️ Skipping {row_username}: mensaje hace {hours_ago:.0f}h (>{RE_ENGAGEMENT_HOURS_MAX}h), no re-engagement.")
                    continue
                
                # If we get here, we might want to reply
                logger.info(f"💬 Found potential unreplied message! Unread: {is_unread}, FromUs: {is_from_us}, ~{hours_ago:.0f}h ago, Text: '{preview_text[:50]}...'")
                
                # Double check: if it's from us but marked as unread, maybe it's a multi-person chat or IG bug?
                # Usually best to reply if UNREAD.
                
                # Click to open
                await row_candidate.click()
                await random_sleep(3, 5)

                # EXTRACT USERNAME
                username = row_username # Use the name found in the inbox list as first candidate
                try:
                    # Specific selectors for Instagram chat header (more reliable)
                    header_selectors = [
                        'header span[role="link"]',
                        'div[role="main"] header h2',
                        'div[role="main"] header h1',
                        'div[role="main"] header span.x1lliihq',
                        'header span.x1lliihq'
                    ]
                    for sel in header_selectors:
                        el = page.locator(sel).first
                        if await el.is_visible():
                            text = (await el.inner_text()).strip()
                            if text and 2 < len(text) < 50:
                                username = text
                                break
                except:
                    pass
                
                if not username or len(username) < 2:
                    username = row_username or "Subscriber"

                # Guardar thread_id para futuras visitas directas (optimización)
                tid = _extract_thread_id_from_url(page.url)
                if tid:
                    save_conversation_mapping(username, instagram_thread_id=tid)
                
                # Check Persistence (to prevent double replies)
                msg_hash = f"{username}_{preview_text[:20]}_{len(preview_text)}"
                
                # Verificar si ya procesamos este mensaje exacto
                if is_message_processed(msg_hash):
                    logger.info(f"⏭️ Skipping {username}: Message hash already processed ({msg_hash[:20]}...).")
                    await page.goto("https://www.instagram.com/direct/inbox/")
                    continue
                
                # Verificar si el texto es exactamente igual al último procesado
                if last_processed_text.get(username) == preview_text:
                    logger.info(f"⏭️ Skipping {username}: Text unchanged from last message.")
                    await page.goto("https://www.instagram.com/direct/inbox/")
                    continue
                
                # Verificar si ya respondimos hace menos de 5 minutos (evitar spam)
                last_response_time = last_processed_text.get(f"{username}_time", 0)
                if time.time() - last_response_time < 300:  # 5 minutos
                    logger.info(f"⏭️ Skipping {username}: Responded recently ({int(time.time() - last_response_time)}s ago).")
                    await page.goto("https://www.instagram.com/direct/inbox/")
                    continue

                # --- INTELLIGENT REPLY GENERATION ---
                # (Same logic as before, but ensure we extract the message text from the last message in the chat)
                # instead of just the preview.
                
                # Wait for messages to load (20s para dar tiempo a cargar el chat)
                try:
                    await page.wait_for_selector('div[role="row"], div[class*="x78zum5"], div[dir="auto"]', timeout=20000)
                except Exception:
                    logger.warning("Timeout waiting for message rows. Attempting to proceed with available elements.")

                # Selectores ampliados para leer el texto interno del chat (quién envió el último mensaje)
                all_messages = await page.locator(
                    'div[role="row"], div[class*="x1n2on33"], div[class*="xexx8yu"], '
                    'div[data-scope="messages"] div, section div[dir="auto"]'
                ).all()
                if not all_messages:
                    logger.warning("No messages found in opened chat.")
                else:
                    last_msg_el = all_messages[-1]
                    try:
                        last_message_text = await last_msg_el.inner_text()
                    except Exception:
                        last_message_text = ""
                    if not (last_message_text and last_message_text.strip()):
                        try:
                            last_message_text = await last_msg_el.evaluate('el => el.textContent || ""')
                        except Exception:
                            last_message_text = ""
                    last_message_text = (last_message_text or "").strip()
                    
                    # --- DETECCIÓN MULTIMEDIA (Fotos/Audios) ---
                    # Si no hay texto o el texto es genérico, revisamos elementos visuales
                    if not last_message_text or last_message_text.lower() in ["imagen", "foto", "nota de voz", "audio", "voice clip"]:
                        # Buscar imágenes en el último mensaje
                        imgs = await last_msg_el.locator('img').all()
                        if imgs:
                            last_message_text = "[IMAGEN_CLIENTE]"
                            logger.info(f"📸 Detección visual: El cliente envió una imagen.")
                        
                        # Buscar audios (etiquetas de accesibilidad comunes en IG para clips de voz)
                        voice_indicators = await last_msg_el.locator('[aria-label*="voz"], [aria-label*="voice"], [aria-label*="audio"]').all()
                        if voice_indicators:
                            last_message_text = "[AUDIO_CLIENTE]"
                            logger.info(f"🔊 Detección visual: El cliente envió un audio.")
                        
                        # Si sigue vacío pero hay contenido, marcar como imagen por defecto (común en burbujas de IG)
                        if not last_message_text:
                            # Verificar si la burbuja tiene un contenedor de medios
                            media_container = await last_msg_el.locator('div[class*="x1n2on33"]').count()
                            if media_container > 0:
                                last_message_text = "[IMAGEN_CLIENTE]"
                                logger.info(f"🖼️ Detección por contenedor: Tratando como imagen.")
                    
                    # --- INTELLIGENT REPLY GENERATION ---
                    response = None
                    voice_file = None
                    
                    use_reengagement = RE_ENGAGEMENT_HOURS_MIN <= hours_ago <= RE_ENGAGEMENT_HOURS_MAX
                    if use_reengagement:
                        # Memoria de saludos: no enviar dos veces el mismo recordatorio al mismo cliente
                        # Solo saltamos si el nombre NO es genérico, para evitar falsos positivos
                        is_generic = username in ["Subscriber", "Usuario", "Instagram User", "Usuario de Instagram"]
                        if did_send_reengagement(username) and not is_generic:
                            logger.info(f"⏭️ Skipping re-engagement @{username}: ya recibió recordatorio antes.")
                            await page.goto("https://www.instagram.com/direct/inbox/")
                            continue
                        client_lang = get_client_language(username) if TELEGRAM_OPERACIONES_ENABLED else None
                        response = _get_reengagement_message(client_lang)
                        logger.info(f"📢 Re-engagement (magia colombiana) para @{username} (~{hours_ago:.0f}h)")
                    else:
                        # --- Traducción de Entrada para Operaciones ---
                        # Se detecta idioma, se traduce a español si es necesario y se guarda el idioma del cliente
                        try:
                            from shared.translate_utils import detect_language
                            detected_lang = detect_language(last_message_text)
                            if detected_lang and detected_lang.lower() != "es":
                                save_client_language(username, detected_lang)
                                logger.info(f"🌐 Idioma detectado para @{username}: {detected_lang}")
                        except Exception as e:
                            logger.debug(f"Error detectando idioma de entrada: {e}")

                        # --- Telegram Operaciones: Espera para intervención humana incluso con IA activa ---
                        wait_human_seconds = int(os.getenv("INSTAGRAM_WAIT_FOR_HUMAN_SECONDS", "15"))
                        
                        if TELEGRAM_OPERACIONES_ENABLED:
                            # Envía a Telegram (esta función ya traduce si detectó idioma)
                            send_instagram_dm_to_telegram(username, last_message_text)
                            set_pending_human(username, last_message_text[:50])
                            
                            logger.info(f"⏳ Ventana de {wait_human_seconds}s para intervención humana (@{username})...")
                            deadline = time.time() + wait_human_seconds
                            while time.time() < deadline:
                                human_response = consume_reply(username)
                                if human_response is not None and human_response.strip():
                                    response = human_response.strip()
                                    logger.info(f"👤 Respuesta humana recibida por Telegram para @{username}.")
                                    # Auditoría: Marcar como respuesta humana
                                    save_conversation_mapping(username, last_responder="HUMAN_RESPONSE")
                                    break
                                await asyncio.sleep(2)
                                    
                            clear_pending_human(username)
                        
                        # Si no hubo respuesta humana, generar con IA / fallback
                        if response is None:
                            # Incrementar contador de mensajes para rastrear seguridad
                            from shared.persistence import increment_message_count, get_message_count
                            msg_count = increment_message_count(username)
                            
                            # Auditoría: Marcar como respuesta de IA
                            save_conversation_mapping(username, last_responder="AI_RESPONSE")
                            
                            # Obtener respuesta inteligente con VOZ (Realismo Extremo)
                            try:
                                from ai_models.ai_handler import AIHandler
                                ai = AIHandler()
                                context = f"Conversación con @{username}. Mensaje #{msg_count}. "
                                if msg_count < 5:
                                    context += "REGLA: No envíes links directos aún. Enfócate en conectar. Usa AUDIO BAIT si es natural."
                                else:
                                    context += "Ya hay confianza, puedes sugerir el 'link en mi bio'. Prueba a usar un audio para convencerlo."
                                
                                # Usar respuesta con voz (genera texto + path de audio)
                                result = await ai.get_response_with_voice(last_message_text, user_id=username, context=context)
                                response = result.get("text")
                                voice_file = result.get("voice_file")
                                
                                logger.info(f"🤖 IA Response for @{username} (Msg #{msg_count}): {response[:50]}...")
                                if voice_file:
                                    logger.info(f"🎙️ Generado audio para @{username}: {voice_file}")
                            except Exception as e:
                                logger.error(f"Error generando respuesta de IA con voz: {e}")
                                response = "Hola mi amor, qué lindo verte por aquí 💕 Mira el link de mi bio y hablemos mejor 😘"
                                voice_file = None

                    # --- Traducción de Salida (Cliente) ---
                    # Antes de enviar, traducimos al idioma original del cliente si se detectó alguno
                    try:
                        client_lang = get_client_language(username) if TELEGRAM_OPERACIONES_ENABLED else None
                        if client_lang and response:
                            from shared.translate_utils import translate_for_client
                            translated = translate_for_client(response, client_lang)
                            if translated:
                                logger.info(f"🌐 Respuesta traducida del español al {client_lang} para @{username}.")
                                response = translated
                    except Exception as e:
                        logger.debug(f"Traducción de salida falló para @{username}: {e}")

                    # Type and send
                    textbox = page.locator('div[role="textbox"][contenteditable="true"]').last
                    if await textbox.is_visible():
                        # Si hay audio, intentar enviarlo primero o después
                        if voice_file and os.path.exists(voice_file):
                            try:
                                # Buscar botón de adjuntar (clip o imagen)
                                attach_btn = page.locator('svg[aria-label="Adjuntar contenido multimedia"], svg[aria-label="Add Photo or Video"], input[type="file"]').first
                                if await attach_btn.is_visible(timeout=3000):
                                    async with page.expect_file_chooser() as fc_info:
                                        if await attach_btn.count() > 0 and await attach_btn.get_attribute("type") == "file":
                                            await attach_btn.set_input_files(voice_file)
                                        else:
                                            await attach_btn.click()
                                        file_chooser = await fc_info.value
                                        await file_chooser.set_files(voice_file)
                                    logger.info(f"📤 Audio enviado a @{username}")
                                    await random_sleep(3, 5)
                            except Exception as e:
                                logger.warning(f"No se pudo enviar el archivo de audio: {e}")

                        await textbox.fill(response)
                        await random_sleep(2, 4)
                        await page.keyboard.press("Enter")
                        logger.info(f"✅ Sent reply to {username}: {response}")
                        
                        # Save to persistence
                        save_processed_message(msg_hash)
                        
                        conversations_checked += 1
                        # Guardar texto Y timestamp para evitar repeticiones
                        last_processed_text[username] = preview_text
                        last_processed_text[f"{username}_time"] = time.time()
                        # Memoria de saludos: registrar que ya enviamos re-engagement a este cliente
                        if use_reengagement:
                            record_reengagement_sent(username, response[:80] if response else "")
                            delay = random.uniform(RE_ENGAGEMENT_DELAY_MIN, RE_ENGAGEMENT_DELAY_MAX)
                            logger.info(f"⏳ Re-engagement: pausa {delay:.0f}s antes del siguiente mensaje.")
                            await asyncio.sleep(delay)
                        else:
                            await asyncio.sleep(max(0, MIN_DELAY_BETWEEN_ACTIONS - 2))
                    else:
                        logger.warning("Could not find textbox.")
                    
                    if conversations_checked >= MAX_DMS_PER_CYCLE:
                        logger.info(f"Límite de DMs por ciclo alcanzado ({MAX_DMS_PER_CYCLE}), pausando inbox.")
                        break
                
                # Return to inbox
                await page.goto("https://www.instagram.com/direct/inbox/")
                await page.wait_for_selector('text=Primary', timeout=12000)
                await random_sleep(2, 4)
                
            except Exception as e:
                logger.error(f"Error handling convo {i}: {e}")
                if "inbox" not in page.url:
                     await page.goto("https://www.instagram.com/direct/inbox/")
                     await random_sleep(2,3)

        # Guardar pendientes para el Dashboard (Pendientes de responder: N, Último mensaje de: X hace Y horas)
        save_pending_reengagement(pending_list)

    except Exception as e:
        logger.error(f"Error in check_instagram_inbox: {e}")

async def process_old_conversations(page: Page):
    """
    Re-engagement: usa la misma estrategia que check_instagram_inbox (timestamps + ancestros)
    para encontrar conversaciones antiguas y no depender de selectores que fallen.
    """
    logger.info("📢 Starting Re-Engagement Campaign (Old Users)...")
    try:
        await page.goto("https://www.instagram.com/direct/inbox/")
        try:
            await page.wait_for_selector('text=Primary', timeout=12000)
        except Exception:
            logger.warning("Re-engagement: Inbox no cargó (Primary no encontrado).")
            return
        await random_sleep(2, 4)
        await close_instagram_popups(page)
        await random_sleep(1, 2)
        
        # Mismo scroll que en check_instagram_inbox para cargar conversaciones
        try:
            inbox_list = page.locator('div[aria-label="Direct messages list"], div[aria-label="Lista de mensajes directos"]').first
            if await inbox_list.is_visible():
                for _ in range(25):
                    await inbox_list.evaluate('el => el.scrollTop += 1000')
                    await random_sleep(0.4, 1.0)
            else:
                for _ in range(18):
                    await page.mouse.wheel(0, 2000)
                    await random_sleep(0.8, 1.5)
        except Exception as e:
            logger.warning(f"Re-engagement scroll failed: {e}")
        await random_sleep(2, 3)
        
        # Mismos anclas que en inbox: elementos con timestamp
        timestamp_regex = re.compile(r"^(\d+\s*(min|h|d|sem|w|y|s|m)|ahora|now|just now)$", re.IGNORECASE)
        time_elements = await page.get_by_text(timestamp_regex).all()
        logger.info(f"Found {len(time_elements)} potential old conversations (same strategy as inbox).")
        
        count = 0
        for time_el in time_elements:
            if count >= 10:
                break
            if not await time_el.is_visible():
                continue
            try:
                row_candidate = None
                for selector_try in [
                    ("xpath=./ancestor::div[@role='button']", time_el.locator("xpath=./ancestor::div[@role='button']").first),
                    ("xpath=./ancestor::a[contains(@href,'/direct/t/')]", time_el.locator('xpath=./ancestor::a[contains(@href,"/direct/t/")]').first),
                    ("xpath=..", time_el.locator("xpath=..").locator("xpath=..").locator("xpath=..").first),
                ]:
                    try:
                        cand = selector_try[1]
                        if await cand.count() > 0:
                            row_candidate = cand
                            break
                    except Exception:
                        pass
                if not row_candidate or await row_candidate.count() == 0:
                    continue
                text = ""
                try:
                    text = await row_candidate.inner_text()
                except Exception:
                    pass
                if not text or not text.strip():
                    try:
                        text = await row_candidate.evaluate('el => el.textContent || ""')
                    except Exception:
                        pass
                text_lower = (text or "").lower()
                if any(p in text_lower for p in ["te has perdido un chat", "you missed a video", "video chat", "llamada perdida", "missed call"]):
                    continue
                # Extraer nombre para el log
                try:
                    username = (text.split('\n')[0].strip() or "Subscriber")[:50]
                except Exception:
                    username = "Subscriber"

                try:
                    ts_text = (await time_el.inner_text()).strip()
                except Exception:
                    ts_text = ""
                hours_ago = parse_timestamp_to_hours(ts_text)
                if hours_ago < RE_ENGAGEMENT_HOURS_MIN or hours_ago > RE_ENGAGEMENT_HOURS_MAX:
                    logger.info(f"⏭️ Skipping {username}: hace {hours_ago:.0f}h fuera de rango ({RE_ENGAGEMENT_HOURS_MIN}-{RE_ENGAGEMENT_HOURS_MAX}h).")
                    continue
                await row_candidate.click()
                await random_sleep(4, 6)
                # Refinar username tras abrir el chat si es posible
                try:
                    username_el = page.locator('span[class*="x1lliihq"], h2, h1').first
                    if await username_el.is_visible(timeout=3000):
                        username = (await username_el.inner_text()).split('\n')[0].strip()
                        if len(username) > 30:
                            username = username[:30]
                except Exception:
                    pass
                if not username or len(username) < 2:
                    username = "Subscriber"
                # Guardar thread_id para futuras visitas directas
                tid = _extract_thread_id_from_url(page.url)
                if tid:
                    save_conversation_mapping(username, instagram_thread_id=tid)
                # Memoria de saludos: no enviar dos veces el mismo recordatorio
                if did_send_reengagement(username):
                    logger.info(f"⏭️ Skipping re-engagement @{username}: ya recibió recordatorio antes.")
                    await page.goto("https://www.instagram.com/direct/inbox/")
                    continue
                try:
                    client_lang = get_client_language(username) if TELEGRAM_OPERACIONES_ENABLED else None
                except Exception:
                    client_lang = None
                re_engage_msg = _get_reengagement_message(client_lang)
                textbox = page.locator('div[role="textbox"][contenteditable="true"]').last
                if await textbox.is_visible(timeout=5000):
                    await textbox.fill(re_engage_msg)
                    await random_sleep(2, 5)
                    await page.keyboard.press("Enter")
                    record_reengagement_sent(username, re_engage_msg[:80])
                    logger.info(f"📢 Re-engaged {username} (magia colombiana): {re_engage_msg[:50]}...")
                    count += 1
                    last_processed_text[username] = "RE_ENGAGED"
                    delay = random.uniform(RE_ENGAGEMENT_DELAY_MIN, RE_ENGAGEMENT_DELAY_MAX)
                    await asyncio.sleep(delay)
                await page.goto("https://www.instagram.com/direct/inbox/")
                await random_sleep(2, 4)
            except Exception as e:
                logger.debug(f"Re-engagement row skipped: {e}")
                if "inbox" not in page.url:
                    await page.goto("https://www.instagram.com/direct/inbox/")
                    await random_sleep(2, 3)
    except Exception as e:
        logger.error(f"Error in process_old_conversations: {e}")

async def run_monitor():
    """Main monitor loop. Ahora con reinicio automático de navegador si se cierra."""
    while True:
        logger.info("🚀 Iniciando/Reiniciando sesión de navegador para Instagram... headless=False")
        context = None
        page = None
        try:
            context = await get_browser_context(headless=False, profile_name="instagram_session_v3") 
            page = await context.new_page()
            
            logger.info(f"🌐 Navegando a Instagram: {INSTAGRAM_URL}")
            await page.goto(INSTAGRAM_URL, wait_until="domcontentloaded", timeout=60000)
            logger.info("✅ Página cargada (DOM).")
            await random_sleep(3, 5)
            await close_instagram_popups(page)
            await random_sleep(1, 2)
            
            # Check login initially
            if "login" in page.url or await page.locator('input[name="username"]').is_visible():
                logger.warning("⚠️ IG NOT LOGGED IN! Please login manually in the open window.")
            
            # Infinite Monitor Loop
            cycles = 0
            while True:
                try:
                    cycles += 1
                    logger.info(f"🔄 Instagram Cycle {cycles} starting...")
                    
                    # Check login
                    if "login" in page.url:
                         logger.warning("Check login...")
                         await asyncio.sleep(10)
                    
                    # 0. Puente Telegram -> Instagram
                    await process_telegram_reply_queue(page)
                    
                    # 1. CHECK POSTS (ir al perfil primero; si estamos en inbox no hay posts)
                    if "/direct/" in page.url or "inbox" in page.url.lower():
                        await page.goto(INSTAGRAM_URL, wait_until="domcontentloaded", timeout=30000)
                        await random_sleep(3, 5)
                    post_urls = await get_latest_posts(page)
                    if len(post_urls) > 20:
                        post_urls = post_urls[:20]
                    total_comments_replied = 0
                    for link in post_urls:
                        if total_comments_replied >= MAX_COMMENTS_PER_CYCLE:
                            logger.info(f"Límite de comentarios por ciclo alcanzado ({MAX_COMMENTS_PER_CYCLE}).")
                            break
                        n = await process_post_comments(page, link)
                        total_comments_replied += n
                        await random_sleep(2, 4)

                    # 2. CHECK DIRECT MESSAGES
                    await check_instagram_inbox(page)

                    # 3. RE-ENGAGEMENT
                    await process_old_conversations(page)

                    logger.info(f"💤 Ciclo completo. Pausa {CYCLE_SLEEP}s para evitar bloqueos...")
                    await asyncio.sleep(CYCLE_SLEEP)
                    
                    # Telegram forwarding ELIMINADO por solicitud del usuario (Enfoque 100% Instagram)
        # try:
        #    await telegram_bot.send_message(...)
        # except: pass
                    
                except Exception as e:
                    logger.error(f"Error en monitor loop: {e}")
                    if "closed" in str(e).lower() or "not open" in str(e).lower():
                        logger.warning(f"Detectado cierre de navegador: {e}. Reiniciando ciclo...")
                        break # Salir del bucle interno para reiniciar contexto
                    await asyncio.sleep(30)

        except Exception as e:
            logger.error(f"Error fatal en monitor Instagram: {e}", exc_info=True)
            await asyncio.sleep(10) # Pausa breve antes de reiniciar
        finally:
            if context:
                try:
                    await context.close()
                except: pass
            logger.info("♻️ Reiniciando proceso completo de monitor...")
            await asyncio.sleep(5)

if __name__ == "__main__":
    # Configure logging to console and file
    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    logging.basicConfig(
        level=logging.INFO,
        format=log_format,
        handlers=[
            logging.FileHandler("skill_automation.log", encoding='utf-8'),
            logging.StreamHandler()
        ]
    )
    asyncio.run(run_monitor())
