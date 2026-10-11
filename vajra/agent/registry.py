# -*- coding: utf-8 -*-
"""
VAJRA Tool Registry
Har ethical-hacking phase ke liye tools, unke examples aur availability check.
"""

import os
import shutil

CATEGORIES = [
    {"id": "recon",    "name": "Recon & OSINT",          "emoji": "🔍", "desc": "Target ke baare mein public info jama karna"},
    {"id": "scan",     "name": "Scanning & Enumeration", "emoji": "📡", "desc": "Ports, services, directories, hosts dhoondhna"},
    {"id": "vuln",     "name": "Vulnerability Analysis", "emoji": "🛡️", "desc": "Kamzoriyan (vulnerabilities) aur misconfigurations dhoondhna"},
    {"id": "exploit",  "name": "Gaining Access",         "emoji": "⚡", "desc": "Exploitation & initial access — sirf authorized targets par"},
    {"id": "passwd",   "name": "Password Attacks",       "emoji": "🔑", "desc": "Hash cracking, wordlists, brute-force"},
    {"id": "wireless", "name": "Wireless Testing",       "emoji": "📶", "desc": "WiFi security auditing (root + monitor mode chahiye)"},
    {"id": "post",     "name": "Post-Exploitation",      "emoji": "🧲", "desc": "Privesc + post-exploit enum (maintaining access msf modules se)"},
    {"id": "phone",    "name": "Phone Controls",         "emoji": "📱", "desc": "Termux:API se apne phone ke features control"},
    {"id": "report",   "name": "Reporting & Audit",      "emoji": "📝", "desc": "Audit log + professional pentest report generator"},
]

TOOLS = [
    # ---------------- RECON / OSINT ----------------
    dict(name="theHarvester", cat="recon", check="theHarvester",
         desc="Emails, subdomains, hosts, names — public sources (CRTsh, Bing, DuckDuckgo, Shodan) se",
         examples=["theHarvester -d example.com -b crtsh,bing",
                   "theHarvester -d example.com -b all -l 300"]),
    dict(name="sherlock", cat="recon", check="sherlock",
         desc="300+ social/media sites par username dhoondho",
         examples=["sherlock target_username"]),
    dict(name="holehe", cat="recon", check="holehe",
         desc="Email address kisi website par registered hai ya nahi check karo",
         examples=["holehe someone@example.com"]),
    dict(name="phoneinfoga", cat="recon", check="phoneinfoga",
         desc="Phone number OSINT — carrier, country, possible leaks",
         examples=["phoneinfoga scan -n +911234567890",
                   "phoneinfoga serve -p 8081"]),
    dict(name="fierce", cat="recon", check="fierce",
         desc="DNS reconnaissance + subdomain brute-force",
         examples=["fierce --domain example.com"]),
    dict(name="dnsenum", cat="recon", check="dnsenum",
         desc="DNS enumeration — NS, MX, zone transfer, subdomains",
         examples=["dnsenum example.com"]),
    dict(name="RED_HAWK", cat="recon", check="RED_HAWK",
         desc="All-in-one web reconnaissance suite (PHP based)",
         examples=["echo | RED_HAWK"]),  # interactive tool

    # ---------------- SCANNING / ENUM ----------------
    dict(name="nmap", cat="scan", check="nmap",
         desc="Network mapper — ports, services, versions, OS, NSE scripts",
         examples=["nmap -sV -T4 example.com",
                   "nmap -A -p- 192.168.1.1",
                   "nmap --script vuln -sV example.com",
                   "nmap -sn 192.168.1.0/24"]),
    dict(name="dirsearch", cat="scan", check="dirsearch",
         desc="Web directories & hidden files brute-force",
         examples=["dirsearch -u https://example.com -e php,html,js,bak"]),
    dict(name="gobuster", cat="scan", check="gobuster",
         desc="Fast directory/file + DNS subdomain busting",
         examples=["gobuster dir -u https://example.com -w ~/vajra-tools/wordlist.txt"]),
    dict(name="enum4linux", cat="scan", check="enum4linux",
         desc="SMB/Windows enumeration — shares, users, groups",
         examples=["enum4linux -a 192.168.1.10"]),

    # ---------------- VULNERABILITY ANALYSIS ----------------
    dict(name="nikto", cat="vuln", check="nikto",
         desc="Classic web server vulnerability scanner",
         examples=["nikto -h https://example.com"]),
    dict(name="nuclei", cat="vuln", check="nuclei",
         desc="Modern template-based scanner — 8000+ templates (CVEs, misconfig, exposed panels)",
         examples=["nuclei -u https://example.com",
                   "nuclei -u https://example.com -t cves/ -severity critical,high"]),
    dict(name="searchsploit", cat="vuln", check="searchsploit",
         desc="Exploit-DB ka offline search — version-wise public exploits dhoondho",
         examples=["searchsploit apache 2.4.49",
                   "searchsploit --id wordpress 6.0"]),
    dict(name="testssl.sh", cat="vuln", check="testssl.sh",
         desc="SSL/TLS auditing — ciphers, protocols, heartbleed, POODLE etc.",
         examples=["testssl.sh https://example.com"]),

    # ---------------- GAINING ACCESS ----------------
    dict(name="sqlmap", cat="exploit", check="sqlmap",
         desc="SQL injection automation — dump, bypass, takeover (authorized testing only)",
         examples=["sqlmap -u 'https://example.com/page?id=1' --batch",
                   "sqlmap -u 'https://example.com/page?id=1' --forms --batch --level 3 --risk 2"]),
    dict(name="hydra", cat="exploit", check="hydra",
         desc="Login brute-forcer — SSH, FTP, HTTP forms, RDP, MySQL (apne lab par hi)",
         examples=["hydra -l admin -P wordlist.txt 192.168.1.10 ssh",
                   "hydra -L users.txt -P passes.txt example.com http-post-form '/login:user=^USER^&pass=^PASS^:F=failed'"]),
    dict(name="commix", cat="exploit", check="commix",
         desc="Command injection detection & exploitation",
         examples=["commix -u 'https://example.com/page?cmd=ping' --batch"]),
    dict(name="metasploit", cat="exploit", check="msfconsole",
         desc="#1 exploitation framework — 2000+ exploits, payloads, meterpreter, persistence modules "
              "(install.sh --full se install hota hai, heavy ~1GB)",
         examples=["msfconsole -q -x 'search type:exploit name:apache'",
                   "msfconsole -q -x 'search cve:2021-44228'"]),

    # ---------------- PASSWORD ATTACKS ----------------
    dict(name="john", cat="passwd", check="john",
         desc="John the Ripper — password hash cracking (fast on CPU)",
         examples=["john hashes.txt",
                   "john --wordlist=wordlist.txt hashes.txt"]),
    dict(name="cupp", cat="passwd", check="cupp",
         desc="Target ki personal info se custom wordlist generate karo (social-engineering labs)",
         examples=["cupp -i"]),
    dict(name="crunch", cat="passwd", check="crunch",
         desc="Pattern-based wordlist generator",
         examples=["crunch 8 10 abcdefghij0123456789 -o wordlist.txt"]),

    # ---------------- WIRELESS ----------------
    dict(name="aircrack-ng", cat="wireless", check="aircrack-ng",
         desc="WiFi capture & crack suite — airodump/aireplay/aircrack (root + monitor-mode adapter chahiye)",
         examples=["aircrack-ng capture.cap -w wordlist.txt",
                   "airodump-ng wlan0mon"]),
    dict(name="wifite", cat="wireless", check="wifite",
         desc="Automated WiFi auditing — WPA/WEP/WPS attacks (root chahiye)",
         examples=["wifite"]),

    # ---------------- POST-EXPLOITATION ----------------
    dict(name="linpeas", cat="post", check="linpeas",
         desc="Linux privilege-escalation enumerator — post-exploitation ka pehla kadam",
         examples=["linpeas -a"]),
    dict(name="les", cat="post", check="les",
         desc="Linux Exploit Suggester — kernel/version ke hisaab se privesc exploits suggest karta hai",
         examples=["les"]),
    dict(name="winPEAS", cat="post", check="winPEASx64.exe", check_paths=["~/vajra-tools/winPEASx64.exe"],
         desc="Windows privilege-escalation enumerator (--full install mein milta hai)",
         examples=["./winPEASx64.exe"]),

    # ---------------- PHONE CONTROLS ----------------
    dict(name="termux-camera-photo", cat="phone", check="termux-camera-photo",
         desc="Apne phone ki camera se photo lo (Termux:API app chahiye)",
         examples=["termux-camera-photo -c 0 photo.jpg"]),
    dict(name="termux-location", cat="phone", check="termux-location",
         desc="Apne phone ki GPS location",
         examples=["termux-location -p network"]),
    dict(name="termux-sms-list", cat="phone", check="termux-sms-list",
         desc="Apne hi phone ke SMS padho (OTP automation waghera)",
         examples=["termux-sms-list -l 10"]),
    dict(name="termux-wifi-connectioninfo", cat="phone", check="termux-wifi-connectioninfo",
         desc="Connected WiFi ki details",
         examples=["termux-wifi-connectioninfo"]),

    # ---------------- REPORTING ----------------
    dict(name="vajra-report", cat="report", check="vajra",
         desc="Built-in report generator — audit log se professional markdown pentest report",
         examples=["vajra --report"]),
]


def installed(entry):
    """Tool available hai ya nahi (PATH ya custom path se check karo)."""
    if shutil.which(entry["check"]):
        return True
    for p in entry.get("check_paths", []):
        if os.path.isfile(os.path.expanduser(p)):
            return True
    return False


def installed_map():
    return {t["name"]: installed(t) for t in TOOLS}


def summary_lines():
    """LLM ke system prompt ke liye category-wise tool summary."""
    lines = []
    for cat in CATEGORIES:
        tools = [t for t in TOOLS if t["cat"] == cat["id"]]
        parts = []
        for t in tools:
            ex = t["examples"][0] if t.get("examples") else t["name"]
            parts.append("%s (%s)" % (t["name"], ex))
        lines.append("%s %s: %s" % (cat["emoji"], cat["name"], "; ".join(parts)))
    return lines


def status_table():
    """CLI ke liye colored status table lines."""
    out = []
    for cat in CATEGORIES:
        out.append("\n%s %s — %s" % (cat["emoji"], cat["name"], cat["desc"]))
        for t in [x for x in TOOLS if x["cat"] == cat["id"]]:
            mark = "✓" if installed(t) else "✗"
            out.append("   [%s] %-22s %s" % (mark, t["name"], t["desc"][:70]))
    return "\n".join(out)
