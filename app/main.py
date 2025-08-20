from fastapi import FastAPI, Body
from pydantic import BaseModel
from google.adk.cli.utils.agent_loader import AgentLoader
from google.adk.runners import InMemoryRunner
from google.genai import types
import logging
import os
from pathlib import Path
import asyncio
from fastapi.responses import HTMLResponse, JSONResponse
from datetime import datetime, timezone

logging.basicConfig(
  level=getattr(logging, os.getenv("LOGLEVEL", "INFO")),
  format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

DEFAULT_AGENTS_DIR = str(Path(__file__).resolve().parents[1])
AGENTS_DIR = os.getenv("AGENTS_DIR", DEFAULT_AGENTS_DIR)
AGENT_NAME = os.getenv("AGENT_NAME", "fhir_clini_assistant")

# In-memory session mappings
SESSION_TO_PATIENT: dict[str, str] = {}
SESSION_TO_ENCOUNTER: dict[str, str] = {}
SESSION_TO_TRANSCRIPT: dict[str, list[tuple[str, str]]] = {}

loader = AgentLoader(agents_dir=AGENTS_DIR)
agent = loader.load_agent(AGENT_NAME)
runner = InMemoryRunner(agent=agent, app_name="clini_assistant_api")

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

class ChatRequest(BaseModel):
  user_id: str
  message: str
  patient_id: str | None = None
  session_id: str | None = None

class BootstrapRequest(BaseModel):
  user_id: str
  patient_id: str

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

@app.post("/bootstrap")
async def bootstrap(req: BootstrapRequest):
  logger.info("BOOTSTRAP_REQ user_id=%s patient_id=%s", req.user_id, req.patient_id)
  session = await runner.session_service.create_session(app_name="clini_assistant_api", user_id=req.user_id)
  session_id = session.id
  # Inicializar transcript
  SESSION_TO_TRANSCRIPT[session_id] = []
  # Prefetch in parallel
  from fhir_clini_assistant.fhir_tools import GetPatientByIdTool, GetMotivoConsultaTool, GetAreasAfectadasTool
  patient_tool = GetPatientByIdTool()
  motivos_tool = GetMotivoConsultaTool()
  areas_tool = GetAreasAfectadasTool()
  from fhir_clini_assistant.fhir_tools import ScoreRiesgoTool
  score_tool = ScoreRiesgoTool()
  async def _safe(coro):
    try:
      return await coro
    except Exception as e:
      logger.warning("BOOTSTRAP_PREFETCH_FAIL: %s", e)
      return None
  patient_task = _safe(patient_tool.run_async(args={"patient_id": req.patient_id}, tool_context=None))
  motivos_task = _safe(motivos_tool.run_async(args={"patient": req.patient_id}, tool_context=None))
  areas_task = _safe(areas_tool.run_async(args={"patient": req.patient_id}, tool_context=None))
  score_task = _safe(score_tool.run_async(args={"patient": req.patient_id}, tool_context=None))
  patient_res, motivos_res, areas_res, score_res = await asyncio.gather(patient_task, motivos_task, areas_task, score_task)

  # Crear Encounter in-progress para esta sesión
  encounter_id = None
  try:
    from fhir_clini_assistant.fhir_tools import CreateEncounterTool
    enc_tool = CreateEncounterTool()
    enc_res = await enc_tool.run_async(args={"patient_id": req.patient_id, "session_id": session_id}, tool_context=None)
    encounter_id = (enc_res or {}).get("encounter_id")
    # Mapear sesión a encounter y patient para usos posteriores
    if encounter_id:
      SESSION_TO_ENCOUNTER[session_id] = encounter_id
    SESSION_TO_PATIENT[session_id] = req.patient_id
    logger.info("BOOTSTRAP_ENCOUNTER_CREATED id=%s", encounter_id)
  except Exception as e:
    logger.warning("BOOTSTRAP_ENCOUNTER_FAIL: %s", e)

  nombre = (patient_res or {}).get("nombre") if isinstance(patient_res, dict) else None
  motivos = (motivos_res or {}).get("motivos") if isinstance(motivos_res, dict) else None
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

  # Crear RiskAssessment enlazado al Encounter y Patient
  risk_assessment_id = None
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
      "evidence": (score_res or {}).get("evidence"),
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
  if motivos: context_lines.append("Motivos: " + ", ".join(motivos))
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
    tags = []
    if fpg_cat: tags.append(f"FPG {fpg_cat}")
    if a1c_cat: tags.append(f"HbA1c {a1c_cat}")
    extra = f" ({', '.join(tags)})" if tags else ""
    context_lines.append(f"Analitos: score {analytes_score}{extra}")
  if trig_val is not None:
    context_lines.append(f"Triglicéridos: {trig_val} mg/dL (score {trig_score if trig_score is not None else 'NA'})")
  if hdl_val is not None:
    context_lines.append(f"HDL: {hdl_val} mg/dL (score {hdl_score if hdl_score is not None else 'NA'})")
  if riesgo_cat is not None and riesgo_pct is not None:
    context_lines.append(f"Riesgo global: {riesgo_cat} ({riesgo_pct}% de {riesgo_pts_max} puntos)")
  if fam_score is not None:
    context_lines.append(f"Antecedentes familiares (1er grado): score {fam_score} ({len(fam_matches)} coincidencias)")

  parts = [
    types.Part.from_text(text=f"patient:{req.patient_id}"),
    types.Part.from_text(text=f"patient={req.patient_id}"),
    types.Part.from_text(text=f"patient_id={req.patient_id}"),
  ]
  if context_lines:
    parts.append(types.Part.from_text(text=f"[contexto_inicial] {' | '.join(context_lines)}"))
  # Kickoff instruction
  kickoff = (
    "Inicia la consulta con saludo empático, menciona nombre, motivos y áreas afectadas disponibles, "
    "y formula la primera pregunta abierta para caracterizar el problema principal."
  )
  parts.append(types.Part.from_text(text=kickoff))
  content = types.Content(role="user", parts=parts)

  first_reply = None
  async for event in runner.run_async(user_id=req.user_id, session_id=session_id, new_message=content):
    if event.content and event.content.parts:
      text = "".join([p.text or "" for p in event.content.parts if p.text])
      if text:
        first_reply = text
  # Guardar primer mensaje del agente en transcript
  try:
    if first_reply:
      SESSION_TO_TRANSCRIPT.setdefault(session_id, []).append(("agent", first_reply))
  except Exception:
    pass
  logger.info(
    "BOOTSTRAP_OK session_id=%s reply_len=%d nombre=%s motivos=%s areas=%s imc_val=%s imc_score=%s edad_val=%s edad_score=%s cintura_val=%s cintura_score=%s fumar_estado=%s fumar_score=%s sexo=%s sexo_score=%s analytes_score=%s trig_val=%s trig_score=%s hdl_val=%s hdl_score=%s riesgo_cat=%s riesgo_pct=%s fam_score=%s fam_matches=%s",
    session_id, len(first_reply or ""), nombre, (len(motivos or []) if isinstance(motivos, list) else 0),
    (len(areas or []) if isinstance(areas, list) else 0), imc_val, imc_score,
    edad_val, edad_score, cintura_val, cintura_score, fumar_estado, fumar_score, sexo_genero, sexo_score, analytes_score, trig_val, trig_score, hdl_val, hdl_score, riesgo_cat, riesgo_pct, fam_score, len(fam_matches or [])
  )
  return {"session_id": session_id, "reply": first_reply, "prefetch": {
    "nombre": nombre,
    "motivos": motivos,
    "areas": areas,
    "imc": {"valor": imc_val, "score": imc_score},
    "edad": {"valor": edad_val, "score": edad_score},
    "cintura_cm": {"valor": cintura_val, "score": cintura_score},
    "fumar": {"estado": fumar_estado, "score": fumar_score},
    "sexo": {"genero": sexo_genero, "score": sexo_score},
    "analitos": {"score": analytes_score, "fpg": {"valor": fpg_val, "categoria": fpg_cat}, "hba1c": {"valor": a1c_val, "categoria": a1c_cat}},
    "trigliceridos": {"valor": trig_val, "score": trig_score},
    "hdl": {"valor": hdl_val, "score": hdl_score},
    "riesgo_global": {"categoria": riesgo_cat, "puntos": {"obtenidos": riesgo_pts_obt, "maximos": riesgo_pts_max, "porcentaje": riesgo_pct}},
    "antecedentes_familiares": {"score": fam_score, "coincidencias": fam_matches},
  }, "encounter_id": encounter_id, "risk_assessment_id": risk_assessment_id}

@app.post("/chat")
async def chat(req: ChatRequest):
  logger.info("CHAT_REQ user_id=%s session_id=%s patient_id=%s msg_len=%d", req.user_id, req.session_id, req.patient_id, len(req.message or ""))
  # Create or reuse session
  if req.session_id:
    session_id = req.session_id
    just_created = False
  else:
    session = await runner.session_service.create_session(app_name="clini_assistant_api", user_id=req.user_id)
    session_id = session.id
    just_created = True
  logger.info("CHAT_SESSION id=%s created=%s", session_id, just_created)

  # Append user message to transcript
  try:
    SESSION_TO_TRANSCRIPT.setdefault(session_id, []).append(("user", req.message or ""))
  except Exception:
    pass

  # Prefetch only on first turn
  context_lines: list[str] = []
  if just_created and req.patient_id:
    try:
      from fhir_clini_assistant.fhir_tools import GetMotivoConsultaTool, GetPatientByIdTool
      motivos_tool = GetMotivoConsultaTool()
      motivos_res = await motivos_tool.run_async(args={"patient": req.patient_id}, tool_context=None)
      motivos_list = motivos_res.get("motivos") or []
      if motivos_list:
        context_lines.append("Motivos de consulta detectados: " + ", ".join(motivos_list))
      logger.info("CHAT_PREFETCH motivos_count=%d", len(motivos_list))
    except Exception as e:
      logger.warning("Prefetch motivos failed: %s", e)
    try:
      from fhir_clini_assistant.fhir_tools import GetPatientByIdTool
      patient_tool = GetPatientByIdTool()
      p = await patient_tool.run_async(args={"patient_id": req.patient_id}, tool_context=None)
      nombre = p.get("nombre") or ""
      if nombre:
        context_lines.append(f"Paciente: {nombre}")
      logger.info("CHAT_PREFETCH patient_name=%s", nombre or "(vacio)")
    except Exception as e:
      logger.warning("Prefetch patient failed: %s", e)

  parts = [types.Part.from_text(text=req.message)]
  # Incluir siempre contexto de paciente y sesión si está disponible
  effective_pid = req.patient_id or SESSION_TO_PATIENT.get(session_id)
  if effective_pid:
    parts.append(types.Part.from_text(text=f"patient:{effective_pid}"))
    parts.append(types.Part.from_text(text=f"patient={effective_pid}"))
    parts.append(types.Part.from_text(text=f"patient_id={effective_pid}"))
    parts.append(types.Part.from_text(text=f"Contexto: el ID del paciente es {effective_pid}."))
  if session_id:
    parts.append(types.Part.from_text(text=f"session_id={session_id}"))
  if context_lines:
    parts.append(types.Part.from_text(text=f"[contexto_inicial] {' | '.join(context_lines)}"))

  content = types.Content(role="user", parts=parts)
  logger.debug("CHAT_SEND parts=%d just_created=%s", len(parts), just_created)

  last_text = None
  try:
    async for event in runner.run_async(user_id=req.user_id, session_id=session_id, new_message=content):
      if event.content and event.content.parts:
        text = "".join([p.text or "" for p in event.content.parts if p.text])
        if text:
          last_text = text
  except Exception as e:
    logger.exception("CHAT_ERROR: %s", e)
    raise
  # Append agent reply to transcript
  try:
    if last_text:
      SESSION_TO_TRANSCRIPT.setdefault(session_id, []).append(("agent", last_text))
  except Exception:
    pass

  # Fallback: si el usuario indica cierre, registrar ClinicalImpression y cerrar Encounter
  def _looks_like_close(msg: str) -> bool:
    m = (msg or "").strip().lower()
    return any(
      kw in m for kw in [
        "es correcto", "todo correcto", "no tengo mas dudas", "no tengo más dudas", "no, gracias", "no gracias", "podemos terminar", "cerrar consulta", "fin de la consulta"
      ]
    )
  if _looks_like_close(req.message):
    try:
      from fhir_clini_assistant.fhir_tools import CreateClinicalImpressionTool, UpdateEncounterStatusTool
      effective_pid = req.patient_id or SESSION_TO_PATIENT.get(session_id)
      # Generar resumen de toda la sesión con el agente
      summary_text = None
      try:
        # Construir prompt con el transcript
        lines = []
        for role, text in (SESSION_TO_TRANSCRIPT.get(session_id) or [])[-100:]:  # limitar tamaño
          if not text:
            continue
          prefix = "Paciente" if role == "user" else "Agente"
          lines.append(f"{prefix}: {text}")
        transcript_blob = "\n".join(lines)
        instr = (
          "Genera un resumen de anamnesis clínicamente relevante en 6-10 líneas, claro y conciso, "
          "sin llamadas a herramientas, basado estrictamente en la conversación. "
          "Estructura: motivo de consulta; HPI; antecedentes y hábitos; hallazgos relevantes; cierre."
        )
        parts_sum = [
          types.Part.from_text(text="[tarea] resumen_anamnesis"),
          types.Part.from_text(text=instr),
          types.Part.from_text(text="[conversacion]"),
          types.Part.from_text(text=transcript_blob),
        ]
        content_sum = types.Content(role="user", parts=parts_sum)
        sum_text = None
        async for ev in runner.run_async(user_id=req.user_id, session_id=session_id, new_message=content_sum):
          if ev.content and ev.content.parts:
            t = "".join([p.text or "" for p in ev.content.parts if p.text])
            if t:
              sum_text = t
        summary_text = (sum_text or "").strip()
      except Exception as e:
        logger.warning("CHAT_CLOSE_SUMMARY_GEN_FAIL: %s", e)
      if not summary_text:
        summary_text = (last_text or "").strip() or "Anamnesis registrada por el asistente clínico."
      # Crear ClinicalImpression
      ci_tool = CreateClinicalImpressionTool()
      ci_args = {"patient_id": effective_pid, "session_id": session_id, "summary": summary_text}
      ci_res = await ci_tool.run_async(args=ci_args, tool_context=None)
      logger.info("CHAT_CLOSE CI_CREATED id=%s", (ci_res or {}).get("clinical_impression_id"))
      # Cerrar Encounter
      upd_tool = UpdateEncounterStatusTool()
      upd_res = await upd_tool.run_async(args={"session_id": session_id, "status": "completed"}, tool_context=None)
      logger.info("CHAT_CLOSE ENCOUNTER_COMPLETED id=%s", (upd_res or {}).get("encounter_id"))
      # Añadir confirmación al mensaje final si no hubo respuesta textual
      if not last_text:
        last_text = "He registrado tu anamnesis y cerrado la consulta. Gracias por tu tiempo."
    except Exception as e:
      logger.warning("CHAT_CLOSE_FALLBACK_FAIL: %s", e)

  logger.info("CHAT_OK reply_len=%d", len(last_text or ""))
  return {"reply": last_text, "session_id": session_id}

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
    function setSession(id){
      sessionId = id || '';
      if(sessionId) localStorage.setItem('session_id', sessionId); else localStorage.removeItem('session_id');
      document.getElementById('session_id').value = sessionId;
      const pid = document.getElementById('patient_id');
      pid.disabled = !!sessionId;
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
    window.addEventListener('DOMContentLoaded', ()=>{
      setSession(sessionId);
      document.getElementById('send_btn').addEventListener('click', (e)=>{ e.preventDefault(); sendMessage(); });
      document.getElementById('message').addEventListener('keydown', (e)=>{
        if((e.ctrlKey||e.metaKey) && e.key==='Enter'){ e.preventDefault(); sendMessage(); }
      });
    });
  </script>
</head>
<body>
  <div class=\"wrap\">
    <div class=\"card\">
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
      <div id="transcript" style="margin-top:12px;"></div>
      <div class="row">
        <div style="flex:1">
          <label for="message">Mensaje</label>
          <textarea id="message" rows="3" placeholder="Escribe tu mensaje... (Ctrl/Cmd + Enter para enviar)"></textarea>
        </div>
      </div>
      <div class="row">
        <button id="send_btn" type="button" onclick="sendMessage()">Enviar</button>
        <button class="secondary" type="button" onclick="resetSession()">Reiniciar sesión</button>
      </div>
      <div class="muted">Sugerencia: en el primer turno ingresa el Patient ID, luego continúa usando la misma sesión.</div>
    </div>
  </div>
</body>
</html>
""" 