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
import hashlib, time
from fastapi import WebSocket, WebSocketDisconnect
from fhir_clini_assistant.agent import _INSTRUCTION as LIVE_SYSTEM_INSTRUCTION
import importlib
import re
import ast
from app.config import VISIBLE_DELIM, JSON_DELIM, CLOSE_STATUS, SANITIZE_TOKENS, USE_FHIR_FALLBACK, USE_LEGACY_EXEC
from app.services.closure import parse_closing_blocks as svc_parse_closing_blocks, sanitize_visible_markdown as svc_sanitize_visible
from app.services.fhir import create_clinical_impression as fhir_create_ci, update_encounter_status as fhir_update_enc_status, rest_finish_encounter as fhir_rest_finish
from app.services.checklist import llm_extract_criterios as svc_llm_extract_criterios
from app.routes.live import router as live_router
from app.routes.live_sdk import router as live_sdk_router
from app.routes.text import router as text_router
from app.services.bootstrap import prefetch as svc_prefetch, create_encounter as svc_create_encounter, build_context_lines as svc_build_ctx, build_kickoff_text as svc_kickoff
from app.services.chat import build_user_parts_texts as svc_build_user_parts

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
ENCOUNTER_PLAN_HASHES: dict[str, set[str]] = {}

# Removed inline Live session manager; handled in app.routes.live_sdk

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

from app.api import app

# Allow Streamlit UI (8501) to call this backend

app.include_router(live_router)
app.include_router(live_sdk_router)
app.include_router(text_router)

# Expose shared state for routers
app.state.SESSION_TO_PATIENT = SESSION_TO_PATIENT
app.state.SESSION_TO_ENCOUNTER = SESSION_TO_ENCOUNTER
app.state.SESSION_TO_TRANSCRIPT = SESSION_TO_TRANSCRIPT
app.state.ENCOUNTER_PLAN_HASHES = ENCOUNTER_PLAN_HASHES
app.state.LIVE_SESSIONS = {} # Removed LIVE_SESSIONS
app.state.live_runner = live_runner
app.state.live_agent = live_agent
app.state.runner = runner
app.state.anamnesis_runner = anamnesis_runner
app.state.risk_runner = risk_runner


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

  # Prefetch via service
  patient_res, motivos_res, areas_res, score_res = await svc_prefetch(req.patient_id, agent_kind)

  # Crear Encounter in-progress para esta sesión (con propósito según agente)
  encounter_id = None
  try:
    purpose = "risk" if agent_kind == "risk" else "anamnesis"
    encounter_id = await svc_create_encounter(req.patient_id, session_id, purpose)
    if encounter_id:
      SESSION_TO_ENCOUNTER[session_id] = encounter_id
    SESSION_TO_PATIENT[session_id] = req.patient_id
    logger.info("BOOTSTRAP_ENCOUNTER_CREATED id=%s purpose=%s", encounter_id, purpose)
  except Exception as e:
    logger.warning("BOOTSTRAP_ENCOUNTER_FAIL: %s", e)

  # Build kickoff context
  context_lines = svc_build_ctx(patient_res, motivos_res, areas_res, score_res)
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
  }, "encounter_id": encounter_id, "risk_assessment_id": None}

async def _llm_extract_criterios(session_id: str, user_text: str):
  # Delegate to service implementation for consistency
  try:
    await svc_llm_extract_criterios(session_id, user_text)
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

# Deterministic closing blocks parsing and validation (added)
def _parse_closing_blocks(text: str) -> tuple[Optional[str], Optional[dict]]:
  return svc_parse_closing_blocks(text)

# Sanitize visible markdown from any accidental code/tool noise (added)
def _sanitize_visible_markdown(md: str) -> str:
  return svc_sanitize_visible(md)

# Minimal validation of CI payload (added)
def _validate_ci_payload(d: dict) -> tuple[bool, str]:
  try:
    ci = d.get("clinical_impression")
    if not isinstance(ci, dict):
      return False, "missing clinical_impression object"
    req = ("status", "subject_ref", "encounter_ref", "summary", "protocols")
    for k in req:
      if k not in ci:
        return False, f"missing {k}"
    if not isinstance(ci["status"], str): return False, "status must be str"
    if not (isinstance(ci["subject_ref"], str) and ci["subject_ref"].startswith("Patient/")):
      return False, "subject_ref must be 'Patient/<id>'"
    if not (isinstance(ci["encounter_ref"], str) and ci["encounter_ref"].startswith("Encounter/")):
      return False, "encounter_ref must be 'Encounter/<id>'"
    if not isinstance(ci["summary"], str): return False, "summary must be str"
    if not isinstance(ci["protocols"], list): return False, "protocols must be list"
    return True, "ok"
  except Exception as e:
    return False, f"exception {e}"

# Execute CI creation and encounter completion with idempotency and retries (added)
async def _deterministic_close(session_id: str, user_id: str, visible_md: str, payload: dict) -> tuple[bool, str]:
  ok, reason = _validate_ci_payload(payload)
  if not ok:
    logger.warning("CLOSE_VALIDATION_FAIL session_id=%s msg=%s", session_id, reason)
    return False, "validation_fail"
  ci = payload["clinical_impression"]
  subject_ref = ci.get("subject_ref")
  encounter_ref = ci.get("encounter_ref")
  # Prefer patient_id from server mapping; fallback to subject_ref if valid
  mapped_pid = SESSION_TO_PATIENT.get(session_id)
  patient_id = mapped_pid if mapped_pid else (subject_ref.split("/", 1)[1] if isinstance(subject_ref, str) and subject_ref.lower().startswith("patient/") else "")
  # Prefer encounter from session mapping; fallback to payload if looks valid
  encounter_id = SESSION_TO_ENCOUNTER.get(session_id)
  if not encounter_id and isinstance(encounter_ref, str) and encounter_ref.lower().startswith("encounter/"):
    eid = encounter_ref.split("/", 1)[1].strip()
    if eid and "<" not in eid and ">" not in eid:
      encounter_id = eid
  summary = ci.get("summary") or ""

  # Idempotency by hash of CI object
  try:
    canon = json.dumps(ci, sort_keys=True, ensure_ascii=False)
  except Exception:
    canon = str(ci)
  plan_hash = hashlib.sha256(canon.encode("utf-8")).hexdigest()
  seen = ENCOUNTER_PLAN_HASHES.setdefault(encounter_id or session_id, set())
  if plan_hash in seen:
    logger.info("CLOSE_IDEMPOTENT_SKIP encounter=%s hash=%s", (encounter_id or session_id), plan_hash[:12])
    # Ensure encounter finished
    try:
      from fhir_clini_assistant.fhir_tools import UpdateEncounterStatusTool
      args_up = {"status": CLOSE_STATUS}
      if encounter_id:
        args_up["encounter_id"] = encounter_id
      else:
        args_up["session_id"] = session_id
      await UpdateEncounterStatusTool().run_async(args=args_up, tool_context=None)
      logger.info("CLOSE_ENCOUNTER_OK encounter=%s (idempotent)", (encounter_id or session_id))
    except Exception as e:
      logger.warning("CLOSE_ENCOUNTER_FAIL encounter=%s err=%s (idempotent)", (encounter_id or session_id), e)
      if USE_FHIR_FALLBACK:
        try:
          await _complete_encounter_fallback(encounter_id=encounter_id, session_id=session_id)
          logger.info("CLOSE_ENCOUNTER_OK_FALLBACK encounter=%s (idempotent)", (encounter_id or session_id))
        except Exception as e2:
          logger.warning("CLOSE_ENCOUNTER_FAIL_FALLBACK encounter=%s err=%s (idempotent)", (encounter_id or session_id), e2)
    return True, plan_hash

  # Create CI with retries, then finish encounter
  # Use service wrappers for FHIR operations
  args_ci = {"patient_id": patient_id, "summary": summary}
  if encounter_id:
    args_ci["encounter_id"] = encounter_id
  else:
    args_ci["session_id"] = session_id
  attempts = 0
  last_err = None
  while attempts < 3:
    attempts += 1
    try:
      res = await fhir_create_ci(args_ci)
      ci_id = (res or {}).get("clinical_impression_id")
      logger.info("CLOSE_CI_OK encounter=%s patient=%s hash=%s ci_id=%s", (encounter_id or session_id), patient_id, plan_hash[:12], ci_id)
      seen.add(plan_hash)
      try:
        up_args = {"status": CLOSE_STATUS}
        if encounter_id:
          up_args["encounter_id"] = encounter_id
        else:
          up_args["session_id"] = session_id
        await fhir_update_enc_status(up_args)
        logger.info("CLOSE_ENCOUNTER_OK encounter=%s", (encounter_id or session_id))
      except Exception as e:
        logger.warning("CLOSE_ENCOUNTER_FAIL encounter=%s err=%s", (encounter_id or session_id), e)
        if USE_FHIR_FALLBACK:
          try:
            # REST fallback
            fhir_rest_finish(encounter_id=encounter_id, session_id=session_id, status=CLOSE_STATUS)
            logger.info("CLOSE_ENCOUNTER_OK_FALLBACK encounter=%s", (encounter_id or session_id))
          except Exception as e2:
            logger.warning("CLOSE_ENCOUNTER_FAIL_FALLBACK encounter=%s err=%s", (encounter_id or session_id), e2)
      return True, plan_hash
    except Exception as e:
      last_err = e
      time.sleep(0.5 * attempts)
  logger.warning("CLOSE_CI_FAIL encounter=%s patient=%s err=%s", (encounter_id or session_id), patient_id, last_err)
  return False, "create_ci_failed"

# Direct REST fallback to set Encounter.status (configurable)
async def _complete_encounter_fallback(encounter_id: Optional[str], session_id: str) -> None:
  # Delegate to service REST helper
  fhir_rest_finish(encounter_id=encounter_id, session_id=session_id, status=CLOSE_STATUS)

def _strip_tool_calls(text: str) -> str:
  if not text:
    return text
  removed_xml = 0
  removed_func = 0
  removed_yaml = 0
  removed_json = 0
  t = text
  # Remove execute_tool_code blocks
  t, n = re.subn(r"<\s*execute_tool_code\s*>[\s\S]*?<\s*/\s*execute_tool_code\s*>", "", t, flags=re.IGNORECASE)
  removed_xml += n
  # Remove XML-like tool tags with closing tag
  t, n = re.subn(r"<\s*(?:tools\.)?(create_clinical_impression|update_encounter_status)\b[^>]*>[\s\S]*?<\s*/\s*\1\s*>", "", t, flags=re.IGNORECASE)
  removed_xml += n
  # Remove self-closing XML-like tags
  t, n = re.subn(r"<\s*(?:tools\.)?(create_clinical_impression|update_encounter_status)\b[^>]*/\s*>", "", t, flags=re.IGNORECASE)
  removed_xml += n
  # Remove YAML-like blocks: tool_name: (newline) indented key: value lines
  lines = t.splitlines()
  out_lines = []
  i = 0
  while i < len(lines):
    ln = lines[i]
    m = re.match(r"\s*(?:tools\.)?(create_clinical_impression|update_encounter_status)\s*:\s*$", ln, flags=re.IGNORECASE)
    if m:
      removed_yaml += 1
      i += 1
      # Skip indented block
      while i < len(lines):
        if lines[i].strip() == "":
          i += 1
          continue
        if re.match(r"\s+\S", lines[i]):
          i += 1
          continue
        break
      continue
    out_lines.append(ln)
    i += 1
  t = "\n".join(out_lines)
  # Remove JSON tool blocks (simple heuristic: single-object blocks containing tool_code with our tool names)
  t, n = re.subn(r"\{[\s\S]*?\btool_code\b\s*:\s*\"(create_clinical_impression|update_encounter_status)\"[\s\S]*?\}", "", t, flags=re.IGNORECASE)
  removed_json += n
  # Remove function-call forms anywhere (with optional tools. prefix)
  t, n = re.subn(r"(?:tools\.)?(create_clinical_impression|update_encounter_status)\s*\([^\)]*\)", "", t, flags=re.IGNORECASE)
  removed_func += n
  # Remove inline code-fenced function calls and empty fences
  t = re.sub(r"`\s*(?:tools\.)?(create_clinical_impression|update_encounter_status)\s*\([^`]*\)`", "", t, flags=re.IGNORECASE)
  t = re.sub(r"(^|\n)>?\s*``\s*(\n|$)", "\n", t)  # strip lonely ``` remnants
  # Collapse excessive blank lines
  t = re.sub(r"\n{3,}", "\n\n", t)
  if removed_xml or removed_func or removed_yaml or removed_json:
    try:
      logger.info("STRIP_TOOL_CALLS removed xml=%d yaml=%d json=%d func=%d", removed_xml, removed_yaml, removed_json, removed_func)
    except Exception:
      pass
  return t.strip()

async def _execute_xml_tool_tags(session_id: str, text: str) -> bool:
  if not text:
    return False
  ran_any = False
  try:
    ft = importlib.import_module('fhir_clini_assistant.fhir_tools')
    CreateClinicalImpressionTool = getattr(ft, 'CreateClinicalImpressionTool', None)
    UpdateEncounterStatusTool = getattr(ft, 'UpdateEncounterStatusTool', None)

    def _parse_attrs(attrs_str: str) -> dict:
      out = {}
      # Support attr="..." or attr='...'
      for m in re.finditer(r"(\w+)\s*=\s*\"([^\"]*)\"", attrs_str):
        out[m.group(1)] = m.group(2)
      for m in re.finditer(r"(\w+)\s*=\s*'([^']*)'", attrs_str):
        out[m.group(1)] = m.group(2)
      return out

    # Closing-tag form
    pattern_close = re.compile(r"<\s*(?:tools\.)?(create_clinical_impression|update_encounter_status)\b([^>]*)>([\s\S]*?)<\s*/\s*\1\s*>", re.IGNORECASE)
    # Self-closing form
    pattern_self = re.compile(r"<\s*(?:tools\.)?(create_clinical_impression|update_encounter_status)\b([^>]*)/\s*>", re.IGNORECASE)

    matches = list(pattern_close.finditer(text)) + list(pattern_self.finditer(text))
    if matches:
      logger.info("EXEC_XML_TOOL found=%d", len(matches))
    for m in matches:
      fname = m.group(1).lower()
      attrs = _parse_attrs(m.group(2) or "")
      inner = m.group(3) if m.lastindex and m.lastindex >= 3 else None
      kwargs = dict(attrs)
      # Normalize keys
      if fname == 'create_clinical_impression':
        if 'summary' not in kwargs:
          if 'clinical_impression' in kwargs:
            kwargs['summary'] = kwargs.pop('clinical_impression')
          elif 'impression' in kwargs:
            kwargs['summary'] = kwargs.pop('impression')
          elif inner and inner.strip():
            kwargs['summary'] = inner.strip()
        if CreateClinicalImpressionTool:
          ci_tool = CreateClinicalImpressionTool()
          res = await ci_tool.run_async(args=kwargs, tool_context=None)
          logger.info("CI_CREATE_OK_XML session_id=%s res=%s", session_id, (res or {}))
          # Auto-close after CI
          try:
            enc_id = SESSION_TO_ENCOUNTER.get(session_id)
            up_tool = UpdateEncounterStatusTool()
            if enc_id:
              await up_tool.run_async(args={"encounter_id": enc_id, "status": "completed"}, tool_context=None)
            else:
              await up_tool.run_async(args={"session_id": session_id, "status": "completed"}, tool_context=None)
            logger.info("ENCOUNTER_AUTOCLOSE_OK_XML session_id=%s", session_id)
          except Exception as e:
            logger.warning("ENCOUNTER_AUTOCLOSE_FAIL_XML session_id=%s err=%s", session_id, e)
          ran_any = True
      elif fname == 'update_encounter_status':
        if 'encounter_id' not in kwargs and 'session_id' not in kwargs:
          enc_id = SESSION_TO_ENCOUNTER.get(session_id)
          if enc_id:
            kwargs['encounter_id'] = enc_id
          else:
            kwargs['session_id'] = session_id
        if UpdateEncounterStatusTool:
          up_tool = UpdateEncounterStatusTool()
          res = await up_tool.run_async(args=kwargs, tool_context=None)
          logger.info("ENCOUNTER_UPDATE_OK_XML session_id=%s res=%s", session_id, (res or {}))
          ran_any = True
  except Exception as e:
    logger.warning("EXEC_XML_TOOL_FAIL session_id=%s err=%s", session_id, e)
  return ran_any

async def _execute_yaml_tool_plans(session_id: str, text: str) -> bool:
  if not text:
    return False
  ran_any = False
  try:
    ft = importlib.import_module('fhir_clini_assistant.fhir_tools')
    CreateClinicalImpressionTool = getattr(ft, 'CreateClinicalImpressionTool', None)
    UpdateEncounterStatusTool = getattr(ft, 'UpdateEncounterStatusTool', None)
    lines = (text or "").splitlines()
    i = 0
    found = 0
    while i < len(lines):
      ln = lines[i]
      m = re.match(r"\s*(?:tools\.)?(create_clinical_impression|update_encounter_status)\s*:\s*$", ln, flags=re.IGNORECASE)
      if not m:
        i += 1
        continue
      tool_name = m.group(1).lower()
      i += 1
      block = []
      while i < len(lines):
        cur = lines[i]
        if cur.strip() == "":
          block.append(cur)
          i += 1
          continue
        if re.match(r"\s+\S", cur):
          block.append(cur)
          i += 1
          continue
        break
      # Parse key: value pairs
      kwargs = {}
      for b in block:
        mm = re.match(r"\s*([A-Za-z_][\w\-]*)\s*:\s*(.*)$", b)
        if not mm:
          continue
        k = mm.group(1)
        v = mm.group(2).strip()
        if v.startswith('"') and v.endswith('"') and len(v) >= 2:
          v = v[1:-1]
        elif v.startswith("'") and v.endswith("'") and len(v) >= 2:
          v = v[1:-1]
        elif v.lower() in ("null", "none"):
          v = None
        else:
          # Try numeric
          try:
            if "." in v:
              v = float(v)
            else:
              v = int(v)
          except Exception:
            pass
        kwargs[k] = v
      # Normalize keys
      if tool_name == 'create_clinical_impression' and CreateClinicalImpressionTool:
        if 'summary' not in kwargs:
          for alt in ('clinical_impression', 'impression', 'impression_text'):
            if alt in kwargs:
              kwargs['summary'] = kwargs.pop(alt)
              break
        ci = CreateClinicalImpressionTool()
        res = await ci.run_async(args=kwargs, tool_context=None)
        logger.info("CI_CREATE_OK_YAML session_id=%s res=%s", session_id, (res or {}))
        # Auto-close after CI
        try:
          enc_id = SESSION_TO_ENCOUNTER.get(session_id)
          up = UpdateEncounterStatusTool()
          if enc_id:
            await up.run_async(args={"encounter_id": enc_id, "status": "completed"}, tool_context=None)
          else:
            await up.run_async(args={"session_id": session_id, "status": "completed"}, tool_context=None)
          logger.info("ENCOUNTER_AUTOCLOSE_OK_YAML session_id=%s", session_id)
        except Exception as e:
          logger.warning("ENCOUNTER_AUTOCLOSE_FAIL_YAML session_id=%s err=%s", session_id, e)
        ran_any = True
        found += 1
      elif tool_name == 'update_encounter_status' and UpdateEncounterStatusTool:
        if 'encounter_id' not in kwargs and 'session_id' not in kwargs:
          enc_id = SESSION_TO_ENCOUNTER.get(session_id)
          if enc_id:
            kwargs['encounter_id'] = enc_id
          else:
            kwargs['session_id'] = session_id
        up = UpdateEncounterStatusTool()
        res = await up.run_async(args=kwargs, tool_context=None)
        logger.info("ENCOUNTER_UPDATE_OK_YAML session_id=%s res=%s", session_id, (res or {}))
        ran_any = True
        found += 1
    if found:
      logger.info("EXEC_YAML_TOOL found=%d", found)
  except Exception as e:
    logger.warning("EXEC_YAML_TOOL_FAIL session_id=%s err=%s", session_id, e)
  return ran_any

async def _execute_json_tool_blocks(session_id: str, text: str) -> bool:
  if not text:
    return False
  ran_any = False
  try:
    ft = importlib.import_module('fhir_clini_assistant.fhir_tools')
    CreateClinicalImpressionTool = getattr(ft, 'CreateClinicalImpressionTool', None)
    UpdateEncounterStatusTool = getattr(ft, 'UpdateEncounterStatusTool', None)
    # Find all JSON objects in text that contain tool_code
    objs = []
    for m in re.finditer(r"\{[\s\S]*?\}", text):
      chunk = m.group(0)
      if 'tool_code' not in chunk:
        continue
      try:
        data = json.loads(chunk)
        if isinstance(data, dict) and str(data.get('tool_code', '')).lower() in ('create_clinical_impression','update_encounter_status'):
          objs.append(data)
      except Exception:
        # Try to replace single quotes with double quotes as a fallback
        try:
          data = json.loads(chunk.replace("'", '"'))
          if isinstance(data, dict) and str(data.get('tool_code', '')).lower() in ('create_clinical_impression','update_encounter_status'):
            objs.append(data)
        except Exception:
          continue
    if objs:
      logger.info("EXEC_JSON_TOOL found=%d", len(objs))
    for data in objs:
      name = str(data.get('tool_code', '')).lower()
      if name == 'create_clinical_impression' and CreateClinicalImpressionTool:
        kwargs = dict(data)
        # Normalize keys
        kwargs.pop('tool_code', None)
        if 'summary' not in kwargs:
          for alt in ('clinical_impression','impression','impression_text','text'):
            if alt in kwargs and kwargs.get(alt):
              kwargs['summary'] = kwargs.pop(alt)
              break
        ci_tool = CreateClinicalImpressionTool()
        res = await ci_tool.run_async(args=kwargs, tool_context=None)
        logger.info("CI_CREATE_OK_JSON session_id=%s res=%s", session_id, (res or {}))
        # Auto-close
        try:
          up = UpdateEncounterStatusTool()
          enc_id = SESSION_TO_ENCOUNTER.get(session_id)
          if enc_id:
            await up.run_async(args={"encounter_id": enc_id, "status": "completed"}, tool_context=None)
          else:
            await up.run_async(args={"session_id": session_id, "status": "completed"}, tool_context=None)
          logger.info("ENCOUNTER_AUTOCLOSE_OK_JSON session_id=%s", session_id)
        except Exception as e:
          logger.warning("ENCOUNTER_AUTOCLOSE_FAIL_JSON session_id=%s err=%s", session_id, e)
        ran_any = True
      elif name == 'update_encounter_status' and UpdateEncounterStatusTool:
        kwargs = dict(data)
        kwargs.pop('tool_code', None)
        # Prefer mapping if encounter_id missing or looks like session
        if 'encounter_id' not in kwargs and 'session_id' not in kwargs:
          enc_id = SESSION_TO_ENCOUNTER.get(session_id)
          if enc_id:
            kwargs['encounter_id'] = enc_id
          else:
            kwargs['session_id'] = session_id
        res = await UpdateEncounterStatusTool().run_async(args=kwargs, tool_context=None)
        logger.info("ENCOUNTER_UPDATE_OK_JSON session_id=%s res=%s", session_id, (res or {}))
        ran_any = True
  except Exception as e:
    logger.warning("EXEC_JSON_TOOL_FAIL session_id=%s err=%s", session_id, e)
  return ran_any

async def _execute_tool_code(session_id: str, text: str) -> bool:
  if not text:
    return False
  # Try tag block first
  block = re.search(r"<execute_tool_code>([\s\S]+?)</execute_tool_code>", text)
  code = block.group(1) if block else text
  ran_any = False
  try:
    logger.info("EXEC_TOOL_SCAN session_id=%s len=%d", session_id, len(text or ""))
    # First, execute any XML-like tags
    xml_any = await _execute_xml_tool_tags(session_id, text)
    ran_any = ran_any or xml_any
    # Then, execute YAML-like tool plans
    yaml_any = await _execute_yaml_tool_plans(session_id, text)
    ran_any = ran_any or yaml_any
    # Then, execute JSON-like tool blocks
    json_any = await _execute_json_tool_blocks(session_id, text)
    ran_any = ran_any or json_any
    # Then, find function calls with optional 'tools.' prefix
    pattern = re.compile(r"(?:tools\.)?(create_clinical_impression|update_encounter_status)\s*\((.*?)\)", re.DOTALL | re.IGNORECASE)
    matches = list(pattern.finditer(code))
    if not matches:
      return ran_any
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
        # Auto-close after CI
        try:
          enc_id = SESSION_TO_ENCOUNTER.get(session_id)
          up_tool = UpdateEncounterStatusTool()
          if enc_id:
            await up_tool.run_async(args={"encounter_id": enc_id, "status": "completed"}, tool_context=None)
          else:
            await up_tool.run_async(args={"session_id": session_id, "status": "completed"}, tool_context=None)
          logger.info("ENCOUNTER_AUTOCLOSE_OK session_id=%s", session_id)
        except Exception as e:
          logger.warning("ENCOUNTER_AUTOCLOSE_FAIL session_id=%s err=%s", session_id, e)
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

  # Compose content from user (+ optional hidden checklist anchor)
  effective_pid = req.patient_id or SESSION_TO_PATIENT.get(session_id) or ""
  part_texts = svc_build_user_parts(session_id, agent_kind, req.message, effective_pid or None)
  parts = [types.Part.from_text(text=t) for t in part_texts]

  last_text = ""
  try:
    async for event in active_runner.run_async(user_id=req.user_id, session_id=session_id, new_message=types.Content(role="user", parts=parts)):
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

  # Deterministic closure pipeline: parse two-block response first
  logger.info("CHAT_REPLY_LEN session_id=%s len=%d", session_id, len(last_text or ""))
  visible_md, ci_payload = _parse_closing_blocks(last_text or "")
  logger.info("CHAT_BLOCKS_DETECT session_id=%s has_visible=%s has_json=%s", session_id, bool(visible_md), bool(ci_payload))
  if visible_md and ci_payload:
    sanitized = _sanitize_visible_markdown(visible_md)
    ok, _ = await _deterministic_close(session_id=session_id, user_id=req.user_id, visible_md=sanitized, payload=ci_payload)
    SESSION_TO_TRANSCRIPT.setdefault(session_id, []).append(("agent", sanitized))
    return {"reply": sanitized}
  # Else legacy path: execute any tool code emitted by agent before storing reply
  if USE_LEGACY_EXEC:
    try:
      executed = await _execute_tool_code(session_id, last_text or "")
      if executed:
        logger.info("EXEC_TOOL_CODE_DONE session_id=%s", session_id)
    except Exception as _:
      pass
  else:
    logger.info("LEGACY_EXEC_DISABLED session_id=%s", session_id)
  # Store and return cleaned text (tool instructions stripped and sanitized)
  cleaned_reply = _sanitize_visible_markdown(_strip_tool_calls(last_text or ""))
  SESSION_TO_TRANSCRIPT.setdefault(session_id, []).append(("agent", cleaned_reply))

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
    lower_last = (cleaned_reply or "").lower()
    # Strip tool call lines before extracting summary
    stripped_text = cleaned_reply
    logger.info("CLOSE_STRIP_LEN raw=%d stripped=%d", len(last_text or ''), len(stripped_text or ''))
    summary_text = _extract_summary_from_text(stripped_text)
    user_confirm = any((msg or "").lower().strip() in ("es correcto", "correcto") for role, msg in (SESSION_TO_TRANSCRIPT.get(session_id) or [])[-3:] if role == "user")
    trigger_close = any(k in lower_last for k in ["cerramos", "terminamos", "fin de la consulta", "con esto cerramos", "consulta ha finalizado"]) or summary_text is not None or user_confirm
    logger.info("CLOSE_CHECK session_id=%s has_summary=%s user_confirm=%s trigger=%s", session_id, bool(summary_text), user_confirm, trigger_close)
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
          logger.info("CI_SUMMARY_LEN cleaned=%d", len(resumen_clean or ''))
          args_ci = {"patient_id": pid, "summary": resumen_clean}
          if enc_id:
            args_ci["encounter_id"] = enc_id
          else:
            args_ci["session_id"] = session_id
          ci_res = await ci_tool.run_async(args=args_ci, tool_context=None)
          logger.info("CI_CREATE_OK_FALLBACK session_id=%s res=%s", session_id, (ci_res or {}))
          # Auto-close after CI created via fallback
          try:
            if enc_id:
              await up_tool.run_async(args={"encounter_id": enc_id, "status": "completed"}, tool_context=None)
            else:
              await up_tool.run_async(args={"session_id": session_id, "status": "completed"}, tool_context=None)
            logger.info("ENCOUNTER_AUTOCLOSE_OK_FALLBACK session_id=%s", session_id)
          except Exception as e:
            logger.warning("ENCOUNTER_AUTOCLOSE_FAIL_FALLBACK session_id=%s err=%s", session_id, e)
        except Exception as e:
          logger.warning("CI_CREATE_FAIL_FALLBACK session_id=%s err=%s", session_id, e)
  except Exception as e:
    logger.warning("CHAT_FALLBACK_CLOSE_FAIL: %s", e)

  return {"reply": cleaned_reply or ""}

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