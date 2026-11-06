# 🛡️ RatanSec Super Agent v2

**Private-key AI security agent** — apne laptop/VPS par chalao, apni API key ya local model use karo,
aur authorized targets ke liye **bounded, evidence-backed posture missions** chalao.

> v2 ka focus: default-deny scope, exact-plan human approval, no raw shell, no exploitation,
> no credentials in chat, aur fail-closed audit. Yeh full autonomous hacking tool nahi hai.

## Kya-kya hai

| Surface | Kahan | Kaam |
|---|---|---|
| Dashboard | `/` | missions, chat, approvals, RoE, arsenal, reports, evidence, provider |
| Mobile PWA | `/mobile` | responsive console; phone par install |
| CLI | `python -m superagent.cli` | mission client + chat (raw shell retired) |
| API docs | `/api/docs` | OpenAPI |
| Offline demo | `--demo` | fixture mission, no network/provider/key |

### Mission profiles

- **Quick posture**: DNS validation + HTTP response headers + TLS certificate metadata
- **Web hygiene**: quick + `security.txt` + `robots.txt`
- **TLS review**: DNS + TLS certificate/protocol

Live probes: redirect follow nahi karte, credentials/cookies send nahi karte, response body read nahi
karte (sirf do well-known text files, 16 KiB cap), DNS answer pin karte hain, aur har step se pehle
authorization re-check karte hain.

### Arsenal

139-entry catalog **reference/install map** hai. v2 mein executable adapters sirf:
`dig`, `whois`, `nmap` (fixed safe ports, no NSE scripts, pinned address). Har adapter ko bhi human
approval chahiye. Exploit frameworks, brute force, raw shell aur remote package install retired hain.

---

## 1. Offline demo (bina key, bina target traffic)

```bash
cd ratansec-os
python3 -m venv .venv && source .venv/bin/activate
pip install -r superagent/requirements.txt
bash scripts/superagent.sh --demo
```

Kholo `http://127.0.0.1:8000`. **Run offline demo** dabao — fixture findings/report/evidence workflow
dikhega. Demo mode mein live records, provider calls, audit export aur target traffic disabled hain.

## 2. Live private setup

```bash
cp superagent/.env.example .env
chmod 600 .env
# edit .env locally:
# APP_PASSWORD=...
# SUPERAGENT_API_TOKEN=...
# SUPERAGENT_PROVIDER=openrouter
# SUPERAGENT_API_KEY=...
# SUPERAGENT_BASE_URL=https://openrouter.ai/api/v1
# SUPERAGENT_MODEL=...
bash scripts/superagent.sh
```

Console `http://127.0.0.1:8000` par locked milega. Password/token server `.env` se aata hai.
**Key chat/browser field mein mat daalo.** API status key hint bhi return nahi karta.

### Local model (Ollama / LM Studio / vLLM)

```env
SUPERAGENT_PROVIDER=ollama
SUPERAGENT_BASE_URL=http://127.0.0.1:11434/v1
SUPERAGENT_MODEL=your-local-model
# key required nahi
```

Plain HTTP sirf loopback provider ke liye allowed hai. Remote provider ke liye HTTPS zaroori hai.
Provider test button server se ek chhota `READY` completion call karta hai; target data send nahi hota.

## 3. Authorized mission workflow

1. **Scope / RoE** tab mein record banao: client, exact hosts/CIDR, dates, signer, authorization reference.
   Record `recon`, `web`, `reporting` sections permit kare.
2. **Missions** mein target URL + objective + profile do. Plan banega, traffic nahi jayega.
3. **Approvals** mein exact plan/hash dekh kar approve/deny karo. Record revoke/expire hua to approval fail.
4. Mission bounded probes chalata hai; timeline, findings, SHA-256 evidence aur Markdown report banta hai.
5. **Emergency stop** ya RoE revoke se kaam rukta hai.

> RoE record operator-supplied reference hai, cryptographic proof of consent nahi. Written permission
> aur program/cloud-provider policy khud verify karo.

## 4. CLI

```bash
python -m superagent.cli --url http://127.0.0.1:8000 --token "$SUPERAGENT_API_TOKEN"
# commands: /help /mission /approve /deny /missions /read /stop /scope /records /chat /provider-test
python -m superagent.cli --mission https://app.example.com --profile quick --objective "Pre-audit posture"
```

## 5. Docker

```bash
cp superagent/.env.example .env   # edit locally
docker compose -f superagent/docker-compose.yml up -d --build
```

Compose host port `127.0.0.1:8000` par bind karta hai. Remote access ke liye HTTPS reverse proxy lagao;
`SUPERAGENT_TRUSTED_PROXY=1` sirf trusted proxy ke peeche set karo. Container non-root, cap-drop,
no-new-privileges aur read-only root filesystem ke saath chalta hai.

## 6. Tests

```bash
pip install pytest httpx
python -m pytest -q superagent/tests/test_v2.py
python -m superagent.tests.test_smoke
```

Tests offline hain: auth/CSRF, default deny, RoE revoke, exact-plan approval, retired shell/install,
key non-disclosure, demo isolation, report escaping.

## 7. Security boundaries (honest limits)

- Default deny; metadata/link-local/reserved ranges hard-blocked.
- Live mode bina password/token start nahi hota.
- Cookies random, HttpOnly, SameSite=strict; query-string tokens retired.
- Cross-origin cookie writes blocked; API token header se aate hain.
- Provider redirects disabled; error bodies echo nahi hote; secrets redact hote hain.
- Audit fail-closed hai. Local hash chain casual tampering detect karta hai, lekin off-host
  append-only storage/signed timestamps ka substitute nahi.
- Findings posture observations hain; exploitability proof nahi. Missing header ≠ confirmed vulnerability.
- Yeh tool authorized security testing ke liye hai. Unauthorized access, DoS, credential theft,
  persistence, evasion ya destructive actions supported nahi.

Legal/authorization templates: [`../docs/`](../docs/).


## 📱 Sirf phone hai? Laptop nahi?

Phone ko hi server bana do (Termux, no root) — URL `http://127.0.0.1:8000`.
Guide: [`PHONE_SETUP.md`](PHONE_SETUP.md)
