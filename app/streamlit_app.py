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

  if st.session_state.risk_session_id:
    st.caption(f"Session ID actual: {st.session_state.risk_session_id}")

# ---------- Voz tab (existente) ----------
with voice_tab:
  if "live_session_id" not in st.session_state:
    st.session_state.live_session_id = ""
  if "voice_history" not in st.session_state:
    st.session_state.voice_history = []

  st.text_input("User ID (Voz)", key="user_id_live", value="u1")
  st.text_input("Patient ID (primer turno)", key="patient_id_live", disabled=bool(st.session_state.live_session_id))

  c5, c6 = st.columns(2)

  def bootstrap_live():
    user_id = (st.session_state.get("user_id_live") or "u1").strip()
    patient_id = (st.session_state.get("patient_id_live") or "").strip()
    if not patient_id:
      st.warning("Ingresa un Patient ID para iniciar la consulta.")
      return
    try:
      with st.spinner("Entrando a consulta (voz)…"):
        # Solo crea sesión de texto para precarga, pero no envía turnos; la WS realizará kickoff
        resp = requests.post(f"{backend_url}/bootstrap_live", json={"user_id": user_id, "patient_id": patient_id}, timeout=180)
        if resp.status_code != 200:
          st.error(f"Error {resp.status_code}: {resp.text}")
          return
        data = resp.json()
        st.session_state.live_session_id = data.get("session_id", "")
        st.session_state.voice_history.append(("system", "[Live listo]"))
    except Exception as e:
      st.error(f"Error de red: {e}")

  with c5:
    if st.button("Entrar (Voz)", type="primary", disabled=bool(st.session_state.live_session_id)):
      bootstrap_live()
  with c6:
    if st.button("Reiniciar sesión (voz)"):
      st.session_state.live_session_id = ""
      st.session_state.voice_history.append(("system", "[Sesión reiniciada]") )

  st.markdown("---")
  st.subheader("Parámetros de audio")
  colA, colB = st.columns(2)
  with colA:
    mic_rate = st.selectbox("Frecuencia del micrófono (Hz)", options=[8000, 16000, 22050, 24000, 44100, 48000], index=1)
    out_rate = st.selectbox("Frecuencia de reproducción (Hz)", options=[8000, 16000, 22050, 24000, 44100, 48000], index=3)
  with colB:
    playback_rate = st.slider("Velocidad de reproducción", min_value=0.6, max_value=1.4, value=1.0, step=0.05, help="Ajusta velocidad (y tono) del audio")
    volume_gain = st.slider("Volumen", min_value=0.0, max_value=2.0, value=1.0, step=0.05)
  prebuffer_ms = st.number_input("Pre-buffer (ms)", min_value=0, max_value=1000, value=150, step=10, help="Acumula audio antes de reproducir para reducir cortes")

  st.markdown("---")
  st.subheader("Conversación (Voz)")
  if not st.session_state.voice_history:
    st.info("Inicia la consulta arriba (Voz)")
  else:
    for role, text in st.session_state.voice_history:
      if role == "user":
        st.markdown(f"**Tú (voz):** {text}")
      elif role == "agent":
        st.markdown(f"**Agente (voz):** {text}")
      else:
        st.markdown(f"`{role}` {text}")

  if st.session_state.live_session_id:
    st.caption(f"Session ID (Voz): {st.session_state.live_session_id}")

  st.markdown("---")
  st.subheader("Sesión Live (WebSocket) - Streaming audio↔audio")
  ws_client = """
  <div>
    <button id='ws_start'>Conectar</button>
    <button id='ws_stop'>Detener</button>
    <div id='ws_status' style='margin-top:8px;color:#9ca3af'>idle</div>
  </div>
  <script>
    let ws = null; let mic = null; let ac = null; let source = null; let proc = null;
    const MIC_RATE = %MIC_RATE%;
    const OUT_RATE = %OUT_RATE%;
    const PLAYBACK_RATE = %PBR%;
    const VOLUME = %VOL%;
    const PREBUFFER_MS = %PBUF%;
    // Simple accumulator buffer for smoother playback
    let acc = [];
    let accSamples = 0;
    function start(){
      const st = document.getElementById('ws_status');
      try{
        const url = '%WS%' + '?user_id=' + encodeURIComponent('%USER%') + '&patient_id=' + encodeURIComponent('%PATIENT%');
        ws = new WebSocket(url);
        ws.binaryType = 'arraybuffer';
        ws.onopen = async ()=>{
          st.textContent = 'conectado – pidiendo micrófono…';
          mic = await navigator.mediaDevices.getUserMedia({audio:{sampleRate:MIC_RATE, channelCount:1}});
          ac = new (window.AudioContext||window.webkitAudioContext)({sampleRate:MIC_RATE});
          source = ac.createMediaStreamSource(mic);
          proc = ac.createScriptProcessor(4096,1,1);
          source.connect(proc); proc.connect(ac.destination);
          proc.onaudioprocess = (e)=>{
            const ch = e.inputBuffer.getChannelData(0);
            const buf = new ArrayBuffer(ch.length*2); const view = new DataView(buf); let o=0;
            for(let i=0;i<ch.length;i++){ let s=Math.max(-1,Math.min(1,ch[i])); view.setInt16(o, s<0?s*0x8000:s*0x7FFF, true); o+=2; }
            try{ if(ws && ws.readyState===1) ws.send(buf); }catch(_){ }
          };
          st.textContent='transmitiendo…';
        };
        ws.onmessage = (ev)=>{
          if(typeof ev.data === 'string'){ try{ const j=JSON.parse(ev.data); if(j.event&&j.text){ document.getElementById('ws_status').textContent = j.event+': '+j.text; } }catch(_){}; return; }
          const ab = ev.data; const pcm = new Int16Array(ab);
          // Convert to Float32 and accumulate
          const f32 = new Float32Array(pcm.length);
          for(let i=0;i<pcm.length;i++){ f32[i] = pcm[i]/32768; }
          acc.push(f32); accSamples += f32.length;
          const minSamples = Math.floor(OUT_RATE * (PREBUFFER_MS/1000));
          if(accSamples < minSamples){ return; }
          // Concatenate
          let all = new Float32Array(accSamples);
          let off = 0; for(const a of acc){ all.set(a, off); off += a.length; }
          acc = []; accSamples = 0;
          const ctx = new (window.AudioContext||window.webkitAudioContext)({sampleRate:OUT_RATE});
          const b = ctx.createBuffer(1, all.length, OUT_RATE); b.copyToChannel(all, 0, 0);
          const src = ctx.createBufferSource(); src.buffer=b; src.playbackRate.value = PLAYBACK_RATE;
          const gain = ctx.createGain(); gain.gain.value = VOLUME;
          src.connect(gain).connect(ctx.destination); src.start();
        };
        ws.onclose = ()=>{ document.getElementById('ws_status').textContent='cerrado'; };
        ws.onerror = (e)=>{ document.getElementById('ws_status').textContent='error'; };
      }catch(e){ document.getElementById('ws_status').textContent = 'error: '+e; }
    }
    function stop(){ try{ if(proc){ proc.disconnect(); proc=null; } if(source){ source.disconnect(); source=null; } if(ac){ ac.close(); ac=null; } if(mic){ mic.getTracks().forEach(t=>t.stop()); mic=null; } if(ws){ ws.close(); ws=null; } acc=[]; accSamples=0; document.getElementById('ws_status').textContent='detenido'; }catch(_){} }
    document.getElementById('ws_start').addEventListener('click', (e)=>{ e.preventDefault(); start(); });
    document.getElementById('ws_stop').addEventListener('click', (e)=>{ e.preventDefault(); stop(); });
  </script>
  """
  ws_url = (public_backend_url or '').replace('https://','wss://').replace('http://','ws://') + '/live/ws'
  ws_client = (ws_client
               .replace('%WS%', ws_url)
               .replace('%USER%', st.session_state.get('user_id_live') or 'u1')
               .replace('%PATIENT%', st.session_state.get('patient_id_live') or '')
               .replace('%MIC_RATE%', str(int(mic_rate)))
               .replace('%OUT_RATE%', str(int(out_rate)))
               .replace('%PBR%', str(float(playback_rate)))
               .replace('%VOL%', str(float(volume_gain)))
               .replace('%PBUF%', str(int(prebuffer_ms))))
  st.components.v1.html(ws_client, height=230)

  # Auto-start suggestion
  if st.session_state.live_session_id:
    st.caption("Sugerencia: pulsa Conectar para iniciar el streaming. Se usará la misma instrucción y voz Kore.") 