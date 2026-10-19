"""Natural Telugu / Hindi / Tamil... voices for phones that have none installed.
Provider is chosen by environment variables:
  GOOGLE_TTS_API_KEY                      -> Google Cloud Text-to-Speech (recommended, one simple call)
  BHASHINI_USER_ID + BHASHINI_API_KEY     -> Bhashini (government service; adapter written from public examples, test it)
Audio is cached on disk so each phrase is paid for once. Text is limited in length and calls are rate limited."""
import base64
import hashlib
import logging
import os
import time
from collections import defaultdict, deque
from pathlib import Path

import httpx
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import Response
from pydantic import BaseModel

router = APIRouter(prefix="/tts", tags=["tts"])
LANGS = {"en-IN", "hi-IN", "te-IN", "ta-IN", "kn-IN", "mr-IN", "gu-IN", "bn-IN"}
MAX_CHARS = 400
PER_MINUTE = 60
CACHE_DIR = Path(os.getenv("MEDIA_DIR", "./media")) / "tts"
_hits = defaultdict(deque)


def _provider():
    if os.getenv("GOOGLE_TTS_API_KEY"):
        return "google"
    if os.getenv("BHASHINI_USER_ID") and os.getenv("BHASHINI_API_KEY"):
        return "bhashini"
    return None


def _limit(request: Request):
    ip = request.headers.get("x-forwarded-for", "").split(",")[0].strip() or (request.client.host if request.client else "?")
    if len(_hits) > 5000:
        _hits.clear()
    q, now = _hits[ip], time.time()
    while q and now - q[0] > 60:
        q.popleft()
    if len(q) >= PER_MINUTE:
        raise HTTPException(429, "Too many requests, please wait a minute")
    q.append(now)


async def _google(text: str, lang: str, rate: float):
    url = "https://texttospeech.googleapis.com/v1/text:synthesize?key=" + os.getenv("GOOGLE_TTS_API_KEY", "")
    body = {"input": {"text": text}, "voice": {"languageCode": lang}, "audioConfig": {"audioEncoding": "MP3", "speakingRate": rate}}
    async with httpx.AsyncClient(timeout=20) as c:
        r = await c.post(url, json=body)
        r.raise_for_status()
        return base64.b64decode(r.json()["audioContent"]), "audio/mpeg"


async def _bhashini(text: str, lang: str, rate: float):
    code = lang.split("-")[0]
    pipeline = os.getenv("BHASHINI_PIPELINE_ID", "64392f96daac500b55c543cd")
    hdr = {"userID": os.getenv("BHASHINI_USER_ID", ""), "ulcaApiKey": os.getenv("BHASHINI_API_KEY", ""), "Content-Type": "application/json"}
    async with httpx.AsyncClient(timeout=25) as c:
        cfg = await c.post("https://meity-auth.ulcacontrib.org/ulca/apis/v0/model/getModelsPipeline", headers=hdr,
                           json={"pipelineTasks": [{"taskType": "tts", "config": {"language": {"sourceLanguage": code}}}], "pipelineRequestConfig": {"pipelineId": pipeline}})
        cfg.raise_for_status()
        j = cfg.json()
        ep = j["pipelineInferenceAPIEndPoint"]
        key = ep["inferenceApiKey"]
        service = j["pipelineResponseConfig"][0]["config"][0]["serviceId"]
        r = await c.post(ep["callbackUrl"], headers={key["name"]: key["value"], "Content-Type": "application/json"},
                         json={"pipelineTasks": [{"taskType": "tts", "config": {"language": {"sourceLanguage": code}, "serviceId": service, "gender": "female", "samplingRate": 8000}}],
                               "inputData": {"input": [{"source": text}]}})
        r.raise_for_status()
        return base64.b64decode(r.json()["pipelineResponse"][0]["audio"][0]["audioContent"]), "audio/wav"


async def _speak(text: str, lang: str, rate: float, request: Request) -> Response:
    text = (text or "").strip()
    if not text or len(text) > MAX_CHARS:
        raise HTTPException(400, f"Text must be 1 to {MAX_CHARS} characters")
    if lang not in LANGS:
        raise HTTPException(400, "Unsupported language")
    prov = _provider()
    if not prov:
        raise HTTPException(503, "No speech provider is set up on the server")
    _limit(request)
    rate = min(1.4, max(0.5, round(float(rate), 1)))
    key = hashlib.sha256(f"{prov}|{lang}|{rate}|{text}".encode()).hexdigest()
    audio_f, mime_f = CACHE_DIR / f"{key}.bin", CACHE_DIR / f"{key}.mime"
    if audio_f.exists():
        return Response(audio_f.read_bytes(), media_type=mime_f.read_text() if mime_f.exists() else "audio/mpeg")
    try:
        audio, mime = await (_google(text, lang, rate) if prov == "google" else _bhashini(text, lang, rate))
    except Exception:
        logging.exception("tts failed (%s, %s)", prov, lang)
        raise HTTPException(502, "Speech service failed")
    try:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        audio_f.write_bytes(audio)
        mime_f.write_text(mime)
    except OSError:
        pass
    return Response(audio, media_type=mime)


class TTSIn(BaseModel):
    text: str
    lang: str = "te-IN"
    rate: float = 0.9


@router.post("")
async def tts(body: TTSIn, request: Request):
    return await _speak(body.text, body.lang, body.rate, request)


@router.get("/say")   # quick test in a browser: /tts/say?text=నమస్కారం&lang=te-IN
async def say(request: Request, text: str = "నమస్కారం", lang: str = "te-IN", rate: float = 0.9):
    return await _speak(text, lang, rate, request)


@router.get("/status")
def status():
    return {"provider": _provider(), "languages": sorted(LANGS)}
