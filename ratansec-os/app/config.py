"""RatanSec OS — central configuration.

Sab kuch environment variables se control hota hai. Local development ke liye
project root me `.env` file rakh sakte ho (dekho `.env.example`).
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

APP_NAME = "RatanSec OS"
APP_TAGLINE = "AI pentest environment — Kali tools + AI copilot"
VERSION = "1.0.0"

# Security ke liye: yeh hosts kabhi scan nahi honge (cloud metadata / SSRF abuse).
BLOCKED_HOSTS = {
    "169.254.169.254",          # AWS/GCP/Azure metadata
    "169.254.170.2",            # ECS task metadata
    "100.100.100.200",          # Alibaba metadata
    "metadata.google.internal",
    "metadata",
}
BLOCKED_NETWORKS = ("169.254.0.0/16",)  # link-local pura block

LOCAL_HOSTS = {"localhost", "127.0.0.1", "::1", "0.0.0.0", "host.docker.internal"}


def _load_dotenv() -> None:
    """Chhota .env loader (koi dependency nahi)."""
    here = Path(__file__).resolve().parent.parent
    for candidate in (Path.cwd() / ".env", here / ".env"):
        if not candidate.is_file():
            continue
        try:
            for line in candidate.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, _, value = line.partition("=")
                key = key.strip()
                value = value.strip().strip('"').strip("'")
                if key:
                    os.environ.setdefault(key, value)
        except OSError:
            pass
        break


_load_dotenv()


def _env(name: str, default: str = "") -> str:
    return os.environ.get(name, default).strip()


def _env_bool(name: str, default: bool = False) -> bool:
    raw = _env(name)
    if not raw:
        return default
    return raw.lower() in ("1", "true", "yes", "on", "y")


def _env_int(name: str, default: int) -> int:
    raw = _env(name)
    try:
        return int(raw) if raw else default
    except ValueError:
        return default


def _env_list(name: str) -> list[str]:
    raw = _env(name)
    return [item.strip().lower() for item in raw.split(",") if item.strip()]


@dataclass(frozen=True)
class Settings:
    # --- Auth -------------------------------------------------------------
    app_password: str = field(default_factory=lambda: _env("APP_PASSWORD"))

    # --- AI (OpenRouter, OpenAI-compatible) -------------------------------
    openrouter_api_key: str = field(default_factory=lambda: _env("OPENROUTER_API_KEY"))
    openrouter_base_url: str = field(
        default_factory=lambda: _env("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
    )
    model: str = field(default_factory=lambda: _env("MODEL", "openai/gpt-4o-mini"))
    model_override_allowed: bool = field(default_factory=lambda: _env_bool("MODEL_OVERRIDE_ALLOWED", True))
    ai_timeout: int = field(default_factory=lambda: _env_int("AI_TIMEOUT", 90))
    ai_max_steps: int = field(default_factory=lambda: _env_int("AI_MAX_STEPS", 4))
    openrouter_referer: str = field(default_factory=lambda: _env("OPENROUTER_REFERER", "https://github.com/Ratan-patel"))

    # --- Scope / safety ---------------------------------------------------
    allowed_targets: list[str] = field(default_factory=lambda: _env_list("ALLOWED_TARGETS"))
    allow_any_target: bool = field(default_factory=lambda: _env_bool("ALLOW_ANY_TARGET", True))
    allow_scope_override: bool = field(default_factory=lambda: _env_bool("ALLOW_SCOPE_OVERRIDE", False))
    allow_local_targets: bool = field(default_factory=lambda: _env_bool("ALLOW_LOCAL_TARGETS", True))
    approval_mode: str = field(default_factory=lambda: _env("APPROVAL_MODE", "").lower())  # "", auto, manual
    allow_install: bool = field(default_factory=lambda: _env_bool("ALLOW_INSTALL", False))

    # --- Limits -----------------------------------------------------------
    max_scan_seconds: int = field(default_factory=lambda: _env_int("MAX_SCAN_SECONDS", 420))
    max_output_chars: int = field(default_factory=lambda: _env_int("MAX_OUTPUT_CHARS", 60000))
    max_concurrent_scans: int = field(default_factory=lambda: _env_int("MAX_CONCURRENT_SCANS", 2))
    agent_step_timeout: int = field(default_factory=lambda: _env_int("AGENT_STEP_TIMEOUT", 45))

    # --- Misc -------------------------------------------------------------
    data_dir: Path = field(default_factory=lambda: Path(_env("DATA_DIR", "./data")).expanduser())
    log_level: str = field(default_factory=lambda: _env("LOG_LEVEL", "info").lower())

    # ------------------------------------------------------------------
    @property
    def effective_approval_mode(self) -> str:
        """Scope set hai -> auto allowed. Warna manual approval (UI se confirm)."""
        if self.approval_mode in ("auto", "manual"):
            return self.approval_mode
        return "auto" if self.allowed_targets else "manual"

    @property
    def secure(self) -> bool:
        """APP_PASSWORD set hai ya nahi (public deploy ke liye MUST)."""
        return bool(self.app_password)

    @property
    def ai_configured(self) -> bool:
        return bool(self.openrouter_api_key)

    @property
    def reports_dir(self) -> Path:
        return self.data_dir / "reports"

    def ensure_dirs(self) -> None:
        self.reports_dir.mkdir(parents=True, exist_ok=True)


settings = Settings()
settings.ensure_dirs()
