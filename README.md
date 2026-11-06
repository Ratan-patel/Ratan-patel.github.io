# Ratan Kumar Patel — Offensive Security Practitioner

> **CEH v12 · Red Team Operations · VAPT · AI Security · Corporate Cybersecurity Training**

Live site: **[ratan-patel.github.io](https://ratan-patel.github.io/)**

This repo hosts the source for my personal cybersecurity portfolio. The site documents 6+ years of adversarial simulation, VAPT engagements, AI/LLM security research, and 500+ professionals trained.

## What you'll find on the live site

| Section | URL | Description |
|---|---|---|
| Home | [/](https://ratan-patel.github.io/) | Main landing page — background, skills, experience, gallery |
| Red-Team Lab | [lab.html](https://ratan-patel.github.io/lab.html) | Browser-based hacking simulator (nmap, nikto, sqlmap, hydra, mimikatz, terminal) |
| **Super Agent** | [ratansec-superagent.html](https://ratan-patel.github.io/ratansec-superagent.html) · [docs](ratansec-os/superagent/README.md) | AI security agent — 139 Kali tools, terminal, mobile PWA console, RoE records + hash-chained evidence |
| Ethical Hacking Foundation | [ethical-hacking-foundation.html](https://ratan-patel.github.io/ethical-hacking-foundation.html) | Course track |
| Advanced Web & API Pentesting | [advanced-web-api-pentesting.html](https://ratan-patel.github.io/advanced-web-api-pentesting.html) | Course track |
| Red Team Adversary Simulation | [red-team-adversary-simulation.html](https://ratan-patel.github.io/red-team-adversary-simulation.html) | Course track |
| AI Security & LLM Red Teaming | [ai-security-llm-red-teaming.html](https://ratan-patel.github.io/ai-security-llm-red-teaming.html) | Course track |
| Portfolio | [ratan_patel_portfolio.html](https://ratan-patel.github.io/ratan_patel_portfolio.html) | Full portfolio |
| Resume | [ratan_patel_resume.html](https://ratan-patel.github.io/ratan_patel_resume.html) | Print-friendly CV |
| Monetization launch kit | [ratan-monetization-launch-kit.html](https://ratan-patel.github.io/ratan-monetization-launch-kit.html) | Services, courses, AI plans |

## RatanSec Super Agent (self-hosted, private API key)

An AI agent you run on your own machine/VPS with **your own** API key. It plans and executes
authorised security testing with 139 tools across 12 sections (recon → info access → vuln →
web/API → gaining access → exploitation → post-exploitation → priv-esc → cracking → wireless →
reporting → utility), streaming output to a dashboard, a mobile PWA and a CLI terminal.

Safety is enforced, not suggested: engagement **authorization records** (RoE) are mandatory,
destructive commands and intrusive tools always need a human tap, shell mode is off by default,
and every command lands in a hash-chained audit + evidence bundle.

- Android APK: GitHub **Releases** / Actions artifact ([android/README.md](ratansec-os/superagent/android/README.md))
- Docs: [ratansec-os/superagent/README.md](ratansec-os/superagent/README.md)
- Legal + authorization templates: [ratansec-os/docs/](ratansec-os/docs/)
- Quick start: `cd ratansec-os && pip install -r superagent/requirements.txt && uvicorn superagent.webui:app --host 0.0.0.0 --port 8000`

> Intended only for systems you are **written-authorised** to test.

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

## Projects in this repo

- **Portfolio website** — pure HTML/CSS/JS at the repo root (GitHub Pages).
- **[RatanSec OS](ratansec-os/README.md)** — Kali-based AI pentesting environment: AI copilot (OpenRouter tool-calling), 6 scan profiles (nmap/nikto/nuclei/sqlmap/gobuster...), web dashboard, CLI, human-in-the-loop approvals, scope allowlist, AI reports aur audit log. Docker + Render deploy ready. **Start karna hai?** → [CHALANE_KA_TARIKA.md](ratansec-os/CHALANE_KA_TARIKA.md) (Windows/Kali/phone/cloud, ek-command setup).

## Site technical

- Pure HTML/CSS/JS, hosted on GitHub Pages
- GEO score: **100/100** (AI-ready)
- Structured data: Person + Organization + WebSite + ItemList JSON-LD
- AI crawlers (GPTBot, ClaudeBot, PerplexityBot, Google-Extended, CCBot) explicitly allowed in robots.txt
- Sitemap at `/sitemap.xml` (9 URLs), llms.txt for AI engines

---

© Ratan Kumar Patel — built with discipline, deployed with `git push` (and a lot of `git commit --amend`).
