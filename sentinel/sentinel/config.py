"""Configuration: provider settings and run defaults.

Precedence, highest first:
  1. explicit CLI flags
  2. environment variables (SENTINEL_*)
  3. the config file (~/.config/sentinel/config.json)
  4. built-in defaults

The config file never stores an API key. Keys come from the environment or a
credential helper, so the file is safe to commit and safe to screenshot.
"""

from __future__ import annotations

import dataclasses
import json
import os
import stat
from pathlib import Path
from typing import Any

from .providers import (AnthropicProvider, OfflineProvider, OllamaProvider,
                        OpenAICompatProvider, Provider, ProviderError,
                        PROVIDER_KINDS)

CONFIG_VERSION = 1


def config_dir() -> Path:
    return Path(os.environ.get("XDG_CONFIG_HOME", "~/.config")).expanduser() / "sentinel"


def config_path() -> Path:
    override = os.environ.get("SENTINEL_CONFIG")
    return Path(override).expanduser() if override else config_dir() / "config.json"


@dataclasses.dataclass
class Config:
    provider: str = "openai-compat"
    model: str = ""
    base_url: str = ""
    org: str = ""
    native_tools: bool = True
    temperature: float = 0.2
    max_tokens: int = 2048
    timeout: float = 120.0
    max_agent_steps: int = 8
    request_interval: float = 0.4
    scan_timeout: float = 15.0
    stream: bool = True
    source: str = ""
    api_key_env: str = "SENTINEL_API_KEY"

    # ------------------------------------------------------------- load/save

    @classmethod
    def load(cls, path: str | os.PathLike[str] | None = None) -> "Config":
        location = Path(path).expanduser() if path else config_path()
        config = cls()
        config.source = str(location)
        if location.exists():
            try:
                raw = json.loads(location.read_text(encoding="utf-8"))
            except json.JSONDecodeError as exc:
                raise ProviderError(f"{location} is not valid JSON: {exc}") from exc
            for field in dataclasses.fields(cls):
                if field.name in ("source",) or field.name not in raw:
                    continue
                value = raw[field.name]
                current = getattr(config, field.name)
                if isinstance(current, bool):
                    setattr(config, field.name, bool(value))
                elif isinstance(current, int) and not isinstance(current, bool):
                    setattr(config, field.name, int(value))
                elif isinstance(current, float):
                    setattr(config, field.name, float(value))
                else:
                    setattr(config, field.name, str(value))
        config.apply_env()
        return config

    def apply_env(self) -> None:
        env = os.environ
        if env.get("SENTINEL_PROVIDER"):
            self.provider = env["SENTINEL_PROVIDER"].strip().lower()
        if env.get("SENTINEL_MODEL"):
            self.model = env["SENTINEL_MODEL"].strip()
        if env.get("SENTINEL_BASE_URL"):
            self.base_url = env["SENTINEL_BASE_URL"].strip()
        elif env.get("OPENAI_BASE_URL"):
            self.base_url = env["OPENAI_BASE_URL"].strip()
        if env.get("SENTINEL_ORG"):
            self.org = env["SENTINEL_ORG"].strip()
        if env.get("SENTINEL_NO_NATIVE_TOOLS", "").lower() in ("1", "true", "yes"):
            self.native_tools = False
        if env.get("SENTINEL_TEMPERATURE"):
            try:
                self.temperature = float(env["SENTINEL_TEMPERATURE"])
            except ValueError:
                pass
        if env.get("SENTINEL_MAX_TOKENS"):
            try:
                self.max_tokens = int(env["SENTINEL_MAX_TOKENS"])
            except ValueError:
                pass
        if env.get("SENTINEL_MAX_STEPS"):
            try:
                self.max_agent_steps = max(1, int(env["SENTINEL_MAX_STEPS"]))
            except ValueError:
                pass
        if env.get("SENTINEL_NO_STREAM", "").lower() in ("1", "true", "yes"):
            self.stream = False

    def save(self, path: str | os.PathLike[str] | None = None) -> Path:
        location = Path(path).expanduser() if path else config_path()
        location.parent.mkdir(parents=True, exist_ok=True)
        payload = {field.name: getattr(self, field.name)
                   for field in dataclasses.fields(self)
                   if field.name not in ("source",)}
        payload["version"] = CONFIG_VERSION
        location.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        try:
            location.chmod(stat.S_IRUSR | stat.S_IWUSR)
        except OSError:
            pass
        return location

    # ------------------------------------------------------------- provider

    def api_key(self) -> str:
        return (os.environ.get(self.api_key_env)
                or os.environ.get("OPENAI_API_KEY")
                or os.environ.get("ANTHROPIC_API_KEY", "")).strip()

    def build_provider(self) -> Provider:
        kind = (self.provider or "openai-compat").strip().lower()
        if kind in ("offline", "none", "stub"):
            return OfflineProvider()
        if kind not in PROVIDER_KINDS:
            raise ProviderError(
                f"unknown provider {kind!r}; choose from {', '.join(PROVIDER_KINDS)}")
        if kind == "anthropic":
            if not self.model:
                raise ProviderError("a model id is required (SENTINEL_MODEL or "
                                    "`sentinel config set model ...`)")
            key = self.api_key()
            if not key:
                raise ProviderError(
                    "no Anthropic credential found. Export ANTHROPIC_API_KEY or "
                    "SENTINEL_API_KEY.")
            return AnthropicProvider(
                self.model, key,
                base_url=self.base_url or "https://api.anthropic.com",
                timeout=self.timeout)
        if kind == "ollama":
            return OllamaProvider(
                self.model or "llama3.1",
                base_url=self.base_url or "http://127.0.0.1:11434/v1",
                native_tools=self.native_tools, timeout=self.timeout)
        if not self.model:
            raise ProviderError(
                "no model configured. Either:\n"
                "  export SENTINEL_MODEL=<id>\n"
                "  sentinel config set model <id>\n"
                "  sentinel config use-offline        (run tools with no model)")
        base = self.base_url or "https://api.openai.com/v1"
        return OpenAICompatProvider(
            self.model, base_url=base, api_key=self.api_key(), org=self.org,
            native_tools=self.native_tools, timeout=self.timeout)

    def describe(self, redact: bool = True) -> dict[str, Any]:
        data: dict[str, Any] = {field.name: getattr(self, field.name)
                                for field in dataclasses.fields(self)}
        data["api_key_set"] = bool(self.api_key())
        if redact:
            data.pop("api_key_env", None)
        return data
