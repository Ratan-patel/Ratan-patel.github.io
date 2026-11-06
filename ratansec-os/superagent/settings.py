"""Super Agent — configuration (sab kuch env vars se, `.env` bhi padhta hai).

Default tay-setting **safe** hai:
  * Koi target scope set nahi -> sirf lo aur batao, chalega kuch nahi.
  * Intrusive tools (hydra/metasploit/sqlmap...) hamesha human approval.
  * Raw shell/mode sirf jab `SUPERAGENT_ALLOW_SHELL=1` + per-session switch ON.
"""

from __future__ import annotations

import os
import shlex
from dataclasses import dataclass, field
from pathlib import Path

APP_NAME = "RatanSec Super Agent"
APP_TAGLINE = "Authorised AI security agent — terminal + mobile console"
VERSION = "1.0.0"

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
                if key:
                    os.environ.setdefault(key, value.strip().strip('"').strip("'"))
        except OSError:
            pass
        break


_load_dotenv()


def _env(name: str, default: str = "") -> str:
    return (os.environ.get(name) or default).strip()


def _env_bool(name: str, default: bool = False) -> bool:
    raw = _env(name).lower()
    if not raw:
        return default
    return raw in ("1", "true", "yes", "on", "y")


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


# Kabhi khud ko (ya cloud metadata ko) target nahi karna — even agar galti se
# scope me aa jaye. Yeh hard block hai, override nahi hota.
BLOCKED_NETWORKS = (
    "169.254.0.0/16",      # link-local + cloud metadata
    "0.0.0.0/8",
    "224.0.0.0/4",         # multicast
    "240.0.0.0/4",         # reserved
)
BLOCKED_HOSTS = {
    "169.254.169.254", "169.254.170.2", "100.100.100.200",
    "metadata.google.internal", "metadata",
}

# Shell mode me ye patterns hard-block (destructive commands kabhi nahi)
SHELL_BLOCKLIST = (
    r"\brm\s+-rf\s+/\s*$", r"\bmkfs(\.|\b)", r"\bdd\s+if=.*of=/dev/",
    r":\(\)\s*\{.*\};:", r"\bshutdown\b", r"\breboot\b", r"\bhalt\b",
    r"\bpoweroff\b", r">\s*/dev/sd", r"\bchmod\s+-R\s+777\s+/\s*$",
    r"\buserdel\s+root\b", r"\bpasswd\s+root\b", r"\bip\s+link\s+set\s+.*down\b",
    r"curl[^|]*\|\s*(ba)?sh", r"wget[^|]*\|\s*(ba)?sh",
)


@dataclass(frozen=True)
class Settings:
    # --- auth ---
    app_password: str = field(default_factory=lambda: _env("APP_PASSWORD"))
    api_token: str = field(default_factory=lambda: _env("SUPERAGENT_API_TOKEN"))
    mobile_token: str = field(default_factory=lambda: _env("SUPERAGENT_MOBILE_TOKEN"))

    # --- AI (user apni private API key deta hai) ---
    # Priority: apni key > OpenRouter > OpenAI > koi bhi OpenAI-compatible
    api_key: str = field(default_factory=lambda: (
        _env("SUPERAGENT_API_KEY") or _env("OPENROUTER_API_KEY") or _env("OPENAI_API_KEY")
        or _env("GEMINI_API_KEY") or _env("GROQ_API_KEY") or _env("DEEPSEEK_API_KEY")
    ))
    api_key_source: str = field(default_factory=lambda: (
        "SUPERAGENT_API_KEY" if _env("SUPERAGENT_API_KEY") else
        "OPENROUTER_API_KEY" if _env("OPENROUTER_API_KEY") else
        "OPENAI_API_KEY" if _env("OPENAI_API_KEY") else
        "GEMINI_API_KEY" if _env("GEMINI_API_KEY") else
        "GROQ_API_KEY" if _env("GROQ_API_KEY") else
        "DEEPSEEK_API_KEY" if _env("DEEPSEEK_API_KEY") else ""
    ))
    base_url: str = field(default_factory=lambda: _env("SUPERAGENT_BASE_URL", "https://openrouter.ai/api/v1"))
    model: str = field(default_factory=lambda: _env("SUPERAGENT_MODEL", _env("MODEL", "openai/gpt-4o-mini")))
    model_override: bool = field(default_factory=lambda: _env_bool("SUPERAGENT_MODEL_OVERRIDE", True))
    temperature: float = field(default_factory=lambda: float(_env("SUPERAGENT_TEMPERATURE", "0.2") or 0.2))
    ai_timeout: int = field(default_factory=lambda: _env_int("SUPERAGENT_AI_TIMEOUT", 120, 10, 600))
    max_steps: int = field(default_factory=lambda: _env_int("SUPERAGENT_MAX_STEPS", 8, 1, 24))
    max_history: int = field(default_factory=lambda: _env_int("SUPERAGENT_MAX_HISTORY", 20, 2, 100))
    extra_headers: str = field(default_factory=lambda: _env("SUPERAGENT_EXTRA_HEADERS"))  # "X-Key: v, Y: z"

    # --- scope / safety ---
    allowed_targets: list[str] = field(default_factory=lambda: _env_list("SUPERAGENT_ALLOWED_TARGETS"))
    allow_any_target: bool = field(default_factory=lambda: _env_bool("SUPERAGENT_ALLOW_ANY_TARGET", False))
    allow_private_ranges: bool = field(default_factory=lambda: _env_bool("SUPERAGENT_ALLOW_PRIVATE_RANGES", True))
    allow_internet: bool = field(default_factory=lambda: _env_bool("SUPERAGENT_ALLOW_INTERNET", True))
    require_roe: bool = field(default_factory=lambda: _env_bool("SUPERAGENT_REQUIRE_ROE", True))
    approval_mode: str = field(default_factory=lambda: _env("SUPERAGENT_APPROVAL_MODE", "manual").lower())

    # --- execution ---
    allow_shell: bool = field(default_factory=lambda: _env_bool("SUPERAGENT_ALLOW_SHELL", False))
    allow_install: bool = field(default_factory=lambda: _env_bool("SUPERAGENT_ALLOW_INSTALL", False))
    max_cmd_seconds: int = field(default_factory=lambda: _env_int("SUPERAGENT_MAX_CMD_SECONDS", 300, 5, 3600))
    max_output_chars: int = field(default_factory=lambda: _env_int("SUPERAGENT_MAX_OUTPUT_CHARS", 24000, 2000, 400000))
    max_concurrent: int = field(default_factory=lambda: _env_int("SUPERAGENT_MAX_CONCURRENT", 2, 1, 8))
    default_timeout: int = field(default_factory=lambda: _env_int("SUPERAGENT_DEFAULT_TIMEOUT", 120, 5, 3600))

    # --- APK hosting (optional) ---
    apk_file: str = field(default_factory=lambda: _env("SUPERAGENT_APK_PATH", ""))

    # --- storage / misc ---
    data_dir: Path = field(default_factory=lambda: Path(_env("SUPERAGENT_DATA_DIR", "./data/superagent")).expanduser())
    host: str = field(default_factory=lambda: _env("HOST", "0.0.0.0"))
    port: int = field(default_factory=lambda: _env_int("PORT", 8000, 1, 65535))
    log_level: str = field(default_factory=lambda: _env("LOG_LEVEL", "info").lower())

    # -- helpers -----------------------------------------------------------
    @property
    def ai_configured(self) -> bool:
        return bool(self.api_key)

    @property
    def auth_required(self) -> bool:
        return bool(self.app_password or self.api_token)

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

    def ensure_dirs(self) -> None:
        for path in (self.data_dir, self.roe_dir, self.runs_dir, self.reports_dir, self.evidence_dir):
            path.mkdir(parents=True, exist_ok=True)

    def header_map(self) -> dict[str, str]:
        out: dict[str, str] = {}
        for chunk in self.extra_headers.split(","):
            if ":" in chunk:
                key, _, value = chunk.partition(":")
                if key.strip():
                    out[key.strip()] = value.strip()
        return out


settings = Settings()
settings.ensure_dirs()


def apk_path() -> Path | None:
    """APK (agar server par rakhi hai) — /app-debug.apk se download ke liye."""
    candidates = [settings.apk_file] if settings.apk_file else []
    candidates += [str(HOME_DIR / "superagent" / "android" / "superagent.apk"), str(settings.data_dir / "superagent.apk")]
    for candidate in candidates:
        path = Path(candidate).expanduser()
        if path.is_file():
            return path
    return None


def effective_approval(session_approval: bool, intrusive: bool) -> bool:
    """Approval chahiye ya nahi?

    * intrusive tool -> HAMESHA approval (kabhi bypass nahi)
    * warna: session ka auto-approve switch, ya extra tools ke liye manual mode
    """
    if intrusive:
        return True
    if session_approval:
        return False
    return settings.approval_mode != "auto"


def quote(argv: list[str]) -> str:
    return " ".join(shlex.quote(str(a)) for a in argv)
