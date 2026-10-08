# AIRT Scanner — Android app (APK)

Download (phone-friendly, always the latest build):

**https://github.com/Ratan-patel/Ratan-patel.github.io/releases/download/airt-v1.0.0/AIRT-Scanner-1.0.0-release.apk**

Also available on the [Releases page](https://github.com/Ratan-patel/Ratan-patel.github.io/releases)
as a workflow artifact (`airt-scanner-apk`) if the direct link is blocked.

## Install

1. Open the link **on the phone** (Chrome/Firefox). The file is ~40 KB, so it downloads instantly.
2. Open it from the notification or **Files → Downloads**.
3. Android will warn about installing from an unknown source → allow it for the browser,
   then tap **Install**. (The APK is signed with a debug key: installable by sideloading,
   not published on Play.)
4. Requires **Android 7.0+** (minSdk 24). No account, no permissions beyond network access,
   no telemetry.

## Why an app instead of a web page

A browser page cannot test most staging bots: cross-origin HTTP is blocked (CORS) and plain
`http://` endpoints are refused. The app performs every request **natively**
(`HttpURLConnection` through a WebView bridge), so:

* no CORS restrictions — any reachable endpoint works;
* `http://` lab endpoints work;
* custom headers / bearer tokens work;
* the whole 67-probe corpus + JS scoring engine ship **inside the APK** (works offline in
  simulator mode).

## Using it

**Simulator (no network, first run):**
Target type → *Offline simulator*, tick the authorisation box, **Start scan**.
That exercises the full engine and shows the report flow.

**Your own bot on the same Wi-Fi:**

1. On the laptop, start the bot so it listens on the LAN: the bundled practice bot already
   binds `0.0.0.0`, so `python3 examples/vulnerable_bot.py` is enough.
2. Find the laptop's LAN IP (`ipconfig` / `ip a`) — e.g. `192.168.1.5`.
3. In the app: Target type → *Custom HTTP bot*, endpoint
   `http://192.168.1.5:8899/chat`, body template `{"message": "{prompt}"}`,
   response path `reply`, tick authorisation → **Start scan**.
4. `localhost` on the phone means *the phone*, not your laptop — always use the LAN IP.

**A hosted bot:** paste the HTTPS URL and add `Authorization: Bearer …` in the headers box.

## Exports

The three buttons at the bottom write into **Downloads/**:
`airt_scan_<timestamp>.json`, `airt_report_<timestamp>.html`, `airt_scan_<timestamp>.sarif`.
Open the HTML one in any browser to share the evidence, or upload the SARIF to GitHub
Code Scanning.

## What it does not do

* It is not a Play-Store release: debug-signed, no signing config, no Play metadata.
* Single-turn probes only (same as the CLI today).
* The phone must reach the target — nothing is proxied through this project.
* Scanning a production system from a phone is a bad idea regardless of tooling.

## Rebuilding it yourself

The APK is built entirely by GitHub Actions — no local Android toolchain needed:

1. Fork/clone the repo, push any change under `tools/ai-redteam-scanner/android/**`
   (or run the workflow manually: **Actions → Build AIRT Scanner APK → Run workflow**).
2. The workflow installs JDK 17 + Gradle 8.7, uses the runner's preinstalled Android SDK,
   regenerates the bundled UI from the Python corpus, builds debug **and** release APKs,
   verifies them with `aapt2 dump badging` + a byte-for-byte asset hash check,
   uploads them as artifacts and publishes them to the release tag.

Local build (if you do have the SDK):

```bash
python3 gen_mobile.py                       # refresh the bundled page
cd android && gradle :app:assembleRelease   # APK in app/build/outputs/apk/release/
```
