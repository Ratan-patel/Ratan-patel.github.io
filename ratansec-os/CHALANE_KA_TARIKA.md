# 🚀 RatanSec OS — Aaunga kaise, chalaunga kaise (poora guide)

Bhai, tension mat le. Neeche **4 tarike** diye hain. Apna wala choose kar aur bas copy-paste kar de. Har step me likha hai kya type karna hai.

## Pehle: tujhe sirf 3 cheezein chahiye

| # | Cheez | Kahan se | Cost |
|---|---|---|---|
| 1 | **Computer / phone** | Tera laptop, PC ya Android phone | — |
| 2 | **AI API key** (OpenRouter) | [openrouter.ai/keys](https://openrouter.ai/keys) → signup (Google login) → "Create Key" | Free credits se shuru, baad me ~₹150–600/mo |
| 3 | **Target** (jispar practice karega) | Apna domain, ya practice lab (neeche list hai) | — |

⚠️ **Yaad rakhna:** bina likhit permission kisi website/server ko scan karna **illegal** hai (India me IT Act). Practice labs ya apne domains par hi chalao.

---

# 🅰️ TARIKA 1 — Windows laptop (sabse aasan, 10 min)

### Option 1a — Sirf dashboard + AI (bina hacking tools)

Ismein AI chat chalega, scans bhi chalenge par **tools (nmap etc.) nahi milenge** — output me "skipped" dikhega. Practice/UI dekhne ke liye yeh theek hai.

1. **Python install karo:** [python.org/downloads](https://www.python.org/downloads/) → "Download Python 3.x" → installer chalao → **"Add python.exe to PATH" pe tick** karo → Install.
2. **Repo download karo:** GitHub page → green "Code" button → "Download ZIP" → extract karo (jaise `C:\Users\TeraNaam\ratansec-os`).
3. **`start-windows.bat` par double-click** karo (ratansec-os folder ke andar hai).
4. Pehli baar `.env` file khulegi Notepad me — usme ye do lines bharo:
   ```
   APP_PASSWORD=mera-password-123
   OPENROUTER_API_KEY=sk-or-v1-xxxxxxxx
   ```
   Save karo → Notepad band karo → bat file dobara double-click.
5. Browser khud khul jayega: **http://localhost:8000** → password daalo → ho gaya! 🎉

### Option 1b — Poora Kali + saare hacking tools (recommended)

Windows ke andar hi asli Kali chalao (WSL = Windows Subsystem for Linux). Ismein **nmap, nikto, sqlmap, hydra sab kaam karenge**.

**Step 1** — PowerShell **admin** me kholo (Start → "PowerShell" → right click → Run as administrator) aur type karo:
```powershell
wsl --install -d kali-linux
```
Restart maange to karo. Phir Kali ka username/password set karo.

**Step 2** — Start menu se **Kali Linux** kholo (terminal khulega) aur ye paste karo:
```bash
sudo apt update && sudo apt install -y python3-venv python3-pip git
```

**Step 3** — Project WSL ke home me laao (ZIP download kiya tha to):
```bash
# Windows Downloads se copy (apna path sahi karo)
cp -r /mnt/c/Users/TeraNaam/Downloads/ratansec-os ~/
cd ~/ratansec-os
```
Ya seedha clone karo:
```bash
cd ~ && git clone https://github.com/Ratan-patel/Ratan-patel.github.io.git
cd Ratan-patel.github.io/ratansec-os
```

**Step 4** — Ek hi command me setup (Python env + tools + config):
```bash
./setup.sh --with-tools
```
Yeh khud: Python check karega → dependencies install karega → `apt` se tools install karega → password generate karega → server start kar dega.

**Step 5** — Terminal me ye dikhega:
```
Dashboard (iss machine par):  http://localhost:8000
Password:                     xxxxxxxx
```
Windows browser me `http://localhost:8000` kholo → password daalo → **ready!**

**AI on karna hai?** Alag terminal me:
```bash
nano .env      # OPENROUTER_API_KEY=sk-or-v1-... line bharo → Ctrl+O, Enter, Ctrl+X
./start.sh     # restart
```

**Band kaise karein:** terminal me `Ctrl + C`.
**Dobara chalane ke liye:** bas `cd ~/ratansec-os && ./start.sh`

---

# 🅱️ TARIKA 2 — Kali / Ubuntu / Parrot / macOS terminal

```bash
# 1) Project laao
git clone https://github.com/Ratan-patel/Ratan-patel.github.io.git
cd Ratan-patel.github.io/ratansec-os

# 2) One-command setup (tools ke saath)
./setup.sh --with-tools --key sk-or-v1-TERI-KEY

# bas! Server start ho gaya → browser: http://localhost:8000
```

Flags jo kaam ke hain:
```bash
./setup.sh                      # interaktive (tools install poochega)
./setup.sh --with-tools         # tools bhi install karo
./setup.sh --no-tools           # sirf app, tools baad me
./setup.sh --key sk-or-v1-xxx   # AI key daal do
./setup.sh --password mera123   # apna password
./setup.sh --port 9000          # dusra port
./setup.sh --no-start           # sirf setup, start mat karo
```

Band karna: `Ctrl + C` · Dobara chalana: `./start.sh`

**Docker wale (Kali + sab tools pre-installed):**
```bash
cp .env.example .env && nano .env      # password + key bharo
docker compose up -d --build           # pehli build 5-10 min
# → http://localhost:8000 ; band: docker compose down
```

---

# 🅲 TARIKA 3 — Android phone (Termux) — bina laptop

1. **Termux install karo** — [F-Droid](https://f-droid.org/packages/com.termux/) se (Play Store wala purana hai, usme kuch kaam nahi karta).
2. Termux kholo aur ye paste karo:
```bash
pkg update -y && pkg install -y python git nmap curl whois dnsutils
termux-setup-storage        # permission maangega → Allow
```
3. Project laao:
```bash
cd ~ && git clone https://github.com/Ratan-patel/Ratan-patel.github.io.git
cd Ratan-patel.github.io/ratansec-os
./setup.sh --key sk-or-v1-TERI-KEY
```
4. Phone ke browser me **http://localhost:8000** kholo → password → chal gaya! 📱

Termux me saare tools nahi milte (nikto/gobuster skip ho sakte hain) — jo milega wahi chalega, baaki "skipped" dikhega. Sirf AI chat + nmap + curl + whois chahiye to ye best hai.

> Phone ko background me chalate rehna ho: Termux me `termux-wake-lock` chala do (notification me "Acquire wakelock" bhi kar sakta hai).

---

# 🅳 TARIKA 4 — Cloud par (kabhi bhi, kahin se — asli plan)

## D1. Render (free se shuru) — dashboard internet par

1. Repo GitHub par hona chahiye → [github.com/Ratan-patel/Ratan-patel.github.io](https://github.com/Ratan-patel/Ratan-patel.github.io) (already hai ✅)
2. [render.com](https://render.com) → GitHub se signup
3. **New +** → **Blueprint** → repo select karo → Render khud `ratansec-os/render.yaml` dhundh lega → **Apply**
4. Deploy shuru hote hi **Environment** tab me ye 3 secrets daalo:
   ```
   APP_PASSWORD       = mera-strong-password
   OPENROUTER_API_KEY = sk-or-v1-xxxx
   ALLOWED_TARGETS    = tera-domain.com,*.tera-lab.com
   ```
5. Save → deploy complete hone ka wait (~5-10 min) → upar wala URL kholo: `https://ratansec-os-xxxx.onrender.com` → password → **chal gaya!**

**Dhyan rakho:**
- Free plan 15 min idle ke baad so jaata hai (pehli load 30-60 sec slow). Starter ($7 ≈ ₹600/mo) always-on.
- Free par **reports restart pe gayab** ho jaati hain (ephemeral disk).
- Node ke liye: `ALLOWED_TARGETS` khaali chhod diya to har scan manual approval maangega (safety default).
- Cloud par tools connected-environment par nahi chalti — **internet wale authorized domains** par hi scans karo.

## D2. VPS (Hetzner / DigitalOcean / Oracle free tier) — full power

```bash
# 1) VPS me SSH karo
ssh root@YOUR_SERVER_IP

# 2) Setup (Ubuntu 22.04+ / Kali / Debian)
apt update && apt install -y git python3-venv python3-pip
git clone https://github.com/Ratan-patel/Ratan-patel.github.io.git
cd Ratan-patel.github.io/ratansec-os
./setup.sh --with-tools --key sk-or-v1-TERI-KEY --port 8000

# 3) 24x7 background me chalane ke liye (screen)
apt install -y screen
screen -S ratansec ./start.sh        # Ctrl+A, D = detach (background me chalta rahega)
# wapas aane ke liye: screen -r ratansec
```
Dashboard: `http://YOUR_SERVER_IP:8000` (VPS ke firewall me port 8000 allow karo, ya `ufw allow 8000`).

**Docker wala VPS (Kali + sab tools):**
```bash
curl -fsSL https://get.docker.com | sh
git clone https://github.com/Ratan-patel/Ratan-patel.github.io.git
cd Ratan-patel.github.io/ratansec-os && cp .env.example .env && nano .env
docker compose up -d --build
```

---

# 🔑 AI key add karna (sabse important)

1. [openrouter.ai](https://openrouter.ai) → Sign up (Google se sekund me) → **Keys** → **Create Key** → copy karo (`sk-or-v1-...`).
2. Free me bhi chal jaata hai; ₹ kam lagti hai kyunki `gpt-4o-mini` sasta hai.
3. Key daalne ke 2 tarike:
   - **Local:** `nano .env` → `OPENROUTER_API_KEY=sk-or-v1-xxxx` → save → restart (`./start.sh`)
   - **Render:** Dashboard → Environment → Add Env Var → Save (automatic redeploy)
4. Verify: dashboard ke top par **`AI: gpt-4o-mini`** green dikhna chahiye. Laal ho to key galat/missing hai.

**Model badalna:** `.env` me `MODEL=anthropic/claude-3.5-sonnet` ya `MODEL=google/gemini-flash-1.5` etc.

---

# 🎮 Ab actually kaise use karein (roz ka kaam)

## Dashboard se (browser)

| Tab | Karo kya |
|---|---|
| **🧠 AI Chat** | Hinglish me likho: *"example.com ka quick recon karo"* → AI khud tools chalata hai aur findings samjhata hai |
| **🎯 Scan** | Target daalo + profile choose karo → Start. Profile: quick (2-4 min) / web / network / vuln / full |
| **📡 Runs** | Live output step-by-step. **AI report banao** button yahin hai. Cancel bhi |
| **📄 Reports** | AI analysis wali report, download `.md` |
| **🧰 Tools** | Kaunsa tool ready hai + version. Missing ka install command |
| **🔍 Audit** | Har command ka record (evidence) |

**Approval card:** sqlmap/hydra wale scan ya scope-less target par yellow card aayega → **Approve** karo to scan chalega, **Deny** karo to ruk jayega. Yeh safety ke liye hai.

## Terminal (CLI) se — server chal raha ho tab

```bash
export RATANSEC_URL=http://localhost:8000     # ya render wala URL
export RATANSEC_PASSWORD='tera-password'

python cli.py status                                     # sab status
python cli.py tools                                       # kaunse tools hain
python cli.py scan --target example.com --profile quick --wait     # scan + live output
python cli.py scan --target example.com --profile full --wait --report   # + AI report
python cli.py chat "example.com ke open ports check karo"  # AI copilot terminal se
python cli.py runs                                          # purane scans
python cli.py report <run_id> --name client-demo             # report banao
python cli.py approvals                                     # pending approvals
python cli.py approve <approval_id>
python cli.py audit                                          # command history
```

## API se (apni website/app me)

```bash
curl -X POST http://localhost:8000/api/chat -H "Authorization: Bearer TeraPassword" \
  -H 'Content-Type: application/json' \
  -d '{"messages":[{"role":"user","content":"example.com ka recon karo"}],"conversation_id":"c1"}'
```
Poori interactive docs: **http://localhost:8000/api/docs**

---

# 🧪 Practice kahan karein (legal targets)

| Platform | Kya hai | Kaisa start |
|---|---|---|
| **OWASP Juice Shop** | Apne laptop par vulnerable app | `docker run -d -p 3000:3000 bkimminich/juice-shop` → target: `http://localhost:3000` |
| **TryHackMe** | Guided rooms (beginner best) | tryhackme.com → free rooms |
| **Hack The Box** | Real-ish machines | hackthebox.com (starting point free) |
| **PortSwigger Academy** | Web security labs (free) | portswigger.net/web-security |
| **VulnHub / VulnLab** | Local VMs practice | vulnhub.com |
| **Apna domain** | Apni website/hosting | bas apna domain scan karo |

Example (Juice Shop ko ethically scan karna):
```bash
docker run -d -p 3000:3000 bkimminich/juice-shop
python cli.py scan --target http://localhost:3000 --profile web --wait --report
```

---

# 🆘 Problem aaye to (troubleshooting)

| Error / Problem | Solution |
|---|---|
| `Permission denied: ./setup.sh` | `chmod +x setup.sh start.sh scripts/*.sh` phir dobara chalao |
| `python3: command not found` | Kali/Ubuntu: `sudo apt install -y python3 python3-venv python3-pip` · Termux: `pkg install python` |
| `venv nahi bana` / `ensurepip` error | `sudo apt install -y python3-venv python3-pip` |
| `Address already in use` (port 8000 busy) | `./start.sh` ki jagah: `PORT=9000 ./start.sh` ya purana process band karo: `pkill -f app.webui` |
| Dashboard khulta hai par **sab tools "skipped"** | Tools install nahi hain → `bash scripts/install-tools.sh` (ya Docker image use karo) |
| `nmap: you don't have permission` | App khud `-sT` (connect scan) laga deta hai; phir bhi error aaye to `NMAP_FORCE_CONNECT=1` set karo |
| `AI: off` / chat me key error | `.env` me `OPENROUTER_API_KEY` bharo → restart. 402 aaye to OpenRouter me credits add karo |
| Chat me "model nahi mila" (404) | `.env` me `MODEL=openai/gpt-4o-mini` kar do |
| Login page par password nahi pata | `grep APP_PASSWORD .env` (agar `.env` nahi hai to auth off hai — koi password nahi maangega) |
| Render par "Application failed to respond" | Free plan cold start — 60 sec wait karo; phir bhi na chale to Render ke **Logs** tab dekho |
| Render par reports restart pe gayab | Free plan ka ephemeral disk — paid plan + disk mount `/app/data` karo |
| Scan bahut slow | `quick` profile use karo, `MAX_CONCURRENT_SCANS=1` |
| Termux me pip fail | `pkg install python-pip` phir `./setup.sh` |

Quick self-test (sab theek hai ya nahi):
```bash
python3 tests/smoke_test.py                                  # 55 checks (offline)
python3 tests/smoke_test.py --url http://localhost:8000 --token "$APP_PASSWORD"   # server live hai ya nahi
```

---

# 📋 Ek line me summary

| Tera situation | Kya karo |
|---|---|
| Windows, jaldi chahiye | Repo ZIP → `start-windows.bat` double-click |
| Windows + asli tools chahiye | `wsl --install -d kali-linux` → `./setup.sh --with-tools` |
| Kali/Ubuntu already hai | `git clone` → `./setup.sh --with-tools` |
| Phone se | Termux → `./setup.sh` |
| 24x7 internet par | Render Blueprint (free) ya VPS + `screen` |
| Sabse professional | VPS + Docker (full Kali image) |

Har case me aakhri step same hai: **browser me `http://localhost:8000` (ya Render wala URL) kholo → password → kaam shuru.**
