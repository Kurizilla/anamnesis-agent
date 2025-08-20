import os
import requests
import streamlit as st

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")

st.set_page_config(page_title="Clini-Assistant (Local)", page_icon="🩺", layout="centered")
st.title("Clini-Assistant · Pruebas locales")

with st.sidebar:
  st.subheader("Configuración")
  backend_url = st.text_input("Backend URL", BACKEND_URL)
  st.caption("Apunta al servicio FastAPI (por defecto http://localhost:8000)")

# Estado de sesión
if "session_id" not in st.session_state:
  st.session_state.session_id = ""
if "history" not in st.session_state:
  st.session_state.history = []  # lista de (role, text)

st.text_input("User ID", key="user_id", value="u1")
patient_help = "Se usa en el primer turno para iniciar la sesión, precargar motivos y áreas afectadas."
st.text_input("Patient ID (primer turno)", key="patient_id", help=patient_help, disabled=bool(st.session_state.session_id))

# Botones de control de sesión
c1, c2 = st.columns(2)

def bootstrap_session():
  user_id = st.session_state.user_id.strip() or "u1"
  patient_id = st.session_state.patient_id.strip()
  if not patient_id:
    st.warning("Ingresa un Patient ID para iniciar la consulta.")
    return
  try:
    with st.spinner("Estás entrando a tu consulta…"):
      resp = requests.post(f"{backend_url}/bootstrap", json={"user_id": user_id, "patient_id": patient_id}, timeout=180)
      if resp.status_code != 200:
        st.error(f"Error {resp.status_code}: {resp.text}")
        return
      data = resp.json()
      st.session_state.session_id = data.get("session_id", "")
      first_reply = data.get("reply") or "(sin respuesta)"
      st.session_state.history.append(("agent", first_reply))
  except Exception as e:
    st.error(f"Error de red: {e}")

with c1:
  if st.button("Entrar a la consulta", type="primary", disabled=bool(st.session_state.session_id)):
    bootstrap_session()
with c2:
  if st.button("Reiniciar sesión"):
    st.session_state.session_id = ""
    st.session_state.history.append(("system", "[Sesión reiniciada]"))

st.markdown("---")

# Formulario de chat con limpieza automática del textarea
with st.form("chat_form", clear_on_submit=True):
  msg = st.text_area("Mensaje", key="message", height=120, placeholder="Escribe tu mensaje…",
                     disabled=not bool(st.session_state.session_id))
  col1, col2 = st.columns(2)
  submit = col1.form_submit_button("Enviar", type="primary", disabled=not bool(st.session_state.session_id))
  # Deja el botón de reinicio aquí también por conveniencia
  reset = col2.form_submit_button("Reiniciar sesión")


def send_message():
  if not st.session_state.session_id:
    st.warning("Primero inicia la consulta con 'Entrar a la consulta'.")
    return
  message = (st.session_state.get("message") or "").strip()
  if not message:
    return
  payload = {"user_id": st.session_state.user_id, "message": message, "session_id": st.session_state.session_id}
  try:
    st.session_state.history.append(("user", message))
    resp = requests.post(f"{backend_url}/chat", json=payload, timeout=120)
    if resp.status_code != 200:
      st.error(f"Error {resp.status_code}: {resp.text}")
      st.session_state.history.append(("agent", f"[Error {resp.status_code}] {resp.text}"))
      return
    data = resp.json()
    reply = data.get("reply") or "(sin respuesta)"
    st.session_state.history.append(("agent", reply))
  except Exception as e:
    st.error(f"Error de red: {e}")
    st.session_state.history.append(("agent", f"[Error de red] {e}"))

if submit:
  send_message()
if reset:
  st.session_state.session_id = ""
  st.session_state.history.append(("system", "[Sesión reiniciada]"))

st.markdown("""
<small>
Flujo: 1) Ingresa Patient ID y pulsa “Entrar a la consulta” (se hará prefetch y saludo inicial). 2) Continúa chateando.
</small>
""", unsafe_allow_html=True)

st.markdown("---")
st.subheader("Conversación")
if not st.session_state.history:
  st.info("Aún no hay mensajes. Inicia la consulta arriba.")
else:
  for role, text in st.session_state.history:
    if role == "user":
      st.markdown(f"**Tú:** {text}")
    elif role == "agent":
      st.markdown(f"**Agente:** {text}")
    else:
      st.markdown(f"`{role}` {text}")

# Mostrar session_id actual
if st.session_state.session_id:
  st.caption(f"Session ID actual: {st.session_state.session_id}") 