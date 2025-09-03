import logging
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

logger = logging.getLogger(__name__)

app = FastAPI(title="Clini Assistant API")
# Attach a shared logger for routers using app.logger
app.logger = logging.getLogger("app.main")
app.logger.info("API_READY")

# Allow Streamlit UI (8501) to call this backend
app.add_middleware(
  CORSMiddleware,
  allow_origins=[
    "http://localhost:8501",
    "http://127.0.0.1:8501",
  ],
  allow_credentials=True,
  allow_methods=["*"],
  allow_headers=["*"],
)

# Log 500s and exceptions centrally
@app.middleware("http")
async def _log_errors(request: Request, call_next):
  try:
    response = await call_next(request)
    if getattr(response, "status_code", 200) >= 500:
      app.logger.error("HTTP_5XX path=%s method=%s status=%s", request.url.path, request.method, getattr(response, "status_code", None))
    return response
  except Exception as e:
    try:
      body = await request.body()
      blen = len(body or b"")
    except Exception:
      blen = -1
    app.logger.exception("HTTP_EXCEPTION path=%s method=%s body_len=%s err=%s", request.url.path, request.method, blen, e)
    raise 