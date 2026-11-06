# 🥷 RatanSec Super Agent

**Authorised AI security agent** — natural language me bolo, agent Kali/Linux tools chalata hai
(recon → enumeration → vuln analysis → web/API → approval ke baad exploitation → report),
aur har command ka **hash-chained evidence record** banta hai.

Teen surface:

| Surface | Kahan | Kis liye |
|---|---|---|
| 🧠 **Dashboard** | `/` | AI chat, terminal, arsenal, runs, approvals, records, reports, evidence |
| 📱 **Mobile console (PWA)** | `/mobile` | phone par install ho jata hai — chat, approvals, terminal, records |
| ⌨️ **CLI** | `python -m superagent.cli` | asli Linux terminal feel — `agent` mode + `!` shell passthrough |

Aap apni **private API key** lagate ho (OpenRouter / OpenAI / Groq / DeepSeek / koi bhi
OpenAI-compatible endpoint) — key server par rehti hai, browser me kabhi nahi jaati.

---

## 1. 60-second start

```bash
cd ratansec-os
python3 -m venv .venv && source .venv/bin/activate
pip install -r superagent/requirements.txt

cp superagent/.env.example .env      # values bharo (neeche list)

# tools (Kali/Debian/Ubuntu/Termux) — optional, jitne chahiye
bash scripts/install-agent-tools.sh core     # ya: full / catalog

uvicorn superagent.webui:app --host 0.0.0.0 --port 8000
```

Kholo: `http://localhost:8000` (dashboard) aur `http://<phone-same-wifi-ip>:8000/mobile`.

Minimum `.env`:

```env
APP_PASSWORD=ek-lamba-password            # dashboard lock
SUPERAGENT_API_TOKEN=ek-random-token      # mobile/CLI ke liye (X-Agent-Token)
SUPERAGENT_API_KEY=sk-...                 # aapki private AI key
SUPERAGENT_BASE_URL=https://openrouter.ai/api/v1
SUPERAGENT_MODEL=openai/gpt-4o-mini
SUPERAGENT_ALLOW_SHELL=1                  # terminal ke liye (default 0)
```

> AI key ke bina bhi sab kaam karta hai (terminal, manual tools, records, reports) — sirf chat off rehta hai.

---

## 2. AI provider — apni key, apna endpoint

| Provider | `SUPERAGENT_BASE_URL` | Note |
|---|---|---|
| OpenRouter | `https://openrouter.ai/api/v1` | ek key, saare models (default) |
| OpenAI | `https://api.openai.com/v1` | `SUPERAGENT_MODEL=gpt-4o-mini` |
| Groq | `https://api.groq.com/openai/v1` | fast + sasta |
| DeepSeek | `https://api.deepseek.com/v1` | tool-calling support |
| Ollama (local) | `http://127.0.0.1:11434/v1` | model: `qwen2.5:14b` etc. |
| Apna proxy / gateway | `https://your-gateway/v1` | `SUPERAGENT_EXTRA_HEADERS` se custom auth header |

Extra headers: `SUPERAGENT_EXTRA_HEADERS="X-Api-Key: abc, X-Org: myteam"`.

Environment se key automatic pick hoti hai: `SUPERAGENT_API_KEY` → `OPENROUTER_API_KEY` →
`OPENAI_API_KEY` → `GEMINI_API_KEY` → `GROQ_API_KEY` → `DEEPSEEK_API_KEY`.

---

## 3. Tool arsenal — 12 sections, 139 tools

| # | Section | Kya | Examples |
|---|---|---|---|
| 1 | Recon / OSINT | domain, DNS, cert, tech-stack, OSINT | nmap, dig, subfinder, amass, theHarvester, whatweb, wafw00f, sslscan, masscan, sherlock |
| 2 | Info Access / Enum | SMB, NFS, SNMP, LDAP, shares, crawl | enum4linux-ng, smbmap, rpcclient, snmpwalk, ldapsearch, httpx, katana, dalfox |
| 3 | Vulnerability Analysis | CVEs, misconfig, secrets, SAST | nmap-vuln, nuclei, nikto, wapiti, zap-baseline, searchsploit, trivy, gitleaks, semgrep |
| 4 | Web / API Testing | endpoints, params, JWT, GraphQL | ffuf, gobuster, feroxbuster, wpscan, sqlmap, commix, xsstrike, jwt_tool, graphql-cop |
| 5 | Gaining Access | login services (approval-only) | hydra, medusa, ncrack, patator, responder, bettercap, aircrack-ng |
| 6 | Exploitation / PoC | verified CVE proof, AD | metasploit, msfvenom, sqlmap-exploit, corsy, ssrfmap, impacket, routersploit |
| 7 | Post-Exploitation | situational awareness (approval) | linpeas, winpeas, bloodhound, secretsdump, chisel, proxychains |
| 8 | Priv-Esc Checks | read-only misconfig checks | sudo-check, suid-finder, getcap, pspy, linux-exploit-suggester |
| 9 | Password / Hash | apne hashes ka audit | hashcat, john, hashid, cewl, crunch, rsmangler |
| 10 | Wireless / RF | apne SSID/AP ka posture | airmon-ng, airodump-ng, aireplay-ng, wifite, bettercap-wifi |
| 11 | Reporting | evidence + chain-of-custody | sha256sum, gpg-sign, evidence bundle |
| 12 | Utility | helpers | curl, nc, socat, jq, openssl, proxychains-wrap |

Missing tool? Arsenal tab me install hint dikhta hai ("install missing" approval ke saath),
ya `bash scripts/install-agent-tools.sh full`.

---

## 4. Safety model (yeh sabse important part hai)

```
user / AI
   │  tool call
   ▼
[1] catalog gate      → sirf defined tool + defined flags (argv-only, shell=false)
[2] scope check       → target authorized? (RoE record + allowlist, default DENY)
[3] hard blocks       → 169.254.x.x / metadata / multicast / 0.0.0.0 — never
[4] approval gate     → intrusive tools + shell = human tap (phone par)
[5] executor          → timeout, output cap, cancel, no shell injection
[6] audit + evidence  → hash-chained JSONL (tamper-evident)
```

* **Intrusive tools** (hydra, metasploit, sqlmap, responder, hashcat, linpeas, mimikatz…) **kabhi**
  approval bypass nahi kar sakte — AI bhi nahi.
* **Shell mode** off by default (`SUPERAGENT_ALLOW_SHELL=0`). On karne par bhi: blocklist
  (`rm -rf /`, `mkfs`, fork bombs, `curl | bash` …), approval, aur poora audit.
* **Koi record → koi command nahi.** Pehle Records tab me engagement banao (client, scope,
  sections, dates, signature reference).
* **Audit chain verify** har time dashboard se hota hai; tamper hone par `broken_at` dikhata hai.

---

## 5. Authorization records (RoE) — aapke paas records hain, system unhe enforce karta hai

Records tab (ya `POST /api/records`) me:

| Field | Example |
|---|---|
| client | Acme Pvt Ltd — Q4 External VAPT |
| scope | `acme.in, *.acme.in, 10.20.30.0/24` |
| sections | recon, vuln, web, reporting (ya "all") |
| start / end | 2026-11-10 → 2026-11-20 |
| signer + signature | CISO name + `SOW-2026-014` / email ref / PDF id |
| emergency | on-call number |

Rules:

* Record expired/revoked → us target par agent turant ruk jata hai.
* Section record me nahi → us section ka tool us target par nahi chalega.
* Har record hash-chain me hai (`verify_chain()`), revoke karne par bhi entry add hoti hai.
* `POST /api/records/seed-demo` se ek **lab/demo** record (scanme.nmap.org + localhost) milta hai —
  real client kaam ke liye naya record banao.

Client ko bhejne wala authorization letter template: [`docs/AUTHORIZATION_TEMPLATE.md`](../docs/AUTHORIZATION_TEMPLATE.md)
aur rules of engagement + legal checklist: [`docs/SAFETY_AND_LEGAL.md`](../docs/SAFETY_AND_LEGAL.md).

---

## 6. Terminal — "advance terminal" kaise use karein

Dashboard → Terminal tab (ya CLI):

```
catalog mode:  nmap-vuln lab.local ports=80,443
               nuclei https://lab.local severity=high,critical
               ffuf https://lab.local filter_code=404
               sqlmap "https://lab.local/item?id=1" level=2      # approval
shell mode:    id; uname -a; ip a                              # approval
help
```

CLI:

```bash
python -m superagent.cli --url http://127.0.0.1:8000 --token $SUPERAGENT_API_TOKEN
# ya bilkul local (server ke bina, isi machine ke tools):
python -m superagent.cli --local
```

CLI commands: `/mode`, `/ask`, `/tool`, `/scope`, `/records`, `/runs`, `/read`, `/approve`,
`/deny`, `/auto`, `/model`, `/sections`, `/report`, `/audit`. Shell mode me `!<cmd>`.

---

## 7. Phone par (PWA)

1. Server VPS/laptop par chalao, `--host 0.0.0.0`.
2. Phone browser me `https://<host>/mobile` kholo.
3. Login: `APP_PASSWORD` ya `SUPERAGENT_MOBILE_TOKEN`.
4. Chrome/Safari → **Add to Home screen** → app ki tarah khulta hai (offline shell cached).
5. Approvals tab se ek tap me approve/deny; Runs tab me live output.

Security tip: internet par khol rahe ho to HTTPS (Caddy/Cloudflare Tunnel) ke peeche rakho —
`deploy/cloudflared-tunnel.sh` repo me already hai.

---

## 8. Deployment options

| Kahan | Kaise | Note |
|---|---|---|
| Laptop / Kali | `uvicorn superagent.webui:app` | sabse simple, tools local |
| Docker (full Kali) | `docker build -f superagent/Dockerfile -t ratansec-superagent .` | ~2.5-3 GB, sab tools pre-installed |
| Docker (slim) | `-f superagent/Dockerfile.slim` | ~120 MB + nmap; baaki tools host se |
| docker compose | `docker compose -f superagent/docker-compose.yml up -d --build` | volume + NET_RAW |
| Render | `superagent/render.yaml` blueprint | disk 1 GB, root nahi (SYN scan nahi) |
| Termux (phone) | `bash scripts/install-agent-tools.sh core` + uvicorn | nmap -sT, sqlmap, hydra chalte hain |
| GitHub Codespaces | repo me hi chalao | browser hi kaafi |

---

## 9. API (mobile app / apna frontend banao)

Auth: `X-Agent-Token: <SUPERAGENT_API_TOKEN>` (ya cookie session).

```bash
curl -H "X-Agent-Token: $TOKEN" http://host:8000/api/status
curl -H "X-Agent-Token: $TOKEN" -X POST http://host:8000/api/agent/chat \
  -d '{"message":"lab.local ka recon karo","session_id":"s1"}'
curl -H "X-Agent-Token: $TOKEN" -X POST http://host:8000/api/approvals/ap-xxxx -d '{"approved":true}'
curl -H "X-Agent-Token: $TOKEN" http://host:8000/api/agent/followup/s1
```

Full OpenAPI: `/api/docs`. Endpoints: `status, sections, tools, scope, scope/check, records,
agent/chat, agent/followup/{id}, command, command/shell, runs, runs/{id}, runs/{id}/cancel,
approvals, approvals/{id}, reports, audit, audit/verify, evidence/bundle`.

---

## 10. Data / privacy

* Sab kuch local: `data/superagent/{audit.jsonl, roe/, runs/, reports/, evidence/}`.
* Records, approvals, audit — plain JSONL (git me commit mat karo, `.gitignore` me hai).
* API key sirf server process me; UI me `key_hint` (first 6 + last 4) hi dikhta hai.
* Evidence bundle: `POST /api/evidence/bundle` → zip (audit + RoE ledger + chain verify manifest).

---

## 11. Troubleshooting

| Problem | Fix |
|---|---|
| `AI key set nahi` | `SUPERAGENT_API_KEY` set karke restart |
| `Tool install nahi hai` | Arsenal tab → install hint, ya `scripts/install-agent-tools.sh full` |
| `target authorized nahi` | Records tab me record banao (scope me wo host daalo) |
| `wordlist chahiye` | `apt install seclists` ya `flags: wordlist=/path/list.txt` |
| `hydra: user chahiye` | `flags: user=admin passlist=/path/list.txt` |
| `shell mode off` | `.env` me `SUPERAGENT_ALLOW_SHELL=1` |
| Phone se open nahi ho raha | `--host 0.0.0.0`, same wifi, firewall port 8000 |

---

> **Sirf authorised testing ke liye.** Bina likhit permission kisi bhi system ko test karna
> India me IT Act 2000/2008 (Sec 43, 66, 66B-F) ke tahat criminal offence hai — aur lagbhag har
> desh me illegal. Super Agent ke safety layer jaan-boojh kar "deny by default" hain; unhe
> bypass karne ke liye code badalna aapki zimmedari par hai.
