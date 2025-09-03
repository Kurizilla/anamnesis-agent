from typing import Optional, Dict, Any
from fhir_clini_assistant.fhir_tools import (
  CreateClinicalImpressionTool,
  UpdateEncounterStatusTool,
  _new_authorized_session,
  _build_fhir_store_base_url,
)


async def create_clinical_impression(args: Dict[str, Any]) -> Dict[str, Any]:
  tool = CreateClinicalImpressionTool()
  return await tool.run_async(args=args, tool_context=None)


async def update_encounter_status(args: Dict[str, Any]) -> Dict[str, Any]:
  tool = UpdateEncounterStatusTool()
  return await tool.run_async(args=args, tool_context=None)


def rest_finish_encounter(encounter_id: Optional[str], session_id: Optional[str], *, status: str) -> None:
  sess = _new_authorized_session()
  base = _build_fhir_store_base_url()
  eid = encounter_id
  if not eid and session_id:
    r = sess.get(
      f"{base}/Encounter",
      params={"identifier": "http://goes.gob.sv/fhir/identifiers/session|" + session_id},
      headers={"Content-Type": "application/fhir+json;charset=utf-8"},
    )
    r.raise_for_status()
    entries = (r.json() or {}).get("entry") or []
    if entries:
      eid = (entries[0].get("resource") or {}).get("id")
  if not eid:
    raise RuntimeError("encounter_id not resolved for rest_finish_encounter")
  get_r = sess.get(f"{base}/Encounter/{eid}", headers={"Content-Type": "application/fhir+json;charset=utf-8"})
  get_r.raise_for_status()
  res = get_r.json() or {}
  res["status"] = status
  from datetime import datetime, timezone
  now = datetime.now(timezone.utc).isoformat()
  per = res.get("period") or {}
  per["end"] = now
  res["period"] = per
  put_r = sess.put(f"{base}/Encounter/{eid}", headers={"Content-Type": "application/fhir+json;charset=utf-8"}, json=res)
  if put_r.status_code not in (200, 201):
    raise RuntimeError(f"put_failed status={put_r.status_code} body={(put_r.text or '')[:400]}") 