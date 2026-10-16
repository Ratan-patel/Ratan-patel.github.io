# -*- coding: utf-8 -*-
"""
VAJRA Executor — safe command execution.
- Scope checking (authorized targets)
- Risk-based confirmation
- Live streaming output
- Audit logging + report generation
"""

import datetime
import json
import os
import queue
import re
import shlex
import shutil
import subprocess
import threading
import time

VAJRA_HOME = os.path.join(os.path.expanduser("~"), ".vajra")
SCOPE_FILE = os.path.join(VAJRA_HOME, "scope.json")
AUDIT_FILE = os.path.join(VAJRA_HOME, "audit.log")
os.makedirs(VAJRA_HOME, exist_ok=True)

# In commands jo bina confirm ke chal sakte hain (read-only / local)
SAFE_COMMANDS = {
    "ls", "cd", "cat", "head", "tail", "echo", "printf", "whoami", "id", "uname",
    "pwd", "df", "du", "free", "ps", "top", "which", "command", "grep", "find",
    "wc", "date", "cal", "ifconfig", "ip", "netstat", "ss", "whois", "dig",
    "nslookup", "ping", "arp", "curl", "wget", "git", "pip", "pip3", "python",
    "python3", "pkg", "apt", "vajra", "nproc", "uptime", "history", "clear",
    "hostname", "env", "printenv", "sleep", "true", "false", "test", "help",
}

PRIVATE_RE = re.compile(
    r"^(127\.|10\.|192\.168\.|172\.(1[6-9]|2\d|3[01])\.|::1|localhost|0\.0\.0\.0)", re.I)
TARGET_RE = re.compile(r"\b((?:\d{1,3}\.){3}\d{1,3}|(?:[a-zA-Z0-9-]+\.)+[a-zA-Z]{2,12})\b")


# ---------------------------------------------------------------- scope
def scope_list():
    try:
        with open(SCOPE_FILE) as f:
            return json.load(f)
    except Exception:
        return []


def scope_save(items):
    with open(SCOPE_FILE, "w") as f:
        json.dump(sorted(set(items)), f, indent=1)


def scope_add(target):
    items = scope_list()
    if target not in items:
        items.append(target)
        scope_save(items)
    return items


def scope_remove(target):
    items = [t for t in scope_list() if t != target]
    scope_save(items)
    return items


def _base_command(cmd):
    try:
        parts = shlex.split(cmd)
    except ValueError:
        parts = cmd.split()
    if not parts:
        return ""
    return os.path.basename(parts[0])


def extract_targets(cmd):
    found = set()
    for m in TARGET_RE.findall(cmd or ""):
        found.add(m.lower().strip(".,;:"))
    return sorted(found)


def scope_check(cmd):
    """
    (ok, note) return karta hai.
    ok=True  → target scope mein hai (ya local/private, ya koi target nahi)
    ok=False → target scope mein NAHI hai — confirm ke saath warning chahiye
    """
    base = _base_command(cmd)
    if base in SAFE_COMMANDS:
        return True, ""
    targets = extract_targets(cmd)
    if not targets:
        return True, ""
    scope = [s.lower() for s in scope_list()]
    notes, bad = [], []
    for t in targets:
        in_scope = any(t == s or t.endswith("." + s) for s in scope)
        if in_scope:
            continue
        if PRIVATE_RE.match(t):
            notes.append("%s (local/private network)" % t)
            continue
        bad.append(t)
    if not bad:
        return True, ("; ".join(notes) if notes else "")
    return False, ("⚠️  OUT OF SCOPE: %s — authorized target hai toh pehle "
                   "'/scope add <target>' karo, warna confirm karo" % ", ".join(bad))


def is_risky(cmd):
    return _base_command(cmd) not in SAFE_COMMANDS


# ---------------------------------------------------------------- audit
def audit(action, detail=""):
    try:
        ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(AUDIT_FILE, "a") as f:
            f.write("%s | %s | %s\n" % (ts, action, detail.replace("\n", " ")[:500]))
    except Exception:
        pass


def generate_report():
    """Audit log se markdown pentest report banao."""
    try:
        with open(AUDIT_FILE) as f:
            lines = [l.rstrip("\n") for l in f if l.strip()]
    except Exception:
        lines = []
    now = datetime.datetime.now()
    path = os.path.join(VAJRA_HOME, "report_%s.md" % now.strftime("%Y%m%d_%H%M"))
    with open(path, "w") as f:
        f.write("# VAJRA Pentest Report\n\n")
        f.write("**Date:** %s\n\n" % now.strftime("%d %b %Y, %H:%M"))
        f.write("**Operator:** %s\n\n" % os.environ.get("USER", "user"))
        f.write("**Authorized scope:** %s\n\n" % (", ".join(scope_list()) or "(khali)"))
        f.write("> Note: Yeh report VAJRA audit log se auto-generated hai. "
                "Testing sirf authorized systems par hi ki gayi maani jaani chahiye.\n\n")
        f.write("## Activity Log\n\n")
        f.write("| Time | Action | Detail |\n|---|---|---|\n")
        for l in lines[-500:]:
            parts = [p.strip() for p in l.split("|", 2)]
            while len(parts) < 3:
                parts.append("")
            f.write("| %s | %s | %s |\n" % tuple(parts))
        f.write("\n---\n*VAJRA — AI Ethical Hacking Agent*\n")
    return path


# ---------------------------------------------------------------- run
def run(cmd, timeout=900, on_line=None):
    """
    Command chalao — output live stream karo, timeout par maaro.
    Return: {"rc", "output", "timed_out", "duration"}
    """
    audit("RUN", cmd)
    bash = shutil.which("bash") or "/bin/sh"
    env = dict(os.environ)
    env["TERM"] = env.get("TERM", "dumb")
    env["DEBIAN_FRONTEND"] = "noninteractive"
    t0 = time.time()
    proc = subprocess.Popen(
        [bash, "-c", cmd],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
        env=env,
    )
    # reader thread — output nahi dene wale commands (sleep etc.) par bhi
    # timeout kaam kare, isliye queue + deadline polling.
    q = queue.Queue()

    def _reader():
        try:
            for line in proc.stdout:
                q.put(line.rstrip("\n"))
        except Exception:
            pass
        finally:
            q.put(None)  # EOF marker

    threading.Thread(target=_reader, daemon=True).start()

    lines = []
    deadline = t0 + timeout
    eof = timed_out = False
    while not eof:
        remaining = deadline - time.time()
        if remaining <= 0:
            timed_out = True
            break
        try:
            item = q.get(timeout=min(1.0, remaining))
        except queue.Empty:
            continue
        if item is None:
            eof = True
            break
        lines.append(item)
        if on_line:
            try:
                on_line(item)
            except Exception:
                pass

    if timed_out:
        proc.kill()
        rc = -1
    else:
        try:
            rc = proc.wait(timeout=30)
        except subprocess.TimeoutExpired:
            proc.kill()
            rc, timed_out = -1, True
    dur = round(time.time() - t0, 1)
    out = "\n".join(lines)
    if len(out) > 30000:
        out = (out[:8000] + "\n... [output cut — beech ka hissa hata diya] ...\n"
               + out[-20000:])
    audit("DONE rc=%s (%ss)" % (rc, dur), "")
    return {"rc": rc, "output": out, "timed_out": timed_out, "duration": dur}
