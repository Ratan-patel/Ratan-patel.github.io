#!/usr/bin/env python3
"""
Builds an ATS-friendly, text-selectable CV PDF for Ratan Kumar Patel.

Source of truth: content published on https://ratan-patel.github.io/
Run:  python3 job-search/build_cv.py
Out:  job-search/Ratan_Kumar_Patel_CV_2026.pdf
"""
import os

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (BaseDocTemplate, Frame, HRFlowable, ListFlowable,
                                ListItem, PageTemplate, Paragraph, Spacer, Table,
                                TableStyle)

NAVY = colors.HexColor("#0D2137")
GOLD = colors.HexColor("#B8860B")
INK = colors.HexColor("#1A1A2E")
MUTED = colors.HexColor("#4A5568")

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                   "Ratan_Kumar_Patel_CV_2026.pdf")

PAGE_W, PAGE_H = A4
M = 15 * mm

ss = getSampleStyleSheet()


def st(name, **kw):
    base = dict(fontName="Helvetica", fontSize=9.2, leading=12.1, textColor=INK,
                alignment=TA_LEFT, spaceBefore=0, spaceAfter=0)
    base.update(kw)
    return ParagraphStyle(name, **base)


NAME = st("name", fontName="Helvetica-Bold", fontSize=23, leading=25, textColor=NAVY,
          spaceAfter=2)
ROLE = st("role", fontName="Helvetica-Bold", fontSize=10.4, leading=13, textColor=GOLD,
          spaceAfter=4)
CONTACT = st("contact", fontSize=8.9, leading=11.6, textColor=MUTED)
SECTION = st("section", fontName="Helvetica-Bold", fontSize=10.2, leading=12,
             textColor=NAVY, spaceBefore=7, spaceAfter=1)
BODY = st("body", fontSize=9.0, leading=11.8)
JOB = st("job", fontName="Helvetica-Bold", fontSize=9.7, leading=11.8, textColor=NAVY)
JOB_META = st("jobmeta", fontName="Helvetica-Oblique", fontSize=8.9, leading=11.4,
              textColor=MUTED, spaceAfter=1)
BULLET = st("bullet", fontSize=8.95, leading=11.6, leftIndent=9, bulletIndent=1,
            spaceAfter=1)
SMALL = st("small", fontSize=8.6, leading=11.0, textColor=MUTED)


def section(title):
    return [Paragraph(title.upper(), SECTION),
            HRFlowable(width="100%", thickness=0.9, color=GOLD,
                       spaceBefore=1, spaceAfter=4)]


def bullets(items):
    return ListFlowable(
        [ListItem(Paragraph(i, BULLET), leftIndent=9, value="circle") for i in items],
        bulletType="bullet", start="circle", bulletFontSize=5.2,
        bulletColor=GOLD, leftIndent=9, spaceBefore=0, spaceAfter=2)


def two_col(rows, widths=(0.5, 0.5)):
    left, right = [], []
    for l, r in rows:
        left.append(Paragraph("&bull; " + l, BULLET))
        right.append(Paragraph("&bull; " + r, BULLET))
    data = [[left, right]]
    t = Table(data, colWidths=[PAGE_W * widths[0] - M - 6, PAGE_W * widths[1] - M - 6])
    t.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ]))
    return t


def footer(canvas, doc):
    canvas.saveState()
    canvas.setStrokeColor(colors.HexColor("#D8DEE9"))
    canvas.setLineWidth(0.6)
    canvas.line(M, 12 * mm, PAGE_W - M, 12 * mm)
    canvas.setFont("Helvetica", 7.6)
    canvas.setFillColor(MUTED)
    canvas.drawString(M, 8 * mm,
                      "Ratan Kumar Patel  ·  +91 87009 13645  ·  patelratan460@gmail.com  ·  ratan-patel.github.io")
    canvas.drawRightString(PAGE_W - M, 8 * mm, "Page %d" % doc.page)
    canvas.restoreState()


story = []

# ---------------- HEADER ----------------
story.append(Paragraph("RATAN KUMAR PATEL", NAME))
story.append(Paragraph("Cyber Security Trainer &amp; Offensive Security Practitioner &nbsp;|&nbsp; CEH v12", ROLE))
story.append(Paragraph(
    "South Extension, New Delhi, India &nbsp;·&nbsp; +91 87009 13645 &nbsp;·&nbsp; patelratan460@gmail.com<br/>"
    "ratan-patel.github.io &nbsp;·&nbsp; linkedin.com/in/ratan-kumar-patel-032a43367 &nbsp;·&nbsp; github.com/Ratan-patel",
    CONTACT))
story.append(HRFlowable(width="100%", thickness=1.4, color=NAVY, spaceBefore=6, spaceAfter=2))

# ---------------- SUMMARY ----------------
story += section("Professional Summary")
story.append(Paragraph(
    "CEH v12 certified security practitioner and corporate trainer with <b>6+ years</b> of hands-on "
    "experience across VAPT, red-team simulation, network/web application security and AI/LLM red teaming. "
    "Have trained <b>500+ students and working professionals</b> in ethical hacking through lab-first "
    "curriculum design, CTF challenges and real-world attack simulations. Build and ship security tooling "
    "independently — including <b>RatanSec OS</b>, an AI-driven penetration testing environment. "
    "Available immediately for roles in Delhi NCR; equally effective in classroom, corporate and remote delivery.",
    BODY))

# ---------------- CORE SKILLS ----------------
story += section("Core Competencies")
story.append(two_col([
    ("Ethical Hacking &amp; Penetration Testing", "OWASP Top 10 / Web &amp; API Security"),
    ("Vulnerability Assessment (VAPT)", "Network &amp; Firewall Security"),
    ("Red Team &amp; Adversary Simulation", "Incident Response &amp; Threat Intelligence"),
    ("Corporate Training &amp; Curriculum Design", "CTF Design &amp; Lab Engineering"),
    ("AI / LLM Security &amp; Red Teaming", "Bug Bounty Mentoring"),
]))
story.append(Spacer(1, 3))
story.append(Paragraph(
    "<b>Tools:</b> Metasploit · Burp Suite · Nmap · Wireshark · SQLMap · Hydra · John the Ripper · "
    "Nessus · OpenVAS · OWASP ZAP · Mimikatz · Aircrack-ng · Nikto · Nuclei · Gobuster · ffuf<br/>"
    "<b>Platforms:</b> Kali Linux · Parrot OS · Windows Server · Docker · Python · Bash · Git",
    BODY))

# ---------------- EXPERIENCE ----------------
story += section("Professional Experience")
story.append(Paragraph("Ethical Hacking Trainer &amp; Technical Security Manager", JOB))
story.append(Paragraph("Appin Technology Lab &nbsp;|&nbsp; New Delhi &nbsp;|&nbsp; 2020 – 2026", JOB_META))
story.append(bullets([
    "Trained <b>500+ students</b> in ethical hacking, penetration testing, network security and VAPT; "
    "consistently rated among the top trainers for practical, lab-first delivery.",
    "Designed complete course modules covering OWASP Top 10, Metasploit, Burp Suite, Kali Linux, Nmap and Nessus.",
    "Delivered corporate ethical hacking workshops and bootcamps for enterprise cohorts.",
    "Led red team / blue team exercises and designed CTF challenges used across batches.",
    "Mentored learners in bug bounty hunting, exploit development and real-world penetration testing.",
]))

story.append(Spacer(1, 3))
story.append(Paragraph("Technical Security Executive", JOB))
story.append(Paragraph("Silent Front &amp; Software Solutions &nbsp;|&nbsp; New Delhi &nbsp;|&nbsp; 2018 – 2020", JOB_META))
story.append(bullets([
    "Conducted VAPT and ethical hacking assessments on client networks and web applications.",
    "Monitored network security posture and implemented mitigation strategies for identified gaps.",
    "Prepared client-facing security reports, remediation guidance and training documentation for junior analysts.",
]))

# ---------------- PROJECTS ----------------
story += section("Selected Projects")
story.append(Paragraph("RatanSec OS — AI-Driven Penetration Testing Environment", JOB))
story.append(Paragraph("Self-engineered · Kali toolchain + AI copilot · ratan-patel.github.io/ratansec-os.html", JOB_META))
story.append(bullets([
    "Bundles the Kali security toolchain (nmap, nikto, whatweb, gobuster, ffuf, nuclei, sqlmap, hydra, whois, dig) "
    "with an OpenRouter-powered AI copilot that runs tools via function calling, analyses output and drafts reports.",
    "Includes web dashboard, CLI, REST API, human-in-the-loop approvals for intrusive actions, target scope "
    "allowlist and a full audit log; distributed as free VM images (qcow2/raw), Docker image and one-command VPS installer.",
]))
story.append(Spacer(1, 2))
story.append(Paragraph("Red-Team Lab Simulator", JOB))
story.append(Paragraph("Browser-based hacking environment · ratan-patel.github.io/lab.html", JOB_META))
story.append(bullets([
    "Interactive browser lab with missions, simulated nmap/nikto/sqlmap/hydra/mimikatz tooling and a live terminal, "
    "used as a zero-setup teaching aid for beginners.",
]))

# ---------------- CERTS ----------------
story += section("Certifications &amp; Education")
story.append(Paragraph(
    "<b>Certified Ethical Hacker (CEH v12)</b> — EC-Council, 2024 (Credential ECC92840, valid Jul 2024 – Jul 2027)<br/>"
    "<b>MS, Cybersecurity &amp; Information Assurance</b> — Western Governors University, 2023<br/>"
    "<b>PG Diploma, Computer Application</b> — Board of Technical Education, U.P. Lucknow, 2013 (First Division)",
    BODY))

# ---------------- EXTRA ----------------
story += section("Additional Information")
story.append(Paragraph(
    "<b>Languages:</b> Hindi, English &nbsp;·&nbsp; <b>Location:</b> New Delhi (Delhi NCR) &nbsp;·&nbsp; "
    "<b>Availability:</b> Immediate joiner &nbsp;·&nbsp; <b>Work preference:</b> On-site Delhi NCR, hybrid or remote<br/>"
    "<b>Also available for:</b> corporate workshops, VAPT engagements, CTF design, AI/LLM security assessments",
    SMALL))

doc = BaseDocTemplate(OUT, pagesize=A4,
                      leftMargin=M, rightMargin=M, topMargin=11 * mm, bottomMargin=14 * mm,
                      title="Ratan Kumar Patel — Cyber Security Trainer & Offensive Security Practitioner",
                      author="Ratan Kumar Patel",
                      subject="Curriculum Vitae",
                      keywords="CEH, ethical hacking, VAPT, penetration testing, cyber security trainer, red team, Delhi NCR")
frame = Frame(M, 14 * mm, PAGE_W - 2 * M, PAGE_H - 11 * mm - 14 * mm, id="body",
              leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)
doc.addPageTemplates([PageTemplate(id="main", frames=[frame], onPage=footer)])
doc.build(story)
print("wrote", OUT)
