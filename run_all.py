"""
INICIAR TODO (SIMPLIFICADO) - Unifica los servicios sin abrir muchas ventanas.

Foco: Instagram -> WhatsApp.
Ventanas visibles: Solo el Monitor de Instagram.
Servicios en segundo plano: Dashboard, FanWeb, MCP Server.
"""
import subprocess
import sys
import os
import time
import signal
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
processes = []

def run_background(name: str, cmd: list, cwd: Path = None):
    """Lanza un proceso en segundo plano (sin ventana)."""
    cwd = cwd or PROJECT_ROOT
    creation_flags = 0
    if sys.platform == "win32":
        from subprocess import CREATE_NO_WINDOW
        creation_flags = CREATE_NO_WINDOW
    
    p = subprocess.Popen(
        cmd,
        cwd=str(cwd),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=creation_flags
    )
    processes.append((name, p))
    print(f"  [BG] {name} iniciado en segundo plano.")
    time.sleep(1)

def run_visible(name: str, cmd: list, cwd: Path = None):
    """Lanza un proceso en una ventana visible (Principal)."""
    cwd = cwd or PROJECT_ROOT
    if sys.platform == "win32":
        # Usamos start para que sea una ventana independiente pero controlada
        full_cmd = " ".join(f'"{c}"' if " " in str(c) else str(c) for c in cmd)
        subprocess.Popen(f'start "{name}" cmd /c {full_cmd}', shell=True, cwd=str(cwd))
    else:
        subprocess.Popen(cmd, cwd=str(cwd))
    print(f"  [VISIBLE] {name} iniciado.")
    time.sleep(1)

def cleanup(sig=None, frame=None):
    print("\n\n🛑 Deteniendo todos los servicios en segundo plano...")
    for name, p in processes:
        try:
            p.terminate()
            print(f"  - {name} detenido.")
        except:
            pass
    
    # Matar procesos huérfanos comunes en Windows
    if sys.platform == "win32":
        os.system("taskkill /F /IM chrome.exe /T >nul 2>&1")
        os.system("taskkill /F /IM python.exe /T >nul 2>&1")
    
    print("✅ Todo cerrado. ¡Hasta pronto!")
    sys.exit(0)

# Registrar señales de salida
signal.signal(signal.SIGINT, cleanup)
signal.signal(signal.SIGTERM, cleanup)

def main():
    print("=" * 60)
    print("  AURORA LUZ - SISTEMA DE VENTAS SIMPLIFICADO")
    print("  Instagram -> WhatsApp (Cierre Manual)")
    print("=" * 60)

    py = sys.executable

    # 1. Fanvue MCP Server (Plomería interna)
    mcp_server = PROJECT_ROOT / "fanvue_api" / "run_fanvue_mcp.py"
    if mcp_server.exists():
        run_background("Fanvue MCP", [py, str(mcp_server)])

    # 2. Dashboard (Métricas y Control) - http://localhost:8501
    dashboard = PROJECT_ROOT / "dashboard_app.py"
    if dashboard.exists():
        run_background("Dashboard", [py, "-m", "streamlit", "run", "dashboard_app.py", "--server.port", "8501", "--server.headless", "true"])
        
        # 2b. Ngrok Public Tunnel for Dashboard
        print("  [NGROK] Iniciando túnel público para el Dashboard...")
        run_background("Ngrok Dashboard", ["ngrok", "http", "8501", "--log", "stdout"])

    # 3. FanWeb (Web Modelos) - http://localhost:5000
    fanweb = PROJECT_ROOT / "fanweb" / "app.py"
    if fanweb.exists():
        run_background("FanWeb", [py, str(fanweb)])

    # 4. INSTAGRAM MONITOR (ELIMINADO - GESTIÓN MANUAL)
    # insta_script = PROJECT_ROOT / "instagram_bot" / "automation" / "run_instagram_monitor.py"
    print("\n[INFO] Instagram Bot desactivado (Gestión Manual por Socia).")
    
    # Intentar obtener la URL de ngrok (tarda unos segundos en activarse)
    time.sleep(3)
    public_url = "Iniciando..."
    try:
        import requests
        resp = requests.get("http://localhost:4040/api/tunnels", timeout=2)
        if resp.ok:
            tunnels = resp.json().get("tunnels", [])
            for t in tunnels:
                if "8501" in t.get("config", {}).get("addr", ""):
                    public_url = t.get("public_url")
                    break
    except:
        public_url = "Pendiente (abre el dashboard local para ver)"

    print("\n" + "=" * 60)
    print("  ESTADO:")
    print("     - Instagram: MANUAL (Revisa el celular)")
    print("     - Dashboard Local:  http://localhost:8501")
    print(f"     - DASHBOARD PÚBLICO: {public_url}")
    print("     - WhatsApp:  Número listo para conversión")
    print("=" * 60)
    print("\n  👉 Esta ventana controla los procesos de fondo.")
    print("  👉 CIERRA ESTA VENTANA o presiona Ctrl+C para detener TODO.")
    print("=" * 60 + "\n")

    try:
        while True:
            time.sleep(10)
    except KeyboardInterrupt:
        cleanup()

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\n[ERROR] Fallo crítico en el iniciador: {e}")
        cleanup()
