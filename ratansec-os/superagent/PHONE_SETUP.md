# 📱 Phone ko hi server bana do (laptop ki zarurat nahi)

APK kholte hi jo **"Server URL"** maangta hai — woh address hai jahan Super Agent ka
**server** chal raha ho. APK sirf screen hai; agent server par chalta hai.

Tumhare paas 3 raste hain. Sabse aasan pehla hai.

---

## ✅ Rasta 1 — Phone khud server ban jaye (sirf phone chahiye)

Isme agent **tumhare phone ke andar** chalega aur URL hoga `http://127.0.0.1:8000`.
Koi laptop nahi, koi cloud nahi, API key phone se bahar nahi jaati.

### Step 1: Termux install karo

**F-Droid** se Termux lo (Play Store wala purana hai, kaam nahi karta):
https://f-droid.org/packages/com.termux/

### Step 2: Termux kholo aur ye ek line paste karo

```bash
pkg install -y curl && curl -fsSL https://raw.githubusercontent.com/Ratan-patel/Ratan-patel.github.io/arena/77c68fc8-ratan-patel-github-io/ratansec-os/scripts/phone-server.sh -o phone-server.sh && bash phone-server.sh
```

Script khud:
1. `proot-distro` + Debian install karega (~150 MB, sirf pehli baar)
2. Debian ke **prebuilt** FastAPI/uvicorn packages lagayega
   (Termux ke native Python me pydantic-core ke liye Rust compile karna padta hai — 10+ min aur
   aksar fail hota hai. Debian me ready-made binaries milte hain, isliye ye rasta liya.)
3. Super Agent ka source download karega
4. Tumse **console password** puchhega (min 8 chars) — ye app me login ke liye hai
5. Server chalu kar dega

Pehli baar **5–10 minute** lag sakte hain (internet speed par depend). Uske baad har baar turant.

### Step 3: APK me URL daalo

Super Agent app kholo → Server URL me:

```
http://127.0.0.1:8000
```

**Open console** → password daalo (jo Step 2 me set kiya) → dashboard khul gaya. 🎉

### Roz chalane ke liye

Termux kholo → `bash phone-server.sh` → phir app kholo.
Server band: Termux me `Ctrl + C` (Volume Down + C).

> Termux band karoge to server bhi band. Script `termux-wake-lock` laga deta hai taaki
> screen off hone par bhi chalta rahe.

### Apni private API key daalni ho (AI chat ke liye)

```bash
proot-distro login debian
nano /opt/ratansec/ratansec-os/.env
```

`SUPERAGENT_API_KEY=` ke aage apni key paste karo → `Ctrl+O`, `Enter`, `Ctrl+X` →
`exit` → `bash phone-server.sh` dobara.

Key **sirf phone par** rehti hai. Chat me kabhi paste mat karo.

### Sirf demo dekhna ho (bina password, bina key)

```bash
bash phone-server.sh --demo
```

---

## 💻 Rasta 2 — Laptop server, phone console

Laptop aur phone **same Wi-Fi** par hon.

Laptop par:
```bash
cd ratansec-os
cp superagent/.env.example .env      # APP_PASSWORD + apni API key bharo
bash scripts/superagent.sh --host 0.0.0.0 --port 8000
```

Laptop ka IP nikalo: `hostname -I` (Linux/Mac) ya `ipconfig` (Windows).
App me URL: `http://192.168.1.5:8000` (apna IP daalo).

---

## ☁️ Rasta 3 — Cloud server (kahin se bhi access)

Agar phone/laptop band hone par bhi agent chahiye to ek chhota VPS lena padega
(Render / Railway / DigitalOcean / apna existing server). Repo me Docker file ready hai:

```bash
docker build -f superagent/Dockerfile.slim -t superagent .
docker run -p 8000:8000 --env-file .env superagent
```

Public URL par **HTTPS zaroori hai** (Caddy / Cloudflare Tunnel) aur `APP_PASSWORD`
strong rakho. Bina HTTPS password plain text me jaayega.

> Ye rasta paid hai aur setup khud karna padega — isliye Rasta 1 sabse aasan hai.

---

## ❓ Dikkat aaye to

| Problem | Fix |
|---|---|
| `Connect nahi ho paya` | Termux me server chal raha hai? `bash phone-server.sh` dobara chalao |
| App me password reject | Wahi password jo script me set kiya tha. Bhool gaye to script dobara chalao |
| `proot-distro: command not found` | `pkg update && pkg install proot-distro` |
| Download fail | Internet check karo; script dobara chalao (adhoora kaam skip ho jaata hai) |
| Port busy | `bash phone-server.sh --port=8080` → app me `http://127.0.0.1:8080` |
| Source update karna hai | `SA_UPDATE=1 bash phone-server.sh` |
| Debian package purana | Script saaf error dega; `proot-distro reset debian` karke dobara chalao |

---

## 🔒 Safety

* Server `127.0.0.1` par bind hota hai — **bahar se koi access nahi kar sakta**.
* API key/password phone ke `.env` me (permission `600`), kisi cloud par nahi.
* Har mission se pehle **RoE record** (likhit authorization) + **exact-plan approval** zaroori hai.
* Sirf un systems par chalao jinki tumhare paas likhit permission hai.