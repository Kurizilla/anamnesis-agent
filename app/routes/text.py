from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from google.genai import types
from typing import Optional
import importlib
import re
import json
from app.config import CLOSE_STATUS, USE_FHIR_FALLBACK, USE_LEGACY_EXEC
from app.services.bootstrap import prefetch as svc_prefetch, create_encounter as svc_create_encounter, build_context_lines as svc_build_ctx
from app.services.closure import parse_closing_blocks as svc_parse_closing_blocks, sanitize_visible_markdown as svc_sanitize_visible
from app.services.checklist import llm_extract_criterios as svc_llm_extract_criterios
from app.services.fhir import create_clinical_impression as fhir_create_ci, update_encounter_status as fhir_update_enc_status, rest_finish_encounter as fhir_rest_finish
from app.services.chat import build_user_parts_texts as svc_build_user_parts

router = APIRouter()


def _extract_summary_from_text(text: str) -> Optional[str]:
  if not text:
    return None
  m = re.search(r"Resumen[\s\S]{0,40}?:\s*(.+)", text, re.IGNORECASE)
  if m:
    return text[m.start():].strip()[:4000]
  return None


@router.post("/bootstrap")
async def bootstrap(req: dict, request: Request):
  app = request.app
  logger = app.logger if hasattr(app, 'logger') else None
  user_id = (req or {}).get("user_id")
  patient_id = (req or {}).get("patient_id")
  agent_kind = ((req or {}).get("agent_kind") or "anamnesis").strip().lower()
  if logger:
    logger.info("BOOTSTRAP_REQ user_id=%s patient_id=%s agent_kind=%s", user_id, patient_id, agent_kind)
  # Pick runner
  active_runner = getattr(app.state, 'runner', None)
  anamnesis_runner = getattr(app.state, 'anamnesis_runner', None)
  risk_runner = getattr(app.state, 'risk_runner', None)
  if agent_kind == "risk" and risk_runner is not None:
    active_runner = risk_runner
  elif agent_kind == "anamnesis" and anamnesis_runner is not None:
    active_runner = anamnesis_runner
  if not active_runner:
    return JSONResponse({"error": "runner_not_available"}, status_code=500)
  session = await active_runner.session_service.create_session(app_name=getattr(active_runner, "app_name", "clini_assistant_api"), user_id=user_id)
  session_id = session.id
  app.state.SESSION_TO_TRANSCRIPT[session_id] = []
  # Prefetch
  patient_res, motivos_res, areas_res, score_res = await svc_prefetch(patient_id, agent_kind)
  # Encounter
  encounter_id = None
  try:
    purpose = "risk" if agent_kind == "risk" else "anamnesis"
    encounter_id = await svc_create_encounter(patient_id, session_id, purpose)
    if encounter_id:
      app.state.SESSION_TO_ENCOUNTER[session_id] = encounter_id
    app.state.SESSION_TO_PATIENT[session_id] = patient_id
    if logger:
      logger.info("BOOTSTRAP_ENCOUNTER_CREATED id=%s purpose=%s", encounter_id, purpose)
  except Exception as e:
    if logger:
      logger.warning("BOOTSTRAP_ENCOUNTER_FAIL: %s", e)
  # Risk checklist init
  if agent_kind == "risk":
    try:
      ft = importlib.import_module('fhir_clini_assistant.fhir_tools')
      GetRiskChecklistTool = getattr(ft, 'GetRiskChecklistTool', None)
      if GetRiskChecklistTool is None:
        ft = importlib.reload(ft)
        GetRiskChecklistTool = getattr(ft, 'GetRiskChecklistTool', None)
      if GetRiskChecklistTool is None:
        raise AttributeError("GetRiskChecklistTool not found")
      chk_tool = GetRiskChecklistTool()
      await chk_tool.run_async(args={"session_id": session_id}, tool_context=None)
      # Populate checklist statuses from score_res
      anchor_snapshot = None
      try:
        UpdateRiskItemTool = getattr(ft, 'UpdateRiskItemTool')
        updater = UpdateRiskItemTool()
        sr = score_res or {}
        # altura_peso_para_imc
        imc_val = ((sr.get("imc") or {}).get("valor")) if isinstance(sr.get("imc"), dict) else None
        await updater.run_async(args={"session_id": session_id, "item": "altura_peso_para_imc", "status": ("answered" if imc_val is not None else "pending"), "value": (f"IMC {imc_val}" if imc_val is not None else None)}, tool_context=None)
        # cintura_cm
        cintura_val = ((sr.get("cintura_cm") or {}).get("valor")) if isinstance(sr.get("cintura_cm"), dict) else None
        await updater.run_async(args={"session_id": session_id, "item": "cintura_cm", "status": ("answered" if cintura_val is not None else "pending"), "value": (str(cintura_val) if cintura_val is not None else None)}, tool_context=None)
        # fumar_actual
        fumar_estado = ((sr.get("fumar") or {}).get("estado")) if isinstance(sr.get("fumar"), dict) else None
        await updater.run_async(args={"session_id": session_id, "item": "fumar_actual", "status": ("answered" if fumar_estado in ("actual", "no") else "pending"), "value": fumar_estado}, tool_context=None)
        # antecedentes_familiares_dm2_hta
        fam = sr.get("antecedentes_familiares") or {}
        fam_matches = fam.get("coincidencias") or []
        fam_score = fam.get("primer_grado_riesgo")
        fam_value = ("si" if fam_matches else ("no" if fam_score is not None else None))
        await updater.run_async(args={"session_id": session_id, "item": "antecedentes_familiares_dm2_hta", "status": ("answered" if fam_value is not None else "pending"), "value": fam_value}, tool_context=None)
        # sexo: prefer score_riesgo; fallback a Patient.gender
        sexo_genero = ((sr.get("sexo") or {}).get("genero")) if isinstance(sr.get("sexo"), dict) else None
        if not (sexo_genero and str(sexo_genero).strip()):
          try:
            p_gen = (patient_res or {}).get("genero") if isinstance(patient_res, dict) else None
            if p_gen:
              sexo_genero = p_gen
          except Exception:
            pass
        await updater.run_async(args={"session_id": session_id, "item": "sexo", "status": ("answered" if (sexo_genero or "").strip() else "pending"), "value": sexo_genero}, tool_context=None)
        # edad: prefer score_riesgo; fallback a Patient.birthDate
        edad_val = ((sr.get("edad") or {}).get("valor")) if isinstance(sr.get("edad"), dict) else None
        if edad_val is None:
          try:
            b = (patient_res or {}).get("fecha_de_nacimiento") if isinstance(patient_res, dict) else None
            if b:
              by, bm, bd = [int(x) for x in str(b).split('-')[:3]]
              from datetime import date
              today = date.today()
              edad_val = today.year - by - ((today.month, today.day) < (bm, bd))
          except Exception:
            edad_val = None
        await updater.run_async(args={"session_id": session_id, "item": "edad", "status": ("answered" if edad_val is not None else "pending"), "value": (str(edad_val) if edad_val is not None else None)}, tool_context=None)
        # Final snapshot for anchoring
        snap_fn_anchor = getattr(ft, 'get_risk_checklist_snapshot', None)
        anchor_snapshot = snap_fn_anchor(session_id) if callable(snap_fn_anchor) else None
      except Exception as e_upd:
        if logger:
          logger.info("RISK_CHECKLIST_STATUS_APPLY_FAIL session_id=%s err=%s", session_id, e_upd)
      if logger:
        snap_fn = getattr(ft, 'get_risk_checklist_snapshot', None)
        snap = snap_fn(session_id) if callable(snap_fn) else None
        logger.info("RISK_CHECKLIST_BOOTSTRAP session_id=%s snap=%s", session_id, (snap or {}).get('counts'))
    except Exception as e:
      if logger:
        logger.warning("RISK_CHECKLIST_BOOTSTRAP_FAIL: %s", e)
  # Kickoff
  context_lines = svc_build_ctx(patient_res, motivos_res, areas_res, score_res, agent_kind=agent_kind)
  # For risk, avoid motive prompt; ensure neutral kickoff
  kickoff = None
  if agent_kind == "risk":
    kickoff = "Hola, soy Clini-Assistant. Te acompañaré para completar algunos datos que ayudarán a personalizar tu atención."
  else:
    kickoff = "\n".join(context_lines) if context_lines else None
  # Include hidden parts so the agent can use tools without pedir ID
  first_parts = [
    types.Part.from_text(text=f"session_id={session_id}"),
    types.Part.from_text(text=f"agent_kind={agent_kind}"),
  ]
  if patient_id:
    first_parts.append(types.Part.from_text(text=f"patient_id={patient_id}"))
    first_parts.append(types.Part.from_text(text=f"patient:{patient_id}"))
  # Add latest risk checklist anchor BEFORE first model turn
  if agent_kind == "risk":
    try:
      if 'anchor_snapshot' in locals() and anchor_snapshot and isinstance(anchor_snapshot, dict) and anchor_snapshot.get('exists'):
        counts = anchor_snapshot.get('counts') or {}
        pending_list = (anchor_snapshot.get('pending_items') or [])
        pending4 = ", ".join(pending_list[:4])
        first_parts.append(types.Part.from_text(text=f"[checklist_anchor] kind=risk counts={counts} pending4=[{pending4}]"))
    except Exception:
      pass
  first_parts.append(types.Part.from_text(text=kickoff or "Hola, soy tu asistente clínico."))
  content = types.Content(role="user", parts=first_parts)
  first_reply = ""
  try:
    async for event in active_runner.run_async(user_id=user_id, session_id=session_id, new_message=content):
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
    if logger:
      logger.warning("BOOTSTRAP_AGENT_FAIL: %s", e)
  app.state.SESSION_TO_TRANSCRIPT.setdefault(session_id, []).append(("agent", first_reply))
  return {"session_id": session_id, "reply": first_reply, "prefetch": {
    "patient": patient_res, "motivos": motivos_res, "areas": areas_res, "score": score_res,
  }, "encounter_id": encounter_id, "risk_assessment_id": None}


@router.post("/chat")
async def chat(req: dict, request: Request):
  app = request.app
  logger = app.logger if hasattr(app, 'logger') else None
  user_id = (req or {}).get("user_id")
  session_id = (req or {}).get("session_id") or ""
  if not session_id:
    return JSONResponse({"error": "session_id requerido"}, status_code=400)
  agent_kind = ((req or {}).get("agent_kind") or "anamnesis").strip().lower()
  active_runner = getattr(app.state, 'runner', None)
  anamnesis_runner = getattr(app.state, 'anamnesis_runner', None)
  risk_runner = getattr(app.state, 'risk_runner', None)
  if agent_kind == "risk" and risk_runner is not None:
    active_runner = risk_runner
  elif agent_kind == "anamnesis" and anamnesis_runner is not None:
    active_runner = anamnesis_runner
  if logger:
    logger.info("CHAT_SELECT session_id=%s agent_kind=%s runner=%s", session_id, agent_kind, getattr(active_runner, "app_name", "unknown"))
  # Lazy-init checklist (only for anamnesis)
  if agent_kind != "risk":
    try:
      ft = importlib.import_module('fhir_clini_assistant.fhir_tools')
      snap_fn = getattr(ft, 'get_checklist_snapshot', None)
      snap0 = snap_fn(session_id) if callable(snap_fn) else {"exists": False}
      if logger:
        logger.info("CHECKLIST_SNAP0 session_id=%s exists=%s counts=%s", session_id, snap0.get("exists"), snap0.get("counts"))
      if not snap0.get("exists") or (snap0.get("counts") or {}).get("total", 0) == 0:
        sel_area = "sintomas generales"
        pid = app.state.SESSION_TO_PATIENT.get(session_id)
        if pid:
          try:
            GetAreasAfectadasTool = getattr(ft, 'GetAreasAfectadasTool')
            areas_tool = GetAreasAfectadasTool()
            ar = await areas_tool.run_async(args={"patient": pid}, tool_context=None)
            lst = (ar or {}).get("areas")
            if isinstance(lst, list) and lst:
              sel_area = lst[0]
          except Exception:
            pass
        if logger:
          logger.info("CHECKLIST_INIT_ATTEMPT session_id=%s sel_area=%s has_tool=%s", session_id, sel_area, bool(getattr(ft, 'GetCriteriosChecklistTool', None)))
        GetCriteriosChecklistTool = getattr(ft, 'GetCriteriosChecklistTool', None)
        if GetCriteriosChecklistTool is None:
          ft = importlib.reload(ft)
          GetCriteriosChecklistTool = getattr(ft, 'GetCriteriosChecklistTool', None)
        if GetCriteriosChecklistTool is None:
          raise AttributeError("GetCriteriosChecklistTool not found in fhir_tools")
        chk_tool = GetCriteriosChecklistTool()
        chk_res = await chk_tool.run_async(args={"session_id": session_id, "area": sel_area}, tool_context=None)
        if logger:
          logger.info("ANAMNESIS_CHECKLIST_LAZY_INIT session_id=%s area=%s total=%s", session_id, (chk_res or {}).get("area"), (chk_res or {}).get("total"))
    except Exception as e:
      if logger:
        logger.warning("ANAMNESIS_CHECKLIST_LAZY_INIT_FAIL: %s", e)
  # Append user
  message = (req or {}).get("message") or ""
  app.state.SESSION_TO_TRANSCRIPT.setdefault(session_id, []).append(("user", message))
  # Extract checklist criteria from user message before agent reply (only for anamnesis)
  if agent_kind != "risk":
    try:
      await svc_llm_extract_criterios(session_id, message)
    except Exception:
      pass
  else:
    try:
      from app.services.risk_checklist import llm_extract_risk as svc_llm_extract_risk
      # Auto-apply: mark any detected pending variables as answered before model turn
      await svc_llm_extract_risk(session_id, message)
      if logger:
        logger.info("RISK_MSG_AUTO_APPLY session_id=%s", session_id)
    except Exception as e:
      if logger:
        logger.info("RISK_MSG_AUTO_APPLY_ERR session_id=%s err=%s", session_id, e)
  # Risk: capture checklist BEFORE turn for diff logging
  pre_items_map = {}
  if agent_kind == "risk":
    try:
      ft_pre = importlib.import_module('fhir_clini_assistant.fhir_tools')
      GetRiskChecklistTool_pre = getattr(ft_pre, 'GetRiskChecklistTool', None)
      if GetRiskChecklistTool_pre is not None:
        chk_pre = await GetRiskChecklistTool_pre().run_async(args={"session_id": session_id}, tool_context=None)
        items_pre = (chk_pre or {}).get("items") or []
        for it in items_pre:
          name = str((it or {}).get("name") or "").lower()
          pre_items_map[name] = {"status": (it or {}).get("status"), "value": (it or {}).get("value")}
        if logger:
          try:
            pending_pre = [it.get("name") for it in items_pre if (it.get("status") or "").lower() == "pending"]
            answered_pre = [it.get("name") for it in items_pre if (it.get("status") or "").lower() == "answered"]
            logger.info("RISK_MSG_START session_id=%s pending=%s answered=%s", session_id, ", ".join(pending_pre)[:200], ", ".join(answered_pre)[:200])
          except Exception:
            pass
    except Exception:
      pass
  effective_pid = (req or {}).get("patient_id") or app.state.SESSION_TO_PATIENT.get(session_id) or ""
  part_texts = svc_build_user_parts(session_id, agent_kind, message, effective_pid or None)
  parts = [types.Part.from_text(text=t) for t in part_texts]
  last_text = ""
  try:
    async for event in active_runner.run_async(user_id=user_id, session_id=session_id, new_message=types.Content(role="user", parts=parts)):
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
    if logger:
      logger.warning("CHAT_AGENT_FAIL: %s", e)
  # Deterministic close
  if logger:
    logger.info("CHAT_REPLY_LEN session_id=%s len=%d", session_id, len(last_text or ""))
  visible_md, ci_payload = svc_parse_closing_blocks(last_text or "")
  if logger:
    logger.info("CHAT_BLOCKS_DETECT session_id=%s has_visible=%s has_json=%s", session_id, bool(visible_md), bool(ci_payload))
  if visible_md and ci_payload:
    sanitized = svc_sanitize_visible(visible_md)
    # Validate minimal payload
    try:
      ci = ci_payload.get("clinical_impression") if isinstance(ci_payload, dict) else None
      subject_ref = (ci or {}).get("subject_ref")
      encounter_ref = (ci or {}).get("encounter_ref")
      mapped_pid = app.state.SESSION_TO_PATIENT.get(session_id)
      patient_id = mapped_pid if mapped_pid else (subject_ref.split("/", 1)[1] if isinstance(subject_ref, str) and subject_ref.lower().startswith("patient/") else "")
      encounter_id = app.state.SESSION_TO_ENCOUNTER.get(session_id)
      if not encounter_id and isinstance(encounter_ref, str) and encounter_ref.lower().startswith("encounter/"):
        eid = encounter_ref.split("/", 1)[1].strip()
        if eid and "<" not in eid and ">" not in eid:
          encounter_id = eid
      plan_hash = None
      try:
        canon = json.dumps(ci, sort_keys=True, ensure_ascii=False)
        import hashlib
        plan_hash = hashlib.sha256((canon or "").encode("utf-8")).hexdigest()
      except Exception:
        plan_hash = None
      seen = app.state.ENCOUNTER_PLAN_HASHES.get(session_id) if hasattr(app.state, 'ENCOUNTER_PLAN_HASHES') else None
      if seen is None:
        seen = set()
        if hasattr(app.state, 'ENCOUNTER_PLAN_HASHES'):
          app.state.ENCOUNTER_PLAN_HASHES[session_id] = seen
      if plan_hash and plan_hash in seen:
        if logger:
          logger.info("CLOSE_CHECK already_applied hash=%s", plan_hash[:12])
      else:
        try:
          args_ci = {
            "patient_id": patient_id,
            "subject_ref": subject_ref,
            "encounter_id": encounter_id,
            "summary": (ci or {}).get("summary") or _extract_summary_from_text(sanitized) or "",
            "description_md": (ci or {}).get("description_md"),
            "problems": (ci or {}).get("problems"),
            "findings": (ci or {}).get("findings"),
            "prognosis": (ci or {}).get("prognosis"),
            "protocols": (ci or {}).get("protocols") or [],
            "recommendations": (ci or {}).get("recommendations"),
          }
          res = await fhir_create_ci(args_ci)
          ci_id = (res or {}).get("clinical_impression_id")
          if logger:
            logger.info("CLOSE_CI_OK encounter=%s patient=%s hash=%s ci_id=%s", (encounter_id or session_id), patient_id, (plan_hash or "")[:12], ci_id)
          if plan_hash:
            seen.add(plan_hash)
          try:
            up_args = {"status": CLOSE_STATUS}
            if encounter_id:
              up_args["encounter_id"] = encounter_id
            else:
              up_args["session_id"] = session_id
            await fhir_update_enc_status(up_args)
            if logger:
              logger.info("CLOSE_ENCOUNTER_OK encounter=%s", (encounter_id or session_id))
          except Exception as e:
            if logger:
              logger.warning("CLOSE_ENCOUNTER_FAIL encounter=%s err=%s", (encounter_id or session_id), e)
            if USE_FHIR_FALLBACK:
              try:
                fhir_rest_finish(encounter_id=encounter_id, session_id=session_id, status=CLOSE_STATUS)
                if logger:
                  logger.info("CLOSE_ENCOUNTER_OK_FALLBACK encounter=%s", (encounter_id or session_id))
              except Exception as e2:
                if logger:
                  logger.warning("CLOSE_ENCOUNTER_FAIL_FALLBACK encounter=%s err=%s", (encounter_id or session_id), e2)
        except Exception as e:
          if logger:
            logger.warning("CLOSE_CI_FAIL encounter=%s patient=%s err=%s", (encounter_id or session_id), patient_id, e)
    except Exception:
      pass
    app.state.SESSION_TO_TRANSCRIPT.setdefault(session_id, []).append(("agent", sanitized))
    # Risk: after visible response, log item diffs
    if agent_kind == "risk":
      try:
        ft_post = importlib.import_module('fhir_clini_assistant.fhir_tools')
        GetRiskChecklistTool_post = getattr(ft_post, 'GetRiskChecklistTool', None)
        if GetRiskChecklistTool_post is not None:
          chk_post = await GetRiskChecklistTool_post().run_async(args={"session_id": session_id}, tool_context=None)
          items_post = (chk_post or {}).get("items") or []
          updates = []
          for it in items_post:
            name = str((it or {}).get("name") or "").lower()
            st = (it or {}).get("status")
            val = (it or {}).get("value")
            before = pre_items_map.get(name)
            if before and (before.get("status") != st or before.get("value") != val):
              updates.append(f"{name}:{before.get('status')}=>{st}")
          if logger:
            if updates:
              logger.info("RISK_MSG_UPDATES session_id=%s updated=%d items=%s", session_id, len(updates), ", ".join(updates)[:300])
            else:
              logger.info("RISK_MSG_NO_UPDATES session_id=%s", session_id)
          # Fallback: if no updates and still pending, try risk extractor once
          pending_now = [it.get("name") for it in items_post if (it.get("status") or "").lower() == "pending"]
          if (not updates) and pending_now:
            try:
              if logger:
                logger.info("RISK_MSG_FALLBACK_TRY session_id=%s pending=%s", session_id, ", ".join(pending_now)[:200])
              from app.services.risk_checklist import llm_extract_risk as svc_llm_extract_risk
              await svc_llm_extract_risk(session_id, message)
              # Re-check snapshot and log
              chk_post2 = await GetRiskChecklistTool_post().run_async(args={"session_id": session_id}, tool_context=None)
              items_post2 = (chk_post2 or {}).get("items") or []
              updates_fb = []
              for it in items_post2:
                name = str((it or {}).get("name") or "").lower()
                st = (it or {}).get("status")
                val = (it or {}).get("value")
                before = pre_items_map.get(name)
                if before and (before.get("status") != st or before.get("value") != val):
                  updates_fb.append(f"{name}:{before.get('status')}=>{st}")
              if logger:
                if updates_fb:
                  logger.info("RISK_MSG_FALLBACK_UPDATES session_id=%s updated=%d items=%s", session_id, len(updates_fb), ", ".join(updates_fb)[:300])
                else:
                  logger.info("RISK_MSG_FALLBACK_NO_UPDATES session_id=%s", session_id)
            except Exception as e:
              if logger:
                logger.info("RISK_MSG_FALLBACK_ERR session_id=%s err=%s", session_id, e)
      except Exception:
        pass
    return {"reply": sanitized}
  # Legacy execution path
  if USE_LEGACY_EXEC:
    try:
      from app.main import _execute_tool_code, _strip_tool_calls  # reuse existing helpers
      executed = await _execute_tool_code(session_id, last_text or "")
      if executed and logger:
        logger.info("EXEC_TOOL_CODE_DONE session_id=%s", session_id)
    except Exception:
      pass
  else:
    if logger:
      logger.info("LEGACY_EXEC_DISABLED session_id=%s", session_id)
  # Store cleaned text
  try:
    from app.utils.sanitize import strip_tool_calls
    cleaned_reply = svc_sanitize_visible(strip_tool_calls(last_text or ""))
  except Exception:
    cleaned_reply = svc_sanitize_visible(last_text or "")
  app.state.SESSION_TO_TRANSCRIPT.setdefault(session_id, []).append(("agent", cleaned_reply))
  # Checklist debug snapshot (anamnesis only)
  if agent_kind != "risk":
    try:
      ft4 = importlib.import_module('fhir_clini_assistant.fhir_tools')
      snap_fn4 = getattr(ft4, 'get_checklist_snapshot', None)
      s = snap_fn4(session_id) if callable(snap_fn4) else None
      if s and logger:
        logger.info("ANAMNESIS_CHECKLIST session_id=%s area=%s counts=%s pending=%s", session_id, s.get("area"), s.get("counts"), ", ".join(s.get("pending_items") or [])[:256])
    except Exception:
      pass
  else:
    try:
      ft5 = importlib.import_module('fhir_clini_assistant.fhir_tools')
      snap_fn5 = getattr(ft5, 'get_risk_checklist_snapshot', None)
      s2 = snap_fn5(session_id) if callable(snap_fn5) else None
      if s2 and logger:
        logger.info("RISK_CHECKLIST session_id=%s counts=%s pending=%s", session_id, s2.get("counts"), ", ".join(s2.get("pending_items") or [])[:256])
      # Attempt risk closure when no pending
      counts = (s2 or {}).get("counts") or {}
      if int(counts.get("pending") or 0) == 0:
        try:
          from app.services.closure import try_risk_close
          pid = app.state.SESSION_TO_PATIENT.get(session_id)
          res_close = await try_risk_close(session_id, pid)
          if res_close and logger:
            logger.info("RISK_CLOSE_DONE session_id=%s result=%s", session_id, res_close)
        except Exception as e:
          if logger:
            logger.info("RISK_CLOSE_INVOKE_FAIL session_id=%s err=%s", session_id, e)
    except Exception:
      pass
  # Risk: after cleaned reply, log item diffs (non-visible path)
  if agent_kind == "risk":
    try:
      ft_post2 = importlib.import_module('fhir_clini_assistant.fhir_tools')
      GetRiskChecklistTool_post2 = getattr(ft_post2, 'GetRiskChecklistTool', None)
      if GetRiskChecklistTool_post2 is not None:
        chk_post2 = await GetRiskChecklistTool_post2().run_async(args={"session_id": session_id}, tool_context=None)
        items_post2 = (chk_post2 or {}).get("items") or []
        updates2 = []
        for it in items_post2:
          name = str((it or {}).get("name") or "").lower()
          st = (it or {}).get("status")
          val = (it or {}).get("value")
          before = pre_items_map.get(name)
          if before and (before.get("status") != st or before.get("value") != val):
            updates2.append(f"{name}:{before.get('status')}=>{st}")
        if logger:
          if updates2:
            logger.info("RISK_MSG_UPDATES session_id=%s updated=%d items=%s", session_id, len(updates2), ", ".join(updates2)[:300])
          else:
            logger.info("RISK_MSG_NO_UPDATES session_id=%s", session_id)
        # Fallback: if no updates and still pending, try risk extractor once
        pending_now2 = [it.get("name") for it in items_post2 if (it.get("status") or "").lower() == "pending"]
        if (not updates2) and pending_now2:
          try:
            if logger:
              logger.info("RISK_MSG_FALLBACK_TRY session_id=%s pending=%s", session_id, ", ".join(pending_now2)[:200])
            from app.services.risk_checklist import llm_extract_risk as svc_llm_extract_risk
            await svc_llm_extract_risk(session_id, message)
            # Re-check snapshot and log
            chk_post3 = await GetRiskChecklistTool_post2().run_async(args={"session_id": session_id}, tool_context=None)
            items_post3 = (chk_post3 or {}).get("items") or []
            updates_fb2 = []
            for it in items_post3:
              name = str((it or {}).get("name") or "").lower()
              st = (it or {}).get("status")
              val = (it or {}).get("value")
              before = pre_items_map.get(name)
              if before and (before.get("status") != st or before.get("value") != val):
                updates_fb2.append(f"{name}:{before.get('status')}=>{st}")
            if logger:
              if updates_fb2:
                logger.info("RISK_MSG_FALLBACK_UPDATES session_id=%s updated=%d items=%s", session_id, len(updates_fb2), ", ".join(updates_fb2)[:300])
              else:
                logger.info("RISK_MSG_FALLBACK_NO_UPDATES session_id=%s", session_id)
          except Exception as e:
            if logger:
              logger.info("RISK_MSG_FALLBACK_ERR session_id=%s err=%s", session_id, e)
    except Exception:
      pass
  return {"reply": cleaned_reply or ""} 