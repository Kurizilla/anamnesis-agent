#!/usr/bin/env bash
set -euo pipefail

export LOGLEVEL=${LOGLEVEL:-DEBUG}
python - <<'PY'
import logging, os
logging.basicConfig(level=getattr(logging, os.getenv("LOGLEVEL","INFO")), format="%(asctime)s %(levelname)s %(name)s: %(message)s")
from google.adk.cli.utils.agent_loader import AgentLoader
from google.adk.runners import InMemoryRunner
from google.genai import types
import asyncio

AGENTS_DIR = os.getenv("AGENTS_DIR", "/Users/gjkm9/github/goes/adk-python/contributing/samples")
AGENT_NAME = os.getenv("AGENT_NAME", "fhir_clini_assistant")

loader = AgentLoader(agents_dir=AGENTS_DIR)
agent = loader.load_agent(AGENT_NAME)
runner = InMemoryRunner(agent=agent, app_name="local_cli")

async def main():
  session = await runner.session_service.create_session(app_name="local_cli", user_id="local")
  print("Ready. Type messages. Ctrl-C to exit.")
  while True:
    try:
      msg = input("> ").strip()
    except EOFError:
      break
    if not msg:
      continue
    content = types.Content(role="user", parts=[types.Part.from_text(text=msg)])
    async for event in runner.run_async(user_id=session.user_id, session_id=session.id, new_message=content):
      if event.content and event.content.parts:
        text = "".join([p.text or "" for p in event.content.parts if p.text])
        if text:
          print(text)

asyncio.run(main())
PY 