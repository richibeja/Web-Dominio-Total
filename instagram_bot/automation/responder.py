import asyncio
import os
import sys
from pathlib import Path

# Agregar el directorio raíz del proyecto al path para permitir ejecución independiente
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)
import json
import logging
import random
from datetime import datetime
from pathlib import Path
from playwright.async_api import Page
from instagram_bot.automation.browser_utils import get_browser_context, random_sleep
try:
    from config.utopia_finca_links import LINKS as UTOPIA_FINCA_LINKS
except (ImportError, ModuleNotFoundError):
    UTOPIA_FINCA_LINKS = {
        "telegram": os.getenv("LINK_VENTAS_TELEGRAM", "https://t.me/SociosAnbelClub_bot"),
        "fanvue": os.getenv("FANVUE_LINK", "https://www.fanvue.com/luzdeaurorafeyamor")
    }


logger = logging.getLogger(__name__)

FANVUE_URL = "https://www.fanvue.com"
DATA_FILE = Path("data/comentarios_para_fanvue.json")
PROCESSED_FILE = Path("data/instagram_comments_processed.json")

async def send_dm(page: Page, username: str, message: str):
    """Envía un DM en Fanvue usando estrategia de novia virtual."""
    try:
        logger.info(f"📤 Intentando enviar mensaje a {username} en Fanvue...")
        logger.info(f"📝 Mensaje: {message[:150]}...")
        
        # Asegurar que estamos en /messages
        await ensure_messages_page(page)
        
        # Buscar campo de búsqueda o botón "New Message"
        search_success = False
        try:
            # Intentar buscar al usuario
            search_input = page.locator('input[placeholder*="Search"], input[type="search"], input[aria-label*="search"], input[placeholder*="Buscar"]').first
            if await search_input.is_visible(timeout=5000):
                await search_input.click()
                await random_sleep(0.5, 1)
                # Limpiar campo primero
                await search_input.fill("")
                await random_sleep(0.3, 0.5)
                # Escribir username
                await search_input.fill(username)
                logger.info(f"🔍 Buscando usuario: {username}")
                await random_sleep(3, 5)  # Esperar resultados
                
                # Buscar resultados de búsqueda - SOLO en el área de mensajes
                # Evitar resultados de "discover" o videos
                await random_sleep(2, 3)  # Esperar que aparezcan resultados
                
                # Primero buscar solo links de mensajes
                message_results = await page.locator('a[href*="/messages/"]').all()
                if not message_results:
                    # Fallback: buscar cualquier resultado pero filtrar
                    all_results = await page.locator('div[role="button"], a, button').all()
                    message_results = []
                    for r in all_results:
                        try:
                            href = await r.get_attribute("href") or ""
                            if "/messages/" in href:
                                message_results.append(r)
                        except:
                            pass
                
                if message_results:
                    # Filtrar solo resultados que sean de mensajes (no videos, no discover)
                    for result in message_results[:10]:  # Revisar más resultados
                        try:
                            result_text = await result.inner_text()
                            href = await result.get_attribute("href") or ""
                            
                            # Verificar que NO sea un video o contenido de discover
                            is_video = "/video/" in href or "/post/" in href or "/discover" in href or "/creator/" in href or "/profile/" in href
                            
                            if is_video:
                                logger.info(f"⏭️ Saltando resultado de video/discover: {href}")
                                continue  # Saltar videos
                            
                            # Si contiene el username, seleccionarlo
                            if username.lower() in result_text.lower():
                                logger.info(f"🎯 Encontrado usuario {username} en resultado")
                                await result.click()
                                await random_sleep(3, 5)
                                
                                # Verificar que estamos en una página de mensaje
                                current_url = page.url
                                if "/messages/" in current_url:
                                    search_success = True
                                    logger.info(f"✅ Usuario {username} encontrado y seleccionado")
                                    break
                                else:
                                    # Si nos llevó a otra página, volver
                                    logger.warning(f"⚠️ El clic nos llevó a {current_url}, volviendo a /messages")
                                    await ensure_messages_page(page)
                                    continue
                        except Exception as e:
                            logger.debug(f"Error procesando resultado: {e}")
                            continue
                
                # Si no se encontró, intentar el primer resultado que sea de mensajes
                if not search_success and message_results:
                    logger.info("⚠️ Usuario no encontrado, usando primer resultado de mensajes")
                    try:
                        await message_results[0].click()
                        await random_sleep(3, 5)
                        if "/messages/" in page.url:
                            search_success = True
                            logger.info(f"✅ Usando primer resultado de mensajes")
                        else:
                            await ensure_messages_page(page)
                    except:
                        await ensure_messages_page(page)
        except Exception as e:
            logger.warning(f"Búsqueda falló: {e}, intentando método alternativo...")
        
        # Si no hay búsqueda, intentar crear nuevo mensaje
        if not search_success:
            try:
                new_message_btn = page.locator('button:has-text("New"), button:has-text("Nuevo"), a[href*="message"], button:has-text("Message")').first
                if await new_message_btn.is_visible():
                    await new_message_btn.click()
                    await random_sleep(2, 3)
                    logger.info("✅ Botón 'Nuevo mensaje' encontrado")
            except:
                logger.warning("No se encontró botón de nuevo mensaje")
        
        # Buscar campo de texto del mensaje (múltiples intentos)
        message_sent = False
        for attempt in range(3):
            try:
                message_input = page.locator('textarea, div[contenteditable="true"], input[type="text"], [class*="Input"], [class*="textArea"]').last
                if await message_input.is_visible(timeout=5000):
                    await message_input.click()
                    await random_sleep(0.5, 1)
                    
                    # Limpiar campo primero
                    await message_input.fill("")
                    await random_sleep(0.3, 0.5)
                    
                    # Escribir mensaje con delay humano
                    logger.info(f"⌨️ Escribiendo mensaje a {username}...")
                    await message_input.fill(message)  # Usar fill es más rápido y confiable
                    await random_sleep(1, 2)
                    
                    # Verificar que el mensaje se escribió
                    written_text = await message_input.inner_text() if await message_input.get_attribute("contenteditable") else await message_input.input_value()
                    if message[:50] in written_text or len(written_text) > 10:
                        logger.info(f"✅ Mensaje escrito correctamente ({len(written_text)} caracteres)")
                    else:
                        logger.warning(f"⚠️ El mensaje no se escribió correctamente. Reintentando...")
                        continue
                    
                    # Enviar mensaje
                    send_button = page.locator('button[type="submit"], button:has-text("Send"), button:has-text("Enviar"), svg[aria-label*="Send"], [aria-label*="Send"]').first
                    if await send_button.is_visible(timeout=3000):
                        await send_button.click()
                        logger.info(f"✅ Mensaje enviado a {username} en Fanvue")
                        await random_sleep(2, 3)
                        message_sent = True
                        
                        # Volver a /messages después de enviar
                        await ensure_messages_page(page)
                        break
                    else:
                        # Intentar con Enter
                        await page.keyboard.press("Enter")
                        logger.info(f"✅ Mensaje enviado con Enter a {username}")
                        await random_sleep(2, 3)
                        message_sent = True
                        
                        # Volver a /messages después de enviar
                        await ensure_messages_page(page)
                        break
            except Exception as e:
                logger.warning(f"Intento {attempt + 1} falló: {e}")
                await random_sleep(1, 2)
                continue
        
        if message_sent:
            return True
        else:
            logger.error(f"❌ No se pudo enviar mensaje a {username} después de 3 intentos")
            # Screenshot para debug
            try:
                await page.screenshot(path=f"data/debug_fanvue/send_dm_failed_{username}_{int(datetime.now().timestamp())}.png")
            except:
                pass
            return False
        
    except Exception as e:
        logger.error(f"❌ Error enviando DM en Fanvue a {username}: {e}", exc_info=True)
        return False

async def send_audio(page: Page, audio_path: str):
    """Sube un archivo de audio al chat de Fanvue."""
    try:
        if not audio_path or not Path(audio_path).exists():
            return False

        logger.info(f"🎤 Subiendo audio: {audio_path}")
        
        # Buscar botón de adjuntar (clip o imagen)
        # Fanvue suele tener un input file oculto
        file_input = page.locator('input[type="file"]').first
        
        if await file_input.is_visible() or await file_input.is_hidden():
            # Playwright puede subir archivos incluso si el input está oculto
            await file_input.set_input_files(audio_path)
            await random_sleep(2, 3)
            
            # Presionar enviar
            send_button = page.locator('button:has-text("Send"), button:has-text("Enviar"), button[type="submit"], svg[aria-label*="Send"]').first
            if await send_button.is_visible():
                await send_button.click()
                logger.info("✅ Audio enviado correctamente")
                return True
                
        logger.warning("No se encontró input para subir audio")
        return False
    except Exception as e:
        logger.error(f"Error uploading audio: {e}")
        return False


from instagram_bot.comentarios_a_fanvue import ai_handler, generate_response_for_comment

async def get_ai_reply(last_network_message: str, username: str, platform: str = "fanvue") -> str:
    """Generates a reply using the AI Handler with platform-specific context."""
    
    if platform == "instagram":
        # Contexto para INSTAGRAM DM: seducir, enamorar, llevar a WHATSAPP
        context = (
            f"Estás chateando por DM de Instagram con un seguidor ({username}). "
            f"Él escribió: '{last_network_message}'. "
            f"OBJETIVO: Enamorarlo con tu personalidad PAISA. Sé dulce, coqueta y muy humana. "
            f"Sugiérele ir a tu WhatsApp si la charla fluye, para hablar más tranqui o mandarle audios. "
            f"REGLA: NO menciones Telegram ni enlaces de Telegram. Solo WhatsApp para contacto. "
            f"REGLA DE ORO: No vendas. SE UNA NOVIA. Responde como una chica de 25 años en chat. "
            f"USA MUCHO: 'mor', 'bebé', 'pues', 'jaja'. Casi todo en minúsculas. "
            f"Si hablas de tu WhatsApp, que parezca un favor que le haces: 'ay mor, pásame tu Whats y te mando audios por allá q me da pereza escribir aquí 🙈'. "
            f"WHATSAPP: {os.getenv('WHATSAPP_NUMBER', '+57 322 719 8007')} "
        )
    elif platform == "instagram_reengage":
        # Contexto para RE-ENGAGEMENT
        context = (
            f"Estás revisando tus mensajes antiguos en Instagram y ves a ({username}). Hace tiempo no hablas con él. "
            f"Él no ha escrito nada reciente, tú quieres 'despertarlo'. "
            f"OBJETIVO: Ser muy natural, sutil y humana. NO envíes el link de Fanvue ahora. "
            f"1. Saluda de forma casual: 'Hola! tanto tiempo...', 'Me acordé de ti..', '¿Cómo va todo?'. "
            f"2. Sé muy espontánea, como si estuvieras aburrida revisando DMs. "
            f"3. Usa lenguaje natural de chat (minúsculas, abreviaturas, pocos emojis). "
            f"4. NO menciones que eres una IA o un bot. "
        )
    else:
        # Contexto para FANVUE (Ya están ahí - Estrategia Freemium/PPV)
        # Meta: VENDER PPV / INTERACTUAR / RETENER.
        context = (
            f"Estás chateando por privado en Fanvue con un suscriptor ({username}). "
            f"Él escribió: '{last_network_message}'. "
            f"ESTRATEGIA: Él entró gratis, ahora tu trabajo es venderle contenido bloqueado (PPV). "
            f"ACTÚA COMO SU NOVIA VIRTUAL (GF Experience - Trato de Amante). "
            f"1. ERES SU AMANTE: Cariñosa, caliente, celosa de broma, atenta. "
            f"2. HAZLE SENTIR EL REY: 'Eres mi favorito', 'Estaba esperando tu mensaje...'. "
            f"3. INCITA A LA ACCIÓN (VENTA): Siempre insinúa que tienes algo nuevo para él. "
            f"4. FRASES GANCHO: 'Bebé, mira lo que te envié por bloqueado...', 'Te subí algo solo para tus ojos...', '¿Ya viste el video que te mandé? Me puse muy traviesa...'. "
            f"5. USA LENGUAJE PROVOCATIVO: Emojis de fuego, besos, duraznos. Sé explícita pero seductora. "
            f"6. PIDE PROPINAS / APOYO: Sutilmente menciona tus gastos del niño o renta: 'Si me ayudas con la renta hoy, te mando una sorpresa que te va a encantar...'. "
            f"7. NO REGALES NADA: Todo el contenido fuerte debe ser de pago. "
        )

    try:
        # Using ai_handler directly if available
        # Modificado para soportar audio
        if hasattr(ai_handler, 'get_response_with_voice'):
            response_data = await ai_handler.get_response_with_voice(last_network_message, user_id=username, context=context)
            text = response_data.get("text", "")
            audio = response_data.get("voice_file")
            
            if audio:
                # Retornar texto + marcador de audio para que el responder lo detecte
                return f"{text} [AUDIO:{audio}]"
            return text
            
        return await ai_handler.get_response(last_network_message, user_id=username, context=context)
    except Exception as e:
        logger.error(f"Error getting AI reply: {e}")
        import random
        whatsapp_num = os.getenv("WHATSAPP_NUMBER", "+57 322 719 8007").strip()
        fallbacks = [
            f"Ay mor qué pena con vos, me falló el internet un segundo... Pero cuéntame {username} 💕 ¿en qué íbamos?",
            f"Hola {username} 🙈 Te perdí un momento... ¿qué más me decías mor?",
            f"Ay {username} tan lindo que me escribís... aquí Instagram me tiene loca borrando cosas 🙈 mejor me escribes al WhatsApp {whatsapp_num} y ahí te contesto 😘",
            f"Mor se me está trabando esta vaina 😭 escríbeme al Whats {whatsapp_num} que allá sí me carga rápido, dale?",
            f"¿Sigues ahí corazón? 💕 Se me cerró el chat... cuéntamelo todo.",
            f"Bebé, mi señal está horrible hoy 😩... Si no te respondo rápido es por eso. ¿Tienes WhatsApp? Háblame al {whatsapp_num}",
            f"Hola amor ✨ Me quedé esperando tu mensaje... ¿qué pasó?",
            f"Uy mor, casi no me carga esto. Mejor vente a mi WhatsApp {whatsapp_num} y te mando foticos más fácil 📸",
            f"Me encantas {username}... sigue contándome, que soy toda oídos (y ojos) 👀",
            f"Perdón la demora guapo, estaba terminando de arreglarme 💅 ¿En qué quedamos?"
        ]
        return random.choice(fallbacks)

async def process_old_fanvue_conversations(page: Page):
    """
    Re-engagement Campaign para Fanvue: Responde mensajes antiguos sin respuesta.
    """
    logger.info("📢 Iniciando Re-engagement en Fanvue (mensajes antiguos)...")
    try:
        # Asegurar que estamos en /messages
        await ensure_messages_page(page)
        
        # Scroll down para cargar conversaciones antiguas
        logger.info("Haciendo scroll para encontrar conversaciones antiguas...")
        for _ in range(15):  # Scroll más profundo para encontrar conversaciones antiguas
            await page.mouse.wheel(0, 2000)
            await random_sleep(0.5, 1)
        
        await random_sleep(3, 5)
        
        # Buscar todas las conversaciones visibles
        all_conversations = await page.locator('a[href*="/messages/"], div[role="button"], div[role="listitem"]').all()
        logger.info(f"Encontradas {len(all_conversations)} conversaciones totales en Fanvue")
        
        old_conversations = []
        count = 0
        MAX_OLD_CHECKS = 20  # Procesar hasta 20 conversaciones antiguas por ciclo
        
        for conv in all_conversations:
            if count >= MAX_OLD_CHECKS:
                break
                
            if not await conv.is_visible():
                continue
                
            try:
                # Obtener texto de la conversación para verificar si es antigua
                conv_text = await conv.inner_text()
                conv_text_lower = conv_text.lower()
                
                # Verificar si es una conversación antigua (no tiene "hace", "min", "seg" recientes)
                # O tiene indicadores de tiempo antiguo como "d", "sem", "mes"
                is_old = any(indicator in conv_text_lower for indicator in ["d", "sem", "mes", "week", "month", "day", "día"])
                is_recent = any(indicator in conv_text_lower for indicator in ["hace", "min", "seg", "h", "ago", "now", "ahora"])
                
                # Si es antigua y no reciente, procesarla
                if is_old and not is_recent:
                    old_conversations.append(conv)
                    count += 1
                    
            except Exception as e:
                logger.debug(f"Error verificando conversación: {e}")
                continue
        
        logger.info(f"📋 Encontradas {len(old_conversations)} conversaciones antiguas para procesar")
        
        # Procesar cada conversación antigua
        for i, conv in enumerate(old_conversations[:10]):  # Máximo 10 por ciclo
            try:
                conv_name = (await conv.inner_text()).strip().split("\n")[0] if await conv.is_visible() else f"Chat {i}"
                logger.info(f"💬 Revisando conversación antigua {i+1}: {conv_name}")
                
                # Click para abrir
                await conv.click(force=True)
                await random_sleep(8, 12)
                
                # Buscar mensajes
                messages = await page.locator('[class*="Message"], [class*="bubble"], [class*="text"], main p, main span').all()
                if not messages:
                    messages = await page.locator('main [class*="text"], main [class*="bubble"], main p, main span').all()
                
                if not messages:
                    await ensure_messages_page(page)
                    continue
                
                # Verificar si el último mensaje es de nosotros
                last_msg = messages[-1]
                is_from_us = False
                
                try:
                    classes = (await last_msg.get_attribute("class") or "").lower()
                    if any(k in classes for k in ["sent", "mine", "own", "right", "creator", "me"]):
                        is_from_us = True
                    else:
                        box = await last_msg.bounding_box()
                        if box:
                            page_width = page.viewport_size["width"]
                            if box["x"] > (page_width * 0.6):
                                is_from_us = True
                except:
                    pass
                
                # Si el último mensaje NO es de nosotros, responder
                if not is_from_us:
                    last_text = (await last_msg.inner_text()).strip()
                    if not last_text:
                        last_text = await last_msg.locator('span, div[class*="text"]').first.inner_text() if await last_msg.locator('span, div[class*="text"]').count() > 0 else ""
                        last_text = last_text.strip() if last_text else ""
                    
                    if last_text:
                        # Verificar si ya respondimos a este mensaje
                        msg_hash = f"{last_text[:20]}_{len(last_text)}"
                        if not is_message_processed(msg_hash):
                            # Obtener username
                            username_el = page.locator('header div div h2, header div div h3, header span[class*="header"]').first
                            username = await username_el.inner_text() if await username_el.is_visible() else "baby"
                            
                            logger.info(f"💌 Mensaje antiguo sin respuesta de {username}: {last_text[:30]}...")
                            
                            # Generar respuesta
                            reply_text = await get_ai_reply(last_text, username, platform="fanvue")
                            
                            # Enviar respuesta
                            input_selector = 'textarea, div[contenteditable="true"], input[type="text"], [class*="Input"], [class*="textArea"]'
                            message_input = page.locator(input_selector).last
                            
                            if await message_input.is_visible():
                                await message_input.click()
                                await random_sleep(0.5, 1)
                                await message_input.fill(reply_text)
                                await random_sleep(1, 2)
                                
                                send_button = page.locator('button[type="submit"], button:has(svg[aria-label*="Send"]), button:has(svg), [aria-label*="Send"], [class*="SendButton"]').last
                                if await send_button.is_visible():
                                    await send_button.click()
                                    logger.info(f"✅ Respondido mensaje antiguo de {username}")
                                    save_processed_message(msg_hash)
                                    await random_sleep(3, 5)
                
                # Volver a la lista de mensajes
                await page.goto(f"{FANVUE_URL}/messages")
                await random_sleep(3, 5)
                
            except Exception as e:
                logger.error(f"Error procesando conversación antigua {i}: {e}")
                try:
                    await page.goto(f"{FANVUE_URL}/messages")
                    await random_sleep(2, 3)
                except:
                    pass
                continue
                
    except Exception as e:
        logger.error(f"Error en process_old_fanvue_conversations: {e}")

async def ensure_messages_page(page: Page):
    """
    Asegura que estamos en la página de mensajes y no en otras secciones.
    Cierra cualquier video, modal o popup que pueda estar abierto.
    """
    current_url = page.url
    messages_url = f"{FANVUE_URL}/messages"
    
    # Detectar si estamos en una página de video, discover o contenido
    unwanted_pages = ["/video/", "/post/", "/discover", "/creator/", "/profile/", "/feed"]
    is_unwanted = any(unwanted in current_url for unwanted in unwanted_pages)
    
    # Detectar si estamos en una página de login/auth o similar
    auth_pages = ["/login", "/auth", "/signin", "/signup", "/verify", "/2fa"]
    is_auth = any(auth_path in current_url.lower() for auth_path in auth_pages)
    
    if is_auth:
        logger.info(f"🔑 Detectada página de autenticación ({current_url}). Esperando a que el usuario termine...")
        await random_sleep(15, 30)
        return
        
    if is_unwanted:
        logger.warning(f"⚠️ Estamos en página no deseada: {current_url}, cerrando y yendo a /messages...")
        # Intentar cerrar con Escape primero
        try:
            await page.keyboard.press("Escape")
            await random_sleep(1, 2)
        except:
            pass
    
    # Si no estamos en /messages, ir ahí
    if "/messages" not in current_url:
        logger.info(f"⚠️ No estamos en /messages (estamos en: {current_url}), navegando...")
        await page.goto(messages_url, wait_until="domcontentloaded", timeout=60000)
        await random_sleep(3, 5)
    
    # Cerrar cualquier popup, modal o video que pueda aparecer
    max_close_attempts = 5
    for attempt in range(max_close_attempts):
        try:
            # Cerrar modales de video o contenido
            close_buttons = [
                'button[aria-label*="Close"]',
                'button:has-text("Close")',
                'button:has-text("Cerrar")',
                '[class*="close"]',
                '[class*="Close"]',
                'svg[aria-label*="Close"]',
                '[aria-label*="close"]',
                '[aria-label*="Close"]'
            ]
            
            closed_something = False
            for selector in close_buttons:
                try:
                    close_btn = page.locator(selector).first
                    if await close_btn.is_visible(timeout=1000):
                        await close_btn.click()
                        logger.info(f"✅ Cerrado popup/modal (intento {attempt + 1})")
                        await random_sleep(1, 2)
                        closed_something = True
                        break
                except:
                    continue
            
            # Si no encontramos botón de cerrar, intentar Escape
            if not closed_something:
                try:
                    await page.keyboard.press("Escape")
                    await random_sleep(1, 2)
                except:
                    pass
            
            # Verificar que seguimos en /messages después de cerrar
            if is_unwanted:
                logger.warning("⚠️ Se salió de /messages después de cerrar, volviendo...")
                await page.goto(messages_url, wait_until="domcontentloaded", timeout=60000)
                await random_sleep(2, 3)
            else:
                # Si estamos en /messages, salir del loop
                break
                
        except Exception as e:
            logger.debug(f"Error cerrando popup (intento {attempt + 1}): {e}")
            if attempt < max_close_attempts - 1:
                await random_sleep(1, 2)
    
    # Verificación final
    if "/messages" not in page.url and is_unwanted:
        logger.warning("⚠️ Verificación final: no estamos en /messages y es página no deseada, forzando navegación...")
        await page.goto(messages_url, wait_until="domcontentloaded", timeout=60000)
        await random_sleep(2, 3)
    
    logger.debug(f"✅ Asegurado que estamos en /messages: {page.url}")

async def check_inbox(page: Page):
    """
    Checks Fanvue Inbox for unread or unanswered messages.
    """
    logger.info("📩 Verificando Inbox de Fanvue (mensajes nuevos)...")
    try:
        # Asegurar que estamos en /messages
        await ensure_messages_page(page)
        
        # 0. Handle Cookie Banners
        try:
            cookie_button = page.locator('button:has-text("OK"), button:has-text("Accept"), button:has-text("Aceptar")').first
            if await cookie_button.is_visible():
                await cookie_button.click()
                logger.info("Aceptadas cookies.")
                await random_sleep(1, 2)
                # Verificar que seguimos en /messages
                await ensure_messages_page(page)
        except: pass

        # 1. Estrategia de detección por marcas de tiempo (V7)
        # Buscamos elementos que contengan "hace", "ago", "h", "d", "m"
        time_selectors = [':text("hace")', ':text("ago")', ':text(" min ")', ':text(" h ")', ':text(" d ")', ':text(" seg ")']
        
        # Intentar cerrar popups
        try:
            close_btn = page.locator('button:has(svg[data-testid*="Close text-secondary"]), button:has-text("Descartar"), [aria-label*="Close"]').first
            if await close_btn.is_visible():
                await close_btn.click()
                logger.info("Cerrada ventana emergente detectada.")
        except: pass

        # Búsqueda basada en tiempos
        conversations = []
        seen_texts = set()
        
        for ts in time_selectors:
            try:
                found = await page.locator(ts).all()
                for el in found:
                    # Subir al padre que sea clicable (a, button, [role=button], [role=listitem])
                    # Usamos una búsqueda de ancestro
                    parent_button = el.locator('xpath=./ancestor::*[self::a or self::button or @role="button" or @role="listitem"]').first
                    if await parent_button.is_visible():
                        txt = await parent_button.inner_text()
                        if txt not in seen_texts:
                            conversations.append(parent_button)
                            seen_texts.add(txt)
            except: pass

        if not conversations:
            logger.info(f"Detección por tiempo fallida. Intentando búsqueda por link /messages/.")
            conversations = await page.locator('a[href*="/messages/"]:not([class*="nav"])').all()
        
        logger.info(f"👉 Encontradas {len(conversations)} conversaciones reales.")
        
        if not conversations:
            logger.info(f"Fanvue no encontró conversaciones en el primer intento. Re-intentando...")
            await random_sleep(5, 7)
            # Intentar búsqueda alternativa: cualquier elemento clicable que contenga texto de tiempo
            all_candidates = await page.locator('div[role="button"], a, button').all()
            conversations = []
            ui_exclusions = ["settings", "configuración", "logout", "cerrar sesión", "menu", "menú"]
            for c in all_candidates:
                try:
                    txt = (await c.inner_text() or "").lower()
                    if any(x in txt for x in ["hace", "seg", "min", "hora", "día", "day", "hour", "ago"]):
                        if not any(ex in txt for ex in ui_exclusions):
                            conversations.append(c)
                except: pass

        logger.info(f"👉 Encontradas {len(conversations)} conversaciones reales.")
        
        if not conversations:
            await page.screenshot(path="data/fanvue_debug_v6_null.png")
            return

        # 2. Bucle de procesamiento
        for i in range(min(len(conversations), 10)): 
            try:
                # Usar el locator ya encontrado (Playwright lo mantendrá si es posible)
                conv = conversations[i]
                
                # Intentar obtener el nombre para el log
                try: 
                    conv_name = (await conv.inner_text()).strip().split("\n")[0]
                except: 
                    conv_name = f"Chat {i}"
                
                # Verificar que estamos en /messages antes de hacer clic
                await ensure_messages_page(page)
                
                # Click para abrir - solo si es un link a /messages/
                old_url = page.url
                logger.info(f"💬 Abriendo chat {i}: {conv_name}")
                
                # Verificar que el elemento es realmente un link de mensaje
                try:
                    href = await conv.get_attribute("href")
                    if href and "/messages/" in href:
                        # Es un link válido de mensaje, hacer clic
                        await conv.click(force=True)
                    else:
                        # Intentar navegar directamente al link si existe
                        if href:
                            await page.goto(f"{FANVUE_URL}{href}" if href.startswith("/") else href)
                        else:
                            # Si no tiene href, intentar clic pero verificar después
                            await conv.click(force=True)
                except:
                    # Si no se puede obtener href, hacer clic normal
                    await conv.click(force=True)
                
                await random_sleep(5, 8)
                
                # Verificar que estamos en una página de mensaje (no en discover u otra sección)
                current_url = page.url
                if "/messages/" not in current_url and "/messages" not in current_url:
                    logger.warning(f"⚠️ El clic nos llevó fuera de /messages (URL: {current_url}), volviendo...")
                    await ensure_messages_page(page)
                    continue  # Saltar esta conversación
                
                # Captura para debug
                debug_dir = Path("data/debug_fanvue")
                debug_dir.mkdir(parents=True, exist_ok=True)
                path = f"data/debug_fanvue/click_{i}_{int(datetime.now().timestamp())}.png"
                await page.screenshot(path=path)
                
                # Buscar burbujas de mensaje
                msg_selector = '[class*="Message"], [class*="bubble"], [class*="text"], main p, main span'
                messages = await page.locator(msg_selector).all()
                
                if not messages:
                    logger.info("No se detectaron burbujas estándar, buscando cualquier texto en el área principal...")
                    messages = await page.locator('main [class*="text"], main [class*="bubble"], main p, main span').all()

                if not messages:
                    continue
                    
                # Saltar el "AI Creator Coach" opcionalmente
                try:
                    header_el = page.locator('header, [class*="Header"], h2').first
                    header_text = (await header_el.inner_text(timeout=5000) or "").lower()
                    if "ai creator coach" in header_text:
                        logger.info("🤖 Este es el AI Creator Coach. Saltando.")
                        continue
                except:
                    logger.info("No se pudo leer el encabezado (timeout o no existe), continuando con la extracción de mensajes.")

                last_msg = messages[-1]
                
                is_from_us = False
                try:
                    # Check for common 'sent' classes
                    classes = (await last_msg.get_attribute("class") or "").lower()
                    # Fanvue often uses 'Message_sent' or 'Message_creator'
                    if any(k in classes for k in ["sent", "mine", "own", "right", "creator", "me"]):
                        is_from_us = True
                    else:
                        # Check horizontal position
                        box = await last_msg.bounding_box()
                        if box:
                            page_width = page.viewport_size["width"]
                            # If the message starts in the right 40% of the page
                            if box["x"] > (page_width * 0.6):
                                is_from_us = True
                                # logger.info(f"Detected as FROM US via position (x={box['x']})")
                except: pass

                # Extract text more robustly - sometimes inner_text on bubble is empty but child span has it
                last_text = (await last_msg.inner_text()).strip()
                if not last_text:
                    # try getting text from any span/div inside
                    last_text = await last_msg.locator('span, div[class*="text"]').first.inner_text()
                    last_text = last_text.strip() if last_text else ""
                
                # If STILL empty, try a very expensive search for any text in that row
                if not last_text:
                    last_text = await last_msg.evaluate("el => el.textContent")
                    last_text = last_text.strip() if last_text else ""

                logger.info(f"💬 Conversación {i} Último Msg: '{last_text[:20]}...' Enviado por nosotros: {is_from_us}")

                if not last_text:
                    continue

                if is_from_us:
                    # logger.info(f"Last message in {i} is from us. Skipping.")
                    continue
                
                # If we just replied, we probably shouldn't reply again immediately.
                # We need a way to know if we already processed this.
                # We can store the text hash in our JSON.
                
                # Let's assume we reply if we haven't seen this message hash.
                msg_hash = f"{last_text[:20]}_{len(last_text)}"
                
                if is_message_processed(msg_hash):
                    # logger.info(f"Message '{last_text[:10]}...' already replied.")
                    continue
                
                # If it's seemingly from us (contains common phrases we use? No that's risky)
                # Let's rely on the processed check.
                
                # GENERATE REPLY
                # We need the username.
                # Username in Fanvue chat header usually in a h2 or h3 or span
                username_el = page.locator('header div div h2, header div div h3, header span[class*="header"]').first

                username = await username_el.inner_text() if await username_el.is_visible() else "baby"
                
                logger.info(f"💌 New message from {username}: {last_text[:30]}...")
                
                reply_text = await get_ai_reply(last_text, username)
                
                # Check for Audio Marker
                audio_path = None
                if "[AUDIO:" in reply_text:
                    try:
                        parts = reply_text.split("[AUDIO:")
                        reply_text = parts[0].strip()
                        audio_path = parts[1].replace("]", "").strip()
                    except:
                         pass

                # SEND REPLY
                # (Reuse send logic code)
                input_selector = 'textarea, div[contenteditable="true"], input[type="text"], [class*="Input"], [class*="textArea"]'
                message_input = page.locator(input_selector).last
                
                if await message_input.is_visible():
                    await message_input.click()
                    await random_sleep(0.5, 1)
                    await message_input.fill(reply_text)
                    await random_sleep(1, 2)
                    
                    # Robust send button search
                    send_button = page.locator('button[type="submit"], button:has(svg[aria-label*="Send"]), button:has(svg), [aria-label*="Send"], [class*="SendButton"]').last
                    if await send_button.is_visible():
                        await send_button.click()
                        logger.info(f"✅ Fanvue Auto-replied to {username}")
                        
                        # Send Audio strategically (30% chance or if specific keywords found)
                        should_voice = audio_path is not None
                        voice_keywords = ["voz", "audio", "escuhar", "habla", "dime", "cuenta"]
                        if any(k in last_text.lower() for k in voice_keywords):
                            should_voice = True
                        
                        if should_voice or random.random() < 0.3:
                            if not audio_path:
                                # Generate voice specifically for the last message if not already done
                                # this is a fallback if get_ai_reply didn't return audio
                                pass 
                            if audio_path:
                                await send_audio(page, audio_path)
                        
                        save_processed_message(msg_hash)
                        # Adaptive safety delay for bulk catch-up
                        await random_sleep(3, 5)
                        
                        # Volver a /messages después de responder
                        await ensure_messages_page(page)
                
            except Exception as e:
                logger.error(f"❌ Error procesando conversación {i}: {e}")
                # Asegurar que volvemos a /messages después de error
                await ensure_messages_page(page)
                continue
        
        # Al final, asegurar que estamos en /messages
        await ensure_messages_page(page)
                
    except Exception as e:
        logger.error(f"Error in check_inbox: {e}")
        # Asegurar que volvemos a /messages después de error
        try:
            await ensure_messages_page(page)
        except:
            pass

# Persistence system for DMs (simple json)
DM_PROCESSED_FILE = Path("data/fanvue_dms_processed.json")

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
    with open(DM_PROCESSED_FILE, 'w') as f:
        json.dump(data, f)


async def run_responder():
    """Reads pending comments AND checks inbox. Ahora con reinicio automático de navegador si se cierra."""
    while True:
        logger.info("🚀 Iniciando/Reiniciando sesión de navegador para Fanvue... headless=False")
        context = None
        page = None
        messages_url = f"{FANVUE_URL}/messages"
        try:
            context = await get_browser_context(headless=False, profile_name="fanvue_session")
            page = await context.new_page()
            
            # Intentar cargar Fanvue; si falla (login, timeout), reintentar SIN cerrar la ventana
            for attempt in range(1, 11):
                try:
                    logger.info(f"🌐 Navegando a Fanvue Mensajes (intento {attempt})...")
                    await page.goto(messages_url, wait_until="domcontentloaded", timeout=45000)
                    logger.info("✅ Página cargada (DOM).")
                    await random_sleep(3, 5)
                    break
                except Exception as e:
                    logger.warning(f"⚠️ No se pudo cargar Fanvue: {e}")
                    # Si el navegador se cerró, salir para volver a empezar
                    if "closed" in str(e).lower():
                        raise e
                    logger.info("👉 Si la ventana pide login, inicia sesión ahora. Reintentando en 20s...")
                    await asyncio.sleep(20)
            else:
                logger.error("No se pudo cargar Fanvue tras varios intentos. Reiniciando navegador...")
                raise Exception("Max initial load attempts reached")

            # Infinite Loop for cycles
            cycles = 0
            while True:
                try:
                    cycles += 1
                    logger.info(f"🔄 Fanvue Cycle {cycles} starting...")
                    
                    # Asegurar que estamos en /messages al inicio de cada ciclo
                    await ensure_messages_page(page)
                    
                    # PAUSA DE SEGURIDAD PARA EVITAR BUCLES LOCOS
                    await random_sleep(10, 20)
                    
                    # 1. PROCESS PENDING OUTBOUND MESSAGES (From Instagram REDIRECTS)
                    pending = []
                    if DATA_FILE.exists():
                        try:
                            with open(DATA_FILE, 'r', encoding='utf-8') as f:
                                pending = json.load(f)
                        except: pending = []

                    if pending:
                        logger.info(f"📤 Processing {len(pending)} pending outbound messages...")
                        
                        pending_updates = False
                        for item in pending:
                            status = item.get("status", "pending")
                            if status == "pending":
                                username = item["username"]
                                response = item["response"]
                                
                                # Verificar que el mensaje tenga el link
                                fanvue_link = os.getenv("FANVUE_LINK", "https://www.fanvue.com/SociosAnbelClub")
                                if fanvue_link not in response:
                                    logger.warning(f"⚠️ Mensaje para {username} NO tiene link! Agregando...")
                                    response = f"{response}\n\nay mor, se me olvidaba pasarte mi link para q hablemos más rico por allá 🙈 es gratis entrar: {fanvue_link}"
                                    item["response"] = response
                                
                                # Verificar que mencione que es gratis
                                if "gratis" not in response.lower() and "free" not in response.lower():
                                    logger.warning(f"⚠️ Mensaje para {username} NO menciona que es gratis! Agregando...")
                                    response = response.replace(fanvue_link, f"{fanvue_link} (ay bebé, y recordá q entrar es gratis pues, no tenés q pagar nada para verme 💋)")
                                    item["response"] = response
                                
                                logger.info(f"📨 Enviando a {username}: {response[:100]}...")
                                success = await send_dm(page, username, response)
                                if success:
                                    item["status"] = "sent"
                                    pending_updates = True
                                    logger.info(f"✅ Mensaje enviado exitosamente a {username} en Fanvue")
                                else:
                                    logger.error(f"❌ FALLO al enviar mensaje a {username}")
                                await random_sleep(2, 4)
                        
                        if pending_updates:
                             with open(DATA_FILE, 'w', encoding='utf-8') as f:
                                json.dump(pending, f, indent=2, ensure_ascii=False)
                    
                    # 2. CHECK INBOX (AUTO-REPLY - mensajes nuevos)
                    await check_inbox(page)
                    
                    # Asegurar que seguimos en /messages después de check_inbox
                    await ensure_messages_page(page)
                    
                    # 3. PROCESS OLD CONVERSATIONS (Re-engagement - mensajes antiguos)
                    # Solo cada 5 ciclos para no ser demasiado agresivo
                    if cycles % 5 == 0:
                        logger.info("📢 Ejecutando re-engagement de mensajes antiguos...")
                        await process_old_fanvue_conversations(page)
                        # Asegurar que volvemos a /messages
                        await ensure_messages_page(page)
                    
                    logger.info("💤 Fanvue cycle complete. Waiting 60s...")
                    await asyncio.sleep(60)

                except Exception as e:
                    logger.error(f"Error in Fanvue loop (Cycle {cycles}): {e}")
                    await asyncio.sleep(60)
                    try:
                        await page.reload()
                    except:
                        pass
            
        except Exception as e:
            logger.error(f"Error fatal en responder Fanvue: {e}", exc_info=True)
            # No salimos, pausamos y volvemos a intentar el ciclo completo (re-iniciando navegador)
            await asyncio.sleep(30)
        finally:
            if context:
                try:
                    await context.close()
                except Exception:
                    pass

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
    asyncio.run(run_responder())
