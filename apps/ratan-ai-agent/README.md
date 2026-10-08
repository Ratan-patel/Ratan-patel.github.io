# RATAN AI AGENT 2.1 — Android app

Source of the installable Android build of the RATAN AI assistant, produced by
`.github/workflows/build-ratan-agent-apk.yml` and published as a GitHub Release.

**Download (phone-friendly, always the newest build):**

> **https://github.com/Ratan-patel/Ratan-patel.github.io/releases/download/ratan-ai-agent-v2.1/Ratan-AI-Agent-2.1.0-release.apk**

Release notes, checksums and the debug build: [releases/tag/ratan-ai-agent-v2.1](https://github.com/Ratan-patel/Ratan-patel.github.io/releases/tag/ratan-ai-agent-v2.1) ·
install walkthrough: [docs/APK.md](docs/APK.md).

---

## Why 2.0 exists

The 1.1 APK on this repository's releases page was a 64 MB binary with no source: nothing in it
could be reviewed, rebuilt, or patched. 2.0 replaces it with an app that is **built here**:

| | 1.1 upload | 2.0 (this directory) |
|---|---|---|
| Source in repo | no | yes — `android/app/src/main/java/…` |
| Platform | unknown | `compileSdk`/`targetSdk` **36** today (Android 16 — the newest platform the public SDK channel publishes); the workflow moves to **API 37** by itself the moment Google ships `platforms;android-37`. Android 17's `ACCESS_LOCAL_NETWORK` flow is already implemented. |
| Toolchain | unknown | AGP 9.4.0 · Gradle 9.6.0 · JDK 21 · build-tools 36+ |
| Stable identity | — | signing certificate SHA-256 `79dce484cfafa35025c8df74880a17c374f20a0b23a982331e85f4022908ca83` · package `io.github.ratanpatel.ratanagent` · every build is a fresh ZIP, so the APK hash changes per rebuild and the release notes always quote the current one · site page: [ratan-ai-agent.html](https://ratan-patel.github.io/ratan-ai-agent.html) |
| Reproducible build | no | GitHub Actions, every push |
| Signature | changed between builds | stable key → updates install in place |
| Offline value | none | bundled AIRT red-team toolkit (67 probes) |
| Third-party code | unknown | none — framework-only, no analytics |

## Bring your own API (optional) — new in 2.1

The app ships pointed at the hosted RATAN AI assistant. You can instead drive it with **your own
provider**, entirely from the dashboard (section 06 · CHAT). Nothing is mandatory: leave the
toggle off and the hosted agent behaves exactly as before.

| Preset | What it talks to | Notes |
|---|---|---|
| `openai` | OpenAI **or anything OpenAI-compatible** — Azure OpenAI, Groq, Together, OpenRouter, vLLM, LM Studio, llama.cpp server, a self-hosted gateway | blank base URL = `https://api.openai.com`; the app appends `/v1/chat/completions` (or accepts a full URL you paste) |
| `anthropic` | Claude models | adds `x-api-key` + `anthropic-version`, moves the system prompt out of band, always sends `max_tokens` |
| `ollama` | a local model server (`http://127.0.0.1:11434`, or your laptop's LAN IP) | no key required; needs local-network access from Android 17 |
| `custom` | any private JSON API you can describe | you supply path, extra headers, a body template and a response path |

Custom placeholders: `{{MODEL}}`, `{{PROMPT}}`, `{{MESSAGES}}` (raw JSON array), `{{SYSTEM}}`,
`{{TEMPERATURE}}`, `{{MAX_TOKENS}}`, and `{{KEY}}` inside headers only.

### How the credential is handled

| Property | Implementation |
|---|---|
| Storage | Android Keystore key (AES-256-GCM, random IV per write, hardware-backed where available) via `SecureStore.java` |
| Exposure to the page | **none** — the dashboard may write a key and can only ever read back a masked tail (`…a1b2`) |
| Scope of use | the credential is attached only to the URL built from your stored profile; the web layer cannot choose the destination |
| Redirects | `Authorization`/`Cookie`/`x-api-key` are dropped on any cross-host redirect |
| Errors | the key is redacted out of every message, hint and raw snippet before it reaches the UI |
| Backups | disabled for the app's files and preferences (`data_extraction_rules.xml`) |
| Concurrency | one completion in flight at a time, so a misbehaving page cannot fan out paid calls |

`TEST CONNECTION` runs a minimal round-trip and reports the provider's own error text plus a
plain-language hint (rejected key, unknown model, wrong path, rate limit, unreachable host,
LAN permission missing).

Use keys and endpoints that you own or are authorised to use — the app stores them on the device
and sends them nowhere else.

## What the app does

* **RATAN AI chat** — the hosted assistant, opened inside a hardened WebView rather than a
  browser tab.
* **Android 17 local-network support** — Android 17 refuses LAN access unless an app holds the
  `ACCESS_LOCAL_NETWORK` runtime permission. The shell declares it, asks for it at the right
  moment, and explains the failure when it is missing, so lab targets on `192.168.x.x` stay
  reachable instead of failing with an opaque network error.
* **Offline red-team toolkit** — the same page the standalone AIRT scanner ships
  (`tools/ai-redteam-scanner/mobile.html`, copied in by `tools/sync_assets.py` so the two can
  never drift): 67 probes across 11 categories, 9 evasion mutations, OWASP LLM Top-10 mapping.
* **Native HTTP bridge** — JavaScript cannot reach a plain-`http` lab bot (CORS + cleartext
  rules); the bridge can. It enforces its own policy per redirect hop: https everywhere, LAN
  cleartext allowed by default, public cleartext off, `Authorization`/`Cookie` dropped on
  cross-host redirects, header-injection guards, response caps, gzip.
* **Voice and image input** — microphone/camera permissions are handed to the WebView only after
  the user approves them.
* **Reports in Downloads/** — JSON, standalone HTML and SARIF 2.1.0, written through MediaStore.
* **Diagnostics that answer support questions** — build, device, WebView version, network,
  permission state, APK signature fingerprint, and a one-tap self-test including a reachability
  probe of the configured endpoint.
* **Configurable endpoint** — point the app at a self-hosted deployment (or a lab instance) from
  the dashboard; timeouts and response caps are adjustable too.
* **Bring your own API** — chat against OpenAI-compatible endpoints, Anthropic, a local Ollama
  server, or a private JSON API, with the key held in the Android Keystore (see below).

## Layout

```
apps/ratan-ai-agent/
├── android/                          Gradle project (no wrapper jar needed in CI)
│   ├── build.gradle                  AGP 9.4.0
│   ├── settings.gradle, gradle.properties
│   └── app/
│       ├── build.gradle              API 37, signing via env, buildConfig fields
│       └── src/
│           ├── main/java/…/          MainActivity · AgentBridge · HttpEngine · NetPolicy · Prefs
│           │                          SecureStore (Keystore secrets) · LlmClient (BYOK providers)
│           ├── main/assets/          home.html (dashboard) · toolkit.html (generated)
│           ├── main/res/             icon, theme (+v31 splash), network security config
│           ├── debug/res/xml/        debug-only NSC that trusts user CAs (for a proxy)
│           └── main/AndroidManifest.xml
├── docs/APK.md                       install + usage for a phone
├── keystore/                          stable release key (public by design, documented)
└── tools/
    ├── sync_assets.py                bundle the AIRT page into assets/toolkit.html
    ├── check_web_assets.js           parse every <script> block + marker assertions
    ├── verify_apk.py                 package/version/SDK/assets checks on the built APK
    └── make_keystore.py              mint a PKCS#12 signing identity (no JDK required)
```

## Building it

Everything happens on GitHub runners — no local Android SDK is required:

```bash
gh workflow run build-ratan-agent-apk.yml          # or push to main / arena/**
gh run watch
```

Locally, with an SDK and Gradle 9.6+ installed:

```bash
python3 tools/ai-redteam-scanner/gen_mobile.py                     # refresh the corpus
python3 apps/ratan-ai-agent/tools/sync_assets.py                   # bundle it
node apps/ratan-ai-agent/tools/check_web_assets.js apps/ratan-ai-agent/android/app/src/main/assets/*.html
cd apps/ratan-ai-agent/android && gradle :app:assembleRelease      # APK in app/build/outputs/apk/release
```

The workflow regenerates the toolkit, bundles it, syntax-checks the bundled JavaScript, builds
debug **and** release, then verifies the release APK (package name, versionCode 200,
`targetSdk 37`, bundled pages, ≥60 probes in the corpus) before it is allowed to publish.

## Signing

Release APKs are signed with `keystore/ratan-agent-release.p12` so the signature is stable
across builds and updates install over the previous release. That key is public on purpose and
documented in [keystore/README.md](keystore/README.md) — generate your own and pass it through
repository secrets (`ANDROID_KEYSTORE_BASE64`, `ANDROID_KEYSTORE_PASSWORD`, `ANDROID_KEY_ALIAS`,
`ANDROID_KEY_PASSWORD`) before distributing anywhere that matters.

## Privacy

No analytics, no crash reporting, no third-party SDKs. Scan results, endpoints and tokens stay
on the device; backup and device-transfer are disabled for everything the app writes
(`data_extraction_rules.xml`). The only network traffic is what the operator points the app at.

## Authorised testing only

The bundled toolkit fires real adversarial prompts, and the HTTP bridge can reach anything the
phone can route to. Use it against systems you own or have written permission to test — the
same rule the AIRT CLI and the training material in this repository already state.
