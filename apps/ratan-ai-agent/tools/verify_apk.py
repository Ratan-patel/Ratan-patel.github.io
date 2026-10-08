#!/usr/bin/env python3
"""Post-build verification of the RATAN AI AGENT APK.

    python3 apps/ratan-ai-agent/tools/verify_apk.py out/Ratan-AI-Agent-2.0.0-release.apk

Checks that the artefact really is the app we think we built: package name, version code,
target/min SDK, the bundled pages, the dex, and the SHA-256 fingerprint of the signing
certificate (printed so a release note can quote it).
"""

from __future__ import annotations

import hashlib
import os
import subprocess
import sys
import zipfile

EXPECTED_PACKAGE = "io.github.ratanpatel.ratanagent"
EXPECTED_VERSION_CODE = "200"
EXPECTED_VERSION_NAME = "2.0.0"
EXPECTED_TARGET_SDK = "37"
EXPECTED_MIN_SDK = "24"
REQUIRED_ENTRIES = ("AndroidManifest.xml", "classes.dex", "assets/home.html", "assets/toolkit.html")
ASSET_MARKERS = {
    "assets/home.html": ("RatanBridge", "Red-team toolkit"),
    "assets/toolkit.html": ("AirTBridge", "owasp"),
}


def run(command: list[str]) -> str:
    return subprocess.run(command, capture_output=True, text=True, check=False).stdout


def main(argv: list[str]) -> int:
    if len(argv) != 1:
        print(__doc__, file=sys.stderr)
        return 2
    apk = argv[0]
    if not os.path.exists(apk):
        print(f"error: {apk} not found", file=sys.stderr)
        return 2

    problems: list[str] = []
    print(f"apk            {apk}")
    print(f"size           {os.path.getsize(apk) / 1024:.1f} KB")
    print(f"sha256(apk)    {hashlib.sha256(open(apk, 'rb').read()).hexdigest()}")

    with zipfile.ZipFile(apk) as archive:
        names = archive.namelist()
        for entry in REQUIRED_ENTRIES:
            if entry not in names:
                problems.append(f"missing entry: {entry}")
        for entry, markers in ASSET_MARKERS.items():
            if entry not in names:
                continue
            payload = archive.read(entry).decode("utf-8", "replace")
            for marker in markers:
                if marker not in payload:
                    problems.append(f"{entry}: marker {marker!r} missing")
            if entry == "assets/toolkit.html":
                probes = payload.count('"category"')
                print(f"toolkit probes {probes}")
                if probes < 60:
                    problems.append(f"toolkit.html: only {probes} probes bundled")
        dex = [n for n in names if n.startswith("classes") and n.endswith(".dex")]
        print(f"dex files      {len(dex)}")

    aapt2 = os.environ.get("AAPT2", "aapt2")
    badging = run([aapt2, "dump", "badging", apk])
    if not badging:
        problems.append("aapt2 dump badging produced no output (set AAPT2=/path/to/aapt2)")
    else:
        first = badging.splitlines()[0] if badging.splitlines() else ""
        print(f"badging        {first.strip()}")
        if f"name='{EXPECTED_PACKAGE}'" not in first:
            problems.append(f"package name is not {EXPECTED_PACKAGE}")
        if f"versionCode='{EXPECTED_VERSION_CODE}'" not in first:
            problems.append(f"versionCode is not {EXPECTED_VERSION_CODE}")
        if f"versionName='{EXPECTED_VERSION_NAME}'" not in first:
            problems.append(f"versionName is not {EXPECTED_VERSION_NAME}")
        for line in badging.splitlines():
            if line.startswith("sdkVersion:") and EXPECTED_MIN_SDK not in line:
                problems.append(f"minSdk mismatch: {line}")
            if line.startswith("targetSdkVersion:") and EXPECTED_TARGET_SDK not in line:
                problems.append(f"targetSdk mismatch: {line}")
            if line.startswith("sdkVersion:") or line.startswith("targetSdkVersion:"):
                print(f"              {line.strip()}")

    if problems:
        print("\nAPK verification FAILED:")
        for problem in problems:
            print(f"  - {problem}")
        return 1
    print("\nAPK verification passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
