"""Fail-closed, hash-chained audit/evidence ledger.

A local hash chain detects accidental edits and casual tampering. It is not a
substitute for off-host append-only storage or signed timestamps; copy bundles
off-host for stronger chain-of-custody.
"""
from __future__ import annotations

import hashlib
import json
import os
import threading
import time
import zipfile
from collections import deque
from pathlib import Path
from typing import Any

from .settings import settings

_lock = threading.RLock()
_recent: deque[dict[str, Any]] = deque(maxlen=1000)
AUDIT_FILE: Path = settings.data_dir / "audit.jsonl"
EVIDENCE_FILE: Path = settings.evidence_dir / "evidence.log"
_last_hash: dict[str, str] = {}


class AuditError(RuntimeError):
    pass


def _canonical(payload: dict[str, Any]) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str)


def _tail_hash(path: Path) -> str:
    if not path.is_file():
        return "genesis"
    last = "genesis"
    with path.open("r", encoding="utf-8") as fh:
        for line in fh:
            if line.strip():
                last = json.loads(line).get("hash", "genesis")
    return last


def _redact_value(value: Any) -> Any:
    from .provider import redact
    if isinstance(value, str):
        return redact(value)
    if isinstance(value, dict):
        return {k: ("[REDACTED]" if k.lower() in {"password", "token", "api_key", "authorization", "secret"} else _redact_value(v))
                for k, v in value.items()}
    if isinstance(value, list):
        return [_redact_value(v) for v in value]
    return value


def _append(path: Path, record: dict[str, Any]) -> str:
    key = str(path)
    prev = _last_hash.get(key) or _tail_hash(path)
    body = {k: v for k, v in record.items() if k not in {"hash", "prev"}}
    digest = hashlib.sha256((prev + _canonical(body)).encode("utf-8")).hexdigest()
    record = {**body, "prev": prev, "hash": digest}
    try:
        path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        with path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(record, ensure_ascii=False, default=str) + "\n")
            fh.flush()
            os.fsync(fh.fileno())
        path.chmod(0o600)
    except OSError as exc:
        raise AuditError("Audit write failed; action refused (fail closed).") from exc
    _last_hash[key] = digest
    return digest


def log(event: str, *, evidence: bool = False, **fields: Any) -> dict[str, Any]:
    record: dict[str, Any] = {"ts": time.time(), "time": time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime()),
                              "event": event, **_redact_value(fields)}
    with _lock:
        digest = _append(AUDIT_FILE, record)
        if evidence:
            _append(EVIDENCE_FILE, {"kind": "evidence", **record})
        stored = {**record, "hash": digest}
        _recent.append(stored)
    return stored


def recent(limit: int = 100) -> list[dict[str, Any]]:
    with _lock:
        items = list(_recent)
        if not items and AUDIT_FILE.is_file():
            for line in AUDIT_FILE.read_text(encoding="utf-8").splitlines()[-limit:]:
                try:
                    items.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    return list(reversed(items))[:limit]


def verify(path: Path | None = None) -> dict[str, Any]:
    target = path or AUDIT_FILE
    if not target.is_file():
        return {"ok": True, "records": 0, "message": "No records yet."}
    prev = "genesis"
    count = 0
    try:
        for line_no, line in enumerate(target.read_text(encoding="utf-8").splitlines(), start=1):
            if not line.strip():
                return {"ok": False, "records": count, "broken_at": line_no, "message": "Blank line in ledger."}
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                return {"ok": False, "records": count, "broken_at": line_no, "message": "Corrupt ledger line."}
            body = {k: v for k, v in record.items() if k not in ("hash", "prev")}
            if record.get("prev") != prev:
                return {"ok": False, "records": count, "broken_at": line_no, "message": "Chain link mismatch."}
            digest = hashlib.sha256((prev + _canonical(body)).encode("utf-8")).hexdigest()
            if record.get("hash") != digest:
                return {"ok": False, "records": count, "broken_at": line_no, "message": "Hash mismatch — tamper detected."}
            prev = digest
            count += 1
    except OSError:
        return {"ok": False, "records": count, "message": "Ledger could not be read."}
    return {"ok": True, "records": count, "last_hash": prev, "file": str(target), "message": "Chain intact."}


def export_bundle() -> Path:
    with _lock:
        stamp = time.strftime("%Y%m%d-%H%M%S", time.gmtime())
        out = settings.evidence_dir / f"evidence-bundle-{stamp}-{os.urandom(3).hex()}.zip"
        checks = {"audit": verify(AUDIT_FILE), "evidence": verify(EVIDENCE_FILE)}
        if not all(c["ok"] for c in checks.values()):
            raise AuditError("Ledger integrity check failed; export refused.")
        with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as zf:
            for path in (AUDIT_FILE, EVIDENCE_FILE, settings.roe_dir / "ledger.jsonl"):
                if path.is_file():
                    zf.write(path, str(path.relative_to(settings.data_dir)))
            for directory in (settings.evidence_dir, settings.reports_dir, settings.missions_dir):
                for path in sorted(directory.glob("*")):
                    if path.is_file() and path != out and not path.name.endswith(".tmp"):
                        zf.write(path, str(path.relative_to(settings.data_dir)))
            manifest = {"generated_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                        "version": "2.0.0", "chains": checks,
                        "note": "Local hash chain; copy off-host for stronger custody."}
            zf.writestr("manifest.json", json.dumps(manifest, indent=2))
        out.chmod(0o600)
        log("evidence_bundle", evidence=True, file=out.name)
    return out
