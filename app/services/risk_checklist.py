import os, json, logging, re
from typing import Optional, List, Tuple
from google import genai
from google.genai import types as genai_types

logger = logging.getLogger(__name__)


def _to_float(s: str) -> Optional[float]:
  try:
    return float(str(s).replace(',', '.'))
  except Exception:
    return None


def _extract_height_weight(text: str) -> Tuple[Optional[float], Optional[float]]:
  t = (text or "").lower()
  height_m = None
  weight_kg = None
  # Height patterns: 1.80 m, 1,80m, 180 cm
  m = re.search(r"(\d+[\.,]?\d*)\s*m(?!g)\b", t)
  if m:
    v = _to_float(m.group(1))
    if v and 0.5 < v < 2.5:
      height_m = v
  if height_m is None:
    m2 = re.search(r"(\d+)\s*cm\b", t)
    if m2:
      v2 = _to_float(m2.group(1))
      if v2 and 50 < v2 < 260:
        height_m = v2 / 100.0
  # Weight patterns: 80 kg, 175 lb/lbs
  w1 = re.search(r"(\d+[\.,]?\d*)\s*kg\b", t)
  if w1:
    wv = _to_float(w1.group(1))
    if wv and 20 < wv < 400:
      weight_kg = wv
  if weight_kg is None:
    w2 = re.search(r"(\d+[\.,]?\d*)\s*l(?:b|lbs)\b", t)
    if w2:
      wv2 = _to_float(w2.group(1))
      if wv2 and 40 < wv2 < 900:
        weight_kg = round(wv2 * 0.45359237, 2)
  return height_m, weight_kg


def _extract_cintura_cm(text: str) -> Optional[int]:
  t = (text or "").lower()
  m = re.search(r"(cintura[^\d]{0,12})?(\d{2,3})\s*cm\b", t)
  if m:
    try:
      v = int(m.group(2))
      if 40 <= v <= 200:
        return v
    except Exception:
      return None
  return None


def _extract_fumar_actual(text: str) -> Optional[str]:
  t = (text or "").lower()
  # Positive smoking
  if re.search(r"\b(fumo|fumar|fumo\s+un|fumo\s+mucho|fumando|soy\s+fumador|fumadora)\b", t):
    if not re.search(r"\b(no\s+fumo|no\s+soy\s+fumador|dej[eé] de fumar|ex\s*-?fumador|ex\s*-?fumadora)\b", t):
      return "actual"
  # Negative
  if re.search(r"\b(no\s+fumo|no\s+fuma|dej[eé] de fumar|ex\s*-?fumador|ex\s*-?fumadora)\b", t):
    return "no"
  return None


def _extract_antecedentes_familiares(text: str) -> Optional[str]:
  t = (text or "").lower()
  has_parent = re.search(r"\b(madre|padre|mama|mam[aá]|papa|pap[aá])\b", t)
  has_cond = re.search(r"\b(diabetes(\s+tipo\s*2)?|hta|hipertensi[oó]n)\b", t)
  neg = re.search(r"\b(ninguno|ninguna|no\s+tengo|sin)\b.*\b(antecedentes|familia|madre|padre|papa|mama|hipertensi[oó]n|diabetes)\b", t)
  if neg:
    return "no"
  if has_parent and has_cond:
    return "si"
  return None


def _extract_sexo(text: str) -> Optional[str]:
  t = (text or "").lower()
  if re.search(r"\b(mujer|femenin[oa])\b", t):
    return "mujer"
  if re.search(r"\b(hombre|masculin[oa])\b", t):
    return "hombre"
  return None


def _extract_edad(text: str) -> Optional[int]:
  t = (text or "").lower()
  m = re.search(r"\b(\d{1,3})\s*a[nñ]os\b", t)
  if m:
    try:
      v = int(m.group(1))
      if 0 < v < 120:
        return v
    except Exception:
      return None
  m2 = re.search(r"\btengo\s+(\d{1,3})\b", t)
  if m2:
    try:
      v2 = int(m2.group(1))
      if 0 < v2 < 120:
        return v2
    except Exception:
      return None
  return None


async def llm_extract_risk(session_id: str, user_text: str) -> None:
  """Extract risk factors from user text and update risk checklist (deterministic + LLM fallback).

  Logs:
    - RISK_EXTRACT_DET_START / RISK_EXTRACT_DET_APPLIED / RISK_EXTRACT_DET_SUMMARY / RISK_EXTRACT_DET_FAIL
    - RISK_EXTRACT_REQ / RISK_EXTRACT_MODEL / RISK_EXTRACT_RAW / RISK_EXTRACT_PARSE_FAIL / RISK_EXTRACT_APPLIED / RISK_EXTRACT_FAIL
  """
  if not (session_id and user_text and user_text.strip()):
    return
  try:
    from fhir_clini_assistant.fhir_tools import get_risk_checklist_snapshot, UpdateRiskItemTool
  except Exception as e:
    logger.debug("RISK_EXTRACT_IMPORT_FAIL: %s", e)
    return

  snap = get_risk_checklist_snapshot(session_id)
  if not (snap and snap.get("exists")):
    return
  pending_items: List[str] = [str(x).lower() for x in (snap.get("pending_items") or [])]
  if not pending_items:
    return

  tool = UpdateRiskItemTool()
  applied = 0
  applied_items: List[str] = []

  # Deterministic extraction
  logger.info("RISK_EXTRACT_DET_START session_id=%s pending=%d", session_id, len(pending_items))
  try:
    if "altura_peso_para_imc" in pending_items:
      h_m, w_kg = _extract_height_weight(user_text)
      if h_m and w_kg:
        try:
          bmi = round(w_kg / (h_m * h_m), 2)
        except Exception:
          bmi = None
        summary = f"altura={round(h_m*100)}cm peso={w_kg}kg" + (f" imc={bmi}" if bmi is not None else "")
        await tool.run_async(args={"session_id": session_id, "item": "altura_peso_para_imc", "status": "answered", "value": summary}, tool_context=None)
        applied += 1
        applied_items.append("altura_peso_para_imc")
        logger.info("RISK_EXTRACT_DET_APPLIED session_id=%s item=altura_peso_para_imc value=%s", session_id, summary)

    if "cintura_cm" in pending_items:
      v = _extract_cintura_cm(user_text)
      if v is not None:
        await tool.run_async(args={"session_id": session_id, "item": "cintura_cm", "status": "answered", "value": str(v)}, tool_context=None)
        applied += 1
        applied_items.append("cintura_cm")
        logger.info("RISK_EXTRACT_DET_APPLIED session_id=%s item=cintura_cm value=%s", session_id, v)

    if "fumar_actual" in pending_items:
      f = _extract_fumar_actual(user_text)
      if f is not None:
        await tool.run_async(args={"session_id": session_id, "item": "fumar_actual", "status": "answered", "value": f}, tool_context=None)
        applied += 1
        applied_items.append("fumar_actual")
        logger.info("RISK_EXTRACT_DET_APPLIED session_id=%s item=fumar_actual value=%s", session_id, f)

    if "antecedentes_familiares_dm2_hta" in pending_items:
      fam = _extract_antecedentes_familiares(user_text)
      if fam is not None:
        await tool.run_async(args={"session_id": session_id, "item": "antecedentes_familiares_dm2_hta", "status": "answered", "value": fam}, tool_context=None)
        applied += 1
        applied_items.append("antecedentes_familiares_dm2_hta")
        logger.info("RISK_EXTRACT_DET_APPLIED session_id=%s item=antecedentes_familiares_dm2_hta value=%s", session_id, fam)

    if "sexo" in pending_items:
      sx = _extract_sexo(user_text)
      if sx is not None:
        await tool.run_async(args={"session_id": session_id, "item": "sexo", "status": "answered", "value": sx}, tool_context=None)
        applied += 1
        applied_items.append("sexo")
        logger.info("RISK_EXTRACT_DET_APPLIED session_id=%s item=sexo value=%s", session_id, sx)

    if "edad" in pending_items:
      ed = _extract_edad(user_text)
      if ed is not None:
        await tool.run_async(args={"session_id": session_id, "item": "edad", "status": "answered", "value": str(ed)}, tool_context=None)
        applied += 1
        applied_items.append("edad")
        logger.info("RISK_EXTRACT_DET_APPLIED session_id=%s item=edad value=%s", session_id, ed)
  except Exception as e:
    logger.debug("RISK_EXTRACT_DET_FAIL: %s", e)

  if applied:
    logger.info("RISK_EXTRACT_DET_SUMMARY session_id=%s applied=%d items=%s", session_id, applied, ", ".join(applied_items))
    return

  # LLM fallback for remaining items
  try:
    client = genai.Client()
    model_id = os.getenv("RISK_EXTRACTOR_MODEL", os.getenv("RISK_AGENT_MODEL", "gemini-2.5-flash"))
    system = (
      "Eres un asistente clínico que extrae datos de factores de riesgo. "
      "Recibirás una lista de ítems de checklist y un texto del paciente. "
      "Devuelve SOLO JSON con los ítems que puedan marcarse como respondidos. "
      "Usa nombres exactos de ítems. No inventes datos. \n"
      "Ítems posibles: altura_peso_para_imc, cintura_cm, fumar_actual, antecedentes_familiares_dm2_hta, sexo, edad.\n"
    )
    prompt = {
      "checklist": pending_items,
      "texto_paciente": user_text,
      "output": {"items": [{"item": "<nombre exacto>", "value": "<resumen breve>", "confidence": 0.0}]}
    }
    logger.info("RISK_EXTRACT_REQ session_id=%s pending=%d text=%.120s", session_id, len(pending_items), (user_text or "")[:120])
    msg = genai_types.Content(role="user", parts=[genai_types.Part(text=system + "\n" + json.dumps(prompt, ensure_ascii=False))])
    resp = await client.aio.models.generate_content(model=model_id, contents=[msg])
    logger.info("RISK_EXTRACT_MODEL=%s", model_id)
    text = ""
    try:
      if resp and resp.candidates and resp.candidates[0].content and resp.candidates[0].content.parts:
        text = "".join([p.text or "" for p in resp.candidates[0].content.parts if getattr(p, "text", None)])
    except Exception:
      text = ""
    logger.info("RISK_EXTRACT_RAW session_id=%s len=%d text=%.200s", session_id, len(text or ""), (text or "")[:200])
    if not text:
      return
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
      logger.info("RISK_EXTRACT_PARSE_FAIL session_id=%s", session_id)
      return
    if isinstance(data, dict) and isinstance(data.get("items"), list):
      items_out = data.get("items")
    elif isinstance(data, list):
      items_out = data
    else:
      logger.info("RISK_EXTRACT_PARSE_EMPTY session_id=%s", session_id)
      return
    applied2 = 0
    applied_items2: List[str] = []
    for obj in items_out:
      try:
        item = (obj or {}).get("item") or (obj or {}).get("criterio")
        val = (obj or {}).get("value")
        conf = (obj or {}).get("confidence")
        if conf is not None:
          try:
            conf = float(conf)
          except Exception:
            conf = None
        if item and (val is not None) and (conf is None or conf >= float(os.getenv("RISK_EXTRACT_CONF_THRESH", "0.6"))):
          await tool.run_async(args={"session_id": session_id, "item": str(item), "status": "answered", "value": str(val)}, tool_context=None)
          applied2 += 1
          applied_items2.append(str(item))
      except Exception as e:
        logger.debug("RISK_EXTRACT_APPLY_FAIL item=%s err=%s", (obj or {}).get("item"), e)
    logger.info("RISK_EXTRACT_APPLIED session_id=%s matched=%d items=%s", session_id, applied2, ", ".join(applied_items2)[:200])
  except Exception as e:
    logger.debug("RISK_EXTRACT_FAIL: %s", e) 