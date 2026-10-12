#!/usr/bin/env python3
"""Generates job-applications/send.html — one-click Gmail compose page."""
import json, urllib.parse, html

CANDIDATE = dict(
    name="Ratan Kumar Patel",
    email="patelratan460@gmail.com",
    phone="+91-8700913645",
    location="Noida Sector 16, Uttar Pradesh, India",
    cv="https://ratan-patel.github.io/ratan_patel_cv.pdf",
    portfolio="https://ratan-patel.github.io/",
    lab="https://ratan-patel.github.io/lab.html",
    linkedin="https://www.linkedin.com/in/ratan-kumar-patel-032a43367/",
    github="https://github.com/Ratan-patel",
)

SIG = f"""Best regards,
{CANDIDATE['name']}
{CANDIDATE['phone']} (WhatsApp) · {CANDIDATE['email']}
{CANDIDATE['linkedin']} · {CANDIDATE['github']}"""

CREDS = """Credentials
- Certified Ethical Hacker (CEH v12) — EC-Council, ECC92840, valid Jul 2024 – Jul 2027
- M.S. Cybersecurity & Information Assurance — Western Governors University (2023)
- 6+ years hands-on · 500+ students trained (Appin Technology Lab, 2020–2026)"""

LINKS = f"""CV: {CANDIDATE['cv']}
Portfolio: {CANDIDATE['portfolio']}
Lab build: {CANDIDATE['lab']}"""

JOBS = [
    # ---- Round 1: remote cybersecurity trainer / instructor ----
    dict(id=1, prio="A",
         company="Hack The Box (HTB Academy)", to="academy@hackthebox.com",
         city="Athens / London", country="Greece / UK", remote="Global remote (contract)",
         role="Academy contract contributor / instructor",
         subject="Contract Academy contributor / live instructor — ethical hacking & web pentesting (CEH v12)",
         source="help.hackthebox.com — invites pitches to this address",
         body=f"""Hi HTB Academy Team,

Your help centre notes that HTB is "selectively open to contracting trusted individuals, prominent community members, or expert third-parties" for Academy content — so I'm writing to introduce myself directly.

I'm {CANDIDATE['name']}, a CEH v12-certified ethical hacker and cybersecurity trainer based in {CANDIDATE['location']}. I work remote-first and can join immediately. Six-plus years hands-on, 500+ students trained.

What I can build and deliver for HTB Academy:

  - Modules/rooms on web application pentesting (OWASP Top 10 — SQLi, XSS, IDOR, SSRF,
    auth bypass, file upload), Active Directory fundamentals, recon/OSINT, and practical
    Burp Suite / Metasploit / Nmap workflows
  - Live instructor-led delivery — I run live cohorts and CTFs and can teach synchronous
    sessions across IST / EU / US timezones
  - Curriculum I have already designed and shipped: CEH- and OSCP-aligned tracks, VAPT
    bootcamps, and red team / blue team lab environments

{CREDS}

Tools: Metasploit, Burp Suite, Nmap, Wireshark, Nessus/OpenVAS, OWASP ZAP, sqlmap, Mimikatz, Hydra, John the Ripper, Aircrack-ng, Kali Linux, Parrot OS.

{LINKS}

Happy to send a sample module outline, or record a short teach-back as an audition.

{SIG}"""),

    dict(id=2, prio="A",
         company="EC-Council (CEI Program)", to="cei@eccouncil.org",
         city="Albuquerque, NM", country="USA (global)", remote="Global — contract instructor pool",
         role="Certified EC-Council Instructor (CEI) — teach CEH worldwide",
         subject="CEI application enquiry — CEH v12 certified (ECC92840), 6+ years instructor experience",
         source="eccouncil.org — official CEI application / enquiry address",
         body=f"""Dear EC-Council CEI Team,

I would like to apply for the Certified EC-Council Instructor (CEI) program so that I can teach CEH and related EC-Council programs.

Candidate details
- Name: {CANDIDATE['name']}
- CEH v12 — EC-Council, Candidate/E Cert ID ECC92840, valid Jul 2024 – Jul 2027
- M.S. Cybersecurity & Information Assurance — Western Governors University (2023)
- Based in {CANDIDATE['location']} — remote-first, available worldwide
- Phone/WhatsApp: {CANDIDATE['phone']}

Instructor experience
- Ethical Hacker Trainer & Technical Security Manager, Appin Technology Lab (2020–2026):
  500+ students trained; designed and delivered modules on OWASP Top 10, Metasploit,
  Burp Suite, Kali Linux, Nmap and Nessus; delivered corporate ethical-hacking workshops
  and bootcamps; led red team / blue team exercises and CTF design.
- Technical Security Executive, Silent Front & Software Solutions (2018–2020): VAPT on
  client networks and web applications, mitigation strategies, client security reporting.

Day count over the past 12 months and course titles can be provided on request.

{CREDS}

Questions
1. I understand the CEI application requires endorsement by an EC-Council Accredited
   Training Center (ATC). Could you advise on how an independent candidate proceeds, or
   point me to ATCs currently accepting CEI sponsorships?
2. Please confirm whether my instructor experience letter from Appin Technology Lab
   satisfies the instructor-qualification requirement, or whether I should sit the
   CEI Exam (312-75).
3. Please send the current cei-agreement-v2.0.pdf application form.

{LINKS}

Thank you for your guidance.

{SIG}"""),

    dict(id=3, prio="A",
         company="Koenig Solutions", to="career@koenig-solutions.com",
         city="New Delhi / Platform, OH", country="India / USA", remote="100% remote — permanent WFH",
         role="Corporate Trainer — Security (ref. KS 369)",
         subject="Application — Cybersecurity Corporate Trainer (ref. KS 369, Security Management Trainer) — 100% remote",
         source="koenig-solutions.com/career — 'Email us at career@koenig-solutions.com'",
         body=f"""Dear Koenig Talent Team,

Your careers page invites candidates to share a resume directly at career@koenig-solutions.com, so I am writing in connection with the Security Management Trainer opening (KS 369) and any other cybersecurity trainer roles you are hiring for.

About me — {CANDIDATE['name']}, based in {CANDIDATE['location']}.

{CREDS}

Experience
- Ethical Hacker Trainer & Technical Security Manager, Appin Technology Lab (2020–2026)
  Trained 500+ students; designed modules on OWASP Top 10, Metasploit, Burp Suite, Kali
  Linux, Nmap, Nessus; delivered corporate ethical-hacking workshops and bootcamps; led
  red team / blue team exercises and CTF design; mentored bug bounty hunting and exploit
  development.
- Technical Security Executive, Silent Front & Software Solutions (2018–2020)
  Conducted VAPT on client networks and web applications, implemented mitigation
  strategies, prepared security reports and training documentation for junior analysts.

I can deliver across EC-Council (CEH), CompTIA Security+, ISC2 and hands-on VAPT tracks, and I am already set up for permanent work from home — exactly the model Koenig runs.

{LINKS}

Available immediately. Thank you for considering my application.

Warm regards,
{CANDIDATE['name']}
{CANDIDATE['phone']} (WhatsApp) · {CANDIDATE['email']}
{CANDIDATE['linkedin']} · {CANDIDATE['github']}"""),

    dict(id=4, prio="A",
         company="TryHackMe", to="business@tryhackme.com",
         city="London", country="UK", remote="Fully Remote (contract)",
         role="Live Class Lead / Live Training Instructor / Room Builder",
         subject="Live Class Lead / Live Training Instructor — fully remote contract",
         source="careers.tryhackme.com (Live Class Lead, Fully Remote)",
         body=f"""Hi TryHackMe Team,

I'm applying for the fully-remote contract instructor and Live Class Lead openings on your careers page (careers.tryhackme.com).

I'm {CANDIDATE['name']} — CEH v12-certified ethical hacker and cybersecurity trainer, based in {CANDIDATE['location']}, remote-first and available immediately.

Why I fit the live-class format:
- 6+ years delivering hands-on technical training; 500+ students trained at Appin
  Technology Lab (2020–2026)
- I run live, lab-led sessions in ethical hacking, VAPT, web application security
  (OWASP Top 10), red team/blue team exercises and CTF design
- I build the labs, not just the slides — I designed CEH/OSCP-aligned curricula and a
  browser-based red-team lab simulator: {CANDIDATE['lab']}
- Comfortable holding a live audience: Q&A, interaction, momentum, war stories from real
  VAPT engagements (Silent Front & Software Solutions, 2018–2020)

Topics I can own: ethical hacking / pentesting fundamentals, web app security, recon & OSINT, Burp Suite and Metasploit in practice, SOC Level 1–2, and AI security fundamentals.

{CREDS}

{LINKS}

I am on IST and can comfortably cover EU and APAC live-class slots. Happy to do a recorded or live audition session.

{SIG}"""),

    dict(id=5, prio="A",
         company="Simplilearn", to="careers@simplilearn.net",
         city="San Francisco, CA / Bangalore", country="USA / India", remote="Remote — global trainer network",
         role="Cybersecurity Trainer / Subject Matter Expert",
         subject="Cybersecurity Trainer / SME — remote, global trainer network",
         source="simplilearn.com/careers — 'reach out to careers@simplilearn.net'",
         body=f"""Dear Simplilearn Careers Team,

I'm writing to join Simplilearn's global trainer network as a Cybersecurity Trainer / Subject Matter Expert. Your careers page lists careers@simplilearn.net as the contact, so I'm reaching out directly.

About me — {CANDIDATE['name']}, based in {CANDIDATE['location']}; remote-first, immediate joiner.

{CREDS}
- Prior: Technical Security Executive, Silent Front & Software Solutions (2018–2020) —
  VAPT on client networks and web applications, mitigation strategies, security reporting

I can teach live classes across: CEH, ethical hacking and penetration testing, VAPT, web application security (OWASP Top 10), network and firewall security, incident response and threat intelligence, plus hands-on labs with Metasploit, Burp Suite, Nmap, Wireshark, Nessus, OWASP ZAP and sqlmap.

I have also built curriculum end-to-end (CEH/OSCP-aligned tracks, VAPT bootcamps, CTFs) and shipped a browser-based red-team lab simulator: {CANDIDATE['lab']}

{LINKS}

Happy to run a demo class for your content team.

{SIG}"""),

    dict(id=6, prio="A",
         company="Zync Group (recruiter)", to="charlie@zyncgroup.io",
         city="Düsseldorf / Berlin", country="Germany", remote="Worldwide fully remote (freelance)",
         role="Penetration Testing Project Lead — Freelance, €60/hr, worldwide remote",
         subject="Freelance Penetration Testing — 6+ yrs VAPT / CEH v12 (re: PT Project Lead, ref 5649)",
         source="Indeed/Zync job post — 'send your CV to charlie@zyncgroup.io'",
         body=f"""Hi Charlie,

I'm responding to the Penetration Testing Project Lead (Freelance — €60 per hour, Worldwide Fully Remote, ref 5649) posting, which lists charlie@zyncgroup.io as the contact.

I'll be straightforward about fit first: that posting asks for C2/native German. My German is limited (English fluency, Hindi native). If German is a hard requirement, this particular role isn't for me — but I'd like to be on your radar for the English-language mandates, and I'd welcome a steer on anything else you're running.

Profile — {CANDIDATE['name']}, based in {CANDIDATE['location']}, remote-first.

{CREDS}
- Technical Security Executive, Silent Front & Software Solutions (2018–2020): VAPT on
  client networks and web applications, mitigation strategies, client reporting

Technical: web application and infrastructure pentesting, network pentesting, threat modelling, vulnerability research and reporting. Tools — Burp Suite, Metasploit, Nmap, Kali Linux, Nessus/OpenVAS, OWASP ZAP, sqlmap, Mimikatz, Hydra, John the Ripper, Aircrack-ng.

I've also led delivery from the training side: 500+ students, corporate bootcamps, and I build lab environments ({CANDIDATE['lab']}) — useful if any of your clients need enablement or red-team upskilling alongside assessment work.

{LINKS}

Day rate and timezone coverage (IST, EU/US overlap) are flexible. Happy to jump on a call.

{SIG}"""),

    dict(id=7, prio="B",
         company="Springboard", to="mentorrecruiting@springboard.com",
         city="San Francisco, CA", country="USA", remote="Remote (part-time mentor)",
         role="Mentor — Cyber Security Career Track (part-time, remote)",
         subject="Cyber Security Career Track Mentor — CEH v12, 6+ yrs, 500+ students mentored",
         source="greenhouse.io/springboardmentors — mentorrecruiting@springboard.com",
         body=f"""Hi Springboard Mentor Recruiting Team,

I'd like to join the Cyber Security Career Track mentor community. I understand the cyber mentor cohort may currently be at capacity and that applying adds me to the waitlist — that's fine, please add me.

About me — {CANDIDATE['name']}, based in {CANDIDATE['location']}.

{CREDS}

Tooling mentioned in your posting that I work with daily: Wireshark, Nessus, Nmap, Kali Linux, Aircrack, Hashcat, VirtualBox, web app attack practice (WebGoat-style), plus Splunk-class log analysis and Snort-class IDS. I'm comfortable with the incident response, vulnerability assessment and network scanning material in the InfoSec Learning curriculum.

I note the posting prefers CISSP; I hold CEH v12 (EC-Council, ECC92840) and an M.S. in Cybersecurity & Information Assurance (WGU), with 6+ years of practitioner experience and 500+ learners trained. Weekly 30-minute video check-ins plus submission review are very much my normal rhythm — 1:1 mentoring and giving direct, useful feedback on learner work is the core of what I've done since 2020.

{LINKS}

Hourly expectation and weekly availability are flexible; I'm on IST and can cover US and EU learner slots.

{SIG}"""),

    dict(id=8, prio="B",
         company="Intellipaat", to="sales@intellipaat.com",
         city="Bangalore", country="India", remote="Fully online / remote",
         role="Cybersecurity Trainer (online bootcamps, 28-week cyber track)",
         subject="Trainer application — Cyber Security online bootcamp (CEH v12, 6+ yrs, 500+ learners)",
         source="intellipaat.com — public contact",
         body=f"""Dear Intellipaat Team,

I'd like to be considered as a trainer for Intellipaat's Cyber Security online programs (your 28-week cyber track and shorter certification courses).

About me — {CANDIDATE['name']}, based in {CANDIDATE['location']}; set up for fully online delivery with dedicated bandwidth and a teaching rig.

{CREDS}
- Prior: Technical Security Executive, Silent Front & Software Solutions (2018–2020) —
  VAPT on client networks and web applications, mitigation strategies, reporting

What I can own end-to-end:
- Live online batches on CEH, ethical hacking, penetration testing, VAPT, web application
  security (OWASP Top 10), network security, incident response and threat intelligence
- Hands-on labs with Metasploit, Burp Suite, Nmap, Wireshark, Nessus, OWASP ZAP, sqlmap,
  Kali Linux
- Curriculum and lab authoring — I've built CEH/OSCP-aligned tracks, VAPT bootcamps and
  CTFs, including a browser-based red-team simulator: {CANDIDATE['lab']}

I'm comfortable with weekday-evening and weekend IST batches, which is typically when working professionals attend.

{LINKS}

Happy to take a demo session for your academic team.

{SIG}"""),

    dict(id=9, prio="B",
         company="Imarticus Learning", to="info@imarticus.com",
         city="Bangalore / Delhi / Mumbai", country="India", remote="Live online (instructor-led)",
         role="Cyber Security faculty — live online bootcamps",
         subject="Faculty application — Cyber Security live online programs (CEH v12, 6+ yrs)",
         source="imarticus.com — public contact",
         body=f"""Dear Imarticus Learning Team,

I'm writing to apply as faculty / trainer for Imarticus Learning's Cyber Security programs (live online and classroom, Bangalore / Delhi / Mumbai).

About me — {CANDIDATE['name']}, based in {CANDIDATE['location']} — NCR, so Delhi batches are straightforward for me and I deliver online for everything else.

{CREDS}
- Prior: Technical Security Executive, Silent Front & Software Solutions (2018–2020) —
  VAPT on client networks and web applications, mitigation strategies, client reporting

Delivery strengths
- Live, lab-first instruction on CEH, ethical hacking, penetration testing, VAPT, web
  application security (OWASP Top 10), network and firewall security, incident response
  and threat intelligence
- 500+ learners trained across cohorts, with consistently strong feedback scores
- I build the labs and curriculum myself, including a browser-based red-team simulator:
  {CANDIDATE['lab']}
- Comfortable with industry-oriented seminars, capstone mentoring and guest-lecture format

{LINKS}

Available immediately, and flexible on evening/weekend batches for working professionals.

{SIG}"""),

    dict(id=10, prio="B",
         company="Educate 360 (TCM Security)", to="info@educate360.com",
         city="Boston, MA", country="USA", remote="Remote (live online) contract",
         role="Cybersecurity Instructor — Ethical Hacker Bootcamp / Web Pentesting / SOC / AI Hacking",
         subject="Cybersecurity Instructor application — Ethical Hacker Bootcamp / Web Penetration Testing (remote contract)",
         source="educate360.com/contact-us + Paylocity posting #4361530",
         body=f"""Dear Educate 360 Hiring Team,

I'm applying for the contract Cybersecurity Instructor role delivering live online training for TCM Security (Paylocity posting #4361530). I'm based in {CANDIDATE['location']}, work remote-first, and am available immediately as a remote contractor.

Courses I can own
- Ethical Hacker Bootcamp: OSINT and reconnaissance, Active Directory exploitation and
  defense, web application hacking basics, hands-on pentesting and professional reporting
- Web Penetration Testing: the four-day live track — vulnerability discovery and
  exploitation with real-world labs
- SOC Level 1 and Level 2
- AI Hacking 101 (I deliver AI-security content and built an LLM red-teaming module)

Note on location: the listing mentions US-based. If that is a hard requirement for this
engagement, I understand — but as a 1099-style remote contractor I can cover US delivery
windows from IST and would welcome being considered for any future cohort.

Why me
- CEH v12 (EC-Council, ECC92840, valid Jul 2024 – Jul 2027); M.S. Cybersecurity &
  Information Assurance, WGU (2023)
- Ethical Hacker Trainer & Technical Security Manager, Appin Technology Lab (2020–2026):
  500+ students trained, modules built on OWASP Top 10, Metasploit, Burp Suite, Kali
  Linux, Nmap, Nessus; corporate workshops and bootcamps; red team / blue team exercises;
  CTF design; bug bounty and exploit development mentoring
- Technical Security Executive, Silent Front & Software Solutions (2018–2020): VAPT on
  client networks and web applications, mitigation strategies, client security reporting
- Consistently top-rated by trainees for hands-on, lab-first delivery

Sample of my lab-building work: {CANDIDATE['lab']}

{LINKS}

Happy to run an audition session.

{SIG}"""),

    dict(id=11, prio="B",
         company="The Knowledge Academy", to="info@theknowledgeacademy.com",
         city="Bracknell, Berkshire", country="UK", remote="Online instructor-led (global)",
         role="Trainer — Cybersecurity / Ethical Hacking",
         subject="Trainer application — Cybersecurity / Ethical Hacking (online instructor-led, remote)",
         source="theknowledgeacademy.com/us/careers — 'taking applications for Trainers'",
         body=f"""Dear Recruitment Team,

Your careers page invites applications from Trainers, so I'm writing to offer my services as a Cybersecurity and Ethical Hacking trainer for your online instructor-led delivery.

About me — {CANDIDATE['name']}, based in {CANDIDATE['location']}; remote-first, immediate joiner.

{CREDS}
- Prior: Technical Security Executive, Silent Front & Software Solutions (2018–2020) —
  VAPT on client networks and web applications, mitigation strategies, reporting

Courses I can deliver online: CEH, CompTIA Security+, ethical hacking and penetration testing, VAPT, web application security (OWASP Top 10), network and firewall security, incident response and threat intelligence — all lab-first, using Metasploit, Burp Suite, Nmap, Wireshark, Nessus, OWASP ZAP and sqlmap.

I also build curriculum and labs, including a browser-based red-team simulator: {CANDIDATE['lab']}

{LINKS}

I'm on IST and can cover UK, EU, US and APAC delivery windows.

{SIG}"""),

    dict(id=12, prio="B",
         company="Firebrand Training", to="info@firebrandtraining.co.uk",
         city="London", country="UK", remote="Online + classroom",
         role="Technical Instructor — Cybersecurity / Ethical Hacking",
         subject="Technical Instructor application — Cybersecurity / Ethical Hacking",
         source="firebrand.training — public contact",
         body=f"""Dear Firebrand Training Team,

I'm writing to apply as a Cybersecurity / Ethical Hacking technical instructor with Firebrand.

About me — {CANDIDATE['name']}, based in {CANDIDATE['location']}.

{CREDS}
- Prior: Technical Security Executive, Silent Front & Software Solutions (2018–2020) —
  VAPT on client networks and web applications, mitigation strategies, reporting

I've built and delivered modules on OWASP Top 10, Metasploit, Burp Suite, Kali Linux, Nmap and Nessus, and run corporate bootcamps, red team / blue team exercises and CTFs.

Firebrand's accelerated format suits how I teach — high pace, high focus, lab-first, with certification outcomes front and centre. I can deliver CEH, CompTIA Security+, penetration testing, VAPT and web application security tracks.

I'm on IST and can cover UK/EU delivery windows for online instructor-led cohorts.

{LINKS}

{SIG}"""),

    dict(id=13, prio="B",
         company="Edureka", to="sales@edureka.co",
         city="Bangalore", country="India", remote="Fully online / freelance",
         role="Freelance instructor — Cybersecurity / Ethical Hacking",
         subject="Instructor application — Cybersecurity / Ethical Hacking (freelance, online)",
         source="edureka.co/instructors/add — instructors can teach from anywhere",
         body=f"""Dear Edureka Team,

I'd like to join Edureka as a freelance instructor for your Cybersecurity and Ethical Hacking programs. Your instructor page notes instructors can conduct training from anywhere in the world, which suits me well — I'm based in {CANDIDATE['location']} and deliver fully online.

About me — {CANDIDATE['name']}

{CREDS}
- Prior: Technical Security Executive, Silent Front & Software Solutions (2018–2020) —
  VAPT on client networks and web applications, mitigation strategies, reporting

I can own live batches on: CEH, ethical hacking and penetration testing, VAPT, web application security (OWASP Top 10), network security, incident response and threat intelligence. I'm comfortable co-creating content with your team and following Edureka's learning methodology.

I also build labs and curriculum — sample: {CANDIDATE['lab']}

{LINKS}

{SIG}"""),

    dict(id=14, prio="B",
         company="Cybrary", to="sales@cybrary.it",
         city="Maryland", country="USA", remote="Virtual classroom (Cybrary Live)",
         role="Cybrary Live instructor — ethical hacking / pentesting",
         subject="Cybrary Live instructor — ethical hacking / pentesting (virtual classroom)",
         source="cybrary.it — public contact; Cybrary Live is instructor-led",
         body=f"""Hi Cybrary Team,

I'm writing to be considered as an instructor for Cybrary Live — your boot-camp style virtual classroom where learners work directly with expert instructors.

About me — {CANDIDATE['name']}, based in {CANDIDATE['location']}; remote-first, immediate joiner.

{CREDS}
- Prior: Technical Security Executive, Silent Front & Software Solutions (2018–2020) —
  VAPT on client networks and web applications, mitigation strategies, reporting

I can deliver live sessions across ethical hacking, penetration testing, VAPT, web application security (OWASP Top 10), SOC operations, incident response and threat intelligence — lab-first, with Metasploit, Burp Suite, Nmap, Wireshark, Nessus, OWASP ZAP and sqlmap.

I also design curriculum and hands-on labs; sample build: {CANDIDATE['lab']}

{LINKS}

Happy to run a demo session for your team.

{SIG}"""),

    dict(id=15, prio="C",
         company="Red Arrow Security", to="hello@redarrowsecurity.com",
         city="Lahore, Punjab", country="Pakistan", remote="Remote",
         role="Penetration Tester / VAPT consultant (senior)",
         subject="Penetration Tester / VAPT consultant — CEH v12, 6+ yrs (remote, senior track)",
         source="redarrowsecurity.com — public contact; they run senior pentest hiring",
         body=f"""Hi Red Arrow Security Team,

I saw Red Arrow's hiring posts for offensive security roles and wanted to introduce myself. I'm writing about the senior track rather than the Associate / fresh-graduate opening.

About me — {CANDIDATE['name']}, based in {CANDIDATE['location']}, remote-first.

{CREDS}
- Prior: Technical Security Executive, Silent Front & Software Solutions (2018–2020)

What I deliver
- Web application, API and network penetration testing; VAPT across web, mobile and
  network; SAST/DAST and source-code review
- Tools: Burp Suite, Metasploit, Nessus, Kali Linux, OWASP ZAP, sqlmap, Nmap,
  Wireshark, Mimikatz, Hydra — aligned with OWASP and SANS methodology
- Clear, evidence-based reporting and client-facing findings walkthroughs
- I also build lab environments and run training ({CANDIDATE['lab']}) — useful if Red Arrow
  ever wants enablement or mentoring bundled with delivery

{LINKS}

Open to contract, part-time or retainer arrangements, and flexible on timezone overlap. Happy to share a sample redacted report.

{SIG}"""),
]


JOBS += [
    dict(id=16, prio="A",
         company="Kratikal Tech", to="resumes@kratikal.zohorecruitmail.com",
         city="Noida, Uttar Pradesh", country="India", remote="Noida-based (same city) + PAN-India offices",
         role="Manager – Security Testing / Security Analyst (AppSec)",
         subject="Application — Manager, Security Testing (Red Team / offensive security) — CEH v12, 6+ yrs, Noida based",
         source="kratikal.zohorecruit.com — 'Share your resume to resumes@kratikal.zohorecruitmail.com'",
         body=f"""Dear Kratikal Hiring Team,

I'm applying for the Manager – Security Testing role (Noida, 5+ years) and any Security Analyst – Application Security openings. I live in {CANDIDATE['location']}, so the Noida location is a straightforward commute.

About me — {CANDIDATE['name']}

{CREDS}
- Prior: Technical Security Executive, Silent Front & Software Solutions (2018–2020)

What I bring
- Web, mobile and API security testing; VAPT across network, web and application layers
- Red team / blue team exercise design and execution, plus CTF authoring
- Tools: Burp Suite, Metasploit, Nessus/OpenVAS, OWASP ZAP, sqlmap, Nmap, Wireshark,
  Mimikatz, Hydra, John the Ripper, Kali Linux
- Team leadership: as Technical Security Manager at Appin Technology Lab I ran the
  training delivery function, mentored junior analysts, and built the curriculum and lab
  environments for offensive security programs
- I build labs, not just run them: {CANDIDATE['lab']}

{LINKS}

Happy to walk through a redacted sample report or run a practical assessment exercise.

{SIG}"""),

    dict(id=17, prio="A",
         company="Allied Boston Consultants", to="info@alliedboston.com",
         city="Noida Sector 132, Uttar Pradesh", country="India", remote="Noida-based (same city)",
         role="Cyber Security Testing (CST) — consultant / trainer",
         subject="Cyber Security Testing + training — CEH v12, 6+ yrs, Noida based (immediate joiner)",
         source="alliedboston.com (Noida) — public contact info@alliedboston.com; Chitranshu Jain heads CST",
         body=f"""Dear Allied Boston Team,

I'm writing about opportunities in your Cyber Security Testing (CST) practice. I'm based in {CANDIDATE['location']} — your office is at Express Trade Towers 2, Sector 132, so I'm effectively local, and available immediately.

About me — {CANDIDATE['name']}

{CREDS}
- Prior: Technical Security Executive, Silent Front & Software Solutions (2018–2020)

What I can do for Allied Boston
- VAPT delivery: web, mobile, API and network testing; SAST/DAST and source-code review;
  clear, client-ready reporting
- Training delivery: I understand Allied Boston is a consulting *and training*
  organisation. Training is my core strength — 500+ learners, corporate workshops, and
  I can own CEH, VAPT, web app security and red team tracks end to end
- Curriculum and lab authoring — sample build: {CANDIDATE['lab']}
- Tools: Burp Suite, Metasploit, Nessus, OWASP ZAP, sqlmap, Nmap, Wireshark, Kali Linux

Open to full-time, contract, or a hybrid delivery-plus-training role.

{LINKS}

Happy to come in for a face-to-face discussion given we're in the same city.

{SIG}"""),

    dict(id=18, prio="A",
         company="Cyber Defentech", to="training@cyberdefentech.com",
         city="Rohini, Delhi", country="India", remote="Delhi NCR — online + offline batches",
         role="Trainer — Penetration Tester / Red Team Analyst Trainer",
         subject="Trainer application — Penetration Testing / Red Team Analyst (CEH v12, 6+ yrs, NCR based)",
         source="cyberdefentech.in / .com — public contact; role 'Trainer - Penetration Tester' advertised",
         body=f"""Dear Cyber Defentech Team,

I'm writing to apply for the Trainer – Penetration Tester / Red Team Analyst Trainer role. I'm based in {CANDIDATE['location']} — Rohini is a straightforward commute for me, and I'm comfortable with both classroom and online batches.

About me — {CANDIDATE['name']}

{CREDS}
- Prior: Technical Security Executive, Silent Front & Software Solutions (2018–2020) —
  VAPT on client networks and web applications, mitigation strategies, reporting

Courses I can own end to end
- CEH (I hold CEH v12 — EC-Council, ECC92840, valid Jul 2024 – Jul 2027)
- CPENT-aligned advanced enterprise penetration testing
- Ethical hacking, VAPT, web application security (OWASP Top 10), SOC, and cloud security
- Hands-on labs with Kali Linux, Nmap, Burp Suite, Wireshark, Metasploit, Nessus, OWASP
  ZAP and sqlmap

I run lab-first batches: every concept is demonstrated live, then the students break it themselves. I've designed CEH/OSCP-aligned curricula, run red team / blue team exercises and authored CTFs, plus a browser-based red-team simulator: {CANDIDATE['lab']}

My batch delivery days over the last 12 months and course titles are available on request.

{LINKS}

Available immediately, and flexible on weekday/weekend and evening batches.

{SIG}"""),

    dict(id=19, prio="A",
         company="Qualysec Technologies", to="career@qualysec.com",
         city="Bhubaneswar / Bengaluru", country="India", remote="India (CREST-accredited, remote-friendly)",
         role="Senior Penetration Tester (web, mobile, cloud, IoT, network)",
         subject="Senior Penetration Tester — CEH v12, 6+ yrs (web / network / cloud / API)",
         source="qualysec.com/career — 'For Career: career@qualysec.com'",
         body=f"""Dear Qualysec Hiring Team,

I'm applying for the Senior Penetration Tester role. Qualysec's careers page lists career@qualysec.com as the contact, so I'm reaching out directly.

About me — {CANDIDATE['name']}, based in {CANDIDATE['location']}, remote-first.

{CREDS}
- Prior: Technical Security Executive, Silent Front & Software Solutions (2018–2020)

Testing I deliver
- Web application, API, mobile (Android/iOS), network (external + internal) and cloud
  security assessments
- Manual testing with Burp Suite, Metasploit, Nessus/OpenVAS, OWASP ZAP, sqlmap, Nmap,
  Wireshark, Mimikatz, Hydra, John the Ripper, Kali Linux
- OWASP-aligned methodology; PTES-style scoping and reporting; clear remediation guidance
- I also build lab environments and run offensive-security training ({CANDIDATE['lab']}) —
  useful for internal enablement and for client-facing awareness sessions

I hold CEH v12 (EC-Council, ECC92840, valid Jul 2024 – Jul 2027), which your posting lists among the required certifications, and an M.S. in Cybersecurity & Information Assurance (WGU).

{LINKS}

Happy to complete a practical assessment or share a redacted sample report.

{SIG}"""),

    dict(id=20, prio="B",
         company="SecureLayer7", to="job@securelayer7.net",
         city="Pune / Austin, TX", country="India / USA", remote="Hybrid + remote",
         role="Security Consultant / Pentester / Engagement Lead",
         subject="Offensive security role — CEH v12, 6+ yrs VAPT (remote / hybrid)",
         source="securelayer7.net/career — 'refer them to job@securelayer7.net'",
         body=f"""Hi SecureLayer7 Team,

I'm applying for offensive security roles with SecureLayer7. Your careers page says applications can go to job@securelayer7.net, so I'm writing there.

About me — {CANDIDATE['name']}, based in {CANDIDATE['location']}. I'm in the India entity's hiring pool and am comfortable with hybrid or fully remote.

{CREDS}
- Prior: Technical Security Executive, Silent Front & Software Solutions (2018–2020)

What I'd bring
- Web, API, network and mobile VAPT; source-code review; threat modelling
- Tools: Burp Suite, Metasploit, Nessus/OpenVAS, OWASP ZAP, sqlmap, Nmap, Wireshark,
  Mimikatz, Hydra, John the Ripper, Kali Linux
- I've run the delivery side too: as Technical Security Manager at Appin Technology Lab I
  owned training delivery, mentored junior analysts, and built offensive-security
  curriculum and labs — sample build: {CANDIDATE['lab']}

To answer your process question up front: what I'd want to build at SecureLayer7 is a repeatable, well-documented offensive security practice — templated scoping, consistent evidence capture, and lab environments that let new consultants ramp fast.

{LINKS}

Happy to go through a practical assessment.

{SIG}"""),

    dict(id=21, prio="B",
         company="Payatu", to="info@payatu.com",
         city="Pune, Maharashtra", country="India", remote="India — services + Security Trainings practice",
         role="Security Consultant (VAPT) / Security Trainer",
         subject="Security Consultant + Security Trainer — CEH v12, 6+ yrs, 500+ learners trained",
         source="payatu.com / LinkedIn — 'drop an email on info@payatu.com'",
         body=f"""Dear Payatu Team,

I'm writing about security consulting and — given that Payatu runs a Security Trainings practice — training roles.

About me — {CANDIDATE['name']}, based in {CANDIDATE['location']}, remote-first.

{CREDS}
- Prior: Technical Security Executive, Silent Front & Software Solutions (2018–2020)

What I offer
- VAPT delivery across web, network, mobile and API; secure code review; IoT and product
  security testing exposure
- Training delivery: 500+ learners, corporate bootcamps, CEH/OSCP-aligned curriculum
  design, red team / blue team exercises, CTF authoring
- Lab authoring — sample build: {CANDIDATE['lab']}
- Tools: Burp Suite, Metasploit, Nessus/OpenVAS, OWASP ZAP, sqlmap, Nmap, Wireshark,
  Mimikatz, Hydra, John the Ripper, Kali Linux

I've followed Payatu's fuzzing and IoT research work, and the combination of research, services and training is exactly the mix I've built my career around.

{LINKS}

Happy to run a demo training session or complete a practical assessment.

{SIG}"""),

    dict(id=22, prio="B",
         company="New Horizons (Educate 360)", to="info@newhorizons.com",
         city="Boston, MA", country="USA", remote="Live online instructor-led",
         role="Contract Instructor — cybersecurity / IT certification",
         subject="Contract Instructor application — cybersecurity & IT certification (live online)",
         source="newhorizons.com — public contact info@newhorizons.com (Educate 360 brand)",
         body=f"""Dear New Horizons Hiring Team,

I'm applying as a contract instructor for New Horizons' live online instructor-led programs. Your site lists info@newhorizons.com as the contact, so I'm writing there directly.

About me — {CANDIDATE['name']}, based in {CANDIDATE['location']}, remote-first and available immediately for live online delivery.

{CREDS}
- Prior: Technical Security Executive, Silent Front & Software Solutions (2018–2020)

I can deliver across the information security and certification catalogue: CEH, CompTIA Security+, ethical hacking, penetration testing, VAPT, web application security (OWASP Top 10), network and cloud security, and incident response — lab-first, with Metasploit, Burp Suite, Nmap, Wireshark, Nessus, OWASP ZAP and sqlmap.

I've run 500+ learners through cohorts, built CEH/OSCP-aligned curricula, and authored hands-on labs including a browser-based red-team simulator: {CANDIDATE['lab']}

I'm on IST and can cover US, EU and APAC delivery windows.

{LINKS}

Happy to run an audition session.

{SIG}"""),

    dict(id=23, prio="C",
         company="Trojan Hunt India", to="v.tamanna@trojanhuntindia.com",
         city="India", country="India", remote="Remote",
         role="Security Consultant (VAPT)",
         subject="Security Consultant application — CEH v12, 6+ yrs VAPT, remote",
         source="Public job listing — 'submit their resume to v.tamanna@trojanhuntindia.com'",
         body=f"""Dear Trojan Hunt Team,

I'm writing to apply for the Security Consultant role. The listing asks for resumes at v.tamanna@trojanhuntindia.com, so I'm sending mine there.

About me — {CANDIDATE['name']}, based in {CANDIDATE['location']}, set up for remote work (dedicated workspace, laptop, unlimited wired-grade connectivity).

{CREDS}
- Prior: Technical Security Executive, Silent Front & Software Solutions (2018–2020)

What I deliver
- VAPT across web, network, mobile and API; vulnerability assessment and prioritisation;
  remediation guidance and retesting
- Tools: Burp Suite, Metasploit, Nessus/OpenVAS, OWASP ZAP, sqlmap, Nmap, Wireshark,
  Mimikatz, Hydra, John the Ripper, Kali Linux
- OWASP-aligned reporting that a non-technical stakeholder can actually act on
- I also build labs and run offensive-security training ({CANDIDATE['lab']}), which helps
  when clients need enablement alongside the assessment

{LINKS}

Open to full-time or contract. Available immediately.

{SIG}"""),
]


def gmail_link(to, subject, body):
    q = {"view": "cm", "fs": "1", "to": to,
         "su": subject, "body": body}
    return "https://mail.google.com/mail/?" + urllib.parse.urlencode(q)


PRIO_LABEL = {"A": "Best fit", "B": "Good fit", "C": "Worth a shot"}
PRIO_ORDER = {"A": 0, "B": 1, "C": 2}

def main():
    jobs = sorted(JOBS, key=lambda j: (PRIO_ORDER[j["prio"]], j["id"]))
    cards = []
    for j in jobs:
        link = gmail_link(j["to"], j["subject"], j["body"])
        body_html = html.escape(j["body"])
        cards.append(f"""
    <details class="card p{j['prio']}" id="job{j['id']}">
      <summary>
        <div class="sum">
          <span class="prio p{j['prio']}">{j['prio']}</span>
          <span class="co">{html.escape(j['company'])}</span>
          <span class="role">{html.escape(j['role'])}</span>
          <span class="loc">{html.escape(j['city'])}, {html.escape(j['country'])} &middot; {html.escape(j['remote'])}</span>
          <a class="btn" href="{html.escape(link)}" target="_blank" rel="noopener">Open in Gmail &rarr;</a>
        </div>
      </summary>
      <div class="detail">
        <div class="meta">
          <div><b>To:</b> <code>{html.escape(j['to'])}</code></div>
          <div><b>Subject:</b> {html.escape(j['subject'])}</div>
          <div class="src"><b>Source:</b> {html.escape(j['source'])}</div>
        </div>
        <pre class="body">{body_html}</pre>
        <div class="actions">
          <a class="btn" href="{html.escape(link)}" target="_blank" rel="noopener">Open in Gmail &rarr;</a>
          <a class="btn ghost" href="{CANDIDATE['cv']}" target="_blank" rel="noopener">Download CV (attach it)</a>
        </div>
      </div>
    </details>""")

    page = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>One-click job applications — {CANDIDATE['name']}</title>
<style>
  * {{ box-sizing: border-box; }}
  body {{ margin:0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
         background:#0f1115; color:#e6e8ee; line-height:1.5; }}
  header {{ padding:28px 20px 20px; border-bottom:1px solid #232734; background:#151823; }}
  h1 {{ margin:0 0 6px; font-size:22px; }}
  .sub {{ color:#9aa3b2; font-size:14px; }}
  .howto {{ margin:16px 20px 0; padding:14px 16px; background:#1a1f2e; border:1px solid #2a3145;
            border-radius:10px; font-size:14px; }}
  .howto ol {{ margin:8px 0 0; padding-left:20px; }}
  .howto li {{ margin:4px 0; }}
  main {{ max-width:1100px; margin:0 auto; padding:18px 16px 60px; }}
  .card {{ background:#161a24; border:1px solid #242a3a; border-radius:12px; margin:10px 0; overflow:hidden; }}
  .card[open] {{ border-color:#3a4560; }}
  summary {{ cursor:pointer; padding:14px 16px; list-style:none; }}
  summary::-webkit-details-marker {{ display:none; }}
  .sum {{ display:flex; flex-wrap:wrap; align-items:center; gap:10px; }}
  .prio {{ font-weight:700; font-size:12px; width:22px; height:22px; border-radius:6px;
           display:inline-flex; align-items:center; justify-content:center; color:#0f1115; }}
  .prio.A {{ background:#4ade80; }} .prio.B {{ background:#60a5fa; }} .prio.C {{ background:#fbbf24; }}
  .co {{ font-weight:650; }}
  .role {{ color:#c3cadb; font-size:14px; }}
  .loc {{ color:#8b95a8; font-size:13px; margin-left:auto; }}
  .btn {{ display:inline-block; padding:7px 13px; border-radius:8px; background:#3b82f6; color:#fff;
          text-decoration:none; font-size:13px; font-weight:600; white-space:nowrap; }}
  .btn:hover {{ background:#2563eb; }}
  .btn.ghost {{ background:transparent; border:1px solid #3a4560; color:#c3cadb; }}
  .btn.ghost:hover {{ background:#1e2432; }}
  .detail {{ padding:0 16px 16px; border-top:1px solid #242a3a; }}
  .meta {{ padding:12px 0; font-size:13px; color:#a8b1c2; }}
  .meta code {{ background:#0f131c; padding:2px 6px; border-radius:5px; color:#7dd3fc; }}
  .src {{ color:#7c8698; font-size:12px; margin-top:4px; }}
  pre.body {{ background:#0f131c; border:1px solid #242a3a; border-radius:8px; padding:14px;
              overflow-x:auto; white-space:pre-wrap; word-wrap:break-word; font-size:12.5px;
              color:#d6dbe6; font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
              max-height:420px; overflow-y:auto; }}
  .actions {{ display:flex; gap:10px; flex-wrap:wrap; margin-top:12px; }}
  @media (max-width:640px) {{ .loc {{ margin-left:0; width:100%; }} .btn {{ width:100%; text-align:center; }} }}
</style>
</head>
<body>
<header>
  <h1>One-click job applications — {CANDIDATE['name']}</h1>
  <div class="sub">{html.escape(CANDIDATE['location'])} &middot; {CANDIDATE['email']} &middot; {CANDIDATE['phone']}
    &middot; <a style="color:#7dd3fc" href="{CANDIDATE['cv']}" target="_blank" rel="noopener">CV</a></div>
</header>
<div class="howto">
  <b>How to use this page (works on laptop or phone):</b>
  <ol>
    <li>Click <b>Open in Gmail</b> — it opens a Gmail compose window with the recipient, subject and body already filled in.</li>
    <li>Click <b>Download CV</b>, then attach <code>Ratan_Kumar_Patel_CV.pdf</code> to the message. (The CV link is already in the email body too, so it works even if you skip this.)</li>
    <li>Hit send. Then tick it off below.</li>
  </ol>
  <div style="margin-top:10px;color:#9aa3b2">Priority: <b style="color:#4ade80">A</b> = best fit ·
  <b style="color:#60a5fa">B</b> = good fit · <b style="color:#fbbf24">C</b> = worth a shot. {len(jobs)} applications total.</div>
</div>
<main>
{''.join(cards)}
</main>
</body>
</html>"""
    out = "/home/user/Ratan-patel.github.io/job-applications/send.html"
    with open(out, "w", encoding="utf-8") as f:
        f.write(page)
    with open("/home/user/Ratan-patel.github.io/job-applications/jobs.json", "w", encoding="utf-8") as f:
        json.dump([{k: v for k, v in j.items()} for j in jobs], f, indent=2, ensure_ascii=False)
    print(f"wrote {out} with {len(jobs)} jobs")


if __name__ == "__main__":
    main()
