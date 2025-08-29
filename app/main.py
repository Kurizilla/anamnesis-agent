from fastapi import FastAPI, Body, Request
from pydantic import BaseModel
from google.adk.cli.utils.agent_loader import AgentLoader
from google.adk.runners import InMemoryRunner
from google.genai import types
import logging
import os
from pathlib import Path
import asyncio
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse, Response
from datetime import datetime, timezone
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional
from google.auth import default as google_auth_default
from google.auth.transport.requests import AuthorizedSession
from google import genai
from google.genai import types as genai_types
import io, wave
import uuid, json, base64
from fastapi import WebSocket, WebSocketDisconnect
from fhir_clini_assistant.agent import _INSTRUCTION as LIVE_SYSTEM_INSTRUCTION
import importlib
import re
import ast

logging.basicConfig(
  level=getattr(logging, os.getenv("LOGLEVEL", "INFO")),
  format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

# Helper to describe an agent (model/instruction)
def _describe_agent(agent_obj):
  info = {}
  try:
    info["model"] = getattr(agent_obj, "model", None)
  except Exception:
    info["model"] = None
  try:
    instr = getattr(agent_obj, "instruction", None)
    info["instruction_preview"] = (instr[:240] + "…") if isinstance(instr, str) and len(instr) > 240 else instr
  except Exception:
    info["instruction_preview"] = None
  return info

DEFAULT_AGENTS_DIR = str(Path(__file__).resolve().parents[1])
AGENTS_DIR = os.getenv("AGENTS_DIR", DEFAULT_AGENTS_DIR)
AGENT_NAME = os.getenv("AGENT_NAME", "fhir_clini_assistant")

# In-memory session mappings
SESSION_TO_PATIENT: dict[str, str] = {}
SESSION_TO_ENCOUNTER: dict[str, str] = {}
SESSION_TO_TRANSCRIPT: dict[str, list[tuple[str, str]]] = {}

# Live audio session manager (SDK-based)
class _LiveSessionState:
  def __init__(self, session_id: str):
    self.id = session_id
    self.in_q: asyncio.Queue = asyncio.Queue()  # items: {"type":"text"|"audio","data":..., "mime":...}
    self.out_q: asyncio.Queue = asyncio.Queue() # items sent to SSE as dict
    self.worker: asyncio.Task | None = None
    self.closed: bool = False

LIVE_SESSIONS: dict[str, _LiveSessionState] = {}

async def _live_worker(state: _LiveSessionState):
  model_id = os.getenv("LIVE_MODEL", "gemini-live-2.5-flash-preview-native-audio")
  client = genai.Client()
  cfg = genai_types.LiveConnectConfig(
    response_modalities=["AUDIO"],
    input_audio_transcription=genai_types.AudioTranscriptionConfig(),
    output_audio_transcription=genai_types.AudioTranscriptionConfig(),
    speech_config=genai_types.SpeechConfig(
      voice_config=genai_types.VoiceConfig(
        prebuilt_voice_config=genai_types.PrebuiltVoiceConfig(voice_name="Kore")
      )
    ),
    system_instruction=genai_types.Content(role="system", parts=[genai_types.Part(text=LIVE_SYSTEM_INSTRUCTION)]),
  )
  try:
    async with client.aio.live.connect(model=model_id, config=cfg) as session:
      async def _sender():
        while True:
          item = await state.in_q.get()
          if item is None:
            break
          try:
            if item.get("type") == "text":
              text = item.get("data") or ""
              await session.send_client_content(
                turns=genai_types.Content(role="user", parts=[genai_types.Part(text=text)]),
                turn_complete=True,
              )
            elif item.get("type") == "audio":
              data = item.get("data") or b""
              mime = item.get("mime") or "audio/pcm;rate=16000"
              await session.send_realtime_input(audio=genai_types.Blob(data=data, mime_type=mime))
          except Exception as e:
            await state.out_q.put({"event": "error", "message": f"sender_error: {e}"})

      async def _receiver():
        async for message in session.receive():
          try:
            sc = getattr(message, "server_content", None)
            if not sc:
              continue
            # Transcriptions
            if getattr(sc, "input_transcription", None) and getattr(sc.input_transcription, "text", None):
              await state.out_q.put({"event": "input_transcription", "text": sc.input_transcription.text})
            if getattr(sc, "output_transcription", None) and getattr(sc.output_transcription, "text", None):
              await state.out_q.put({"event": "output_transcription", "text": sc.output_transcription.text})
            # Audio chunks from model
            mt = getattr(sc, "model_turn", None)
            if mt and getattr(mt, "parts", None):
              for p in mt.parts:
                if getattr(p, "inline_data", None) and getattr(p.inline_data, "data", None):
                  b = p.inline_data.data  # raw PCM int16 24kHz
                  await state.out_q.put({
                    "event": "audio_chunk",
                    "mime": "audio/pcm;rate=24000",
                    "data": base64.b64encode(b).decode("ascii"),
                  })
          except Exception as e:
            await state.out_q.put({"event": "error", "message": f"receiver_error: {e}"})
        # End of stream
        await state.out_q.put({"event": "closed"})

      send_task = asyncio.create_task(_sender())
      recv_task = asyncio.create_task(_receiver())
      await asyncio.gather(send_task, recv_task)
  except Exception as e:
    await state.out_q.put({"event": "error", "message": f"live_connect_error: {e}"})
  finally:
    state.closed = True

loader = AgentLoader(agents_dir=AGENTS_DIR)
logger.info("AGENTS_DIR=%s AGENT_NAME=%s", AGENTS_DIR, AGENT_NAME)
agent = loader.load_agent(AGENT_NAME)
runner = InMemoryRunner(agent=agent, app_name="clini_assistant_api")

# Load dedicated agents for anamnesis and risk (text mode)
anamnesis_runner = None
risk_runner = None
try:
  from fhir_clini_assistant import anamnesis_agent as _ANAMNESIS_AGENT, risk_agent as _RISK_AGENT
  anamnesis_runner = InMemoryRunner(agent=_ANAMNESIS_AGENT, app_name="clini_assistant_anamnesis")
  risk_runner = InMemoryRunner(agent=_RISK_AGENT, app_name="clini_assistant_risk")
  logger.info("SPECIALIZED_AGENTS: anamnesis and risk runners initialized")
except Exception as e:
  logger.warning("SPECIALIZED_AGENTS_LOAD_FAIL: %s", e)

# Load live voice agent alongside the text agent
LIVE_AGENT_NAME = os.getenv("AGENT_NAME_LIVE", "fhir_clini_assistant_live")
logger.info("LIVE_AGENT_NAME=%s", LIVE_AGENT_NAME)
try:
  live_agent = loader.load_agent(LIVE_AGENT_NAME)
  live_runner = InMemoryRunner(agent=live_agent, app_name="clini_assistant_live_api")
  try:
    tools = []
    for t in getattr(live_agent, "tools", []) or []:
      tn = getattr(t, "name", None) or t.__class__.__name__
      tools.append(tn)
    logger.info("LIVE_TOOLS_LOADED: %s", ", ".join(tools))
    logger.info("LIVE_AGENT_DESC: %s", _describe_agent(live_agent))
  except Exception as e:
    logger.warning("LIVE_TOOLS_LIST_ERROR: %s", e)
except Exception as e:
  live_agent = None
  live_runner = None
  logger.warning("LIVE_AGENT_LOAD_FAIL: %s", e)

# Log tools on startup
try:
  tool_names = []
  for t in getattr(agent, "tools", []) or []:
    # OpenAPIToolset has many operations; show its class name
    tn = getattr(t, "name", None) or t.__class__.__name__
    tool_names.append(tn)
  logger.info("TOOLS_LOADED: %s", ", ".join(tool_names))
except Exception as e:
  logger.warning("TOOLS_LIST_ERROR: %s", e)

app = FastAPI(title="Clini Assistant API")

# Allow Streamlit UI (8501) to call this backend
app.add_middleware(
  CORSMiddleware,
  allow_origins=[
    "http://localhost:8501",
    "http://127.0.0.1:8501",
  ],
  allow_credentials=True,
  allow_methods=["*"],
  allow_headers=["*"],
)

class ChatRequest(BaseModel):
  user_id: str
  message: str
  patient_id: Optional[str] = None
  session_id: Optional[str] = None
  agent_kind: Optional[str] = None  # "anamnesis" | "risk"

class BootstrapRequest(BaseModel):
  user_id: str
  patient_id: str
  agent_kind: Optional[str] = None  # "anamnesis" | "risk"

@app.get("/debug/tools")
async def debug_tools():
  try:
    tools = []
    for t in getattr(agent, "tools", []) or []:
      tn = getattr(t, "name", None) or t.__class__.__name__
      tools.append(tn)
    return JSONResponse({"tools": tools})
  except Exception as e:
    return JSONResponse({"error": str(e)}, status_code=500)

@app.get("/debug/live_tools")
async def debug_live_tools():
  if not live_agent:
    return JSONResponse({"error": "live_agent not available", "agents_dir": AGENTS_DIR, "live_agent_name": LIVE_AGENT_NAME}, status_code=503)
  try:
    tools = []
    for t in getattr(live_agent, "tools", []) or []:
      tn = getattr(t, "name", None) or t.__class__.__name__
      tools.append(tn)
    return JSONResponse({"tools": tools, "agents_dir": AGENTS_DIR, "live_agent_name": LIVE_AGENT_NAME})
  except Exception as e:
    return JSONResponse({"error": str(e)}, status_code=500)

@app.get("/debug/live_agent")
async def debug_live_agent():
  if not live_agent:
    return JSONResponse({"error": "live_agent not available", "agents_dir": AGENTS_DIR, "live_agent_name": LIVE_AGENT_NAME}, status_code=503)
  return JSONResponse({"agent": _describe_agent(live_agent)})

@app.post("/bootstrap")
async def bootstrap(req: BootstrapRequest):
  logger.info("BOOTSTRAP_REQ user_id=%s patient_id=%s agent_kind=%s", req.user_id, req.patient_id, req.agent_kind)
  # Escoger runner según agente
  agent_kind = (req.agent_kind or "anamnesis").strip().lower()
  active_runner = runner
  if agent_kind == "risk" and risk_runner is not None:
    active_runner = risk_runner
  elif agent_kind == "anamnesis" and anamnesis_runner is not None:
    active_runner = anamnesis_runner

  session = await active_runner.session_service.create_session(app_name=getattr(active_runner, "app_name", "clini_assistant_api"), user_id=req.user_id)
  session_id = session.id
  # Inicializar transcript
  SESSION_TO_TRANSCRIPT[session_id] = []
  # Prefetch in parallel
  from fhir_clini_assistant.fhir_tools import GetPatientByIdTool, GetMotivoConsultaTool, GetAreasAfectadasTool
  patient_tool = GetPatientByIdTool()
  motivos_tool = GetMotivoConsultaTool()
  areas_tool = GetAreasAfectadasTool()
  async def _safe(coro):
    try:
      return await coro
    except Exception as e:
      logger.warning("BOOTSTRAP_PREFETCH_FAIL: %s", e)
      return None
  patient_task = _safe(patient_tool.run_async(args={"patient_id": req.patient_id}, tool_context=None))
  motivos_task = _safe(motivos_tool.run_async(args={"patient": req.patient_id}, tool_context=None))
  areas_task = _safe(areas_tool.run_async(args={"patient": req.patient_id}, tool_context=None))
  # Solo calcular score de riesgo en el agente de riesgo
  score_res = None
  if agent_kind == "risk":
    from fhir_clini_assistant.fhir_tools import ScoreRiesgoTool
    score_tool = ScoreRiesgoTool()
    score_task = _safe(score_tool.run_async(args={"patient": req.patient_id}, tool_context=None))
    patient_res, motivos_res, areas_res, score_res = await asyncio.gather(patient_task, motivos_task, areas_task, score_task)
  else:
    patient_res, motivos_res, areas_res = await asyncio.gather(patient_task, motivos_task, areas_task)

  # Crear Encounter in-progress para esta sesión (con propósito según agente)
  encounter_id = None
  try:
    from fhir_clini_assistant.fhir_tools import CreateEncounterTool
    enc_tool = CreateEncounterTool()
    purpose = "risk" if agent_kind == "risk" else "anamnesis"
    enc_res = await enc_tool.run_async(args={"patient_id": req.patient_id, "session_id": session_id, "purpose": purpose}, tool_context=None)
    encounter_id = (enc_res or {}).get("encounter_id")
    # Mapear sesión a encounter y patient para usos posteriores
    if encounter_id:
      SESSION_TO_ENCOUNTER[session_id] = encounter_id
    SESSION_TO_PATIENT[session_id] = req.patient_id
    logger.info("BOOTSTRAP_ENCOUNTER_CREATED id=%s purpose=%s", encounter_id, purpose)
  except Exception as e:
    logger.warning("BOOTSTRAP_ENCOUNTER_FAIL: %s", e)

  nombre = (patient_res or {}).get("nombre") if isinstance(patient_res, dict) else None
  motivos = (motivos_res or {}).get("motivos") if isinstance(motivos_res, dict) else None
  motivos_msg = (motivos_res or {}).get("mensaje") if isinstance(motivos_res, dict) else None
  areas = (areas_res or {}).get("areas") if isinstance(areas_res, dict) else None
  imc_val = None
  imc_score = None
  if isinstance(score_res, dict):
    imc = score_res.get("imc") or {}
    imc_val = imc.get("valor")
    imc_score = imc.get("score")
  edad_val = None
  edad_score = None
  if isinstance(score_res, dict):
    ed = score_res.get("edad") or {}
    edad_val = ed.get("valor")
    edad_score = ed.get("score")
  cintura_val = None
  cintura_score = None
  fumar_estado = None
  fumar_score = None
  if isinstance(score_res, dict):
    cin = score_res.get("cintura_cm") or {}
    cintura_val = cin.get("valor")
    cintura_score = cin.get("score")
    f = score_res.get("fumar") or {}
    fumar_estado = f.get("estado")
    fumar_score = f.get("score")
  sexo_genero = None
  sexo_score = None
  if isinstance(score_res, dict):
    sx = score_res.get("sexo") or {}
    sexo_genero = sx.get("genero")
    sexo_score = sx.get("score")
  analytes_score = None
  fpg_val = None
  fpg_cat = None
  a1c_val = None
  a1c_cat = None
  if isinstance(score_res, dict):
    an = score_res.get("analitos") or {}
    analytes_score = an.get("score")
    fpg = an.get("fpg") or {}
    a1c = an.get("hba1c") or {}
    fpg_val = fpg.get("valor")
    fpg_cat = fpg.get("categoria")
    a1c_val = a1c.get("valor")
    a1c_cat = a1c.get("categoria")
  trig_val = None
  trig_score = None
  if isinstance(score_res, dict):
    tr = score_res.get("trigliceridos") or {}
    trig_val = tr.get("valor")
    trig_score = tr.get("score")
  hdl_val = None
  hdl_score = None
  if isinstance(score_res, dict):
    hdl = score_res.get("hdl") or {}
    hdl_val = hdl.get("valor")
    hdl_score = hdl.get("score")
  riesgo_cat = None
  riesgo_pct = None
  riesgo_pts_obt = None
  riesgo_pts_max = None
  if isinstance(score_res, dict):
    rg = score_res.get("riesgo_global") or {}
    riesgo_cat = rg.get("categoria")
    pts = rg.get("puntos") or {}
    riesgo_pct = pts.get("porcentaje")
    riesgo_pts_obt = pts.get("obtenidos")
    riesgo_pts_max = pts.get("maximos")

  # Crear RiskAssessment únicamente en el flujo de riesgo
  risk_assessment_id = None
  if agent_kind == "risk":
    try:
      outcome_map = {"bajo": "low", "medio": "medium", "alto": "high"}
      outcome_code = outcome_map.get(str(riesgo_cat).lower(), "low")
      # Componer rationale sencillo en prosa con variables disponibles
      rationale_parts = []
      if imc_val is not None: rationale_parts.append(f"IMC {imc_val} (score {imc_score if imc_score is not None else 'NA'})")
      if cintura_val is not None: rationale_parts.append(f"cintura {cintura_val} cm (score {cintura_score if cintura_score is not None else 'NA'})")
      if fumar_estado is not None: rationale_parts.append(f"tabaquismo: {fumar_estado} (score {fumar_score if fumar_score is not None else 'NA'})")
      if fpg_val is not None and fpg_cat: rationale_parts.append(f"glucosa {fpg_val} mg/dL ({fpg_cat})")
      if a1c_val is not None and a1c_cat: rationale_parts.append(f"HbA1c {a1c_val}% ({a1c_cat})")
      if trig_val is not None: rationale_parts.append(f"triglicéridos {trig_val} mg/dL (score {trig_score if trig_score is not None else 'NA'})")
      if hdl_val is not None: rationale_parts.append(f"HDL {hdl_val} mg/dL (score {hdl_score if hdl_score is not None else 'NA'})")
      fam_score_local = None
      try:
        if isinstance(score_res, dict):
          fam = score_res.get("antecedentes_familiares") or {}
          fam_score_local = fam.get("primer_grado_riesgo")
      except Exception:
        fam_score_local = None
      if fam_score_local is not None: rationale_parts.append(f"antecedentes familiares (score {fam_score_local})")
      rationale_text = (
        f"Resultado de riesgo {outcome_code} basado en: " + ", ".join(rationale_parts) if rationale_parts else f"Resultado de riesgo {outcome_code}."
      )
      from fhir_clini_assistant.fhir_tools import CreateRiskAssessmentTool
      ra_tool = CreateRiskAssessmentTool()
      ra_args = {
        "patient_id": req.patient_id,
        "session_id": session_id,
        "encounter_id": encounter_id,
        "outcome": outcome_code,
        "rationale": rationale_text,
        "occurrence_datetime": datetime.now(timezone.utc).isoformat(),
        "evidence": (score_res or {}).get("evidence") if isinstance(score_res, dict) else None,
      }
      ra_res = await ra_tool.run_async(args=ra_args, tool_context=None)
      risk_assessment_id = (ra_res or {}).get("risk_assessment_id")
      logger.info("BOOTSTRAP_RISK_ASSESSMENT_CREATED id=%s outcome=%s", risk_assessment_id, outcome_code)
    except Exception as e:
      logger.warning("BOOTSTRAP_RISK_ASSESSMENT_FAIL: %s", e)

  fam_score = None
  fam_matches = []
  if isinstance(score_res, dict):
    fam = score_res.get("antecedentes_familiares") or {}
    fam_score = fam.get("primer_grado_riesgo")
    fam_matches = fam.get("coincidencias") or []

  context_lines = []
  if nombre: context_lines.append(f"Paciente: {nombre}")
  if motivos:
    context_lines.append("Motivos: " + ", ".join(motivos))
  elif motivos_msg:
    context_lines.append("[hint] No hay motivos de consulta registrados en el triage; pide el motivo principal al paciente.")
  if areas: context_lines.append("Áreas afectadas: " + ", ".join(areas))
  if imc_val is not None:
    context_lines.append(f"IMC: {imc_val} (score {imc_score if imc_score is not None else 'NA'})")
  if edad_val is not None:
    context_lines.append(f"Edad: {edad_val} (score {edad_score if edad_score is not None else 'NA'})")
  if cintura_val is not None:
    context_lines.append(f"Cintura: {cintura_val} cm (score {cintura_score if cintura_score is not None else 'NA'})")
  if fumar_estado is not None:
    context_lines.append(f"Fumar: {fumar_estado} (score {fumar_score if fumar_score is not None else 'NA'})")
  if sexo_genero is not None:
    context_lines.append(f"Sexo: {sexo_genero} (score {sexo_score if sexo_score is not None else 'NA'})")
  if analytes_score is not None:
    context_lines.append(f"Analitos (score global): {analytes_score}")
  if fpg_val is not None and fpg_cat is not None:
    context_lines.append(f"Glucosa: {fpg_val} mg/dL ({fpg_cat})")
  if a1c_val is not None and a1c_cat is not None:
    context_lines.append(f"HbA1c: {a1c_val}% ({a1c_cat})")
  if trig_val is not None:
    context_lines.append(f"Triglicéridos: {trig_val} (score {trig_score if trig_score is not None else 'NA'})")
  if hdl_val is not None:
    context_lines.append(f"HDL: {hdl_val} (score {hdl_score if hdl_score is not None else 'NA'})")
  if fam_score is not None:
    context_lines.append(f"Antecedentes familiares (score): {fam_score} – {', '.join(fam_matches) if fam_matches else 'sin coincidencias destacadas'}")

  kickoff = "\n".join(context_lines) if context_lines else None

  # First agent message
  parts = [types.Part.from_text(text=kickoff or "Hola, soy tu asistente clínico. ¿En qué puedo ayudarte hoy?")]
  content = types.Content(role="user", parts=parts)
  first_reply = ""
  try:
    async for event in active_runner.run_async(user_id=req.user_id, session_id=session_id, new_message=content):
      text_candidate = None
      if hasattr(event, "data") and getattr(event.data, "text", None):
        text_candidate = event.data.text
      elif hasattr(event, "content") and getattr(getattr(event, "content", None), "parts", None):
        try:
          text_candidate = "".join([(p.text or "") for p in event.content.parts if getattr(p, "text", None)])
        except Exception:
          text_candidate = None
      if text_candidate:
        first_reply = text_candidate
  except Exception as e:
    logger.warning("BOOTSTRAP_AGENT_FAIL: %s", e)

  # Guardar primer mensaje del agente en transcript
  SESSION_TO_TRANSCRIPT.setdefault(session_id, []).append(("agent", first_reply))

  return {"session_id": session_id, "reply": first_reply, "prefetch": {
    "patient": patient_res, "motivos": motivos_res, "areas": areas_res, "score": score_res,
  }, "encounter_id": encounter_id, "risk_assessment_id": risk_assessment_id}

async def _llm_extract_criterios(session_id: str, user_text: str):
  try:
    from fhir_clini_assistant.fhir_tools import get_checklist_snapshot, UpdateCriterioEstadoTool
  except Exception as e:
    logger.debug("CHECKLIST_EXTRACT_IMPORT_FAIL: %s", e)
    return
  snap = get_checklist_snapshot(session_id)
  if not (snap and snap.get("exists")):
    return
  items = snap.get("pending_items") or []
  if not items:
    return
  area = snap.get("area") or ""
  try:
    client = genai.Client()
    model_id = os.getenv("ANAMNESIS_EXTRACTOR_MODEL", os.getenv("ANAMNESIS_AGENT_MODEL", "gemini-2.5-flash"))
    system = (
      "Eres un asistente clínico que extrae datos estructurados. "
      "Recibirás un área clínica activa y una lista de criterios (checklist). "
      "A partir del texto del paciente, indica qué criterios quedan satisfechos, su valor y una confianza 0..1. "
      "Responde SOLO en JSON. Formatos válidos: {\"items\":[{\"criterio\":...,\"value\":...,\"confidence\":0.0-1.0}]} o bien una lista simple de esos objetos. "
      "Usa exactamente los nombres de criterio provistos (case-insensitive). No inventes valores."
    )
    prompt = {
      "area": area,
      "criterios_pendientes": items,
      "texto_paciente": user_text,
      "output": {"items": [{"criterio": "<nombre exacto>", "value": "<resumen breve>", "confidence": 0.0}]}
    }
    logger.info("CHECKLIST_EXTRACT_REQ session_id=%s area=%s pending=%s text=%.120s", session_id, area, len(items), (user_text or "")[:120])
    msg = genai_types.Content(role="user", parts=[genai_types.Part(text=system + "\n" + json.dumps(prompt, ensure_ascii=False))])
    resp = await client.aio.models.generate_content(model=model_id, contents=[msg])
    logger.info("CHECKLIST_EXTRACT_MODEL=%s", model_id)
    text = ""
    try:
      if resp and resp.candidates and resp.candidates[0].content and resp.candidates[0].content.parts:
        text = "".join([p.text or "" for p in resp.candidates[0].content.parts if getattr(p, "text", None)])
    except Exception:
      text = ""
    logger.info("CHECKLIST_EXTRACT_RAW session_id=%s len=%d text=%.200s", session_id, len(text or ""), (text or "")[:200])
    if not text:
      return
    # Parse JSON (tolerant)
    data = None
    try:
      data = json.loads(text)
    except Exception:
      try:
        start = text.find("[")
        end = text.rfind("]")
        if start >= 0 and end > start:
          data = json.loads(text[start:end+1])
      except Exception:
        data = None
    if data is None:
      logger.info("CHECKLIST_EXTRACT_PARSE_FAIL session_id=%s", session_id)
      return
    # Normalize to list under key "items"
    if isinstance(data, dict) and isinstance(data.get("items"), list):
      items_out = data.get("items")
    elif isinstance(data, list):
      items_out = data
    else:
      logger.info("CHECKLIST_EXTRACT_PARSE_EMPTY session_id=%s", session_id)
      return
    tool = UpdateCriterioEstadoTool()
    applied = 0
    for obj in items_out:
      try:
        crit = (obj or {}).get("criterio")
        val = (obj or {}).get("value")
        conf = (obj or {}).get("confidence")
        if conf is not None:
          try:
            conf = float(conf)
          except Exception:
            conf = None
        if crit and val and (conf is None or conf >= float(os.getenv("ANAMNESIS_EXTRACT_CONF_THRESH", "0.6"))):
          await tool.run_async(args={"session_id": session_id, "criterio": str(crit), "status": "answered", "value": str(val)}, tool_context=None)
          applied += 1
      except Exception as e:
        logger.debug("CHECKLIST_EXTRACT_APPLY_FAIL criterio=%s err=%s", (obj or {}).get("criterio"), e)
    logger.info("CHECKLIST_EXTRACT_APPLIED session_id=%s area=%s matched=%d", session_id, area, applied)
  except Exception as e:
    logger.debug("CHECKLIST_EXTRACT_FAIL: %s", e)

def _extract_summary_from_text(text: str) -> Optional[str]:
  if not text:
    return None
  # Look for a block starting with 'Resumen' lines
  m = re.search(r"Resumen[\s\S]{0,40}?:\s*(.+)", text, re.IGNORECASE)
  if m:
    # Take from the match to the end, but cap length
    return text[m.start():].strip()[:4000]
  return None

def _strip_tool_calls(text: str) -> str:
  if not text:
    return text
  # Remove any lines that contain create_clinical_impression(...) or update_encounter_status(...)
  lines = (text or "").splitlines()
  cleaned = []
  for ln in lines:
    if re.search(r"\b(create_clinical_impression|update_encounter_status)\s*\(", ln):
      continue
    # remove inline code fences around those calls
    ln2 = re.sub(r"`\s*(create_clinical_impression|update_encounter_status)\s*\([^`]*\)`", "", ln)
    cleaned.append(ln2)
  return "\n".join(cleaned).strip()

async def _execute_tool_code(session_id: str, text: str) -> bool:
  if not text:
    return False
  # Try tag block first
  block = re.search(r"<execute_tool_code>([\s\S]+?)</execute_tool_code>", text)
  code = block.group(1) if block else text
  ran_any = False
  try:
    # Find all function calls with optional 'tools.' prefix
    pattern = re.compile(r"(?:tools\.)?(create_clinical_impression|update_encounter_status)\s*\((.*?)\)", re.DOTALL | re.IGNORECASE)
    matches = list(pattern.finditer(code))
    if not matches:
      return False
    ft = importlib.import_module('fhir_clini_assistant.fhir_tools')
    CreateClinicalImpressionTool = getattr(ft, 'CreateClinicalImpressionTool', None)
    UpdateEncounterStatusTool = getattr(ft, 'UpdateEncounterStatusTool', None)
    for m in matches:
      fname = m.group(1).strip()
      args_str = m.group(2)
      # Robust kwargs parsing via AST (supports commas inside strings)
      try:
        node = ast.parse(f"f({args_str})", mode='eval')
        if not isinstance(node.body, ast.Call):
          continue
        kwargs = {}
        for kw in node.body.keywords:
          kwargs[kw.arg] = ast.literal_eval(kw.value)
      except Exception:
        kwargs = {}
      if fname == 'create_clinical_impression' and CreateClinicalImpressionTool:
        ci_tool = CreateClinicalImpressionTool()
        # normalize keys to 'summary'
        if 'clinical_impression' in kwargs and 'summary' not in kwargs:
          kwargs['summary'] = kwargs.pop('clinical_impression')
        if 'impression' in kwargs and 'summary' not in kwargs:
          kwargs['summary'] = kwargs.pop('impression')
        res = await ci_tool.run_async(args=kwargs, tool_context=None)
        logger.info("CI_CREATE_OK session_id=%s res=%s", session_id, (res or {}))
        ran_any = True
      elif fname == 'update_encounter_status' and UpdateEncounterStatusTool:
        up_tool = UpdateEncounterStatusTool()
        if 'encounter_id' not in kwargs and 'session_id' not in kwargs:
          enc_id = SESSION_TO_ENCOUNTER.get(session_id)
          if enc_id:
            kwargs['encounter_id'] = enc_id
          else:
            kwargs['session_id'] = session_id
        res = await up_tool.run_async(args=kwargs, tool_context=None)
        logger.info("ENCOUNTER_UPDATE_OK session_id=%s res=%s", session_id, (res or {}))
        ran_any = True
  except Exception as e:
    logger.warning("EXEC_TOOL_CODE_FAIL session_id=%s err=%s", session_id, e)
  return ran_any

@app.post("/chat")
async def chat(req: ChatRequest):
  session_id = req.session_id or ""
  if not session_id:
    return JSONResponse({"error": "session_id requerido"}, status_code=400)

  # Escoger runner según agente
  agent_kind = (req.agent_kind or "anamnesis").strip().lower()
  active_runner = runner
  if agent_kind == "risk" and risk_runner is not None:
    active_runner = risk_runner
  elif agent_kind == "anamnesis" and anamnesis_runner is not None:
    active_runner = anamnesis_runner
  logger.info("CHAT_SELECT session_id=%s agent_kind=%s runner=%s", session_id, agent_kind, getattr(active_runner, "app_name", "unknown"))

  # Lazy-init checklist if missing (prefer anamnesis, but allow creation for any chat if needed)
  try:
    ft = importlib.import_module('fhir_clini_assistant.fhir_tools')
    logger.info("FHIR_TOOLS_EXPORTS=%s", sorted([a for a in dir(ft) if not a.startswith('_')])[:50])
    snap_fn = getattr(ft, 'get_checklist_snapshot', None)
    if callable(snap_fn):
      snap0 = snap_fn(session_id)
    else:
      snap0 = {"exists": False}
    logger.info("CHECKLIST_SNAP0 session_id=%s exists=%s counts=%s", session_id, snap0.get("exists"), snap0.get("counts"))
    if not snap0.get("exists") or (snap0.get("counts") or {}).get("total", 0) == 0:
      sel_area = "sintomas generales"
      pid = SESSION_TO_PATIENT.get(session_id)
      if pid:
        try:
          GetAreasAfectadasTool = getattr(ft, 'GetAreasAfectadasTool')
          areas_tool = GetAreasAfectadasTool()
          ar = await areas_tool.run_async(args={"patient": pid}, tool_context=None)
          lst = (ar or {}).get("areas")
          if isinstance(lst, list) and lst:
            sel_area = lst[0]
        except Exception as _:
          pass
      logger.info("CHECKLIST_INIT_ATTEMPT session_id=%s sel_area=%s has_tool=%s", session_id, sel_area, bool(getattr(ft, 'GetCriteriosChecklistTool', None)))
      GetCriteriosChecklistTool = getattr(ft, 'GetCriteriosChecklistTool', None)
      if GetCriteriosChecklistTool is None:
        ft = importlib.reload(ft)
        GetCriteriosChecklistTool = getattr(ft, 'GetCriteriosChecklistTool', None)
      if GetCriteriosChecklistTool is None:
        raise AttributeError("GetCriteriosChecklistTool not found in fhir_tools")
      chk_tool = GetCriteriosChecklistTool()
      chk_res = await chk_tool.run_async(args={"session_id": session_id, "area": sel_area}, tool_context=None)
      logger.info("ANAMNESIS_CHECKLIST_LAZY_INIT session_id=%s area=%s total=%s", session_id, (chk_res or {}).get("area"), (chk_res or {}).get("total"))
  except Exception as e:
    logger.warning("ANAMNESIS_CHECKLIST_LAZY_INIT_FAIL: %s", e)

  # Append user message to transcript
  SESSION_TO_TRANSCRIPT.setdefault(session_id, []).append(("user", req.message))

  # Server-side structured extraction: update checklist from user text if checklist exists
  try:
    ft2 = importlib.import_module('fhir_clini_assistant.fhir_tools')
    snap_fn2 = getattr(ft2, 'get_checklist_snapshot', None)
    snap_exists = bool(snap_fn2 and snap_fn2(session_id).get("exists"))
  except Exception:
    snap_exists = False
  if snap_exists:
    try:
      await _llm_extract_criterios(session_id, req.message or "")
    except Exception as _:
      pass

  # Compose content from user (+ optional hidden checklist anchor)
  parts = [types.Part.from_text(text=req.message)]
  try:
    # Hidden session/patient info for tool calls
    effective_pid = req.patient_id or SESSION_TO_PATIENT.get(session_id) or ""
    parts.insert(0, types.Part.from_text(text=f"session_id={session_id}"))
    if effective_pid:
      parts.insert(1, types.Part.from_text(text=f"patient_id={effective_pid}"))
    parts.insert(2, types.Part.from_text(text=f"agent_kind={agent_kind}"))
    # Snapshot checklist for anchoring (not shown to user)
    ft3 = importlib.import_module('fhir_clini_assistant.fhir_tools')
    snap_fn3 = getattr(ft3, 'get_checklist_snapshot', None)
    snap = snap_fn3(session_id) if callable(snap_fn3) else None
    if snap and snap.get("exists"):
      counts = snap.get("counts") or {}
      area = snap.get("area") or ""
      pending = ", ".join((snap.get("pending_items") or [])[:4])
      anchor = f"[checklist_anchor] area={area} counts={counts} pending4=[{pending}]"
      parts.insert(3, types.Part.from_text(text=anchor))
  except Exception as _:
    pass

  content = types.Content(role="user", parts=parts)

  last_text = ""
  try:
    async for event in active_runner.run_async(user_id=req.user_id, session_id=session_id, new_message=content):
      text_candidate = None
      if hasattr(event, "data") and getattr(event.data, "text", None):
        text_candidate = event.data.text
      elif hasattr(event, "content") and getattr(getattr(event, "content", None), "parts", None):
        try:
          text_candidate = "".join([(p.text or "") for p in event.content.parts if getattr(p, "text", None)])
        except Exception:
          text_candidate = None
      if text_candidate:
        last_text = text_candidate
  except Exception as e:
    logger.warning("CHAT_AGENT_FAIL: %s", e)

  # Append agent reply to transcript
  SESSION_TO_TRANSCRIPT.setdefault(session_id, []).append(("agent", last_text))

  # Execute any tool code emitted by agent
  try:
    executed = await _execute_tool_code(session_id, last_text or "")
    if executed:
      logger.info("EXEC_TOOL_CODE_DONE session_id=%s", session_id)
  except Exception as _:
    pass

  # Emit DEBUG with current checklist snapshot after agent reply
  try:
    ft4 = importlib.import_module('fhir_clini_assistant.fhir_tools')
    snap_fn4 = getattr(ft4, 'get_checklist_snapshot', None)
    s = snap_fn4(session_id) if callable(snap_fn4) else None
    if s:
      logger.info("ANAMNESIS_CHECKLIST session_id=%s area=%s counts=%s pending=%s", session_id, s.get("area"), s.get("counts"), ", ".join(s.get("pending_items") or [])[:256])
  except Exception as _:
    pass

  # Server-side fallback: si el agente no cierra, intenta generar ClinicalImpression
  try:
    # Triggers: explicit close phrases, presence of summary, or user's confirmation
    lower_last = (last_text or "").lower()
    # Strip tool call lines before extracting summary
    stripped_text = _strip_tool_calls(last_text or "")
    summary_text = _extract_summary_from_text(stripped_text)
    user_confirm = any((msg or "").lower().strip() in ("es correcto", "correcto") for role, msg in (SESSION_TO_TRANSCRIPT.get(session_id) or [])[-3:] if role == "user")
    trigger_close = any(k in lower_last for k in ["cerramos", "terminamos", "fin de la consulta", "con esto cerramos", "consulta ha finalizado"]) or summary_text is not None or user_confirm
    if trigger_close:
      # Generar resumen: preferir el extraído del mensaje; si no, pedir al modelo con todo el transcript
      resumen = summary_text
      if not resumen:
        transcript = SESSION_TO_TRANSCRIPT.get(session_id) or []
        if transcript:
          lines = []
          for role, text in transcript:
            if not text:
              continue
            prefix = "Paciente" if role == "user" else "Agente"
            # Strip potential tool calls from transcript lines too
            lines.append(f"{prefix}: {_strip_tool_calls(text)}")
          joined = "\n".join(lines)
          system_sum = types.Content(role="system", parts=[types.Part.from_text(text=(
            "Eres un asistente clínico. Resume en 8-14 líneas la anamnesis completa, "
            "destacando motivo de consulta, antecedentes relevantes, hallazgos reportados, y factores de riesgo clave. "
            "Escribe en español, redacta con oraciones completas y sin viñetas."
          ))])
          user_sum = types.Content(role="user", parts=[types.Part.from_text(text=joined)])
          try:
            async for ev in active_runner.run_async(user_id=req.user_id, session_id=session_id, new_message=system_sum):
              pass
            async for ev in active_runner.run_async(user_id=req.user_id, session_id=session_id, new_message=user_sum):
              if hasattr(ev, "data") and getattr(ev.data, "text", None):
                resumen = ev.data.text
              elif hasattr(ev, "content") and getattr(getattr(ev, "content", None), "parts", None):
                try:
                  resumen = "".join([(p.text or "") for p in ev.content.parts if getattr(p, "text", None)])
                except Exception:
                  resumen = None
          except Exception:
            resumen = None
      # Crear ClinicalImpression y completar Encounter
      from fhir_clini_assistant.fhir_tools import CreateClinicalImpressionTool, UpdateEncounterStatusTool
      ci_tool = CreateClinicalImpressionTool()
      up_tool = UpdateEncounterStatusTool()
      enc_id = SESSION_TO_ENCOUNTER.get(session_id)
      pid = SESSION_TO_PATIENT.get(session_id)
      if pid and (enc_id or session_id) and resumen:
        try:
          # Strip lingering tool-calls from resumen
          resumen_clean = _strip_tool_calls(resumen)
          args_ci = {"patient_id": pid, "summary": resumen_clean}
          if enc_id:
            args_ci["encounter_id"] = enc_id
          else:
            args_ci["session_id"] = session_id
          ci_res = await ci_tool.run_async(args=args_ci, tool_context=None)
          logger.info("CI_CREATE_OK_FALLBACK session_id=%s res=%s", session_id, (ci_res or {}))
          if enc_id:
            await up_tool.run_async(args={"encounter_id": enc_id, "status": "completed"}, tool_context=None)
          else:
            await up_tool.run_async(args={"session_id": session_id, "status": "completed"}, tool_context=None)
        except Exception as e:
          logger.warning("CI_CREATE_FAIL_FALLBACK session_id=%s err=%s", session_id, e)
  except Exception as e:
    logger.warning("CHAT_FALLBACK_CLOSE_FAIL: %s", e)

  return {"reply": last_text or ""}


# ========== WebRTC (Vertex Live API) ==========
def _build_live_webrtc_urls() -> list[str]:
  project = os.getenv("GOOGLE_CLOUD_PROJECT") or os.getenv("PROJECT_ID")
  location = os.getenv("GOOGLE_CLOUD_LOCATION") or os.getenv("GOOGLE_CLOUD_REGION") or "us-central1"
  model = os.getenv("LIVE_MODEL", "gemini-live-2.5-flash-preview-native-audio")
  # Endpoint override if provided
  override = os.getenv("LIVE_WEBRTC_URL")
  if override:
    return [override]
  # Correct Live API (native audio) endpoint shape candidates
  return [
    f"https://{location}-aiplatform.googleapis.com/v1/projects/{project}/locations/{location}:live:webrtc?model=publishers/google/models/{model}",
    f"https://{location}-aiplatform.googleapis.com/v1beta1/projects/{project}/locations/{location}:live:webrtc?model=publishers/google/models/{model}",
    f"https://{location}-aiplatform.googleapis.com/v1/projects/{project}/locations/{location}/live:webrtc?model=publishers/google/models/{model}",
    f"https://{location}-aiplatform.googleapis.com/v1beta1/projects/{project}/locations/{location}/live:webrtc?model=publishers/google/models/{model}",
  ]

@app.post("/live/webrtc/offer")
async def webrtc_offer(payload: dict):
  try:
    offer_type = (payload or {}).get("type") or "offer"
    offer_sdp = (payload or {}).get("sdp") or ""
    if not offer_sdp:
      return JSONResponse({"error": "missing sdp"}, status_code=400)
    urls = _build_live_webrtc_urls()
    creds, _ = google_auth_default()
    sess = AuthorizedSession(creds)

    # Try each URL: JSON first, then SDP fallback
    for url in urls:
      # JSON attempt
      try:
        body = {"type": offer_type, "sdp": offer_sdp}
        headers = {"Content-Type": "application/json"}
        logger.info("LIVE_WEBRTC_FORWARD_JSON url=%s len_sdp=%d", url, len(offer_sdp))
        resp = sess.post(url, headers=headers, json=body)
        if resp.status_code == 200 and (resp.json() or {}).get("sdp"):
          ans = resp.json() or {}
          return JSONResponse({"type": ans.get("type", "answer"), "sdp": ans.get("sdp", "")})
        logger.warning("LIVE_WEBRTC_JSON_FAIL status=%s body_len=%d url=%s", resp.status_code, len(getattr(resp, 'text', '') or ''), url)
      except Exception as e:
        logger.warning("LIVE_WEBRTC_JSON_EXC url=%s err=%s", url, e)

      # SDP attempt
      sdp_url = url + ("&alt=sdp" if "?" in url else "?alt=sdp")
      headers_sdp = {"Content-Type": "application/sdp", "Accept": "application/sdp"}
      logger.info("LIVE_WEBRTC_FORWARD_SDP url=%s len_sdp=%d", sdp_url, len(offer_sdp))
      resp2 = sess.post(sdp_url, headers=headers_sdp, data=offer_sdp)
      if resp2.status_code == 200:
        answer_sdp = resp2.text or ""
        if not answer_sdp.strip():
          logger.warning("LIVE_WEBRTC_SDP_EMPTY url=%s", sdp_url)
        return JSONResponse({"type": "answer", "sdp": answer_sdp})
      logger.warning("LIVE_WEBRTC_SDP_ERROR status=%s url=%s", resp2.status_code, sdp_url)

    return JSONResponse({"error": "live_api_error", "status": 404, "body": "All endpoint variants returned non-200"}, status_code=502)
  except Exception as e:
    logger.exception("LIVE_WEBRTC_EXCEPTION: %s", e)
    return JSONResponse({"error": str(e)}, status_code=500)


# Live voice endpoints (use live_runner/agent)
@app.post("/bootstrap_live")
async def bootstrap_live(req: BootstrapRequest):
  if not live_runner:
    logger.error("BOOTSTRAP_LIVE_UNAVAILABLE agents_dir=%s live_name=%s", AGENTS_DIR, LIVE_AGENT_NAME)
    return JSONResponse({"error": "Live agent not available", "agents_dir": AGENTS_DIR, "live_agent_name": LIVE_AGENT_NAME}, status_code=503)
  logger.info("BOOTSTRAP_LIVE_REQ user_id=%s patient_id=%s", req.user_id, req.patient_id)
  logger.info("BOOTSTRAP_LIVE_AGENT_MODEL %s", getattr(live_agent, "model", None))
  session = await live_runner.session_service.create_session(app_name="clini_assistant_live_api", user_id=req.user_id)
  session_id = session.id
  SESSION_TO_TRANSCRIPT[session_id] = []
  # Reuse same prefetch and encounter creation as text
  from fhir_clini_assistant.fhir_tools import GetPatientByIdTool, GetMotivoConsultaTool, GetAreasAfectadasTool, ScoreRiesgoTool
  async def _safe(coro):
    try:
      return await coro
    except Exception as e:
      logger.warning("BOOTSTRAP_LIVE_PREFETCH_FAIL: %s", e)
      return None
  patient_res = await _safe(GetPatientByIdTool().run_async(args={"patient_id": req.patient_id}, tool_context=None))
  motivos_res = await _safe(GetMotivoConsultaTool().run_async(args={"patient": req.patient_id}, tool_context=None))
  areas_res = await _safe(GetAreasAfectadasTool().run_async(args={"patient": req.patient_id}, tool_context=None))
  score_res = await _safe(ScoreRiesgoTool().run_async(args={"patient": req.patient_id}, tool_context=None))
  # Context extraction similar to text bootstrap
  nombre = (patient_res or {}).get("nombre") if isinstance(patient_res, dict) else None
  motivos = (motivos_res or {}).get("motivos") if isinstance(motivos_res, dict) else None
  motivos_msg = (motivos_res or {}).get("mensaje") if isinstance(motivos_res, dict) else None
  areas = (areas_res or {}).get("areas") if isinstance(areas_res, dict) else None
  context_lines = []
  if nombre: context_lines.append(f"Paciente: {nombre}")
  if motivos:
    context_lines.append("Motivos: " + ", ".join(motivos))
  elif motivos_msg:
    context_lines.append("[hint] No hay motivos de consulta registrados en el triage; pide el motivo principal al paciente.")
  if areas:
    context_lines.append("Áreas afectadas: " + ", ".join(areas))
  # Create Encounter
  encounter_id = None
  try:
    from fhir_clini_assistant.fhir_tools import CreateEncounterTool
    enc_tool = CreateEncounterTool()
    enc_res = await enc_tool.run_async(args={"patient_id": req.patient_id, "session_id": session_id}, tool_context=None)
    encounter_id = (enc_res or {}).get("encounter_id")
    if encounter_id:
      SESSION_TO_ENCOUNTER[session_id] = encounter_id
    SESSION_TO_PATIENT[session_id] = req.patient_id
    logger.info("BOOTSTRAP_LIVE_ENCOUNTER_CREATED id=%s", encounter_id)
  except Exception as e:
    logger.warning("BOOTSTRAP_LIVE_ENCOUNTER_FAIL: %s", e)
  # Build kickoff and send first turn (brief for voice)
  parts = [
    types.Part.from_text(text=f"patient:{req.patient_id}"),
    types.Part.from_text(text=f"session_id={session_id}"),
  ]
  if context_lines:
    parts.append(types.Part.from_text(text=f"[contexto_inicial] {' | '.join(context_lines)}"))
  if motivos:
    kickoff_live = (
      "Iniciemos. Veo motivos registrados. No asumas diagnósticos; en pocas palabras, cuéntame qué te preocupa más ahora mismo."
    )
  else:
    kickoff_live = (
      "Iniciemos. No tengo motivos registrados en triage. ¿Cuál es tu motivo principal de consulta hoy?"
    )
  parts.append(types.Part.from_text(text=kickoff_live))
  content = types.Content(role="user", parts=parts)
  logger.info("BOOTSTRAP_LIVE_KICKOFF parts=%d", len(parts))
  for i, p in enumerate(parts):
    try:
      logger.debug("BOOTSTRAP_LIVE_PART[%d]=%s", i, (p.text or "")[:200])
    except Exception:
      pass
  first_reply = None
  async for event in live_runner.run_async(user_id=req.user_id, session_id=session_id, new_message=content):
    if event.content and event.content.parts:
      text = "".join([p.text or "" for p in event.content.parts if p.text])
      if text:
        first_reply = text
  if first_reply:
    SESSION_TO_TRANSCRIPT.setdefault(session_id, []).append(("agent", first_reply))
  return {"session_id": session_id, "reply": first_reply, "encounter_id": encounter_id}


@app.post("/chat_live")
async def chat_live(req: ChatRequest):
  if not live_runner:
    return JSONResponse({"error": "Live agent not available"}, status_code=503)
  logger.info("CHAT_LIVE_REQ user_id=%s session_id=%s", req.user_id, req.session_id)
  logger.info("CHAT_LIVE_AGENT_MODEL %s", getattr(live_agent, "model", None))
  # Ensure session
  if req.session_id:
    session_id = req.session_id
    just_created = False
  else:
    session = await live_runner.session_service.create_session(app_name="clini_assistant_live_api", user_id=req.user_id)
    session_id = session.id
    just_created = True
  # Track user message
  SESSION_TO_TRANSCRIPT.setdefault(session_id, []).append(("user", req.message or ""))
  # Build parts
  parts = [types.Part.from_text(text=req.message or "")]
  pid = req.patient_id or SESSION_TO_PATIENT.get(session_id)
  if pid:
    parts.append(types.Part.from_text(text=f"patient:{pid}"))
  parts.append(types.Part.from_text(text=f"session_id={session_id}"))
  content = types.Content(role="user", parts=parts)
  logger.info("CHAT_LIVE_SEND parts=%d", len(parts))
  # Run
  last_text = None
  async for event in live_runner.run_async(user_id=req.user_id, session_id=session_id, new_message=content):
    if event.content and event.content.parts:
      text = "".join([p.text or "" for p in event.content.parts if p.text])
      if text:
        last_text = text
  if last_text:
    SESSION_TO_TRANSCRIPT.setdefault(session_id, []).append(("agent", last_text))
  return {"reply": last_text, "session_id": session_id}


# ---------- Live Connect (SDK) TTS fallback ----------
@app.post("/live/tts")
async def live_tts(req: dict):
  try:
    text = (req or {}).get("text") or "Hola, esta es una prueba de voz del agente Live."
    client = genai.Client()
    cfg = genai_types.LiveConnectConfig(
      response_modalities=["AUDIO"],
      input_audio_transcription=genai_types.AudioTranscriptionConfig(),
      output_audio_transcription=genai_types.AudioTranscriptionConfig(),
      proactivity=genai_types.ProactivityConfig(proactive_audio=True),
    )
    model_id = os.getenv("LIVE_MODEL", "gemini-live-2.5-flash")
    audio_chunks: list[bytes] = []

    async with client.aio.live.connect(model=model_id, config=cfg) as session:
      await session.send_client_content(
        turns=genai_types.Content(role="user", parts=[genai_types.Part(text=text)])
      )
      async for message in session.receive():
        sc = getattr(message, "server_content", None)
        if not sc:
          continue
        mt = getattr(sc, "model_turn", None)
        if mt and getattr(mt, "parts", None):
          for p in mt.parts:
            if getattr(p, "inline_data", None) and getattr(p.inline_data, "data", None):
              audio_chunks.append(p.inline_data.data)
    raw_pcm = b"".join(audio_chunks)
    if not raw_pcm:
      return JSONResponse({"error": "no_audio_returned"}, status_code=502)
    # Wrap PCM 16-bit mono 24kHz into WAV
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
      wf.setnchannels(1)
      wf.setsampwidth(2)
      wf.setframerate(24000)
      wf.writeframes(raw_pcm)
    return Response(content=buf.getvalue(), media_type="audio/wav")
  except Exception as e:
    logger.exception("LIVE_TTS_ERROR: %s", e)
    return JSONResponse({"error": str(e)}, status_code=500)

# ---------- Live SDK audio<->audio endpoints (WebSocket) ----------
@app.websocket("/live/ws")
async def live_ws(websocket: WebSocket):
  await websocket.accept()
  # Params for prefetch/bootstrap
  qp = websocket.query_params or {}
  user_id = qp.get("user_id") or "u1"
  patient_id = qp.get("patient_id") or ""
  # Create a local session id for mapping Encounter/Transcript
  ws_session_id = str(uuid.uuid4())
  SESSION_TO_TRANSCRIPT[ws_session_id] = []

  model_id = os.getenv("LIVE_MODEL", "gemini-live-2.5-flash-preview-native-audio")
  client = genai.Client()
  cfg = genai_types.LiveConnectConfig(
    response_modalities=["AUDIO"],
    input_audio_transcription=genai_types.AudioTranscriptionConfig(),
    output_audio_transcription=genai_types.AudioTranscriptionConfig(),
    speech_config=genai_types.SpeechConfig(
      voice_config=genai_types.VoiceConfig(
        prebuilt_voice_config=genai_types.PrebuiltVoiceConfig(voice_name="Kore")
      )
    ),
    system_instruction=genai_types.Content(role="system", parts=[genai_types.Part(text=LIVE_SYSTEM_INSTRUCTION)]),
  )
  try:
    async with client.aio.live.connect(model=model_id, config=cfg) as session:
      # Prefetch (similar to /bootstrap) and Encounter/RiskAssessment
      kickoff_live = None
      try:
        if patient_id:
          from fhir_clini_assistant.fhir_tools import (
            GetPatientByIdTool, GetMotivoConsultaTool, GetAreasAfectadasTool,
            ScoreRiesgoTool, CreateEncounterTool, CreateRiskAssessmentTool,
          )
          # Prefetch data
          patient_tool = GetPatientByIdTool()
          motivos_tool = GetMotivoConsultaTool()
          areas_tool = GetAreasAfectadasTool()
          score_tool = ScoreRiesgoTool()
          p_task = asyncio.create_task(patient_tool.run_async(args={"patient_id": patient_id}, tool_context=None))
          m_task = asyncio.create_task(motivos_tool.run_async(args={"patient": patient_id}, tool_context=None))
          a_task = asyncio.create_task(areas_tool.run_async(args={"patient": patient_id}, tool_context=None))
          s_task = asyncio.create_task(score_tool.run_async(args={"patient": patient_id}, tool_context=None))
          patient_res, motivos_res, areas_res, score_res = await asyncio.gather(p_task, m_task, a_task, s_task)
          nombre = (patient_res or {}).get("nombre") if isinstance(patient_res, dict) else None
          motivos = (motivos_res or {}).get("motivos") if isinstance(motivos_res, dict) else None
          motivos_msg = (motivos_res or {}).get("mensaje") if isinstance(motivos_res, dict) else None
          areas = (areas_res or {}).get("areas") if isinstance(areas_res, dict) else None
          # Create Encounter
          try:
            enc_tool = CreateEncounterTool()
            enc_res = await enc_tool.run_async(args={"patient_id": patient_id, "session_id": ws_session_id}, tool_context=None)
            enc_id = (enc_res or {}).get("encounter_id")
            if enc_id:
              SESSION_TO_ENCOUNTER[ws_session_id] = enc_id
            SESSION_TO_PATIENT[ws_session_id] = patient_id
            logger.info("LIVE_WS_ENCOUNTER_CREATED id=%s", enc_id)
          except Exception as e:
            logger.warning("LIVE_WS_ENCOUNTER_FAIL: %s", e)
          # RiskAssessment (same rationale light)
          try:
            outcome_map = {"bajo": "low", "medio": "medium", "alto": "high"}
            rg = (score_res or {}).get("riesgo_global") or {}
            outcome_code = outcome_map.get(str(rg.get("categoria", "")).lower(), "low")
            rationale = ""
            try:
              imc = (score_res or {}).get("imc") or {}
              parts = []
              if imc.get("valor") is not None:
                parts.append(f"IMC {imc.get('valor')}")
              an = (score_res or {}).get("analitos") or {}
              if (an.get("fpg") or {}).get("valor") is not None:
                parts.append(f"FPG {an['fpg'].get('valor')}")
              if (an.get("hba1c") or {}).get("valor") is not None:
                parts.append(f"HbA1c {an['hba1c'].get('valor')}")
              rationale = "; ".join(parts) or None
            except Exception:
              rationale = None
            ra_args = {
              "patient_id": patient_id,
              "session_id": ws_session_id,
              "outcome": outcome_code,
              "rationale": rationale or f"Resultado de riesgo {outcome_code}.",
              "occurrence_datetime": datetime.now(timezone.utc).isoformat(),
              "evidence": (score_res or {}).get("evidence"),
            }
            ra_res = await CreateRiskAssessmentTool().run_async(args=ra_args, tool_context=None)
            logger.info("LIVE_WS_RISK_CREATED id=%s", (ra_res or {}).get("risk_assessment_id"))
          except Exception as e:
            logger.warning("LIVE_WS_RISK_FAIL: %s", e)
          # Compose kickoff like text bootstrap
          lines = []
          if nombre: lines.append(f"Paciente: {nombre}")
          if motivos:
            lines.append("Motivos: " + ", ".join(motivos))
          elif motivos_msg:
            lines.append("[hint] No hay motivos de consulta registrados en el triage; pide el motivo principal al paciente.")
          if areas: lines.append("Áreas afectadas: " + ", ".join(areas))
          if motivos:
            kickoff_live = (
              "Inicia la consulta con saludo empático, menciona nombre, motivos y áreas afectadas disponibles, y formula la primera pregunta abierta para caracterizar el problema principal."
            )
          else:
            kickoff_live = (
              "Inicia la consulta con saludo empático. No asumas motivos de consulta. Explica brevemente que no hay motivos registrados en triage y pide de forma abierta que te cuente el motivo principal de consulta; luego continúa con preguntas de caracterización."
            )
          parts0 = [
            genai_types.Part(text=f"patient:{patient_id}"),
            genai_types.Part(text=f"session_id={ws_session_id}"),
          ]
          if lines:
            parts0.append(genai_types.Part(text=f"[contexto_inicial] {' | '.join(lines)}"))
          if kickoff_live:
            parts0.append(genai_types.Part(text=kickoff_live))
          await session.send_client_content(
            turns=genai_types.Content(role="user", parts=parts0),
            turn_complete=True,
          )
      except Exception as e:
        logger.warning("LIVE_WS_PREFETCH_FAIL: %s", e)

      async def _sender_from_ws():
        while True:
          try:
            msg = await websocket.receive()
          except WebSocketDisconnect:
            break
          data = msg.get("bytes")
          text = msg.get("text")
          try:
            if data is not None:
              await session.send_realtime_input(
                audio=genai_types.Blob(data=data, mime_type="audio/pcm;rate=16000")
              )
            elif text:
              try:
                j = json.loads(text)
                if j.get("type") == "text":
                  t = j.get("text") or ""
                  await session.send_client_content(
                    turns=genai_types.Content(role="user", parts=[genai_types.Part(text=t)]),
                    turn_complete=True,
                  )
              except Exception:
                await session.send_client_content(
                  turns=genai_types.Content(role="user", parts=[genai_types.Part(text=text)]),
                  turn_complete=True,
                )
          except Exception as e:
            await websocket.send_text(json.dumps({"event": "error", "message": f"send_error: {e}"}))
            break

      async def _receiver_to_ws():
        async for message in session.receive():
          sc = getattr(message, "server_content", None)
          if not sc:
            continue
          if getattr(sc, "input_transcription", None) and getattr(sc.input_transcription, "text", None):
            await websocket.send_text(json.dumps({"event": "input_transcription", "text": sc.input_transcription.text}))
            SESSION_TO_TRANSCRIPT.setdefault(ws_session_id, []).append(("user", sc.input_transcription.text))
          if getattr(sc, "output_transcription", None) and getattr(sc.output_transcription, "text", None):
            await websocket.send_text(json.dumps({"event": "output_transcription", "text": sc.output_transcription.text}))
            SESSION_TO_TRANSCRIPT.setdefault(ws_session_id, []).append(("agent", sc.output_transcription.text))
          mt = getattr(sc, "model_turn", None)
          if mt and getattr(mt, "parts", None):
            for p in mt.parts:
              if getattr(p, "inline_data", None) and getattr(p.inline_data, "data", None):
                await websocket.send_bytes(p.inline_data.data)

      send_task = asyncio.create_task(_sender_from_ws())
      recv_task = asyncio.create_task(_receiver_to_ws())
      await asyncio.gather(send_task, recv_task)
  except Exception as e:
    try:
      await websocket.send_text(json.dumps({"event": "error", "message": str(e)}))
    except Exception:
      pass
  finally:
    try:
      await websocket.close()
    except Exception:
      pass

# ---------- Live SDK audio<->audio endpoints ----------
@app.post("/live/session/start")
async def live_session_start():
  sid = str(uuid.uuid4())
  state = _LiveSessionState(session_id=sid)
  LIVE_SESSIONS[sid] = state
  state.worker = asyncio.create_task(_live_worker(state))
  logger.info("LIVE_SESSION_START id=%s", sid)
  return {"session_id": sid}

@app.post("/live/session/send-text")
async def live_session_send_text(payload: dict):
  sid = (payload or {}).get("session_id")
  text = (payload or {}).get("text") or ""
  st = LIVE_SESSIONS.get(sid)
  if not st:
    return JSONResponse({"error": "invalid_session"}, status_code=404)
  await st.in_q.put({"type": "text", "data": text})
  return {"ok": True}

@app.post("/live/session/send-audio")
async def live_session_send_audio(request: Request, session_id: str):
  st = LIVE_SESSIONS.get(session_id)
  if not st:
    return JSONResponse({"error": "invalid_session"}, status_code=404)
  data = await request.body()
  if not data:
    return JSONResponse({"error": "empty_body"}, status_code=400)
  await st.in_q.put({"type": "audio", "data": data, "mime": "audio/pcm;rate=16000"})
  return {"ok": True}

@app.get("/live/session/receive")
async def live_session_receive(session_id: str):
  st = LIVE_SESSIONS.get(session_id)
  if not st:
    return JSONResponse({"error": "invalid_session"}, status_code=404)

  async def _gen():
    try:
      # Initial hello
      yield f"data: {json.dumps({'event': 'open'})}\n\n"
      while True:
        msg = await st.out_q.get()
        yield f"data: {json.dumps(msg)}\n\n"
        if msg.get("event") in ("closed", "error"):
          break
    except asyncio.CancelledError:
      pass

  return StreamingResponse(_gen(), media_type="text/event-stream")

@app.post("/live/session/stop")
async def live_session_stop(payload: dict):
  sid = (payload or {}).get("session_id")
  st = LIVE_SESSIONS.pop(sid, None)
  if not st:
    return {"ok": True}
  try:
    await st.in_q.put(None)
    if st.worker and not st.worker.done():
      st.worker.cancel()
  except Exception:
    pass
  logger.info("LIVE_SESSION_STOP id=%s", sid)
  return {"ok": True}

@app.get("/healthz")
async def healthz():
  return {"status": "ok"}

@app.get("/", response_class=HTMLResponse)
async def ui_index():
  return """
<!doctype html>
<html lang=\"es\">
<head>
  <meta charset=\"utf-8\" />
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
  <title>Clini-Assistant (Local)</title>
  <style>
    :root{
      --bg:#0b1220;         /* slate-950 */
      --panel:#0f172a;      /* slate-900 */
      --muted:#94a3b8;      /* slate-400 */
      --text:#e5e7eb;       /* gray-200 */
      --border:#1e293b;     /* slate-800 */
      --primary:#22c55e;    /* green-500 */
      --primary-600:#16a34a;/* green-600 */
      --secondary:#334155;  /* slate-700 */
      --accent:#38bdf8;     /* sky-400 */
    }
    html,body{height:100%}
    body{font-family:system-ui,-apple-system,Segoe UI,Roboto,Arial,sans-serif;margin:0;background:var(--bg);color:var(--text)}
    .wrap{padding:20px}
    .card{background:var(--panel);border:1px solid var(--border);border-radius:12px;padding:16px;max-width:980px;margin:0 auto;box-shadow:0 1px 2px rgba(0,0,0,.25)}
    h2{margin:0 0 12px 0;font-weight:600}
    .row{display:flex;gap:12px;margin-bottom:12px;flex-wrap:wrap}
    .row>*{flex:1 1 240px}
    label{display:block;font-size:12px;color:var(--muted);margin-bottom:6px}
    input,textarea,button{width:100%;padding:10px;border:1px solid var(--border);border-radius:10px;font-size:14px;background:#0b1220;color:var(--text)}
    input:disabled{opacity:.6}
    textarea{resize:vertical;min-height:100px}
    button{background:var(--primary);border-color:transparent;color:#06120b;font-weight:600;cursor:pointer}
    button:hover{background:var(--primary-600)}
    button.secondary{background:var(--secondary);color:var(--text)}
    #transcript{white-space:pre-wrap;background:#0a0f1c;border:1px solid var(--border);border-radius:10px;padding:12px;max-height:420px;min-height:180px;overflow:auto;font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:13px}
    .muted{color:var(--muted);font-size:12px}
    .pill{display:inline-block;background:#0a182a;border:1px solid var(--border);padding:4px 8px;border-radius:999px;color:var(--accent);font-size:12px}
  </style>
  <script>
    let sessionId = localStorage.getItem('session_id') || '';
    let liveSessionId = localStorage.getItem('session_id_live') || '';
    function setSession(id){
      sessionId = id || '';
      if(sessionId) localStorage.setItem('session_id', sessionId); else localStorage.removeItem('session_id');
      document.getElementById('session_id').value = sessionId;
      const pid = document.getElementById('patient_id');
      pid.disabled = !!sessionId;
    }
    function setLiveSession(id){
      liveSessionId = id || '';
      if(liveSessionId) localStorage.setItem('session_id_live', liveSessionId); else localStorage.removeItem('session_id_live');
      document.getElementById('session_id_live').value = liveSessionId;
      const pid = document.getElementById('patient_id_live');
      pid.disabled = !!liveSessionId;
    }
    async function sendMessage(){
      const btn = document.getElementById('send_btn');
      console.log('[UI] click send');
      btn.disabled = true; btn.textContent = 'Enviando…';
      try{
        const userId = document.getElementById('user_id').value.trim() || 'u1';
        const patientId = document.getElementById('patient_id').value.trim();
        const message = document.getElementById('message').value.trim();
        console.log('[UI] payload pre', { userId, patientId, hasSession: !!sessionId, msgLen: message.length });
        if(!message){ btn.disabled=false; btn.textContent='Enviar'; return; }
        const payload = { user_id: userId, message: message };
        if(sessionId) payload.session_id = sessionId; else if(patientId) payload.patient_id = patientId;
        appendLine('You: ' + message);
        document.getElementById('message').value='';
        const res = await fetch('/chat', { method:'POST', headers:{ 'Content-Type':'application/json' }, body: JSON.stringify(payload) });
        console.log('[UI] fetch status', res.status);
        if(!res.ok){ const txt = await res.text(); console.error('[UI] fetch error body', txt); appendLine('Error: ' + res.status + ' - ' + txt); return; }
        const data = await res.json();
        console.log('[UI] response', data);
        if(data.session_id && !sessionId) setSession(data.session_id);
        appendLine('Agent: ' + (data.reply || '(sin respuesta)'));
      }catch(e){ console.error('[UI] network error', e); appendLine('Error de red: ' + e); }
      finally{ btn.disabled=false; btn.textContent='Enviar'; }
    }
    function resetSession(){ setSession(''); appendLine('[sesión reiniciada]'); }
    function appendLine(text){ const t=document.getElementById('transcript'); t.textContent += (t.textContent?'\n':'') + text; t.scrollTop=t.scrollHeight; }
    // Voice tab helpers
    async function bootstrapLive(){
      const userId = document.getElementById('user_id_live').value.trim() || 'u1';
      const patientId = document.getElementById('patient_id_live').value.trim();
      if(!patientId){ alert('Ingresa un Patient ID'); return; }
      const btn = document.getElementById('live_bootstrap_btn');
      btn.disabled = true; btn.textContent = 'Entrando…';
      try{
        const res = await fetch('/bootstrap_live', { method:'POST', headers:{ 'Content-Type':'application/json' }, body: JSON.stringify({ user_id:userId, patient_id:patientId }) });
        if(!res.ok){ const txt = await res.text(); alert('Error bootstrap: '+txt); return; }
        const data = await res.json();
        if(data.session_id && !liveSessionId) setLiveSession(data.session_id);
        appendVoice('Agent: ' + (data.reply || '(sin respuesta)'));
      } finally{ btn.disabled=false; btn.textContent='Entrar a la consulta'; }
    }
    function appendVoice(text){ const t=document.getElementById('voice_transcript'); t.textContent += (t.textContent?'\n':'') + text; t.scrollTop=t.scrollHeight; }
    async function sendVoiceMessage(text){
      const userId = document.getElementById('user_id_live').value.trim() || 'u1';
      const payload = { user_id: userId, message: text, session_id: liveSessionId };
      appendVoice('You: ' + text);
      const res = await fetch('/chat_live', { method:'POST', headers:{ 'Content-Type':'application/json' }, body: JSON.stringify(payload) });
      if(!res.ok){ const txt = await res.text(); appendVoice('Error: '+txt); return; }
      const data = await res.json();
      if(data.session_id && !liveSessionId) setLiveSession(data.session_id);
      appendVoice('Agent: ' + (data.reply || '(sin respuesta)'));
      speak((data.reply||''));
    }
    // Simple browser STT/TTS
    let recog = null; let recognizing=false;
    function initRecog(){ const R = window.SpeechRecognition || window.webkitSpeechRecognition; if(!R) return null; const r = new R(); r.lang='es-ES'; r.interimResults=false; r.maxAlternatives=1; r.onresult=(ev)=>{ const txt=ev.results[0][0].transcript; sendVoiceMessage(txt); }; r.onerror=(e)=>{ console.warn('recog error', e); }; r.onend=()=>{ recognizing=false; updateRecogUI(); }; return r; }
    function startRecog(){ if(!recog) recog=initRecog(); if(!recog){ alert('Reconocimiento de voz no soportado en este navegador'); return; } recognizing=true; updateRecogUI(); recog.start(); }
    function stopRecog(){ if(recog && recognizing){ recog.stop(); } recognizing=false; updateRecogUI(); }
    function updateRecogUI(){ const b = document.getElementById('rec_btn'); if(!b) return; b.textContent = recognizing? 'Detener dictado' : 'Dictar'; }
    function speak(text){ try{ const u=new SpeechSynthesisUtterance(text||''); u.lang='es-ES'; speechSynthesis.speak(u);}catch(e){} }
    // Tabs
    function showTab(tab){ const t=document.getElementById('text_card'); const v=document.getElementById('voice_card'); if(tab==='text'){ t.style.display='block'; v.style.display='none'; } else { t.style.display='none'; v.style.display='block'; } }
    window.addEventListener('DOMContentLoaded', ()=>{
      setSession(sessionId);
      setLiveSession(liveSessionId);
      showTab('text');
      document.getElementById('send_btn').addEventListener('click', (e)=>{ e.preventDefault(); sendMessage(); });
      document.getElementById('message').addEventListener('keydown', (e)=>{
        if((e.ctrlKey||e.metaKey) && e.key==='Enter'){ e.preventDefault(); sendMessage(); }
      });
    });
  </script>
</head>
<body>
  <div class=\"wrap\">
    <div class=\"card\" style=\"margin-bottom:12px\"> 
      <div class=\"row\">
        <button class=\"secondary\" type=\"button\" onclick=\"showTab('text')\">Texto</button>
        <button class=\"secondary\" type=\"button\" onclick=\"showTab('voice')\">Voz (Live)</button>
      </div>
    </div>
    <div id=\"text_card\" class=\"card\">
      <h2>Clini-Assistant (Local) <span class=\"pill\">modo oscuro</span></h2>
      <div class=\"row\">
        <div>
          <label for=\"user_id\">User ID</label>
          <input id=\"user_id\" value=\"u1\" />
        </div>
        <div>
          <label for=\"patient_id\">Patient ID (solo primer turno)</label>
          <input id=\"patient_id\" placeholder=\"Patient UUID\" />
        </div>
        <div>
          <label for=\"session_id\">Session ID</label>
          <input id=\"session_id\" placeholder=\"auto\" disabled />
        </div>
      </div>
      <div id=\"transcript\" style=\"margin-top:12px;\"></div>
      <div class=\"row\">
        <div style=\"flex:1\">
          <label for=\"message\">Mensaje</label>
          <textarea id=\"message\" rows=\"3\" placeholder=\"Escribe tu mensaje... (Ctrl/Cmd + Enter para enviar)\"></textarea>
        </div>
      </div>
      <div class=\"row\">
        <button id=\"send_btn\" type=\"button\" onclick=\"sendMessage()\">Enviar</button>
        <button class=\"secondary\" type=\"button\" onclick=\"resetSession()\">Reiniciar sesión</button>
      </div>
      <div class=\"muted\">Sugerencia: en el primer turno ingresa el Patient ID, luego continúa usando la misma sesión.</div>
    </div>
    <div id=\"voice_card\" class=\"card\" style=\"display:none\">
      <h2>Clini-Assistant (Voz) <span class=\"pill\">preview</span></h2>
      <div class=\"row\">
        <div>
          <label for=\"user_id_live\">User ID</label>
          <input id=\"user_id_live\" value=\"u1\" />
        </div>
        <div>
          <label for=\"patient_id_live\">Patient ID (primer turno)</label>
          <input id=\"patient_id_live\" />
        </div>
        <div>
          <label for=\"session_id_live\">Session ID</label>
          <input id=\"session_id_live\" placeholder=\"auto\" disabled />
        </div>
      </div>
      <div class=\"row\">
        <button id=\"live_bootstrap_btn\" type=\"button\" onclick=\"bootstrapLive()\">Entrar a la consulta</button>
        <button id=\"rec_btn\" class=\"secondary\" type=\"button\" onclick=\"recognizing?stopRecog():startRecog()\">Dictar</button>
        <button class=\"secondary\" type=\"button\" onclick=\"setLiveSession(''); appendVoice('[sesión reiniciada]')\">Reiniciar sesión</button>
      </div>
      <div id=\"voice_transcript\" style=\"margin-top:12px; white-space:pre-wrap; background:#0a0f1c; border:1px solid var(--border); border-radius:10px; padding:12px; max-height:420px; min-height:180px; overflow:auto; font-family:ui-monospace, SFMono-Regular, Menlo, monospace; font-size:13px\"></div>
      <div class=\"muted\">Nota: Uso de reconocimiento y síntesis de voz del navegador para prototipado. El procesamiento clínico se hace con el agente Live.</div>
    </div>
  </div>
</body>
</html>
""" 