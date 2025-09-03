import os, json, logging
from typing import Optional
from google import genai
from google.genai import types as genai_types

logger = logging.getLogger(__name__)


def get_snapshot(session_id: str) -> Optional[dict]:
  try:
    from fhir_clini_assistant.fhir_tools import get_checklist_snapshot
  except Exception as e:
    logger.debug("CHECKLIST_SNAP_IMPORT_FAIL: %s", e)
    return None
  try:
    snap = get_checklist_snapshot(session_id)
    if snap and isinstance(snap, dict):
      try:
        area = snap.get("area")
        counts = snap.get("counts") or {}
        pending = snap.get("pending_items") or []
        answered = snap.get("answered_items") or []
        logger.info(
          "CHECKLIST_SNAPSHOT session_id=%s area=%s total=%s pending=%s answered=%s",
          session_id,
          area,
          counts.get("total"),
          len(pending),
          len(answered),
        )
        if pending:
          logger.debug("CHECKLIST_PENDING session_id=%s items=%s", session_id, ", ".join(pending)[:400])
        if answered:
          logger.debug("CHECKLIST_ANSWERED session_id=%s items=%s", session_id, ", ".join(answered)[:400])
      except Exception:
        pass
    return snap if (snap and isinstance(snap, dict)) else None
  except Exception as e:
    logger.debug("CHECKLIST_SNAP_FAIL: %s", e)
    return None


async def llm_extract_criterios(session_id: str, user_text: str) -> None:
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
    applied_items = []
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
          applied_items.append(str(crit))
      except Exception as e:
        logger.debug("CHECKLIST_EXTRACT_APPLY_FAIL criterio=%s err=%s", (obj or {}).get("criterio"), e)
    logger.info("CHECKLIST_EXTRACT_APPLIED session_id=%s area=%s matched=%d", session_id, area, applied)
    try:
      snap2 = get_snapshot(session_id)
      if snap2:
        pending2 = (snap2.get("pending_items") or [])
        answered2 = (snap2.get("answered_items") or [])
        logger.info("CHECKLIST_AFTER_APPLY session_id=%s pending=%d answered=%d applied_items=%s", session_id, len(pending2), len(answered2), ", ".join(applied_items)[:200])
    except Exception:
      pass
  except Exception as e:
    logger.debug("CHECKLIST_EXTRACT_FAIL: %s", e) 