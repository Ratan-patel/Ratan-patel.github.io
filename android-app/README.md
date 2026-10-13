# Sentinel Android App

Phone par chalne wala Sentinel — wahi rules jo Python CLI mein hain:

- **Scope pehle, scan baad mein.** Target scope list mein nahi hai to kuch nahi chalega.
- **Hard prohibitions kabhi override nahi hote:** ICS/SCADA/medical ports, government/military domains,
  satellite/ SCADA/ critical-infrastructure hostnames, aur third-party providers (Google, OpenAI,
  Microsoft, GitHub, Stripe...) — inko khud add karke bhi scan nahi hoga.
- **Tools (read-only):** HTTP header audit (score ke saath), TLS/certificate audit,
  connect-only port discovery (active checkbox + protected ports refused),
  aur **Ask AI** — tumhari apni koi bhi OpenAI-compatible API / private gateway / Ollama.

## APK kaise bana

Ye sandbox mein Android SDK nahi hai, isliye APK **GitHub Actions** par banta hai
(`.github/workflows/build-apk.yml`, JDK 17 + Gradle 8.7 + Android SDK runner par):

1. Actions tab → **Build Sentinel APK** → Run workflow
2. Khatm hone par **Sentinel-APK** artifact download karo → `Sentinel.apk`
3. Phone par install karo (unknown sources allow karna hoga, kyunki ye Play Store build nahi hai)

APK debug-signed hai — apne phone par personal use ke liye theek hai.
Play Store / dusron ko distribute karna ho to apni release keystore se sign karna hoga.

## Privacy

- API key sirf phone ke app-private storage mein save hota hai, kahin upload nahi hota.
- App koi analytics/tracking nahi karta, koi server ko data nahi bhejta — sirf tumhare diye hue
  target aur model endpoint ko request jaati hai.
