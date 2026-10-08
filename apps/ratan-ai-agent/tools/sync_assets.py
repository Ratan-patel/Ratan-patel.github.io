#!/usr/bin/env python3
"""Bundle the AIRT scanner page into the agent app.

    python3 apps/ratan-ai-agent/tools/sync_assets.py          # copy
    python3 apps/ratan-ai-agent/tools/sync_assets.py --check  # verify only (CI)

The offline red-team toolkit inside RATAN AI AGENT 2.0 is *the same artefact* the standalone
scanner ships: `tools/ai-redteam-scanner/mobile.html`, which `gen_mobile.py` regenerates from
the Python corpus. Copying rather than forking means the app can never drift from the CLI
payload set — and CI fails if the two ever disagree.
"""

from __future__ import annotations

import hashlib
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
APP_DIR = os.path.dirname(HERE)
REPO_ROOT = os.path.dirname(os.path.dirname(APP_DIR))

SOURCE = os.path.join(REPO_ROOT, "tools", "ai-redteam-scanner", "mobile.html")
TARGET = os.path.join(APP_DIR, "android", "app", "src", "main", "assets", "toolkit.html")

# Cheap sanity markers: if any of these disappear the source page is not what we think it is.
REQUIRED_MARKERS = ("AirTBridge", "AIRT", "owasp", "LLM01")


def read(path: str) -> str:
    with open(path, encoding="utf-8") as handle:
        return handle.read()


def digest(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def main(argv: list[str]) -> int:
    check_only = "--check" in argv

    if not os.path.exists(SOURCE):
        print(f"error: {SOURCE} is missing", file=sys.stderr)
        print("hint: run  python3 tools/ai-redteam-scanner/gen_mobile.py", file=sys.stderr)
        return 2

    source = read(SOURCE)
    for marker in REQUIRED_MARKERS:
        if marker not in source:
            print(f"error: marker {marker!r} not found in {SOURCE}; refusing to bundle",
                  file=sys.stderr)
            return 2

    if check_only:
        if not os.path.exists(TARGET):
            print(f"error: {TARGET} is missing", file=sys.stderr)
            return 2
        bundled = read(TARGET)
        if digest(bundled) != digest(source):
            print("error: bundled toolkit.html differs from tools/ai-redteam-scanner/mobile.html",
                  file=sys.stderr)
            print("hint: python3 apps/ratan-ai-agent/tools/sync_assets.py", file=sys.stderr)
            return 3
        print(f"toolkit.html in sync ({len(source) / 1024:.1f} KB, sha256 {digest(source)[:16]}…)")
        return 0

    os.makedirs(os.path.dirname(TARGET), exist_ok=True)
    with open(TARGET, "w", encoding="utf-8") as handle:
        handle.write(source)
    print(f"toolkit.html <= {os.path.relpath(SOURCE, REPO_ROOT)}"
          f" ({len(source) / 1024:.1f} KB, sha256 {digest(source)[:16]}…)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
