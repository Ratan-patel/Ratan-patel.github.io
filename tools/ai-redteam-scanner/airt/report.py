"""Report writers: terminal, JSON, JSONL, SARIF 2.1.0, standalone HTML."""

from __future__ import annotations

import html
import json
import os
from datetime import datetime, timezone
from typing import Any, Dict, List

RESET = "\033[0m"
BOLD = "\033[1m"
DIM = "\033[2m"
RED = "\033[91m"
ORANGE = "\033[38;5;208m"
YELLOW = "\033[93m"
GREEN = "\033[92m"
BLUE = "\033[94m"
GREY = "\033[90m"

VERDICT_STYLE = {
    "vulnerable": (RED, "VULNERABLE"),
    "likely-vulnerable": (ORANGE, "LIKELY"),
    "inconclusive": (YELLOW, "UNCLEAR"),
    "resistant": (GREEN, "RESISTED"),
    "error": (GREY, "ERROR"),
}

GRADE_COLOUR = {"A": GREEN, "B": GREEN, "C": YELLOW, "D": ORANGE, "E": ORANGE, "F": RED}

BANNER = r"""
   _   ___ ___ _____
  /_\ |_ _| _ \_   _|    AI Red-Teaming Scanner
 / _ \ | ||   / | |      prompt injection · jailbreaks · exfil · boundaries
/_/ \_\___|_|_\ |_|      authorised testing only
"""


def supports_colour() -> bool:
    if os.getenv("NO_COLOR"):
        return False
    if os.getenv("FORCE_COLOR"):
        return True
    return bool(getattr(__import__("sys").stdout, "isatty", lambda: False)())


class Palette:
    def __init__(self, enabled: bool = True):
        self.on = enabled

    def c(self, text: str, colour: str) -> str:
        return f"{colour}{text}{RESET}" if self.on else text


def render_banner() -> str:
    return BANNER


def render_summary(summary: Dict[str, Any], results: List[Dict[str, Any]],
                   pal: Palette, max_rows: int = 25, show_responses: bool = False) -> str:
    out: List[str] = []
    c = pal.c
    tgt = summary["target"]
    out.append(c("─" * 78, GREY))
    out.append(f"{c('Target', BOLD)}      {tgt['name']}  {c('(' + tgt['kind'] + ')', GREY)}")
    if tgt.get("system_prompt"):
        out.append(f"{c('System', BOLD)}      {c('operator system prompt supplied (white-box mode)', GREY)}")
    out.append(f"{c('Requests', BOLD)}    {summary['requests']}   "
               f"{c('model calls', BOLD)} {summary['model_calls']}   "
               f"{c('est. tokens', BOLD)} ~{summary['est_tokens']}   "
               f"{c('avg latency', BOLD)} {summary['avg_latency_ms']} ms")
    out.append(f"{c('Duration', BOLD)}    {summary['duration_s']} s   "
               f"{c('refusal rate', BOLD)} {summary['refusal_rate']}%")

    counts = summary["counts"]
    out.append("")
    out.append("  ".join([
        c(f"VULNERABLE {counts['vulnerable']}", RED + BOLD),
        c(f"LIKELY {counts['likely']}", ORANGE),
        c(f"UNCLEAR {counts['inconclusive']}", YELLOW),
        c(f"RESISTED {counts['resistant']}", GREEN),
        c(f"ERROR {counts['error']}", GREY),
    ]))

    risk = summary["risk"]
    grade_col = GRADE_COLOUR.get(risk["grade"], YELLOW)
    bar_len = 32
    filled = int(round(bar_len * risk["score"] / 100.0))
    bar = c("█" * filled, grade_col) + c("░" * (bar_len - filled), GREY)
    out.append("")
    out.append(f"{c('Security Posture', BOLD)}  [{bar}]  "
               f"{c(str(risk['score']) + '/100', grade_col + BOLD)}  "
               f"{c('grade ' + risk['grade'], grade_col + BOLD)}")

    out.append("")
    out.append(c("Category breakdown", BOLD))
    for cat, stat in sorted(summary["by_category"].items(),
                            key=lambda kv: (-kv[1]["findings"], kv[0])):
        ratio = stat["findings"] / stat["total"] if stat["total"] else 0
        colour = RED if ratio >= 0.5 else ORANGE if ratio > 0 else GREEN
        label = f"{cat:<22} {stat['findings']:>2}/{stat['total']:<2} findings"
        out.append(f"  {c(label, colour)}")

    if summary.get("by_mutation") and len(summary["by_mutation"]) > 1:
        out.append("")
        out.append(c("Evasion (mutation) effectiveness", BOLD))
        for mut, stat in sorted(summary["by_mutation"].items(),
                                key=lambda kv: -kv[1]["findings"]):
            if mut == "none":
                continue
            out.append(f"  {mut:<16} {stat['findings']:>2}/{stat['total']:<2} "
                       f"{c('bypasses a naive keyword filter' if stat['findings'] else '', GREY)}")

    findings = summary["findings"]
    if findings:
        out.append("")
        out.append(c(f"Findings — top {min(max_rows, len(findings))} of {len(findings)}", BOLD))
        for idx, f in enumerate(findings[:max_rows], 1):
            colour, label = VERDICT_STYLE.get(f["verdict"], (YELLOW, f["verdict"].upper()))
            head = f"[{idx}] {f['probe_id']} · {f['name']}"
            meta = (f"severity {f['severity']}/5 · {f['owasp']} · "
                    f"{f['confidence']}% match")
            out.append("")
            out.append(f"{c(head, BOLD)}  {c(label, colour + BOLD)}  {c(meta, GREY)}")
            if f["mutation"] not in ("none", ""):
                out.append(f"    {c('mutation:', GREY)} {f['mutation']}  "
                           f"{c(f['mutation_note'], GREY)}")
            if show_responses and f.get("response"):
                snippet = f["response"].strip().replace("\n", " ")[:220]
                out.append(f"    {c('response:', GREY)} {snippet}")
        if len(findings) > max_rows:
            out.append("")
            out.append(c(f"  ... {len(findings) - max_rows} more findings in the JSON/HTML report", GREY))
    else:
        out.append("")
        out.append(c("No exploitable findings — target resisted every probe in scope.", GREEN))

    out.append("")
    out.append(c("─" * 78, GREY))
    return "\n".join(out)


def render_findings_detail(results: List[Dict[str, Any]], category: str | None = None) -> str:
    lines: List[str] = []
    for r in results:
        if category and r["category"] != category:
            continue
        if r["verdict"] not in ("vulnerable", "likely-vulnerable"):
            continue
        lines.append(f"\n### {r['probe_id']} — {r['name']}")
        lines.append(f"category={r['category']} severity={r['severity']} owasp={r['owasp']} "
                     f"verdict={r['verdict']} confidence={r['confidence']}%")
        lines.append("PROMPT:\n" + r["prompt"][:1500])
        lines.append("RESPONSE:\n" + (r["response"] or "<empty>")[:2000])
    return "\n".join(lines)


# --------------------------------------------------------------------- SARIF
def write_sarif(path: str, summary: Dict[str, Any], results: List[Dict[str, Any]]) -> str:
    rules, rule_ids = [], {}
    for r in results:
        if r["verdict"] not in ("vulnerable", "likely-vulnerable"):
            continue
        if r["probe_id"] in rule_ids:
            continue
        rule_ids[r["probe_id"]] = True
        rules.append({
            "id": r["probe_id"],
            "name": r["name"].replace(" ", ""),
            "shortDescription": {"text": r["name"]},
            "fullDescription": {"text": r.get("mutation_note") or r["category"]},
            "helpUri": "https://owasp.org/www-project-top-10-for-large-language-model-applications/",
            "properties": {"category": r["category"], "owasp": r["owasp"],
                           "security-severity": str(min(10.0, r["severity"] * 2.0))},
        })
    sarif = {
        "$schema": "https://json.schemastore.org/sarif-2.1.0.json",
        "version": "2.1.0",
        "runs": [{
            "tool": {"driver": {
                "name": "AIRT", "version": summary["version"],
                "informationUri": "https://github.com/Ratan-patel/Ratan-patel.github.io",
                "rules": rules}},
            "results": [{
                "ruleId": r["probe_id"],
                "level": "error" if r["severity"] >= 4 else "warning",
                "message": {"text": f"{r['name']} — {r['verdict']} ({r['confidence']}% match). "
                                    f"Response excerpt: {(r['response'] or '')[:300]!r}"},
                "properties": {"mutation": r["mutation"], "category": r["category"],
                               "owasp": r["owasp"], "severity": r["severity"]},
            } for r in results if r["verdict"] in ("vulnerable", "likely-vulnerable")],
        }],
    }
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(sarif, fh, indent=2)
    return path


# ---------------------------------------------------------------------- HTML
_HTML_CSS = """
:root{--bg:#0b1020;--panel:#131a2f;--line:#243055;--txt:#e7ecff;--dim:#8b97c4;
--red:#ff5c7a;--orange:#ffa64d;--yellow:#ffd166;--green:#4ade80;--blue:#69a7ff}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--txt);
font:15px/1.55 ui-sans-serif,system-ui,-apple-system,Segoe UI,Roboto,sans-serif}
.wrap{max-width:1120px;margin:0 auto;padding:32px 20px 80px}
h1{margin:0 0 4px;font-size:26px;letter-spacing:.3px}
h2{font-size:18px;margin:34px 0 12px;border-bottom:1px solid var(--line);padding-bottom:8px}
.sub{color:var(--dim);margin-bottom:24px;font-size:13px}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:12px}
.card{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:14px}
.card .k{color:var(--dim);font-size:11px;text-transform:uppercase;letter-spacing:.08em}
.card .v{font-size:22px;font-weight:650;margin-top:4px}
.gauge{display:flex;align-items:center;gap:14px;background:var(--panel);
border:1px solid var(--line);border-radius:12px;padding:16px 18px;margin:18px 0}
.bar{flex:1;height:12px;border-radius:99px;background:#1d2745;overflow:hidden}
.bar>i{display:block;height:100%;border-radius:99px}
.grade{font-size:34px;font-weight:800;line-height:1}
table{width:100%;border-collapse:collapse;font-size:13.5px}
th,td{text-align:left;padding:9px 10px;border-bottom:1px solid var(--line);vertical-align:top}
th{color:var(--dim);font-size:11px;text-transform:uppercase;letter-spacing:.06em}
tr.f:hover{background:#16203c}
.pill{display:inline-block;padding:2px 9px;border-radius:99px;font-size:11px;font-weight:650;
white-space:nowrap}
.v-vulnerable{background:rgba(255,92,122,.16);color:var(--red);border:1px solid rgba(255,92,122,.4)}
.v-likely-vulnerable{background:rgba(255,166,77,.14);color:var(--orange);border:1px solid rgba(255,166,77,.4)}
.v-inconclusive{background:rgba(255,209,102,.13);color:var(--yellow);border:1px solid rgba(255,209,102,.35)}
.v-resistant{background:rgba(74,222,128,.13);color:var(--green);border:1px solid rgba(74,222,128,.35)}
.v-error{background:rgba(139,151,196,.12);color:var(--dim);border:1px solid var(--line)}
details{background:var(--panel);border:1px solid var(--line);border-radius:12px;
padding:12px 14px;margin-bottom:10px}
summary{cursor:pointer;font-weight:600;list-style:none}
summary::-webkit-details-marker{display:none}
pre{background:#0a0f1f;border:1px solid var(--line);border-radius:8px;padding:10px;
overflow-x:auto;font-size:12.5px;white-space:pre-wrap;word-break:break-word}
.two{display:grid;grid-template-columns:1fr 1fr;gap:10px}
@media(max-width:760px){.two{grid-template-columns:1fr}}
.lbl{color:var(--dim);font-size:11px;text-transform:uppercase;letter-spacing:.07em;margin:10px 0 4px}
.toolbar{display:flex;gap:8px;flex-wrap:wrap;margin:14px 0}
.toolbar input,.toolbar select{background:var(--panel);border:1px solid var(--line);color:var(--txt);
border-radius:8px;padding:8px 10px;font-size:13px}
.note{color:var(--dim);font-size:12.5px}
.sev-5{color:var(--red)}.sev-4{color:var(--orange)}.sev-3{color:var(--yellow)}
footer{margin-top:44px;color:var(--dim);font-size:12px;border-top:1px solid var(--line);padding-top:14px}
"""

_HTML_JS = """
const rows=[...document.querySelectorAll('tr.f')];
function applyFilters(){
  const q=(document.getElementById('q').value||'').toLowerCase();
  const c=document.getElementById('cat').value;
  const m=document.getElementById('mut').value;
  rows.forEach(r=>{
    const okQ=!q||r.dataset.text.includes(q);
    const okC=!c||r.dataset.cat===c;
    const okM=!m||r.dataset.mut===m;
    r.style.display=(okQ&&okC&&okM)?'':'none';
  });
}
['q','cat','mut'].forEach(id=>document.getElementById(id).addEventListener('input',applyFilters));
applyFilters();
"""


def _esc(v: Any) -> str:
    return html.escape(str(v if v is not None else ""))


def _sev_colour(sev: int) -> str:
    return {5: "var(--red)", 4: "var(--orange)", 3: "var(--yellow)"}.get(sev, "var(--blue)")


def write_html(path: str, summary: Dict[str, Any], results: List[Dict[str, Any]],
               target_note: str = "") -> str:
    risk = summary["risk"]
    grade_colour = {"A": "var(--green)", "B": "var(--green)", "C": "var(--yellow)",
                    "D": "var(--orange)", "E": "var(--orange)", "F": "var(--red)"}.get(
        risk["grade"], "var(--yellow)")
    counts = summary["counts"]
    findings = summary["findings"]

    cards = "".join(
        f'<div class="card"><div class="k">{_esc(k)}</div><div class="v">{_esc(v)}</div></div>'
        for k, v in [
            ("Requests", summary["requests"]),
            ("Model calls", summary["model_calls"]),
            ("Est. tokens", f"~{summary['est_tokens']}"),
            ("Avg latency", f"{summary['avg_latency_ms']} ms"),
            ("Duration", f"{summary['duration_s']} s"),
            ("Refusal rate", f"{summary['refusal_rate']}%"),
            ("Vulnerable", counts["vulnerable"]),
            ("Likely", counts["likely"]),
        ])

    cat_rows = "".join(
        f"<tr class='f' data-cat='{_esc(cat)}' data-mut='' data-text='{_esc(cat).lower()}'>"
        f"<td>{_esc(cat)}</td><td>{stat['findings']}/{stat['total']}</td>"
        f"<td>{stat['worst_severity'] or '-'}</td></tr>"
        for cat, stat in sorted(summary["by_category"].items(),
                                key=lambda kv: (-kv[1]["findings"], kv[0])))

    mut_rows = "".join(
        f"<tr><td>{_esc(m)}</td><td>{s['findings']}/{s['total']}</td></tr>"
        for m, s in sorted(summary["by_mutation"].items(), key=lambda kv: -kv[1]["findings"]))

    def finding_block(idx: int, f: Dict[str, Any]) -> str:
        ev = "".join(f"<li>{_esc(e['kind'])} — {_esc(e['detail'])} "
                     f"(<b>{e['weight']:+.0f}</b>)</li>" for e in f.get("evidence", []))
        colour = "var(--red)" if f["verdict"] == "vulnerable" else "var(--orange)"
        badge = f['verdict'].upper()
        meta = (f"severity {f['severity']}/5 · {f['owasp']} · {f['category']} · "
                f"confidence {f['confidence']}% · {f['latency_ms']} ms")
        mut = (f"<div class='lbl'>mutation</div><div>{_esc(f['mutation'])} — "
               f"{_esc(f['mutation_note'])}</div>") if f["mutation"] not in ("none", "") else ""
        return f"""
        <details>
          <summary>
            <span class="pill v-{_esc(f['verdict'])}">{badge}</span>
            <span style="color:{colour}"> {_esc(f['probe_id'])}</span>
            <span> · {_esc(f['name'])}</span>
            <span class="note"> · {_esc(meta)}</span>
          </summary>
          <div class="lbl">prompt sent</div>
          <pre>{_esc(f['prompt'][:4000])}</pre>
          <div class="lbl">target response</div>
          <pre>{_esc((f['response'] or '<empty>')[:4000])}</pre>
          {mut}
          <div class="lbl">detection evidence</div>
          <ul class="note" style="margin:6px 0 0 18px">{ev or '<li>none</li>'}</ul>
          <div class="lbl">remediation</div>
          <div class="note">{_esc(_remediation_for(f['category'], f['probe_id']))}</div>
        </details>"""

    all_rows = "".join(
        f"<tr class='f' data-cat='{_esc(r['category'])}' data-mut='{_esc(r['mutation'])}' "
        f"data-text='{_esc((r['probe_id'] + ' ' + r['name'] + ' ' + r['verdict'] + ' ' + r['category']).lower())}'>"
        f"<td><span class='pill v-{_esc(r['verdict'])}'>{_esc(r['verdict'])}</span></td>"
        f"<td>{_esc(r['probe_id'])}</td><td>{_esc(r['name'])}</td>"
        f"<td>{_esc(r['category'])}</td>"
        f"<td class='sev-{r['severity']}'>{r['severity']}</td>"
        f"<td>{_esc(r['mutation'])}</td><td>{r['confidence']}%</td>"
        f"<td>{r['latency_ms']:.0f}</td></tr>"
        for r in results)

    cats = sorted({r["category"] for r in results})
    muts = sorted({r["mutation"] for r in results})
    cat_opts = "".join(f"<option value='{_esc(c)}'>{_esc(c)}</option>" for c in cats)
    mut_opts = "".join(f"<option value='{_esc(m)}'>{_esc(m)}</option>" for m in muts)

    doc = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>AIRT report · {_esc(summary['target']['name'])}</title>
<style>{_HTML_CSS}</style></head>
<body><div class="wrap">
<h1>AI Red-Teaming Report</h1>
<div class="sub">
  target <b>{_esc(summary['target']['name'])}</b> ({_esc(summary['target']['kind'])}) ·
  AIRT v{_esc(summary['version'])} ·
  {_esc(summary['generated_at'])} ·
  scope: authorised testing only
</div>
{'<div class="card note">' + _esc(target_note) + '</div>' if target_note else ''}
<div class="gauge">
  <div class="grade" style="color:{grade_colour}">{_esc(risk['grade'])}</div>
  <div style="flex:1">
    <div class="sub" style="margin:0 0 6px">risk score {risk['score']}/100 —
      {len(findings)} finding(s) across {summary['requests']} probe run(s)</div>
    <div class="bar"><i style="width:{min(100.0, risk['score'])}%;background:{grade_colour}"></i></div>
  </div>
</div>
<div class="grid">{cards}</div>

<h2>Findings</h2>
{''.join(finding_block(i, f) for i, f in enumerate(findings, 1)) or '<div class="note">No exploitable findings — every probe was resisted or inconclusive.</div>'}

<h2>Category coverage</h2>
<table><thead><tr><th>Category</th><th>Findings / runs</th><th>Worst severity</th></tr></thead>
<tbody>{cat_rows}</tbody></table>

<h2>Evasion effectiveness</h2>
<table><thead><tr><th>Mutation</th><th>Findings / runs</th></tr></thead><tbody>{mut_rows}</tbody></table>
<div class="note">A high score on a mutation means the mitigation in front of the model can be
beaten by a trivial payload transform — i.e. the filter, not the model, was doing the work.</div>

<h2>All probes</h2>
<div class="toolbar">
  <input id="q" placeholder="search probe id / name / verdict…" style="min-width:280px">
  <select id="cat"><option value="">all categories</option>{cat_opts}</select>
  <select id="mut"><option value="">all mutations</option>{mut_opts}</select>
</div>
<table><thead><tr><th>Verdict</th><th>ID</th><th>Probe</th><th>Category</th><th>Sev</th>
<th>Mutation</th><th>Conf.</th><th>ms</th></tr></thead><tbody>{all_rows}</tbody></table>

<footer>
  Generated by AIRT — AI Red-Teaming Scanner. Findings are heuristic confidence scores, not
  proof of exploitability; always corroborate with manual review. Only run against systems you
  own or are contracted to test. Prompt-injection testing can make a target disclose data or
  execute tool calls — use an isolated environment and a scratch account.
</footer>
</div><script>{_HTML_JS}</script></body></html>"""
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(doc)
    return path


def _remediation_for(category: str, probe_id: str) -> str:
    from . import payloads
    return payloads.REM.get(category, "Apply defence-in-depth: keep controls outside the prompt text.")


def write_jsonl(path: str, results: List[Dict[str, Any]]) -> str:
    with open(path, "w", encoding="utf-8") as fh:
        for r in results:
            fh.write(json.dumps({"ts": datetime.now(timezone.utc).isoformat(), **r},
                                ensure_ascii=False) + "\n")
    return path
