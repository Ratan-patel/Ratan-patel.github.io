"""FastAPI app — Super Agent dashboard + mobile console.

Chalao:
    uvicorn superagent.webui:app --host 0.0.0.0 --port 8000
    python -m superagent.webui
"""

from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from . import audit, catalog, records
from .server import api
from .settings import APP_NAME, APP_TAGLINE, VERSION, settings

STATIC = Path(__file__).resolve().parent / "static"

logging.basicConfig(level=getattr(logging, settings.log_level.upper(), logging.INFO),
                    format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("superagent")


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings.ensure_dirs()
    audit.log("boot", version=VERSION, ai=settings.ai_configured, model=settings.model,
              auth=settings.auth_required, shell=settings.allow_shell,
              roe=len(records.records.active()), tools=catalog.TOTAL_TOOLS)
    if not settings.auth_required:
        log.warning("APP_PASSWORD / token set nahi — dashboard khula hai. Public deploy se pehle set karo!")
    if not settings.ai_configured:
        log.warning("SUPERAGENT_API_KEY set nahi hai — AI chat off rahega (manual terminal kaam karega).")
    if settings.allow_shell:
        log.warning("Shell mode ON hai — approval + blocklist active hai, phir bhi dhyan se.")
    log.info("%s %s ready | tools=%s | approvals=%s", APP_NAME, VERSION, catalog.TOTAL_TOOLS,
             settings.approval_mode)
    yield
    audit.log("shutdown", version=VERSION)


app = FastAPI(title=APP_NAME, description=APP_TAGLINE, version=VERSION,
              docs_url="/api/docs", openapi_url="/api/openapi.json", redoc_url=None, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=".*",
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

app.include_router(api)


@app.middleware("http")
async def headers(request: Request, call_next):
    response = await call_next(request)
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("Referrer-Policy", "no-referrer")
    response.headers.setdefault("X-Frame-Options", "SAMEORIGIN")
    response.headers.setdefault("Permissions-Policy", "geolocation=(), microphone=(), camera=()")
    return response


@app.exception_handler(Exception)
async def unhandled(request: Request, exc: Exception):  # pragma: no cover
    log.exception("Unhandled: %s", exc)
    return JSONResponse(status_code=500, content={"detail": f"Internal error: {exc}"})


@app.get("/", include_in_schema=False)
def index():
    return FileResponse(STATIC / "index.html")


@app.get("/mobile", include_in_schema=False)
def mobile():
    return FileResponse(STATIC / "mobile.html")


@app.get("/connect", include_in_schema=False)
def connect_page():
    """Android APK ka setup screen (server URL + token) — browser se bhi kaam karta hai."""
    return FileResponse(STATIC / "connect.html")


@app.get("/terminal", include_in_schema=False)
def terminal():
    return FileResponse(STATIC / "index.html")


@app.get("/manifest.webmanifest", include_in_schema=False)
def manifest():
    return FileResponse(STATIC / "manifest.webmanifest", media_type="application/manifest+json")


@app.get("/sw.js", include_in_schema=False)
def service_worker():
    return FileResponse(STATIC / "sw.js", media_type="application/javascript")


@app.get("/healthz", include_in_schema=False)
def healthz():
    return {"ok": True, "app": APP_NAME, "version": VERSION}


@app.get("/app-debug.apk", include_in_schema=False)
def apk_download():
    """Agar APK server ke paas rakhi hai (SUPERAGENT_APK_PATH) to seedha download."""
    from .settings import apk_path

    path = apk_path()
    if path is None:
        raise HTTPException(status_code=404, detail="APK yahan rakhi nahi hai — GitHub Actions artifacts/Releases se download karo.")
    return FileResponse(path, filename=path.name, media_type="application/vnd.android.package-archive")


if STATIC.is_dir():
    app.mount("/static", StaticFiles(directory=STATIC), name="static")


def run() -> None:  # pragma: no cover
    import uvicorn

    uvicorn.run("superagent.webui:app", host=settings.host, port=settings.port,
                log_level=settings.log_level, proxy_headers=True)


if __name__ == "__main__":  # pragma: no cover
    run()
