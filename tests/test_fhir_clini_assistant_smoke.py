import os
import asyncio
import pytest

from google.genai import types
from google.adk.runners import InMemoryRunner
from google.adk.cli.utils.agent_loader import AgentLoader


REPO_ROOT = "/Users/gjkm9/github/goes/adk-python"
AGENT_DIR = f"{REPO_ROOT}/contributing/samples"
AGENT_NAME = "fhir_clini_assistant"


def _env_ready() -> bool:
  # LLM via Vertex (or API KEY) and FHIR store envs
  llm_ok = (
      os.getenv("GOOGLE_API_KEY")
      or (
          os.getenv("GOOGLE_GENAI_USE_VERTEXAI") in ("1", "true", "TRUE")
          and os.getenv("GOOGLE_CLOUD_PROJECT")
          and (os.getenv("GOOGLE_CLOUD_LOCATION") or os.getenv("GOOGLE_CLOUD_REGION"))
      )
  )
  fhir_ok = (
      os.getenv("FHIR_PROJECT")
      and os.getenv("FHIR_LOCATION")
      and os.getenv("FHIR_DATASET")
      and os.getenv("FHIR_STORE")
  )
  return bool(llm_ok and fhir_ok)


@pytest.mark.skipif(not _env_ready(), reason="Missing required env for Vertex/API key or FHIR store")
@pytest.mark.asyncio
async def test_fhir_clini_assistant_smoke_prints_outputs(capfd):
  loader = AgentLoader(agents_dir=AGENT_DIR)
  agent = loader.load_agent(AGENT_NAME)
  runner = InMemoryRunner(agent=agent, app_name="fhir_clini_assistant_smoke")

  session = await runner.session_service.create_session(
      app_name="fhir_clini_assistant_smoke", user_id="smoke_user"
  )

  queries = [
      "la paciente d9774db8-c2ba-4386-85ca-440340a551e3 fuma?",
      "cuál es la fecha de nacimiento de 24fff615-f135-4a92-afc9-049e7467d277",
      "el paciente 40d087ed-462f-4f1e-bbb2-7e3e1c094a30 fue a la escuela?",
      "el paciente 40d087ed-462f-4f1e-bbb2-7e3e1c094a30 tiene diabetes??",
      "el paciente 40d087ed-462f-4f1e-bbb2-7e3e1c094a30 tiene antecedentes familiares?",
      "¿Qué condiciones clínicas recientes tiene el paciente 40d087ed-462f-4f1e-bbb2-7e3e1c094a30?",
      "Qué laboratorios tiene el paciente 24fff615-f135-4a92-afc9-049e7467d277?",
      "d9774db8-c2ba-4386-85ca-440340a551e3 tiene alergias?",
      "¿Qué medicamentos le han sido prescritos recientemente al paciente 634c5649-815d-48b8-9933-56c14a52a800?",
  ]

  for q in queries:
    content = types.Content(role="user", parts=[types.Part.from_text(text=q)])
    last_text = None
    async for event in runner.run_async(
        user_id=session.user_id,
        session_id=session.id,
        new_message=content,
    ):
      if event.content and event.content.parts:
        text = "".join([p.text or "" for p in event.content.parts if p.text])
        if text:
          last_text = text
    print(f"Q: {q}\nA: {last_text or '(sin respuesta de texto)'}\n")

  # Ensure at least one answer text was produced
  captured = capfd.readouterr()
  assert "A: " in captured.out 