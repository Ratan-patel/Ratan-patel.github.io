# Ratan Patel वेबसाइट सुधार रिपोर्ट

## स्थिति का सार

मैंने सार्वजनिक वेबसाइट [ratan-patel.github.io](https://ratan-patel.github.io/) [1] और उसके GitHub Pages स्रोत कोड का ऑडिट किया। Google AI Studio में पिछली Gemini 3.7 Flash चैट खोलने की कोशिश की गई, लेकिन उपलब्ध ब्राउज़र सत्र में `patelratan460@gmail.com` खाता **Signed out** दिखा। इसलिए उस पुरानी चैट के शब्दशः सुझाव निकालना संभव नहीं हुआ। Gemini 3.7 Flash API की मॉडल उपलब्धता सत्यापित हुई, पर ऑडिट अनुरोध पर API ने लगातार `503 Service Unavailable` लौटाया। इस कारण नीचे के बदलाव प्रकाशित वेबसाइट और स्रोत कोड के स्वतंत्र तकनीकी ऑडिट पर आधारित हैं।

## लागू किए गए सुधार

| क्षेत्र | क्या बदला | लाभ |
|---|---|---|
| SEO | Canonical URL, robots metadata और `og:type=website` जोड़े गए। | Search/social parsers को पेज की canonical पहचान अधिक स्पष्ट मिलती है। |
| Trust और clarity | “Live Attack Surface Grid” को “Simulated Attack Surface Grid” किया गया और स्पष्ट नोट जोड़ा गया कि map, feed, counters और readiness scores वास्तविक monitoring नहीं हैं। | Demo telemetry को live security claim समझे जाने का जोखिम कम होता है। |
| Console safety | Console header को `DEMO CONSOLE · NO NETWORK ACCESS` किया गया; “secure session” भाषा को local demonstration wording से बदला गया। | इंटरैक्टिव हिस्सा वास्तविक network shell या live monitoring नहीं होने की बात साफ़ करता है। |
| Outdated route | Terminal में hardcoded `gofile.io` download route हटाकर `ratan-os-release.html#free-downloads` internal release route किया गया। | टूटे या अस्थायी third-party download link का जोखिम घटता है। |
| Accessibility | Primary navigation label, menu button `aria-expanded`, console `role=log`, command input label और map/radar canvas labels जोड़े गए। | Screen readers और keyboard users के लिए site context बेहतर होता है। |
| Keyboard interaction | Credential flip cards को `tabindex` दिया गया और hover के साथ focus पर भी detail view खुलता है। | Credential cards अब keyboard से भी उपयोग किए जा सकते हैं। |
| Reduced motion | `prefers-reduced-motion: reduce` support जोड़ा गया; भारी background motion और animations कम हो जाते हैं। | Motion-sensitive users के लिए अनुभव अधिक सुरक्षित और आरामदायक होता है। |
| Verification reference | Random बदलते verification hash को स्थिर `CEH v12 · ECC92840` profile reference किया गया। | UI में हर कुछ सेकंड बदलने वाले pseudo-verification value से बचा गया। |

## ऑडिट में मिले महत्वपूर्ण विषय

वेबसाइट का cyber/terminal visual identity प्रभावशाली है, लेकिन homepage बहुत लंबा और animation-heavy है। इसके कारण मुख्य visitor—corporate client, training customer या VAPT prospect—के लिए यह समझना कठिन हो सकता है कि पहले कौन-सा action लेना है। अगले चरण में hero section में तीन स्पष्ट user paths रखना उपयोगी होगा: **VAPT / Red Team**, **Training**, और **RATAN OS**। प्रत्येक path को एक outcome-oriented CTA और एक संक्षिप्त proof point से जोड़ा जा सकता है।

मौजूदा page में simulated attack feed, readiness percentages, scan outputs और certificate verification animations हैं। इन्हें स्पष्ट demo labels देना trust के लिए आवश्यक था और यह सुधार branch में लागू कर दिया गया है। वास्तविक credential verification के लिए केवल तभी external verification link दिखाना चाहिए जब वह आधिकारिक और स्थायी हो; client-side “verification hash” को प्रमाण के रूप में प्रस्तुत नहीं करना चाहिए।

संपर्क form mail client में `mailto:` draft खोलता है, जो static GitHub Pages के लिए सरल और privacy-preserving है। फिर भी CTA copy में यह स्पष्ट रहना चाहिए कि form submit करने के बाद visitor को अपने mail client में **Send** दबाना होगा। वर्तमान copy यह बात बताती है; इसे भविष्य में prominent success state और fallback email link के साथ और मजबूत किया जा सकता है।

## परीक्षण

स्थानीय preview server पर homepage सफलतापूर्वक render हुआ। DOM verification में canonical URL, robots metadata, demo notice, primary navigation label, console log role, simulated map label, तीन keyboard-focusable credential cards और स्थिर CEH profile reference मौजूद मिले। `git diff --check` भी सफल रहा और browser console में कोई runtime error दिखाई नहीं दिया।

## Gemini द्वारा साझा किए गए HTML से किए गए integrations

आपके attachment में दिया गया HTML एक अलग Tailwind/Three.js homepage concept था। उसे पूरा replacement बनाने के बजाय मैंने उसके उपयोगी content architecture को मौजूदा साइट की cyber/terminal identity और RATAN OS sections को सुरक्षित रखते हुए integrate किया है। इसमें **Authorized Security Assessments** के तीन cards, एक fictional और sanitized VAPT finding viewer, तथा चार structured training tracks जोड़े गए हैं। Navigation में `TRAINING` और `SAMPLE` anchors भी जोड़े गए हैं।

Attachment में sample report के भीतर token-जैसा और internal-host-जैसा text था। उसे live-looking credential या target detail के रूप में copy नहीं किया गया। Integrated viewer केवल `<redacted-example-token>`, `example-records` और `example.invalid` जैसे clearly fictional placeholders इस्तेमाल करता है और UI पर साफ़ लिखा है कि इसमें कोई real client data, credential या target detail नहीं है। Tab interaction `textContent` के माध्यम से सुरक्षित रूप से update होती है, इसलिए sample payload HTML injection का रास्ता नहीं बनाता।

## नई Cyber Security Academy architecture

नई Academy को अलग landing page `academy.html` में बनाया गया है। उसमें तीन paid tracks अलग cards में हैं: **Cyber Security Foundations** — ₹9,999 और 12 weeks; **Offensive Systems Security** — ₹14,999 और 14 weeks; तथा **Cyber Risk, Operations & Strategy** — ₹12,999 और 10 weeks। Full Academy Program तीनों tracks को ₹32,999 में जोड़ता है। सूची-मूल्य ₹37,997 होने के कारण exact saving ₹4,998 है, इसलिए UI में इसे **approximately ₹5,000 saving** लिखा गया है; यह pricing arithmetic को ईमानदारी से दर्शाता है।

Homepage पर Academy का compact pricing preview और `// ACADEMY` navigation link जोड़े गए हैं। पहले से मौजूद practical learning material को **Existing Learning Tracks** नाम देकर अलग रखा गया है। RATAN OS का existing `#ratanos` section और RATAN AI के existing external CTAs को बदला नहीं गया; Academy footer में भी दोनों अलग product links के रूप में दिखते हैं। Academy page को `sitemap.xml` में भी जोड़ा गया है।

## Git स्थिति

बदलाव live `main` branch पर publish नहीं किए गए हैं। वे स्थानीय branch `improve/gemini-audit-2026` में commit `534ddf7` पर हैं। Patch file साथ में दी गई है ताकि आप बदलावों की समीक्षा कर सकें। यदि आप चाहें तो अगला कदम GitHub पर branch push करना, pull request बनाना, या आपकी स्पष्ट अनुमति के बाद `main` में merge करना हो सकता है।

## Academy course reference update

Academy के तीन paid tracks अब वास्तविक ethical-hacking/cybersecurity curriculum themes पर आधारित हैं। पहला track **Cybersecurity Foundations & Ethical Hacking** है, जो Harvard के CS50 Introduction to Cybersecurity topics—hacking/cracking, social-engineering risks, passwords, MFA और defensive foundations—से प्रेरित है [6]। दूसरा track **Offensive Security & Web Application Testing** है, जो MIT xPRO Professional Certificate in Cybersecurity के vulnerability testing, simulated web-application attacks और learn-by-doing themes से प्रेरित है [7]। तीसरा track **Cyber Defence, Threat Detection & Systems Security** है, जो Oxford Advanced Security तथा Oxford MSc in Software and Systems Security के attack detection, threat modelling, SOC/incident response, secure programming, network/cloud security और governance themes से प्रेरित है [8] [9]।

Page copy में स्पष्ट कर दिया गया है कि RATAN Academy स्वतंत्र है और Harvard, MIT या Oxford से affiliated, accredited या certified होने का दावा नहीं करती। University names केवल public curriculum references के रूप में links सहित दिखाए गए हैं। User-provided prices और durations unchanged हैं: ₹9,999/12 weeks, ₹14,999/14 weeks और ₹12,999/10 weeks; Full Academy bundle ₹32,999 है।

## RATAN AI V5 implementation

RATAN AI के लिए public page `ai/index.html` और chat route `ai/chat/index.html` बनाए गए हैं। Public page में v1 Gemini 1.5, v2 Gemini 2.0, v3 Gemini 2.5, v4 Gemini 3.6 और v5 Gemini 3.7 Flash की पूरी version history है। v5 को **LIVE NOW** mark किया गया है। Explorer free, Pro ₹499 और Expert ₹1,499 plans उसी page पर हैं। Chat route noindex है और उसमें access gate, responsible-use notice तथा Gemini 3.7 Flash chat composer है।

Gemini API key को static frontend में नहीं रखा गया। `cloudflare/worker.js` में server-side proxy तैयार है। Worker `GEMINI_API_KEY` और `RATAN_AI_ACCESS_CODE` को secrets के रूप में अपेक्षित करता है, invalid access पर 401 और unconfigured deployment पर 503 देता है, message length सीमित करता है, और Gemini Interactions API के stable model string `gemini-3.7-flash` को call करता है। Worker unit test में model selection, upstream API-key header, access-code gate और response parsing सफल रहे।

अभी live chat को production में स्वीकार करने से पहले Cloudflare Worker deploy करना, दोनों secrets configure करना और वास्तविक identity provider या managed access layer जोड़ना बाकी है। Static email/access-code gate केवल UI gate है; असली security boundary Worker secret check है। GitHub Pages custom `/api/ai/chat` reverse proxy नहीं देता, इसलिए या तो Worker URL को `window.RATAN_AI_PROXY_URL` में configure करना होगा, या custom domain/reverse proxy के पीछे `/api/ai/chat` map करना होगा।

Google की आधिकारिक guidance के अनुसार API key को client-side code में expose नहीं करना चाहिए; इसी कारण यह separation रखा गया है [3]। Google की current model list में `gemini-3.7-flash` stable model endpoint के रूप में दर्ज है [4]। Interactions API request shape और multi-turn `previous_interaction_id` flow official text-generation guide के अनुरूप है [5]।

## References

[1]: https://ratan-patel.github.io/ "Ratan Patel public website"
[2]: https://aistudio.google.com/ "Google AI Studio"
[3]: https://ai.google.dev/gemini-api/docs/api-key "Google Gemini API key and security guidance"
[4]: https://ai.google.dev/gemini-api/docs/models "Google Gemini API model list"
[5]: https://ai.google.dev/gemini-api/docs/text-generation "Google Gemini API text generation and Interactions API"
[6]: https://pll.harvard.edu/course/cs50s-introduction-cybersecurity "Harvard CS50's Introduction to Cybersecurity"
[7]: https://xpro.mit.edu/courses/course-v1:xPRO-PCCYx/ "MIT xPRO Professional Certificate in Cybersecurity"
[8]: https://www.cs.ox.ac.uk/teaching/courses/2024-2025/advsec/ "Oxford Advanced Security"
[9]: https://www.ox.ac.uk/admissions/graduate/courses/msc-software-and-systems-security "Oxford MSc in Software and Systems Security"


## Homepage Academy offer

Homepage के सबसे ऊपर वाले featured-offer strip को `FEATURED OFFERS // FIVE PATHS` में बदला गया है। इसमें RATAN Academy का gold-accented card अब सीधे दिखाई देता है: तीन ethical-hacking tracks, ₹9,999 से starting price, Full Academy ₹32,999 और लगभग ₹5,000 saving के साथ `VIEW ACADEMY OFFER` CTA। यह card `academy.html` पर जाता है; RATAN AI, RATAN OS, free ethical-hacking starter और VAPT/services cards अलग बने हुए हैं।


## Menu Offers page Academy callout

The menu bar `// OFFERS` route, `ratan-monetization-launch-kit.html`, now opens with a prominent `00 // RATAN ACADEMY OFFER` callout. It shows the three ethical-hacking track prices, the Full Academy price of INR 32,999, the exact INR 4,998 saving, and an `Explore RATAN Academy` CTA to `academy.html`. The existing standalone courses, VAPT/Red Team services, RATAN OS and RATAN AI offers remain separate below it. Local link and pricing checks passed.


## Business audit pass — August 2026

The pasted business audit was cross-checked against the live homepage and source code. The most concrete issue was the hero counters rendering as zero; the HTML now contains truthful fallback values of `500+` and `6+`, while the animation can still enhance them when JavaScript runs. The hero now has a clearer conversion hierarchy: `REQUEST A SCOPE CALL`, `JOIN RATAN ACADEMY`, `TRY RATAN AI`, and `FREE RATAN OS DOWNLOADS`, followed by an enterprise scope note.

Lead capture remains intentionally privacy-preserving because the current GitHub Pages site has no hosted form backend. The inquiry form still opens an email draft, but it now has a visible WhatsApp fallback. No CRM or Formspree endpoint was invented without a user-owned account and consent. The credentials section now offers a request-verification-details path without fabricating a public EC-Council verification URL.

The homepage now links to a new `insights.html` page with three practical, authorization-first articles on API readiness, BOLA/IDOR and AI security boundaries, each linking to the relevant OWASP reference. RATAN OS now has a working `#verification` anchor from the homepage trust CTA, and the top offer copy distinguishes free downloads from optional INR 4,999 setup/checksum support. The CMU handbook copy now explicitly describes itself as an independent reference and not a CMU course, credential or partnership. Services now explain that international teams may request a USD quote while INR values remain the source starting points.

Static QA after the changes: 21 HTML pages, zero broken local targets, zero duplicate IDs, zero old external RATAN AI links, Academy pricing math passed, Insights route present, verification anchor present, counter fallback present, WhatsApp fallback present, non-affiliation wording present, and the old paid-download wording removed.


## RATAN Academy consolidation

The standalone Academy landing page has been merged into the menu-linked `RATAN ACADEMY OFFER` page at `ratan-monetization-launch-kit.html`. The consolidated page now contains the complete three-track curriculum, official Harvard/MIT/Oxford curriculum-reference links, non-affiliation wording, individual prices, enrollment CTAs, Full Academy pricing and lawful-use boundary. The old `academy.html` route remains only as a compatibility redirect to `ratan-monetization-launch-kit.html#academy-offer`; it has been removed from the sitemap and from public navigation. Existing links were updated to the consolidated page, and local checks passed for the three tracks, bundle arithmetic, redirect, sitemap exclusion and absence of legacy Academy links.


## Credential-verification cleanup

The unnecessary credential-verification CTA, request-verification email link, synthetic CEH verification hash and related verification wording were removed from the public homepage. The education and certification cards remain as ordinary profile information, without inviting verification or presenting a client-side hash as proof. HTML-only scan returned zero credential-verification references, and the local homepage loaded without browser console output.
