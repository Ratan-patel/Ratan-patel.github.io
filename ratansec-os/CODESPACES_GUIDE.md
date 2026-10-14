# 🌐 RASTA A (सबसे आसान) — बिना कुछ install किए, सिर्फ browser se chalao

**Ye guide un ke liye hai jo kuch install nahi karna chahte.** Tumhara "server" GitHub ke free cloud computer par chalega, aur tumhare computer/phone par **kuch bhi nahi** hoga.

⏱️ **Pehli baar: 8–12 minutes.** Uske baad roz: **1 click**.

---

## ✅ Shuru karne se pehle 2 cheezein ready rakho

| # | Cheez | Kahan se |
|---|---|---|
| 1 | **GitHub account** (logged in) | Already hai (tumhara repo GitHub par hai) → browser me github.com kholo, logged in ho |
| 2 | **AI key** (OpenRouter) | openrouter.ai → Google se login → https://openrouter.ai/keys → "Create Key" → `sk-or-v1-...` **Notepad me copy** kar lo |

> AI key abhi nahi hai? Koi baat nahi — pehle dashboard chalu karo (scan kaam karenga), key baad me Part 5 me daal dena.

---

## 📍 PART 1 — Codespace banao (cloud computer) — 5 clicks

1. Browser me kholo: **https://github.com/Ratan-patel/Ratan-patel.github.io**
   *(Ye tumhara apna repo hai — login rehna zaroori hai, warna Code button nahi dikhega)*

2. Page par **hara (green) "Code" button** dabao — ye page ke upar-right side me hota hai, "Add file" ke paas

3. Us popup me 3 tabs dikhenge: `Local` · `Codespaces` · (kuch aur)
   👉 **"Codespaces"** tab par click karo

4. Usme likha hoga: **"Create codespace on main"** — par humein **branch** chunna hai kyunki naya code abhi `main` me nahi aaya:
   - Button ke aage **"…"** (three dots) par click karo
   - Ek list khulegi — usme dhundo: **`arena/f71ea5d9-ratan-patel-github-io`**
   - Us par click karo → button ban jayega: **"Create codespace on arena/f71ea5d9-ratan-patel-github-io"**
   - Us button par click karo

> 💡 **Aasan shortcut (optional):** tum chaaho to pehle PR merge kar do — GitHub par kholo **https://github.com/Ratan-patel/Ratan-patel.github.io/pull/14** → neeche **hara "Merge pull request"** button → **"Confirm merge"**. Uske baad step 4 me seedha **"Create codespace on main"** dabana kaafi hai.

5. ✅ **CHECK:** Screen par bada sa "**Setting up your codespace…**" likha aayega, progress bar chalega.
   *(Isme 1–3 minute lagte hain. Browser band mat karo. Agar 5 min se zyada ho jaye to page refresh kar do — setup background me chalta rehta hai.)*

---

## 📍 PART 2 — Setup ka wait (aur password note karna) — 3–5 min

Setup hote hi browser me **VS Code** jaisa screen khulega (GitHub ka "Codespaces" editor). Screen aisa dikhega:

```
┌──────────────────────────────────────────────────────────────┐
│  ☰  🔍  🌿 arena/…   Files                    ＜  ⤢  ⋯        │  ← upar toolbar
├───────┬──────────────────────────────────────────────────────┤
│  📄   │                                                      │
│  🔎   │   (yahan file editor khulega — abhi khaali)          │
│  🔀   │                                                      │
│  🐞   │                                                      │
│  ⬇️   │                                                      │
├───────┴──────────────────────────────────────────────────────┤
│  TERMINAL   PORTS   PROBLEMS   OUTPUT      ← ye tabs neeche hain│
│  vscode@codespaces:/workspaces/Ratan-patel.github.io$        │
│  (yahan commands chalenge — ye "Terminal" hai)               │
└──────────────────────────────────────────────────────────────┘
```

**Ye automatic ho raha hoga (tumhe kuch nahi karna):**
- Terminal me tools install honge (nmap, sqlmap, nikto…) — isme **2–4 minute** lagte hain. Tum lines ko chalti hui dekhoge.
- Phir dashboard apne aap start ho jayega.

✅ **CHECK — jab ye banner dikhe, samjho sab ready hai:**

```
  ╔══════════════════════════════════════════════════════════╗
  ║  RatanSec OS READY — dashboard chal raha hai             ║
  ╚══════════════════════════════════════════════════════════╝
     Dashboard:  Ports tab → port 8000 ke aage globe icon par click karo
     Password:   wVmvZVsmxATf        ← 👈 YE NOTE KAR LO (Notepad me likh lo)
     AI:         OFF — key add karne ke liye: nano .env → OPENROUTER_API_KEY=sk-or-v1-...
```

❌ **Banner 10 minute me bhi nahi aaya?** Terminal me click karo aur ye ek line paste karke Enter dabao:
```bash
bash ratansec-os/scripts/codespace-start.sh
```
(Ye khud sab kar dega aur banner phir dikha dega.)

> **Terminal dikh nahi raha?** Keyboard me **Ctrl + `** (backtick — Tab wale button ke upar) dabao, ya upar menu me **"Terminal" → "New Terminal"**.

---

## 📍 PART 3 — Dashboard kholo aur login karo — 2 clicks

1. **Neeche waale tabs me "PORTS"** par click karo (TERMINAL ke bagal me hai)

2. Wahan ek row dikhegi:

```
   Port   Address              Forwarded Address                        Visibility
   8000   localhost:8000       https://xxxxx-8000.app.github.dev    🌐   Private
                              ↑ is row me aage globe 🌐 icon hai — us par click karo
```

3. ✅ **CHECK:** Naya tab khulega jisme **login screen** aayega:
   ```
   🛡️  RatanSec OS
   Dashboard locked hai — password daalo.
   [ APP_PASSWORD…………… ]
   [      Unlock      ]
   ```
4. **PART 2 wala password** daalo → **Unlock** → 🎉 **Dashboard khul gaya!**

> **Alternate tarika:** start hote waqt neeche-right me ek chhota popup bhi aata hai — *"Your application running on port 8000 is available"* → usme **"Open in Browser"** dabao. Wahi kaam hai.

> **Password bhool gaye?** Terminal me ye chalao:
> ```bash
> grep APP_PASSWORD ratansec-os/.env
> ```
> Jo dikhe uske `=` ke aage wala hissa password hai.

---

## 📍 PART 4 — Dashboard ka pehla tour (30 second me samjho)

Upar tabs hain, ye kaam karte hain:

| Tab | Kya karta hai |
|---|---|
| **🧠 AI Chat** | Yahan Hinglish me likho — AI khud scan chalayega aur samjhayega |
| **🎯 Scan** | Target + profile chun ke seedha scan (AI ke bina bhi) |
| **📡 Runs** | Live scan output, cancel, **AI report banao** button |
| **📄 Reports** | Banayi hui reports (download bhi kar sakte ho) |
| **🧰 Tools** | Kaunse tools ready hain (nmap, nikto…) |
| **🔍 Audit** | Har command ka record |

Upar chips me ye dikhna chahiye: `AI: …` · `Mode: …` · `Tools: 11/12` · `Scans: 0` · `OS: Debian`

---

## 📍 PART 5 — AI key daalo (2 minute) — AI ko chalu karne ke liye

**Terminal me** ye chalao (click karke, paste karke Enter):

```bash
nano ratansec-os/.env
```

Ab editor khulega (nano). Arrow keys se neeche jao jab tak ye line dikhe:

```
OPENROUTER_API_KEY=
```

Uske `=` ke **turant baad** apni key paste karo (mouse se cursor wahin rakho, phir right-click → Paste, ya `Shift + Insert`):

```
OPENROUTER_API_KEY=sk-or-v1-तुम्हारी-पूरी-key
```

**Save karo:** `Ctrl + O` → `Enter` → phir `Ctrl + X` (band ho jayega)

**Restart karo:**
```bash
bash ratansec-os/scripts/codespace-start.sh
```

✅ **CHECK:** Dashboard tab par wapas jao → page refresh (F5) karo → upar **`AI: gpt-4o-mini` hara (green)** dikhna chahiye.

> Free me test karna ho? `.env` me ye bhi badal do: `MODEL=deepseek/deepseek-chat-v3.1:free`
> Key galat hui to chat me saaf message aayega (401/402/404) — uske hisaab se fix karo.

---

## 📍 PART 6 — Pehla scan (click-by-click) — 3 minute

1. **"🧠 AI Chat"** tab me neeche ke **text box** me likho:
   ```
   example.com ka quick recon karo
   ```
   👉 `example.com` ki jagah **apna authorized target** likho (apna domain, ya practice lab).

2. **Enter** dabao → screen par aayega:
   ```
   ⏳ Analysis kar raha hoon …  (teen dots chalti rahengi)
   ```
   Uske baad AI khud tools chalayega (isme 2–4 minute lagte hain).

3. Pehli baar **peela card** aa sakta hai:
   ```
   ⚠️ Approval chahiye
   'example.com' par Quick Recon (5 steps)
   $ nmap -T4 -Pn -sT -F --open -sV example.com
   [ Approve & run ]   [ Deny ]
   ```
   👉 **"Approve & run"** dabao. (Ye safety feature hai — app pehle tumse permission leta hai.)

4. Ab **"📡 Runs"** tab me jao — live output step-by-step dikhega:
   ```
   [running] nmap   Nmap top-100 ports — example.com      (12s)
   [done   ] nmap   …                                     (14.2s)
   ```

5. Scan khatam → AI chat me apne aap analysis aa jayega (open ports, versions, kya risk hai).

6. **Report banane ke liye:** "📡 Runs" tab → apna run select karo (left list me) → **"AI report banao"** button → phir **"📄 Reports"** tab me jaake padho / **Download .md** karo.

7. 🎉 Bas! Yahi tumhara routine hai: **chat me maango → approve karo → report lo.**

---

## 📍 PART 7 — Rozana ka tarika + time limits (paisa ₹0 rakhne ke liye)

**Chalu karna:**
1. github.com kholo → **https://github.com/codespaces** (ya avatar → "Your codespaces")
2. Apna codespace dikhega → us par click → VS Code khul jayega
3. Terminal me (agar dashboard chalu nahi hai to):
   ```bash
   bash ratansec-os/scripts/codespace-start.sh
   ```
4. PORTS tab → 8000 → globe icon → login

**Band karna (zaroori — minutes bachane ke liye):**
- VS Code screen me neeche-left **"⋯" ya gear** menu → **"Stop Current Codespace"**
- Ya browser me https://github.com/codespaces → **"⋯"** → **Stop**

**Limits:**
- Free GitHub account: **~60–120 hours/month** (machine type ke hisaab se). Roz 2 ghante chalao to poora mahina kaafi hai.
- **Kaam na ho to Stop kar do** — warna minutes katte rehte hain.
- Seekhna khatam? Codespace **Delete** kar do ("⋯" → Delete).
- Frontend/website wala kaam (GitHub Pages) is se alag chalta hai — us par koi asar nahi.

**Phone se use karna hai?** Wahi forwarded URL (`https://xxxx-8000.app.github.dev`) phone ke browser me kholo — **GitHub me logged in hona zaroori hai** (port "Private" hai).
👉 Public karna ho (phone/bahari access ke liye): PORTS tab → port 8000 par **right-click** → **Port Visibility** → **Public** → ⚠️ **phir password strong rakho** (warna koi bhi dashboard khol lega).

---

## 🆘 PART 8 — Codespaces me kuch atke to (troubleshooting)

| # | Problem | Kya karo |
|---|---|---|
| 1 | "Setting up your codespace" 5 min se zyada | Page refresh karo. Setup background me chalta rehta hai |
| 2 | Terminal dikh nahi raha | `Ctrl + \`` dabao, ya menu → Terminal → New Terminal |
| 3 | Tools install wali lines bahut aa rahi hain | Normal — 2–4 min lgte hain (nmap, sqlmap etc. aa rahe hain) |
| 4 | "RatanSec OS READY" banner nahi aaya | Terminal me: `bash ratansec-os/scripts/codespace-start.sh` |
| 5 | PORTS tab me 8000 nahi dikh raha | Pehle banner aa jaye (server start ho), phir PORTS tab ka ⟳ refresh dabao |
| 6 | "Port 8000 … not found" / naya tab blank | Terminal me `tail -20 /tmp/ratansec.log` chalao — usme asli error dikhega |
| 7 | Password nahi pata | `grep APP_PASSWORD ratansec-os/.env` |
| 8 | Login ke baad `AI: off` | Key `.env` me nahi daali → PART 5 karo |
| 9 | `.env` file nahi mil rahi | Terminal me: `cd ~/workspaces/Ratan-patel.github.io/ratansec-os && ls -a` |
| 10 | Sab tools `skipped` dikha rahe | Terminal me: `bash ratansec-os/scripts/install-tools.sh` (ya Codespace ko restart karo) |
| 11 | Codespace bahut slow | Free machine par pehli baar slow hota hai. Kaam khatam? Stop kar do |
| 12 | "You have exceeded your codespaces usage" | Mahine ki limit khatam — agle mahine reset hoti hai, tab tak Windows raasta (B) use karo |
| 13 | Kuch aur error | Screenshot ya error text mujhe bhej do — main fix bata dunga |

---

## 🎯 PART 9 — Practice karo (legal targets)

| Target | Kaise |
|---|---|
| **Apna domain** | `ratan-patel.github.io` (tumhara hi hai) — target daalo: `ratan-patel.github.io` |
| **Juice Shop (vulnerable app)** | Terminal me: `docker run -d -p 3000:3000 bkimminich/juice-shop` → target: `http://localhost:3000` |
| **TryHackMe** | tryhackme.com → free rooms → unka target IP daalo |
| **PortSwigger Web Security Academy** | portswigger.net/web-security → free labs |

⚠️ **Sirf authorized targets** — apne systems, labs, ya jinke paas likhit permission ho.

---

## 🔁 Ek line recap

**Chalane ke liye:** github.com/codespaces → apna codespace → terminal me `bash ratansec-os/scripts/codespace-start.sh` → PORTS (8000) → globe icon → password → **kaam shuru!**
