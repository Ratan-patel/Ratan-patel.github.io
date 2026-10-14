# 🛡️ RatanSec OS

**AI-powered pentest environment** — Kali Linux tools + apna AI copilot (OpenRouter) + web dashboard + CLI + reports + audit log.

> Sirf **authorized** security testing ke liye. Bina likhit permission kisi bhi system ko scan karna illegal hai. Yeh tool aapki zimmedari ke saath aapke targets par chalta hai.

---

## 1. Yeh kya hai (60 second me)

RatanSec OS ek **cloud-first** pentest environment hai:

```
┌──────────────────────────────────────────────────────────────┐
│  Browser / CLI                                               │
│  ├─ 🧠 AI Chat   → "example.com ka recon karo"               │
│  ├─ 🎯 Scan      → quick / web / network / vuln / full       │
│  ├─ 📡 Runs      → live output, cancel, AI analysis          │
│  ├─ 📄 Reports   → Markdown report (AI summary ke saath)     │
│  ├─ 🧰 Tools     → kaunse tools ready hain                   │
│  └─ 🔍 Audit     → har command ka record                     │
└───────────────┬──────────────────────────────────────────────┘
                │ FastAPI (REST + dashboard)
┌───────────────▼──────────────────────────────────────────────┐
│  AI Agent (OpenRouter, tool-calling)                         │
│   ├─ scope check (allowlist)  ├─ approval gates              │
│   └─ argv-only executor       └─ audit log                   │
└───────────────┬──────────────────────────────────────────────┘
                │
┌───────────────▼──────────────────────────────────────────────┐
│  Kali Linux container: nmap · nikto · whatweb · gobuster ·   │
│  ffuf · nuclei · sqlmap · hydra · whois · dig · curl · nc    │
└──────────────────────────────────────────────────────────────┘
```

Tum apni **API key** daalte ho (`OPENROUTER_API_KEY`), AI model choose karte ho, aur cloud par deploy kar dete ho. Baaki sab ready hai.

---

## 2. Reality check: "25 MB me Kali + AI"?

Yeh **possible nahi hai**. Seedhe numbers:

| Cheez | Actual size |
|---|---|
| Kali Linux ISO | ~4.5 GB |
| Parrot Security ISO | ~2.5 GB |
| Metasploit framework | ~400 MB+ |
| nmap + sqlmap + nuclei + ffuf + gobuster + hydra (installed) | ~150–250 MB |
| Ek local AI model (chhota bhi) | 300 MB – 4 GB |
| Yeh Docker image (Kali + tools + backend) | ~2.5–3.5 GB |

Isliye is project ka design yeh hai: **AI brain + control layer halka rakhna** (backend code ~120 KB, 3 dependencies) aur **tools cloud image me** (jo on-demand start hoti hai). Agar tumhe 25 MB ke andar kuch chahiye to wahi `app/` core + `cli.py` alag se chal jaate hain (Kali tools sirf tab install hote hain jab zaroorat ho — dekho section 10, Plan A).

---

## 3. Features

| Feature | Detail |
|---|---|
| 🧠 **AI copilot** | OpenRouter (koi bhi model: GPT-4o, Claude, Gemini, Llama, DeepSeek…). Natural language → tool calls → analysis. |
| 🎯 **6 scan profiles** | `quick`, `web`, `network`, `vuln`, `webapp`, `full` — sab Kali tools se. |
| 🚦 **Human approval gates** | sqlmap/hydra jaise intrusive tools aur scope-less targets par dashboard me Approve/Deny card. |
| 🛡️ **Scope allowlist** | `ALLOWED_TARGETS=example.com,*.mysite.in,10.0.0.0/24` — bahar wale targets block. |
| 🔒 **Injection-proof execution** | Sirf argv-based subprocess (shell = off), target validation, output caps, timeouts. |
| 🚫 **Metadata protection** | Cloud metadata IPs (169.254.x.x, metadata.google.internal) hard-blocked — SSRF abuse nahi. |
| 📄 **AI reports** | Markdown report + AI analysis, dashboard se download. |
| 🔍 **Audit log** | Har command `data/audit.jsonl` me — evidence aur accountability. |
| 💻 **CLI + REST API** | `cli.py` se ya apne app/site se API call karke control. |
| 🔑 **Auth** | `APP_PASSWORD` (cookie session + Bearer token), rate limits. |
| ☁️ **Deploy-ready** | Dockerfile, docker-compose, Render blueprint. |

---

## 4. Start kaise karun? (30 seconds)

> Naya ho? **ZERO se shuru karo: [SHURU_SE_GUIDE.md](SHURU_SE_GUIDE.md)** — ek-ek cheez, ek-ek click, "kya dikhega" checkpoints + browser-only rasta (kuch install nahi).
> Sirf browser hai (kuch install nahi karna)? **[CODESPACES_GUIDE.md](CODESPACES_GUIDE.md)** — screen-by-screen.
> Short version: **[CHALANE_KA_TARIKA.md](CHALANE_KA_TARIKA.md)** (Windows, Kali, phone/Termux, cloud).

**Linux / Kali / Ubuntu / macOS / Termux** (ek command):
```bash
cd ratansec-os
./setup.sh --with-tools        # Python env + tools + config + server start
# → browser: http://localhost:8000
# band karne ke liye: Ctrl+C   |   dobara chalane ke liye: ./start.sh
```

**Windows:** `start-windows.bat` par double-click (Python installed hona chahiye). Asli tools ke saath chahiye to `wsl --install -d kali-linux` karke Kali terminal me `./setup.sh --with-tools`.

Scripts kya karte hain:
| Script | Kaam |
|---|---|
| `setup.sh` | Python check → `.venv` + dependencies → optional tools install → `.env` (password + key) → server start. Flags: `--with-tools`, `--no-tools`, `--no-start`, `--port`, `--password`, `--key` |
| `start.sh` | Server start (URL + password screen par dikha deta hai). Roz bas yahi chalana hai. |
| `scripts/install-tools.sh` | Missing tools install (apt ya Termux `pkg`), best-effort |
| `start-windows.bat` | Windows par native Python se one-click start |

---

## 5. Docker se (Kali + saare tools pre-installed)

```bash
cd ratansec-os
cp .env.example .env        # APP_PASSWORD + OPENROUTER_API_KEY bharo

docker compose up -d --build
# dashboard: http://localhost:8000
```

Pehli build ~5–10 min lagti hai (Kali packages download hote hain). Iske baad seconds me start.

> PaaS/Render par bhaari Kali image slow ho sakti hai — wahan `Dockerfile.slim` (Debian, ~800 MB, non-root) use hoti hai, jo `render.yaml` me already set hai.

**Bina Docker, manual (agar script nahi chalani):**

```bash
sudo apt-get update && sudo apt-get install -y python3-venv python3-pip nmap nikto whatweb gobuster ffuf sqlmap hydra whois dnsutils curl
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
cp .env.example .env         # values bharo
.venv/bin/python -m app.webui        # → http://localhost:8000
```

**Sirf AI chat + apne VPS ke tools remote se control karna ho** → CLI mode:

```bash
pip install -r requirements.txt
python cli.py --url https://your-app.onrender.com --token "$APP_PASSWORD" status
```

---

## 6. Render par deploy (tumhara plan: PaaS)

1. Repo GitHub par push karo (yeh folder included).
2. Render → **New → Blueprint** → repo select → Blueprint path `ratansec-os/render.yaml`.
3. Dashboard se secrets daalo:
   - `APP_PASSWORD` — strong password (public deploy par MUST)
   - `OPENROUTER_API_KEY` — tumhari key
   - `ALLOWED_TARGETS` — jaise `example.com,*.mysite.in` (khaali chhoda to har scan manual approval maangega)
4. Deploy → URL mil jayega: `https://ratansec-os-xxxx.onrender.com`

**Plan ka dhyan rakho:**
- **Free plan:** 512 MB RAM, idle timeout, ephemeral disk (reports restart par ud jaati hain). Sirf learning/testing ke liye.
- **Starter ($7/mo ≈ ₹600):** always-on, behtar CPU — real kaam ke liye.
- **Persistent disk** (paid): `render.yaml` me commented block uncomment karo — reports + audit bach jaate hain.
- Render par raw socket scans (nmap SYN/OS detection) limited hote hain; `-T4 -Pn -sV --open` style scans achhe chalte hain. Deeper scans ke liye VPS (Hetzner/DO) better hai.

---

## 7. Dashboard kaise use karo

| Tab | Kaam |
|---|---|
| **AI Chat** | "example.com ka quick recon karo", "open ports check karo", "mile findings ka report banao" — AI khud tools chalata hai. Quick-prompt chips bhi hain. |
| **Scan** | Target + profile choose karke direct scan. Plan preview dikhta hai; approval chahiye to card aata hai. |
| **Runs** | Live step-by-step output, cancel, **AI report banao**, delete. |
| **Reports** | Saari reports, markdown preview + `.md` download. |
| **Tools** | Kaunse tools installed hain, version, missing tools ke install commands (optional: dashboard se install — `ALLOW_INSTALL=1`). |
| **Audit** | Har event: logins, commands, approvals, reports. |

### Approval flow

```
AI/UI scan request
      │
      ├─ scope me hai + profile safe  → turant chal jaata hai (auto)
      ├─ scope khaali (manual mode)   → Approve/Deny card
      └─ sqlmap/hydra (intrusive)     → hamesha Approve/Deny card
```
Approve karne par scan chalta hai aur AI result aage analyze karke chat me jawab de deta hai.

---

## 8. Scan profiles

| Profile | Kya karta hai | Approx time |
|---|---|---|
| `quick` | whois + DNS + HTTP headers + nmap top-100 ports | 2–4 min |
| `web` | WhatWeb fingerprint + nmap HTTP scripts + Nikto + gobuster dir | 4–7 min |
| `network` | nmap top-1000 ports + service/version + default scripts | 5–8 min |
| `vuln` | nmap `vuln` scripts + Nuclei templates | 5–8 min |
| `webapp` | sqlmap (level 1, batch) + ffuf — **parameter wala URL chahiye**, approval required | 3–6 min |
| `full` | quick + web + vuln (sabse detailed) | 10–15 min |

---

## 9. CLI cheat-sheet

```bash
export RATANSEC_URL=https://your-app.onrender.com
export RATANSEC_PASSWORD='...'

python cli.py status                                   # server + AI + scope status
python cli.py tools                                    # tool availability
python cli.py profiles                                 # profiles list
python cli.py scan --target example.com --profile quick --wait
python cli.py scan --target example.com --profile full --wait --report
python cli.py runs                                     # recent runs
python cli.py show <run_id>                            # full output
python cli.py report <run_id> --name client-demo       # AI report banao
python cli.py chat "example.com ka web scan karo"      # AI copilot
python cli.py approvals                                # pending approvals
python cli.py approve <approval_id>
python cli.py audit --limit 50
```

---

## 10. REST API (apne app me integrate karo)

```bash
# login (cookie) — ya `Authorization: Bearer $APP_PASSWORD` use karo
curl -X POST http://localhost:8000/api/login -H 'Content-Type: application/json' \
     -d '{"password":"'"$APP_PASSWORD"'"}'

# scan start
curl -X POST http://localhost:8000/api/scan -H "Authorization: Bearer $APP_PASSWORD" \
     -H 'Content-Type: application/json' -d '{"target":"example.com","profile":"quick"}'

# AI chat (tool-calling ke saath)
curl -X POST http://localhost:8000/api/chat -H "Authorization: Bearer $APP_PASSWORD" \
     -H 'Content-Type: application/json' \
     -d '{"messages":[{"role":"user","content":"example.com ka recon karo"}],"conversation_id":"c1"}'
```

Full interactive docs: `/api/docs` (Swagger UI).

| Endpoint | Kaam |
|---|---|
| `GET /api/status` · `GET /api/meta` · `GET /api/health` | status/meta |
| `POST /api/login` · `POST /api/logout` | auth |
| `GET /api/tools` · `GET /api/profiles` | arsenal |
| `POST /api/scan` · `GET /api/runs` · `GET /api/runs/{id}` | scans |
| `POST /api/runs/{id}/cancel` · `DELETE /api/runs/{id}` | control |
| `POST /api/runs/{id}/report` | AI report generate |
| `GET /api/reports` · `GET /api/reports/{name}` | reports |
| `GET /api/approvals` · `POST /api/approvals/{id}` | human-in-the-loop |
| `GET /api/audit` | audit log |
| `POST /api/chat` · `GET /api/chat/followup/{conv}` | AI copilot |

---

## 11. Environment variables

| Variable | Default | Matlab |
|---|---|---|
| `APP_PASSWORD` | *(khaali)* | Dashboard/API password. Public deploy par MUST. |
| `OPENROUTER_API_KEY` | *(khaali)* | AI key — [openrouter.ai/keys](https://openrouter.ai/keys). |
| `MODEL` | `openai/gpt-4o-mini` | AI model id (koi bhi OpenRouter model). |
| `AI_MAX_STEPS` | `4` | Ek chat turn me max tool calls. |
| `ALLOWED_TARGETS` | *(khaali)* | Comma-separated allowlist: `example.com,*.site.in,10.0.0.0/24`. |
| `ALLOW_ANY_TARGET` | `1` | Allowlist khaali hone par bhi scan allowed (manual approval ke saath). |
| `ALLOW_LOCAL_TARGETS` | `1` | `localhost`/`127.0.0.1` allowed (lab). |
| `ALLOW_SCOPE_OVERRIDE` | `0` | Allowlist ke bahar wale target par logged-in override. |
| `APPROVAL_MODE` | *(auto)* | `auto` (scope par bina poochhe) / `manual` (har scan approval). |
| `MAX_SCAN_SECONDS` | `420` | Ek run ka total budget. |
| `MAX_CONCURRENT_SCANS` | `2` | Parallel scans (free tier par 1–2 rakho). |
| `ALLOW_INSTALL` | `0` | Dashboard se `apt-get install` allowed. |
| `DATA_DIR` | `./data` | Reports + audit log ka path (`/app/data` Docker me). |
| `PORT` / `HOST` | `8000` / `0.0.0.0` | Server bind. |

Poori list: [`.env.example`](.env.example).

---

## 12. AI setup (tumhari API key)

1. [openrouter.ai/keys](https://openrouter.ai/keys) → key banao (`sk-or-v1-...`).
2. `OPENROUTER_API_KEY=...` env me daalo (Render/VPS/docker-compose).
3. Model choose karo:

| Model id | Kab use karo | Rough cost |
|---|---|---|
| `openai/gpt-4o-mini` | default — sasta, tool-calling achha | ~$0.15 / $0.6 per 1M tokens |
| `openai/gpt-4o` | deep analysis | ~$2.5 / $10 per 1M |
| `anthropic/claude-3.5-sonnet` | best reasoning for reports | ~$3 / $15 per 1M |
| `google/gemini-flash-1.5` | bahut sasta, fast | ~$0.07 / $0.3 per 1M |
| `deepseek/deepseek-chat` | budget reasoning | ~$0.14 / $0.28 per 1M |

**Kharcha (realistic):** ek chat turn me ~3–8k tokens jaate hain. `gpt-4o-mini` par ek scan+analysis ≈ **₹0.2–1**. Roz 20 scans → **₹150–600/month**. Model override dashboard ke chat box se bhi kar sakte ho.

---

## 13. Security design (kyun yeh safe hai)

1. **No shell** — har command argv list ke roop me chalti hai (`shell=False`), isliye `; rm -rf /` jaisa injection impossible.
2. **Target validation** — host/IP/CIDR parse hota hai, forbidden characters reject, `-` se shuru hone wale values block.
3. **Hard blocks** — `169.254.0.0/16`, `169.254.169.254`, `metadata.google.internal`, `100.100.100.200` (cloud metadata) kabhi scan nahi honge → SSRF/credential-theft risk khatam.
4. **Scope allowlist** — allowlist ke bahar wale targets default me reject.
5. **Approval gates** — intrusive tools (sqlmap, hydra) aur scope-less mode me human confirmation.
6. **Limits** — per-step timeout, per-run budget, max parallel scans, output truncation (LLM context aur memory bachane ke liye).
7. **Auth + rate limits** — login attemps 10/5min, scan 12/min, chat 25/min.
8. **Audit** — sab kuch `data/audit.jsonl` me, posterity ke liye.
9. **AI guardrails** — system prompt me authorized-only rules; AI ke paas `confirmed=true` jaise bypass flags nahi hain (approval sirf insaan de sakta hai).

---

## 14. Project structure

```
ratansec-os/
├── app/
│   ├── config.py        # env-driven settings + .env loader
│   ├── security.py      # auth, scope allowlist, rate limits, metadata blocks
│   ├── tools.py         # tool registry + scan profiles
│   ├── executor.py      # argv-only command runner + run manager
│   ├── ai.py            # OpenRouter client + agent loop (tool calling) + guardrails
│   ├── approvals.py     # human-in-the-loop approvals
│   ├── report.py        # Markdown report builder
│   ├── server.py        # REST API routes
│   ├── webui.py         # FastAPI app + uvicorn runner
│   └── static/          # dashboard (index.html, styles.css, app.js — no frameworks)
├── cli.py               # terminal client (status/scan/chat/report/approve…)
├── scripts/entrypoint.sh
├── tests/smoke_test.py  # 50+ dependency-free checks
├── Dockerfile           # Kali + tools + app
├── docker-compose.yml
├── render.yaml          # Render blueprint
└── .env.example
```

---

## 15. Test karo

```bash
python3 tests/smoke_test.py                                  # 53 local checks
python3 tests/smoke_test.py --url http://localhost:8000 --token "$APP_PASSWORD"   # live server check
```

---

## 16. Troubleshooting

| Problem | Fix |
|---|---|
| Tools "missing" dikha rahe hain | Local install: `sudo apt-get install -y nmap nikto whatweb gobuster ffuf nuclei sqlmap hydra dirb`. Docker me sab pre-installed hai. |
| `nmap` "you don't have permission" | Container ko `--cap-add=NET_RAW --cap-add=NET_ADMIN` do, ya scans `-Pn -sT` (connect scan) use karein. |
| AI 401 / 402 / 429 | Key galat / credits khatam / rate limit. Dashboard banner aur `Runs → Report` output me exact message milta hai. |
| AI "model nahi mila" (404) | `MODEL` env me valid OpenRouter id daalo (jaise `openai/gpt-4o-mini`). |
| Scan bahut slow | `MAX_CONCURRENT_SCANS=1`, chhota profile (`quick`), ya `--top-ports` kam karo. |
| Render free par restart par reports gayab | Ephemeral disk hai — paid plan + disk mount `/app/data` karo. |
| Dashboard publicly khula hai | `APP_PASSWORD` set karo aur service restart karo. |

---

## 17. Roadmap

- **Plan A (25 MB core)** — `app/` + `cli.py` akele bhi chalte hain: local machine/phone (Termux) par AI + tool orchestration, tools on-demand install. Yani chhota core + cloud brain ka combo.
- **Plan B** — Alpine-based bootable mini ISO (~400–500 MB): real "remix OS" feel, USB/VM boot.
- **Plan C (yeh project)** — Kali Docker + AI dashboard: sabse advanced, cloud par.

Aage ke ideas: scheduled scans (cron), Slack/Telegram alerts, PDF reports, multi-user accounts, nuclei template auto-update, lab-VM integration.

---

## 18. Legal

RatanSec OS ek **authorized security testing** tool hai: apne systems, lab VMs, ya jinke paas likhit permission ho (bug bounty scope, client contract, CTF) — sirf unhi par chalayo. Scope allowlist aur approval gates ko seriously use karo. Galat use ki zimmedari user ki hai.

---

© Ratan Kumar Patel · Kali tools © Offensive Security / respective projects · MIT-style use at your own risk.
