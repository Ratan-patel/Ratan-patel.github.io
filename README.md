# Ratan Kumar Patel — Offensive Security Practitioner

> **CEH v12 · Red Team Operations · VAPT · AI Security · Corporate Cybersecurity Training**

Live site: **[ratan-patel.github.io](https://ratan-patel.github.io/)**

This repo hosts the source for my personal cybersecurity portfolio. The site documents 6+ years of adversarial simulation, VAPT engagements, AI/LLM security research, and 500+ professionals trained.

## What you'll find on the live site

| Section | URL | Description |
|---|---|---|
| Home | [/](https://ratan-patel.github.io/) | Main landing page — background, skills, experience, gallery |
| Red-Team Lab | [lab.html](https://ratan-patel.github.io/lab.html) | Browser-based hacking simulator (nmap, nikto, sqlmap, hydra, mimikatz, terminal) |
| Pentest Lab Arsenal | [pentest-lab.html](https://ratan-patel.github.io/pentest-lab.html) | Full controlled-sandbox manifest, tool inventory, ATT&CK mapping and rebuild guide |
| Engagement Kit | [engagement-kit.html](https://ratan-patel.github.io/engagement-kit.html) | Interactive builder for the paperwork that makes testing lawful: **Authorization to Test** letter, **Rules of Engagement**, scope & exclusions checklist, abort procedure and engagement log. Includes readiness checks that block on empty exclusions, third-party testing and production-plus-high-impact combinations. Templates only — not legal advice |
| MITRE ATT&CK Mapper | [mitre-attack-mapper.html](https://ratan-patel.github.io/mitre-attack-mapper.html) | Interactive ATT&CK **v19** coverage cockpit — 180+ techniques across 15 tactics, real adversary profiles (APT29, Lazarus, Scattered Spider, Volt Typhoon, APT41), per-tactic scoring, gap analysis and an adversary-emulation plan generator. Runs fully client-side |
| C2 Frameworks & Detection | [c2-frameworks.html](https://ratan-patel.github.io/c2-frameworks.html) | Verified 2026 comparison of Cobalt Strike alternatives (Sliver, Mythic, Merlin, AdaptixC2, Empire, PoshC2 — plus Havoc's archive status), C2 architecture and redirector design, operator OPSEC, home-lab build guide and the defender-side detection playbook |
| RATAN OS Advanced | [ratan-os-advanced.html](https://ratan-patel.github.io/ratan-os-advanced.html) | Roadmap, architecture and an interactive build planner for RATAN OS Advanced Edition — module catalogue, size/RAM estimates, dependency resolution, isolated lab profiles and a generated live-build manifest |
| Ethical Hacking Foundation | [ethical-hacking-foundation.html](https://ratan-patel.github.io/ethical-hacking-foundation.html) | Course track |
| Advanced Web & API Pentesting | [advanced-web-api-pentesting.html](https://ratan-patel.github.io/advanced-web-api-pentesting.html) | Course track |
| Red Team Adversary Simulation | [red-team-adversary-simulation.html](https://ratan-patel.github.io/red-team-adversary-simulation.html) | Course track |
| AI Security & LLM Red Teaming | [ai-security-llm-red-teaming.html](https://ratan-patel.github.io/ai-security-llm-red-teaming.html) | Course track |
| CMU MSIS Handbook | [cmu-msis-handbook.html](https://ratan-patel.github.io/cmu-msis-handbook.html) | Free online cybersecurity handbook — 6 chapters, 40 sections, practical examples |
| Portfolio | [ratan_patel_portfolio.html](https://ratan-patel.github.io/ratan_patel_portfolio.html) | Full portfolio |
| Resume | [ratan_patel_resume.html](https://ratan-patel.github.io/ratan_patel_resume.html) | Print-friendly CV |
| Monetization launch kit | [ratan-monetization-launch-kit.html](https://ratan-patel.github.io/ratan-monetization-launch-kit.html) | Services, courses, AI plans |


## Commercial and trust pages

| Page | Purpose |
|---|---|
| [Services](https://ratan-patel.github.io/services.html) | Scope-first VAPT and red-team packages with starting prices, process and authorization boundary. |
| [Offers](https://ratan-patel.github.io/ratan-monetization-launch-kit.html) | Training, RATAN OS and RATAN AI access overview. |
| [RATAN OS Release](https://ratan-patel.github.io/ratan-os-release.html) | Download route, verification status and safe-use guidance. |
| [Policies](https://ratan-patel.github.io/terms.html) | Terms, privacy/data handling, refund guidance and acceptable use. |

## Credentials

- **CEH v12** — EC-Council (ECC92840 · valid Jul 2024 – Jul 2027)
- **MS Cybersecurity & Information Assurance** — Western Governors University (2023)

## Services available for hire (remote-first)

- Corporate ethical hacking workshops & bootcamps
- VAPT engagements (web, API, network, cloud)
- Red team / adversary simulation
- AI/LLM security assessments
- CTF design and facilitation
- 1-on-1 mentoring for bug bounty hunters

## Contact

- **Email:** patelratan460@gmail.com
- **WhatsApp:** https://wa.me/918700913645
- **LinkedIn:** [linkedin.com/in/ratan-kumar-patel-032a43367](https://www.linkedin.com/in/ratan-kumar-patel-032a43367/)
- **Website:** [ratan-patel.github.io](https://ratan-patel.github.io/)

## Android builds in this repo

Two apps are built here by GitHub Actions and published as release assets — no local Android
toolchain required on your machine:

| App | Source | Download |
|---|---|---|
| **RATAN AI AGENT 2.0** — assistant + offline red-team toolkit, Android 17 (API 37) | [`apps/ratan-ai-agent/`](apps/ratan-ai-agent/) | [Ratan-AI-Agent-2.0.0-release.apk](https://github.com/Ratan-patel/Ratan-patel.github.io/releases/download/ratan-ai-agent-v2.0/Ratan-AI-Agent-2.0.0-release.apk) |
| **AIRT Scanner 1.0** — AI red-teaming probe engine for a phone | [`tools/ai-redteam-scanner/`](tools/ai-redteam-scanner/) | [AIRT-Scanner-1.0.0-release.apk](https://github.com/Ratan-patel/Ratan-patel.github.io/releases/download/airt-v1.0.0/AIRT-Scanner-1.0.0-release.apk) |

Both are framework-only WebView apps (no analytics, no third-party runtime), signed with a
stable key so updates install in place, and both ship the same 67-probe AIRT corpus so the
phone and the CLI can never disagree about what was tested.

## Site technical

- Pure HTML/CSS/JS, hosted on GitHub Pages
- GEO score: **100/100** (AI-ready)
- Structured data: Person + Organization + WebSite + ItemList JSON-LD
- AI crawlers (GPTBot, ClaudeBot, PerplexityBot, Google-Extended, CCBot) explicitly allowed in robots.txt
- Sitemap at `/sitemap.xml` (9 URLs), llms.txt for AI engines

---

© Ratan Kumar Patel — built with discipline, deployed with `git push` (and a lot of `git commit --amend`).
