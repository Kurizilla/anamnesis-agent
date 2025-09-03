import re
from typing import Tuple

SANITIZE_DEFAULT_TOKENS: Tuple[str, ...] = (
  "print(",
  "default_api",
  "<execute_tool_code",
  "<tools.",
  "<create_clinical_impression",
  "<update_encounter_status",
)


def strip_tool_calls(text: str) -> str:
  if not text:
    return text
  removed_xml = 0
  removed_func = 0
  removed_yaml = 0
  removed_json = 0
  t = text
  t, n = re.subn(r"<\s*execute_tool_code\s*>[\s\S]*?<\s*/\s*execute_tool_code\s*>", "", t, flags=re.IGNORECASE)
  removed_xml += n
  t, n = re.subn(r"<\s*(?:tools\.)?(create_clinical_impression|update_encounter_status)\b[^>]*>[\s\S]*?<\s*/\s*\1\s*>", "", t, flags=re.IGNORECASE)
  removed_xml += n
  t, n = re.subn(r"<\s*(?:tools\.)?(create_clinical_impression|update_encounter_status)\b[^>]*/\s*>", "", t, flags=re.IGNORECASE)
  removed_xml += n
  lines = t.splitlines()
  out_lines = []
  i = 0
  while i < len(lines):
    ln = lines[i]
    m = re.match(r"\s*(?:tools\.)?(create_clinical_impression|update_encounter_status)\s*:\s*$", ln, flags=re.IGNORECASE)
    if m:
      removed_yaml += 1
      i += 1
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
  t, n = re.subn(r"\{[\s\S]*?\btool_code\b\s*:\s*\"(create_clinical_impression|update_encounter_status)\"[\s\S]*?\}", "", t, flags=re.IGNORECASE)
  removed_json += n
  t, n = re.subn(r"(?:tools\.)?(create_clinical_impression|update_encounter_status)\s*\([^\)]*\)", "", t, flags=re.IGNORECASE)
  removed_func += n
  t = re.sub(r"`\s*(?:tools\.)?(create_clinical_impression|update_encounter_status)\s*\([^`]*\)`", "", t, flags=re.IGNORECASE)
  t = re.sub(r"(^|\n)>?\s*``\s*(\n|$)", "\n", t)
  t = re.sub(r"\n{3,}", "\n\n", t)
  return t.strip()


def sanitize_visible_markdown(md: str, extra_tokens: Tuple[str, ...] = ()) -> str:
  if not md:
    return md
  t = str(md)
  # Strip fenced code blocks
  t = re.sub(r"```[\s\S]*?```", "", t)
  # Strip inline backticks
  t = re.sub(r"`[^`]*`", "", t)
  # Strip HTML/script/style tags
  t = re.sub(r"<script[\s\S]*?</script>", "", t, flags=re.IGNORECASE)
  t = re.sub(r"<style[\s\S]*?</style>", "", t, flags=re.IGNORECASE)
  t = re.sub(r"<[^>]+>", "", t)
  # Remove any known tokens
  for tok in (SANITIZE_DEFAULT_TOKENS + tuple(extra_tokens or ())):
    if not tok:
      continue
    t = t.replace(tok, "")
  # Collapse blank lines
  t = re.sub(r"\n{3,}", "\n\n", t)
  return t.strip() 