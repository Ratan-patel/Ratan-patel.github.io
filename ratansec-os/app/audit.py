"""Audit log — har executed command aur important event yahan record hota hai.

File: data/audit.jsonl (append-only). Memory me last 500 events bhi rehte hain
taaki UI jaldi dikha sake. Public deploy par ye evidence ka kaam karta hai.
"""

from __future__ import annotations

import json
import threading
import time
from collections import deque
from pathlib import Path
from typing import Any

from .config import settings

_lock = threading.Lock()
_recent: deque[dict[str, Any]] = deque(maxlen=500)
_audit_file: Path = settings.data_dir / "audit.jsonl"


def log(event: str, **fields: Any) -> dict[str, Any]:
    """Ek audit event likho. Kabhi exception nahi raise karta."""
    record: dict[str, Any] = {"ts": time.time(), "event": event, **fields}
    with _lock:
        _recent.append(record)
        try:
            with _audit_file.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps(record, ensure_ascii=False, default=str) + "\n")
        except OSError:
            pass
    return record


def recent(limit: int = 100) -> list[dict[str, Any]]:
    with _lock:
        items = list(_recent)
    return list(reversed(items))[: max(1, min(limit, 500))]
