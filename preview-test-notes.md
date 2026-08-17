# Local preview test

The local preview at http://127.0.0.1:8765/ served the homepage and exposed the expected interactive elements, including the simulated map and radar canvases, console input, chips, form fields, and navigation links. The browser extraction showed the new map/radar accessibility labels and command-input label.

A follow-up console query returned an empty document title and zero credential focus elements, which suggests the browser console ran during a transient navigation/loading state rather than after full DOM initialization. Re-run the page view/console check after the page settles before treating that query as a failure.

The second local navigation to `/index.html` rendered the homepage successfully with the expected title, CTA links, simulated canvases, console input, and contact form. Browser extraction also confirmed the new canvas labels for the map and radar and the command input label. The visual preview retained the existing cyber/terminal identity while loading normally.

Final DOM verification passed: canonical URL, robots metadata, demo notice, primary navigation label, console role, simulated map label, three keyboard-focusable credential cards, and static CEH profile reference were all present. The browser console showed no runtime error output; only the verification object was present.

After integrating the Gemini-provided content, the local preview rendered the new navigation links, three security assessment cards, sanitized VAPT finding viewer, and four training-track cards. The browser showed the report tabs as interactive tab buttons and the page remained visually consistent with the existing cyber identity. The HIGH tab click was executed from the rendered page and did not produce a navigation or load failure.

The first console check ran before the correct tab was selected and showed the default Critical state. After selecting the correct HIGH tab, the rendered page visibly updated to `SAMPLE-INJ-02` with the sanitized dynamic-query finding and its remediation text. No real token, host, or client data is used.

Academy page local preview passed: title, three individual prices (`₹9,999`, `₹14,999`, `₹12,999`), bundle price (`₹32,999`), exact saving note (`₹4,998`), four mail enrollment links, and separate RATAN OS/RATAN AI links were present in the DOM. The public page rendered with the existing commercial visual system.

Homepage verification passed: `// ACADEMY` navigation, `#academy` preview, all three Academy prices, `Explore the Academy` CTA, `Existing Learning Tracks` heading, RATAN OS section, and multiple separate RATAN AI links were present. The homepage rendered with the original hero and existing product sections intact.

RATAN AI local preview passed: `/ai/` rendered the public product page with the v1→v5 lineage, V5 Gemini 3.7 Flash LIVE NOW badge, Explorer/Pro/Expert plans, requested prices, and chat CTAs. `/ai/chat/` rendered the noindex access gate with email/access-code fields, safe-use notice, Gemini 3.7 Flash label, and request-access fallback. The frontend defaults to `/api/ai/chat` or a configurable `window.RATAN_AI_PROXY_URL`; it does not contain a Gemini key.

The local chat gate test accepted a synthetic test email/access code and transitioned to the conversation panel with the initial safety message and composer. This confirms the UI gate behavior only; the upstream proxy remains intentionally unconfigured in the local static preview.

Cloudflare deployment attempts: the Cloudflare MCP execute call and direct REST upload both returned authentication error 10000 / HTTP 401. The dashboard opened in the browser but remained on the Cloudflare loading screen with no interactive controls, so no browser deployment action was taken. No Gemini secret was sent or changed in these failed attempts.

Final local health-check passed: 20 HTML pages scanned, 0 broken local href targets, 0 duplicate ID pages, 0 old external RATAN AI links, Academy prices present, RATAN AI version history and plans present, sitemap entry present, and no Gemini key in frontend files. Published GitHub Pages check: `/` returned 200, while `academy.html`, `/ai/`, and `/ai/chat/` returned 404 because the review branch has not been merged/pushed to the live main deployment.

Homepage upper offer update verified locally: the top strip now reads `FEATURED OFFERS // FIVE PATHS` and includes a gold-accented `RATAN ACADEMY` card with `3 ethical-hacking tracks`, starting price ₹9,999, Full Academy ₹32,999, approximately ₹5,000 saving, and a working `VIEW ACADEMY OFFER` link to academy.html. The separate Academy section below the hero also shows the updated track names and pricing.

Business audit QA: local homepage now renders 500+ and 6+ counter fallback values, focused hero CTAs (`REQUEST A SCOPE CALL`, `JOIN RATAN ACADEMY`, `TRY RATAN AI`, `FREE RATAN OS DOWNLOADS`), enterprise scope note, credential-verification CTA, WhatsApp fallback and SHA256/trust-center CTA. Top RATAN OS card now says free release with optional support rather than implying paid download. New `insights.html` rendered successfully with three practical security articles and OWASP reference links; navigation and CTAs are present.

Academy consolidation QA: `ratan-monetization-launch-kit.html` now contains the full three-track RATAN Academy curriculum, Harvard/MIT/Oxford reference links, non-affiliation notice, individual prices and Full Academy bundle. The old `/academy.html` compatibility route redirected locally to `ratan-monetization-launch-kit.html#academy-offer`; only the RATAN ACADEMY OFFER navigation entry remains.

Credential-removal QA: local homepage renders successfully after removing the credential-verification CTA and synthetic verification hash. Education and certification cards remain; no browser console output/errors were observed.

RATAN OS latest-version QA: homepage no longer contains v1.0/v1.0.0/ratan-os-1.0 references. Hero shows OS v1.3.0 Latest CLI Build; the OS section identifies v1.3.0 Ethical CLI (Parrot 7.3, amd64, QEMU/USB) and v1.2.0 Lite AI Edition (Debian XFCE, offline Qwen3-4B, 3.0 GiB). HTML parser and git diff checks passed. Local preview visibly shows the latest RATAN OS 7.3 Ethical CLI offer.

High-resolution website QA: local homepage visibly renders the sharpened portrait in the hero. Browser runtime confirmed the WebP source loaded completely at 1632x2176, with a 3/4 portrait frame and 1600px fluid max-width token at a 1280px viewport. The homepage extraction exposes the HD image asset without broken loading.
Payment-method QA: local offer page visibly reloads with a direct `View payment methods` CTA and two payment cards. The extracted page confirms UPI ID `9650053559@ybl`, UPI app link, USDT ERC-20-only wording, wallet `0xE06c98E92afd5Ba805293c7162707aA694772c78`, copy buttons, network confirmation mail link, USD reference-only wording, and irreversibility/seed-phrase safety copy. Local HTML parse, diff check and HTTP 200 checks passed.

IMPORTANT: This section contains public payment instructions. Confirm recipient, network and amount in writing before accepting any payment; never request or expose PINs, OTPs, seed phrases or private keys.

Live payment verification: GitHub Pages workflow completed successfully. Cache-busted live checks returned offer page HTTP 200, with UPI ID, supplied USDT ERC-20 wallet, USD reference-only wording, copy control and services USDT-equivalent quote all present.

