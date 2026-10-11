# -*- coding: utf-8 -*-
"""
VAJRA Chat — agent brain.
LLM ke tool-calls ko executor se jodta hai, confirmation flow sambhalta hai.
CLI aur Web server dono yehi core use karte hain.
"""

import json
import time
import uuid

from . import executor, registry
from .llm import LLM, VajraError

MAX_TOOL_CALLS = 6          # ek message par max kitne commands
MAX_HISTORY = 40            # context mein max messages

SYSTEM_PROMPT = """Tum VAJRA (वज्र) ho — Android phone ke Termux par chalne wala advanced AI ethical-hacking agent.

MISSION: Authorized security testing mein user ko full madad karna — labs, CTFs, unke khud ke assets, bug bounty targets (in-scope), ya written permission wale engagements.

INSTALLED TOOLS (phase-wise):
%s

Plus normal Linux/Termux commands (curl, dig, whois, ping, ssh, traceroute, base64, etc.) sab available hain.

STYLE RULES:
- User ki bhasha mein jawab do (Hinglish / Hindi / English — jo bhi user use kare). Chhota, seedha, action-oriented.
- Pattern: plan → command chalao → result ka summary → agla kadam.
- Tool output ka SUMMARY do, 1000 lines chipkao mat. Important findings (open ports, vulns, creds pattern) highlight karo.
- Scans lamba chal sakta hai — reasonable flags use karo (e.g. nmap -T4, top-1000 ports pehle, poora -p- baad mein).

HARD RULES:
1. Commands chalane ke liye sirf shell() tool use karo. Ek waqt mein ek hi meaningful command — output dekh kar aage badho.
2. SIRF authorized targets. Agar target user ke scope mein nahi lagta, pehle warn karo aur confirm maango.
3. Illegal cheezein (bina permission kisi ka access/credential/phishing, malware, harassment, DDoS) — politely mana kar do aur legal alternative batao (TryHackMe, HackTheBox, bug bounty programs).
4. Koi tool installed nahi? User ko 'bash install.sh' (heavy tools ke liye --full) suggest karo, ya equivalent nmap/python se kaam nikalo.
5. Destructive commands (rm -rf /, mkfs, mass reboot) kabhi suggest mat karo — chahe user hi kyu na maange, warna mana kar do.
6. Output file/cleanup commands chalate waqt user ke home directory ka respect rakho."""

TOOLS_SCHEMA = [{
    "type": "function",
    "function": {
        "name": "shell",
        "description": "Termux/Linux shell command chalao (hacking tools, scans, recon — sab). "
                       "Output stream hota hai aur user confirmation ke baad hi execute hota hai.",
        "parameters": {
            "type": "object",
            "properties": {
                "command": {
                    "type": "string",
                    "description": "Poora shell command jo chalana hai",
                },
                "purpose": {
                    "type": "string",
                    "description": "Ek line mein: yeh command kya karegi (Hinglish mein)",
                },
            },
            "required": ["command", "purpose"],
        },
    },
}]

BASH_BLOCK = None  # import re lazily below
import re as _re
BASH_BLOCK = _re.compile(r"```(?:bash|sh|shell|console)\s*\n(.*?)```", _re.S)


class Pending:
    """Web UI ke liye pending confirmation."""
    def __init__(self, calls, note=""):
        self.id = uuid.uuid4().hex[:12]
        self.calls = calls        # list of {"id","name","arguments" dict}
        self.idx = 0
        self.note = note

    def current(self):
        return self.calls[self.idx] if self.idx < len(self.calls) else None


class VajraSession:
    """Ek chat session (CLI ya Web)."""

    def __init__(self, llm, yolo=False):
        self.llm = llm
        self.history = []          # list of OpenAI-format messages
        self.yolo = yolo           # True → risky commands bhi bina confirm
        self.plain_mode = False    # model tools support nahi karta
        self.last_latency = None

    # ------------------------------------------------------------- public
    def send(self, text, emit, confirm_cb=None):
        """User message bhejo. Return: ("done", None) ya ("pending", Pending)."""
        self.history.append({"role": "user", "content": text})
        return self._loop(emit, confirm_cb)

    def resume(self, pid, approved, emit, confirm_cb=None):
        """Web confirm ke baad continue."""
        pend = getattr(self, "_pending_store", {}).pop(pid, None)
        if not pend:
            emit({"t": "error", "message": "Pending command nahi mila (expire ho gaya)."})
            return "done", None
        call = pend.current()
        if approved:
            self._execute_call(call, emit)
        else:
            emit({"t": "note", "text": "⛔ Command cancel kar diya gaya."})
            self.history.append({
                "role": "tool", "tool_call_id": call["id"],
                "content": "User ne yeh command chalane se mana kiya."})
        pend.idx += 1
        self._pending_store = getattr(self, "_pending_store", {})
        if pend.idx < len(pend.calls):
            self._pending_store[pend.id] = pend
            nxt = pend.current()
            self._maybe_confirm(nxt, emit, note=pend.note, pend=pend)
            return "pending", pend
        return self._loop(emit, confirm_cb)

    # ------------------------------------------------------------- internals
    def _messages(self):
        sysmsg = SYSTEM_PROMPT % "\n".join(registry.summary_lines())
        return [{"role": "system", "content": sysmsg}] + self.history[-MAX_HISTORY:]

    def _execute_call(self, call, emit):
        args = call.get("args") or {}
        cmd = args.get("command", "")
        emit({"t": "tool_run", "command": cmd, "purpose": args.get("purpose", "")})
        res = executor.run(cmd, on_line=lambda l: emit({"t": "output", "line": l}))
        summary = res["output"] or "(no output)"
        if res["timed_out"]:
            summary = "[TIMEOUT — command %ss mein band kar diya]\n%s" % (
                res["duration"], summary)
        if len(summary) > 12000:
            summary = summary[:6000] + "\n...[cut]...\n" + summary[-5000:]
        self.history.append({
            "role": "tool", "tool_call_id": call["id"],
            "content": "rc=%s dur=%ss\n%s" % (res["rc"], res["duration"], summary)})

    def _needs_confirm(self, cmd, note):
        if self.yolo and not note:
            return False
        return executor.is_risky(cmd) or bool(note)

    def _maybe_confirm(self, call, emit, note="", pend=None):
        cmd = call["args"].get("command", "")
        purpose = call["args"].get("purpose", "")
        event = {"t": "confirm", "command": cmd, "purpose": purpose, "note": note,
                 "id": pend.id if pend else ""}
        if pend:
            event["id"] = pend.id
        emit(event)
        return event

    def _loop(self, emit, confirm_cb=None):
        budget = MAX_TOOL_CALLS
        while budget > 0:
            tools = None if self.plain_mode else TOOLS_SCHEMA
            try:
                stream = self.llm.chat_stream(self._messages(), tools=tools)
            except VajraError as e:
                msg = str(e)
                if not self.plain_mode and ("tool" in msg.lower() or "400" in msg[:12]):
                    # Model tools support nahi karta — plain mode try karo
                    self.plain_mode = True
                    emit({"t": "note",
                          "text": "ℹ️  Yeh model tool-calling support nahi karta — "
                                  "plain mode mein command suggest karega."})
                    continue
                emit({"t": "error", "message": msg})
                return "done", None

            text, calls, latency = "", [], None
            for ev in stream:
                if ev["type"] == "text":
                    text += ev["delta"]
                    emit({"t": "delta", "text": ev["delta"]})
                elif ev["type"] == "tool_call":
                    calls.append(ev)
                elif ev["type"] == "done":
                    latency = ev.get("latency")
            self.last_latency = latency
            emit({"t": "meta", "latency": latency})

            # ---- assistant message history mein daalo
            if text or calls:
                amsg = {"role": "assistant", "content": text or ""}
                if calls:
                    amsg["content"] = text or None
                    amsg["tool_calls"] = [
                        {"id": c["id"], "type": "function",
                         "function": {"name": c["name"], "arguments": c["arguments"]}}
                        for c in calls]
                self.history.append(amsg)

            # ---- plain mode: ```bash block detect karke offer karo
            if self.plain_mode:
                m = BASH_BLOCK.search(text or "")
                if m:
                    cmd = m.group(1).strip()
                    call = {"id": "plain-" + uuid.uuid4().hex[:8], "name": "shell",
                            "args": {"command": cmd, "purpose": "(model ka suggested command)"}}
                    self._offer(call, emit, confirm_cb,
                                note="Model ne command suggest kiya (tool-mode unavailable)")
                    return "done", None
                return "done", None

            if not calls:
                return "done", None

            # ---- tool calls process karo
            parsed = []
            for c in calls:
                try:
                    cargs = json.loads(c.get("arguments") or "{}")
                except Exception:
                    cargs = {"command": "", "purpose": "parse fail"}
                parsed.append({"id": c["id"], "name": c["name"], "args": cargs})

            for call in parsed:
                cmd = call["args"].get("command", "").strip()
                if not cmd:
                    self.history.append({"role": "tool", "tool_call_id": call["id"],
                                         "content": "Empty command."})
                    continue
                ok, note = executor.scope_check(cmd)
                budget -= 1
                if not self._needs_confirm(cmd, "" if ok else note):
                    self._execute_call(call, emit)
                    continue
                # confirmation chahiye
                if confirm_cb is not None:
                    if confirm_cb(cmd, call["args"].get("purpose", ""),
                                  "" if ok else note):
                        self._execute_call(call, emit)
                    else:
                        emit({"t": "note", "text": "⛔ Cancel."})
                        self.history.append({
                            "role": "tool", "tool_call_id": call["id"],
                            "content": "User declined."})
                else:
                    return self._offer(call, emit, confirm_cb,
                                       note="" if ok else note)
                if budget <= 0:
                    break

        # budget khatam — final answer force karo
        self.history.append({"role": "user",
                             "content": "(Bas — ab naya command mat chalao, "
                                        "ab tak ke findings ka short final summary do.)"})
        try:
            for ev in self.llm.chat_stream(self._messages()):
                if ev["type"] == "text":
                    emit({"t": "delta", "text": ev["delta"]})
        except VajraError as e:
            emit({"t": "error", "message": str(e)})
        return "done", None

    def _offer(self, call, emit, confirm_cb, note=""):
        """Pending banao — web ke liye return, CLI ke liye sync confirm."""
        if confirm_cb is not None:
            if confirm_cb(call["args"].get("command", ""),
                          call["args"].get("purpose", ""), note):
                self._execute_call(call, emit)
                return self._loop(emit, confirm_cb)
            emit({"t": "note", "text": "⛔ Cancel."})
            self.history.append({"role": "tool", "tool_call_id": call["id"],
                                 "content": "User declined."})
            return self._loop(emit, confirm_cb)
        pend = Pending([call], note=note)
        self._pending_store = getattr(self, "_pending_store", {})
        self._pending_store[pend.id] = pend
        self._maybe_confirm(call, emit, note=note, pend=pend)
        return "pending", pend
