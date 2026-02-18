#!/usr/bin/env python3
"""
Dashboard Streamlit (puerto 8501) para la agencia de modelos.
Muestra el log de Nuevos Clientes registrado por el bot de Telegram.
"""

import json
from pathlib import Path

import streamlit as st

DATA_DIR = Path(__file__).resolve().parent / "data"
CLIENTES_LOG = DATA_DIR / "nuevos_clientes.json"

st.set_page_config(
    page_title="Aurora Agency — Dashboard",
    page_icon="💎",
    layout="wide",
)

st.title("💎 Aurora Agency — Dashboard")
st.markdown("**Nuevos clientes** registrados desde el bot de Telegram.")

if not CLIENTES_LOG.exists():
    st.info("Aún no hay registros. Los nuevos clientes aparecerán aquí cuando usen /start en el bot.")
    st.stop()

try:
    data = json.loads(CLIENTES_LOG.read_text(encoding="utf-8"))
except Exception as e:
    st.error(f"Error leyendo el log: {e}")
    st.stop()

if not data:
    st.info("Aún no hay clientes registrados. Cuando alguien pulse /start en Telegram, aparecerá aquí.")
    st.stop()

# Mostrar métrica rápida
st.metric("Total nuevos clientes (registrados)", len(data))

# Tabla: fecha, user_id, username, nombre
rows = []
for e in data:
    fecha = e.get("date", "")[:19].replace("T", " ") if e.get("date") else "—"
    user_id = e.get("user_id", "—")
    username = ("@" + e.get("username")) if e.get("username") else "—"
    nombre = (e.get("first_name", "") + " " + (e.get("last_name") or "")).strip() or "—"
    rows.append({"Fecha": fecha, "ID": user_id, "Usuario": username, "Nombre": nombre})

st.dataframe(rows, use_container_width=True, hide_index=True)

st.caption("Log guardado en `data/nuevos_clientes.json`. Actualiza la página para ver nuevos registros.")
