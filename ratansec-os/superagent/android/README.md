# 📱 RatanSec Agent v3 — standalone Android app

**Koi server nahi chahiye.** App me apni API key daalo, AI agent phone par hi chal jaata hai.
Pehle version (v2) ko self-hosted server chahiye tha — v3 me woh zarurat khatam.

## Download

```
https://github.com/Ratan-patel/Ratan-patel.github.io/releases/latest/download/RatanSec-SuperAgent-release.apk
```

Release page: https://github.com/Ratan-patel/Ratan-patel.github.io/releases/tag/apk-latest

## Install

1. Link phone ke browser me kholo → APK download (~2.6 MB)
2. Settings → **Install unknown apps** → Chrome/File Manager allow
3. APK → **Install** → **Open**
4. Play Protect warning → **Details → Install anyway** (self-signed app hai)

> ⚠️ **Purana version (v1/v2) installed hai to pehle uninstall karo.** Har CI build naye
> certificate se sign hoti hai — upar update karne par "App not installed" aayega.

## Chalana (30 second)

1. **Settings** tab → Provider chuno:
   | Provider | Base URL | Model example |
   |---|---|---|
   | OpenRouter | `https://openrouter.ai/api/v1` | `openai/gpt-4o-mini` |
   | OpenAI | `https://api.openai.com/v1` | `gpt-4o-mini` |
   | Groq | `https://api.groq.com/openai/v1` | `llama-3.3-70b-versatile` |
   | DeepSeek | `https://api.deepseek.com/v1` | `deepseek-chat` |
   | Ollama (LAN) | `http://127.0.0.1:11434/v1` | `qwen2.5:7b` |
2. **API key** paste → **Save** → **Test connection** (green ✓ aana chahiye)
3. **Scope** tab → host (`example.com`) + authorization note → checkbox tick → **Add to scope**
4. **Chat** tab → poocho: *"example.com ka security posture check karo"*

Bas. Agent tool calls chalayega, findings dikhayega, fix batayega.

## Key ki privacy

* Key **Android Keystore** se AES/GCM encrypt hokar app-private storage me rehti hai.
* WebView/JavaScript ko key **kabhi nahi milti** — native code hi `Authorization` header lagata hai.
* Key seedhi tumhare provider ko jaati hai. Beech me **koi server nahi**.
* Chat history me key nahi jaati; `allowBackup=false` se cloud backup bhi band.
* **Key hatao** button se turant delete.

## Kya kar sakta hai

| ✅ Allowed | ❌ Not possible |
|---|---|
| DNS resolve | Port scanning |
| HTTP security headers review | Exploits / payloads |
| TLS certificate + protocol review | Brute force |
| security.txt / robots.txt padhna | Shell commands |
| Findings + remediation | Bina scope ke koi request |
| Report share (text) | Redirects follow karna |

Har probe se pehle **scope check** hota hai. Loopback/link-local/metadata (169.254.x) hamesha
blocked. Private ranges (192.168.x, 10.x) sirf Settings me explicitly on karne par.
Response body read nahi hota (sirf 2 well-known public files, 16 KiB cap). Cookies/auth headers
capture nahi hote.

## Architecture

```
assets/app/{index.html,app.css,app.js}   bundled UI (chat / scope / settings)
        ↕ Native bridge (async, JSON)
MainActivity.kt   WebView + WebViewAssetLoader + bridge
Secrets.kt        Android Keystore AES/GCM — API key
Store.kt          provider settings + authorized targets (RoE)
Agent.kt          OpenAI-compatible tool-calling loop (bounded steps)
Probes.kt         on-device DNS / HTTP / TLS / text-file checks
```

UI `https://appassets.androidplatform.net/assets/app/` se load hoti hai (offline, file:// band).
Saara network native side par hota hai — isliye CORS ka issue nahi aur key JS me nahi aati.

## Build

```bash
cd ratansec-os/superagent/android
gradle :app:assembleDebug     # JDK 17 + SDK 34 + Gradle 8.7
```

Ya GitHub → **Actions → Build RatanSec Agent APK → Run workflow**.
Commit message me `[apk-release]` likhne par APK automatically Release par publish hoti hai.

## Limitations (imaandari se)

* TLS probe hostname se connect karta hai (DNS pinning nahi) — hardened server version jitna strict nahi.
* Sirf 5 passive tools; nmap/exploit jaisa kuch nahi. Advanced testing ke liye server version
  (`ratansec-os/superagent/`) use karo.
* Provider tool-calling support karta ho tohi agent tools chala payega (OpenRouter/OpenAI/Groq/DeepSeek theek hain).
* Findings **observations** hain, verified vulnerabilities nahi — manually confirm karo.

> Sirf un systems par use karo jinki likhit authorization tumhare paas hai.
