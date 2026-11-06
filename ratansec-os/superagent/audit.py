"""Audit + evidence — append-only, hash-chained JSONL.

Do files banti hain:
  data/superagent/audit.jsonl       -> har event (login, command, approval, report...)
  data/superagent/evidence/evidence.log -> chain-of-custody (kaun, kab, kya, hash)

Har record me `prev` (pichhla hash) hota hai, isliye beech ka record badalne par
chain toot jaati hai — `verify()` se check kar sakte ho.
"""

from __future__ import annotations

import hashlib
import json
import threading
import time
from collections import deque
from pathlib import Path
from typing import Any

from .settings import settings

_lock = threading.Lock()
_recent: deque[dict[str, Any]] = deque(maxlen=1000)
AUDIT_FILE: Path = settings.data_dir / "audit.jsonl"
EVIDENCE_FILE: Path = settings.evidence_dir / "evidence.log"
_last_hash: dict[str, str] = {}


def _canonical(payload: dict[str, Any]) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str)


def _tail_hash(path: Path) -> str:
    if not path.is_file():
        return "genesis"
    try:
        with path.open("rb") as fh:
            fh.seek(0, 2)
            size = fh.tell()
            fh.seek(max(0, size - 4096))
            chunk = fh.read().decode("utf-8", "replace")
        for line in reversed(chunk.splitlines()):
            if line.strip():
                return json.loads(line).get("hash", "genesis")
    except (OSError, json.JSONDecodeError):
        pass
    return "genesis"


def _append(path: Path, record: dict[str, Any]) -> str:
    key = str(path)
    prev = _last_hash.get(key) or _tail_hash(path)
    body = {k: v for k, v in record.items() if k != "hash"}
    digest = hashlib.sha256((prev + _canonical(body)).encode("utf-8")).hexdigest()
    record = {**body, "prev": prev, "hash": digest}
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(record, ensure_ascii=False, default=str) + "\n")
    except OSError:
        pass
    _last_hash[key] = digest
    return digest


def log(event: str, *, evidence: bool = False, **fields: Any) -> dict[str, Any]:
    record: dict[str, Any] = {"ts": time.time(), "time": time.strftime("%Y-%m-%d %H:%M:%S"), "event": event, **fields}
    with _lock:
        _append(AUDIT_FILE, record)
        if evidence:
            _append(EVIDENCE_FILE, {"kind": "evidence", **record})
        _recent.append(record)
    return record


def recent(limit: int = 100) -> list[dict[str, Any]]:
    with _lock:
        items = list(_recent)
    if not items and AUDIT_FILE.is_file():
        # server restart ke baad file se padho
        lines = AUDIT_FILE.read_text(encoding="utf-8").splitlines()[-limit:]
        for line in lines:
            try:
                items.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return list(reversed(items))[:limit]


def verify(path: Path | None = None) -> dict[str, Any]:
    target = path or AUDIT_FILE
    if not target.is_file():
        return {"ok": True, "records": 0, "message": "Abhi koi record nahi."}
    prev = "genesis"
    count = 0
    for count, line in enumerate(target.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            return {"ok": False, "records": count - 1, "broken_at": count, "message": "Corrupt line mili."}
        body = {k: v for k, v in record.items() if k not in ("hash", "prev")}
        if record.get("prev") != prev:
            return {"ok": False, "records": count - 1, "broken_at": count, "message": "Chain link toota (prev hash mismatch)."}
        digest = hashlib.sha256((prev + _canonical(body)).encode("utf-8")).hexdigest()
        if record.get("hash") != digest:
            return {"ok": False, "records": count - 1, "broken_at": count, "message": "Record ka hash match nahi — tamper detected."}
        prev = digest
    return {"ok": True, "records": count, "file": str(target), "message": "Chain intact."}


def export_bundle() -> Path:
    """Evidence bundle — audit + chain verification + records ek zip me."""
    import zipfile

    stamp = time.strftime("%Y%m%d-%H%M%S")
    out = settings.evidence_dir / f"evidence-bundle-{stamp}.zip"
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as zf:
        if AUDIT_FILE.is_file():
            zf.write(AUDIT_FILE, "audit.jsonl")
        ledger = settings.roe_dir / "ledger.jsonl"
        if ledger.is_file():
            zf.write(ledger, "roe-ledger.jsonl")
        manifest = {
            "generated": time.strftime("%Y-%m-%d %H:%M:%S"),
            "audit_chain": verify(AUDIT_FILE),
            "evidence_chain": verify(EVIDENCE_FILE),
        }
        zf.writestr("manifest.json", json.dumps(manifest, indent=2))
    log("evidence_bundle", evidence=True, file=out.name)
    return out
