from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from google.genai import types
from datetime import datetime, timezone
import asyncio

router = APIRouter()


@router.post("/bootstrap_live")
async def bootstrap_live(req: dict, request: Request):
  app = request.app
  live_runner = getattr(app.state, "live_runner", None)
  live_agent = getattr(app.state, "live_agent", None)
  if not live_runner:
    return JSONResponse({"error": "Live agent not available"}, status_code=503)
  user_id = (req or {}).get("user_id") or "u1"
  patient_id = (req or {}).get("patient_id") or ""
  if not patient_id:
    return JSONResponse({"error": "patient_id requerido"}, status_code=400)
  session = await live_runner.session_service.create_session(app_name="clini_assistant_live_api", user_id=user_id)
  session_id = session.id
  app.state.SESSION_TO_TRANSCRIPT[session_id] = []
  # Prefetch like text
  from fhir_clini_assistant.fhir_tools import GetPatientByIdTool, GetMotivoConsultaTool, GetAreasAfectadasTool, ScoreRiesgoTool
  async def _safe(coro):
    try:
      return await coro
    except Exception:
      return None
  patient_res = await _safe(GetPatientByIdTool().run_async(args={"patient_id": patient_id}, tool_context=None))
  motivos_res = await _safe(GetMotivoConsultaTool().run_async(args={"patient": patient_id}, tool_context=None))
  areas_res = await _safe(GetAreasAfectadasTool().run_async(args={"patient": patient_id}, tool_context=None))
  score_res = await _safe(ScoreRiesgoTool().run_async(args={"patient": patient_id}, tool_context=None))
  nombre = (patient_res or {}).get("nombre") if isinstance(patient_res, dict) else None
  motivos = (motivos_res or {}).get("motivos") if isinstance(motivos_res, dict) else None
  motivos_msg = (motivos_res or {}).get("mensaje") if isinstance(motivos_res, dict) else None
  areas = (areas_res or {}).get("areas") if isinstance(areas_res, dict) else None
  # Create Encounter
  encounter_id = None
  try:
    from fhir_clini_assistant.fhir_tools import CreateEncounterTool
    enc_tool = CreateEncounterTool()
    enc_res = await enc_tool.run_async(args={"patient_id": patient_id, "session_id": session_id}, tool_context=None)
    encounter_id = (enc_res or {}).get("encounter_id")
    if encounter_id:
      app.state.SESSION_TO_ENCOUNTER[session_id] = encounter_id
    app.state.SESSION_TO_PATIENT[session_id] = patient_id
  except Exception:
    pass
  # Kickoff
  parts = [
    types.Part.from_text(text=f"patient:{patient_id}"),
    types.Part.from_text(text=f"session_id={session_id}"),
  ]
  lines = []
  if nombre: lines.append(f"Paciente: {nombre}")
  if motivos: lines.append("Motivos: " + ", ".join(motivos))
  elif motivos_msg: lines.append("[hint] No hay motivos de consulta registrados en el triage; pide el motivo principal al paciente.")
  if areas: lines.append("Áreas afectadas: " + ", ".join(areas))
  if lines:
    parts.append(types.Part.from_text(text=f"[contexto_inicial] {' | '.join(lines)}"))
  kickoff_live = (
    "Iniciemos. Veo motivos registrados. No asumas diagnósticos; en pocas palabras, cuéntame qué te preocupa más ahora mismo."
    if motivos else "Iniciemos. No tengo motivos registrados en triage. ¿Cuál es tu motivo principal de consulta hoy?"
  )
  parts.append(types.Part.from_text(text=kickoff_live))
  content = types.Content(role="user", parts=parts)
  first_reply = None
  async for event in live_runner.run_async(user_id=user_id, session_id=session_id, new_message=content):
    if event.content and event.content.parts:
      text = "".join([p.text or "" for p in event.content.parts if p.text])
      if text:
        first_reply = text
  if first_reply:
    app.state.SESSION_TO_TRANSCRIPT.setdefault(session_id, []).append(("agent", first_reply))
  return {"session_id": session_id, "reply": first_reply, "encounter_id": encounter_id}


@router.post("/chat_live")
async def chat_live(req: dict, request: Request):
  app = request.app
  live_runner = getattr(app.state, "live_runner", None)
  if not live_runner:
    return JSONResponse({"error": "Live agent not available"}, status_code=503)
  user_id = (req or {}).get("user_id") or "u1"
  session_id = (req or {}).get("session_id")
  message = (req or {}).get("message") or ""
  if not session_id:
    session = await live_runner.session_service.create_session(app_name="clini_assistant_live_api", user_id=user_id)
    session_id = session.id
  app.state.SESSION_TO_TRANSCRIPT.setdefault(session_id, []).append(("user", message))
  # Build parts
  parts = [types.Part.from_text(text=message)]
  pid = (req or {}).get("patient_id") or app.state.SESSION_TO_PATIENT.get(session_id)
  if pid:
    parts.append(types.Part.from_text(text=f"patient:{pid}"))
  parts.append(types.Part.from_text(text=f"session_id={session_id}"))
  content = types.Content(role="user", parts=parts)
  last_text = None
  async for event in live_runner.run_async(user_id=user_id, session_id=session_id, new_message=content):
    if event.content and event.content.parts:
      text = "".join([p.text or "" for p in event.content.parts if p.text])
      if text:
        last_text = text
  if last_text:
    app.state.SESSION_TO_TRANSCRIPT.setdefault(session_id, []).append(("agent", last_text))
  return {"reply": last_text, "session_id": session_id} 