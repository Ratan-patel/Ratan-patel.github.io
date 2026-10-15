"""Entry point — FastAPI app + dashboard static files + uvicorn runner.

Chalane ke liye:
    python -m app.webui          # ya
    uvicorn app.webui:app --host 0.0.0.0 --port 8000
"""

from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from . import audit
from .config import APP_NAME, APP_TAGLINE, VERSION, settings
from .server import api

STATIC_DIR = Path(__file__).resolve().parent / "static"

logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
log = logging.getLogger("ratansec")


@asynccontextmanager
async def lifespan(app: FastAPI):
    audit.log(
        "boot",
        version=VERSION,
        auth=settings.secure,
        ai=settings.ai_configured,
        model=settings.model,
        scope=settings.allowed_targets or ["(unset → manual approval)"],
        approval_mode=settings.effective_approval_mode,
    )
    if not settings.secure:
        log.warning("APP_PASSWORD set nahi hai — dashboard bina auth ke khula hai. Public deploy se pehle password lagao!")
    if not settings.ai_configured:
        log.warning("OPENROUTER_API_KEY set nahi hai — AI chat disabled rahega (tools kaam karenge).")
    log.info("%s %s ready | approval_mode=%s", APP_NAME, VERSION, settings.effective_approval_mode)
    yield
    audit.log("shutdown", version=VERSION)


app = FastAPI(
    title=APP_NAME,
    description=APP_TAGLINE,
    version=VERSION,
    docs_url="/api/docs",
    openapi_url="/api/openapi.json",
    redoc_url=None,
    lifespan=lifespan,
)

# CLI / external clients apni machine se call kar sakte hain.
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=".*",
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

app.include_router(api)


@app.middleware("http")
async def security_headers(request, call_next):
    response = await call_next(request)
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("Referrer-Policy", "no-referrer")
    return response


@app.exception_handler(Exception)
async def unhandled(request, exc):  # pragma: no cover - defensive
    log.exception("Unhandled error: %s", exc)
    return JSONResponse(status_code=500, content={"detail": f"Internal error: {exc}"})


@app.get("/", include_in_schema=False)
def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


if STATIC_DIR.is_dir():
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


def run() -> None:  # pragma: no cover
    import uvicorn

    host = os.environ.get("HOST", "0.0.0.0")
    port = int(os.environ.get("PORT", "8000"))
    uvicorn.run("app.webui:app", host=host, port=port, log_level=settings.log_level, proxy_headers=True)


if __name__ == "__main__":  # pragma: no cover
    run()
