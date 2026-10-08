# RATAN AI AGENT 2.0 — install & usage (Android)

Download link (open it **on the phone**):

> **https://github.com/Ratan-patel/Ratan-patel.github.io/releases/download/ratan-ai-agent-v2.0/Ratan-AI-Agent-2.0.0-release.apk**

Alternative: the [Releases page](https://github.com/Ratan-patel/Ratan-patel.github.io/releases) or
the workflow artifact `ratan-ai-agent-apk` if the direct link is blocked on your network.

## Install

1. Open the link in Chrome/Firefox on the phone. The APK is small — 703,725 bytes (≈690 KB)
   in the first 2.0 build — so it downloads instantly.
2. Open it from the notification or **Files → Downloads**.
3. Android warns about unknown sources → allow it for the browser, then tap **Install**.
4. Launch **RATAN AI AGENT**. The first screen is a local dashboard that works with no network.

> **Coming from 1.1?** Uninstall the old APK first. The 1.1 upload was signed with a different
> key, and Android refuses to replace an app across signatures. Nothing is lost — 1.1 stored
> nothing on the device that 2.0 needs.

**Requirements:** Android 7.0+ (`minSdk 24`), about 3 MB free space, internet for the chat feature.
The offline toolkit needs no network at all.

## First run

| Screen | What it is |
|---|---|
| **Dashboard** (`home.html`) | Local, offline, instant. Version/build info, network state, LAN addresses, permissions, settings. |
| **Open RATAN AI AGENT** | The hosted assistant. If the network is down, the app falls back to the dashboard with an offline banner instead of an error page. |
| **Red-team toolkit** | The bundled AIRT scanner. Works in aeroplane mode. |
| **Diagnostics** | One-tap self-test: build, WebView engine, signature, permissions, endpoint reachability. Copy or share the result when reporting a problem. |
| **Settings** | Endpoint URL, transport policy (LAN cleartext, public cleartext, external links), timeouts, response cap. |

## Talking to a lab target from the phone

1. On the laptop, start the target so it listens on the LAN — the practice bot in this repo
   already binds `0.0.0.0`:

   ```bash
   python3 tools/ai-redteam-scanner/examples/vulnerable_bot.py    # :8899
   ```

2. Find the laptop's LAN address (`ip a` / `ipconfig`) — for example `192.168.1.5`.
3. In the app: **Red-team toolkit → target URL** `http://192.168.1.5:8899/chat`, body template
   `{"message": "{prompt}"}`, response path `reply`.
4. Android 17 asks for **local network access** the first time. Without that grant the request
   is refused by the platform — the app says so explicitly instead of showing a timeout.
   (On Android 16 and older this permission does not exist and nothing is asked.)

`localhost` on the phone means *the phone*. Always use the LAN address of the machine running
the target.

## Where exports go

The toolkit's three export buttons write into **Downloads/**:

* `airt_scan_<timestamp>.json` — machine-readable results
* `airt_report_<timestamp>.html` — self-contained evidence report (open in any browser)
* `airt_scan_<timestamp>.sarif` — SARIF 2.1.0 for GitHub code scanning / DefectDojo

The dashboard can also copy or share a diagnostics blob (build, device, permissions, endpoint)
— that is the fastest way to get help with a problem.

## Trust and verification

* Framework-only app: no Play Services, no analytics, no third-party runtime libraries.
* Only bundled pages and the configured agent origin are allowed to render in-app; every other
  link opens in the browser.
* Release APKs are signed with a stable, documented key so updates install in place. Verify a
  download yourself:

  ```bash
  sha256sum Ratan-AI-Agent-2.0.0-release.apk     # match the release notes, which quote the
                                                 # hash of the exact asset they describe
  apksigner verify --print-certs Ratan-AI-Agent-2.0.0-release.apk | head -5
  # signing certificate SHA-256 (stable across builds):
  #   79dce484cfafa35025c8df74880a17c374f20a0b23a982331e85f4022908ca83
  ```

## Troubleshooting

| Symptom | Fix |
|---|---|
| "App not installed" while updating | An older RATAN AI AGENT build is still installed — uninstall it, then install 2.0. |
| Agent screen shows "OFFLINE" | No connectivity to the endpoint. The toolkit still works; check the endpoint in Settings. |
| LAN scan says permission required | Tap **Grant LAN access** on the dashboard and accept the Android dialog. |
| Voice input does nothing | Dashboard → **Allow mic** (Android shows the permission dialog once). |
| Download button does nothing | The toolkit falls back to the in-app saver; check **Downloads/** or the app's own folder on older Android. |

## Authorised testing only

Real adversarial prompts leave this app in `toolkit` mode, and the HTTP bridge reaches whatever
the phone can route to. Test only systems you own or have written permission to test.
