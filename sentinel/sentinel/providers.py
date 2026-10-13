"""Model backends. Sentinel is model-agnostic: point it at anything.

Supported out of the box:
  * any OpenAI-compatible endpoint - OpenAI, Azure OpenAI, Groq, Together,
    OpenRouter, DeepInfra, Fireworks, Cerebras, vLLM, TGI, llama.cpp server,
    LM Studio, LiteLLM, Kong/NGINX AI gateway, or a private in-house proxy.
    You supply `base_url` + `api_key` + `model` and it works.
  * Anthropic Messages API
  * Ollama (local)
  * offline - deterministic stub used for tests and air-gapped demos

Everything is stdlib `urllib`, so the package installs and runs anywhere
Python 3.10+ does. Streaming is supported via SSE parsing.
"""

from __future__ import annotations

import dataclasses
import gzip
import json
import os
import time
import urllib.error
import urllib.request
from typing import Any, Callable, Iterable, Iterator, Sequence

DEFAULT_TIMEOUT = 120.0
DEFAULT_MAX_RETRIES = 3
USER_AGENT = "sentinel-agent/1.0 (+https://github.com/Ratan-patel/Ratan-patel.github.io)"


class ProviderError(Exception):
    """Transport or API-level failure."""


@dataclasses.dataclass
class Message:
    role: str            # system | user | assistant | tool
    content: str = ""
    tool_calls: list[dict[str, Any]] = dataclasses.field(default_factory=list)
    tool_call_id: str | None = None
    name: str | None = None

    def to_dict(self) -> dict[str, Any]:
        data: dict[str, Any] = {"role": self.role, "content": self.content}
        if self.tool_calls:
            data["tool_calls"] = self.tool_calls
        if self.tool_call_id:
            data["tool_call_id"] = self.tool_call_id
        if self.name:
            data["name"] = self.name
        return data


@dataclasses.dataclass
class ToolSpec:
    """A JSON-schema tool description handed to the model."""

    name: str
    description: str
    parameters: dict[str, Any]

    def to_openai(self) -> dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }

    def to_anthropic(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": self.parameters,
        }


@dataclasses.dataclass
class ToolCall:
    id: str
    name: str
    arguments: dict[str, Any]


@dataclasses.dataclass
class Completion:
    text: str = ""
    tool_calls: list[ToolCall] = dataclasses.field(default_factory=list)
    model: str = ""
    finish_reason: str = ""
    usage: dict[str, int] = dataclasses.field(default_factory=dict)
    raw: dict[str, Any] = dataclasses.field(default_factory=dict)
    latency_ms: int = 0


class Provider:
    """Common interface for every backend."""

    name = "provider"
    supports_native_tools = False

    def __init__(self, model: str, timeout: float = DEFAULT_TIMEOUT,
                 max_retries: int = DEFAULT_MAX_RETRIES,
                 extra_headers: dict[str, str] | None = None) -> None:
        self.model = model
        self.timeout = timeout
        self.max_retries = max_retries
        self.extra_headers = extra_headers or {}

    # -- public API ---------------------------------------------------------

    def complete(self, messages: Sequence[Message],
                 tools: Sequence[ToolSpec] | None = None,
                 temperature: float = 0.2,
                 max_tokens: int = 2048) -> Completion:
        raise NotImplementedError

    def stream(self, messages: Sequence[Message],
               tools: Sequence[ToolSpec] | None = None,
               temperature: float = 0.2,
               max_tokens: int = 2048,
               on_token: Callable[[str], None] | None = None) -> Completion:
        """Default: non-streaming, then replay. Subclasses may override."""
        completion = self.complete(messages, tools, temperature, max_tokens)
        if on_token and completion.text:
            on_token(completion.text)
        return completion

    def probe(self) -> str:
        """Cheap liveness check used by `sentinel doctor`."""
        started = time.monotonic()
        completion = self.complete(
            [Message("user", "Reply with exactly: PONG")],
            temperature=0.0, max_tokens=16,
        )
        elapsed = int((time.monotonic() - started) * 1000)
        reply = (completion.text or "").strip().splitlines()[0][:40] if completion.text else ""
        return f"{self.name}:{self.model} ok in {elapsed}ms -> {reply!r}"

    # -- shared HTTP --------------------------------------------------------

    def _request(self, url: str, payload: dict[str, Any],
                 headers: dict[str, str]) -> dict[str, Any]:
        body = json.dumps(payload).encode("utf-8")
        all_headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Accept-Encoding": "gzip",
            "User-Agent": USER_AGENT,
            **headers,
            **self.extra_headers,
        }
        last_error: Exception | None = None
        for attempt in range(1, self.max_retries + 1):
            request = urllib.request.Request(url, data=body, headers=all_headers, method="POST")
            try:
                with urllib.request.urlopen(request, timeout=self.timeout) as response:
                    raw = response.read()
                    if response.headers.get("Content-Encoding") == "gzip":
                        raw = gzip.decompress(raw)
                    return json.loads(raw.decode("utf-8"))
            except urllib.error.HTTPError as exc:
                detail = exc.read().decode("utf-8", "replace")[:600]
                if exc.code in (429, 500, 502, 503, 504) and attempt < self.max_retries:
                    last_error = ProviderError(f"HTTP {exc.code}: {detail}")
                    time.sleep(min(2 ** attempt, 8))
                    continue
                raise ProviderError(f"HTTP {exc.code} from {url}: {detail}") from exc
            except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
                last_error = ProviderError(f"{type(exc).__name__}: {exc}")
                if attempt < self.max_retries:
                    time.sleep(min(2 ** attempt, 8))
                    continue
                raise ProviderError(
                    f"could not reach {url} after {attempt} attempts: {exc}"
                ) from exc
        raise ProviderError(str(last_error))

    def _stream_request(self, url: str, payload: dict[str, Any],
                        headers: dict[str, str]) -> Iterator[str]:
        body = json.dumps(payload).encode("utf-8")
        all_headers = {
            "Content-Type": "application/json",
            "Accept": "text/event-stream",
            "Accept-Encoding": "gzip",
            "User-Agent": USER_AGENT,
            **headers,
            **self.extra_headers,
        }
        request = urllib.request.Request(url, data=body, headers=all_headers, method="POST")
        try:
            response = urllib.request.urlopen(request, timeout=self.timeout)
        except urllib.error.HTTPError as exc:
            raise ProviderError(
                f"HTTP {exc.code} from {url}: {exc.read().decode('utf-8', 'replace')[:600]}"
            ) from exc
        except urllib.error.URLError as exc:
            raise ProviderError(f"could not reach {url}: {exc}") from exc

        with response:
            stream: Iterable[bytes]
            if response.headers.get("Content-Encoding") == "gzip":
                stream = gzip.GzipFile(fileobj=response)
            else:
                stream = response
            buffer = b""
            for chunk in stream:
                buffer += chunk
                while b"\n" in buffer:
                    line, buffer = buffer.split(b"\n", 1)
                    yield line.decode("utf-8", "replace").rstrip("\r")


# ---------------------------------------------------------------------------


class OpenAICompatProvider(Provider):
    """Any endpoint speaking the OpenAI Chat Completions protocol.

    This is the one to use for a private/self-hosted API: set `base_url` to your
    gateway and `api_key` to whatever it expects (some accept any non-empty
    string, so `SENTINEL_API_KEY=dummy` is fine for an unauthenticated LAN box).
    """

    name = "openai-compat"
    supports_native_tools = True

    def __init__(self, model: str, base_url: str, api_key: str = "",
                 org: str = "", native_tools: bool = True, **kwargs: Any) -> None:
        super().__init__(model, **kwargs)
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.org = org
        # Some small/local models advertise tool support and then emit garbage.
        # `native_tools=False` forces the portable text protocol in agent.py.
        self.supports_native_tools = native_tools

    @property
    def endpoint(self) -> str:
        base = self.base_url
        if base.endswith("/chat/completions"):
            return base
        if base.endswith("/v1"):
            return base + "/chat/completions"
        return base + "/v1/chat/completions"

    def _headers(self) -> dict[str, str]:
        headers: dict[str, str] = {}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        if self.org:
            headers["OpenAI-Organization"] = self.org
        return headers

    def _payload(self, messages: Sequence[Message], tools: Sequence[ToolSpec] | None,
                 temperature: float, max_tokens: int, stream: bool) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": [m.to_dict() for m in messages],
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": stream,
        }
        if tools and self.supports_native_tools:
            payload["tools"] = [t.to_openai() for t in tools]
            payload["tool_choice"] = "auto"
        return payload

    def complete(self, messages: Sequence[Message],
                 tools: Sequence[ToolSpec] | None = None,
                 temperature: float = 0.2,
                 max_tokens: int = 2048) -> Completion:
        started = time.monotonic()
        data = self._request(
            self.endpoint,
            self._payload(messages, tools, temperature, max_tokens, stream=False),
            self._headers(),
        )
        choices = data.get("choices") or []
        if not choices:
            raise ProviderError(f"empty choices in response: {json.dumps(data)[:400]}")
        message = choices[0].get("message") or {}
        calls: list[ToolCall] = []
        for raw_call in message.get("tool_calls") or []:
            function = raw_call.get("function") or {}
            calls.append(ToolCall(
                id=str(raw_call.get("id") or f"call_{len(calls)}"),
                name=str(function.get("name") or ""),
                arguments=_loose_json(function.get("arguments")),
            ))
        return Completion(
            text=message.get("content") or "",
            tool_calls=calls,
            model=str(data.get("model") or self.model),
            finish_reason=str(choices[0].get("finish_reason") or ""),
            usage=data.get("usage") or {},
            raw=data,
            latency_ms=int((time.monotonic() - started) * 1000),
        )

    def stream(self, messages: Sequence[Message],
               tools: Sequence[ToolSpec] | None = None,
               temperature: float = 0.2,
               max_tokens: int = 2048,
               on_token: Callable[[str], None] | None = None) -> Completion:
        started = time.monotonic()
        text_parts: list[str] = []
        # tool-call deltas arrive split across chunks, keyed by index
        call_buffer: dict[int, dict[str, Any]] = {}
        finish = ""
        model = self.model
        for line in self._stream_request(
            self.endpoint,
            self._payload(messages, tools, temperature, max_tokens, stream=True),
            self._headers(),
        ):
            if not line.startswith("data:"):
                continue
            data = line[5:].strip()
            if data == "[DONE]":
                break
            try:
                event = json.loads(data)
            except json.JSONDecodeError:
                continue
            model = str(event.get("model") or model)
            for choice in event.get("choices") or []:
                delta = choice.get("delta") or {}
                piece = delta.get("content")
                if piece:
                    text_parts.append(piece)
                    if on_token:
                        on_token(piece)
                if choice.get("finish_reason"):
                    finish = str(choice["finish_reason"])
                for raw_call in delta.get("tool_calls") or []:
                    index = int(raw_call.get("index") or 0)
                    slot = call_buffer.setdefault(index, {"id": "", "name": "", "args": ""})
                    if raw_call.get("id"):
                        slot["id"] = str(raw_call["id"])
                    function = raw_call.get("function") or {}
                    if function.get("name"):
                        slot["name"] += str(function["name"])
                    if function.get("arguments"):
                        slot["args"] += str(function["arguments"])
        calls = [
            ToolCall(id=slot["id"] or f"call_{index}", name=slot["name"],
                     arguments=_loose_json(slot["args"]))
            for index, slot in sorted(call_buffer.items())
            if slot["name"]
        ]
        return Completion(
            text="".join(text_parts), tool_calls=calls, model=model,
            finish_reason=finish, latency_ms=int((time.monotonic() - started) * 1000),
        )


class AnthropicProvider(Provider):
    name = "anthropic"
    supports_native_tools = True

    def __init__(self, model: str, api_key: str, base_url: str = "https://api.anthropic.com",
                 version: str = "2023-06-01", **kwargs: Any) -> None:
        super().__init__(model, **kwargs)
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.version = version

    def _headers(self) -> dict[str, str]:
        return {"x-api-key": self.api_key, "anthropic-version": self.version}

    def complete(self, messages: Sequence[Message],
                 tools: Sequence[ToolSpec] | None = None,
                 temperature: float = 0.2,
                 max_tokens: int = 2048) -> Completion:
        system_parts = [m.content for m in messages if m.role == "system" and m.content]
        turns: list[dict[str, Any]] = []
        for message in messages:
            if message.role == "system":
                continue
            if message.role == "tool":
                turns.append({
                    "role": "user",
                    "content": [{
                        "type": "tool_result",
                        "tool_use_id": message.tool_call_id or "",
                        "content": message.content,
                    }],
                })
                continue
            blocks: list[dict[str, Any]] = []
            if message.content:
                blocks.append({"type": "text", "text": message.content})
            for call in message.tool_calls:
                blocks.append({
                    "type": "tool_use", "id": call.id,
                    "name": call.name, "input": call.arguments,
                })
            role = "assistant" if message.role == "assistant" else "user"
            turns.append({"role": role, "content": blocks or [{"type": "text", "text": ""}]})

        payload: dict[str, Any] = {
            "model": self.model, "max_tokens": max_tokens,
            "temperature": temperature, "messages": turns,
        }
        if system_parts:
            payload["system"] = "\n\n".join(system_parts)
        if tools:
            payload["tools"] = [t.to_anthropic() for t in tools]

        started = time.monotonic()
        data = self._request(self.base_url + "/v1/messages", payload, self._headers())
        text_parts: list[str] = []
        calls: list[ToolCall] = []
        for block in data.get("content") or []:
            if block.get("type") == "text":
                text_parts.append(block.get("text") or "")
            elif block.get("type") == "tool_use":
                calls.append(ToolCall(
                    id=str(block.get("id") or f"call_{len(calls)}"),
                    name=str(block.get("name") or ""),
                    arguments=block.get("input") or {},
                ))
        return Completion(
            text="".join(text_parts), tool_calls=calls,
            model=str(data.get("model") or self.model),
            finish_reason=str(data.get("stop_reason") or ""),
            usage=data.get("usage") or {}, raw=data,
            latency_ms=int((time.monotonic() - started) * 1000),
        )


class OllamaProvider(OpenAICompatProvider):
    """Local models via Ollama's OpenAI-compatible surface."""

    name = "ollama"

    def __init__(self, model: str, base_url: str = "http://127.0.0.1:11434/v1",
                 api_key: str = "ollama", **kwargs: Any) -> None:
        super().__init__(model, base_url=base_url, api_key=api_key, **kwargs)


class OfflineProvider(Provider):
    """Deterministic stub. No network, no key, no model download.

    Used by the test-suite and by `sentinel scan` when you only want the
    deterministic audit tools and no LLM narration.
    """

    name = "offline"
    supports_native_tools = False

    def __init__(self, model: str = "offline", script: Sequence[str] | None = None,
                 **kwargs: Any) -> None:
        super().__init__(model, **kwargs)
        self.script = list(script) if script else []
        self.calls = 0

    def complete(self, messages: Sequence[Message],
                 tools: Sequence[ToolSpec] | None = None,
                 temperature: float = 0.2,
                 max_tokens: int = 2048) -> Completion:
        self.calls += 1
        if self.script:
            text = self.script[min(self.calls - 1, len(self.script) - 1)]
        else:
            last_user = next(
                (m.content for m in reversed(messages) if m.role == "user"), ""
            )
            text = (
                "[offline provider] no model configured. Deterministic tool results "
                f"above are authoritative. (prompt was {len(last_user)} chars)"
            )
        return Completion(text=text, model=self.model, finish_reason="stop",
                          usage={"prompt_tokens": 0, "completion_tokens": 0})


# ---------------------------------------------------------------------------


def _loose_json(value: Any) -> dict[str, Any]:
    """Model tool-arguments are frequently malformed. Salvage what we can."""
    if isinstance(value, dict):
        return value
    if value is None:
        return {}
    text = str(value).strip()
    if not text:
        return {}
    try:
        parsed = json.loads(text)
        return parsed if isinstance(parsed, dict) else {"value": parsed}
    except json.JSONDecodeError:
        pass
    # strip markdown fences and leading prose
    if "```" in text:
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]
    start, end = text.find("{"), text.rfind("}")
    if start != -1 and end > start:
        try:
            parsed = json.loads(text[start:end + 1])
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            pass
    # last resort: flat key=value pairs
    recovered: dict[str, Any] = {}
    for piece in text.replace(",", " ").split():
        if "=" in piece:
            key, _, raw = piece.partition("=")
            recovered[key.strip().strip('"\'')] = raw.strip().strip('"\'')
    return recovered


# ---------------------------------------------------------------------------


def provider_from_env() -> Provider:
    """Build a provider from environment variables.

    SENTINEL_PROVIDER   openai-compat | anthropic | ollama | offline  (default openai-compat)
    SENTINEL_MODEL      model id                                      (required)
    SENTINEL_BASE_URL   private/self-hosted endpoint                  (openai-compat/ollama)
    SENTINEL_API_KEY    credential
    SENTINEL_ORG        optional org id
    SENTINEL_NO_NATIVE_TOOLS=1  force the portable text tool protocol
    """
    kind = os.environ.get("SENTINEL_PROVIDER", "openai-compat").strip().lower()
    model = os.environ.get("SENTINEL_MODEL", "").strip()
    base_url = os.environ.get("SENTINEL_BASE_URL", "").strip()
    api_key = (os.environ.get("SENTINEL_API_KEY")
               or os.environ.get("OPENAI_API_KEY", "")).strip()
    native = os.environ.get("SENTINEL_NO_NATIVE_TOOLS", "").strip() not in ("1", "true", "yes")

    if kind in ("offline", "none", "stub"):
        return OfflineProvider()
    if kind == "anthropic":
        if not model:
            raise ProviderError("SENTINEL_MODEL is required for the anthropic provider")
        return AnthropicProvider(model, api_key or os.environ.get("ANTHROPIC_API_KEY", ""),
                                 base_url or "https://api.anthropic.com")
    if kind == "ollama":
        return OllamaProvider(model or "llama3.1", base_url or "http://127.0.0.1:11434/v1",
                              native_tools=native)
    if not model:
        raise ProviderError(
            "SENTINEL_MODEL is required (e.g. export SENTINEL_MODEL=gpt-4o-mini)"
        )
    if not base_url:
        base_url = os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1")
    return OpenAICompatProvider(model, base_url=base_url, api_key=api_key,
                                org=os.environ.get("SENTINEL_ORG", ""),
                                native_tools=native)


PROVIDER_KINDS = ("openai-compat", "anthropic", "ollama", "offline")
