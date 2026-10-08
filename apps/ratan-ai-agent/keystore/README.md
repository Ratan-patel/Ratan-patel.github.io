# Signing key for RATAN AI AGENT releases

`ratan-agent-release.p12` is a PKCS#12 keystore (RSA-4096, self-signed, ~30-year validity)
used by `.github/workflows/build-ratan-agent-apk.yml` so every build of the app carries the
**same signature**. That is what lets a new release install over the previous one instead of
forcing users to uninstall.

| | |
|---|---|
| file | `ratan-agent-release.p12` |
| alias | `ratan-agent` |
| store password | `quartz-agent-ratan-zenith-b3e6bf297507` |
| key password | `quartz-agent-ratan-zenith-b3e6bf297507` |
| store type | `PKCS12` |
| certificate SHA-256 | `79dce484cfafa35025c8df74880a17c374f20a0b23a982331e85f4022908ca83` |

## This key is public on purpose — read before shipping

A keystore that lives in a public repository provides **no identity guarantee**. Anyone can
sign an APK with it. Its only job here is to keep the signature stable for sideload updates,
which is exactly the trust model of an Android debug key — with the difference that the
fingerprint is documented so anyone can verify they installed a build from this repo.

Before distributing anywhere that matters (Play, an enterprise MDM, paying clients), generate
your own key and inject it through CI secrets instead:

```bash
python3 apps/ratan-ai-agent/tools/make_keystore.py \
    --out /secure/location/ratan-agent.p12 --alias ratan-agent --password "$(openssl rand -base64 24)"

base64 -w0 /secure/location/ratan-agent.p12   # -> GitHub secret ANDROID_KEYSTORE_BASE64
```

Repository secrets the workflow understands (all four must be set):

* `ANDROID_KEYSTORE_BASE64` — the `.p12` file, base64-encoded
* `ANDROID_KEYSTORE_PASSWORD`
* `ANDROID_KEY_ALIAS`
* `ANDROID_KEY_PASSWORD`

When they are absent the workflow transparently falls back to the in-repo keystore above, so
community forks still produce installable, checksum-verifiable APKs.

Verify the signature of any published APK yourself:

```bash
apksigner verify --print-certs Ratan-AI-Agent-2.0.0-release.apk | head -5
```
