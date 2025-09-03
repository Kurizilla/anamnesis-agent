from typing import List, Optional
from app.services.checklist import get_snapshot


def build_user_parts_texts(session_id: str, agent_kind: str, message: str, effective_pid: Optional[str]) -> List[str]:
  parts: List[str] = []
  # Hidden session/patient info for tool calls
  parts.append(f"session_id={session_id}")
  if effective_pid:
    parts.append(f"patient_id={effective_pid}")
  parts.append(f"agent_kind={agent_kind}")
  # Snapshot checklist for anchoring (not shown to user)
  snap = get_snapshot(session_id)
  if snap and snap.get("exists"):
    counts = snap.get("counts") or {}
    area = snap.get("area") or ""
    pending_list = (snap.get("pending_items") or [])
    pending = ", ".join(pending_list[:4])
    anchor = f"[checklist_anchor] area={area} counts={counts} pending4=[{pending}]"
    parts.append(anchor)
  # User message at the end
  parts.append(message)
  return parts 