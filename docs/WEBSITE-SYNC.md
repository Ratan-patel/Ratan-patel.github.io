# Website sync checklist

The live site is published by GitHub Pages **from `main`**. A change that only lives on a
feature branch is not on the website yet — merge first, then verify.

This file exists so that every future app/tool release keeps the site truthful. Work down it
whenever something ships.

## 1. Facts that change with every build (never hard-code these)

| Fact | Why | Where it belongs instead |
|---|---|---|
| APK **SHA-256** | Every build is a fresh ZIP, so the hash changes when CI runs again — even for identical source | The **release notes**, which the workflow regenerates per build, and the release comment. Site copy says "the release notes quote the hash of the asset it is serving". |
| APK **size** | Moves by a few bytes between builds | Say "about 700 KB", not an exact byte count. |
| **Signing certificate** SHA-256 | Stable on purpose: it is what lets one build upgrade another | Safe to print on the site, in READMEs and in `llms.txt`: `79dce484cfafa35025c8df74880a17c374f20a0b23a982331e85f4022908ca83` |
| **Package name / versionCode / versionName** | Change only on a deliberate bump | Fine to print; remember `tools/verify_apk.py` fails the build if they drift from the workflow's expectations. |

## 2. On every release

1. **Bump** in `apps/ratan-ai-agent/android/app/build.gradle`: `versionCode`, `versionName`.
2. **Mirror the version** in `.github/workflows/build-ratan-agent-apk.yml` (artifact names,
   `RELEASE_TAG`, titles, the `RATAN_VERSION_CODE`/`RATAN_VERSION_NAME` export for the verifier).
3. **Update the site** (all of these, or the site goes stale):
   - `ratan-ai-agent.html` — the release & trust page: download links, "what changed in <version>",
     compatibility table, troubleshooting.
   - `index.html` — the agent panel: version tag, download button, release-notes link, feature line.
   - `assets/enhancements.js` — the command-palette entry (download link).
   - `lab.html` — the simulation banner link.
   - `sitemap.xml` — `<lastmod>` for touched pages.
   - `llms.txt` — the AI-engine summary (versions, what the app does, certificate fingerprint).
   - `README.md` (root) — the site table and the Android-builds table.
   - `apps/ratan-ai-agent/README.md`, `apps/ratan-ai-agent/docs/APK.md` — install notes, features.
4. **Keep the shared nav in step** — the `AI AGENT APP` entry lives in the `nav-inner` block of
   every commercial page (plus the two RATAN OS pages, which use a slightly different anchor).
   A new page should be added to that block, to `sitemap.xml`, to `llms.txt` and to the palette.
5. **Commit and push the branch, open/merge the PR**, then wait for both workflows:
   - `Build RATAN AI AGENT APK` — rebuilds and republishes the release (a merge counts as a push
     to `main`, so this runs again even if the branch build already passed).
   - `pages build and deployment` — publishes the site.
6. **Verify** the deployment: `gh api repos/Ratan-patel/Ratan-patel.github.io/pages/builds/latest`
   should report `status: built` with the merge commit as `commit`. Then spot-check the live page.

## 3. When only prose changes

Add `[skip-agent-build]` to the commit message. The APK workflow's `if:` guard skips the run, so
an already-published asset is not replaced (and its hash does not move) just because a sentence
changed. Site-only paths (`*.html`, `sitemap.xml`, `llms.txt`, `README.md`) never trigger an APK
rebuild anyway — the guard is for commits that mix prose into `apps/**`.

## 4. Definition of done for a release

- [ ] Version bumped in Gradle **and** mirrored in the workflow
- [ ] CI green: APK built, verified, published, assets count ≥ 2
- [ ] Release notes carry the current hash, size and certificate
- [ ] `ratan-ai-agent.html` and the homepage panel show the new version and links
- [ ] `sitemap.xml`, `llms.txt`, both READMEs updated
- [ ] PR merged to `main`, `pages` build reports `built`
- [ ] Report back with: version, direct APK link, release link, certificate fingerprint
