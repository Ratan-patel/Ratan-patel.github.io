"""Terminal front-end. Stdlib argparse only, so it runs on a bare Python 3.10+."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any, Sequence

from . import __version__
from .agent import Agent
from .authz import (Guard, PROTECTED_DOMAIN_PATTERNS, PROTECTED_HOST_FRAGMENTS,
                    PROTECTED_PORTS, PROTECTED_PROVIDER_PATTERNS,
                    authorization_banner, default_audit_log, load_scope)
from .config import Config, config_path
from .providers import (OfflineProvider, Provider, ProviderError,
                        PROVIDER_KINDS, provider_from_env)
from .report import console_summary, markdown_report, write_reports
from .scope import (Authorization, Scope, ScopeError, blank_scope,
                    default_scope_path, looks_like_domain, looks_like_hostname,
                    looks_like_ip, utcnow)
from .tools import build_registry, probe_catalog, severity_counts, sort_findings
from .tools.base import RateLimiter, ToolContext
from .ui import BOLD as BOLD_ON, UI, prompt_yes_no

RULES_DOC = """\
Sentinel refuses these regardless of what any scope file says, because an
individual cannot grant themselves permission to touch them.

PORTS never probed (ICS/SCADA, medical, out-of-band mgmt, abuse amplifiers):
  {ports}

DOMAIN patterns never targeted (military / government / treaty bodies):
  {domains}

HOSTNAME fragments never targeted (critical infrastructure):
  {fragments}

PUBLIC PROVIDER domains never targeted (needs their written permission or an
in-scope disclosure program, not your scope file):
  {providers}
"""


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="sentinel",
        description=(
            "Sentinel - a model-agnostic, read-only security assessment agent "
            "for assets you own or hold written permission to test."
        ),
        epilog=(
            "Sentinel cannot attack anything. It audits configuration and "
            "exposure, and it refuses targets outside a signed scope. "
            "Run `sentinel rules` to see the hard prohibitions."
        ),
    )
    parser.add_argument("--version", action="version",
                        version=f"sentinel {__version__}")
    parser.add_argument("--scope", metavar="PATH",
                        help="scope file (default: $SENTINEL_SCOPE or "
                             "~/.config/sentinel/scope.json)")
    parser.add_argument("--no-color", action="store_true", help="disable ANSI colour")
    parser.add_argument("--json", action="store_true",
                        help="machine-readable output where supported")
    sub = parser.add_subparsers(dest="command", metavar="COMMAND")

    # --- doctor ---------------------------------------------------------
    doctor = sub.add_parser("doctor", help="check config, scope and provider health")
    doctor.add_argument("--skip-provider", action="store_true",
                        help="do not make a live model call")

    # --- rules ----------------------------------------------------------
    sub.add_parser("rules", help="print the hard prohibition rules")

    # --- tools ----------------------------------------------------------
    tools = sub.add_parser("tools", help="list assessment tools")
    tools.add_argument("--json", dest="tools_json", action="store_true")

    probes = sub.add_parser("probes", help="list the LLM safety probes")
    probes.add_argument("--json", dest="probes_json", action="store_true")

    # --- scope ----------------------------------------------------------
    scope = sub.add_parser("scope", help="manage the authorization scope")
    scope_sub = scope.add_subparsers(dest="scope_command", metavar="ACTION")

    scope_init = scope_sub.add_parser("init", help="write a starter scope file")
    scope_init.add_argument("--path", help="where to write (default: config dir)")
    scope_init.add_argument("--holder", help="who holds the authorization")
    scope_init.add_argument("--reference", default="SELF-OWNED-ASSETS")
    scope_init.add_argument("--days", type=int, default=30,
                            help="authorization validity in days (default 30)")
    scope_init.add_argument("--force", action="store_true")

    scope_sub.add_parser("show", help="print the loaded scope")
    scope_sub.add_parser("validate", help="check the scope file parses and is live")

    scope_add = scope_sub.add_parser("add", help="add a target to the scope")
    scope_add.add_argument("targets", nargs="+",
                           help="domains, hosts, CIDRs, URLs, model endpoints "
                                "or local paths")
    scope_add.add_argument("--kind", choices=("auto", "domain", "host", "network",
                                              "url", "model", "path"),
                           default="auto")
    scope_add.add_argument("--i-own-this", action="store_true",
                           help="assert you own the target or hold written "
                                "permission to test it")

    scope_remove = scope_sub.add_parser("remove", help="remove a target")
    scope_remove.add_argument("targets", nargs="+")

    # --- config ---------------------------------------------------------
    config = sub.add_parser("config", help="manage model/provider configuration")
    config_sub = config.add_subparsers(dest="config_command", metavar="ACTION")
    config_sub.add_parser("show", help="print effective configuration")
    config_set = config_sub.add_parser("set", help="set a config value")
    config_set.add_argument("key", choices=("provider", "model", "base_url",
                                            "org", "native_tools", "temperature",
                                            "max_tokens", "max_agent_steps",
                                            "request_interval", "stream",
                                            "api_key_env"))
    config_set.add_argument("value")
    config_sub.add_parser("providers", help="list provider backends")
    config_offline = config_sub.add_parser(
        "use-offline", help="run with no model at all (deterministic tools only)")
    config_offline.add_argument("--off", action="store_true",
                                help="switch back to openai-compat")

    # --- scan -----------------------------------------------------------
    scan = sub.add_parser(
        "scan", help="run assessment tools directly (no model required)")
    scan.add_argument("target", help="URL, host, domain, path or model endpoint")
    scan.add_argument("--tools", default="auto",
                      help="comma list, or 'auto' (default), 'web', 'quick'")
    scan.add_argument("--active", action="store_true",
                      help="permit the rate-limited TCP service-discovery tool")
    scan.add_argument("--ports", help="port spec for ports_audit, e.g. 22,80,443")
    scan.add_argument("--offline", action="store_true",
                      help="skip tools needing third-party advisory/CT services")
    scan.add_argument("--interval", type=float, default=0.4,
                      help="seconds between requests (default 0.4)")
    scan.add_argument("--timeout", type=float, default=15.0)
    scan.add_argument("--report", metavar="DIR", help="also write reports to DIR")
    scan.add_argument("--narrate", action="store_true",
                      help="ask the configured model to summarise the results")
    scan.add_argument("--model", help="override the configured model id")
    scan.add_argument("--base-url", help="override the configured endpoint")

    # --- ask / chat -----------------------------------------------------
    ask = sub.add_parser("ask", help="one-shot natural-language assessment")
    ask.add_argument("goal", nargs="+", help="what you want assessed")
    ask.add_argument("--context", help="extra context for the model")
    ask.add_argument("--active", action="store_true")
    ask.add_argument("--steps", type=int, help="max agent steps")
    ask.add_argument("--report", metavar="DIR")
    ask.add_argument("--offline", action="store_true",
                     help="force the offline provider (no model call)")
    ask.add_argument("--model", help="override the configured model id")
    ask.add_argument("--base-url", help="override the configured endpoint")
    ask.add_argument("--provider", choices=PROVIDER_KINDS,
                     help="override the configured provider kind")
    ask.add_argument("--interval", type=float, default=0.4,
                     help="seconds between outbound requests (default 0.4)")
    ask.add_argument("--timeout", type=float, default=15.0,
                     help="per-request timeout in seconds")

    chat = sub.add_parser("chat", help="interactive assessment session")
    chat.add_argument("--active", action="store_true")
    chat.add_argument("--steps", type=int)
    chat.add_argument("--report", metavar="DIR")
    chat.add_argument("--offline", action="store_true")
    chat.add_argument("--model")
    chat.add_argument("--base-url")
    chat.add_argument("--interval", type=float, default=0.4)
    chat.add_argument("--timeout", type=float, default=15.0)

    # --- llm-audit ------------------------------------------------------
    llm = sub.add_parser(
        "llm-audit",
        help="test the safety controls of an LLM endpoint YOU operate")
    llm.add_argument("endpoint", help="base URL of your inference endpoint")
    llm.add_argument("--model", required=True, help="model id to send")
    llm.add_argument("--probes", help="comma list of probe ids (default: all)")
    llm.add_argument("--system-prompt", help="the system prompt you deploy")
    llm.add_argument("--max-tokens", type=int, default=400)
    llm.add_argument("--report", metavar="DIR")
    llm.add_argument("--api-key", help="prefer SENTINEL_LLM_API_KEY")
    llm.add_argument("--interval", type=float, default=0.4)
    llm.add_argument("--timeout", type=float, default=60.0)

    # --- audit-log ------------------------------------------------------
    log = sub.add_parser("audit-log", help="inspect the authorization decision log")
    log.add_argument("--path", help="default: $SENTINEL_AUDIT_LOG or "
                                    "~/.local/state/sentinel/audit.jsonl")
    log.add_argument("--denied-only", action="store_true")
    log.add_argument("--tail", type=int, default=40)

    return parser


# --------------------------------------------------------------------- main


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    ui = UI()
    if args.no_color:
        ui.color = False

    if not args.command:
        parser.print_help()
        _print_first_run_hint(ui)
        return 0

    try:
        return _dispatch(args, ui, parser)
    except ScopeError as exc:
        ui.error(str(exc))
        ui.info("run `sentinel scope init` then `sentinel scope add <asset-you-own>`")
        return 2
    except ProviderError as exc:
        ui.error(str(exc))
        ui.info("run `sentinel doctor` to diagnose the provider configuration")
        return 3
    except KeyboardInterrupt:
        ui.line("")
        ui.warn("interrupted")
        return 130


def _dispatch(args: argparse.Namespace, ui: UI,
              parser: argparse.ArgumentParser) -> int:
    handlers = {
        "doctor": cmd_doctor, "rules": cmd_rules, "tools": cmd_tools,
        "probes": cmd_probes, "scope": cmd_scope, "config": cmd_config,
        "scan": cmd_scan, "ask": cmd_ask, "chat": cmd_chat,
        "llm-audit": cmd_llm_audit, "audit-log": cmd_audit_log,
    }
    handler = handlers.get(args.command)
    if handler is None:
        parser.print_help()
        return 0
    return handler(args, ui)


# ------------------------------------------------------------------ plumbing


def _load(args: argparse.Namespace, required: bool = True) -> Scope | None:
    return load_scope(getattr(args, "scope", None), required=required)


def _context(scope: Scope | None, args: argparse.Namespace,
             ui: UI) -> tuple[Guard, ToolContext]:
    guard = Guard(scope, audit_log=default_audit_log())
    ctx = ToolContext(
        guard=guard, scope=scope,
        limiter=RateLimiter(float(getattr(args, "interval", 0.4) or 0.4)),
        timeout=float(getattr(args, "timeout", 15.0) or 15.0),
        offline=bool(getattr(args, "offline", False)),
        allow_active=bool(getattr(args, "active", False)),
        on_progress=None if getattr(args, "json", False) else ui.spinner_text,
    )
    return guard, ctx


def _provider(args: argparse.Namespace, ui: UI) -> Provider:
    config = Config.load()
    if getattr(args, "provider", None):
        config.provider = args.provider
    if getattr(args, "model", None):
        config.model = args.model
    if getattr(args, "base_url", None):
        config.base_url = args.base_url
    if getattr(args, "offline", False):
        return OfflineProvider()
    return config.build_provider()


def _print_first_run_hint(ui: UI) -> None:
    ui.line("")
    ui.rule(label="first run")
    ui.info("1. sentinel scope init                     # create your authorization file")
    ui.info("2. sentinel scope add my-app.test --i-own-this")
    ui.info("3. sentinel config set model <id>          # or: sentinel config use-offline")
    ui.info("4. sentinel scan https://my-app.test")
    ui.info("5. sentinel ask \"audit my app's HTTP security and summarise\"")
    ui.line("")
    ui.info("Only add assets you own or hold written permission to test.")


# ------------------------------------------------------------------ commands


def cmd_rules(args: argparse.Namespace, ui: UI) -> int:
    text = RULES_DOC.format(
        ports=" ".join(str(p) for p in sorted(PROTECTED_PORTS)),
        domains=", ".join(PROTECTED_DOMAIN_PATTERNS),
        fragments=", ".join(PROTECTED_HOST_FRAGMENTS),
        providers=", ".join(PROTECTED_PROVIDER_PATTERNS),
    )
    if args.json:
        print(json.dumps({
            "protected_ports": sorted(PROTECTED_PORTS),
            "protected_domain_patterns": list(PROTECTED_DOMAIN_PATTERNS),
            "protected_host_fragments": list(PROTECTED_HOST_FRAGMENTS),
            "protected_providers": list(PROTECTED_PROVIDER_PATTERNS),
        }, indent=2))
        return 0
    ui.heading("Hard prohibitions")
    ui.line(text)
    ui.info("These are constants in sentinel/authz.py. A scope file cannot "
            "override them, and neither can a prompt.")
    return 0


def cmd_tools(args: argparse.Namespace, ui: UI) -> int:
    registry = build_registry()
    if getattr(args, "tools_json", False):
        print(json.dumps([{"name": t.name, "active": t.active,
                           "description": t.description, "schema": t.schema}
                          for t in registry.all()], indent=2))
        return 0
    ui.heading("Assessment tools")
    rows = []
    for tool in registry.all():
        rows.append([tool.name, "ACTIVE" if tool.active else "passive",
                     tool.kind, tool.description.splitlines()[0][:70]])
    ui.table(["tool", "mode", "target kind", "purpose"], rows)
    ui.line("")
    ui.info("ACTIVE tools additionally require --active and an in-scope host. "
            "They open TCP connections only; no tool sends a payload.")
    return 0


def cmd_probes(args: argparse.Namespace, ui: UI) -> int:
    catalog = probe_catalog()
    if getattr(args, "probes_json", False):
        print(json.dumps(catalog, indent=2))
        return 0
    ui.heading("LLM safety probes (OWASP Top 10 for LLM Applications)")
    rows = [[p["owasp"], p["id"], p["severity"], p["title"][:60]]
            for p in catalog]
    ui.table(["owasp", "probe id", "if failed", "what it tests"], rows)
    ui.line("")
    ui.info("Every probe uses a benign canary token. None asks a model to "
            "produce harmful content, and nothing a model returns is executed.")
    return 0


def cmd_doctor(args: argparse.Namespace, ui: UI) -> int:
    ui.heading("Sentinel doctor")
    config = Config.load()
    ui.kv("config file", config.source)
    ui.kv("provider", config.provider)
    ui.kv("model", config.model or "(none)")
    ui.kv("base url", config.base_url or "(provider default)")
    ui.kv("native tools", "yes" if config.native_tools else "no (text protocol)")
    ui.kv("api key set", "yes" if config.api_key() else "NO")

    ui.line("")
    ui.rule(label="scope")
    scope_path = Path(args.scope).expanduser() if getattr(args, "scope", None) \
        else default_scope_path()
    ui.kv("scope file", str(scope_path))
    scope = None
    if scope_path.exists():
        try:
            scope = Scope.load(scope_path)
            ui.ok(authorization_banner(scope))
            ui.kv("domains", ", ".join(scope.domains) or "-")
            ui.kv("hosts", ", ".join(scope.hosts) or "-")
            ui.kv("networks", ", ".join(scope.networks) or "-")
            ui.kv("urls", ", ".join(scope.urls) or "-")
            ui.kv("model endpoints", ", ".join(scope.model_endpoints) or "-")
            ui.kv("local paths", ", ".join(scope.local_paths) or "-")
            if scope.is_empty():
                ui.warn("scope lists no targets - every network tool will refuse")
            if scope.authorization.is_expired():
                ui.error("authorization EXPIRED - renew it in writing")
        except ScopeError as exc:
            ui.error(str(exc))
    else:
        ui.warn("no scope file - run `sentinel scope init`")

    ui.line("")
    ui.rule(label="guard")
    ui.kv("audit log", str(default_audit_log()))
    guard = Guard(scope, audit_log=None)
    samples = ["https://example.com", "10.0.0.5", "localhost",
               "scada.internal", "1.1.1.1"]
    if scope:
        samples = scope.domains[:2] + scope.hosts[:2] + samples[:2]
    rows = []
    for sample in samples[:6]:
        decision = guard.check(sample, kind="url")
        rows.append([sample[:34], "ALLOW" if decision.allowed else "DENY",
                     decision.rule, decision.reason[:44]])
    ui.table(["sample target", "verdict", "rule", "reason"], rows)
    guard.decisions.clear()

    if not args.skip_provider:
        ui.line("")
        ui.rule(label="provider")
        try:
            provider = config.build_provider()
            if isinstance(provider, OfflineProvider):
                ui.ok("offline provider - no network calls will be made")
            else:
                ui.info(f"probing {provider.name}:{provider.model} ...")
                ui.ok(provider.probe())
        except ProviderError as exc:
            ui.error(str(exc))
            ui.info("set SENTINEL_MODEL / SENTINEL_BASE_URL / SENTINEL_API_KEY, "
                    "or run `sentinel config use-offline` to use the tools "
                    "without a model")
            return 3
    return 0


def cmd_scope(args: argparse.Namespace, ui: UI) -> int:
    action = getattr(args, "scope_command", None)
    if not action:
        ui.error("choose an action: init | show | add | remove | validate")
        return 2

    path = Path(args.scope).expanduser() if getattr(args, "scope", None) \
        else default_scope_path()

    if action == "init":
        destination = Path(args.path).expanduser() if args.path else path
        if destination.exists() and not args.force:
            ui.error(f"{destination} already exists (use --force to overwrite)")
            return 2
        import datetime as _dt
        template = blank_scope(args.holder or "")
        template["authorization"]["reference"] = args.reference
        today = utcnow().date()
        template["authorization"]["issued"] = today.isoformat()
        template["authorization"]["expires"] = (
            (today + _dt.timedelta(days=args.days)).isoformat() + "T23:59:59+00:00")
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(json.dumps(template, indent=2) + "\n",
                               encoding="utf-8")
        try:
            destination.chmod(0o600)
        except OSError:
            pass
        ui.ok(f"wrote {destination}")
        ui.info("Now add ONLY assets you own or hold written permission to test:")
        ui.info(f"  sentinel scope add my-app.test --i-own-this")
        ui.info("Self-signed permission is not permission. If you do not own the "
                "asset, use its published bug-bounty or VDP program instead.")
        return 0

    if action == "show":
        scope = Scope.load(path)
        if args.json:
            print(json.dumps(scope.to_dict(), indent=2))
            return 0
        ui.heading("Scope")
        ui.kv("file", scope.source or str(path))
        ui.kv("name", scope.name)
        ui.kv("banner", authorization_banner(scope))
        ui.line("")
        rows = []
        for kind, values in (("domain", scope.domains), ("host", scope.hosts),
                             ("network", scope.networks), ("url", scope.urls),
                             ("model", scope.model_endpoints),
                             ("path", scope.local_paths)):
            for value in values:
                rows.append([kind, value])
        ui.table(["kind", "target"], rows or [["-", "(none)"]])
        return 0

    if action == "validate":
        try:
            scope = Scope.load(path)
        except ScopeError as exc:
            ui.error(str(exc))
            return 2
        problems = []
        if scope.authorization.is_expired():
            problems.append("authorization expired")
        if not scope.authorization.expires:
            problems.append("no expiry set - an open-ended authorization is bad "
                            "practice")
        if scope.is_empty():
            problems.append("no targets listed")
        guard = Guard(scope, audit_log=None)
        for kind, values in (("domain", scope.domains), ("host", scope.hosts),
                             ("url", scope.urls), ("model", scope.model_endpoints)):
            for value in values:
                decision = guard.check(value, kind=kind)
                if not decision.allowed:
                    problems.append(f"{value} -> {decision.rule}: {decision.reason}")
        if problems:
            ui.warn(f"{len(problems)} problem(s) in {path}")
            for problem in problems:
                ui.error(problem)
            return 1
        ui.ok(f"{path} is valid and live")
        return 0

    if action in ("add", "remove"):
        scope = Scope.load(path) if path.exists() else Scope.from_dict(
            blank_scope(), source=str(path))
        field_of = {"domain": "domains", "host": "hosts", "network": "networks",
                    "url": "urls", "model": "model_endpoints", "path": "local_paths"}

        if action == "add" and not args.i_own_this:
            ui.line("")
            ui.warn("Before adding anything, be certain of one of these:")
            ui.info("  - you own the asset, or")
            ui.info("  - you hold written permission naming you and this asset, or")
            ui.info("  - it is covered by a bug-bounty/VDP program whose scope "
                    "includes it and whose rules you have read.")
            ui.info("If none of those is true, do not add it and do not scan it.")
            if not prompt_yes_no(
                    "  Do you own these targets or hold written permission to "
                    "test them?", default=False):
                ui.refuse("nothing added")
                return 2

        added: list[str] = []
        refusals = 0
        for raw in args.targets:
            target = raw.strip()
            if not target:
                continue
            kind = args.kind
            if kind == "auto":
                kind = _guess_kind(target)
            field = field_of.get(kind)
            if not field:
                ui.error(f"cannot classify {target!r}; pass --kind explicitly")
                continue
            if action == "add":
                blocked = Guard(None).prohibited(target)
                if blocked and blocked.startswith("shared-hosting:"):
                    # Your own subdomain on a shared platform: passive audit is
                    # legitimate, active probing is not. Add it, say so.
                    getattr(scope, field).append(target)                         if target not in getattr(scope, field) else None
                    added.append(f"{kind}:{target}")
                    ui.warn(f"{target} is on shared hosting "
                            f"({blocked.split(':', 1)[1]}). Passive audits "
                            f"(headers, TLS, DNS) are allowed; active port "
                            f"probing will always be refused, because the host "
                            f"answering belongs to the platform.")
                    continue
                if blocked:
                    ui.refuse(f"{target} -> {blocked}")
                    ui.info("This is a hard prohibition. No scope file can "
                            "override it, so it was not added.")
                    refusals += 1
                    continue
                if target in getattr(scope, field):
                    ui.info(f"{target} already in scope.{field}")
                    continue
                getattr(scope, field).append(target)
                added.append(f"{kind}:{target}")
            else:
                if target in getattr(scope, field):
                    getattr(scope, field).remove(target)
                    added.append(f"-{kind}:{target}")
                else:
                    ui.warn(f"{target} was not in scope.{field}")

        scope.save(path)
        if args.json:
            print(json.dumps({"changed": added, "path": str(path)}, indent=2))
        else:
            for entry in added:
                ui.ok(entry)
            ui.info(f"saved {path}")
        return 1 if refusals else 0

    ui.error(f"unknown scope action {action!r}")
    return 2


def _guess_kind(target: str) -> str:
    text = target.strip()
    if "/" in text and not text.startswith("/"):
        return "url"
    if text.startswith("/") or text.startswith(".") or text.startswith("~"):
        return "path"
    if ":" in text and not text.startswith("["):
        head = text.split("://")[0]
        if any(head.endswith(suffix) for suffix in (":11434", ":8000", ":8080",
                                                    ":1234", ":5000")):
            return "model"
    if "/" in text and "." not in text.split("/")[0]:
        return "network"
    if looks_like_ip(text.split("/")[0]):
        return "network" if "/" in text else "host"
    host = text.split("://")[-1].split("/")[0].split(":")[0]
    if looks_like_domain(host):
        return "domain"
    if looks_like_hostname(host):
        return "host"
    return "path"


def cmd_config(args: argparse.Namespace, ui: UI) -> int:
    action = getattr(args, "config_command", None) or "show"
    config = Config.load()

    if action == "show":
        if args.json:
            print(json.dumps(config.describe(), indent=2))
            return 0
        ui.heading("Configuration")
        for key, value in config.describe().items():
            ui.kv(key, value)
        ui.line("")
        ui.info(f"file: {config_path()}  (API keys are never stored here - they "
                f"come from the environment)")
        return 0

    if action == "providers":
        ui.heading("Provider backends")
        rows = [
            ["openai-compat", "any base_url speaking the OpenAI protocol",
             "OpenAI, Azure, Groq, Together, OpenRouter, Fireworks, Cerebras, "
             "vLLM, TGI, llama.cpp, LM Studio, LiteLLM, private gateways"],
            ["anthropic", "Messages API", "Claude models, or a proxy"],
            ["ollama", "local", "any model pulled into Ollama"],
            ["offline", "no network", "deterministic tools only, no narration"],
        ]
        ui.table(["kind", "protocol", "works with"], rows)
        ui.line("")
        ui.info("Point at a private API with:")
        ui.info("  export SENTINEL_PROVIDER=openai-compat")
        ui.info("  export SENTINEL_BASE_URL=https://llm-gateway.internal/v1")
        ui.info("  export SENTINEL_MODEL=<whatever the gateway serves>")
        ui.info("  export SENTINEL_API_KEY=<credential>")
        return 0

    if action == "set":
        key, value = args.key, args.value
        field_types = {"native_tools": bool, "stream": bool, "temperature": float,
                       "max_tokens": int, "max_agent_steps": int,
                       "request_interval": float, "timeout": float}
        caster = field_types.get(key, str)
        try:
            if caster is bool:
                value = value.strip().lower() in ("1", "true", "yes", "on")
            else:
                value = caster(value)
        except ValueError:
            ui.error(f"{value!r} is not a valid {caster.__name__} for {key}")
            return 2
        setattr(config, key, value)
        path = config.save()
        ui.ok(f"{key} = {value!r}")
        ui.info(f"saved {path}")
        return 0

    if action == "use-offline":
        config.provider = "openai-compat" if args.off else "offline"
        path = config.save()
        ui.ok(f"provider = {config.provider}")
        ui.info(f"saved {path}")
        if not args.off:
            ui.info("Offline mode runs every deterministic tool and prints "
                    "results without any model call. Good for air-gapped or "
                    "CI use.")
        return 0

    ui.error(f"unknown config action {action!r}")
    return 2


TOOL_PRESETS = {
    "quick": ["http_audit", "tls_audit"],
    "web": ["http_audit", "tls_audit", "dns_audit", "surface_audit"],
    "auto": None,          # decided per target kind
    "repo": ["deps_audit", "secrets_audit"],
}


def _tools_for(target: str, spec: str, active: bool) -> list[str]:
    registry = build_registry()
    names = registry.names()
    if spec != "auto":
        wanted = [s.strip() for s in spec.split(",") if s.strip()]
        unknown = [w for w in wanted if w not in names]
        if unknown:
            raise ValueError(f"unknown tool(s): {', '.join(unknown)}; "
                             f"available: {', '.join(names)}")
        return wanted
    preset = TOOL_PRESETS.get("auto")
    kind = _guess_kind(target)
    if kind == "path":
        chosen = ["secrets_audit", "deps_audit"]
    elif kind in ("domain", "host", "url"):
        chosen = ["http_audit", "tls_audit", "dns_audit", "surface_audit"]
        if kind == "host":
            chosen = ["tls_audit", "dns_audit"]
    elif kind == "model":
        chosen = []
    elif kind == "network":
        chosen = ["dns_audit"]
    else:
        chosen = ["http_audit", "tls_audit"]
    if active:
        chosen.append("ports_audit")
    return [c for c in chosen if c in names]


def cmd_scan(args: argparse.Namespace, ui: UI) -> int:
    scope = _load(args)
    guard, ctx = _context(scope, args, ui)
    registry = build_registry()

    if not scope:
        ui.error("no scope loaded")
        ui.info("sentinel scope init && sentinel scope add <asset-you-own> "
                "--i-own-this")
        return 2

    ui.heading(f"Scan: {args.target}")
    ui.info(authorization_banner(scope))
    if args.active:
        ui.warn("--active: TCP service discovery is permitted for in-scope hosts")

    try:
        selected = _tools_for(args.target, args.tools, args.active)
    except ValueError as exc:
        ui.error(str(exc))
        return 2

    if not selected:
        ui.error(f"no tools apply to {args.target!r}")
        ui.info("for an LLM endpoint use `sentinel llm-audit`; for a directory "
                "use `sentinel scan .`")
        return 2

    results = []
    for name in selected:
        tool = registry.get(name)
        if tool is None:
            continue
        arguments = _scan_arguments(name, args)
        ui.clear_line()
        ui.line("  " + ui.paint(name, BOLD_ON))
        result = registry.execute(name, arguments, ctx)
        results.append(result)
        ui.clear_line()
        if result.refused:
            ui.refuse(f"{name}: {result.error}")
        elif not result.ok:
            ui.error(f"{name}: {result.error}")
        else:
            ui.ok(f"{name}: {len(result.findings)} finding(s) in "
                  f"{result.duration_ms}ms")
            ui.findings(sort_findings(result.findings), limit=25)
        ui.line("")

    counts = severity_counts(results)
    ui.rule(label="result")
    ui.counts(counts)

    from .agent import AgentRun
    run = AgentRun(goal=f"scan {args.target}", results=results,
                   provider="(none)" if not args.narrate else "configured",
                   model="")
    if args.narrate:
        provider = _provider(args, ui)
        if isinstance(provider, OfflineProvider):
            ui.info("offline provider - skipping narration")
        else:
            ui.line("")
            ui.rule(label="narration")
            agent = Agent(provider, registry, ctx, max_steps=1,
                          stream=False)
            agent.registry = _EmptyRegistry()
            narrated = agent.run(
                "Summarise these assessment results. Do not call any tools; the "
                "scan is already complete. Report only what the data supports.\n\n"
                + json.dumps([r.to_dict() for r in results], default=str)[:24000])
            run.final_text = narrated.final_text
            run.provider = provider.name
            run.model = provider.model
            ui.line(narrated.final_text)

    ui.line("")
    ui.line(console_summary(run, guard))

    if args.report:
        paths = write_reports(run, scope, guard, args.report,
                              basename=_safe_name(args.target))
        ui.line("")
        ui.ok(f"markdown report: {paths['markdown']}")
        ui.ok(f"json report:     {paths['json']}")
    if args.json:
        print(json.dumps([r.to_dict() for r in results], indent=2, default=str))
    return 0 if not any(r.refused for r in results) or results else 1


class _EmptyRegistry:
    """Narration must not be able to call tools - the scan is already done."""

    def specs(self, include_active: bool = True) -> list:
        return []

    def all(self) -> list:
        return []

    def names(self) -> list:
        return []

    def execute(self, name: str, arguments: dict, ctx: Any) -> Any:
        raise RuntimeError("narration is not permitted to call tools")


def _scan_arguments(name: str, args: argparse.Namespace) -> dict[str, Any]:
    target = args.target
    if name == "ports_audit":
        payload: dict[str, Any] = {"target": target}
        if args.ports:
            payload["ports"] = args.ports
        return payload
    if name == "llm_audit":
        return {"target": target, "model": args.model or ""}
    if name in ("deps_audit", "secrets_audit"):
        return {"target": target}
    if name == "http_audit":
        return {"target": target, "method": "GET"}
    return {"target": target}


def cmd_ask(args: argparse.Namespace, ui: UI) -> int:
    scope = _load(args)
    guard, ctx = _context(scope, args, ui)
    registry = build_registry()
    config = Config.load()
    if args.steps:
        config.max_agent_steps = args.steps

    goal = " ".join(args.goal).strip()
    provider = _provider(args, ui)

    if not args.json:
        ui.heading("Sentinel")
        ui.info(authorization_banner(scope))
        ui.info(f"model: {provider.name}:{provider.model}  "
                f"max steps: {config.max_agent_steps}")
        ui.line("")

    tokens: list[str] = []

    def on_token(piece: str) -> None:
        tokens.append(piece)
        sys.stdout.write(piece)
        sys.stdout.flush()

    def on_event(kind: str, payload: dict[str, Any]) -> None:
        if args.json:
            return
        ui.clear_line()
        if kind == "tool_call":
            name = payload.get("name")
            arguments = json.dumps(payload.get("arguments") or {}, default=str)
            ui.info(f"-> {name} {arguments[:110]}")
        elif kind == "tool_result":
            state = "REFUSED" if payload.get("refused") else (
                "error" if not payload.get("ok") else "ok")
            ui.info(f"<- {payload.get('name')} {state} "
                    f"({payload.get('findings')} findings, "
                    f"worst={payload.get('worst')})")
        elif kind == "protocol_fallback":
            ui.warn(f"native tool-calling unavailable, using the text protocol "
                    f"({payload.get('reason','')[:80]})")
        elif kind == "error":
            ui.error(str(payload.get("error"))[:300])

    agent = Agent(provider, registry, ctx,
                  max_steps=config.max_agent_steps,
                  temperature=config.temperature,
                  max_tokens=config.max_tokens,
                  stream=config.stream and not args.json,
                  on_token=on_token, on_event=on_event)
    run = agent.run(goal, extra_context=args.context or "")

    if tokens and not args.json:
        ui.line("")

    if run.error and not run.final_text:
        ui.error(run.error)

    if args.json:
        print(json.dumps(run.to_dict(), indent=2, default=str))
    else:
        # The answer is printed whether or not a report was requested; writing
        # a file must not swallow the result the operator asked for.
        if run.final_text and not tokens:
            ui.line("")
            ui.line(run.final_text.rstrip())
        ui.line("")
        ui.rule(label="result")
        ui.counts(severity_counts(run.results))
        ui.line(console_summary(run, guard))
        if run.error:
            ui.warn(run.error)

    if args.report:
        paths = write_reports(run, scope, guard, args.report)
        ui.line("")
        ui.ok(f"markdown report: {paths['markdown']}")
        ui.ok(f"json report:     {paths['json']}")

    if run.refused_by_guard or run.refused_by_model:
        ui.line("")
        ui.info("Part of this request was refused. See the authorization log "
                "with `sentinel audit-log --denied-only`.")
    return 0


def cmd_chat(args: argparse.Namespace, ui: UI) -> int:
    scope = _load(args)
    guard, ctx = _context(scope, args, ui)
    registry = build_registry()
    config = Config.load()
    if args.steps:
        config.max_agent_steps = args.steps
    provider = _provider(args, ui)

    ui.banner()
    ui.info(authorization_banner(scope))
    ui.info(f"model: {provider.name}:{provider.model}")
    ui.info("commands: /scope  /tools  /report  /active  /quit")
    ui.line("")

    history: list[Any] = []
    while True:
        try:
            line = input(ui.paint("sentinel> ", "\033[1;32m")).strip()
        except (EOFError, KeyboardInterrupt):
            ui.line("")
            break
        if not line:
            continue
        if line in ("/quit", "/exit", "/q"):
            break
        if line == "/scope":
            ui.line(authorization_banner(scope))
            continue
        if line == "/tools":
            for tool in registry.all():
                ui.info(f"{tool.name}{' [active]' if tool.active else ''}")
            continue
        if line == "/active":
            ctx.allow_active = not ctx.allow_active
            ui.warn(f"active probing {'ENABLED' if ctx.allow_active else 'disabled'}")
            continue
        if line.startswith("/report"):
            parts = line.split(maxsplit=1)
            directory = parts[1] if len(parts) > 1 else "reports"
            from .agent import AgentRun
            run = AgentRun(goal="chat session", results=[
                r for h in history for r in h.results])
            paths = write_reports(run, scope, guard, directory)
            ui.ok(f"{paths['markdown']}")
            continue

        agent = Agent(provider, registry, ctx,
                      max_steps=config.max_agent_steps,
                      temperature=config.temperature,
                      max_tokens=config.max_tokens,
                      stream=config.stream,
                      on_token=lambda piece: (sys.stdout.write(piece),
                                              sys.stdout.flush()),
                      on_event=_chat_event(ui))
        run = agent.run(line)
        history.append(run)
        ui.line("")
        ui.line(console_summary(run, guard))
        ui.line("")
    return 0


def _chat_event(ui: UI):
    def handler(kind: str, payload: dict[str, Any]) -> None:
        ui.clear_line()
        if kind == "tool_call":
            ui.info(f"-> {payload.get('name')} "
                    f"{json.dumps(payload.get('arguments') or {})[:100]}")
        elif kind == "tool_result":
            state = "REFUSED" if payload.get("refused") else (
                "error" if not payload.get("ok") else "ok")
            ui.info(f"<- {payload.get('name')} {state}")
        elif kind == "error":
            ui.error(str(payload.get("error"))[:200])
    return handler


def cmd_llm_audit(args: argparse.Namespace, ui: UI) -> int:
    scope = _load(args)
    guard, ctx = _context(scope, args, ui)
    registry = build_registry()

    if not scope:
        ui.error("no scope loaded")
        return 2

    ui.heading("LLM safety audit")
    ui.info(authorization_banner(scope))
    ui.info(f"endpoint: {args.endpoint}")
    ui.info(f"model:    {args.model}")
    ui.line("")
    ui.warn("Confirm this endpoint is one you operate, or one you have written "
            "permission to evaluate.")
    ui.info("Sentinel sends benign canary probes only. It never asks the model "
            "to produce harmful content, and it never executes anything the "
            "model returns.")
    if not os.environ.get("SENTINEL_ASSUME_AUTHORIZED") and \
            not prompt_yes_no("  Do you operate this endpoint or hold written "
                              "permission to evaluate it?", default=False):
        ui.refuse("nothing sent")
        return 2

    arguments: dict[str, Any] = {
        "target": args.endpoint, "model": args.model,
        "max_tokens": args.max_tokens,
    }
    if args.probes:
        arguments["probes"] = [p.strip() for p in args.probes.split(",")]
    if args.system_prompt:
        arguments["system_prompt"] = args.system_prompt
    if args.api_key:
        arguments["api_key"] = args.api_key

    result = registry.execute("llm_audit", arguments, ctx)
    if result.refused:
        ui.refuse(result.error or "")
        ui.info("Add the endpoint with: sentinel scope add "
                f"{args.endpoint} --kind model --i-own-this")
        return 2
    if not result.ok:
        ui.error(result.error or "audit failed")

    data = result.data
    ui.line("")
    ui.rule(label="controls")
    ui.kv("probes run", data.get("probes_run", 0))
    ui.kv("controls failed", data.get("controls_failed", 0))
    ui.kv("controls held", data.get("controls_held", 0))
    if data.get("transport_errors"):
        ui.warn(f"transport errors: {len(data['transport_errors'])}")
        for error in data["transport_errors"][:5]:
            ui.info(str(error)[:160])
    ui.line("")
    ui.findings(sort_findings(result.findings), limit=40)

    from .agent import AgentRun
    run = AgentRun(goal=f"llm-audit {args.endpoint} ({args.model})",
                   results=[result], provider="n/a", model="n/a")
    if args.report:
        paths = write_reports(run, scope, guard, args.report,
                              basename="llm-audit")
        ui.line("")
        ui.ok(f"markdown report: {paths['markdown']}")
        ui.ok(f"json report:     {paths['json']}")
    if args.json:
        print(json.dumps(result.to_dict(), indent=2, default=str))
    return 0 if not data.get("controls_failed") else 1


def cmd_audit_log(args: argparse.Namespace, ui: UI) -> int:
    path = Path(args.path).expanduser() if args.path else default_audit_log()
    if not path.exists():
        ui.info(f"no audit log yet at {path}")
        return 0
    entries: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            entry = json.loads(line)
        except json.JSONDecodeError:
            continue
        if args.denied_only and entry.get("allowed"):
            continue
        entries.append(entry)
    tail = entries[-args.tail:]
    if args.json:
        print(json.dumps(tail, indent=2))
        return 0
    ui.heading(f"Authorization log ({len(entries)} entries, showing {len(tail)})")
    rows = [[e.get("timestamp", "")[11:19] or e.get("timestamp", "")[:19],
             "ALLOW" if e.get("allowed") else "DENY",
             str(e.get("target", ""))[:34], e.get("rule", ""),
             str(e.get("reason", ""))[:40]] for e in tail]
    ui.table(["time", "verdict", "target", "rule", "reason"], rows)
    ui.line("")
    ui.info(f"full log: {path}")
    return 0


def _safe_name(target: str) -> str:
    import re
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "-", target).strip("-")
    return (cleaned or "scan")[:60]
