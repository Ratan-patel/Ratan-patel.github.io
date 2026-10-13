"""Rate-limited TCP service-discovery on hosts you own.

This is the one tool that actively opens connections, so it carries the most
restrictions in the package:

  * requires `--active` (ctx.allow_active) *and* a scope entry for the host
  * refuses every port in authz.PROTECTED_PORTS - ICS/SCADA, medical, IPMI,
    telnet, RDP, VNC, SMTP, NTP, SNMP, DNS, memcached, SSDP and friends are
    never touched, whatever the scope file says
  * default port list is 24 common service ports, not a full 1-65535 sweep
  * hard rate limit (default 2 connections/second) and a connection ceiling
  * connect-only: it completes the TCP handshake and closes. No banner grab by
    default, no protocol interaction, no credential attempt, no payload.

If you need more than this, use nmap against a range you own, with a written
authorization in hand. An agent should not be improvising that.
"""

from __future__ import annotations

import ipaddress
import json
import select
import socket
import time
from typing import Any

from ..authz import PROTECTED_PORTS
from ..scope import host_from_url
from .base import Finding, Tool, ToolContext, ToolResult

#: The default list. Common services a developer actually runs.
DEFAULT_PORTS: tuple[int, ...] = (
    21, 22, 53, 80, 110, 143, 443, 465, 587, 993, 995,
    3000, 3306, 5432, 5672, 6379, 8000, 8080, 8443, 8888,
    9090, 9200, 11211, 15672, 27017,
)

#: Ports that are always refused, even with --active, because a connect attempt
#: against them is either an abuse vector or an industrial-control protocol.
ALWAYS_REFUSED = PROTECTED_PORTS

SERVICE_NAMES: dict[int, str] = {
    21: "ftp", 22: "ssh", 23: "telnet", 25: "smtp", 53: "dns", 80: "http",
    110: "pop3", 111: "rpcbind", 135: "msrpc", 139: "netbios-ssn", 143: "imap",
    443: "https", 445: "microsoft-ds", 465: "smtps", 587: "submission",
    993: "imaps", 995: "pop3s", 1433: "mssql", 1521: "oracle",
    2049: "nfs", 2375: "docker", 2376: "docker-tls", 3000: "dev-server",
    3128: "squid", 3306: "mysql", 3389: "rdp", 4444: "metasploit-default",
    5000: "flask/upnp", 5432: "postgresql", 5601: "kibana", 5672: "amqp",
    5900: "vnc", 5984: "couchdb", 6379: "redis", 6443: "kubernetes-api",
    7001: "weblogic", 8000: "http-alt", 8008: "http-alt", 8009: "ajp13",
    8080: "http-proxy", 8081: "http-alt", 8086: "influxdb", 8443: "https-alt",
    8888: "http-alt", 9000: "http-alt/php-fpm", 9090: "prometheus",
    9200: "elasticsearch", 9300: "elasticsearch-transport",
    10000: "webmin", 10250: "kubelet", 10255: "kubelet-readonly",
    11211: "memcached", 15672: "rabbitmq-mgmt", 27017: "mongodb",
    27018: "mongodb-shard", 50000: "sap",
}

#: Services that should never be listening on a public interface.
INTERNAL_ONLY = {
    2375: "Docker daemon (unauthenticated = root on the host)",
    6379: "Redis (historically unauthenticated, writable)",
    9200: "Elasticsearch (no auth by default)",
    27017: "MongoDB (no auth by default before 4.x)",
    5432: "PostgreSQL",
    3306: "MySQL/MariaDB",
    5672: "AMQP/RabbitMQ broker",
    11211: "memcached (also a DDoS amplification vector)",
    6443: "Kubernetes API server",
    10250: "kubelet (authenticated exec into pods)",
    10255: "kubelet read-only port",
    9090: "Prometheus (metrics leak service topology)",
    5601: "Kibana",
    15672: "RabbitMQ management console",
    8086: "InfluxDB",
    5984: "CouchDB",
    10000: "Webmin",
    3128: "Squid proxy (open-proxy risk)",
    4444: "Default Metasploit handler port - unexpected on a server you run",
    7001: "WebLogic (frequent deserialization target)",
    8009: "AJP13 (Ghostcat)",
    9300: "Elasticsearch transport (cluster-join port)",
}


def parse_ports(spec: Any) -> list[int]:
    """Parse "22,80,443,8000-8010" into a sorted list, dropping protected ports."""
    if spec is None:
        return [p for p in DEFAULT_PORTS if p not in ALWAYS_REFUSED]
    if isinstance(spec, int):
        return [] if spec in ALWAYS_REFUSED else [spec]
    if isinstance(spec, (list, tuple)):
        out: list[int] = []
        for item in spec:
            out += parse_ports(item)
        return sorted(set(out))
    text = str(spec).strip()
    if not text:
        return [p for p in DEFAULT_PORTS if p not in ALWAYS_REFUSED]
    ports: list[int] = []
    for piece in text.replace(";", ",").split(","):
        piece = piece.strip()
        if not piece:
            continue
        if "-" in piece:
            low, _, high = piece.partition("-")
            try:
                start, stop = int(low), int(high)
            except ValueError:
                continue
            if stop < start:
                start, stop = stop, start
            stop = min(stop, start + 2000)      # ceiling on any single range
            ports += [p for p in range(start, stop + 1) if p not in ALWAYS_REFUSED]
        else:
            try:
                value = int(piece)
            except ValueError:
                continue
            if value not in ALWAYS_REFUSED:
                ports.append(value)
    return sorted({p for p in ports if 1 <= p <= 65535})


class PortsAudit(Tool):
    name = "ports_audit"
    description = (
        "Rate-limited TCP service discovery on a host you own and that is listed "
        "in your scope. Requires the --active flag. Completes a handshake and "
        "closes - no banner grab, no protocol interaction, no credential "
        "attempt. Protected ports (ICS/SCADA, medical, IPMI, telnet, RDP, VNC, "
        "SMTP, NTP, SNMP, DNS, memcached, SSDP) are always refused."
    )
    kind = "port-scan"
    active = True
    schema = {
        "type": "object",
        "properties": {
            "target": {"type": "string",
                       "description": "Host or IP in scope that you own."},
            "ports": {
                "type": "string",
                "description": "Comma list / range, e.g. '22,80,443' or "
                               "'8000-8010'. Default: 24 common service ports.",
            },
            "max_ports": {"type": "integer",
                          "description": "Hard cap on ports probed. Default 200."},
            "rate_per_second": {
                "type": "number",
                "description": "Connections per second. Clamped to 1-10. Default 2.",
            },
            "grab_banner": {
                "type": "boolean",
                "description": "Read (never send) the first bytes a service "
                               "volunteers on connect. Default false.",
            },
        },
        "required": ["target"],
    }

    MAX_RATE = 10.0

    def run(self, args: dict[str, Any], ctx: ToolContext) -> ToolResult:
        target = str(args.get("target") or "").strip()
        host = host_from_url(target) or target

        ports = parse_ports(args.get("ports"))
        max_ports = int(args.get("max_ports") or 200)
        refused_ports = self._requested_but_protected(args.get("ports"))
        if len(ports) > max_ports:
            ports = ports[:max_ports]

        decision = self.authorize(ctx, host)
        if not decision.allowed:
            return ctx.refuse(self.name, host, decision.reason, decision.rule)

        if not ports:
            return ToolResult(
                tool=self.name, target=host, ok=False, refused=True,
                error=f"every requested port is on the protected list "
                      f"({sorted(refused_ports)}); none were probed",
                findings=[Finding(
                    title="Requested ports are protected",
                    severity="info",
                    detail=f"Refused: {sorted(refused_ports)}. These belong to "
                           f"industrial-control, medical, out-of-band management "
                           f"or abuse-amplification protocols.",
                    remediation="Sentinel never probes them. If you genuinely "
                                "operate such a system, assess it with tooling "
                                "and procedures specific to that environment.",
                    evidence={"refused_ports": sorted(refused_ports)},
                )],
                data={"ports_probed": 0, "open": [],
                      "protected_ports_refused": sorted(refused_ports)},
            )

        rate = min(max(float(args.get("rate_per_second") or 2.0), 0.2), self.MAX_RATE)
        interval = 1.0 / rate
        grab = bool(args.get("grab_banner", False))

        open_ports: list[dict[str, Any]] = []
        closed = 0
        filtered = 0
        started = time.monotonic()
        timeout = min(max(ctx.timeout, 1.0), 8.0)

        for port in ports:
            ctx.limiter.wait()
            ctx.log(f"ports: {host}:{port}")
            state, banner = self._probe(host, port, timeout, grab)
            if state == "open":
                entry: dict[str, Any] = {
                    "port": port, "state": state,
                    "service": SERVICE_NAMES.get(port, ""),
                }
                if banner:
                    entry["banner"] = banner[:200]
                open_ports.append(entry)
            elif state == "closed":
                closed += 1
            else:
                filtered += 1
            # honour the rate limit without double-sleeping on the limiter
            remaining = interval - (time.monotonic() - started) % interval
            if remaining > 0 and remaining < interval:
                time.sleep(min(remaining, interval))

        findings = self._analyse(host, open_ports, refused_ports)
        elapsed = int((time.monotonic() - started) * 1000)
        return ToolResult(
            tool=self.name, target=host, ok=True, findings=findings,
            data={
                "ports_probed": len(ports),
                "open": open_ports,
                "closed": closed,
                "filtered": filtered,
                "rate_per_second": rate,
                "banner_grab": grab,
                "protected_ports_refused": sorted(refused_ports),
                "elapsed_ms": elapsed,
                "note": "TCP connect-only. No protocol interaction was performed.",
            },
            duration_ms=elapsed,
        )

    # ------------------------------------------------------------- internals

    @staticmethod
    def _requested_but_protected(spec: Any) -> list[int]:
        if spec is None:
            return []
        raw: list[int] = []
        if isinstance(spec, (int,)):
            raw = [spec]
        elif isinstance(spec, (list, tuple)):
            for item in spec:
                raw += PortsAudit._requested_but_protected(item)
            return raw
        else:
            text = str(spec)
            for piece in text.replace(";", ",").split(","):
                piece = piece.strip()
                if "-" in piece:
                    low, _, high = piece.partition("-")
                    try:
                        start, stop = int(low), min(int(high), int(low) + 2000)
                    except ValueError:
                        continue
                    raw += list(range(start, stop + 1))
                else:
                    try:
                        raw.append(int(piece))
                    except ValueError:
                        continue
        return sorted({p for p in raw if p in ALWAYS_REFUSED})

    @staticmethod
    def _probe(host: str, port: int, timeout: float,
               grab: bool) -> tuple[str, str | None]:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        try:
            result = sock.connect_ex((host, port))
        except (socket.gaierror, socket.herror, UnicodeError):
            return "unresolved", None
        except (socket.timeout, TimeoutError):
            return "filtered", None
        except OSError:
            return "closed", None
        if result == 0:
            banner: str | None = None
            if grab:
                try:
                    ready, _, _ = select.select([sock], [], [], min(timeout, 2.0))
                    if ready:
                        chunk = sock.recv(256)
                        banner = chunk.decode("utf-8", "replace").strip() or None
                except (OSError, socket.timeout, TimeoutError, UnicodeDecodeError):
                    banner = None
            try:
                sock.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
            sock.close()
            return "open", banner
        sock.close()
        # ECONNREFUSED vs EHOSTUNREACH/ETIMEDOUT
        if result in (111, 10061):
            return "closed", None
        if result in (110, 113, 10060, 10065):
            return "filtered", None
        return "closed", None

    def _analyse(self, host: str, open_ports: list[dict[str, Any]],
                 refused: list[int]) -> list[Finding]:
        out: list[Finding] = []
        if not open_ports:
            out.append(Finding(
                title="No TCP services answered",
                severity="info",
                detail=f"{host} refused or filtered every probed port.",
                remediation="Expected for a host behind a firewall or with no "
                            "listening services.",
            ))
            return out

        is_public = not _is_private_address(host)

        for entry in open_ports:
            port = entry["port"]
            service = entry.get("service") or "unknown"
            if port in INTERNAL_ONLY:
                severity = "critical" if is_public else "medium"
                out.append(Finding(
                    title=f"{service} (tcp/{port}) reachable"
                          + (" from a public interface" if is_public else ""),
                    severity=severity,
                    detail=INTERNAL_ONLY[port]
                           + (" The host resolved to a non-private address, so this "
                              "service is likely internet-facing." if is_public else
                              " The host is on a private range, so exposure is "
                              "limited to that network - still worth restricting."),
                    remediation=f"Bind {service} to 127.0.0.1 or a private "
                                f"interface, or front it with mTLS/authentication "
                                f"and a firewall rule. Never expose this port "
                                f"publicly.",
                    evidence=entry,
                ))
            elif port in (21, 23, 139, 445, 135, 3389, 5900):
                out.append(Finding(
                    title=f"Legacy remote-access protocol tcp/{port} ({service})",
                    severity="high" if is_public else "medium",
                    detail=f"{service} is in use. These protocols are weakly "
                           f"authenticated or cleartext and are heavily scanned.",
                    remediation="Replace with SSH/HTTPS-based access and place it "
                                "behind a VPN or zero-trust gateway.",
                    evidence=entry,
                ))
            elif port in (80, 8080, 8000, 8008, 8081, 8888, 3000, 5000, 9000):
                out.append(Finding(
                    title=f"Plain-HTTP service on tcp/{port}",
                    severity="medium" if is_public else "info",
                    detail=f"{service} is serving without TLS on this port.",
                    remediation="Serve HTTPS and redirect or reject plain HTTP.",
                    evidence=entry,
                ))
            else:
                out.append(Finding(
                    title=f"tcp/{port} open ({service})",
                    severity="info",
                    detail="Service answered a TCP handshake.",
                    remediation="Confirm this port is meant to be reachable from "
                                "where it is reachable.",
                    evidence=entry,
                ))

        if len(open_ports) > 8 and is_public:
            out.append(Finding(
                title=f"{len(open_ports)} services exposed on a public host",
                severity="high",
                detail="Every listening service is attack surface. Ports found: "
                       + ", ".join(str(e["port"]) for e in open_ports),
                remediation="Reduce to the minimum set, default-deny inbound at "
                            "the firewall, and put the rest behind a VPN.",
            ))
        if refused:
            out.append(Finding(
                title="Protected ports were requested and refused",
                severity="info",
                detail=f"Sentinel did not probe: {sorted(refused)}.",
                remediation="These protocols require environment-specific "
                            "assessment procedures, not an automated connect scan.",
            ))
        return out


def _is_private_address(host: str) -> bool:
    try:
        address = ipaddress.ip_address(host)
    except ValueError:
        try:
            resolved = socket.gethostbyname(host)
            address = ipaddress.ip_address(resolved)
        except (socket.gaierror, socket.herror, ValueError, OSError, UnicodeError):
            return False
    return address.is_private or address.is_loopback or address.is_link_local
