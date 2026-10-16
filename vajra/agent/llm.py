# -*- coding: utf-8 -*-
"""
VAJRA LLM backends — zero-dependency (sirf Python stdlib).
Supported: Groq (fast+free), Google Gemini (free), OpenAI, OpenRouter (free models),
           Ollama (fully offline/local).
Sab OpenAI-compatible /chat/completions API use karte hain with streaming + tool calling.
"""

import json
import ssl
import time
import urllib.error
import urllib.request

DEFAULTS = {
    "groq": {
        "label": "Groq (sabse TEZ + free) — groq.com se key lo",
        "base": "https://api.groq.com/openai/v1",
        "model": "llama-3.3-70b-versatile",
        "needs_key": True,
        "hint": "console.groq.com/keys par free key banao",
    },
    "gemini": {
        "label": "Google Gemini (free tier)",
        "base": "https://generativelanguage.googleapis.com/v1beta/openai",
        "model": "gemini-2.0-flash",
        "needs_key": True,
        "hint": "aistudio.google.com/apikey par free key banao",
    },
    "openai": {
        "label": "OpenAI (GPT)",
        "base": "https://api.openai.com/v1",
        "model": "gpt-4o-mini",
        "needs_key": True,
        "hint": "platform.openai.com/api-keys",
    },
    "openrouter": {
        "label": "OpenRouter (GPT/Claude/Llama sab, free models bhi)",
        "base": "https://openrouter.ai/api/v1",
        "model": "meta-llama/llama-3.3-70b-instruct:free",
        "needs_key": True,
        "hint": "openrouter.ai/keys",
    },
    "ollama": {
        "label": "Ollama (fully OFFLINE, free, private — bina key)",
        "base": "http://127.0.0.1:11434/v1",
        "model": "llama3.2",
        "needs_key": False,
        "hint": "Termux mein: pkg install ollama && ollama serve && ollama pull llama3.2",
    },
}

FAST_MODELS = {
    "groq": "llama-3.3-70b-versatile",
    "gemini": "gemini-2.0-flash",
    "openrouter": "meta-llama/llama-3.3-70b-instruct:free",
}


class VajraError(Exception):
    """User-friendly error."""


class LLM:
    def __init__(self, backend="groq", api_key="", model="", base_url=""):
        self.backend = backend or "groq"
        d = DEFAULTS.get(self.backend, DEFAULTS["groq"])
        self.base = (base_url or d["base"]).rstrip("/")
        self.model = model or d["model"]
        self.api_key = api_key or ""

    # ------------------------------------------------------------------
    def _headers(self):
        key = self.api_key or "ollama"
        return {"Authorization": "Bearer " + key}

    def _payload(self, messages, tools=None, stream=True):
        p = {
            "model": self.model,
            "messages": messages,
            "stream": stream,
            "temperature": 0.25,
        }
        if tools:
            p["tools"] = tools
            p["tool_choice"] = "auto"
        return p

    def _open(self, payload, timeout=300):
        req = urllib.request.Request(
            self.base + "/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json", "User-Agent": "vajra/1.0",
                     **self._headers()},
            method="POST",
        )
        ctx = ssl.create_default_context()
        try:
            return urllib.request.urlopen(req, timeout=timeout, context=ctx)
        except urllib.error.HTTPError as e:
            body = ""
            try:
                body = e.read().decode("utf-8", "replace")
            except Exception:
                pass
            msg = body[:400]
            try:
                j = json.loads(body)
                msg = (j.get("error") or {}).get("message") or body[:400]
            except Exception:
                pass
            raise VajraError("HTTP %s: %s" % (e.code, msg)) from None
        except urllib.error.URLError as e:
            reason = getattr(e, "reason", e)
            if "Connection refused" in str(reason) or "refused" in str(reason).lower():
                raise VajraError(
                    "Server se connection nahi bana (%s).\n"
                    "Ollama use kar rahe ho? Pehle dusre session mein chalao: ollama serve" % reason) from None
            raise VajraError("Connection fail: %s" % reason) from None

    # ------------------------------------------------------------------
    def chat_stream(self, messages, tools=None):
        """
        Generator — events yield karta hai:
          {"type": "text", "delta": "..."}                  # answer ka tukda
          {"type": "tool_call", "id","name","arguments"}    # poora tool call (accumulated)
          {"type": "done", "latency": float, "tokens": int}
        """
        t0 = time.time()
        resp = self._open(self._payload(messages, tools=tools, stream=True))
        text_acc = []
        calls = {}  # index -> {"id","name","arguments"}
        tokens = 0
        try:
            for raw in resp:
                line = raw.decode("utf-8", "replace").strip()
                if not line.startswith("data:"):
                    continue
                data = line[5:].strip()
                if data == "[DONE]":
                    break
                try:
                    obj = json.loads(data)
                except Exception:
                    continue
                if obj.get("usage"):
                    tokens = (obj["usage"].get("total_tokens") or 0)
                ch = (obj.get("choices") or [{}])[0]
                delta = ch.get("delta") or {}
                piece = delta.get("content")
                if piece:
                    text_acc.append(piece)
                    yield {"type": "text", "delta": piece}
                for tc in delta.get("tool_calls") or []:
                    idx = tc.get("index", 0)
                    slot = calls.setdefault(idx, {"id": "", "name": "", "arguments": ""})
                    if tc.get("id"):
                        slot["id"] = tc["id"]
                    fn = tc.get("function") or {}
                    if fn.get("name"):
                        slot["name"] = fn["name"]
                    if fn.get("arguments"):
                        slot["arguments"] += fn["arguments"]
        finally:
            try:
                resp.close()
            except Exception:
                pass
        for idx in sorted(calls):
            c = calls[idx]
            c["type"] = "tool_call"
            yield c
        yield {"type": "done", "latency": round(time.time() - t0, 2),
               "tokens": tokens, "text": "".join(text_acc)}

    # ------------------------------------------------------------------
    def test(self):
        """Latency test — (seconds, reply_text) return karta hai."""
        t0 = time.time()
        out = []
        for ev in self.chat_stream([{"role": "user",
                                     "content": "Reply with exactly: VAJRA Online"}]):
            if ev["type"] == "text":
                out.append(ev["delta"])
        return round(time.time() - t0, 2), "".join(out).strip()
