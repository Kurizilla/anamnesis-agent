import os
import requests
import streamlit as st

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")
PUBLIC_BACKEND_URL = os.getenv("PUBLIC_BACKEND_URL", "http://localhost:8000")

st.set_page_config(page_title="Clini-Assistant (Local)", page_icon="🩺", layout="centered")
st.title("Clini-Assistant · Pruebas locales")

with st.sidebar:
  st.subheader("Configuración")
  backend_url = st.text_input("Backend URL", BACKEND_URL)
  st.caption("Apunta al servicio FastAPI (por defecto http://localhost:8000)")
  public_backend_url = st.text_input("Backend URL (para navegador)", PUBLIC_BACKEND_URL)
  st.caption("Usado por el navegador para WebRTC (no puede usar hostnames internos del cluster como clini_api)")

# Tabs for Text (Anamnesis, Riesgo) and Voice
anam_tab, risk_tab, voice_tab = st.tabs(["Texto: Anamnesis", "Texto: Riesgo", "Voz (Live)"])

# ---------- Texto: Anamnesis ----------
with anam_tab:
  # Estado de sesión independiente
  if "anam_session_id" not in st.session_state:
    st.session_state.anam_session_id = ""
  if "anam_history" not in st.session_state:
    st.session_state.anam_history = []  # lista de (role, text)

  st.text_input("User ID", key="anam_user_id", value="u1")
  patient_help = "Se usa en el primer turno para iniciar la sesión, precargar motivos y áreas afectadas."
  st.text_input("Patient ID (primer turno)", key="anam_patient_id", help=patient_help, disabled=bool(st.session_state.anam_session_id))

  c1, c2 = st.columns(2)

  def bootstrap_anam():
    user_id = (st.session_state.get("anam_user_id") or "u1").strip()
    patient_id = (st.session_state.get("anam_patient_id") or "").strip()
    if not patient_id:
      st.warning("Ingresa un Patient ID para iniciar la consulta.")
      return
    try:
      with st.spinner("Estás entrando a tu consulta (Anamnesis)…"):
        resp = requests.post(f"{backend_url}/bootstrap", json={"user_id": user_id, "patient_id": patient_id, "agent_kind": "anamnesis"}, timeout=180)
      if resp.status_code != 200:
        st.error(f"Error {resp.status_code}: {resp.text}")
        return
      data = resp.json()
      st.session_state.anam_session_id = data.get("session_id", "")
      first_reply = data.get("reply") or "(sin respuesta)"
      st.session_state.anam_history.append(("agent", first_reply))
    except Exception as e:
      st.error(f"Error de red: {e}")

  with c1:
    if st.button("Entrar a la consulta (Anamnesis)", type="primary", disabled=bool(st.session_state.anam_session_id)):
      bootstrap_anam()
  with c2:
    if st.button("Reiniciar sesión (Anamnesis)"):
      st.session_state.anam_session_id = ""
      st.session_state.anam_history.append(("system", "[Sesión reiniciada]"))

  st.markdown("---")

  with st.form("chat_form_anam", clear_on_submit=True):
    msg = st.text_area("Mensaje", key="anam_message", height=120, placeholder="Escribe tu mensaje…",
                       disabled=not bool(st.session_state.anam_session_id))
    col1, col2 = st.columns(2)
    submit = col1.form_submit_button("Enviar", type="primary", disabled=not bool(st.session_state.anam_session_id))
    reset = col2.form_submit_button("Reiniciar sesión")

  def send_message_anam():
    if not st.session_state.anam_session_id:
      st.warning("Primero inicia la consulta con 'Entrar a la consulta'.")
      return
    message = (st.session_state.get("anam_message") or "").strip()
    if not message:
      return
    payload = {"user_id": st.session_state.anam_user_id, "message": message, "session_id": st.session_state.anam_session_id, "agent_kind": "anamnesis"}
    try:
      st.session_state.anam_history.append(("user", message))
      resp = requests.post(f"{backend_url}/chat", json=payload, timeout=120)
      if resp.status_code != 200:
        st.error(f"Error {resp.status_code}: {resp.text}")
        st.session_state.anam_history.append(("agent", f"[Error {resp.status_code}] {resp.text}"))
        return
      data = resp.json()
      reply = data.get("reply") or "(sin respuesta)"
      st.session_state.anam_history.append(("agent", reply))
    except Exception as e:
      st.error(f"Error de red: {e}")
      st.session_state.anam_history.append(("agent", f"[Error de red] {e}"))

  if submit:
    send_message_anam()
  if reset:
    st.session_state.anam_session_id = ""
    st.session_state.anam_history.append(("system", "[Sesión reiniciada]"))

  st.markdown("""
<small>
Flujo: 1) Ingresa Patient ID y pulsa “Entrar a la consulta” (se hará prefetch y saludo inicial). 2) Continúa chateando.
</small>
""", unsafe_allow_html=True)

  st.markdown("---")
  st.subheader("Conversación (Anamnesis)")
  if not st.session_state.anam_history:
    st.info("Aún no hay mensajes. Inicia la consulta arriba.")
  else:
    for role, text in st.session_state.anam_history:
      if role == "user":
        st.markdown(f"**Tú:** {text}")
      elif role == "agent":
        st.markdown(f"**Agente:** {text}")
      else:
        st.markdown(f"`{role}` {text}")

  if st.session_state.anam_session_id:
    st.caption(f"Session ID actual: {st.session_state.anam_session_id}")

# ---------- Texto: Riesgo ----------
with risk_tab:
  if "risk_session_id" not in st.session_state:
    st.session_state.risk_session_id = ""
  if "risk_history" not in st.session_state:
    st.session_state.risk_history = []

  st.text_input("User ID", key="risk_user_id", value="u1")
  st.text_input("Patient ID (primer turno)", key="risk_patient_id", disabled=bool(st.session_state.risk_session_id))

  c3, c4 = st.columns(2)

  def bootstrap_risk():
    user_id = (st.session_state.get("risk_user_id") or "u1").strip()
    patient_id = (st.session_state.get("risk_patient_id") or "").strip()
    if not patient_id:
      st.warning("Ingresa un Patient ID para iniciar la consulta.")
      return
    try:
      with st.spinner("Estás entrando a tu consulta (Riesgo)…"):
        resp = requests.post(f"{backend_url}/bootstrap", json={"user_id": user_id, "patient_id": patient_id, "agent_kind": "risk"}, timeout=180)
        if resp.status_code != 200:
          st.error(f"Error {resp.status_code}: {resp.text}")
          return
        data = resp.json()
        st.session_state.risk_session_id = data.get("session_id", "")
        first_reply = data.get("reply") or "(sin respuesta)"
        st.session_state.risk_history.append(("agent", first_reply))
    except Exception as e:
      st.error(f"Error de red: {e}")

  with c3:
    if st.button("Entrar a la consulta (Riesgo)", type="primary", disabled=bool(st.session_state.risk_session_id)):
      bootstrap_risk()
  with c4:
    if st.button("Reiniciar sesión (Riesgo)"):
      st.session_state.risk_session_id = ""
      st.session_state.risk_history.append(("system", "[Sesión reiniciada]"))

  st.markdown("---")

  with st.form("chat_form_risk", clear_on_submit=True):
    msg = st.text_area("Mensaje", key="risk_message", height=120, placeholder="Escribe tu mensaje…",
                       disabled=not bool(st.session_state.risk_session_id))
    col1, col2 = st.columns(2)
    submit = col1.form_submit_button("Enviar", type="primary", disabled=not bool(st.session_state.risk_session_id))
    reset = col2.form_submit_button("Reiniciar sesión")

  def send_message_risk():
    if not st.session_state.risk_session_id:
      st.warning("Primero inicia la consulta con 'Entrar a la consulta'.")
      return
    message = (st.session_state.get("risk_message") or "").strip()
    if not message:
      return
    payload = {"user_id": st.session_state.risk_user_id, "message": message, "session_id": st.session_state.risk_session_id, "agent_kind": "risk"}
    try:
      st.session_state.risk_history.append(("user", message))
      resp = requests.post(f"{backend_url}/chat", json=payload, timeout=120)
      if resp.status_code != 200:
        st.error(f"Error {resp.status_code}: {resp.text}")
        st.session_state.risk_history.append(("agent", f"[Error {resp.status_code}] {resp.text}"))
        return
      data = resp.json()
      reply = data.get("reply") or "(sin respuesta)"
      st.session_state.risk_history.append(("agent", reply))
    except Exception as e:
      st.error(f"Error de red: {e}")
      st.session_state.risk_history.append(("agent", f"[Error de red] {e}"))

  if submit:
    send_message_risk()
  if reset:
    st.session_state.risk_session_id = ""
    st.session_state.risk_history.append(("system", "[Sesión reiniciada]"))

  st.markdown("---")
  st.subheader("Conversación (Riesgo)")
  if not st.session_state.risk_history:
    st.info("Aún no hay mensajes. Inicia la consulta arriba.")
  else:
    for role, text in st.session_state.risk_history:
      if role == "user":
        st.markdown(f"**Tú:** {text}")
      elif role == "agent":
        st.markdown(f"**Agente:** {text}")
      else:
        st.markdown(f"`{role}` {text}")

# ---------- Voz (Live) ----------
with voice_tab:
  st.write("Preview de agente de voz. (La UI de streaming se está integrando por etapas.)") 