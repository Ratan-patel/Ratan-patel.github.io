# ⚡ VAJRA — AI Ethical Hacking Agent (Termux Edition)

<p align="center"><img src="web/icon-512.png" width="110" alt="VAJRA"></p>

**Vajra** (वज्र — Indra ka vajra) ek **AI-powered ethical hacking agent** hai jo Android phone ke **Termux** mein chalta hai. Tum Hinglish mein bolo — "is target ka recon karo", "full port scan chalao" — aur agent khud sahi tool chuna kar command execute karega, output padh kar next step batayega.

> ⚖️ **Sirf authorized testing ke liye** — apne labs, CTFs (TryHackMe/HackTheBox), apne assets, ya written permission wale targets. Bina permission access karna **IT Act 2000 (Sec 43/66)** ke under offence hai. Agent mein scope-checking + audit logging built-in hai.

---

## ✨ Features

| Feature | Detail |
|---|---|
| 🧠 **Powerful AI** | Groq (Llama-3.3-70B — **free + fastest**), Gemini, GPT-4o, Claude (OpenRouter), ya **Ollama offline** — apni key, apna choice |
| 🧰 **30+ tools pre-install** | Har phase ke liye: Recon → Scanning → Vuln Analysis → Gaining Access → Passwords → Wireless → Post-Exploitation → Reporting |
| ⚡ **Tez hai** | Zero pip dependency (pure stdlib), streaming responses, Groq latency ~1-2s, `!command` direct fast-path |
| 🛡️ **Safety built-in** | Authorized-scope manager, har risky command par confirmation, poora audit log |
| 📱 **App jaisa UI** | `vajra --server` → browser → "Add to Home Screen" = **icon wala full-screen app** |
| 🧾 **Pentest Reports** | Ek click mein markdown report (~/.vajra/report_*.md) |

---

## 🚀 Install (3 steps)

```bash
# 1. Termux (F-Droid wala) kholo — https://f-droid.org/packages/com.termux/
pkg update -y && pkg install -y unzip && termux-setup-storage

# 2. vajra.zip ko Downloads se Termux mein lao aur unzip karo
cp ~/storage/downloads/vajra.zip . && unzip vajra.zip && cd vajra

# 3. Sab kuch install karo (~15 min)
bash install.sh          # core tools
bash install.sh --full   # + Metasploit, winPEAS (heavy ~1GB)
```

Pehli baar `vajra` chalao — setup wizard khulega (backend + free API key).

---

## 🤖 AI Backend Setup (1 minute)

| Backend | Free? | Key kahan se | Best for |
|---|---|---|---|
| **Groq** ⭐ | ✅ Free | [console.groq.com/keys](https://console.groq.com/keys) | **Sabse fast** (Llama-3.3-70B, ~1-2s) |
| **Gemini** | ✅ Free tier | [aistudio.google.com/apikey](https://aistudio.google.com/apikey) | Fast + Google quality |
| **OpenRouter** | ✅ Free models | [openrouter.ai/keys](https://openrouter.ai/keys) | GPT/Claude/Llama sab ek jagah |
| **OpenAI** | 💰 Paid | platform.openai.com | GPT-4o |
| **Ollama** 📴 | ✅ Free, **offline** | key nahi chahiye | Privacy — `pkg install ollama && ollama serve && ollama pull llama3.2` |

Key daalne ke liye: `vajra` → `/key` (ya Web UI → Setup tab).

---

## 🧰 Tool Arsenal (phase-wise)

| Phase | Tools |
|---|---|
| 🔍 **Recon & OSINT** | theHarvester, sherlock, holehe, phoneinfoga, fierce, dnsenum, RED_HAWK |
| 📡 **Scanning & Enum** | nmap, dirsearch, gobuster, enum4linux |
| 🛡️ **Vuln Analysis** | nikto, nuclei (8000+ templates), searchsploit, testssl.sh |
| ⚡ **Gaining Access** | sqlmap, hydra, commix, metasploit* |
| 🔑 **Password Attacks** | john, cupp, crunch |
| 📶 **Wireless** | aircrack-ng, wifite *(root + monitor-mode adapter chahiye)* |
| 🧲 **Post-Exploitation** | linpeas, les, winPEAS*, metasploit meterpreter* |
| 📱 **Phone Controls** | termux-camera-photo, termux-location, termux-sms-list, termux-wifi-connectioninfo |
| 📝 **Reporting** | built-in audit log + report generator |

\* = `--full` install se

---

## 💬 Use kaise karein

```bash
vajra                    # interactive chat (Hinglish chalega!)
```

Examples:
- `"example.com ka passive recon karo — emails aur subdomains"`
- `"10.10.14.22 ka full port scan + service versions"`
- `"is URL par SQL injection check karo: http://testphp.vulnweb.com/listproducts.php?cat=1"`
- `"sherlock se username r4tnp dhoondo"`

**Chat commands:**
`/help` madad · `/tools` installed tools · `/scope add example.com` authorized target · `/yolo` confirmations kam · `!nmap -sV x.com` direct command · `/report` report banao · `/exit`

---

## 📱 App (APK-jaisa) kaise banayein

Real APK ki zaroorat nahi — Android ka sandbox nmap/metasploit jaise tools **nahi chala sakta**, isliye Termux engine chahiye hi. Lekin app ka experience mil sakta hai:

```bash
vajra --server
```
1. Phone browser mein kholo → `http://localhost:8080`
2. Browser menu → **"Add to Home Screen"**
3. Done! Icon wala full-screen app — offline bhi khulta hai.

---

## 🧪 Khud check karo

```bash
vajra --selftest    # registry, executor, scope-check, report — sab test
vajra --tools       # kaunsa tool installed hai
```

## 🛠️ Troubleshooting

| Problem | Fix |
|---|---|
| koi tool `✗` par hai | `bash install.sh` dobara chalao (idempotent hai) |
| metasploit fail | Normal hai — Termux par heavy hai; dobara `--full` try karo ya nmap+searchsploit se kaam chalao |
| Ollama slow/boring | RAM kam hai — `ollama pull llama3.2` (3B) use karo, ya Groq free key lo |
| `command not found: vajra` | `source $PREFIX/bin/` — naya session kholo ya `hash -r` |
| pip error | `pip install --upgrade pip` phir `bash install.sh` |
| Web UI nahi khulta | Termux mein: `termux-open-url http://localhost:8080` |

---

## 📁 Structure

```
vajra/
├── install.sh        # one-shot tool installer (Termux)
├── vajra.py          # CLI agent
├── server.py         # Web UI server (PWA)
├── agent/
│   ├── registry.py   # 30+ tools — phase-wise
│   ├── llm.py        # AI backends (Groq/Gemini/OpenAI/OpenRouter/Ollama)
│   ├── executor.py   # safe execution + scope + audit
│   └── chat.py       # agent brain (tool-calling loop)
└── web/              # mobile-first PWA UI
```

---

## ⚖️ Legal & Ethics

Yeh project **education aur authorized penetration testing** ke liye hai. Har command `~/.vajra/audit.log` mein log hoti hai aur out-of-scope targets par agent rok lagata hai. **Written permission ke bina kisi system ko test karna illegal hai.** Seekhne ke liye: [TryHackMe](https://tryhackme.com), [HackTheBox](https://hackthebox.com), [PortSwigger Web Security Academy](https://portswigger.net/web-security).

**VAJRA v1.0** — Made with ⚡ for the Termux hacker community.
