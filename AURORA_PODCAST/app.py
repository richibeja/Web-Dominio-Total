import streamlit as st
import os
import sys
from pathlib import Path
from datetime import datetime

# Page config
st.set_page_config(
    page_title="CHERRY STUDIO - El Sonido del Deseo",
    page_icon="🎙️",
    layout="wide"
)

# Seductive Crimson CSS
st.markdown("""
<style>
    .main { background-color: #0a0000; color: #f0f0f0; }
    .stApp { background: radial-gradient(circle at center, #2d0000, #0a0000); }
    h1, h2, h3 { color: #ff3333; font-family: 'Georgia', serif; text-shadow: 0 0 10px rgba(255,0,0,0.4); }
    .stButton>button {
        background: linear-gradient(135deg, #ff0000 0%, #880000 100%);
        color: white; font-weight: 900; border-radius: 50px;
        box-shadow: 0 4px 20px rgba(255, 0, 0, 0.4); border: none;
        height: 4em;
    }
    .stTextArea>div>div>textarea { background-color: #1a0000; color: #ffcccc; border: 1px solid #440000; font-size: 1.1em; }
    .sidebar .sidebar-content { background-color: #111; }
</style>
""", unsafe_allow_html=True)

# Add project root to path for imports
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / ".env")
import requests
from shared.telegram_sender import queue_audio_for_telegram

def ask_uncensored_ai(prompt, system_message):
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key: return "⚠️ Falta API KEY"
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    model_name = os.getenv("AI_MODEL_NAME", "google/gemini-2.0-flash-lite-preview-02-05:free")
    payload = {
        "model": model_name,
        "messages": [{"role": "system", "content": system_message}, {"role": "user", "content": prompt}],
        "temperature": 1.0, "max_tokens": 1500
    }
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=25)
        return response.json()['choices'][0]['message']['content'] if response.status_code == 200 else f"Error: {response.text}"
    except Exception as e: return f"Error: {str(e)}"

from ai_models.voice_handler import VoiceHandler
vh = VoiceHandler()

# --- AUDIO SYSTEM INITIALIZATION ---
if 'audio_log' not in st.session_state:
    st.session_state.audio_log = [f"[{datetime.now().strftime('%H:%M:%S')}] Sone Engines Online. Ready for recording."]

def add_audio_log(msg):
    st.session_state.audio_log.append(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")

# Deep Red Cyber CSS
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700&display=swap');
    
    .main { background-color: #050000; color: #ff3333; font-family: 'Orbitron', sans-serif; }
    .stApp { background: radial-gradient(circle at center, #2d0000, #050000); }
    
    h1, h2, h3 { color: #ff0000 !important; text-transform: uppercase; letter-spacing: 2px; }
    
    .audio-console {
        background: #110000;
        border: 1px solid #ff0000;
        padding: 8px;
        color: #ff4444;
        font-family: monospace;
        font-size: 10px;
        height: 100px;
        overflow-y: auto;
        border-radius: 4px;
    }
    
    .stButton>button {
        background: #ff0000 !important;
        color: white !important;
        border-radius: 0px !important;
        border: 1px solid white !important;
    }
</style>
""", unsafe_allow_html=True)

# --- 🌍 GLOBAL PARAMETERS & UI INITIALIZATION ---
voice_map = {
    "💎 Cherry (Élite / Colombiana 🇨🇴)": "es-CO-SalomeNeural",
    "🎙️ Sofía (Española / Directa 🇪🇸)": "es-ES-ElviraNeural",
    "🎙️ Alexa (USA / English 🇺🇸)": "en-US-AvaNeural"
}

# --- SIDEBAR (Expert Console & Parameters) ---
with st.sidebar:
    st.title("🎙️ SONIC CONSOLE")
    audio_log_container = st.empty()
    a_logs = "\n".join(st.session_state.audio_log[::-1])
    audio_log_container.markdown(f"<div class='audio-console'>{a_logs}</div>", unsafe_allow_html=True)
    
    st.markdown("---")
    st.header("🎚️ PARAMETERS")
    selected_voice = st.selectbox("🌍 CAMBIAR IDIOMA / VOZ", list(voice_map.keys()), index=0)
    fx = st.multiselect("Inyectar Efectos", ["🚿 Ducha / Agua", "🎵 Música ASMR Suave", "🛏️ Sábanas / Roce", "🤫 Susurros Profundos"])
    proximity = st.select_slider("👂 PROXIMIDAD ASMR", options=["Ambient", "Natural", "Intimate", "Ear-to-Ear"], value="Intimate")
    
    st.markdown("---")
    st.header("🧪 SCRIPT LAB [MULTI-MODEL]")
    
    col_a, col_b = st.columns(2)
    with col_a:
        model_name = st.text_input("Nombre de la Modelo", "Valentina")
        duration_type = st.selectbox("Tipo de Contenido", ["Teaser (Breve/Gancho)", "Full Podcast (Detallado)", "Nota de Voz (Casual)"])
    with col_b:
        intensity = st.select_slider("Intensidad", options=["Sensual", "Atrevida", "Explícita", "Dominante"], value="Explícita")
    
    script_idea_input = st.text_area("¿De qué trata la historia? (Pon una idea simple aquí)", "Estoy en la cama hablando y tocándome pensando en ti...")

    col_1, col_2 = st.columns(2)
    with col_1:
        if st.button("🎲 INSPIRACIÓN ALEATORIA"):
            with st.spinner("Buscando en el baúl de las fantasías..."):
                sys_gen = "Eres un generador de escenarios eróticos de alto impacto. Crea una situación picante, detallada y PROHIBIDA para un audio de 10 minutos. El oyente debe ser el ÚNICO protagonista. No menciones a otros hombres, enfócate en lo que le harías a ÉL."
                random_idea = ask_uncensored_ai("Genera un prompt detallado para un audio erótico de una modelo para su fan. Que sea una situación nueva y excitante.", sys_gen)
                st.session_state.enhanced_idea = random_idea
                st.rerun()
    
    with col_2:
        if st.button("🪄 MEJORAR IDEA"):
            with st.spinner("Potenciando tu idea..."):
                sys_enhancer = "Eres un guionista experto en cine erótico POI (Point of View). Convierte la idea en un prompt detallado donde el oyente sea el centro de la fantasía. Prohibido mencionar a otros hombres."
                enhanced_prompt = ask_uncensored_ai(f"Convierte esta idea en un prompt potente: {script_idea_input}", sys_enhancer)
                st.session_state.enhanced_idea = enhanced_prompt
                st.rerun()

    final_idea = st.session_state.get('enhanced_idea', script_idea_input)
    if 'enhanced_idea' in st.session_state:
        st.success("✨ IDEA LISTA: Puedes usarla o editarla abajo.")
    
    script_idea = st.text_area("Cuerpo de la Fantasía (Lo que usará la IA)", value=final_idea, height=200)

    if st.button("🧬 GENERATE MASTER SCRIPT"):
        add_audio_log(f"Generating {duration_type} for {model_name}...")
        with st.spinner("Inyectando realismo colombiano..."):
            # Lógica de Identidad Dinámica y Acento Colombiano Estándar
            dialect_rules = "ESPAÑOL DE COLOMBIA. Acento natural, dulce y profesional. Usa 'tú' (NO uses 'vos'). Evita regionalismos exagerados."
            
            prompt_duration = "Escribe unas 150-200 palabras." if "Teaser" in duration_type else "Escribe un RELATO MUY LARGO de al menos 600 palabras. Detalla cada sensación, cada gemido, cada movimiento físico sin censura alguna."
            if "Nota de Voz" in duration_type: prompt_duration = "Escribe unas 80 palabras muy naturales, con pausas de respiración (usa ...)."

            sys_prompt = f"""Eres {model_name}, una modelo colombiana real. Estás muy excitada grabando esto para ÉL (el oyente).
            
            REGLAS DE ORO (MANDATORIAS):
            1. SOLO MONÓLOGO: Solo tus palabras. Prohibido "Yo:", "Tú:".
            2. ACENTO: {dialect_rules}.
            3. SIN FILTROS: Sé explícita, visual, sucia y muy descriptiva.
            4. FOCO EN EL CLIENTE: Él es el único hombre en tu mundo. Usa frases como "te imagino aquí", "te estoy pensando", "esto es solo para ti".
            5. PROHIBIDO OTROS HOMBRES: No menciones ex, otros chicos, ni encuentros con nadie más. Él es el centro de la fantasía.
            6. ESTRUCTURA: Empieza DIRECTA, al grano, ya excitada.
            7. LONGITUD: {prompt_duration}
            """
            
            generated_text = ask_uncensored_ai(f"Habla como {model_name} sobre: {script_idea}", sys_prompt)
            st.session_state.script_draft = generated_text
            add_audio_log(f"Script ready for {model_name}.")
            st.rerun()

st.title("🎙️ CHERRY PODCAST: MEGA PROHIBIDO [ELITE EDITION]")
st.markdown("---")

col1, col2 = st.columns([2, 1])

with col1:
    st.subheader("🎭 MASTER RECORDING UNIT")
    
    os.environ["VOICE_EDGE_CODE"] = voice_map[selected_voice]
    
    txt = st.text_area("Buffer de Guion (Pegue aquí su texto con acotaciones)", value=st.session_state.get('script_draft', ''), height=350)
    
    # CLEAN PREVIEW
    if txt.strip():
        with st.expander("🔎 VER TEXTO QUE SE GRABARÁ (LIMPIO)"):
            clean_preview = vh._clean_text_for_tts(txt)
            st.write(clean_preview)

    if st.button("🔴 START PRODUCTION [ENCODE MASTER]"):
        if not txt.strip(): st.error("Buffer empty.")
        else:
            add_audio_log(f"Producing for: {selected_voice}")
            with st.spinner(f"Encoding {selected_voice} master track..."):
                path = vh.generate_voice(txt, user_id="mega_prod_clean", fx_list=fx)
                if path and os.path.exists(path):
                    st.success(f"💎 MASTER READY: {selected_voice}")
                    st.audio(path)
                    add_audio_log("Success.")
                    with open(path, "rb") as f:
                        st.download_button("📥 DESCARGAR MASTER (.MP3)", f, file_name=f"aurora_{datetime.now().strftime('%H%M%S')}.mp3")
                    
                st.session_state.last_produced_path = path

    if st.session_state.get('last_produced_path'):
        c1, c2 = st.columns(2)
        with c1:
            if st.button("📤 ENVIAR AL BOT (DM)"):
                if queue_audio_for_telegram(st.session_state.last_produced_path, caption=f"🔥 Audio de {model_name} listo para ti."):
                    st.success("✅ ¡ENVIADO AL CLIENTE!")
        with c2:
            if st.button("📢 PUBLICAR EN CANAL"):
                if queue_audio_for_telegram(st.session_state.last_produced_path, caption=f"🔥 Nuevo especial de {model_name}. 🎙️", to_channel=True):
                    st.success("✅ ¡PUBLICADO EN EL CANAL!")

with col2:
    st.subheader("🔊 AMBIENT FX")
    fx = st.multiselect("Inyectar Efectos", ["🚿 Ducha / Agua", "🎵 Música ASMR Suave", "🛏️ Sábanas / Roce", "🤫 Susurros Profundos"])
    
    st.markdown("---")
    st.markdown("**MASTER STATUS:** `READY_TO_BURN` 💎")
    
    if st.button("🧹 CLEAR BUFFER"):
        st.session_state.script_draft = ""
        st.rerun()

st.markdown("---")
st.caption("SONIC ELITE v3.2 - [MEGA SECURE]")
