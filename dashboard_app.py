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
        
        /* BOTONES DE VENTAS */
        div[data-testid="stButton"] button {
            width: 100%;
            border-radius: 12px;
            font-weight: bold;
            transition: all 0.3s;
        }
        /* Ebook - Verde Dinero */
        div.row-widget.stButton:nth-of-type(1) button { border: 2px solid #2ecc71; color: #2ecc71; }
        div.row-widget.stButton:nth-of-type(1) button:hover { background-color: #2ecc71; color: white; }
        
        /* Fanvue - Naranja Fuego */
        div.row-widget.stButton:nth-of-type(2) button { border: 2px solid #e67e22; color: #e67e22; }
        div.row-widget.stButton:nth-of-type(2) button:hover { background-color: #e67e22; color: white; }

        /* Telegram - Azul */
        div.row-widget.stButton:nth-of-type(3) button { border: 2px solid #3498db; color: #3498db; }
        div.row-widget.stButton:nth-of-type(3) button:hover { background-color: #3498db; color: white; }

        /* Objeción - Rojo Alerta */
        div.row-widget.stButton:nth-of-type(4) button { border: 2px solid #e74c3c; color: #e74c3c; }
        div.row-widget.stButton:nth-of-type(4) button:hover { background-color: #e74c3c; color: white; }
        
        /* Generador Principal - ROSA AURORA */
        div.stButton > button:first-child {
            background: linear-gradient(45deg, #ff00cc, #333399);
            color: white;
            border: none;
            box-shadow: 0 4px 15px rgba(255, 0, 204, 0.3);
        }
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
    from config.utopia_finca_links import LINKS
    
    st.subheader("✈️ COPILOTO DE VENTAS (Para Socia)")
    st.markdown("---")

    if "manual_handler" not in st.session_state:
        st.session_state.manual_handler = AIHandler()
        
    # Botón de Limpieza Rápida
    if st.button("🧹 Limpiar Texto"):
        # Borrar variable de estado
        st.session_state.client_input = ""
        st.session_state.generated_response = ""
        # Borrar key del widget
        if "input_box" in st.session_state:
            st.session_state["input_box"] = ""
        st.rerun()

    if "client_input" not in st.session_state: st.session_state.client_input = ""
    if "generated_response" not in st.session_state: st.session_state.generated_response = ""

    # SECCIÓN 1: ¿QUÉ DIJO EL CLIENTE?
    col_plat, col_lang, col_input = st.columns([1, 1, 2])
    with col_plat:
        platform = st.radio("Plataforma:", ["WhatsApp 💚", "Instagram 💜", "Telegram 💙", "Fanvue 🧡"], index=1)
    
    with col_lang:
        manual_lang = st.radio("Idioma Cliente:", ["Español (Paisa) 🇨🇴", "Inglés (Latina) 🇺🇸", "Francés (Latina) 🇫🇷"])
        
    with col_input:
        client_text = st.text_area("1. Pega aquí lo que dijo el cliente:", 
                                  value=st.session_state.client_input,
                                  placeholder="Ej: Hola, quiero info... o No tengo dinero...", 
                                  height=100,
                                  key="input_box")
    
    with st.expander("🛒 Objetivo de Venta / Tips", expanded=True):
        st.info("💡 **Tips de Venta:**\n- Ebook: Entrada ($7)\n- Telegram: Comunidad\n- Fanvue: VIP Mensual")
        sales_objective = st.selectbox("Objetivo Ahora:", ["Vender Ebook ($7)", "Vender Fanvue", "Vender Telegram VIP", "Solo Seducción"])

    # SECCIÓN 2: NIVEL DE TOXICIDAD (MÁSCARA)
    toxicity = st.select_slider("🎭 Nivel de Toxicidad / Manipulación:", 
                                options=["🥰 Novia Perfecta", "😈 Manipuladora (Seducción Pro)", "☠️ Tóxica Extrema (Psicología Oscura)"],
                                value="😈 Manipuladora (Seducción Pro)")

    # SECCIÓN 3: BOTONES DE ESTRATEGIA (CEREBRO DE VENTAS)
    st.markdown("### 2. ¿Qué le respondemos?")
    
    col_b1, col_b2, col_b3, col_b4 = st.columns(4)
    
    response_type = None
    
    if col_b1.button("💰 Vender Ebook ($7)"):
        response_type = "SELL_EBOOK"
    
    if col_b2.button("🔞 Vender Fanvue"):
        response_type = "SELL_FANVUE"
        
    if col_b3.button("💎 Vender Telegram"):
        response_type = "SELL_TELEGRAM"

    if col_b4.button("💍 Vender Novia Virtual ($300)"):
        response_type = "SELL_GIRLFRIEND"
        
    if st.button("🛡️ Objeción: 'No Dinero'"):
        response_type = "OBJECTION_MONEY"

    if st.button("💬 Responder / Seguir Charla (Sin Venta)"):
        response_type = "GENERAL_SEDUCTION"

    # LÓGICA DE GENERACIÓN
    if response_type and client_text:
        with st.spinner(f"Cocinando respuesta tipo {response_type}..."):
            
            # CONSTRUCCIÓN DE LA PERSONALIDAD SEGÚN NIVEL
            personality_prompt = ""
            if "Novia Perfecta" in toxicity:
                personality_prompt = """
                MODO: NOVIA PERFECTA 🥰
                - Sé dulce, sumisa, cariñosa y complaciente.
                - Hazlo sentir el hombre más fuerte y amado.
                - Usa emojis de corazones, besos y caritas felices.
                """
            elif "Manipuladora" in toxicity:
                personality_prompt = """
                MODO: MANIPULADORA (ROBERT GREENE) 😈
                - Aplica la Ley 16 (Ausencia) y Arquetipo Sirena.
                - Sé un reto. No se lo des fácil.
                - Hazte la difícil pero deseable.
                - Insinúa que tienes otros pretendientes (Triangulación suave).
                """
            else: # Tóxica Extrema
                personality_prompt = """
                MODO: TÓXICA EXTREMA ☠️
                - Usa la CULPA y el DRAMA. ("No me valoras", "Siempre haces lo mismo").
                - Hazte la víctima. Llora (virtualmente).
                - Sé celosa, posesiva y un poco agresiva-pasiva.
                - Haz que él te pida perdón aunque no haya hecho nada.
                """

            # ---------------------------------------------------------
            
            # ---------------------------------------------------------
            # LÓGICA DEL EMBUDO (FUNNEL) SEGÚN PLATAFORMA
            # ---------------------------------------------------------
            
            # 1. INSTAGRAM (Objetivo: Mover a WhatsApp)
            if "Instagram" in platform:
                wa_link = LINKS.get('whatsapp')
                links_context = f"USA SOLO ESTE LINK: {wa_link} (O diles el número +57 322 719 8007)."
                
                # SELECCIÓN ALEATORIA DE EXCUSAS (Para no sonar robot)
                import random
                excusas = [
                    "EXCUSA: 'Ay bebé, Instagram está súper cansón hoy y me borra mensajes. Escríbeme al WhatsApp mejor'.",
                    "EXCUSA: 'Mor, por acá no puedo mandarte lo que quiero... me da miedo que me bloqueen 🥺. Hablemos por WhatsApp'.",
                    "EXCUSA: 'Shhh... 🤫 Papi, aquí nos vigilan. Vámonos a lo privado en WhatsApp'.",
                    "EXCUSA: 'Cielo, si quieres ver más de mí, aquí no se puede. Te espero en mi WhatsApp personal'.",
                    "EXCUSA: 'Ay no, qué pereza este chat de Instagram, se traba mucho. Escríbeme al WhatsApp +57...'."
                ]
                excusa_elegida = random.choice(excusas)

                if response_type == "GENERAL_SEDUCTION":
                    # DETECCION DE DESPEDIDA / POSPONER
                    despedida_keywords = ["mañana", "trabajar", "dormir", "luego", "noche", "descansa", "ocupado", "voy a"]
                    es_despedida = any(k in client_text.lower() for k in despedida_keywords)
                    
                    if es_despedida:
                        instruction = "EL CLIENTE SE VA O POSPONE. NO VENDAS. Sé la novia perfecta: Deséale suerte, dile que lo extrañarás o que sueñe contigo. Cierra la charla con amor para que vuelva. (0 LINKS)."
                    else:
                        instruction = f"CHARLA CORTA. Coquetea rápido ('jajaja', 'mor'). {excusa_elegida} Pide que te escriban."
                else:
                    # Si intenta vender algo en IG, la IA lo corrige:
                    instruction = f"NO VENDAS AQUÍ (PELIGRO BLOQUEO). Dile: '{excusa_elegida}'. Manda el link de WhatsApp."

            # 2. WHATSAPP (Objetivo: Mover a Telegram)
            elif "WhatsApp" in platform:
                tg_link = LINKS.get('telegram')
                links_context = f"USA PREFERENTEMENTE ESTE LINK (Comunidad): {tg_link}"
                
                if response_type == "SELL_TELEGRAM":
                    instruction = "Invítalo a la Comunidad de Telegram. Dile que ahí subes lo que no puedes mostrar en fotos."
                elif response_type == "SELL_GIRLFRIEND":
                    instruction = "Vende el SERVICIO DE NOVIA VIRTUAL ($300 USD/mes). Dile: 'Mor, imagina despertar con mi voz todos los días, fotos exclusivas solo para ti y chat priority. Sé tu dueña. Solo me quedan 2 cupos'. (Usa Fanvue para cobrar)."
                elif response_type == "SELL_EBOOK" or response_type == "SELL_FANVUE":
                    # En WA sí se puede vender si el cliente ya está listo, pero mejor Telegram
                    links_context += f"\nTAMBIÉN PUEDES USAR: Ebook={LINKS.get('ebook_payment')} | Fanvue={LINKS.get('fanvue')}"
                    instruction = "El cliente quiere comprar YA. Pásale el link directo, pero invítalo también a Telegram después."
                else:
                    instruction = "Charla íntima de novia. Manda audios (texto sugerido). Si la charla muere, invítalo a Telegram."

            # 3. TELEGRAM / FANVUE (Objetivo: VENDER A SACO)
            else:
                links_context = f"""
                LINKS DE COMUNIDAD Y VENTA:
                - Ebook ($7): {LINKS.get('ebook_payment')}
                - Fanvue (Pack): {LINKS.get('fanvue')}
                """
                if response_type == "GENERAL_SEDUCTION":
                    instruction = "Mantén la temperatura alta. Eres la dueña del lugar. Seduce."
                else:
                    instruction = "CIERRA LA VENTA. Sin miedo. Pide el dinero o el clic. Dile que se está perdiendo lo mejor."

            # ---------------------------------------------------------

            # DETECCIÓN DE IDIOMA MANUAL (Por Botones)
            persona_instruction = ""
            if "Inglés" in manual_lang:
                persona_instruction = "🛑 IDIOMA: INGLÉS 🇺🇸. Responde en INGLÉS ESTILO LATINA ('Baby', 'Papi', 'My love'). NO HABLES ESPAÑOL."
            elif "Francés" in manual_lang:
                persona_instruction = "🛑 IDIOMA: FRANCÉS 🇫🇷. Responde en FRANCÉS ESTILO LATINA ('Chéri', 'Mon amour'). NO HABLES ESPAÑOL."
            else:
                persona_instruction = "IDIOMA: Español Colombiano (Paisa). Usa: 'Mor', 'Bebé', 'Cielo', 'Mi Rey'."

            full_prompt = f"""
            ACTÚA COMO: Luz de Aurora (Tu Novia Paisa Caliente).
            PLATAFORMA: {platform}
            
            {personality_prompt}
            
            {persona_instruction}
            
            OBJETIVO ACTUAL: {instruction}
            
            HISTORIAL / MENSAJE DEL CLIENTE: 
            "{client_text}"
            CONTEXTO LINKS:
            {links_context}
            
            Genera 1 respuesta (TEXTO PURO) corta y natural.
            """
            
            try:
                # LLAMADA A LA IA (MODO TURBO: SIN VOZ)
                async def generate():
                    # Usamos process_direct_text_only para evitar cargar TTS
                    return await st.session_state.manual_handler.process_direct_text_only(
                        full_prompt
                    )
                
                result_text = asyncio.run(generate())
                
                # FILTRO DE SEGURIDAD FINAL: Si es Instagram, BORRAR cualquier link que no sea WhatsApp
                if "Instagram" in platform:
                    bad_link = "web-dominio-total.vercel.app"
                    if bad_link in result_text:
                        result_text = result_text.replace("Mi contenido exclusivo está solo aquí bebé: https://" + bad_link + " 💕", "")
                        result_text = result_text.replace("https://" + bad_link, "")
                
                st.session_state.generated_response = result_text
            except Exception as e:
                st.error(f"Error AI: {e}")

    # SECCIÓN 3: RESULTADO
    if st.session_state.generated_response:
        st.markdown("### ✅ Copia esto y pégalo:")
        st.code(st.session_state.generated_response, language="text")
        
        # Botones extra para links rápidos
        st.caption("Links Rápidos (por si la IA no los puso):")
        c1, c2, c3 = st.columns(3)
        c1.code(LINKS.get('ebook_payment'), language="text")
        c2.code(LINKS.get('fanvue'), language="text")
        c3.code(LINKS.get('telegram'), language="text")

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
