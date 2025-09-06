from typing import List, Optional
from app.services.checklist import get_snapshot
import importlib


def build_user_parts_texts(session_id: str, agent_kind: str, message: str, effective_pid: Optional[str]) -> List[str]:
  parts: List[str] = []
  # Hidden session/patient info for tool calls
  parts.append(f"session_id={session_id}")
  if effective_pid:
    parts.append(f"patient_id={effective_pid}")
    parts.append(f"patient:{effective_pid}")
  parts.append(f"agent_kind={agent_kind}")
  # Snapshot checklist for anchoring (not shown to user)
  if (agent_kind or "").strip().lower() == "risk":
    try:
      ft = importlib.import_module('fhir_clini_assistant.fhir_tools')
      snap_fn = getattr(ft, 'get_risk_checklist_snapshot', None)
      snap = snap_fn(session_id) if callable(snap_fn) else None
    except Exception:
      snap = None
  else:
    snap = get_snapshot(session_id)
  if snap and snap.get("exists"):
    counts = snap.get("counts") or {}
    pending_list = (snap.get("pending_items") or [])
    answered_list = (snap.get("answered_items") or [])
    pending_all = ", ".join(pending_list)
    answered_all = ", ".join(answered_list)
    # Strict policy anchor: ask only pending items, never those answered
    anchor = f"[checklist_anchor] kind={agent_kind} counts={counts} pending=[{pending_all}] answered=[{answered_all}] policy=ask_only_pending_one_by_one"
    parts.append(anchor)
  # User message at the end
  parts.append(message)
  return parts 