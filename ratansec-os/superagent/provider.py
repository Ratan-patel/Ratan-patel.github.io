"""Private AI provider transport (OpenAI-compatible chat completions).

The API key is read only from the server environment. Redirects are disabled,
responses are size-capped, and provider error bodies are never echoed back.
"""
from __future__ import annotations

import json
import re
import time
import urllib.error
import urllib.request
from typing import Any

from .settings import VERSION, settings, validate_base_url

MODEL_RE = re.compile(r"^[A-Za-z0-9._:\-/]{1,120}$")
MAX_RESPONSE_BYTES = 2_000_000


class ProviderError(RuntimeError):
    pass


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def _opener() -> urllib.request.OpenerDirector:
    # Ignore ambient HTTP(S)_PROXY so a local model stays local and a private
    # key is not forwarded through an unexpected proxy.
    return urllib.request.build_opener(urllib.request.ProxyHandler({}), _NoRedirect())


def headers() -> dict[str, str]:
    out = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "User-Agent": f"RatanSecSuperAgent/{VERSION}",
    }
    if settings.api_key:
        out["Authorization"] = f"Bearer {settings.api_key}"
    if settings.provider == "openrouter":
        out["HTTP-Referer"] = "https://ratan-patel.github.io/"
        out["X-Title"] = "RatanSec Super Agent"
    out.update(settings.header_map())
    return out


def redact(text: str) -> str:
    out = str(text or "")
    secrets = [settings.api_key, settings.app_password, settings.api_token, settings.mobile_token]
    for value in settings.header_map().values():
        if value:
            secrets.append(value)
    for secret in sorted({s for s in secrets if s and len(s) >= 4}, key=len, reverse=True):
        out = out.replace(secret, "[REDACTED]")
    out = re.sub(r"(?i)(bearer\s+)[A-Za-z0-9._~+\-/=]+", r"\1[REDACTED]", out)
    out = re.sub(r"(?i)((?:api[_-]?key|token|password|secret)\s*[=:]\s*)[^\s,;]+", r"\1[REDACTED]", out)
    return out


def status() -> dict[str, Any]:
    return {
        "configured": settings.ai_configured,
        "provider": settings.provider,
        "model": settings.model,
        "base_url": settings.base_url,
        "local": settings.local_provider,
        "key_source": settings.api_key_source,
        "key_required": not settings.local_provider,
        "max_steps": settings.max_steps,
        "model_override": settings.model_override,
        "demo": settings.demo_mode,
    }


def pick_model(requested: str | None) -> str:
    name = (requested or "").strip()
    if name and settings.model_override and MODEL_RE.fullmatch(name):
        return name
    return settings.model


def _content_text(message: dict[str, Any]) -> str:
    content = message.get("content")
    if isinstance(content, list):
        return "".join(str(p.get("text", "")) if isinstance(p, dict) else str(p) for p in content).strip()
    return ("" if content is None else str(content)).strip()


def chat(messages: list[dict[str, Any]], *, tools: list[dict] | None = None,
         model: str | None = None, temperature: float | None = None,
         max_tokens: int = 2000) -> dict[str, Any]:
    if settings.demo_mode:
        raise ProviderError("Offline demo mode: provider calls are disabled.")
    if not settings.ai_configured:
        raise ProviderError(
            "AI provider configured nahi hai. Server environment mein SUPERAGENT_API_KEY set karo; "
            "local Ollama/LM Studio ke liye SUPERAGENT_PROVIDER=ollama aur loopback base URL use karo."
        )
    base = validate_base_url(settings.base_url)
    payload: dict[str, Any] = {
        "model": pick_model(model),
        "messages": messages,
        "temperature": settings.temperature if temperature is None else temperature,
        "max_tokens": max(64, min(max_tokens, 4000)),
        "stream": False,
    }
    if tools:
        payload["tools"] = tools
        payload["tool_choice"] = "auto"
    request = urllib.request.Request(
        base + "/chat/completions", data=json.dumps(payload).encode("utf-8"),
        headers=headers(), method="POST",
    )
    try:
        with _opener().open(request, timeout=settings.ai_timeout) as response:
            raw = response.read(MAX_RESPONSE_BYTES + 1)
            if len(raw) > MAX_RESPONSE_BYTES:
                raise ProviderError("Provider response too large.")
            body = json.loads(raw.decode("utf-8", "replace"))
    except urllib.error.HTTPError as exc:
        friendly = {
            401: "Provider authentication failed (401). Check the server-side key.",
            402: "Provider credits exhausted (402).",
            403: "Provider access denied (403).",
            404: "Model/endpoint not found (404). Check SUPERAGENT_MODEL and SUPERAGENT_BASE_URL.",
            408: "Provider timed out (408).",
            429: "Provider rate limit (429). Retry shortly.",
        }.get(exc.code, f"Provider request failed ({exc.code}).")
        raise ProviderError(friendly) from None
    except urllib.error.URLError:
        raise ProviderError("Provider se connect nahi hua. Endpoint/network check karo; local model server chal raha hai?") from None
    except (json.JSONDecodeError, UnicodeDecodeError):
        raise ProviderError("Provider ne invalid JSON response diya.") from None
    except TimeoutError:
        raise ProviderError("Provider timeout.") from None
    if not isinstance(body, dict) or body.get("error"):
        raise ProviderError("Provider ne completion nahi di. Model/endpoint configuration check karo.")
    choices = body.get("choices") or []
    if not choices or not isinstance(choices[0], dict):
        raise ProviderError("Provider response mein choice nahi mili.")
    message = choices[0].get("message") or {}
    if not isinstance(message, dict):
        raise ProviderError("Provider response ka message invalid hai.")
    calls = message.get("tool_calls") or []
    if not isinstance(calls, list):
        calls = []
    return {
        "role": "assistant", "content": _content_text(message), "tool_calls": calls,
        "_model": str(body.get("model") or payload["model"]),
        "_usage": body.get("usage") if isinstance(body.get("usage"), dict) else {},
    }


def test_connection() -> dict[str, Any]:
    started = time.monotonic()
    result = chat([
        {"role": "system", "content": "Reply with exactly: READY"},
        {"role": "user", "content": "Connection test. No tools, no target data."},
    ], max_tokens=64, temperature=0)
    return {
        "ok": True, "model": result["_model"],
        "latency_ms": round((time.monotonic() - started) * 1000),
        "reply": result["content"][:80], "usage": result["_usage"],
    }
