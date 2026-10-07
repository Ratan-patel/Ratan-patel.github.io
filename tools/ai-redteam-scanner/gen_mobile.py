#!/usr/bin/env python3
"""Generate the single-file mobile scanner page from the Python corpus.

    python3 gen_mobile.py

Inputs
  mobile.template.html      UI shell with three placeholders
  js/engine.js              scoring + mutators (same logic as airt/scoring.py,
                            verified by tests/engine_js_test.js and the parity check)
  airt/payloads.py          the attack corpus (single source of truth)

Outputs
  mobile.html                              standalone page (open in any browser)
  android/app/src/main/assets/index.html   the same file, bundled into the APK

Re-run this after editing probes, mutations or the UI.
"""

from __future__ import annotations

import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from airt import mutators, payloads  # noqa: E402

TEMPLATE = os.path.join(HERE, "mobile.template.html")
ENGINE = os.path.join(HERE, "js", "engine.js")
OUTPUTS = [
    os.path.join(HERE, "mobile.html"),
    os.path.join(HERE, "android", "app", "src", "main", "assets", "index.html"),
]


def corpus_json() -> str:
    probes = []
    for p in payloads.ALL_PROBES:
        probes.append({
            "id": p.id, "category": p.category, "name": p.name, "prompt": p.prompt,
            "severity": p.severity, "owasp": p.owasp,
            "markers": list(p.success_markers), "regex": list(p.success_regex),
            "complianceIsFailure": p.compliance_is_failure, "noMutate": p.no_mutate,
            "tags": list(p.tags), "remediation": p.remediation,
        })
    return json.dumps(probes, ensure_ascii=False, separators=(",", ":"))


def build() -> str:
    template = open(TEMPLATE, encoding="utf-8").read()
    engine = open(ENGINE, encoding="utf-8").read()
    html = template.replace("/*__ENGINE__*/", engine, 1)
    html = html.replace("/*__CORPUS__*/[]", corpus_json(), 1)
    html = html.replace("/*__MUTATIONS__*/[]",
                        json.dumps(mutators.MUTATOR_NAMES, ensure_ascii=False), 1)
    for placeholder in ("/*__ENGINE__*/", "/*__CORPUS__*/", "/*__MUTATIONS__*/"):
        if placeholder in html:
            raise SystemExit(f"error: placeholder {placeholder} was not substituted")
    return html


def main() -> int:
    html = build()
    for path in OUTPUTS:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(html)
        print(f"wrote {os.path.relpath(path, HERE)} ({len(html) / 1024:.1f} KB)")
    print(f"corpus: {len(payloads.ALL_PROBES)} probes · mutations: {len(mutators.MUTATOR_NAMES)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
