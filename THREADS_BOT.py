"""
🤖 BOT EXCLUSIVO PARA THREADS — Táctica "Mother/Child"
Automatización de publicaciones virales en cuentas esclavas.
"""
import time
import random
import sys
import os
import argparse
from pathlib import Path

# Forzar UTF-8 en Windows
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='ignore', line_buffering=True)
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='ignore', line_buffering=True)

# ── CONFIGURACIÓN DE TIEMPOS ─────────────────────────────────────
# Tiempo de espera entre publicaciones para no ser baneados
ESPERA_MIN_MINUTOS = 60    # Mínimo 1 hora entre posts
ESPERA_MAX_MINUTOS = 180   # Máximo 3 horas entre posts
# ─────────────────────────────────────────────────────────────────

def human_sleep(mi=2.0, ma=5.0):
    time.sleep(random.uniform(mi, ma))

def escribir_como_humano(element, text):
    for char in text:
        element.type(char, delay=random.randint(50, 200))

def cargar_frases():
    ruta = Path(__file__).resolve().parent / "data" / "frases_threads.txt"
    if not ruta.exists():
        print("❌ No se encontró el archivo de frases: data/frases_threads.txt")
        return []
    with open(ruta, "r", encoding="utf-8") as f:
        frases = [line.strip() for line in f.readlines() if line.strip()]
    return frases

def publicar_thread(page, frase):
    print(f"\n✍️ Intentando publicar la frase: '{frase}'...")
    
    # Recargar la página principal para tener el cuadro de texto disponible
    page.goto("https://www.threads.net/", wait_until="domcontentloaded")
    human_sleep(4, 8)
    
    # El cuadro de texto suele estar en el inicio
    try:
        # 1. Hacer clic en el botón de Crear del menú 
        btn_crear = page.locator('svg[aria-label="Crear"], svg[aria-label="Create"], svg[aria-label="New thread"], a[href="/m/create"]')
        if btn_crear.count() > 0:
            btn_crear.first.click(force=True)
            human_sleep(2, 4)
            
        # 2. Encontrar la caja de texto
        caja_texto = page.locator('div[contenteditable="true"]')
        if caja_texto.count() > 0:
            caja_texto.first.click(force=True)
            human_sleep(1, 3)
            # Escribir la frase
            escribir_como_humano(caja_texto.first, frase)
            human_sleep(2, 4)
            
            # 3. Buscar el botón de publicar
            print("   Forzando publicación con el teclado (Ctrl+Enter)...")
            
            # Plan A: Método de teclado. En Threads, oprimir Control + Enter envía el texto al instante.
            page.keyboard.press("Control+Enter")
            human_sleep(1, 2)
            page.keyboard.press("Control+Enter") # Segundo intento por si el primero falló por lag
            human_sleep(3, 4)

            # Plan B: Clic directo pero SIN force=True (para que no haga clic en cosas invisibles)
            btn_publicar = page.locator('div[role="button"]:has-text("Publicar"), div[role="button"]:has-text("Post")')
            try:
                if btn_publicar.count() > 0 and btn_publicar.last.is_visible():
                    btn_publicar.last.click(timeout=3000)
                    print("✅ ¡Botón presionado con el mouse!")
            except:
                pass

            print("✅ ¡Publicación completada (revisa tu perfil)!")
            human_sleep(4, 6)
            return True
        else:
            print("⚠️ No encontré la caja de texto para escribir. Míralo en la pantalla.")
            return False
    except Exception as e:
        print(f"❌ Error al intentar publicar: {e}")
        return False

def run_threads_bot(nombre_perfil):
    from playwright.sync_api import sync_playwright

    user_data_dir = str(Path(__file__).resolve().parent / "data" / "profiles_threads" / nombre_perfil)
    Path(user_data_dir).mkdir(parents=True, exist_ok=True)

    print(f"\n🚀 Iniciando Bot de Threads para el perfil: [{nombre_perfil}]")
    frases_disponibles = cargar_frases()
    
    if not frases_disponibles:
        return

    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            user_data_dir,
            headless=False, # SIEMPRE VISIBLE para que el jefe pueda vigilar
            viewport={"width": 1024, "height": 768},
            locale="es-CO",
        )
        page = context.new_page()

        print("[NAVEGADOR] Abriendo Threads...")
        page.goto("https://www.threads.net/", wait_until="domcontentloaded")
        human_sleep(5, 10)

        # Revisar si hay que iniciar sesión
        print("\n" + "="*60)
        print("⏳ ATENCIÓN: Si no has iniciado sesión, entra ahora con la cuenta de Instagram ESCLAVA o HIJA.")
        print("   Solo hazlo la primera vez, luego el navegador lo recordará.")
        print("   El bot esperará hasta que reconozca la página principal.")
        print("="*60 + "\n")

        # Bucle de automatización principal
        ciclo = 0
        while True:
            ciclo += 1
            # Escoger frase aleatoria que no suene a robot
            frase_elegida = random.choice(frases_disponibles)
            
            # Intentar publicar
            publicado = publicar_thread(page, frase_elegida)
            
            if not publicado:
                print("\n⏳ [ESPERANDO SESIÓN O CARGA] No se pudo publicar. Reintentando en 20 segundos...")
                print("   (Si no has iniciado sesión con 'fit_liamedellin', hazlo ahora en el navegador).")
                time.sleep(20)
                continue
            
            # Espera inteligente y aleatoria de horas
            minutos_espera = random.randint(ESPERA_MIN_MINUTOS, ESPERA_MAX_MINUTOS)
            
            print(f"\n[REPOSO] Ocultándonos del radar de Meta. Esperando {minutos_espera} minutos hasta la próxima publicación...")
            
            # Reposo (dormir en periodos cortos para evitar saturar RAM)
            for _ in range(minutos_espera * 6):
                time.sleep(10) # 10 segundos * 6 = 1 minuto
        
        context.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("perfil", nargs="?", default="perfil_esclavo_1", help="Nombre del perfil del navegador")
    args = parser.parse_args()

    while True:
        try:
            run_threads_bot(args.perfil)
        except KeyboardInterrupt:
            print("\n🛑 Detenido por el usuario.")
            break
        except Exception as e:
            print(f"\n💥 Caída Crítica: {e}")
            print("⏳ Reiniciando sistema en 30 segundos...")
            time.sleep(30)
