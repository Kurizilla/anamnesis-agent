import os
from typing import Final

# Logging
LOGLEVEL: Final[str] = os.getenv("LOGLEVEL", "INFO")

# Deterministic close delimiters
VISIBLE_DELIM: Final[str] = os.getenv("VISIBLE_DELIM", "===VISIBLE_MARKDOWN===")
JSON_DELIM: Final[str] = os.getenv("JSON_DELIM", "===STRUCTURED_JSON===")

# Encounter close status
CLOSE_STATUS: Final[str] = os.getenv("ENCOUNTER_CLOSE_STATUS", "finished")  # HL7 v3 Encounter.status

# Feature flags
USE_LEGACY_EXEC: Final[bool] = os.getenv("USE_LEGACY_EXEC", "false").lower() == "true"
USE_FHIR_FALLBACK: Final[bool] = os.getenv("USE_FHIR_FALLBACK", "true").lower() != "false"

# FHIR protocol(s)
ANAMNESIS_PROTOCOL_URL: Final[str] = "http://goes.gob.sv/fhir/protocols/anamnesis-agent/anamnesis"

# Sanitization tokens to remove from visible text (defense-in-depth)
SANITIZE_TOKENS: Final[tuple[str, ...]] = (
  "print(",
  "default_api",
  "<execute_tool_code",
  "<tools.",
  "<create_clinical_impression",
  "<update_encounter_status",
) 