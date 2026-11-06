# 📱 Super Agent v2 — Android APK

Native Android shell (Kotlin + WebView) jo aapke **self-hosted** Super Agent server ka mobile
console kholta hai. APK GitHub Actions par build hoti hai — laptop par Android SDK ki zarurat nahi.

> APK **agent nahi hai**, sirf console hai. Agent + tools tumhare laptop/VPS par chalte hain,
> aur API key wahin `.env` me rehti hai — phone par key nahi jaati.

## Download (sabse aasan)

Latest release APK — seedha phone ke browser me kholo:

* **Release (recommended):**
  `https://github.com/Ratan-patel/Ratan-patel.github.io/releases/latest/download/RatanSec-SuperAgent-release.apk`
* Debug build:
  `https://github.com/Ratan-patel/Ratan-patel.github.io/releases/latest/download/RatanSec-SuperAgent-debug.apk`
* Release page (dono files + notes):
  `https://github.com/Ratan-patel/Ratan-patel.github.io/releases/tag/apk-latest`

Alternative: GitHub → **Actions** → *Build Super Agent APK* → latest run → artifact
`ratansec-superagent-apk` (ZIP, GitHub login chahiye).

## Install (sideload)

1. Link phone me kholo → APK download.
2. Settings → **Install unknown apps** → Chrome/File Manager ko allow karo.
3. APK par tap → **Install** → **Open**.
4. Play Protect warning aaye to **Details → Install anyway** (app self-signed hai, Play Store par nahi).
5. App khulte hi bundled **Connect** screen aayegi → server URL daalo:
   * `http://192.168.1.5:8000` (laptop ka LAN IP, phone + laptop same Wi-Fi)
   * ya `https://agent.example.com` (VPS + HTTPS)
6. **Open console** → server ka login screen → wahan password daalo → dashboard.

Deep link (optional): `superagent://open?server=http://192.168.1.5:8000`
v2 me **token URL me nahi bheja jata** — login server ke console par hota hai.

## Server chalu karna

```bash
cd ratansec-os
cp superagent/.env.example .env        # apni private API key yahan
bash scripts/superagent.sh --host 0.0.0.0 --port 8000
```

Sirf demo dekhna ho (bina key, bina real scan):

```bash
bash scripts/superagent.sh --demo --host 0.0.0.0 --port 8000
```

Laptop ka IP: `hostname -I` (Linux) / `ipconfig` (Windows).

## APK khud build karna

```bash
cd ratansec-os/superagent/android
# JDK 17 + Android SDK 34 + Gradle 8.7
gradle :app:assembleDebug
# output: app/build/outputs/apk/debug/app-debug.apk
```

Local build se pehle web assets sync karo (CI ye automatically karta hai):

```bash
cd ratansec-os/superagent
cp static/connect.html static/connect.js static/app.css android/app/src/main/assets/web/
sed -i 's|/static/|./|g' android/app/src/main/assets/web/connect.html
```

Ya GitHub par manually build chalao: **Actions → Build Super Agent APK → Run workflow**
(`release = true` karoge to APK Release me attach ho jayegi → direct download link).

## App kya karta hai (aur kya nahi)

* Sirf **wo URL** kholta hai jo aap daalte ho — koi analytics, koi background traffic nahi.
* Bundled connect screen `WebViewAssetLoader` se `https://appassets.androidplatform.net/assets/…`
  par serve hoti hai (offline chalti hai, file:// access band hai).
* Server origin native prefs me save hota hai; **sirf usi origin** ke links app ke andar khulte
  hain, baaki external browser me.
* Password/API key server par rehti hai; app me sirf server URL store hota hai.
* `usesCleartextTraffic` sirf LAN/VPS ke `http://` ke liye — public deployment par HTTPS
  (Caddy / Cloudflare Tunnel) use karo.
* Release APK CI ke debug certificate se signed hai — sideload ke liye theek, Play Store build nahi.

> Sirf un systems par use karo jinke liye likhit authorization hai.