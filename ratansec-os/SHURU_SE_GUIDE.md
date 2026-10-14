# 🟢 RatanSec OS — शुरू से चलाने की गाइड (ek-ek cheez, step-by-step)

Bhai, yeh guide **bilkul zero se** likhi hai. Har cheez ek-ek karke batayi hai:
kya chahiye → kahan se milega → kya command → **screen par kya dikhega (✅ CHECK)** → phir aage kya.

Bas ek baar 10-15 minute do. Uske baad rozana sirf **ek command / ek click**.

---

## ⏱️ शुरू करने से पहले (1 मिनट पढ़ लो)

**Yeh kya hai:** ek software jo tumhare computer (ya internet) par chalta hai. Jab chalu hota hai to tumhare **browser me ek dashboard** khulta hai. Usme tum Hinglish me likhte ho "example.com scan karo" — AI khud tools (nmap, nikto etc.) chalata hai, result samjhata hai, aur report bana deta hai.

**Do hisse hote hain — yeh yaad rakho:**
1. **Server** — jahan RatanSec OS chalega (tumhara computer, phone, cloud).
2. **Browser** — jahan tum use karoge (dashboard/CLI).

**Do zaroori baatein:**
- 🔴 **Sirf un targets par chalao** jinke liye permission hai (apna domain, practice lab, client contract). Bina permission scan karna **illegal** hai.
- 🟢 Chinta mat karo — app me safety built-in hai: scope allowlist + approval cards. Galat target par wo khud rok dega.

---

## 📋 PART 1 — Kya-kya chahiye? (checklist: ek-ek item)

### Item 1 — Ek device (inme se **koi ek** kaafi hai)
| Option | Kya hai | Kitna mushkil |
|---|---|---|
| **A** | Sirf browser wala computer/phone + internet | ⭐ Sabse aasan — **kuch install nahi** (RASTA A) |
| **B** | Windows laptop/PC | ⭐⭐ Aasan |
| **C** | Kali / Ubuntu / macOS laptop | ⭐⭐ Aasan (terminal use karna aata ho) |
| **D** | Android phone | ⭐⭐⭐ Thoda technical |

> **Bas ek device chahiye.** RAM 2 GB+ aur 500 MB free storage kaafi hai. Wahi device team A/B/C/D me se ek rasta choose kar legi (PART 2 me table hai).

### Item 2 — Internet
Chahiye — 2 kaam ke liye: (1) AI se baat karne ke liye, (2) galti se tools install karne ke liye. 2G se bhi chalega (slow).

### Item 3 — Python (ya Docker) — sirf RASTA B/C/D me
- **Python = ek program** jo is app ko chalata hai. Version **3.9 ya usse naya** chahiye.
- **Check kaise karo (abhi kar lo):**
  - **Windows:** Start → `cmd` type karo → Enter → likho: `python --version` → Enter
  - **Linux/macOS:** terminal kholo → likho: `python3 --version`
  - **Phone:** Termux me `python --version`
  - ✅ Agar `Python 3.10.12` jaisa kuch dikhe → **hai**. ❌ Agar `not found` / `not recognized` aaye → install karna padega (PART 4/5 me bataya hai).

### Item 4 — AI key (OpenRouter) — **yeh sabse important hai**
Yeh tumhari "AI ka access card" hai. Free me bhi ban jaati hai.

**Ek-ek click (8 clicks):**
1. Browser me kholo: **https://openrouter.ai**
2. Top-right me **"Sign in"** → **"Continue with Google"** → apna Gmail choose karo → Allow
3. Ab tum OpenRouter me log in ho gaye (free account ban gaya)
4. Upar right me **apna photo/icon** par click → **"Keys"** par click
   (ya seedha kholo: **https://openrouter.ai/keys**)
5. **"Create Key"** button dabao
6. **Name** me likho: `ratansec-os` → **"Create"** dabao
7. Ek lambi key dikhegi, aise: **`sk-or-v1-8f3c...................`**
   👉 **"Copy"** dabao aur **Notepad me paste karke rakh lo** (ye sirf ek baar dikhti hai)
8. (Paisa lagne se bachne ke liye) free models bhi hain — OpenRouter ke models list me `:free` likhe models free hote hain. Shuru me `MODEL=deepseek/deepseek-chat-v3.1:free` jaisa koi free model set kar sakte ho.

**Kharcha (agar paid model chalao):** ek scan+analysis ≈ ₹0.2–1. Roz 10 scan ≈ ₹60–300/mahina. Free models par ₹0.

> ⚠️ Key ko kisi ko mat do (jaise password hoti hai). Ye app usse **sirf AI calls** ke liye use karta hai.

### Item 5 — Ek target (jispar practice karega)
| Option | Kaise |
|---|---|
| **Apna domain** | tumhari website (jaise `ratan-patel.github.io`) — ye already tumhara hai |
| **Practice lab (best for learning)** | OWASP Juice Shop apne computer par: `docker run -d -p 3000:3000 bkimminich/juice-shop` → target: `http://localhost:3000` |
| **TryHackMe / HackTheBox** | free rooms/machines (unke rules ke andar rehna) |
| **Apna lab VM** | Kali me ek vulnerable VM (VulnHub) chalake us par |

### Item 6 — GitHub account (sirf RASTA A aur RASTA E ke liye)
Free hai: **https://github.com/signup** → username, email, password → verify. (Agar pehle se hai to skip.)

### ❌ Ye NAHI chahiye
- Hacking ka experience (AI sikha dega)
- Paisa (start me ₹0 me chal jaata hai)
- Coding knowledge (bas copy-paste)

---

## 🗺️ PART 2 — Apna rasta chuno (yeh table dekh kar decide karo)

| Rasta | Kiske liye | Kya install | Time | Kahin bhi chalta hai? |
|---|---|---|---|---|
| **A** — Browser only (GitHub Codespaces) | Sabse aasan, kuch install nahi | kuch nahi | 5 min | Haan (bas browser) |
| **B** — Windows | Windows laptop/PC | Python (1 click) | 10 min | Nahi (Windows par) |
| **B2** — Windows + asli tools | Poora Kali chahiye Windows me | WSL Kali | 20 min | Nahi |
| **C** — Kali / Ubuntu / macOS | Linux/mac users | Python + git | 5 min | Nahi |
| **D** — Android phone | Sirf phone hai | Termux | 10 min | Nahi |
| **E** — Cloud (Render free / VPS) | 24 ghante chalta rahe, kahin se access | kuch nahi (browser se) | 15 min | **Haan** |

> **Confusion?** Naya ho to **RASTA A** se shuru karo (Aaj: kuch install nahi, 5 minute, browser me dashboard). Baad me chaaho to RASTA E (cloud) par shift kar lo.

---

## 🅰️ RASTA A — Bina kuch install karo, sirf browser (5 min) ⭐ recommended for start

Isme tumhara "server" GitHub ke free cloud computer par chalega. Tumhare computer par **kuch bhi install nahi** hoga.

### A1. GitHub account banao
`https://github.com/signup` → username + email + password → verify email.

### A2. Project ko apne GitHub me "fork" karo (copy banao)
1. Kholo: **https://github.com/Ratan-patel/Ratan-patel.github.io**
2. Right side me **"Fork"** button → next page par **"Create fork"**
3. ✅ CHECK: URL ab `https://github.com/TUMHARA-USERNAME/Ratan-patel.github.io` ho gaya.

### A3. Cloud computer chalu karo (Codespace)
1. Us page par green **"Code"** button dabao
2. **"Codespaces"** tab → **"Create codespace on main"**
3. ✅ CHECK: browser me VS Code jaisa screen khulega, upar likha aayega "Setting up your codespace…"

### A4. Pehli baar ka wait (3–5 min) aur password note karo
- Neeche kaali **Terminal** me automatic sab install hoga (nmap, sqlmap, nikto waghera).
- ✅ CHECK: jab ye banner dikhe → sab ready:
  ```
  ╔══════════════════════════════════════════════════════════╗
  ║  RatanSec OS READY — dashboard chal raha hai             ║
  ╚══════════════════════════════════════════════════════════╝
     Dashboard:  Ports tab → port 8000 ke aage globe icon par click karo
     Password:   wVmvZVsmxATf        ← ye tumhara password hai, likh lo
     AI:         OFF — key add karne ke liye …
  ```
- ❌ Banner nahi dikha? Terminal me ye chalao: `bash ratansec-os/scripts/codespace-start.sh`

### A5. Dashboard kholo
1. VS Code me neeche **"PORTS"** tab par click karo
2. Wahan **Port 8000** dikhega, aage **"Open in Browser"** (globe 🌐 icon) — us par click karo
3. ✅ CHECK: login screen khulega → **A4 wala password** daalo → dashboard!

### A6. AI on karo (key daalo)
Terminal me:
```bash
nano ratansec-os/.env
```
→ `OPENROUTER_API_KEY=` ke aage apni key paste karo (Item 4 wali) →
save karo: **Ctrl+O**, Enter, phir **Ctrl+X** → phir restart:
```bash
bash ratansec-os/scripts/codespace-start.sh
```
✅ CHECK: dashboard ke top par `AI: <model>` **green** ho gaya (page refresh karo).

### A7. Codespaces ke rules (paise ka dhyan)
- Free account me mahine ke ~60–120 hours free — bas **kaam khatam hone par Codespace Stop kar do**, aur learning ke baad **Delete** kar do.
- Stop karne ke liye: VS Code me neeche-left gear/… menu → "Stop Current Codespace"
- Ye rasta **practice/seekhne** ke liye best hai. Roz 24x7 chahiye → RASTA E (cloud).

➡️ Ab **PART 8** par jao (pehla scan).

---

## 🅱️ RASTA B — Windows laptop/PC (10 min)

### B1. Python install karo
1. Kholo: **https://www.python.org/downloads/** → bada peela button **"Download Python 3.x.x"**
2. Download hui file (`python-3.x.x-amd64.exe`) par double-click
3. ⚠️ **Sabse important:** pehli screen par niche ek checkbox hai —
   **☑ "Add python.exe to PATH"** — is par **tick lagao**
4. Phir **"Install Now"** → wait → **"Close"**
5. ✅ CHECK: Start → `cmd` → Enter → likho `python --version` → Enter → `Python 3.12.4` jaisa dikhna chahiye.
   - ❌ Agar "not recognized" aaye → PART 9, Error #1.

### B2. Project download karo
1. Kholo: **https://github.com/Ratan-patel/Ratan-patel.github.io**
2. Green **"Code"** button → **"Download ZIP"**
3. Downloads me file aayegi: `Ratan-patel.github.io-main.zip` → right-click → **"Extract All…"** → **Extract**
4. ✅ CHECK: ek folder bana: `Ratan-patel.github.io-main` → uske andar **`ratansec-os`** folder dikhega.

### B3. Ek click me chalu karo
1. `ratansec-os` folder kholo
2. **`start-windows.bat`** par **double-click**
3. Pehli baar ek kali window khulegi aur dependencies install hongi (1–2 min)

### B4. Notepad me password + AI key daalo
- Automatic **Notepad** khulega (file ka naam `.env`)
- Do lines edit karo:
  ```
  APP_PASSWORD=mera-password-123          ← apna password likho (yaad rakhna)
  OPENROUTER_API_KEY=sk-or-v1-..........  ← Item 4 wali key paste karo
  ```
- Save: **Ctrl + S** → Notepad band karo
- ✅ CHECK: kali window me aage chalega aur browser khud khul jayega.

### B5. Browser me login
1. Browser me: **http://localhost:8000**
2. Password daao (B4 me jo likha) → **Unlock**
3. ✅ CHECK: dashboard khul gaya! Upar `AI:` green hona chahiye.
   - Agar `AI: off` hai → `.env` me key galat/paste nahi hui → B4 dobara karo, phir `start-windows.bat` dobara chalao.

### B6. Rozana ka tarika
- **Chalu:** `start-windows.bat` par double-click
- **Band:** us kali window me **Ctrl + C**, ya window band kar do
- Bas itna hi. Dashboard: `http://localhost:8000`

### B7. Ni: is mode me tools nahi hain?
RASTA B me dashboard + AI chalega, par `nmap`, `sqlmap` waghera Windows me nahi hote — un steps par **"skipped"** likha aayega (app phir bhi kaam karega).
**Asli tools chahiye to B2 (WSL Kali) karo — 20 minute:**

1. **PowerShell admin** kholo: Start → `powershell` type → right-click → **Run as administrator**
2. Type karo: `wsl --install -d kali-linux` → Enter → (restart maange to restart karo)
3. Restart ke baad Start menu → **Kali Linux** → terminal khulega → username + password set karo
4. Kali terminal me ye 3 lines ek-ek karke:
   ```bash
   sudo apt update && sudo apt install -y python3-venv python3-pip git
   git clone https://github.com/Ratan-patel/Ratan-patel.github.io.git
   cd Ratan-patel.github.io/ratansec-os && chmod +x setup.sh start.sh scripts/*.sh
   ```
5. Phir (key apni daalo):
   ```bash
   ./setup.sh --with-tools --key sk-or-v1-TERI-KEY
   ```
6. ✅ CHECK: `Dashboard (iss machine par): http://localhost:8000` + `Password: xxxxx`
7. Windows browser me `http://localhost:8000` kholo → password → **login**
8. **Rozana:** Start menu → Kali → `cd ~/Ratan-patel.github.io/ratansec-os && ./start.sh` · **Band:** Ctrl+C

➡️ Ab **PART 8** par jao (pehla scan).

---

## 🅲 RASTA C — Kali / Ubuntu / Parrot / Debian / macOS (5 min)

### C1. Terminal kholo
- **Kali/Ubuntu:** `Ctrl + Alt + T` (ya top-left me Terminal icon)
- **macOS:** `Cmd + Space` → "Terminal" → Enter

### C2. Python check karo
```bash
python3 --version
```
✅ `Python 3.10.12` jaisa dikhe → aage badho.
❌ Nahi mila → `sudo apt install -y python3 python3-venv python3-pip` (macOS: `brew install python`)

### C3. Project laao (3 commands, ek-ek karke)
```bash
cd ~
git clone https://github.com/Ratan-patel/Ratan-patel.github.io.git
cd Ratan-patel.github.io/ratansec-os
```
✅ CHECK: `ls` chalao → `setup.sh`, `start.sh`, `app`, `cli.py` dikhne chahiye.
❌ `git: command not found` → `sudo apt install -y git`

### C4. Ek command me setup + start
```bash
chmod +x setup.sh start.sh scripts/*.sh
./setup.sh --with-tools --key sk-or-v1-TERI-KEY
```
Yeh khud karega: Python check → `.venv` + dependencies → tools install (sudo password maangega — apna computer ka password daalo) → `.env` bana dega → server start.

### C5. ✅ CHECK — ye dikhna chahiye
```
  Dashboard (iss machine par):  http://localhost:8000
  Phone / dusre device se:      http://192.168.1.5:8000  (same WiFi)
  Password:                     xxxxxxxx
```
Browser me us URL (ya `http://localhost:8000`) kholo → password → **login**.

### C6. Rozana
```bash
cd ~/Ratan-patel.github.io/ratansec-os && ./start.sh
```
- **Band:** `Ctrl + C`
- **Key baad me add karni ho:** `nano .env` → `OPENROUTER_API_KEY=...` → save (Ctrl+O, Enter, Ctrl+X) → `./start.sh` dobara

➡️ Ab **PART 8** par jao (pehla scan).

---

## 🅳 RASTA D — Android phone (Termux) (10 min)

### D1. Termux install karo
- **F-Droid** se: https://f-droid.org/packages/com.termux/ → Download → Install
  (Play Store wala purana version hai — usme kuch cheezein fail hoti hain, isliye F-Droid use karo)
- Phone me "Install unknown apps" allow karna pad sakta hai: Settings → Apps → F-Droid → Allow.

### D2. Termux kholo aur ye ek-ek line chalao
```bash
pkg update -y
pkg install -y python git nmap curl whois dnsutils
termux-setup-storage
```
(Storage permission maangega → **Allow** dabao)

### D3. Project laao
```bash
cd ~
git clone https://github.com/Ratan-patel/Ratan-patel.github.io.git
cd Ratan-patel.github.io/ratansec-os
```

### D4. Setup chalao
```bash
chmod +x setup.sh start.sh scripts/*.sh
./setup.sh --no-tools --key sk-or-v1-TERI-KEY
```
(Phone me saare tools nahi milte — nmap/curl/whois kaam karenge, baaki steps "skipped" dikhenge. Koi dikkat nahi.)

### D5. ✅ CHECK
```
  Dashboard (iss machine par):  http://localhost:8000
  Password:                     xxxxxxxx
```
**Chrome** kholo → `http://localhost:8000` → password → **login** 🎉

### D6. Rozana
```bash
cd ~/Ratan-patel.github.io/ratansec-os && ./start.sh
```
- **Band:** `Ctrl + C`
- Phone ko kai baar ye chalta rehna ho: Termux me `termux-wake-lock` chala do.
- Chhota tip: Termux me long-press → "More" → "Style" se font chhota kar lo, sab aaram se dikhega.

➡️ Ab **PART 8** par jao (pehla scan).

---

## 🅴 RASTA E — Hamesha chalu (cloud me) — Render / VPS

### E1. Render par (free se, browser se hi ho jayega)
1. GitHub account banao (Item 6) → project **Fork** karo (A2 jaisa)
2. Kholo **https://render.com** → **"Get Started"** → **"GitHub"** se sign in karo → Allow
3. Dashboard me **"New +"** → **"Blueprint"**
4. Apna repo (`TUMHARA-USERNAME/Ratan-patel.github.io`) select karo → Render khud config padh lega → **"Apply"** / **"Create"**
5. Ab **Environment** me 3 values daalo (ye zaroori hai):
   | Key | Value |
   |---|---|
   | `APP_PASSWORD` | `mera-strong-password` (apna rakho) |
   | `OPENROUTER_API_KEY` | `sk-or-v1-.......` |
   | `ALLOWED_TARGETS` | `tera-domain.com` (khaali chhoda to har scan par approval maangega) |
6. **"Save"** → deploy chalega (5–10 min). Logs me `RatanSec OS 1.0.0 ready` dikhe to ✅
7. Upar wala URL kholo: `https://ratansec-os-xxxx.onrender.com` → password → **login** 🎉

**Dhyan:**
- Free plan 15 min idle ke baad so jaata hai (pehli load 30–60 sec). Starter (~₹600/mo) always-on.
- Free par reports restart par ud jaati hain (ephemeral disk). Permanent chahiye to paid plan + disk (`render.yaml` me comment khol lo).

### E2. VPS par (Hetzner/DigitalOcean/Oracle free)
1. VPS banao (Ubuntu 22.04) → IP milega
2. Computer ke terminal me: `ssh root@TUMHARA-IP` (password daalo)
3. Phir ek-ek:
   ```bash
   apt update && apt install -y git python3-venv python3-pip screen
   git clone https://github.com/Ratan-patel/Ratan-patel.github.io.git
   cd Ratan-patel.github.io/ratansec-os
   chmod +x setup.sh start.sh scripts/*.sh
   screen -S ratansec
   ./setup.sh --with-tools --key sk-or-v1-TERI-KEY --port 8000
   ```
4. Server chalu hone par: `Ctrl + A` phir `D` (ye "detach" karta hai — background me chalta rahega)
5. Wapas aane ke liye: `screen -r ratansec` · Band karne ke liye: `screen -r ratansec` phir `Ctrl+C`
6. Dashboard: `http://TUMHARA-IP:8000` (firewall me port kholna: `ufw allow 8000`)

➡️ Ab **PART 8** par jao (pehla scan).

---

## 🎯 PART 8 — Pehla scan (ek-ek click) — sab raste same hai

Server kahin bhi chal raha ho (Windows/phone/cloud), browser me ye karo:

1. **Dashboard kholo** → password daalo → login. (Pehli screen: "AI Chat" tab)
2. Neeche **text box** me likho (Hinglish chalega):
   ```
   example.com ka quick recon karo
   ```
   👉 `example.com` ki jagah **apna authorized target** likho (apna domain ya `http://localhost:3000` Juice Shop).
3. **Enter** dabao → AI "Soch raha hoon…" dikhayega → phir wo khud tools chalayega.
4. Pehli baar **peela card** aa sakta hai: **"⚠️ Approval chahiye"** → usme **"Approve & run"** dabao.
   *(Ye safety hai: jab scope allowlist khaali ho, app pehle tumse permission leta hai.)*
5. Scan chalega — **"Runs"** tab me live output step-by-step dikhega:
   ```
   [running] nmap   Nmap top-100 ports — example.com
   [done   ] nmap   …
   ```
6. Khatam hone par AI findings samjhayega: open ports, versions, headers, interesting paths.
7. **Report banane ke liye:** "Runs" tab → run select karo → **"AI report banao"** button → phir **Reports** tab me jaake padho/download karo (`.md` file).

**Bina AI, seedha scan bhi kar sakte ho:** "Scan" tab → target + profile (`quick`) → **Start scan**.

**CLI se (terminal me) agar chaaho:**
```bash
export RATANSEC_URL=http://localhost:8000
export RATANSEC_PASSWORD='tera-password'
python cli.py status
python cli.py scan --target example.com --profile quick --wait --report
```

---

## 🆘 PART 9 — Galti ho jaye to (error → kya karo)

| # | Jo screen par likha aaye | Matlab | Kya karo |
|---|---|---|---|
| 1 | `'python' is not recognized` (Windows) | Python ka PATH tick nahi tha | Python dobara install karo aur **"Add python.exe to PATH"** pe TICK lagao. Ya `py --version` try karo |
| 2 | `Permission denied` (Linux/mac) | Script executable nahi | `chmod +x setup.sh start.sh scripts/*.sh` |
| 3 | `Address already in use` | Port 8000 busy | `PORT=9000 ./start.sh` (phir `http://localhost:9000`), ya purana band karo: `pkill -f app.webui` |
| 4 | Dashboard khulta hai, par sab tools `skipped` | Tools install nahi hain | `bash scripts/install-tools.sh` (Linux/WSL). Windows-only me tools nahi aate → WSL Kali karo (B2) |
| 5 | Top par `AI: off` | Key nahi mili | `.env` me `OPENROUTER_API_KEY=sk-or-v1-...` daalo → restart |
| 6 | Chat me `401` ya "API key galat" | Key galat/copy adhoori | Key dobara copy karo (poori `sk-or-v1-` se shuru) |
| 7 | Chat me `402` | OpenRouter me credits khatam | openrouter.ai → Credits me add karo, ya `.env` me free model: `MODEL=deepseek/deepseek-chat-v3.1:free` |
| 8 | Chat me `404` / "model nahi mila" | Model id galat | `.env`: `MODEL=openai/gpt-4o-mini` |
| 9 | Password bhool gaya | — | Terminal me: `grep APP_PASSWORD .env` (jis folder me project hai) |
| 10 | Terminal band kiya → dashboard band | Server usi terminal me chal raha tha | Normal hai. Dobara `./start.sh` (VPS par `screen` use karo) |
| 11 | Phone se `localhost:8000` nahi khulta (computer par chala rahe ho) | localhost sirf usi device par chalta hai | `./start.sh` me jo "Phone / dusre device se" wala IP dikha (jaise `http://192.168.1.5:8000`) wahi phone me kholo (same WiFi) |
| 12 | Render par 30-60 sec lagta hai | Free plan cold start | Normal. Ya Starter plan lo |
| 13 | Termux me `pkg` error | Purana cache | `pkg update -y` dobara, ya Termux/phone restart karo |
| 14 | Kuch aur samajh nahi aa raha | — | Screenshot/error copy karke mujhe bhej do, main fix bata dunga |

---

## ✅ PART 10 — Final checklist (tick karo, aage badho)

- [ ] **Item 4** — OpenRouter key ban gayi (`sk-or-v1-…` notepad me hai)
- [ ] **Rasta chuna** (A / B / C / D / E)
- [ ] **Server chalu** (terminal me `Uvicorn running on …` ya Codespaces me banner)
- [ ] **Browser me dashboard login** ho gaya (password kaam kiya)
- [ ] Top par **`AI: gpt-4o-mini` green** hai
- [ ] **Pehla scan** chal gaya (approval card approve kiya)
- [ ] **Pehli report** ban gayi (Reports tab me dikh rahi hai)

Saare tick? **Mubarak ho — tumhara apna AI pentest environment chalu hai!** 🎉

Ab practice shuru karo (legal targets): apna domain, OWASP Juice Shop (`http://localhost:3000`), ya TryHackMe rooms. Aur AI se poochhte raho — wo tumhara senior pentester hai: *"nikto ke output me misconfig kaise dhundhu?"* jaisa bhi puchh sakte ho.

---

## 🔁 Ek line ka recap (rozana ke liye)

| Rasta | Chalu karna | Band karnaa |
|---|---|---|
| A (Codespaces) | Codespace kholo → terminal me `bash ratansec-os/scripts/codespace-start.sh` | "Stop Current Codespace" |
| B (Windows) | `start-windows.bat` double-click | band window: Ctrl+C |
| C (Linux/mac) | `cd ~/Ratan-patel.github.io/ratansec-os && ./start.sh` | Ctrl+C |
| D (Termux) | `cd ~/Ratan-patel.github.io/ratansec-os && ./start.sh` | Ctrl+C |
| E (cloud) | khud chalta rehta hai (Render) / `screen -r ratansec` (VPS) | Render: Suspend · VPS: Ctrl+C |
