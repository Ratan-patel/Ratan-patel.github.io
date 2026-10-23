#!/usr/bin/env python3
"""
Single source of truth for the Delhi-NCR outreach campaign.

Every company below is a Delhi NCR (or NCR-servable) employer of cyber security
trainers / VAPT practitioners. Contact addresses are the ones these companies
publish for hiring, HR or general enquiries.

Usage:
    python3 job-search/build_outreach.py

Outputs:
    job-search/applications-email.md   -> ready-to-send mail digest (25 mails)
    job-search/applications.csv        -> tracker import
    and patches portfolio.html table between the APPLICATIONS markers.
"""

import csv
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

CANDIDATE = {
    "name": "Ratan Kumar Patel",
    "phone": "+91 87009 13645",
    "email": "patelratan460@gmail.com",
    "linkedin": "linkedin.com/in/ratan-kumar-patel-032a43367",
    "site": "ratan-patel.github.io",
    "cv": "Ratan_Kumar_Patel_CV_2026.pdf",
}

# ---------------------------------------------------------------------------
# 25 targets. hook = one accurate, company-specific sentence (no flattery filler)
# kind: "trainer" (institute / academy) or "vapt" (security consultancy / product)
# ---------------------------------------------------------------------------
COMPANIES = [
    dict(
        name="Ducat India",
        city="Noida / Greater Noida",
        kind="trainer",
        role="Cyber Security Trainer",
        email="hr@ducatindia.com",
        alt="info@ducatindia.com",
        hook="your open Cyber Security Trainer role (Delhi NCR, 3+ years, CEH/Security+/CHFI preferred) matches my CEH v12 profile and six years of classroom delivery.",
        source="Indeed job post + ducatindia.com contact page",
    ),
    dict(
        name="Craw Cyber Security (Craw Security)",
        city="Saket & Laxmi Nagar, Delhi",
        kind="trainer",
        role="Cyber Security Trainer / Security Analyst",
        email="hr@craw.in",
        alt="info@craw.in; training@craw.in",
        hook="you run CEH, OSCP and VAPT trainer batches out of Saket and Laxmi Nagar, and I have built and delivered exactly those modules — OWASP Top 10, Metasploit, Burp Suite, Nmap, Nessus — for 500+ learners.",
        source="crawsecurity.com/contact + LinkedIn hiring posts (hr@craw.in)",
    ),
    dict(
        name="InfosecTrain (Infosec Train)",
        city="Pitampura, Delhi / Noida",
        kind="trainer",
        role="Cyber Security Trainer / SME",
        email="ops@infosectrain.com",
        alt="hr@infosectrain.com; hire@infosectrain.com",
        hook="your trainers-and-SME onboarding route (ops@infosectrain.com) is exactly where my profile fits: CEH v12, VAPT delivery, and lab/CTF design for certification tracks.",
        source="infosectrain.com/contact-us (Trainers & SMEs) + /career",
    ),
    dict(
        name="Kratikal Tech",
        city="Sector 68, Noida",
        kind="vapt",
        role="Security Testing / VAPT Consultant",
        email="resumes@kratikal.zohorecruitmail.com",
        alt="hr@kratikal.com",
        hook="your Manager – Security Testing and VAPT consultant openings in Noida call for someone who still executes the hard engagements — that is the work I have done since 2018, plus I can train your client teams.",
        source="kratikal.com/career (resume inbox) + kratikal.com/contact-us",
    ),
    dict(
        name="Securium Solutions / Securium Academy",
        city="Sector 1, Noida",
        kind="trainer",
        role="Cyber Security Trainer (₹40k–₹60k listed)",
        email="hr@securiumsolutions.com",
        alt="info@securiumsolutions.com",
        hook="Securium Academy's Noida trainer role asks for exactly my mix — CEH, hands-on VAPT and CTF-driven labs — and I can also support your CERT-In empanelled assessment practice.",
        source="simplyhired / securiumacademy.com/career (hr@securiumsolutions.com)",
    ),
    dict(
        name="Prakhar AI Institute",
        city="Kalkaji, Delhi (hybrid)",
        kind="trainer",
        role="Cyber Security & Ethical Hacking Trainer",
        email="info@prakharaiinstitute.com",
        alt="prakharaiinstitute@gmail.com; +91 98117 77644",
        hook="your Cyber Security & Ethical Hacking trainer vacancy (₹30k–₹1L, hybrid, Kalkaji) is still open, and my 500+ trained learners and ready-to-run lab content can start immediately.",
        source="Indeed job post + prakharaiinstitute.com/contact",
    ),
    dict(
        name="GICSEH (Global Institute of Cyber Security & Ethical Hacking)",
        city="Sector 62 Noida / Preet Vihar Delhi",
        kind="trainer",
        role="Corporate Trainer — Cyber Security",
        email="info@gicseh.com",
        alt="support@gicseh.com",
        hook="GICSEH's career page lists Corporate Trainer openings in the subjects you teach, and my CEH + VAPT background maps directly onto your diploma and EC-Council tracks.",
        source="gicseh.com/career.php",
    ),
    dict(
        name="CETPA Infotech",
        city="Sector 2, Noida",
        kind="trainer",
        role="Cyber Security / Ethical Hacking Trainer",
        email="career@cetpainfotech.com",
        alt="query@cetpainfotech.com",
        hook="CETPA recruits trainers through career@cetpainfotech.com, and I can take both your ethical hacking and corporate security workshops without a ramp-up period.",
        source="cetpainfotech.com/career",
    ),
    dict(
        name="Sveltetech Technologies",
        city="Gurugram",
        kind="vapt",
        role="VAPT Analyst / Security Consultant",
        email="careers@sveltetech.com",
        alt="",
        hook="your VAPT hiring post (Gurugram, 1–7 years, manual testing over scanner output) is exactly the kind of work I do, and I can also front your client training sessions.",
        source="Job post dated Oct 2026 — apply address listed in the ad",
    ),
    dict(
        name="CyberSRC Consultancy",
        city="Noida",
        kind="vapt",
        role="Associate Security Analyst (VAPT)",
        email="pooja@cybersrcc.com",
        alt="contact via cybersrc.com careers form",
        hook="your Associate Security Analyst (VAPT) opening in Noida spans web, mobile, network and cloud testing — that breadth matches my 2018–2026 assessment work.",
        source="Job post (Noida, 1–8 yrs) — recruiter address listed in the ad",
    ),
    dict(
        name="eSec Forte Technologies",
        city="Noida / Gurugram",
        kind="vapt",
        role="Information Security Consultant (VAPT / AppSec / Red Teaming)",
        email="joinus@esecforte.com",
        alt="contact@esecforte.com; parul.ralhan@esecforte.com",
        hook="your Noida openings for VAPT, AppSec and Red Teaming consultants (₹4–9L) are a direct match for my offensive-security and reporting experience.",
        source="esecforte.com/careers (joinus@esecforte.com)",
    ),
    dict(
        name="Certcube Labs",
        city="Pitampura, Delhi",
        kind="vapt",
        role="Security Consultant / Trainer (CERT-In empanelled practice)",
        email="consulting@certcube.com",
        alt="consult@certcube.com",
        hook="Certcube's hiring runs through consulting@certcube.com for VAPT, audits and training delivery, and I bring both the assessment and the classroom side of that work.",
        source="jobs.certcube.com + LinkedIn hiring posts",
    ),
    dict(
        name="Aujas Cybersecurity",
        city="Gurugram",
        kind="vapt",
        role="Consultant / Senior Consultant — Security Verification",
        email="careers@aujas.com",
        alt="HRopsteam@aujas.com",
        hook="Aujas's Security Verification and Risk Advisory roles in Gurugram need practitioners who can test and then explain findings to a client — my VAPT and training record covers both halves.",
        source="aujas.com/join-us + aujas.com consultant page",
    ),
    dict(
        name="Innefu Labs",
        city="Netaji Subhash Place, Delhi",
        kind="vapt",
        role="Cyber Security / Security Engineering roles",
        email="jobs@innefu.com",
        alt="hr@innefu.com; info@innefu.com",
        hook="Innefu's careers page routes every application to jobs@innefu.com, and my VAPT plus AI/LLM red-teaming background suits your cyber and forensics product lines.",
        source="innefu.com/careers",
    ),
    dict(
        name="Torrid Networks",
        city="Sector 63, Noida",
        kind="vapt",
        role="Penetration Tester / VAPT Consultant",
        email="careers@torridnetworks.com",
        alt="apac@torridnetworks.com",
        hook="Torrid's careers page asks for CVs at careers@torridnetworks.com for exactly the VAPT and security-consulting work I have delivered since 2018.",
        source="torridnetworks.com/careers",
    ),
    dict(
        name="TAC Security",
        city="Aerocity, New Delhi",
        kind="vapt",
        role="Security Consultant / Red Team",
        email="info@tacsecurity.com",
        alt="mail@tacsecurity.com (also apply on tacsecurity.com/careers)",
        hook="TAC's vulnerability-management and red-team practice in Aerocity needs consultants who can go from nmap/Burp findings to an executive-ready report — that is my core loop.",
        source="tacsecurity.com/contact-us + career page",
    ),
    dict(
        name="Netrika Consulting",
        city="Saidulajab, New Delhi / Gurugram",
        kind="vapt",
        role="Information Security Consultant / Trainer",
        email="info@netrika.com",
        alt="trust@netrika.com; suruchi.gaur@netrika.com",
        hook="Netrika runs both security consulting and a training & certifications vertical, so a consultant who can also stand up and teach a room is directly useful to you.",
        source="netrika.com/work-with-us + /contact-us",
    ),
    dict(
        name="NIIT Limited",
        city="Gurugram / Delhi NCR centres",
        kind="trainer",
        role="Cyber Security Faculty / Corporate Trainer",
        email="info@niit.com",
        alt="corptraining@niit.com; careercourses@niit.com",
        hook="NIIT's career-course and corporate training arms both deliver security programmes across NCR, and I can take CEH-aligned and ethical-hacking batches from week one.",
        source="niit.com/india contact information",
    ),
    dict(
        name="Jetking Infotrain",
        city="Laxmi Nagar, Delhi (multiple NCR centres)",
        kind="trainer",
        role="Technical Faculty — Cyber Security",
        email="info@jetking.com",
        alt="delro@jetking.com",
        hook="Jetking's career page invites faculty CVs at info@jetking.com for Delhi among other cities; my CEH v12 and lab-first teaching style fit your hardware-and-security tracks.",
        source="jetking.com/career (Technical Faculty, Delhi listed)",
    ),
    dict(
        name="NIIT Foundation",
        city="Najafgarh, Delhi",
        kind="trainer",
        role="Cyber Security Trainer (₹25k–₹30k listed)",
        email="hr@niitfoundation.org",
        alt="contact@niitfoundation.org",
        hook="your Najafgarh Cyber Security Trainer role asks for someone who can teach firewalls, IDS, penetration testing and VAPT hands-on — that is exactly my delivery style.",
        source="SimplyHired listing (Najafgarh) + niitfoundation.org/contact-us (hr@)",
    ),
    dict(
        name="Recon Cyber Security",
        city="Laxmi Nagar / Burari / Janakpuri, Delhi",
        kind="trainer",
        role="Cyber Security Trainer",
        email="training@reconcybersecurity.com",
        alt="info@reconcybersecurity.com",
        hook="Recon's trainer bench covers ethical hacking, forensics and Python across three Delhi centres, and I can add CEH-track depth plus ready CTF labs.",
        source="reconcybersecurity.com/contact-us-recon-cyber-security",
    ),
    dict(
        name="Amity University",
        city="Sector 125, Noida",
        kind="trainer",
        role="Faculty / Visiting Faculty — Cyber Security",
        email="careers@amity.edu",
        alt="faculty@amity.edu; hrd@amity.edu",
        hook="Amity's Noida campus recruits cyber security faculty and industry practitioners, and I can bring a CEH-certified, lab-based syllabus alongside your existing CSE tracks.",
        source="amity.edu/careers + faculty recruitment pages",
    ),
    dict(
        name="Bennett University",
        city="TechZone II, Greater Noida",
        kind="trainer",
        role="Assistant Professor / Professor of Practice — Cyber Security",
        email="career@bennett.edu.in",
        alt="recruitment.cse@bennett.edu.in",
        hook="Bennett's School of Computer Science Engineering and Technology is recruiting for 2026-27, and a Professor-of-Practice profile built on live VAPT and training delivery fits that brief.",
        source="bennett.edu.in/career",
    ),
    dict(
        name="Sharda University",
        city="Knowledge Park III, Greater Noida",
        kind="trainer",
        role="Faculty / Industry Trainer — Cyber Security",
        email="hr@sharda.ac.in",
        alt="recruitment@sharda.ac.in",
        hook="Sharda's current faculty drive (CSE/CSA) accepts profiles through hr@sharda.ac.in, and my industry-side security experience can support both teaching and placement-linked training.",
        source="sharda.ac.in/current-openings",
    ),
    dict(
        name="Manav Rachna University",
        city="Faridabad (Delhi NCR)",
        kind="trainer",
        role="Faculty / Industry Trainer — Cyber Security",
        email="careers.mrei@mrei.ac.in",
        alt="info@mru.edu.in",
        hook="Manav Rachna runs security electives inside its CSE programmes, and a practicing CEH trainer can deliver those as lab-based, industry-aligned modules.",
        source="mru.edu.in / manavrachna.edu.in contact pages",
    ),
    dict(
        name="Galgotias University",
        city="Greater Noida",
        kind="trainer",
        role="Industry Faculty / Trainer — Cyber Security",
        email="recruitments.trainer@galgotiasuniversity.edu.in",
        alt="hr@galgotiasuniversity.edu.in; recruitments@galgotiasuniversity.edu.in",
        hook="your careers page invites trainer and industry-faculty profiles, and I can deliver CSE cyber security electives as lab-based modules with a ready CTF platform from day one.",
        source="galgotiasuniversity.edu.in/p/current-openings",
    ),
    dict(
        name="IIMT Group of Colleges",
        city="Knowledge Park III, Greater Noida",
        kind="trainer",
        role="Faculty / Technical Trainer — Cyber Security",
        email="hr_gn@iimtindia.net",
        alt="contact_gn@iimtindia.net",
        hook="IIMT's Knowledge Park campus recruits technical trainers for CSE and IT streams, and I can take ethical hacking and VAPT subjects with practical labs rather than theory-only delivery.",
        source="iimtindia.net/contact-us + faculty recruitment notices",
    ),
    dict(
        name="GNIOT Group of Institutions",
        city="Knowledge Park II, Greater Noida",
        kind="trainer",
        role="Assistant Professor / Technical Trainer — Cyber Security",
        email="recruitment@gniot.net.in",
        alt="gniot@gniot.net.in",
        hook="your department list includes Cyber Security among the CSE specialisations and you also recruit technical trainers, so a practising CEH trainer who can run hands-on labs fits both tracks.",
        source="faculty recruitment notices (recruitment@gniot.net.in)",
    ),
    dict(
        name="Noida International University",
        city="Sector 17A, Greater Noida",
        kind="trainer",
        role="Assistant Professor / Industry Faculty — Cyber Security",
        email="careers@niu.edu.in",
        alt="registrar.office@niu.edu.in",
        hook="your 2026 recruitment cycle invites faculty applications at careers@niu.edu.in, and a practitioner who can run hands-on security labs would complement the CSE teaching team.",
        source="niu.edu.in/careers + 2026 recruitment notices",
    ),
    dict(
        name="Cyberyaan",
        city="Tilak Nagar, New Delhi",
        kind="trainer",
        role="Cyber Security / Ethical Hacking Trainer",
        email="training@cyberyaan.com",
        alt="pankaj@cyberyaan.com",
        hook="your Delhi batches cover ethical hacking, Linux and cyber security diploma tracks in both Hindi and English, which is exactly how I have taught for six years, and I can add CEH-depth plus ready CTF labs.",
        source="cyberyaan.com/contact-us",
    ),
    dict(
        name="Cryptus Cyber Security",
        city="Shakarpur, Delhi + NCR branches",
        kind="trainer",
        role="Cyber Security / CEH Trainer",
        email="info@cryptus.in",
        alt="",
        hook="Cryptus runs CEH and ethical hacking batches across Delhi, Noida, Greater Noida and Faridabad, and I can take those tracks in Hindi or English with hands-on labs and CTF exercises.",
        source="cryptus.in/contact-us",
    ),
]

# ---------------------------------------------------------------------------
# Application status
#   SENT_TODAY  -> emails sent on 2026-10-23 in this campaign
#   EARLIER     -> already applied before this campaign (Sep-Oct 2026), so no duplicate mail
# ---------------------------------------------------------------------------
SENT_TODAY = {
    "career@cetpainfotech.com", "consulting@certcube.com", "info@tacsecurity.com",
    "info@niit.com", "careers@sveltetech.com", "jobs@innefu.com",
    "careers@torridnetworks.com", "careers@amity.edu", "career@bennett.edu.in",
    "hr@sharda.ac.in", "careers.mrei@mrei.ac.in", "training@reconcybersecurity.com",
    "info@jetking.com", "pooja@cybersrcc.com",
    "recruitments.trainer@galgotiasuniversity.edu.in", "hr_gn@iimtindia.net",
    "recruitment@gniot.net.in", "careers@niu.edu.in", "training@cyberyaan.com",
    "info@cryptus.in",
}
EARLIER = {
    "hr@ducatindia.com", "hr@craw.in", "ops@infosectrain.com",
    "resumes@kratikal.zohorecruitmail.com", "hr@securiumsolutions.com",
    "info@prakharaiinstitute.com", "info@gicseh.com", "hr@niitfoundation.org",
    "joinus@esecforte.com", "careers@aujas.com", "info@netrika.com",
}


def status_of(email):
    if email in SENT_TODAY:
        return "Sent (23 Oct)"
    if email in EARLIER:
        return "Applied earlier"
    return "Ready to send"


SUBJECT = "Application: {role} — Ratan Kumar Patel, CEH v12 | 6+ yrs | 500+ trained | Delhi NCR | Immediate joiner"

BODY = """Respected HR Team,

I am applying for the {role} role at {name} ({city}).

Quick profile: CEH v12 certified (EC-Council, valid to Jul 2027), MS in Cybersecurity & Information Assurance (WGU, 2023), 6+ years across VAPT, red-team simulation, web/API and network security, and corporate ethical hacking training. I have trained 500+ students and working professionals at Appin Technology Lab (2020-2026) and delivered VAPT engagements at Silent Front & Software Solutions (2018-2020). I also built RatanSec OS, an AI-driven pentest environment (Kali toolchain + AI copilot, scope allowlist, audit log), which is public at ratan-patel.github.io/ratansec-os.html.

Why I am writing to {name} specifically: {hook}

I am based in South Extension, New Delhi, available immediately, and open to on-site Delhi NCR, hybrid or remote. My CV is attached (one page, text-based, ATS-friendly).

Request: if the role is currently closed, I would be grateful if you could keep my profile on file or forward it to the relevant hiring manager. A 10-minute call at your convenience is enough for me to show how I would handle the first 30 days.

Thank you for your time.

Regards,
Ratan Kumar Patel
{phone} | {email}
{linkedin} | {site}
"""


def build_rows():
    return COMPANIES


def mail_digest():
    out = []
    out.append("# Delhi NCR — Cyber Security Applications (25 mails)\n")
    out.append("From: **%s** · CV: `job-search/%s` (attach this file)\n" % (CANDIDATE["email"], CANDIDATE["cv"]))
    out.append("Send in batches of 8–10, morning 10:00–11:30 IST (Tue–Thu perform best). "
               "Do **not** CC or BCC across companies — one mail per company.\n")
    out.append("\n## Address book\n")
    out.append("| # | Company | Location | Role | To | Also try |\n|---|---|---|---|---|---|\n")
    for i, c in enumerate(COMPANIES, 1):
        out.append("| %d | %s | %s | %s | `%s` | %s |\n" % (
            i, c["name"], c["city"], c["role"], c["email"], c["alt"] or "—"))
    out.append("\n---\n")
    for i, c in enumerate(COMPANIES, 1):
        out.append("\n## %d. %s\n" % (i, c["name"]))
        out.append("**To:** %s  \n" % c["email"])
        if c["alt"]:
            out.append("**Also try (second mail from a different day):** %s  \n" % c["alt"])
        out.append("**Subject:** %s  \n" % SUBJECT.format(role=c["role"], name=c["name"]))
        out.append("**Where this contact came from:** %s  \n" % c["source"])
        out.append("\n```text\n")
        out.append(BODY.format(role=c["role"], name=c["name"], city=c["city"], hook=c["hook"],
                               phone=CANDIDATE["phone"], email=CANDIDATE["email"],
                               linkedin=CANDIDATE["linkedin"], site=CANDIDATE["site"]))
        out.append("```\n")
    return "".join(out)


def write_csv():
    path = os.path.join(HERE, "applications.csv")
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["#", "Company", "Location", "Role", "Email", "Alternate email",
                    "Source", "Status", "Sent on", "Follow-up on"])
        for i, c in enumerate(COMPANIES, 1):
            st = status_of(c["email"])
            w.writerow([i, c["name"], c["city"], c["role"], c["email"], c["alt"],
                        c["source"], st,
                        "2026-10-23" if st.startswith("Sent") else "",
                        "2026-10-29" if st.startswith("Sent") else ""])
    return path


def write_portfolio_table():
    """Replace the block between the APPLICATIONS markers inside portfolio.html."""
    path = os.path.join(ROOT, "portfolio.html")
    if not os.path.exists(path):
        return None
    html = open(path, encoding="utf-8").read()
    rows = []
    for i, c in enumerate(COMPANIES, 1):
        rows.append(
            '<tr>'
            '<td class="num">{i}</td>'
            '<td><span class="co">{name}</span><span class="co-city">{city}</span></td>'
            '<td>{role}</td>'
            '<td><a href="mailto:{email}?subject={subj}">{email}</a>'
            '{alt_html}</td>'
            '<td><span class="status{sent_cls}">{status}</span></td>'
            '</tr>'.format(
                i=i, name=c["name"], city=c["city"], role=c["role"], email=c["email"],
                subj=SUBJECT.format(role=c["role"], name=c["name"]).replace(" ", "%20").replace("|", "%7C"),
                alt_html=('<span class="alt">%s</span>' % c["alt"]) if c["alt"] else "",
                sent_cls=" sent" if status_of(c["email"]).startswith("Sent") else "",
                status=status_of(c["email"]),
            )
        )
    block = "\n".join(rows)
    html = re.sub(r"<!-- APPLICATIONS:START -->.*?<!-- APPLICATIONS:END -->",
                  "<!-- APPLICATIONS:START -->\n" + block + "\n<!-- APPLICATIONS:END -->",
                  html, flags=re.S)
    html = re.sub(r"<!-- COUNT:START -->.*?<!-- COUNT:END -->",
                  "<!-- COUNT:START -->%d<!-- COUNT:END -->" % len(COMPANIES), html, flags=re.S)
    open(path, "w", encoding="utf-8").write(html)
    return path


if __name__ == "__main__":
    md = os.path.join(HERE, "applications-email.md")
    with open(md, "w", encoding="utf-8") as f:
        f.write(mail_digest())
    print("wrote", md)
    print("wrote", write_csv())
    p = write_portfolio_table()
    print("patched", p if p else "(portfolio.html not found)")
    print("companies:", len(COMPANIES))
