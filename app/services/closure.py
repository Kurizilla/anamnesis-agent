from typing import Optional
import re, json
from app.config import VISIBLE_DELIM, JSON_DELIM, SANITIZE_TOKENS


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