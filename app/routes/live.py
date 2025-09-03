from fastapi import APIRouter
from fastapi.responses import JSONResponse
from google.auth import default as google_auth_default
from google.auth.transport.requests import AuthorizedSession
import os

router = APIRouter()


def _build_live_webrtc_urls() -> list[str]:
  project = os.getenv("GOOGLE_CLOUD_PROJECT") or os.getenv("PROJECT_ID")
  location = os.getenv("GOOGLE_CLOUD_LOCATION") or os.getenv("GOOGLE_CLOUD_REGION") or "us-central1"
  model = os.getenv("LIVE_MODEL", "gemini-live-2.5-flash-preview-native-audio")
  override = os.getenv("LIVE_WEBRTC_URL")
  if override:
    return [override]
  return [
    f"https://{location}-aiplatform.googleapis.com/v1/projects/{project}/locations/{location}:live:webrtc?model=publishers/google/models/{model}",
    f"https://{location}-aiplatform.googleapis.com/v1beta1/projects/{project}/locations/{location}:live:webrtc?model=publishers/google/models/{model}",
    f"https://{location}-aiplatform.googleapis.com/v1/projects/{project}/locations/{location}/live:webrtc?model=publishers/google/models/{model}",
    f"https://{location}-aiplatform.googleapis.com/v1beta1/projects/{project}/locations/{location}/live:webrtc?model=publishers/google/models/{model}",
  ]


@router.post("/live/webrtc/offer")
async def webrtc_offer(payload: dict):
  try:
    offer_type = (payload or {}).get("type") or "offer"
    offer_sdp = (payload or {}).get("sdp") or ""
    if not offer_sdp:
      return JSONResponse({"error": "missing sdp"}, status_code=400)
    urls = _build_live_webrtc_urls()
    creds, _ = google_auth_default()
    sess = AuthorizedSession(creds)
    # Try each URL: JSON first, then SDP fallback
    for url in urls:
      try:
        body = {"type": offer_type, "sdp": offer_sdp}
        headers = {"Content-Type": "application/json"}
        resp = sess.post(url, headers=headers, json=body)
        if resp.status_code == 200 and (resp.json() or {}).get("sdp"):
          ans = resp.json() or {}
          return JSONResponse({"type": ans.get("type", "answer"), "sdp": ans.get("sdp", "")})
      except Exception:
        pass
      sdp_url = url + ("&alt=sdp" if "?" in url else "?alt=sdp")
      headers_sdp = {"Content-Type": "application/sdp", "Accept": "application/sdp"}
      resp2 = sess.post(sdp_url, headers=headers_sdp, data=offer_sdp)
      if resp2.status_code == 200:
        answer_sdp = resp2.text or ""
        return JSONResponse({"type": "answer", "sdp": answer_sdp})
    return JSONResponse({"error": "live_api_error", "status": 404, "body": "All endpoint variants returned non-200"}, status_code=502)
  except Exception as e:
    return JSONResponse({"error": str(e)}, status_code=500) 