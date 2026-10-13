"""Tool registry. Import this to get a fully populated Registry."""

from __future__ import annotations

from .base import (Finding, RateLimiter, Registry, Tool, ToolContext, ToolResult,
                   severity_counts, sort_findings)
from .deps_audit import DepsAudit
from .dns_audit import DnsAudit
from .http_audit import HttpAudit
from .llm_audit import LlmAudit, probe_catalog
from .ports_audit import PortsAudit
from .surface_audit import SurfaceAudit
from .tls_audit import TlsAudit
from .secrets_audit import SecretsAudit


def build_registry() -> Registry:
    registry = Registry()
    for tool in (HttpAudit(), TlsAudit(), DnsAudit(), DepsAudit(),
                 SecretsAudit(), SurfaceAudit(), PortsAudit(), LlmAudit()):
        registry.register(tool)
    return registry


__all__ = [
    "Finding", "RateLimiter", "Registry", "Tool", "ToolContext", "ToolResult",
    "build_registry", "probe_catalog", "severity_counts", "sort_findings",
    "HttpAudit", "TlsAudit", "DnsAudit", "DepsAudit", "SecretsAudit",
    "SurfaceAudit", "PortsAudit", "LlmAudit",
]
