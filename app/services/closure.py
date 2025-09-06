import logging
from typing import Optional
import re, json
from app.config import VISIBLE_DELIM, JSON_DELIM, SANITIZE_TOKENS


logger = logging.getLogger(__name__)


def parse_closing_blocks(text: str) -> tuple[Optional[str], Optional[dict]]:
  if not text:
    return None, None
  vm_match = re.search(rf"{re.escape(VISIBLE_DELIM)}\s*(.*?)\s*{re.escape(VISIBLE_DELIM)}", text, flags=re.DOTALL | re.IGNORECASE)
  sj_match = re.search(rf"{re.escape(JSON_DELIM)}\s*(.*?)\s*{re.escape(JSON_DELIM)}", text, flags=re.DOTALL | re.IGNORECASE)
  visible = vm_match.group(1).strip() if vm_match else None
  payload = None
  if sj_match:
    raw = sj_match.group(1).strip()
    raw = re.sub(r"^```[a-zA-Z]*", "", raw).strip()
    raw = re.sub(r"```$", "", raw).strip()
    try:
      payload = json.loads(raw)
    except Exception:
      payload = None
  return visible, payload


def sanitize_visible_markdown(md: str) -> str:
  if not md:
    return md
  out_lines = []
  in_py = False
  for ln in (md or "").splitlines():
    if re.match(r"^```\s*python\s*$", ln, flags=re.IGNORECASE):
      in_py = True
      continue
    if in_py:
      if re.match(r"^```\s*$", ln):
        in_py = False
      continue
    if any(tok in ln for tok in SANITIZE_TOKENS):
      continue
    out_lines.append(ln)
  out = "\n".join(out_lines)
  out = re.sub(r"\n{3,}", "\n\n", out).strip()
  return out 


async def try_risk_close(session_id: str, patient_id: Optional[str]) -> Optional[dict]:
  """If risk checklist has no pending items, create RiskAssessment and close Encounter.

  Logs:
    - RISK_CLOSE_CHECK pending=... answered=...
    - RISK_CLOSE_FAIL_SCORE / RISK_CLOSE_RA_OK / RISK_CLOSE_ENCOUNTER_OK / RISK_CLOSE_ENCOUNTER_FAIL / RISK_CLOSE_FAIL
    - RISK_CLOSE_BMI_PARSE_INPUT / RISK_CLOSE_BMI_PARSE_OK / RISK_CLOSE_BMI_PARSE_FAIL
    - RISK_CLOSE_ENC_RESOLVE_OK / RISK_CLOSE_ENC_RESOLVE_FAIL
    - RISK_CLOSE_IMC_POST_OK / RISK_CLOSE_IMC_POST_FAIL / RISK_CLOSE_IMC_POST_SKIP
    - RISK_CLOSE_QR_UPSERT_START / RISK_CLOSE_QR_UPSERT_OK / RISK_CLOSE_QR_UPSERT_SKIP / RISK_CLOSE_QR_UPSERT_FAIL
  """
  try:
    import importlib
    ft = importlib.import_module('fhir_clini_assistant.fhir_tools')
    snap_fn = getattr(ft, 'get_risk_checklist_snapshot', None)
    score_tool = getattr(ft, 'ScoreRiesgoTool')
    ra_tool = getattr(ft, 'CreateRiskAssessmentTool')
    up_enc_tool = getattr(ft, 'UpdateEncounterStatusTool', None)
    get_chk_tool = getattr(ft, 'GetRiskChecklistTool', None)
    imc_tool_cls = getattr(ft, 'CreateImcObservationTool', None)
    qr_upsert_cls = getattr(ft, 'UpsertPreventionQuestionnaireResponseTool', None)
    _new_session = getattr(ft, '_new_authorized_session', None)
    _base_url_fn = getattr(ft, '_build_fhir_store_base_url', None)
    if not callable(snap_fn) or score_tool is None or ra_tool is None:
      return None
    snap = snap_fn(session_id)
    counts = (snap or {}).get('counts') or {}
    pending = int(counts.get('pending') or 0)
    answered = int(counts.get('answered') or 0)
    logger.info("RISK_CLOSE_CHECK session_id=%s pending=%d answered=%d", session_id, pending, answered)
    if pending > 0 or not patient_id:
      return None

    # Compute latest risk outcome
    try:
      sc = score_tool()
      sr = await sc.run_async(args={"patient": patient_id}, tool_context=None)
      cat = ((sr or {}).get("riesgo_global") or {}).get("categoria") or "medio"
      rationale = "Resumen breve basado en variables recabadas."
    except Exception as e:
      logger.info("RISK_CLOSE_FAIL_SCORE session_id=%s err=%s", session_id, e)
      return None

    # Resolve Encounter by session for linking Observation
    encounter_id = None
    try:
      if callable(_new_session) and callable(_base_url_fn):
        s = _new_session()
        base = _base_url_fn()
        r = s.get(
          f"{base}/Encounter",
          params={"identifier": "http://goes.gob.sv/fhir/identifiers/session|" + session_id},
          headers={"Content-Type": "application/fhir+json;charset=utf-8"},
        )
        if getattr(r, 'status_code', None) == 200:
          entries = (r.json() or {}).get('entry', [])
          if entries:
            encounter_id = (((entries[0] or {}).get('resource', {}) or {}).get('id'))
      if encounter_id:
        logger.info("RISK_CLOSE_ENC_RESOLVE_OK session_id=%s encounter_id=%s", session_id, encounter_id)
      else:
        logger.info("RISK_CLOSE_ENC_RESOLVE_FAIL session_id=%s", session_id)
    except Exception as e:
      logger.info("RISK_CLOSE_ENC_RESOLVE_FAIL session_id=%s err=%s", session_id, e)

    # Try to compute BMI from checklist value, and extract cintura/fumar for QR upsert
    bmi_value = None
    cintura_val: Optional[int] = None
    fumar_val: Optional[bool] = None
    try:
      if get_chk_tool is not None:
        chk = await get_chk_tool().run_async(args={"session_id": session_id}, tool_context=None)
        items = (chk or {}).get("items") or []
        val_str = None
        for it in items:
          name = str((it or {}).get("name") or "").lower()
          if name == "altura_peso_para_imc":
            val_str = (it or {}).get("value")
          if name == "cintura_cm":
            try:
              v = (it or {}).get("value")
              if v is not None:
                vv = int(str(v).strip())
                cintura_val = vv
            except Exception:
              cintura_val = None
          if name == "fumar_actual":
            v2 = (it or {}).get("value")
            if isinstance(v2, str):
              fumar_val = True if v2.strip().lower() in ("si", "sí", "actual", "true") else (False if v2.strip().lower() in ("no", "false") else None)
            elif isinstance(v2, bool):
              fumar_val = v2
        logger.info("RISK_CLOSE_BMI_PARSE_INPUT session_id=%s value=%s", session_id, (val_str or ""))
        if val_str:
          t = str(val_str).lower()
          # parse height
          h_m = None
          m = re.search(r"(\d+[\.,]?\d*)\s*m(?!g)\b", t)
          if m:
            try:
              v = float(m.group(1).replace(',', '.'))
              if 0.5 < v < 2.5:
                h_m = v
            except Exception:
              h_m = None
          if h_m is None:
            m2 = re.search(r"(\d+)\s*cm\b", t)
            if m2:
              try:
                v2 = int(m2.group(1))
                if 50 < v2 < 260:
                  h_m = v2 / 100.0
              except Exception:
                pass
          # parse weight
          w_kg = None
          w1 = re.search(r"(\d+[\.,]?\d*)\s*kg\b", t)
          if w1:
            try:
              vv = float(w1.group(1).replace(',', '.'))
              if 20 < vv < 400:
                w_kg = vv
            except Exception:
              pass
          if w_kg is None:
            w2 = re.search(r"(\d+[\.,]?\d*)\s*(?:lb|lbs)\b", t)
            if w2:
              try:
                vv2 = float(w2.group(1).replace(',', '.'))
                if 40 < vv2 < 900:
                  w_kg = round(vv2 * 0.45359237, 2)
              except Exception:
                pass
          if h_m and w_kg:
            try:
              bmi_value = round(w_kg / (h_m * h_m), 2)
              logger.info("RISK_CLOSE_BMI_PARSE_OK session_id=%s bmi=%s h_m=%s w_kg=%s", session_id, bmi_value, h_m, w_kg)
            except Exception as e:
              logger.info("RISK_CLOSE_BMI_PARSE_FAIL session_id=%s err=%s", session_id, e)
          else:
            logger.info("RISK_CLOSE_BMI_PARSE_FAIL session_id=%s h_m=%s w_kg=%s", session_id, h_m, w_kg)
    except Exception as e:
      logger.info("RISK_CLOSE_BMI_PARSE_FAIL session_id=%s err=%s", session_id, e)

    # Create RA
    try:
      ra = ra_tool()
      args = {
        "patient_id": patient_id,
        "session_id": session_id,
        "outcome": {"bajo": "low", "medio": "medium", "alto": "high"}.get(str(cat), "medium"),
        "rationale": rationale,
      }
      res = await ra.run_async(args=args, tool_context=None)
      ra_id = (res or {}).get("risk_assessment_id")
      logger.info("RISK_CLOSE_RA_OK session_id=%s id=%s", session_id, ra_id)
    except Exception as e:
      logger.info("RISK_CLOSE_FAIL_RA session_id=%s err=%s", session_id, e)
      return None

    # Upsert QuestionnaireResponse 10009/10012
    try:
      if qr_upsert_cls is not None and (cintura_val is not None or fumar_val is not None):
        logger.info("RISK_CLOSE_QR_UPSERT_START session_id=%s cintura_cm=%s fuma_actual=%s", session_id, cintura_val, fumar_val)
        qr_tool = qr_upsert_cls()
        qr_args = {"patient_id": patient_id, "session_id": session_id}
        if encounter_id:
          qr_args["encounter_id"] = encounter_id
        if cintura_val is not None:
          qr_args["cintura_cm"] = int(cintura_val)
        if fumar_val is not None:
          qr_args["fuma_actual"] = bool(fumar_val)
        qr_res = await qr_tool.run_async(args=qr_args, tool_context=None)
        logger.info("RISK_CLOSE_QR_UPSERT_OK session_id=%s qr_id=%s", session_id, (qr_res or {}).get("questionnaire_response_id"))
      else:
        logger.info("RISK_CLOSE_QR_UPSERT_SKIP session_id=%s tool=%s cintura=%s fumar=%s", session_id, qr_upsert_cls is not None, cintura_val is not None, fumar_val is not None)
    except Exception as e:
      logger.info("RISK_CLOSE_QR_UPSERT_FAIL session_id=%s err=%s", session_id, e)

    # Post IMC Observation if bmi_value is available
    try:
      if bmi_value is not None and imc_tool_cls is not None:
        imc_tool = imc_tool_cls()
        args_imc = {
          "patient_id": patient_id,
          "value_bmi": float(bmi_value),
        }
        if encounter_id:
          args_imc["encounter_id"] = encounter_id
        imc_res = await imc_tool.run_async(args=args_imc, tool_context=None)
        logger.info("RISK_CLOSE_IMC_POST_OK session_id=%s obs_id=%s bmi=%s", session_id, (imc_res or {}).get("observation_id"), bmi_value)
      else:
        logger.info("RISK_CLOSE_IMC_POST_SKIP session_id=%s bmi_available=%s tool_available=%s", session_id, bmi_value is not None, imc_tool_cls is not None)
    except Exception as e:
      logger.info("RISK_CLOSE_IMC_POST_FAIL session_id=%s err=%s", session_id, e)

    # Close encounter
    try:
      if up_enc_tool is not None:
        up = up_enc_tool()
        await up.run_async(args={"session_id": session_id, "status": "finished"}, tool_context=None)
        logger.info("RISK_CLOSE_ENCOUNTER_OK session_id=%s", session_id)
    except Exception as e:
      logger.info("RISK_CLOSE_ENCOUNTER_FAIL session_id=%s err=%s", session_id, e)
    return {"risk_assessment_id": ra_id}
  except Exception as e:
    logger.info("RISK_CLOSE_FAIL session_id=%s err=%s", session_id, e)
    return None 