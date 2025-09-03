from typing import Optional, Tuple, List, Dict, Any
from datetime import datetime, timezone


async def prefetch(patient_id: str, agent_kind: str) -> Tuple[Optional[dict], Optional[dict], Optional[dict], Optional[dict]]:
  from fhir_clini_assistant.fhir_tools import (
    GetPatientByIdTool,
    GetMotivoConsultaTool,
    GetAreasAfectadasTool,
    ScoreRiesgoTool,
  )
  async def _safe(coro):
    try:
      return await coro
    except Exception:
      return None
  patient_task = _safe(GetPatientByIdTool().run_async(args={"patient_id": patient_id}, tool_context=None))
  motivos_task = _safe(GetMotivoConsultaTool().run_async(args={"patient": patient_id}, tool_context=None))
  areas_task = _safe(GetAreasAfectadasTool().run_async(args={"patient": patient_id}, tool_context=None))
  if (agent_kind or "").strip().lower() == "risk":
    score_task = _safe(ScoreRiesgoTool().run_async(args={"patient": patient_id}, tool_context=None))
    patient_res, motivos_res, areas_res, score_res = await __import__('asyncio').gather(patient_task, motivos_task, areas_task, score_task)
  else:
    patient_res, motivos_res, areas_res = await __import__('asyncio').gather(patient_task, motivos_task, areas_task)
    score_res = None
  return patient_res, motivos_res, areas_res, score_res


async def create_encounter(patient_id: str, session_id: str, purpose: Optional[str] = None) -> Optional[str]:
  from fhir_clini_assistant.fhir_tools import CreateEncounterTool
  enc_tool = CreateEncounterTool()
  args = {"patient_id": patient_id, "session_id": session_id}
  if purpose:
    args["purpose"] = purpose
  res = await enc_tool.run_async(args=args, tool_context=None)
  return (res or {}).get("encounter_id")


def build_context_lines(patient_res: Optional[dict], motivos_res: Optional[dict], areas_res: Optional[dict], score_res: Optional[dict] = None) -> List[str]:
  nombre = (patient_res or {}).get("nombre") if isinstance(patient_res, dict) else None
  motivos = (motivos_res or {}).get("motivos") if isinstance(motivos_res, dict) else None
  motivos_msg = (motivos_res or {}).get("mensaje") if isinstance(motivos_res, dict) else None
  areas = (areas_res or {}).get("areas") if isinstance(areas_res, dict) else None
  lines: List[str] = []
  if nombre: lines.append(f"Paciente: {nombre}")
  if motivos:
    lines.append("Motivos: " + ", ".join(motivos))
  elif motivos_msg:
    lines.append("[hint] No hay motivos de consulta registrados en el triage; pide el motivo principal al paciente.")
  if areas:
    lines.append("Áreas afectadas: " + ", ".join(areas))
  return lines


def build_kickoff_text(motivos_res: Optional[dict]) -> str:
  motivos = (motivos_res or {}).get("motivos") if isinstance(motivos_res, dict) else None
  if motivos:
    return "Iniciemos. Veo motivos registrados. No asumas diagnósticos; en pocas palabras, cuéntame qué te preocupa más ahora mismo."
  return "Iniciemos. No tengo motivos registrados en triage. ¿Cuál es tu motivo principal de consulta hoy?" 