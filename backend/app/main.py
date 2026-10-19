import asyncio
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

from . import models  # noqa: F401
from .config import settings
from .db import Base, SessionLocal, engine
from .routers import auth, care, consent, family, health, life, platform, records, safety
from .services.alerts import process_expired
from .services.jobs import run_all

logging.basicConfig(level=logging.INFO)


async def _fast_loop():
    """Every 10 s: unanswered fall prompts escalate (must be quick)."""
    while True:
        await asyncio.sleep(10)
        with SessionLocal() as db:
            try:
                process_expired(db)
            except Exception:
                logging.exception("alert loop")


async def _slow_loop():
    """Every 5 min: stock alerts, visit reminders, call nudges, weekly digest."""
    while True:
        await asyncio.sleep(300)
        with SessionLocal() as db:
            try:
                run_all(db)
            except Exception:
                logging.exception("job loop")


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(engine)
    Path(settings.media_dir).mkdir(parents=True, exist_ok=True)
    tasks = [asyncio.create_task(_fast_loop()), asyncio.create_task(_slow_loop())]
    yield
    for t in tasks:
        t.cancel()


class SecurityHeaders(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        r = await call_next(request)
        r.headers.update({"X-Content-Type-Options": "nosniff", "X-Frame-Options": "DENY", "Referrer-Policy": "no-referrer",
                          "Cache-Control": "no-store", "Permissions-Policy": "geolocation=(self), microphone=(self), camera=(self)"})
        if not settings.debug:
            r.headers["Strict-Transport-Security"] = "max-age=63072000; includeSubDomains"
        return r


app = FastAPI(title="DocBuddy API", version="1.0.0", lifespan=lifespan)
app.add_middleware(SecurityHeaders)
app.add_middleware(GZipMiddleware, minimum_size=500)  # smaller responses for low-end phones / slow data
app.add_middleware(CORSMiddleware, allow_origins=settings.cors_origins.split(","), allow_methods=["*"], allow_headers=["*"])
for r in (auth, consent, health, safety, family, care, records, life, platform):
    app.include_router(r.router)


@app.get("/healthz")
def healthz():
    return {"ok": True}


from .services.registry import router as features_router  # noqa: E402

app.include_router(features_router)
# --- natural voices (text-to-speech) ---
from .routers import tts as tts_router  # noqa: E402

app.include_router(tts_router.router)
