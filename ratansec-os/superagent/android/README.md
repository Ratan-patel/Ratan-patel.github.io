# 📱 Super Agent — Android APK

Native Android shell (Kotlin + WebView) jo aapke **self-hosted** Super Agent server ka mobile
console kholta hai. APK GitHub Actions se build hoti hai — sandbox/CI me Android SDK nahi chahiye.

## Download

1. GitHub → **Actions** → *Build Super Agent APK* → latest run → artifact
   `ratansec-superagent-apk` (debug + release APK).
2. Ya seedha **permanent link** (latest release):
   `https://github.com/Ratan-Patel/Ratan-patel.github.io/releases/latest/download/RatanSec-SuperAgent-debug.apk`

## Install (sideload)

1. APK phone me download karo (Chrome → Download).
2. "Install unknown apps" allow karo (Chrome/File manager ke liye).
3. APK kholo → Install → **Super Agent** app khulegi.
4. App me:
   * **Server URL**: `http://<laptop-ip>:8000` (laptop par `bash scripts/superagent.sh`)
   * **Token**: `.env` ka `SUPERAGENT_MOBILE_TOKEN` (ya `SUPERAGENT_API_TOKEN`)
5. Connect → console khul jayega (chat, terminal, approvals, records, reports).

Deep link: `superagent://open?server=http://192.168.1.5:8000&token=XXXX`

## APK khud build karna

```bash
cd ratansec-os/superagent/android
# Android SDK + JDK 17 chahiye
gradle :app:assembleDebug
# output: app/build/outputs/apk/debug/app-debug.apk
```

## App kya karta hai (aur kya nahi)

* Sirf **wo URL** kholta hai jo aap daalte ho — koi analytics, koi background traffic nahi.
* Token phone ke app-private storage me rehta hai (SharedPreferences + WebView localStorage).
* `usesCleartextTraffic` sirf isliye ki LAN/VPS par `http://` chalta hai — public deployment par
  HTTPS (Caddy / Cloudflare Tunnel) use karo.
* Server hi asli kaam karta hai (tools wahan chalte hain) — app ek console hai.

> Sirf un systems par use karo jinke liye likhit authorization hai.
