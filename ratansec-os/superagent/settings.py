"""RatanSec Super Agent v2 — server-side configuration.

Secrets only come from the process environment / a local `.env` file. They are
never accepted from the browser, returned by the API, or written to reports.
"""
from __future__ import annotations

import os
import re
import shlex
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import urlsplit

APP_NAME = "RatanSec Super Agent"
APP_TAGLINE = "Private-key AI security agent — bounded missions, human approval, evidence"
VERSION = "2.0.0"
HOME_DIR = Path(__file__).resolve().parent.parent


def _load_dotenv() -> None:
    for candidate in (Path.cwd() / ".env", HOME_DIR / ".env"):
        if not candidate.is_file():
            continue
        try:
            for line in candidate.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, _, value = line.partition("=")
                key = key.strip()
                if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", key):
                    os.environ.setdefault(key, value.strip().strip('"').strip("'"))
        except OSError:
            pass
        break


_load_dotenv()


def _env(name: str, default: str = "") -> str:
    return (os.environ.get(name) or default).strip()


def _env_bool(name: str, default: bool = False) -> bool:
    raw = _env(name).lower()
    return default if not raw else raw in ("1", "true", "yes", "on", "y")


def _env_int(name: str, default: int, low: int | None = None, high: int | None = None) -> int:
    try:
        value = int(_env(name) or default)
    except ValueError:
        value = default
    if low is not None:
        value = max(low, value)
    if high is not None:
        value = min(high, value)
    return value


def _env_list(name: str) -> list[str]:
    return [item.strip().lower() for item in _env(name).split(",") if item.strip()]


BLOCKED_NETWORKS = (
    "169.254.0.0/16", "0.0.0.0/8", "224.0.0.0/4", "240.0.0.0/4",
    "100.64.0.0/10", "192.0.0.0/24", "198.18.0.0/15", "::/128",
)
BLOCKED_HOSTS = {
    "169.254.169.254", "169.254.170.2", "100.100.100.200",
    "metadata.google.internal", "metadata", "metadata.azure.internal",
}
LOCAL_HOSTS = {"localhost", "127.0.0.1", "::1"}

# v2 does not expose a general-purpose shell. These legacy patterns are kept
# only so old imports/tests receive a clear rejection instead of execution.
SHELL_BLOCKLIST = (r".*",)


def _api_key() -> str:
    for name in ("SUPERAGENT_API_KEY", "OPENROUTER_API_KEY", "OPENAI_API_KEY",
                 "GROQ_API_KEY", "DEEPSEEK_API_KEY"):
        value = _env(name)
        if value:
            return value
    return ""


def _key_source() -> str:
    for name in ("SUPERAGENT_API_KEY", "OPENROUTER_API_KEY", "OPENAI_API_KEY",
                 "GROQ_API_KEY", "DEEPSEEK_API_KEY"):
        if _env(name):
            return name
    return ""


def is_local_url(url: str) -> bool:
    try:
        parts = urlsplit(url)
        return parts.scheme in {"http", "https"} and (parts.hostname or "").lower() in LOCAL_HOSTS
    except ValueError:
        return False


def validate_base_url(url: str) -> str:
    """HTTPS everywhere; plain HTTP only for a loopback model server."""
    value = (url or "").strip().rstrip("/")
    parts = urlsplit(value)
    if parts.scheme not in {"http", "https"} or not parts.hostname:
        raise ValueError("Provider base URL must be an http(s) URL.")
    if parts.username or parts.password or parts.query or parts.fragment:
        raise ValueError("Provider URL must not contain credentials, query strings or fragments.")
    if parts.scheme == "http" and not is_local_url(value):
        raise ValueError("Plain HTTP is allowed only for localhost/127.0.0.1/[::1] model servers.")
    if (parts.hostname or "").lower() in BLOCKED_HOSTS:
        raise ValueError("Cloud metadata endpoints are blocked.")
    return value


@dataclass(frozen=True)
class Settings:
    app_password: str = field(default_factory=lambda: _env("APP_PASSWORD"))
    api_token: str = field(default_factory=lambda: _env("SUPERAGENT_API_TOKEN"))
    mobile_token: str = field(default_factory=lambda: _env("SUPERAGENT_MOBILE_TOKEN"))

    provider: str = field(default_factory=lambda: _env("SUPERAGENT_PROVIDER", "openrouter").lower())
    api_key: str = field(default_factory=_api_key)
    api_key_source: str = field(default_factory=_key_source)
    base_url: str = field(default_factory=lambda: _env("SUPERAGENT_BASE_URL", "https://openrouter.ai/api/v1"))
    model: str = field(default_factory=lambda: _env("SUPERAGENT_MODEL", _env("MODEL", "openai/gpt-4o-mini")))
    model_override: bool = field(default_factory=lambda: _env_bool("SUPERAGENT_MODEL_OVERRIDE", False))
    temperature: float = field(default_factory=lambda: float(_env("SUPERAGENT_TEMPERATURE", "0.2") or 0.2))
    ai_timeout: int = field(default_factory=lambda: _env_int("SUPERAGENT_AI_TIMEOUT", 90, 5, 300))
    max_steps: int = field(default_factory=lambda: _env_int("SUPERAGENT_MAX_STEPS", 8, 1, 16))
    max_history: int = field(default_factory=lambda: _env_int("SUPERAGENT_MAX_HISTORY", 20, 2, 60))
    extra_headers: str = field(default_factory=lambda: _env("SUPERAGENT_EXTRA_HEADERS"))

    allowed_targets: list[str] = field(default_factory=lambda: _env_list("SUPERAGENT_ALLOWED_TARGETS"))
    allow_any_target: bool = field(default_factory=lambda: _env_bool("SUPERAGENT_ALLOW_ANY_TARGET", False))
    allow_private_ranges: bool = field(default_factory=lambda: _env_bool("SUPERAGENT_ALLOW_PRIVATE_RANGES", False))
    allow_internet: bool = field(default_factory=lambda: _env_bool("SUPERAGENT_ALLOW_INTERNET", True))
    require_roe: bool = field(default_factory=lambda: _env_bool("SUPERAGENT_REQUIRE_ROE", True))
    approval_mode: str = field(default_factory=lambda: _env("SUPERAGENT_APPROVAL_MODE", "manual").lower())

    # Retired in v2: kept as read-only compatibility flags so old deployments
    # cannot accidentally regain arbitrary shell/package-install execution.
    allow_shell: bool = False
    allow_install: bool = False
    max_cmd_seconds: int = field(default_factory=lambda: _env_int("SUPERAGENT_MAX_CMD_SECONDS", 120, 5, 300))
    max_output_chars: int = field(default_factory=lambda: _env_int("SUPERAGENT_MAX_OUTPUT_CHARS", 24000, 2000, 100000))
    max_concurrent: int = field(default_factory=lambda: _env_int("SUPERAGENT_MAX_CONCURRENT", 2, 1, 4))
    default_timeout: int = field(default_factory=lambda: _env_int("SUPERAGENT_DEFAULT_TIMEOUT", 30, 5, 120))
    mission_timeout: int = field(default_factory=lambda: _env_int("SUPERAGENT_MISSION_TIMEOUT", 180, 30, 600))
    approval_ttl: int = field(default_factory=lambda: _env_int("SUPERAGENT_APPROVAL_TTL", 600, 60, 1200))

    demo_mode: bool = field(default_factory=lambda: _env_bool("SUPERAGENT_DEMO_MODE", False))
    apk_file: str = field(default_factory=lambda: _env("SUPERAGENT_APK_PATH", ""))
    data_dir: Path = field(default_factory=lambda: Path(_env("SUPERAGENT_DATA_DIR", "./data/superagent")).expanduser())
    host: str = field(default_factory=lambda: _env("HOST", "127.0.0.1"))
    port: int = field(default_factory=lambda: _env_int("PORT", 8000, 1, 65535))
    log_level: str = field(default_factory=lambda: _env("LOG_LEVEL", "info").lower())
    trusted_proxy: bool = field(default_factory=lambda: _env_bool("SUPERAGENT_TRUSTED_PROXY", False))

    @property
    def local_provider(self) -> bool:
        return self.provider in {"ollama", "local", "lmstudio", "vllm"} or is_local_url(self.base_url)

    @property
    def ai_configured(self) -> bool:
        if self.demo_mode:
            return False
        try:
            validate_base_url(self.base_url)
        except ValueError:
            return False
        return bool(self.api_key) or self.local_provider

    @property
    def auth_required(self) -> bool:
        # Explicit offline demo may be public; every live deployment needs auth.
        return not self.demo_mode

    @property
    def roe_dir(self) -> Path:
        return self.data_dir / "roe"

    @property
    def runs_dir(self) -> Path:
        return self.data_dir / "runs"

    @property
    def reports_dir(self) -> Path:
        return self.data_dir / "reports"

    @property
    def evidence_dir(self) -> Path:
        return self.data_dir / "evidence"

    @property
    def missions_dir(self) -> Path:
        return self.data_dir / "missions"

    def ensure_dirs(self) -> None:
        for path in (self.data_dir, self.roe_dir, self.runs_dir, self.reports_dir,
                     self.evidence_dir, self.missions_dir):
            path.mkdir(parents=True, exist_ok=True, mode=0o700)

    def header_map(self) -> dict[str, str]:
        out: dict[str, str] = {}
        for chunk in self.extra_headers.split(","):
            if ":" in chunk:
                key, _, value = chunk.partition(":")
                key = key.strip()
                if key and re.fullmatch(r"[A-Za-z0-9-]{1,64}", key) and key.lower() not in {"host", "content-length"}:
                    out[key] = value.strip()
        return out

    def validate(self) -> None:
        if self.demo_mode:
            return
        if not self.app_password and not self.api_token and not self.mobile_token:
            raise RuntimeError(
                "Live mode requires APP_PASSWORD or SUPERAGENT_API_TOKEN. "
                "Set credentials, or use SUPERAGENT_DEMO_MODE=1 for the offline demo."
            )
        validate_base_url(self.base_url)
        if self.provider not in {"openrouter", "openai", "groq", "deepseek", "ollama", "local", "lmstudio", "vllm", "custom"}:
            raise RuntimeError("Unknown SUPERAGENT_PROVIDER.")


settings = Settings()
settings.ensure_dirs()


def apk_path() -> Path | None:
    candidates = [settings.apk_file] if settings.apk_file else []
    candidates += [str(HOME_DIR / "superagent" / "android" / "superagent.apk"), str(settings.data_dir / "superagent.apk")]
    for candidate in candidates:
        path = Path(candidate).expanduser()
        if path.is_file():
            return path
    return None


def effective_approval(session_approval: bool, intrusive: bool) -> bool:
    """v2: every live action is human-approved. The old auto switch is ignored."""
    return True


def quote(argv: list[str]) -> str:
    return " ".join(shlex.quote(str(a)) for a in argv)
