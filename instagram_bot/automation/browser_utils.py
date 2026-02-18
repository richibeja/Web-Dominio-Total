import os
import sys
import random
import asyncio
from pathlib import Path
from playwright.async_api import async_playwright, BrowserContext, Page

USER_DATA_DIR = Path("data/browser_session_v2")

# Reintentos si el contexto persistente falla
LAUNCH_MAX_RETRIES = 3
LAUNCH_RETRY_DELAY_SEC = 5

async def get_browser_context(headless: bool = False, profile_name: str = "browser_session") -> BrowserContext:
    """
    Inicia Playwright y retorna un contexto de navegador persistente.
    """
    user_data_path = Path(f"data/{profile_name}")
    user_data_path.mkdir(parents=True, exist_ok=True)
    
    args = [
        "--disable-blink-features=AutomationControlled",
        "--no-sandbox",
        "--disable-setuid-sandbox",
        "--disable-extensions",
        "--disable-infobars",
        "--disable-gpu",
        "--disable-dev-shm-usage",
        "--no-first-run",
        "--no-service-autorun",
        "--password-store=basic",
        "--use-mock-keychain",
        "--mute-audio",
    ]
    
    # Limpieza previa de procesos chrome ELIMINADA para no cerrar navegadores del usuario
    # if sys.platform == "win32":
    #    try:
    #        print(f"DEBUG: Limpiando procesos chrome previos para {profile_name}...")
    #        # os.system("taskkill /F /IM chrome.exe /T >nul 2>&1")
    #    except: 
    #        pass

    last_error = None
    for attempt in range(1, LAUNCH_MAX_RETRIES + 1):
        playwright = None
        print(f"DEBUG: Iniciando Playwright para {profile_name} (intento {attempt}/{LAUNCH_MAX_RETRIES})...")
        try:
            # Forzar limpieza de LOCK antes de cada intento
            lock_file = user_data_path / "SingletonLock"
            if lock_file.exists(): 
                try: lock_file.unlink()
                except: pass
            
            playwright = await async_playwright().start()
            print(f"DEBUG: Lanzando contexto persistente en {user_data_path} (headless={headless})...")
            
            # Timeout de lanzamiento aumentado a 60s
            # HEADLESS FALSE ALWAYS para depuración y evitar bloqueos
            context = await playwright.chromium.launch_persistent_context(
                user_data_dir=user_data_path,
                headless=False, # FORZAR VISIBLE
                viewport={"width": 1280, "height": 720},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--no-sandbox",
                    "--disable-setuid-sandbox",
                    "--disable-dev-shm-usage",
                    # "--disable-gpu", # Habilitar GPU para rendering
                    "--disable-infobars",
                    "--no-first-run",
                    "--no-service-autorun",
                    "--password-store=basic",
                    "--use-mock-keychain",
                ],
                timeout=90000 
            )
            print(f"DEBUG: OK Contexto {profile_name} lanzado.")
            return context
        except Exception as e:
            last_error = e
            print(f"DEBUG: Intento {attempt} fallido: {e}")
            
            # Limpieza PROFUNDA de LOCKs (recursiva)
            if any(x in str(e) for x in ["Target closed", "TargetClosedError", "closed", "browser has been closed"]):
                print(f"DEBUG: Realizando limpieza profunda de bloqueos en {user_data_path}...")
                try:
                    # Matar procesos de nuevo por si acaso
                    # NO MATAR PROCESOS GLOBALMENTE para no cerrar el navegador del usuario
                    # Solo limpiaremos archivos de bloqueo
                    pass
                    
                    # Borrar archivos de bloqueo conocidos de Chromium
                    for lock_name in ["SingletonLock", "lockfile", "LOCK"]:
                        for root, dirs, files in os.walk(user_data_path):
                            for file in files:
                                if lock_name.upper() in file.upper():
                                    try: os.remove(os.path.join(root, file))
                                    except: pass
                    print("DEBUG: Limpieza de LOCKs completada.")
                except Exception as le:
                    print(f"DEBUG: Error en limpieza profunda: {le}")

            if playwright:
                try:
                    await playwright.stop()
                except Exception:
                    pass
            if attempt < LAUNCH_MAX_RETRIES:
                print(f"DEBUG: Reintentando en {LAUNCH_RETRY_DELAY_SEC}s...")
                await asyncio.sleep(LAUNCH_RETRY_DELAY_SEC)
    
    print(f"DEBUG: Error lanzando contexto {profile_name} tras {LAUNCH_MAX_RETRIES} intentos.")
    raise last_error

async def random_sleep(min_seconds: float = 1, max_seconds: float = 3):
    """Sleeps for a random amount of time to simulate human behavior."""
    duration = random.uniform(min_seconds, max_seconds)
    await asyncio.sleep(duration)

async def human_type(page: Page, selector_or_locator, text: str):
    """Types text into a selector or locator with random delays between keystrokes."""
    if hasattr(selector_or_locator, "click"):
        # It's a locator
        await selector_or_locator.click()
    else:
        # It's a selector string
        await page.click(selector_or_locator)

    for char in text:
        await page.keyboard.type(char)
        await asyncio.sleep(random.uniform(0.05, 0.2))
