# Authorization & Legal Framework — RatanSec Super Agent

> **v2 note:** Raw shell, remote package install, exploitation/brute-force frameworks aur auto-approve
> retired hain. Live missions bounded posture probes hain aur har exact plan ko human approval chahiye.
> Neeche ke legal principles phir bhi apply hote hain; tool capability se permission nahi milti.

> **Yeh document legal advice nahi hai.** Deployment se pehle apne lawyer / client ke legal team
> se confirm karo. Purpose: aapke paas records hon, system unhe enforce kare, aur evidence
> court/audit ke liye chain-of-custody me rahe.

---

## 1. Golden rules (5 lines)

1. **Likhit permission ke bina kuch nahi.** Verbal permission kaafi nahi — email/PDF/SOW chahiye.
2. **Scope = exactly wahi host/IP/URL** jo document me hai. Ek character bhi extra = out of scope.
3. **Authorization record banao** (Records tab) — bina record agent command nahi chalayega.
4. **Intrusive tools (brute-force, exploitation, post-exploitation) hamesha human approval** — aur
   unka use bhi sirf documented scope + time window me.
5. **Evidence chain** — command, output, timestamp, approval, record id. Ye aapko bachata hai.

---

## 2. Minimum documents jo aapke paas hone chahiye

| Document | Kya hona chahiye | Kahan rakhein |
|---|---|---|
| **Authorization letter / engagement contract** | client legal name, signatory, scope list, dates, allowed activity type, "permission to test" ka explicit sentence | PDF + `data/superagent/roe/ledger.jsonl` me record |
| **SOW / Work Order** | deliverables, testing window, out-of-scope items, emergency contacts, fee | PDF |
| **Rules of Engagement (RoE)** | kya allowed hai (DoS? social engineering? physical?), rate limits, data handling, reporting timeline | PDF |
| **NDA** | client data confidentiality | PDF |
| **Insurance** (professional indemnity) | enterprise clients ke liye aksar mandatory | policy doc |
| **Contact sheet** | 24×7 on-call (client + aap), escalation path | record ke `emergency` field me |

**Third-party / cloud targets:** AWS/Azure/GCP hosted apps ke liye client ka authorization kaafi
nahi — cloud provider ki testing policy bhi check karo (AWS: penetration testing request form;
Azure: Rules of Engagement; GCP: acceptable use). Shared hosting / SaaS par extra permission chahiye.

**Bug bounty:** program ka scope page + policy hi aapka authorization hai — us scope aur
"out of scope" list ko hi Records me daalo, aur program ka `safe harbor` clause save karo.

---

## 3. India specific (agar client India me hai)

| Kanoon | Relevant sections | Kya matlab |
|---|---|---|
| **IT Act 2000 (amended 2008)** | Sec 43 (damage), 66 (computer-related offences), 66B (stolen device), 66C (identity theft), 66D (cheating), 66F (cyber terrorism) | Unauthorized access/damage criminal offence — written authorization + scope se bachav |
| **DPDP Act 2023** | personal data processing, breach notification | Testing me personal data mile to minimize karo, report me mask karo, client ko batao |
| **Indian Contract Act** | contract + liability | SOW me liability cap, indemnity, confidentiality |
| **BNS 2023** (naya criminal code) | criminal breach of trust / mischief provisions | scope violation par risk |

Do's:
- Permission letter me **"security testing" specifically** likha ho (generic "audit" nahi).
- Testing window aur **rate limits** document me ho (production par DoS risk).
- Data mila to **exfiltrate nahi** — sirf proof (screenshot/first line + hash) aur report.
- Emergency stop: client bole "stop" → turant ruk jao, record revoke karo (Records → Revoke).

Don'ts:
- Client ke production DB ka dump, customer PII, ya source code copy karke rakhna.
- "Just checking" ke liye out-of-scope IP/subdomain par scan.
- Client ke competitor / third-party infra par ek bhi packet.
- Public disclosure bina client ki likhit approval (responsible disclosure timeline SOW me).

---

## 4. Authorization letter template (copy-paste)

```
[Client letterhead]

AUTHORIZATION TO PERFORM SECURITY TESTING

Date: ______________
To: Ratan Kumar Patel / RatanSec (the "Tester")
From: ______________________ (the "Client"), [registered address]
Signatory: ______________________, [designation], [email], [phone]

1. AUTHORIZATION
   The Client authorizes the Tester to perform security testing (reconnaissance,
   vulnerability assessment, and controlled exploitation proof-of-concepts) against
   the systems listed in Annexure A, during the window specified in Annexure B.
   This authorization is limited strictly to the listed scope.

2. SCOPE (Annexure A)
   Domains:    ____________________ (e.g. acme.in, *.acme.in)
   IP ranges:  ____________________ (e.g. 10.20.30.0/24)
   APIs:       ____________________
   Out of scope: __________________ (e.g. payment gateway, third-party SaaS, production DB writes)

3. WINDOW (Annexure B)
   Start: ______  End: ______   Testing hours: ______ (e.g. 22:00–05:00 IST)
   Rate limits: no DoS, no > ___ requests/second, no destructive payloads.

4. CONSTRAINTS
   - No denial-of-service, no destructive actions, no data exfiltration beyond PoC.
   - No social engineering / physical access unless explicitly allowed.
   - Credentials provided: ____________________ (if any)
   - Any discovered personal data handled per DPDP Act 2023 and destroyed after reporting.

5. EMERGENCY CONTACTS
   Client 24x7: ____________   Tester 24x7: ____________
   Either party may immediately stop testing by written notice (email/phone).

6. REPORTING
   Findings reported to ____________ within ___ days; critical findings within ___ hours.

7. LIABILITY & CONFIDENTIALITY
   As per SOW dated ________ / NDA dated ________.

Authorized signature: ______________________   Seal:
Name / Designation: ______________________
```

Annexure A/B ko Records tab me daalo — same wording, same hosts.

---

## 5. Records tab me kya bharna hai (mapping)

| Letter field | Records field |
|---|---|
| Client registered name | `client` |
| Signatory / contact | `signer`, `contact` |
| Annexure A hosts | `scope` (comma separated; `*.domain.com` allowed) |
| Allowed activity types | `sections` (recon, vuln, web, exploitation…) |
| Annexure B window | `start`, `end` |
| Letter date / SOW number / email id | `signature` |
| 24×7 contact | `emergency` |
| Special constraints | `notes` |

Jab engagement khatam ho jaye → **Revoke** record (chain me permanent entry jaati hai).

---

## 6. Evidence chain (court/audit ke liye)

Har command par:

```
ts, time, event, cmd_id, tool, target, display, status, exit_code,
duration, actor, approval_id, roe_id, prev_hash, hash
```

* `data/superagent/audit.jsonl` — append only, hash-chained.
* `data/superagent/evidence/evidence.log` — same cheez evidence-grade (approvals, commands, reports).
* `data/superagent/roe/ledger.jsonl` — authorization records + revokes.
* **`POST /api/evidence/bundle`** → zip: audit + ledger + `manifest.json` (chain verification).

Verify: dashboard → Evidence tab → "Verify chain" (ya `GET /api/audit/verify`).
Tamper hone par `ok:false` + `broken_at` line number milta hai.

Report me ye line hamesha rakho:

> All testing was performed under written authorization [ref] within scope [hosts] during
> [window]. Execution logs are hash-chained and available on request (bundle id ______).

---

## 7. Out-of-scope cheezein jo agent khud block karta hai

* Cloud metadata (`169.254.169.254`, `metadata.google.internal`, `100.100.100.200`) — SSRF abuse.
* Link-local, multicast, reserved ranges.
* Record se bahar ka koi bhi host (default deny).
* Record me permitted nahi wo section.
* Destructive shell patterns (`rm -rf /`, `mkfs`, fork bomb, `curl | bash`, disk overwrite…).
* Record expire/revoke hone ke baad kuch bhi.

Agar kisi legitimate test ke liye inme se kuch chahiye — code ko bypass mat karo; pehle client se
alag written approval lo, phir alag (isolated, client-owned) environment me karo.

---

## 8. Report likhne ka standard (jo client accept karta hai)

1. **Executive Summary** — 1 page, business risk, koi jargon nahi.
2. **Scope & Authorization** — record id, hosts, window, constraints, tester details.
3. **Methodology** — sections/tools used (kaun kaun se), safe-mode settings (sqlmap level/risk, nuclei severity).
4. **Findings table** — ID, Title, Severity (CVSS vector), Affected asset, Evidence ref, Status.
5. **Per-finding detail** — description, reproduction (exact command), impact, evidence (redacted output), remediation, references.
6. **Risk summary & prioritisation** — fix order.
7. **Appendix** — tool list + versions, timeline of testing, evidence bundle hash, sign-off block.

Super Agent ka `save_report` tool isi structure me AI se draft karwa deta hai; aap verify/edit karo.
