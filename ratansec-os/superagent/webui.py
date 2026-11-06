"""FastAPI app — RatanSec Super Agent v2 dashboard + responsive PWA."""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse
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
    settings.validate()
    settings.ensure_dirs()
    audit.log("boot", version=VERSION, ai=settings.ai_configured, model=settings.model,
              auth=settings.auth_required, demo=settings.demo_mode, roe=len(records.records.active()),
              tools=catalog.TOTAL_TOOLS)
    if settings.demo_mode:
        log.warning("OFFLINE DEMO MODE — fixture missions only; live actions/provider calls disabled.")
    elif not settings.ai_configured:
        log.warning("AI provider not configured — missions still work; chat/AI summaries need a server-side key or local model.")
    log.info("%s %s ready | exact-plan approval | default deny | raw shell disabled", APP_NAME, VERSION)
    yield
    audit.log("shutdown", version=VERSION)


app = FastAPI(title=APP_NAME, description=APP_TAGLINE, version=VERSION,
              docs_url="/api/docs", openapi_url="/api/openapi.json", redoc_url=None, lifespan=lifespan)
app.include_router(api)


@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
    response.headers["Cache-Control"] = "no-store"
    # The offline demo is embeddable in the Arena preview. Live mode is not.
    frame = "frame-ancestors *" if settings.demo_mode else "frame-ancestors 'self'"
    response.headers["Content-Security-Policy"] = (
        f"default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; "
        f"img-src 'self' data:; connect-src 'self'; object-src 'none'; base-uri 'self'; {frame}"
    )
    if not settings.demo_mode:
        response.headers["X-Frame-Options"] = "SAMEORIGIN"
    return response


@app.exception_handler(Exception)
async def unhandled(request: Request, exc: Exception):
    log.exception("Unhandled server error")
    return JSONResponse(status_code=500, content={"detail": "Internal server error. Check server logs."})


@app.get("/", include_in_schema=False)
def index():
    return FileResponse(STATIC / "index.html")


@app.get("/mobile", include_in_schema=False)
def mobile():
    return FileResponse(STATIC / "index.html")


@app.get("/connect", include_in_schema=False)
def connect_page():
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
    return {"ok": True, "app": APP_NAME, "version": VERSION, "demo": settings.demo_mode}


@app.get("/app-debug.apk", include_in_schema=False)
def apk_download():
    from .settings import apk_path
    path = apk_path()
    if path is None:
        raise HTTPException(status_code=404, detail="APK not present. Build it via GitHub Actions.")
    return FileResponse(path, filename=path.name, media_type="application/vnd.android.package-archive")


if STATIC.is_dir():
    app.mount("/static", StaticFiles(directory=STATIC), name="static")


def run() -> None:
    import uvicorn
    settings.validate()
    uvicorn.run("superagent.webui:app", host=settings.host, port=settings.port,
                log_level=settings.log_level, proxy_headers=settings.trusted_proxy)


if __name__ == "__main__":
    run()
