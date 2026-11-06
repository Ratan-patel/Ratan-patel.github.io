<!-- Ready-to-send authorization letter. Print/letterhead par daal kar client se sign karwao.
     Signed copy ko engagement ke saath rakho; details Records tab me daalo. -->

**[Client name — letterhead]**

# Authorization to Perform Security Testing

**Date:** ______________
**To:** Ratan Kumar Patel — RatanSec (the "Tester")
**From:** ______________________________ (the "Client"), [registered address]
**Signatory:** ____________________, [designation], [email], [phone]

## 1. Authorization
The Client authorizes the Tester to perform security testing — reconnaissance, vulnerability
assessment, and controlled exploitation proof-of-concepts — against the systems listed in
**Annexure A**, only during the window in **Annexure B**. This authorization is limited strictly
to that scope.

## 2. Scope — Annexure A
| Type | Value |
|---|---|
| Domains / subdomains | `acme.in, *.acme.in` |
| IP ranges | `10.20.30.0/24` |
| APIs / mobile apps | `api.acme.in/v2` |
| Credentials provided | `none / test-account: ____` |
| **Out of scope** | payment gateway, third-party SaaS, production DB writes, … |

## 3. Window — Annexure B
* Start: ______  End: ______
* Testing hours: ______ (e.g. 22:00–05:00 IST)
* Rate limits: no DoS; ≤ ___ req/sec per host; no destructive payloads.

## 4. Constraints
* No denial-of-service, no destructive actions, no data exfiltration beyond proof-of-concept.
* No social engineering / physical access unless explicitly allowed here: __________
* Discovered personal data handled per applicable law (India: DPDP Act 2023) and destroyed after reporting.
* Testing stops immediately on client's written notice (email/phone).

## 5. Emergency contacts
* Client 24×7: ____________
* Tester 24×7: ____________

## 6. Reporting
Findings reported to ____________ within ___ days; critical findings within ___ hours.

## 7. Liability & confidentiality
As per SOW dated ________ and NDA dated ________. Liability cap: ________.

**Authorized signature:** ____________________  **Seal:**
**Name / Designation:** ____________________

---

### Annexure C — activity matrix (tick what is allowed)

| Activity | Allowed | Notes |
|---|---|---|
| Passive recon / OSINT | ☐ | |
| Port & service scanning | ☐ | |
| Vulnerability scanning (nuclei/nikto/nmap scripts) | ☐ | |
| Directory / parameter fuzzing | ☐ | rate limit: ____ |
| Authentication testing (credentialed) | ☐ | accounts: ____ |
| Brute-force / password spraying | ☐ | max attempts: ____ |
| SQLi / XSS / SSRF PoC (read-only) | ☐ | |
| Data extraction (PoC only, max rows ____) | ☐ | |
| Post-exploitation enumeration | ☐ | |
| Social engineering / phishing simulation | ☐ | |
| Wireless testing (SSIDs: ________) | ☐ | |
| Physical access testing | ☐ | |
