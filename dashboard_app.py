"""
Tablero de Control "Luz de Aurora" - Dashboard local

Solo Instagram + Fanvue (sin WhatsApp). Métricas: comentarios/DMs Instagram, pendientes Fanvue.

Puertos del proyecto:
  - 8501: Este dashboard (Streamlit)
  - 3000: Web de modelos / FanWeb (Flask)

Ejecutar: streamlit run dashboard_app.py --server.port 8501
"""
import os
import sys
import json
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

# Raíz del proyecto
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Rutas de datos
DATA_DIR = PROJECT_ROOT / "data"
COMMENTS_PROCESSED = DATA_DIR / "instagram_comments_processed.json"
DMS_PROCESSED = DATA_DIR / "instagram_dms_processed.json"
COMENTARIOS_FANVUE = DATA_DIR / "comentarios_para_fanvue.json"
INVITADOS_TELEGRAM_FILE = DATA_DIR / "instagram_invitados_telegram.json"
PENDING_REENGAGEMENT_FILE = DATA_DIR / "instagram_pending_reengagement.json"
LOG_FILE = PROJECT_ROOT / "instagram_monitor.log"


def load_json_safe(path: Path, default=None):
    if default is None:
        default = {} if "processed" in path.name or "comment" in path.name.lower() else []
    if not path.exists():
        return default
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def get_comments_count():
    data = load_json_safe(COMMENTS_PROCESSED, {})
    return len(data) if isinstance(data, dict) else len(data)


def get_dms_count():
    data = load_json_safe(DMS_PROCESSED, [])
    return len(data) if isinstance(data, list) else 0


def get_fanvue_pending():
    data = load_json_safe(COMENTARIOS_FANVUE, [])
    if not isinstance(data, list):
        return 0, []
    pending = [x for x in data if x.get("status") == "pending"]
    return len(pending), data[-10:][::-1]  # últimos 10


def get_whatsapp_leads_data():
    """Analiza conversations_map.json para contar leads de WhatsApp y mensajes."""
    from shared.persistence import get_conversation_map
    data = get_conversation_map()
    
    total_messages = 0
    leads_count = 0
    leads_list = []
    active_fans = []
    
    for user, entry in data.items():
        if not isinstance(entry, dict): continue
        
        count = entry.get("msg_count", 0)
        total_messages += count
        
        is_lead = entry.get("is_whatsapp_lead", False)
        if is_lead:
            leads_count += 1
            leads_list.append({
                "username": user,
                "messages": count,
                "lead_at": entry.get("whatsapp_lead_at", "")[:19].replace("T", " ")
            })
            
        if count > 0:
            active_fans.append({
                "username": user,
                "messages": count,
                "last_active": entry.get("updated", "")[:19].replace("T", " ")
            })
            
    # Ordenar por mensajes desc
    active_fans = sorted(active_fans, key=lambda x: x["messages"], reverse=True)
    leads_list = sorted(leads_list, key=lambda x: x["lead_at"], reverse=True)
    
    return leads_count, total_messages, leads_list, active_fans


def get_pending_reengagement():
    """Pendientes de responder (último mensaje del cliente, sin respuesta nuestra). Para re-engagement 1h–48h."""
    data = load_json_safe(PENDING_REENGAGEMENT_FILE, [])
    if not isinstance(data, list):
        return 0, []
    return len(data), data


def get_log_tail(lines=50):
    if not LOG_FILE.exists():
        return []
    try:
        with open(LOG_FILE, "r", encoding="utf-8", errors="ignore") as f:
            all_lines = f.readlines()
        return all_lines[-lines:] if len(all_lines) > lines else all_lines
    except Exception:
        return []


def run_streamlit():
    import streamlit as st

    st.set_page_config(
        page_title="Luz de Aurora - Control",
        page_icon="✨",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    st.markdown(
        """
        <style>
        .big-font { font-size:2rem !important; font-weight: bold; }
        .metric-card { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 1rem 1.5rem; border-radius: 10px; margin: 0.5rem 0; }
        .log-box { background: #1e1e1e; color: #d4d4d4; padding: 1rem; border-radius: 8px; font-family: monospace; font-size: 0.85rem; max-height: 400px; overflow-y: auto; }
        </style>
        """,
        unsafe_allow_html=True,
    )

    st.title("✨ Luz de Aurora — Tablero de Control")
    st.caption("Estado de los bots (Instagram + WhatsApp + Web).")

    tabs = st.tabs(["📊 Métricas y Leads", "💬 Asistente de Chat Manual", "📜 Logs del Sistema"])

    with tabs[0]:
        render_metrics_tab()
        
    with tabs[1]:
        render_manual_assistant_tab()
        
    with tabs[2]:
        render_logs_tab()

def render_manual_assistant_tab():
    import streamlit as st
    import asyncio
    from ai_models.ai_handler import AIHandler
    
    st.subheader("🤖 Asistente de Ventas Manual (WhatsApp)")
    st.markdown("""
    La **socia** (mujer) pega aquí lo que dijo el cliente en WhatsApp. 
    La IA genera solo **texto** persuasivo para que lo copies y envíes. Tú grabas tus propios audios si quieres; esta interfaz es solo para el **chat**.
    """)
    
    if "manual_handler" not in st.session_state:
        st.session_state.manual_handler = AIHandler()
        
    from shared.persistence import (
        get_conversation_map, save_client_note, save_client_link, 
        get_client_note, get_client_link,
        save_client_real_name, get_client_real_name,
        save_client_phone, get_client_phone
    )
    
    # Selector de cliente para memoria
    conv_map = get_conversation_map()
    usernames = sorted(list(conv_map.keys()))
    
    with st.expander("👤 Gestión de Contactos y Memoria", expanded=True):
        col_c, col_rn, col_w = st.columns([1, 1, 1])
        selected_user = col_c.selectbox("Seleccionar Cliente (IG):", ["(Nuevo)"] + usernames)
        
        current_rn = ""
        current_phone = ""
        current_note = ""
        current_link = ""
        
        if selected_user != "(Nuevo)":
            current_rn = get_client_real_name(selected_user)
            current_phone = get_client_phone(selected_user)
            current_note = get_client_note(selected_user)
            current_link = get_client_link(selected_user)
            
        real_name = col_rn.text_input("Nombre Real:", value=current_rn, placeholder="Ej: Juan Pérez")
        whatsapp_phone = col_w.text_input("Número WhatsApp:", value=current_phone, placeholder="Ej: +57...")
        
        col_n, col_l, col_s = st.columns([2, 2, 0.5])
        new_note = col_n.text_input("Notas Psicológicas/Detalles:", value=current_note, placeholder="Ej: Está solo, le gusta que lo traten dulce...")
        new_link = col_l.text_input("Link de Venta Personalizado:", value=current_link, placeholder="Ej: Fanvue Promo Link...")
        
        if col_s.button("💾 Guardar"):
            if selected_user != "(Nuevo)":
                save_client_real_name(selected_user, real_name)
                save_client_phone(selected_user, whatsapp_phone)
                save_client_note(selected_user, new_note)
                save_client_link(selected_user, new_link)
                st.success(f"Contacto de @{selected_user} actualizado.")
                st.rerun()
            else:
                st.warning("Selecciona un cliente de la lista.")

    # Ver historial
    if selected_user != "(Nuevo)":
        with st.expander("📜 Historial Reciente de la Conversación"):
            history = st.session_state.manual_handler._get_conversation_history(selected_user)
            for msg in history:
                role = "Tu Novia" if msg["role"] == "assistant" else "Cliente"
                st.markdown(f"**{role}:** {msg['content']}")

    # Input del cliente (para responder a lo que dijo) — Solo chat; la socia graba sus propios audios
    st.markdown("---")
    col_in, col_tac = st.columns([2, 1])
    cliente_msg = col_in.text_area("1. ¿Qué dijo el cliente? (Opcional):", placeholder="Pega aquí el mensaje de WhatsApp...", height=100)
    
    tactics = [
        "Normal (Paisa Dulce)",
        "Sirena (Seducción)",
        "Cansada/Dramática (Urgencia)",
        "Misteriosa (Ley 4 - Hablar poco)",
        "Celosa/Triangulación (Ley 11)",
        "Protector (Hacerlo sentir su salvador)"
    ]
    selected_tactic = col_tac.selectbox("Táctica / Mood:", tactics)

    # Borrador propio (para humanizar)
    borrador_msg = st.text_area("2. ¿Qué quieres decirle tú? (Borrador):", placeholder="Ej: dile que estoy ocupada pero que lo quiero ver luego...", height=80)
    
    col_btn_gen, col_btn_hum, col_img = st.columns([1, 1, 1])
    
    # Respuesta Magica (basada en el cliente)
    if col_btn_gen.button("✨ Generar Respuesta") and (cliente_msg or borrador_msg):
        with st.spinner("Cocinando respuesta..."):
            try:
                # Inyectar táctica en el contexto
                context_plus = f"[TÁCTICA REQUERIDA: {selected_tactic}]"
                if borrador_msg:
                    context_plus += f"\n[IDEA DEL USUARIO: {borrador_msg}]"
                
                async def get_res():
                    return await st.session_state.manual_handler.get_response_with_voice(
                        cliente_msg if cliente_msg else "hola mor", 
                        user_id=selected_user if selected_user != "(Nuevo)" else "manual_sales", 
                        dialect="paisa",
                        context=context_plus,
                        voice_style=None,
                        text_only=True
                    )
                
                result = asyncio.run(get_res())
                st.session_state.last_manual_res = result
            except Exception as e:
                st.error(f"Error: {e}")

    # Humanizar (solo el borrador)
    if col_btn_hum.button("🎭 Paisa-ify (Humanizar)") and borrador_msg:
        with st.spinner("Humanizando..."):
            try:
                prompt_hum = f"Reescribe este borrador para que suene como una chica Paisa real (Medellín), coqueta, en minúsculas y muy natural. Borrador: '{borrador_msg}'"
                async def hum_res():
                    return await st.session_state.manual_handler.get_response_with_voice(
                        prompt_hum, 
                        user_id="manual_humanize", 
                        dialect="paisa",
                        context="[INSTRUCCIÓN: SOLO REESCRIBE EL TEXTO, NO AÑADAS COMENTARIOS]",
                        text_only=True
                    )
                result = asyncio.run(hum_res())
                st.session_state.last_manual_res = result
            except Exception as e:
                st.error(f"Error: {e}")

    # Indicar qué versión del "Modo Dios"
    if cliente_msg or borrador_msg:
        mode_label = "🔥 Paisa (Medellín)" 
        st.info(f"📍 **Modo:** {mode_label} | **Táctica:** {selected_tactic}")

    # Generar Foto (Para prueba de vida / consistencia)
    if col_img.button("📸 Generar Foto Consistente"):
        with st.spinner("Generando foto de la modelo..."):
            photo_path = st.session_state.manual_handler.generate_consistent_image()
            if photo_path:
                st.session_state.last_photo = photo_path
            else:
                st.error("No se pudo generar la imagen (revisa HF_API_TOKEN).")

    # Mostrar Resultados de Respuesta (solo texto; la socia graba sus propios audios)
    if "last_manual_res" in st.session_state:
        res = st.session_state.last_manual_res
        st.success("✅ Respuesta generada (copia y envía por WhatsApp):")
        
        # Link de venta si existe
        venta_link = get_client_link(selected_user) if selected_user != "(Nuevo)" else ""
        if venta_link:
            st.info(f"🔗 **Link de Venta para este cliente:** {venta_link}")
            
        # Solo texto copiable (no se muestra audio; la socia usa su propia voz)
        st.text_area("Copia este texto:", value=res["text"], height=120)

    # Mostrar Foto si se generó
    if "last_photo" in st.session_state:
        photo_path = Path(st.session_state.last_photo)
        if photo_path.exists():
            st.markdown("### 📸 Foto Generada (Consistencia Visual)")
            photo_bytes = photo_path.read_bytes()
            st.image(photo_bytes, caption="Usa esta foto como 'prueba de vida' o contenido exclusivo.")
            st.download_button("⬇️ Descargar esta Foto", photo_bytes, file_name="vida_modelo.jpg")

    st.divider()

def render_logs_tab():
    import streamlit as st
    st.subheader("📜 Últimas líneas del monitor (Instagram)")
    log_lines = get_log_tail(100)
    if log_lines:
        log_text = "".join(log_lines).strip()
        st.code(log_text, language="text")
    else:
        st.info("No hay log aún o el archivo instagram_monitor.log no existe.")

def render_metrics_tab():
    import streamlit as st
    with st.sidebar:
        st.subheader("🔌 Puertos")
        st.markdown("- **8501** — Este dashboard (Streamlit)")
        st.markdown("- **5000** — Web de modelos / FanWeb (Flask)")
        st.markdown("Sin colisiones con Instagram bot (5002) ni OAuth (5004).")

    # Métricas principales
    comments_count = get_comments_count()
    dms_count = get_dms_count()
    leads_count, total_msgs, leads_list, active_fans = get_whatsapp_leads_data()
    pending_reengage_count, pending_reengage_list = get_pending_reengagement()

    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        st.metric("Comentarios (IG)", comments_count)
    with col2:
        st.metric("DMs hoy (IG)", dms_count)
    with col3:
        st.metric("Leads WhatsApp 💎", leads_count)
    with col4:
        st.metric("Total Mensajes", total_msgs)
    with col5:
        st.metric("Estrategia", "IG → WhatsApp")

    st.divider()

    # Pendientes de responder
    st.subheader("📬 Pendientes de responder (re-engagement)")
    if pending_reengage_list:
        for item in pending_reengage_list[:10]:
            user = item.get("username", "?")
            hours = item.get("hours_ago", 0)
            st.text(f"@{user} — hace {hours} h")
    else:
        st.info("No hay pendientes detectados.")
        
    st.divider()

    # Leads de WhatsApp (Diamantes)
    c1, c2 = st.columns(2)
    
    with c1:
        st.subheader("💎 Leads Recientes")
        if leads_list:
            import pandas as pd
            df_leads = pd.DataFrame(leads_list)
            # Resaltar HOT
            def highlight_hot(val):
                color = 'red' if 'HOT' in str(val) else 'black'
                return f'color: {color}'
            
            st.table(df_leads.head(10))
            
    with c2:
        st.subheader("🔥 Fans más Activos")
        if active_fans:
            import pandas as pd
            df_fans = pd.DataFrame(active_fans)
            st.table(df_fans.head(10))

    st.divider()
    st.caption("Dashboard 8501 | Luz de Aurora.")
    
    with st.expander("🤝 Compartir con Socio"):
        import requests
        public_url = None
        try:
            # Intentar obtener la URL de ngrok desde la API local
            resp = requests.get("http://localhost:4040/api/tunnels", timeout=1)
            if resp.ok:
                tunnels = resp.json().get("tunnels", [])
                for t in tunnels:
                    if "8501" in t.get("config", {}).get("addr", ""):
                        public_url = t.get("public_url")
                        break
        except:
            pass

        import socket
        hostname = socket.gethostname()
        local_ip = socket.gethostbyname(hostname)
        
        st.markdown("### 🌐 Acceso Remoto (Para tu Socio)")
        if public_url:
            st.success(f"**Link Público Activo:** {public_url}")
            st.code(public_url)
            st.caption("Pásale este link a tu socio para que entre desde cualquier lugar.")
        else:
            st.warning("No se detectó un link público de ngrok activo.")
            st.info(f"Si están en la misma casa, usa el link local: `http://{local_ip}:8501`")
        
        st.markdown("""
        **Instrucciones para el socio:**
        1. Entrar al link proporcionado.
        2. Usar la pestaña **'Asistente de Chat Manual'**.
        3. Consultar las notas en **'Memoria Compartida'** antes de responder.
        """)


if __name__ == "__main__":
    run_streamlit()
