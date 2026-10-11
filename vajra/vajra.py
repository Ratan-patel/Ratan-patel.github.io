#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
VAJRA ⚡ — Advanced AI Ethical Hacking Agent for Termux
Usage:
  vajra                 interactive chat
  vajra "sawal"         one-shot
  vajra --setup         backend/key setup wizard
  vajra --server        Web UI (app jaisa) chalao — http://localhost:8080
  vajra --tools         tools ki status list
  vajra --report        audit log se pentest report banao
  vajra --selftest      khud ka checkup
"""

import argparse
import getpass
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

from agent import executor, registry                     # noqa: E402
from agent.chat import VajraSession                      # noqa: E402
from agent.llm import DEFAULTS, FAST_MODELS, LLM, VajraError  # noqa: E402

CONFIG_FILE = os.path.join(executor.VAJRA_HOME, "config.json")

BANNER = r"""
\033[1;35m██╗   ██╗ █████╗ ████████╗ █████╗ \033[0m
\033[1;35m██║   ██║██╔══██╗╚══██╔══╝██╔══██╗\033[0m
\033[1;35m██║   ██║███████║   ██║   ███████║\033[0m
\033[1;35m╚██╗ ██╔╝██╔══██║   ██║   ██╔══██║\033[0m
\033[1;35m ╚████╔╝ ██║  ██║   ██║   ██║  ██║\033[0m
\033[1;35m  ╚═══╝  ╚═╝  ╚═╝   ╚═╝   ╚═╝  ╚═╝\033[0m
  \033[1;32m⚡ AI Ethical Hacking Agent — Termux Edition ⚡\033[0m
  \033[2mAuthorized testing ke liye bana hai. Scope set karo: /scope add <target>\033[0m
"""

C = {"g": "\033[1;32m", "y": "\033[1;33m", "r": "\033[1;31m",
     "c": "\033[1;36m", "m": "\033[1;35m", "d": "\033[2m", "0": "\033[0m"}


def col(name):
    return C.get(name, "") if sys.stdout.isatty() and os.environ.get("VAJRA_NOCOLOR") is None else ""


# ------------------------------------------------------------------ config
def load_config():
    try:
        with open(CONFIG_FILE) as f:
            return json.load(f)
    except Exception:
        return {}


def save_config(cfg):
    with open(CONFIG_FILE, "w") as f:
        json.dump(cfg, f, indent=1)
    try:
        os.chmod(CONFIG_FILE, 0o600)
    except Exception:
        pass


def make_llm(cfg=None):
    cfg = cfg or load_config()
    return LLM(backend=cfg.get("backend", "groq"),
               api_key=cfg.get("api_key", ""),
               model=cfg.get("model", ""),
               base_url=cfg.get("base_url", ""))


def needs_setup(cfg):
    b = cfg.get("backend", "groq")
    d = DEFAULTS.get(b, DEFAULTS["groq"])
    return (not cfg.get("backend")) or (d["needs_key"] and not cfg.get("api_key"))


# ------------------------------------------------------------------ setup
def setup_wizard():
    print(col("m") + "\n⚙️  VAJRA Setup — apna AI backend chuno" + col("0"))
    keys = list(DEFAULTS.keys())
    for i, k in enumerate(keys, 1):
        d = DEFAULTS[k]
        print("  %d) %-52s \033[2m%s\033[0m" % (i, d["label"], d["hint"]))
    while True:
        try:
            n = input("\nChoice [1-5] (default 1 Groq — sabse fast): ").strip() or "1"
            backend = keys[int(n) - 1]
            break
        except (ValueError, IndexError):
            print(col("r") + "1 se 5 tak number daalo" + col("0"))
    cfg = load_config()
    cfg["backend"] = backend
    d = DEFAULTS[backend]
    if d["needs_key"]:
        print("\n🔑 API key daalo (%s):" % d["hint"])
        key = getpass.getpass("   key (input hidden): ").strip()
        if not key:
            print(col("y") + "Key khali — baad mein /key se set kar lena." + col("0"))
        cfg["api_key"] = key
    else:
        cfg["api_key"] = ""
    if backend == "ollama":
        print(col("y") + "\nℹ️  6GB+ RAM ho toh behtar model: qwen2.5:7b-instruct"
              "\n   pull: ollama pull qwen2.5:7b-instruct" + col("0"))
    default_model = d["model"]
    m = input("\n🤖 Model [%s]: " % default_model).strip()
    if m:
        cfg["model"] = m
    else:
        cfg["model"] = default_model
    save_config(cfg)
    print(col("g") + "\n✓ Config save ho gaya: ~/.vajra/config.json" + col("0"))

    # latency test
    if cfg.get("api_key") or not d["needs_key"]:
        print(col("c") + "\n⏱  Speed test chal raha hai..." + col("0"))
        try:
            secs, reply = make_llm(cfg).test()
            print(col("g") + "✓ Online! Latency: %ss | Model ne kaha: %s"
                  % (secs, reply[:60]) + col("0"))
        except VajraError as e:
            print(col("r") + "✗ Test fail: %s" % e + col("0"))
            print(col("d") + "   /key se dobara try kar sakte ho." + col("0"))


# ------------------------------------------------------------------ CLI emit
def cli_emit(ev):
    t = ev.get("t")
    if t == "delta":
        sys.stdout.write(ev["text"])
        sys.stdout.flush()
    elif t == "tool_run":
        print("\n" + col("y") + "⚡ CHAL RAHA HAI: " + col("0") + ev["command"])
        if ev.get("purpose"):
            print(col("d") + "   → " + ev["purpose"] + col("0"))
        print(col("d") + "   " + "─" * 46 + col("0"))
    elif t == "output":
        print("  " + ev["line"][:400])
    elif t == "note":
        print(col("y") + ev["text"] + col("0"))
    elif t == "error":
        print(col("r") + "\n✗ " + ev["message"] + col("0"))
    # meta/confirm CLI mein alag se handle hote hain


def cli_confirm(cmd, purpose, note):
    print("\n" + col("c") + "🖥️  COMMAND: " + col("0") + cmd)
    if purpose:
        print(col("d") + "   maqsad: " + purpose + col("0"))
    if note:
        print(col("y") + "   " + note + col("0"))
    try:
        ans = input(col("y") + "   Chalau? [y/N] " + col("0")).strip().lower()
    except (EOFError, KeyboardInterrupt):
        return False
    return ans in ("y", "yes", "ha", "haan", "chala", "chalo")


# ------------------------------------------------------------------ REPL
HELP = """
%s /help      — yeh madad
  /tools     — saare tools ki installed status
  /scope     — authorized targets dekho / add / remove (/scope add example.com)
  /key       — API key dobara set karo
  /backend   — backend badlo (groq/gemini/openai/openrouter/ollama)
  /model     — model badlo
  /fast      — is backend ka fastest model set karo
  /yolo      — confirmations OFF/ON toggle (out-of-scope par bhi rahega)
  /report    — ab tak ka audit report banao
  /reset     — chat history reset
  !command   — seedha command chalao (AI ke bina)
  /exit      — band karo%s""" % (col("c"), col("0"))


def repl():
    cfg = load_config()
    if needs_setup(cfg):
        setup_wizard()
        cfg = load_config()
    llm = make_llm(cfg)
    session = VajraSession(llm, yolo=cfg.get("yolo", False))
    print(BANNER if sys.stdout.isatty() else BANNER.replace("\033[", "\033["))
    print(col("d") + "Backend: %s | Model: %s | /help se commands dekho\n" % (
        llm.backend, llm.model) + col("0"))

    while True:
        try:
            text = input(col("g") + "⚡ you ▸ " + col("0")).strip()
        except (EOFError, KeyboardInterrupt):
            print("\n" + col("m") + "VAJRA band. Jai Hind 🙏" + col("0"))
            break
        if not text:
            continue
        # ----- slash commands
        if text.startswith("/"):
            parts = text.split()
            cmd = parts[0].lower()
            if cmd == "/exit" or cmd == "/quit":
                print(col("m") + "VAJRA band. Jai Hind 🙏" + col("0"))
                break
            elif cmd == "/help":
                print(HELP)
            elif cmd == "/tools":
                print(registry.status_table())
            elif cmd == "/scope":
                if len(parts) >= 3 and parts[1] == "add":
                    executor.scope_add(parts[2])
                    print(col("g") + "✓ Scope mein add: %s" % parts[2] + col("0"))
                elif len(parts) >= 3 and parts[1] in ("rm", "remove", "del"):
                    executor.scope_remove(parts[2])
                    print(col("g") + "✓ Scope se hata diya." + col("0"))
                else:
                    items = executor.scope_list()
                    print(col("c") + "🎯 Authorized scope:" + col("0"))
                    for i in items:
                        print("   • " + i)
                    if not items:
                        print(col("y") + "   (khali — /scope add example.com se add karo)" + col("0"))
            elif cmd == "/key":
                key = getpass.getpass("Nayi API key: ").strip()
                cfg["api_key"] = key
                save_config(cfg)
                session.llm = make_llm(cfg)
                print(col("g") + "✓ Key update." + col("0"))
            elif cmd == "/backend":
                if len(parts) > 1 and parts[1] in DEFAULTS:
                    cfg["backend"] = parts[1]
                    save_config(cfg)
                    session.llm = make_llm(cfg)
                    print(col("g") + "✓ Backend: %s (model: %s)" % (parts[1], session.llm.model) + col("0"))
                else:
                    print("Options: " + ", ".join(DEFAULTS))
            elif cmd == "/model":
                if len(parts) > 1:
                    cfg["model"] = parts[1]
                    save_config(cfg)
                    session.llm = make_llm(cfg)
                    print(col("g") + "✓ Model: %s" % parts[1] + col("0"))
                else:
                    print("Abhi: %s — /model <naam> se badlo" % session.llm.model)
            elif cmd == "/fast":
                m = FAST_MODELS.get(session.llm.backend)
                if m:
                    cfg["model"] = m
                    save_config(cfg)
                    session.llm = make_llm(cfg)
                    print(col("g") + "⚡ Fast model set: %s" % m + col("0"))
                else:
                    print(col("y") + "Is backend ke liye alag fast model nahi hai." + col("0"))
            elif cmd == "/yolo":
                session.yolo = not session.yolo
                cfg["yolo"] = session.yolo
                save_config(cfg)
                state = "ON (confirm kam)" if session.yolo else "OFF (confirm normal)"
                print(col("y") + "Yolo mode: %s" % state + col("0"))
            elif cmd == "/report":
                p = executor.generate_report()
                print(col("g") + "✓ Report ban gayi: %s" % p + col("0"))
            elif cmd == "/reset":
                session.history = []
                print(col("g") + "✓ History reset." + col("0"))
            else:
                print(col("y") + "Unknown command. /help dekho." + col("0"))
            continue
        # ----- direct shell fast-path
        if text.startswith("!"):
            cmd = text[1:].strip()
            ok, note = executor.scope_check(cmd)
            print(col("y") + "🖥️  " + cmd + col("0"))
            if note:
                print(col("y") + note + col("0"))
            res = executor.run(cmd, on_line=lambda l: print("  " + l[:400]))
            print(col("d") + "   [rc=%s, %ss]" % (res["rc"], res["duration"]) + col("0"))
            continue
        # ----- AI
        print(col("m") + "🤖 vajra ▸ " + col("0"), end="", flush=True)
        state, _ = session.send(text, cli_emit, confirm_cb=cli_confirm)
        while state == "pending":
            try:
                ans = input(col("y") + "\n   Chalau? [y/N] " + col("0")).strip().lower()
            except (EOFError, KeyboardInterrupt):
                ans = "n"
            state, _ = session.resume(_.id, ans in ("y", "yes", "haan"), cli_emit,
                                      confirm_cb=cli_confirm)
        if session.last_latency:
            print(col("d") + "\n   [%.1fs | %s]" % (session.last_latency, llm.model) + col("0"))
        print()


# ------------------------------------------------------------------ main
def main():
    p = argparse.ArgumentParser(prog="vajra",
                                description="VAJRA — AI Ethical Hacking Agent (Termux)")
    p.add_argument("prompt", nargs="*", help="one-shot sawal")
    p.add_argument("--setup", action="store_true", help="setup wizard")
    p.add_argument("--server", action="store_true", help="Web UI server chalao")
    p.add_argument("--port", type=int, default=8080)
    p.add_argument("--host", default="0.0.0.0")
    p.add_argument("--tools", action="store_true", help="tools status print karo")
    p.add_argument("--report", action="store_true", help="report generate karo")
    p.add_argument("--selftest", action="store_true", help="self test")
    p.add_argument("--version", action="version", version="vajra 1.0.0")
    args = p.parse_args()

    if args.selftest:
        sys.exit(selftest())
    if args.tools:
        print(registry.status_table())
        return
    if args.report:
        pth = executor.generate_report()
        print("✓ Report: %s" % pth)
        return
    if args.server:
        import server
        server.serve(args.host, args.port)
        return
    if args.setup:
        setup_wizard()
        return
    if args.prompt:
        cfg = load_config()
        if needs_setup(cfg):
            setup_wizard()
            cfg = load_config()
        session = VajraSession(make_llm(cfg))
        state, pend = session.send(" ".join(args.prompt), cli_emit, confirm_cb=cli_confirm)
        while state == "pending":
            try:
                ans = input(col("y") + "Chalau? [y/N] " + col("0")).strip().lower()
            except (EOFError, KeyboardInterrupt):
                ans = "n"
            state, _ = session.resume(pend.id, ans in ("y", "yes", "haan"), cli_emit,
                                      confirm_cb=cli_confirm)
        return
    repl()


# ------------------------------------------------------------------ selftest
def selftest():
    print("VAJRA selftest\n" + "=" * 50)
    fails = []

    def check(name, fn):
        try:
            ok, extra = fn()
            print("[%s] %s %s" % ("✓" if ok else "✗", name, extra or ""))
            if not ok:
                fails.append(name)
        except Exception as e:
            print("[✗] %s — %s" % (name, e))
            fails.append(name)

    check("Python version >= 3.8", lambda: (sys.version_info >= (3, 8), sys.version.split()[0]))
    check("Registry loads", lambda: (len(registry.TOOLS) >= 25, "%d tools, %d categories" % (
        len(registry.TOOLS), len(registry.CATEGORIES))))
    check("Registry sanity", lambda: (
        all(t.get("name") and t.get("cat") in [c["id"] for c in registry.CATEGORIES]
            and t.get("desc") and t.get("examples") for t in registry.TOOLS), ""))
    check("Executor echo", lambda: (executor.run("echo VAJRA_TEST_OK")["output"] == "VAJRA_TEST_OK", ""))
    check("Executor timeout", lambda: (executor.run("sleep 5", timeout=1)["timed_out"], ""))
    check("Scope add/remove", lambda: (
        executor.scope_add("selftest.example"),
        (lambda: (executor.scope_remove("selftest.example"),
                  ("selftest.example" not in executor.scope_list(), ""))[1])()[1]))
    check("Scope check (out-of-scope pakde)", lambda: (
        executor.scope_check("nmap evil-selftest-target.com")[0] is False, ""))
    check("Scope check (local ok)", lambda: (
        executor.scope_check("nmap 127.0.0.1")[0] is True, ""))
    check("Scope check (safe cmd ok)", lambda: (
        executor.scope_check("ls -la")[0] is True, ""))
    check("Report generate", lambda: (os.path.isfile(executor.generate_report()), ""))

    cfg = load_config()
    d = DEFAULTS.get(cfg.get("backend", "groq"), DEFAULTS["groq"])
    if cfg.get("api_key") or not d["needs_key"]:
        def t():
            s, r = make_llm(cfg).test()
            return "VAJRA" in r or len(r) > 0, "%.1fs — %s" % (s, r[:40])
        check("LLM backend test", t)
    else:
        print("[i] LLM test skip — API key set nahi hai (/key ya --setup se karo)")

    print("=" * 50)
    if fails:
        print("✗ FAIL: %s" % ", ".join(fails))
        return 1
    print("✓ Sab PASS — VAJRA ready hai!")
    return 0


if __name__ == "__main__":
    main()
