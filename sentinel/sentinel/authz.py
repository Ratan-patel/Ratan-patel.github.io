"""The refusal layer.

Every network-facing tool in Sentinel routes through `Guard.check()` before it
opens a socket or issues a request. The guard enforces three things in order:

1. Hard prohibitions that no scope file can ever override (satellite/telemetry
   bands, ICS/SCADA and medical device ports, military/government TLDs, public
   infrastructure you cannot personally authorize).
2. Scope membership - the target must be inside a loaded scope.
3. Scope validity - the authorization must exist and not be expired.

Every decision, allow or deny, is appended to a JSONL audit log. That log is
the thing you hand a client or a bug-bounty program when they ask "what did you
actually touch, and when".
"""

from __future__ import annotations

import dataclasses
import datetime as _dt
import fnmatch
import ipaddress
import json
import os
import socket
from pathlib import Path
from typing import Any

from . import scope as _scope
from .scope import Scope, ScopeError, host_from_url, looks_like_ip, utcnow

# ---------------------------------------------------------------------------
# Hard prohibitions. These are NOT configurable and NOT overridable by a scope
# file, because an individual cannot grant themselves permission to touch them.
# ---------------------------------------------------------------------------

#: Ports belonging to industrial control, SCADA, medical-device and utility
#: protocols. Touching these on anything you do not physically own has caused
#: real-world harm (power grids, hospital equipment), so they are blocked flat.
PROTECTED_PORTS: frozenset[int] = frozenset(
    {
        102,     # ISO-TSAP / S7comm (Siemens PLC)
        1801,    # MQSeries
        2000,    # COTP / some SCADA stacks
        2404,    # IEC 60870-5-104 (power grid telecontrol)
        4000, 4001, 4002,  # ICCP / utility inter-control comms
        44818,   # EtherNet/IP (CIP)
        47808,   # BACnet (building automation)
        50100, 50110, 50200,  # proprietary ICS
        502,     # Modbus
        4840, 4843,  # OPC-UA
        10101, 10102,  # utility telemetry
        7171, 7172,  # GE/Siemens industrial
        11111, 20000, 20001,  # DNP3 / industrial
        3109, 3110,  # IEC 61850 (substation automation)
        9004, 9005,  # medical device / hospital integration engines
        10443, 10444,  # pacemaker/implant programmer comms
        161, 162,    # SNMP - read is fine elsewhere, but not via an agent probe
        8291,    # MikroTik router management
        9100,    # raw printer / JetDirect (used for worm propagation)
        11211,   # memcached (amplification abuse vector)
        1900,    # SSDP (amplification abuse vector)
        389, 636,  # LDAP - directory writes are out of scope for a read-only agent
        123,     # NTP (amplification abuse vector)
        53,      # DNS zone probing belongs in dns_audit, not a port scan
        25, 465, 587,  # SMTP - mail relays are a spam/abuse vector
        623,     # IPMI/BMC - out-of-band server management
        5900, 5901, 5902,  # VNC
        3389,    # RDP
        23, 2323,  # Telnet
        21,      # FTP
    }
)

#: TLDs and host patterns belonging to military, government and international
#: treaty bodies. Bug-bounty programs and government VDPs exist for these; an
#: unattended agent has no business pointing at them.
PROTECTED_DOMAIN_PATTERNS: tuple[str, ...] = (
    "*.mil", "*.int", "*.gov", "*.gov.*",
    "*.mod", "*.gouv.*", "*.go.*", "*.gov.in",
    "mil.*", "*.army", "*.navy", "*.airforce", "*.spaceforce",
    "*.nato.int", "*.esa.int", "*.europa.eu",
)

#: Hostname fragments that identify critical-infrastructure, financial-core,
#: aviation, space and emergency-services systems.
PROTECTED_HOST_FRAGMENTS: tuple[str, ...] = (
    "scada", "ics.", ".ics", "plc", "hmi", "substation", "grid-", "-grid",
    "satellite", "satcom", "groundstation", "ground-station", "ttc-",
    "telecommand", "telemetry", "uplink", "downlink",
    "airspace", "airtraffic", "atc-", "flightrad", "adsb", "ads-b",
    "swiftnet", "core-banking", "swift.", "rtgs", "neft",
    "emergency", "e911", "911.", "112.", "dispatch",
    "nuclear", "reactor", "powerplant", "water-treatment", "wtp-",
    "hospital-pacs", "dicom", "pacsv", "infusion-pump",
    "election", "evm", "voting-machine", "ballot",
    "rail-signalling", "etcs", "cbtc", "interlocking",
)

#: IP ranges that are public infrastructure or otherwise not personally
#: authorizable by an individual operator.
PROTECTED_NETWORKS: tuple[str, ...] = (
    "0.0.0.0/8",          # this-network
    "100.64.0.0/10",      # CGNAT - shared with strangers
    "169.254.0.0/16",     # link-local
    "192.0.0.0/24",       # IETF protocol assignments
    "192.0.2.0/24",       # TEST-NET-1
    "192.88.99.0/24",     # 6to4 relay anycast
    "198.18.0.0/15",      # benchmarking
    "198.51.100.0/24",    # TEST-NET-2
    "203.0.113.0/24",     # TEST-NET-3
    "224.0.0.0/4",        # multicast
    "240.0.0.0/4",        # reserved / future use
    "255.255.255.255/32", # broadcast
    "2001:db8::/32",      # documentation
    "fe80::/10",          # link-local v6
    "ff00::/8",           # multicast v6
    "::/128", "::1/128",  # unspecified / loopback v6 handled separately
    "fc00::/7",           # ULA
)

PROTECTED_HOSTNAMES: frozenset[str] = frozenset(
    {
        "localhost", "broadcasthost", "ip6-localhost", "ip6-loopback",
        "root-servers.net", "a.root-servers.net", "b.root-servers.net",
        "c.root-servers.net", "d.root-servers.net", "e.root-servers.net",
        "f.root-servers.net", "g.root-servers.net", "h.root-servers.net",
        "i.root-servers.net", "j.root-servers.net", "k.root-servers.net",
        "l.root-servers.net", "m.root-servers.net",
    }
)

#: Well-known public API/hosting providers. You cannot authorize a scan of these
#: by writing your own scope file - that requires their written permission or an
#: in-scope program on their disclosure page. Listed at the registrable-domain
#: level so `login.microsoftonline.com` and `s3.eu-west-1.amazonaws.com` are both
#: caught, not just `www.microsoft.com`.
PROTECTED_PROVIDER_PATTERNS: tuple[str, ...] = (
    # hyperscalers and their asset/API domains
    "*.amazonaws.com", "amazonaws.com", "*.aws.dev", "*.amazon.com",
    "*.cloudfront.net", "*.alexa.com", "*.a2z.com",
    "*.azure.com", "azure.com", "*.azure-api.net",
    "*.azureedge.net", "*.azurecr.io", "*.azurecontainer.io", "*.windows.net",
    "*.microsoft.com", "microsoft.com", "*.microsoftonline.com",
    "microsoftonline.com", "*.live.com", "*.msn.com", "*.office.com",
    "*.visualstudio.com", "*.dynamics.com", "*.bing.com", "*.skype.com",
    "*.googleapis.com", "googleapis.com", "*.google.com", "google.com",
    "*.googleusercontent.com", "*.gstatic.com", "*.youtube.com",
    "*.withgoogle.com", "*.run.app", "*.blogspot.com",
    "*.cloud.google.com",
    "*.oraclecloud.com", "*.oracle.com", "*.customer-oci.com",
    "*.ibm.com", "*.cloud.ibm.com", "*.mybluemix.net",
    "*.alibabacloud.com", "*.aliyuncs.com",
    # AI providers
    "*.openai.com", "openai.com", "*.oaistatic.com", "*.oaiusercontent.com",
    "*.chatgpt.com", "chatgpt.com",
    "*.anthropic.com", "anthropic.com", "*.claude.ai", "*.claude.site",
    "*.cohere.ai", "*.cohere.com", "*.mistral.ai", "*.huggingface.co",
    "*.replicate.com", "*.together.ai", "*.groq.com", "*.fireworks.ai",
    "*.deepinfra.com", "*.cerebras.ai", "*.perplexity.ai", "*.x.ai",
    # code hosting and CI
    "*.github.com", "github.com", "*.githubusercontent.com",
    "*.githubassets.com", "*.gitlab.com", "*.bitbucket.org", "*.atlassian.net",
    "*.atlassian.com",
    # social / consumer platforms
    "*.facebook.com", "*.fb.com", "*.facebook.net", "*.meta.com",
    "*.instagram.com", "*.whatsapp.com", "*.threads.net",
    "*.twitter.com", "*.x.com", "*.t.co", "*.pscp.tv",
    "*.linkedin.com", "*.licdn.com", "*.apple.com", "*.icloud.com",
    "*.netflix.com", "*.nflxvideo.net", "*.spotify.com", "*.discord.com",
    "*.discordapp.com", "*.slack.com", "*.zoom.us", "*.telegram.org",
    # payments and finance
    "*.stripe.com", "*.stripe.network", "*.paypal.com", "*.braintreegateway.com",
    "*.visa.com", "*.mastercard.com", "*.adyen.com", "*.checkout.com",
    # security/CDN infrastructure
    "*.cloudflare.com", "cloudflare.com", "*.cloudflareaccess.com",
    "*.akamai.net", "*.akamaized.net", "*.fastly.net", "*.fastly.com",
    "*.cdn77.org", "*.incapdns.net", "*.imperva.com",
    # SaaS whose infrastructure is not yours even if the data is
    "*.salesforce.com", "*.force.com", "*.adobe.com", "*.adobe.io",
    "*.dropbox.com", "*.box.com", "*.notion.so", "*.notion.site",
    "*.figma.com", "*.canva.com", "*.okta.com", "*.auth0.com",
    "*.duo.com", "*.datadoghq.com", "*.newrelic.com", "*.splunkcloud.com",
    "*.sendgrid.net", "*.twilio.com", "*.zendesk.com", "*.servicenow.com",
    "*.workday.com", "*.sap.com", "*.snowflakecomputing.com",
    "*.bigquery.com", "*.databricks.com", "*.mongodb.com", "*.atlas.mongodb.com",
)

#: Shared-hosting platforms that hand *you* a subdomain. A read-only audit of
#: your own subdomain there (your GitHub Pages site, your Vercel preview) is
#: normal owner behaviour, so passive tools may assess it when it is listed in
#: scope. Active probing is still refused, because the machine answering is the
#: platform's, not yours.
SHARED_HOSTING_PATTERNS: tuple[str, ...] = (
    "*.github.io", "github.io",
    "*.gitlab.io", "*.gitlab-pages.dev",
    "*.vercel.app", "*.vercel.dev", "*.now.sh",
    "*.netlify.app", "*.netlify.com",
    "*.pages.dev", "*.workers.dev",
    "*.herokuapp.com", "*.herokussl.com",
    "*.render.com", "*.onrender.com",
    "*.fly.dev", "*.railway.app", "*.ngrok.io", "*.ngrok-free.app",
    "*.azurewebsites.net", "*.firebaseapp.com", "*.web.app",
    "*.appspot.com", "*.elasticbeanstalk.com", "*.cloudfunctions.net",
    "*.surge.sh", "*.neocities.org", "*.wixsite.com", "*.wordpress.com",
    "*.medium.com", "*.substack.com", "*.ghost.io",
)


@dataclasses.dataclass(frozen=True)
class Decision:
    allowed: bool
    target: str
    kind: str
    reason: str
    rule: str = ""
    scope_name: str = ""
    timestamp: str = dataclasses.field(
        default_factory=lambda: utcnow().isoformat(timespec="seconds")
    )

    def to_dict(self) -> dict[str, Any]:
        return dataclasses.asdict(self)

    def deny(self) -> str:
        return f"REFUSED [{self.rule}]: {self.reason}"


def _in_protected_network(candidate: str) -> str | None:
    try:
        address = ipaddress.ip_address(candidate)
    except ValueError:
        return None
    for entry in PROTECTED_NETWORKS:
        try:
            if address in ipaddress.ip_network(entry, strict=False):
                return entry
        except ValueError:
            continue
    return None


def _match_patterns(host: str, patterns: tuple[str, ...]) -> str | None:
    """Case-folded glob match. `fnmatchcase` so behaviour is identical on
    Windows and POSIX.

    A `*.example.com` pattern also matches the bare apex `example.com`, so the
    block lists do not have to enumerate both forms - a gap there would be a
    real hole, not a style choice.
    """
    for pattern in patterns:
        if fnmatch.fnmatchcase(host, pattern):
            return pattern
        if pattern.startswith("*.") and host == pattern[2:]:
            return pattern
    return None


class Guard:
    """Enforces hard prohibitions, scope membership and scope validity."""

    def __init__(self, scope: Scope | None, audit_log: Path | None = None,
                 strict: bool = True) -> None:
        self.scope = scope
        self.audit_log = audit_log
        self.strict = strict
        self.decisions: list[Decision] = []
        if audit_log:
            audit_log.parent.mkdir(parents=True, exist_ok=True)

    # --------------------------------------------------------------- checks

    def prohibited(self, target: str, port: int | None = None,
                   active: bool = False) -> str | None:
        """Return the blocking rule that fires, or None if nothing does.

        `active=True` marks a tool that opens raw connections (ports_audit).
        Shared-hosting platforms are permitted for passive audits of your own
        subdomain but never for active probing - the host answering is the
        platform's, not yours.
        """
        text = (target or "").strip().lower()
        if not text:
            return "empty-target"

        if port is not None:
            try:
                port_number = int(port)
            except (TypeError, ValueError):
                return "invalid-port"
            if port_number in PROTECTED_PORTS:
                return f"protected-port:{port_number}"
            if not 1 <= port_number <= 65535:
                return "port-out-of-range"

        host = host_from_url(text) or text
        host = host.rstrip(".")

        if _in_protected_network(host):
            return f"protected-network:{_in_protected_network(host)}"

        if host in PROTECTED_HOSTNAMES:
            # localhost is permitted only when the scope explicitly lists it,
            # which is handled downstream; the hard block is on the name itself
            # appearing without scope membership.
            return "protected-hostname"

        pattern = _match_patterns(host, PROTECTED_DOMAIN_PATTERNS)
        if pattern:
            return f"protected-tld:{pattern}"

        shared = _match_patterns(host, SHARED_HOSTING_PATTERNS)
        if shared:
            if active:
                return f"shared-hosting-active:{shared}"
            return f"shared-hosting:{shared}"

        pattern = _match_patterns(host, PROTECTED_PROVIDER_PATTERNS)
        if pattern:
            return f"public-provider:{pattern}"

        for fragment in PROTECTED_HOST_FRAGMENTS:
            if fragment in host:
                return f"critical-infrastructure:{fragment}"

        return None

    def resolve(self, host: str) -> list[str]:
        """Best-effort DNS resolution used to catch scopes aimed at a friendly
        hostname that actually lives on public infrastructure."""
        try:
            infos = socket.getaddrinfo(host, None)
        except (socket.gaierror, socket.herror, OSError, UnicodeError):
            return []
        return sorted({info[4][0] for info in infos})

    def check(self, target: str, *, kind: str = "host", port: int | None = None,
              resolve: bool = False, active: bool = False) -> Decision:
        """Decide whether `target` may be touched."""
        text = (target or "").strip()
        if not text:
            return self._record(Decision(False, text, kind, "empty target", "empty-target"))

        rule = self.prohibited(text, port, active=active)

        if rule == "protected-hostname":
            # Loopback is fine when the scope says so; otherwise it is a block.
            # Compare the extracted host, not the raw target, so that
            # "http://localhost:11434" resolves to "localhost" before matching.
            bare = (host_from_url(text.lower()) or text.lower()).rstrip(".")
            if not (self.scope and (self.scope.matches_host(bare)
                                    or self.scope.matches_ip(bare))):
                return self._record(
                    Decision(False, text, kind,
                             "loopback/reserved hostname not present in scope", rule)
                )
            rule = None

        # A shared-hosting subdomain you own is a legitimate passive-audit
        # target; it still has to be listed in scope, so fall through to the
        # normal membership checks instead of denying here.
        shared_hosting = rule is not None and rule.startswith("shared-hosting:")

        if rule and not shared_hosting:
            return self._record(
                Decision(False, text, kind, self._explain(rule), rule,
                         self.scope.name if self.scope else "")
            )
        if rule and shared_hosting:
            rule = None

        if resolve and not looks_like_ip(text):
            host = host_from_url(text) or text
            for address in self.resolve(host):
                blocked = _in_protected_network(address)
                if blocked:
                    return self._record(
                        Decision(False, text, kind,
                                 f"{host} resolves to protected range {blocked}",
                                 f"protected-network:{blocked}",
                                 self.scope.name if self.scope else "")
                    )
                pattern = _match_patterns(address, PROTECTED_PROVIDER_PATTERNS)
                if pattern:
                    return self._record(
                        Decision(False, text, kind,
                                 f"{host} resolves into {pattern}",
                                 f"public-provider:{pattern}",
                                 self.scope.name if self.scope else "")
                    )

        if self.scope is None:
            return self._record(
                Decision(False, text, kind,
                         "no scope loaded - run `sentinel scope init` then add the "
                         "assets you own or hold written permission to test",
                         "no-scope")
            )

        if self.scope.authorization.is_expired():
            left = self.scope.authorization.days_left()
            return self._record(
                Decision(False, text, kind,
                         f"authorization '{self.scope.authorization.reference}' "
                         f"expired ({left} days ago) - renew the engagement in "
                         f"writing before continuing",
                         "expired-authorization", self.scope.name)
            )

        if self.scope.is_empty():
            return self._record(
                Decision(False, text, kind,
                         f"scope '{self.scope.name}' lists no targets",
                         "empty-scope", self.scope.name)
            )

        if self._in_scope(text, kind):
            return self._record(
                Decision(True, text, kind, "in scope", "allow", self.scope.name)
            )

        return self._record(
            Decision(False, text, kind,
                     f"'{text}' is not listed in scope '{self.scope.name}'. "
                     f"If you own it or hold written permission, add it with "
                     f"`sentinel scope add`; otherwise do not touch it.",
                     "out-of-scope", self.scope.name)
        )

    def _in_scope(self, text: str, kind: str) -> bool:
        assert self.scope is not None
        lowered = text.lower()
        if kind == "path":
            return self.scope.matches_path(text)
        if kind == "model":
            return self.scope.matches_model_endpoint(text)
        if kind == "url":
            return self.scope.matches_url(text)
        if kind == "port-scan":
            host = host_from_url(lowered) or lowered
            return (self.scope.matches_domain(host) or self.scope.matches_host(host)
                    or self.scope.matches_ip(host))
        host = host_from_url(lowered) or lowered
        if looks_like_ip(host):
            return self.scope.matches_ip(host) or self.scope.matches_host(host)
        return (self.scope.matches_domain(host) or self.scope.matches_host(host)
                or self.scope.matches_url(lowered))

    def _explain(self, rule: str) -> str:
        kind, _, detail = rule.partition(":")
        if kind == "protected-port":
            return (
                f"port {detail} belongs to industrial-control / SCADA / medical / "
                f"out-of-band management protocols. Sentinel never probes these."
            )
        if kind == "protected-network":
            return f"{detail} is reserved or shared public address space."
        if kind == "protected-tld":
            return (
                f"'{detail}' is a military/government/international-treaty domain. "
                f"Use that organisation's published VDP or bug-bounty program instead."
            )
        if kind == "public-provider":
            return (
                f"'{detail}' is third-party public infrastructure. Scanning it "
                f"requires the provider's own written permission or an in-scope "
                f"disclosure program - not a self-signed scope file."
            )
        if kind == "shared-hosting-active":
            return (
                f"'{detail}' is a shared-hosting platform. You may passively audit "
                f"your own subdomain there, but the machine answering an active "
                f"probe belongs to the platform, so active probing is refused."
            )
        if kind == "critical-infrastructure":
            return (
                f"target looks like critical infrastructure ('{detail}'). "
                f"This class of system is never probed by Sentinel."
            )
        if kind == "port-out-of-range":
            return "port number outside 1-65535."
        if kind == "invalid-port":
            return "port must be an integer."
        return rule

    # ------------------------------------------------------------- auditing

    def _record(self, decision: Decision) -> Decision:
        self.decisions.append(decision)
        if self.audit_log:
            try:
                with self.audit_log.open("a", encoding="utf-8") as handle:
                    handle.write(json.dumps(decision.to_dict()) + "\n")
            except OSError:
                pass
        return decision

    def summary(self) -> dict[str, int]:
        allowed = sum(1 for d in self.decisions if d.allowed)
        return {"total": len(self.decisions), "allowed": allowed,
                "denied": len(self.decisions) - allowed}


# ---------------------------------------------------------------------------


def default_audit_log() -> Path:
    override = os.environ.get("SENTINEL_AUDIT_LOG")
    if override:
        return Path(override).expanduser()
    base = Path(os.environ.get("XDG_STATE_HOME", "~/.local/state")).expanduser()
    return base / "sentinel" / "audit.jsonl"


def load_scope(path: str | os.PathLike[str] | None = None,
               *, required: bool = True) -> Scope | None:
    """Load a scope file, returning None (or raising) when unavailable."""
    location = Path(path).expanduser() if path else _scope.default_scope_path()
    try:
        loaded = Scope.load(location)
    except ScopeError:
        if required:
            raise
        return None
    return loaded


def authorization_banner(scope: Scope | None) -> str:
    if scope is None:
        return "NO SCOPE LOADED - all network tools are disabled"
    auth = scope.authorization
    left = auth.days_left()
    state = "EXPIRED" if auth.is_expired() else (
        f"{left}d left" if left is not None else "no expiry"
    )
    return (
        f"scope={scope.name!r} holder={auth.holder!r} ref={auth.reference!r} "
        f"granted_by={auth.granted_by!r} status={state}"
    )


def assert_valid(scope: Scope | None) -> None:
    """Raise unless a scope exists and its authorization is live."""
    if scope is None:
        raise ScopeError("no scope loaded")
    if scope.authorization.is_expired():
        raise ScopeError(
            f"authorization '{scope.authorization.reference}' expired on "
            f"{scope.authorization.expires:%Y-%m-%d}"
        )
    if scope.is_empty():
        raise ScopeError(f"scope '{scope.name}' has no targets listed")


def _dt_iso(value: _dt.datetime | None) -> str | None:
    return value.isoformat() if value else None
