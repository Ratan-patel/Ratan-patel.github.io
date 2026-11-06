"""Super Agent — Tool Arsenal catalog.

Yeh file **data** hai, code nahi. Har tool ke liye:
  * Kaunsa section (recon, gaining-access, exploitation, ...)
  * Kis binary/apt package se chalta hai
  * Allowed flags (safe default) — agent `-K` (KATAR) ke through sirf yehi
    flags set kar sakta hai. Free-form args tabhi allowed hain jab user ne
    settings me "raw args" ka switch ON kiya ho.
  * Intrusive? (to hamesha human approval lagega)
  * AI kya karega — short description jo AI ko batati hai kab use karna hai.

Naya tool add karna ho to neeche LIST me ek entry add karo — baaki sab
(scope, approval, audit, UI, AI tool-schema) automatically apply ho jayega.
"""

from __future__ import annotations

from dataclasses import dataclass, field

# Sections — UI aur AI dono isi order me dikhate hain
SECTIONS: dict[str, dict[str, str]] = {
    "recon": {
        "title": "1. Recon / OSINT",
        "icon": "🛰️",
        "purpose": "Domain, IP, DNS, certificates, tech-stack ki information ikattha karna.",
    },
    "info-access": {
        "title": "2. Information Access / Enumeration",
        "icon": "📂",
        "purpose": "Files, SMB/NFS shares, LDAP, DNS zone, cloud storage — exposed data dhundna.",
    },
    "vuln": {
        "title": "3. Vulnerability Analysis",
        "icon": "🔬",
        "purpose": "Misconfig, outdated software, CVEs — verification (proof) ke saath.",
    },
    "web": {
        "title": "4. Web / API Testing",
        "icon": "🌐",
        "purpose": "Endpoints, hidden paths, headers, TLS, API schemas.",
    },
    "gaining-access": {
        "title": "5. Gaining Access / Initial Foothold",
        "icon": "🚪",
        "purpose": "Authorized credentials / login service testing (rate-limited, approval-only).",
    },
    "exploitation": {
        "title": "6. Exploitation / PoC",
        "icon": "💥",
        "purpose": "Verified CVE ka minimal, non-destructive proof-of-concept.",
    },
    "post": {
        "title": "7. Post-Exploitation / Situational Awareness",
        "icon": "🧭",
        "purpose": "Foothold ke baad (likhit permission ke saath) system ki samajh — read-only.",
    },
    "privilege": {
        "title": "8. Privilege Escalation Checks",
        "icon": "🪜",
        "purpose": "Misconfigured sudo/SUID/capabilities — escalation *path* detect karna, weaponize nahi.",
    },
    "cracking": {
        "title": "9. Password / Hash Analysis",
        "icon": "🔑",
        "purpose": "Apne lab hashes par dictionary/rule audit — password policy review.",
    },
    "wireless": {
        "title": "10. Wireless / RF",
        "icon": "📶",
        "purpose": "Apne SSID/AP ke security posture ki jaanch (capture audit).",
    },
    "reporting": {
        "title": "11. Reporting & Evidence",
        "icon": "📄",
        "purpose": "Findings → client-ready report + hash-chained evidence chain.",
    },
    "utility": {
        "title": "12. Utility",
        "icon": "🧰",
        "purpose": "Chhote helpers — hashing, encoding, wordlist, proxy/tunnel.",
    },
}


@dataclass(frozen=True)
class Tool:
    name: str
    section: str
    binary: str
    package: str
    summary: str
    # flags agent `-K name=value` / `-F name` se set kar sakta hai
    flags: dict[str, str] = field(default_factory=dict)
    # allowed flag names jinme arbitrary value ja sakti hai (host, url, path...)
    valued: tuple[str, ...] = ()
    intrusive: bool = False
    # true = ye tool target ke against nahi chalta (jaise hashid, echo)
    offline: bool = False
    install_hint: str = ""
    version_flag: str = "--version"
    example: str = ""
    # profile me kaun kaun se flags default lagte hain (full scan profiles)
    default_args: tuple[str, ...] = ()


def _t(*a, **kw) -> Tool:
    return Tool(*a, **kw)


# ---------------------------------------------------------------------------
# TOOL LIST
# ---------------------------------------------------------------------------
TOOLS: dict[str, Tool] = {}


def _add(tool: Tool) -> None:
    TOOLS[tool.name] = tool


# ---- 1. RECON -------------------------------------------------------------
_add(_t("whois", "recon", "whois", "whois",
       "Domain registrar, dates, nameservers, org info.",
       flags={}, example="whois target=example.com"))
_add(_t("dig", "recon", "dig", "dnsutils",
       "DNS records (A/AAAA/MX/NS/TXT/SOA/CNAME), zone info.",
       flags={"record": "string (A, MX, NS, TXT, SOA, CNAME, ANY)",
              "server": "custom resolver IP (optional)"},
       valued=("record", "server", "target"), example="dig target=example.com record=TXT"))
_add(_t("host", "recon", "host", "dnsutils",
       "Simple DNS lookup + reverse lookup.",
       flags={"reverse": "", "record": "string"},
       example="host target=8.8.8.8 reverse=1"))
_add(_t("nslookup", "recon", "nslookup", "dnsutils",
       "DNS query (fallback jab dig na ho).", flags={"record": "string"}))
_add(_t("dnsx", "recon", "dnsx", "dnsx",
       "Fast DNS toolkit — bulk resolution + records.",
       flags={"record": "a/aaaa/cname/mx/ns/txt", "domain": "scan domain ke saare subdomains (optional)"},
       valued=("record", "target", "domain")))
_add(_t("theHarvester", "recon", "theHarvester", "theharvester",
       "Emails, subdomains, hosts — public sources (OSINT).",
       flags={"source": "duckduckgo/bing/crtsh/otx...", "limit": "max results"},
       valued=("source", "target", "limit"), install_hint="pipx install theHarvester"))
_add(_t("amass", "recon", "amass", "amass",
       "Attack-surface mapping / subdomain enumeration (passive mode default).",
       flags={"mode": "enum/passive", "timeout": "minutes"},
       valued=("mode", "target", "timeout")))
_add(_t("subfinder", "recon", "subfinder", "subfinder",
       "Passive subdomain discovery (kaafi reliable).",
       flags={"all": "saare sources", "silent": ""}, valued=("target",)))
_add(_t("assetfinder", "recon", "assetfinder", "assetfinder",
       "Subdomain finder (sirf output).", valued=("target",)))
_add(_t("findomain", "recon", "findomain", "findomain",
       "Cross-platform subdomain enumerator.", valued=("target",)))
_add(_t("dnsrecon", "recon", "dnsrecon", "dnsrecon",
       "DNS enumeration — zone transfer, brute-force, SRV records.",
       flags={"type": "std/axfr/brt/srv", "domain": "target domain"},
       valued=("type", "target", "domain")))
_add(_t("fierce", "recon", "fierce", "fierce",
       "DNS recon + zone-transfer attempts.",
       flags={"domain": "target"}, valued=("domain", "target")))
_add(_t("dmitry", "recon", "dmitry", "dmitry",
       "Deepmagic Information Gathering — whois/subdomain/ports.",
       flags={"whois": "", "subdomain": "", "portscan": ""}, valued=("target",)))
_add(_t("sublist3r", "recon", "sublist3r", "sublist3r",
       "Subdomain enumeration (OSINT engines).", valued=("target",)))
_add(_t("whatweb", "recon", "whatweb", "whatweb",
       "Web fingerprinting — CMS, server, frameworks, headers.",
       flags={"aggression": "1-4", "verbose": ""}, valued=("target",), default_args=("-q", "--no-errors")))
_add(_t("wafw00f", "recon", "wafw00f", "wafw00f",
       "WAF detect karta hai (kaunsa firewall aage hai).", valued=("target",)))
_add(_t("sslyze", "recon", "sslyze", "sslyze",
       "TLS/SSL configuration audit — weak ciphers, protocols, cert chain.",
       flags={"certinfo": "", "json": "json output"}, valued=("target",)))
_add(_t("sslscan", "recon", "sslscan", "sslscan",
       "Fast TLS scanner — ciphers + Heartbleed check.",
       flags={"no-failed": "sirf supported", "show-cert": ""}, valued=("target",)))
_add(_t("testssl", "recon", "testssl.sh", "testssl.sh",
       "Comprehensive TLS test (kuch minute lagta hai).",
       flags={"severity": "LOW/MEDIUM/HIGH", "fast": ""}, valued=("target",), install_hint="apt install testssl.sh"))
_add(_t("traceroute", "recon", "traceroute", "traceroute",
       "Network path trace — hops dikhata hai.",
       flags={"max_hops": "1-64", "numeric": ""}, valued=("target", "max_hops")))
_add(_t("ping", "recon", "ping", "iputils-ping",
       "ICMP reachability (fast check).",
       flags={"count": "1-10"}, valued=("target", "count")))
_add(_t("masscan", "recon", "masscan", "masscan",
       "Bahut fast port discovery (authorized scope par hi).",
       flags={"rate": "packets/sec", "ports": "1-1000 / 80,443 / -", "wait": "seconds"},
       valued=("rate", "ports", "wait", "target"), intrusive=True,
       install_hint="apt install masscan (root/NET_RAW chahiye)"))
_add(_t("gau", "recon", "gau", "gau",
       "GetAllUrls — Wayback/Common Crawl se known URLs.",
       flags={"subs": "subdomains include", "providers": "wayback,commoncrawl,otx"},
       valued=("target",)))
_add(_t("waybackurls", "recon", "waybackurls", "waybackurls",
       "Wayback Machine se purane URLs.",
       flags={"no_subs": ""}, valued=("target",)))
_add(_t("shuffledns", "recon", "shuffledns", "shuffledns",
       "Mass DNS brute-force (wildcard handling ke saath).",
       flags={"wordlist": "path"}, valued=("target", "wordlist")))
_add(_t("cloud_enum", "recon", "cloud_enum", "cloud_enum",
       "Public cloud storage buckets (AWS/Azure/GCP) — keyword based.",
       flags={"keyword": "company name"}, valued=("keyword", "target"),
       install_hint="pipx install cloud_enum"))
_add(_t("sherlock", "recon", "sherlock", "sherlock",
       "Username se social-media accounts (OSINT).",
       flags={"timeout": "seconds"}, valued=("target", "timeout")))

# ---- 2. INFORMATION ACCESS / ENUMERATION ----------------------------------
_add(_t("enum4linux", "info-access", "enum4linux", "enum4linux",
       "Windows/SMB enumeration — users, shares, groups.",
       flags={"all": "full enumeration", "users": "", "shares": ""}, valued=("target",)))
_add(_t("enum4linux-ng", "info-access", "enum4linux-ng", "enum4linux-ng",
       "enum4linux ka modern rewrite (JSON output).",
       flags={"all": "", "json": "out.json"}, valued=("target", "json")))
_add(_t("smbclient", "info-access", "smbclient", "smbclient",
       "SMB shares list / anonymous connect.",
       flags={"list": "share list", "user": "username", "no_pass": ""},
       valued=("target", "user"), intrusive=False))
_add(_t("smbmap", "info-access", "smbmap", "smbmap",
       "SMB share permissions (read/write) — exposed data ka risk.",
       flags={"host": "single host", "user": "user", "pass": "password (approval)", "recursive": ""},
       valued=("target", "user"), intrusive=True))
_add(_t("rpcclient", "info-access", "rpcclient", "samba-common-bin",
       "MS-RPC enumeration (users/groups) — no creds mode.",
       flags={"user": "username (blank = guest)", "command": "enumdomusers / querydominfo"},
       valued=("target", "user", "command")))
_add(_t("nfs-ls", "info-access", "showmount", "nfs-common",
       "NFS exports list — kaunsi directory share hai.",
       flags={"exports": ""}, valued=("target",)))
_add(_t("snmpwalk", "info-access", "snmpwalk", "snmp",
       "SNMP walk — devices, interfaces, sysinfo (default community 'public').",
       flags={"community": "community string (default public)", "version": "1/2c/3"},
       valued=("target", "community", "version")))
_add(_t("snmp-check", "info-access", "snmp-check", "snmpcheck",
       "SNMP data ko readable form me — users, processes, shares.",
       valued=("target",)))
_add(_t("onesixtyone", "info-access", "onesixtyone", "onesixtyone",
       "SNMP community string scanner.",
       flags={"community": "comma list"}, valued=("target", "community")))
_add(_t("ldapsearch", "info-access", "ldapsearch", "ldap-utils",
       "LDAP directory query — users, groups, policies.",
       flags={"base": "search base DN", "filter": "ldap filter", "server": "ldap://host"},
       valued=("base", "filter", "server", "target")))
_add(_t("ldapdomaindump", "info-access", "ldapdomaindump", "ldapdomaindump",
       "AD ko LDIF/HTML me dump (creds ke saath, approval).",
       flags={"user": "domain\\\\user", "pass": "password"}, valued=("user", "target"), intrusive=True))
_add(_t("nbtscan", "info-access", "nbtscan", "nbtscan",
       "NetBIOS name scan — Windows hosts identify.",
       flags={"verbose": ""}, valued=("target",)))
_add(_t("crackmapexec", "info-access", "crackmapexec", "crackmapexec",
       "SMB/WinRM/LDAP spray + share audit (approval mandatory).",
       flags={"protocol": "smb/winrm/ldap/mssql", "user": "username", "pass": "password",
              "shares": "list shares", "hash": "NTLM hash"},
       valued=("protocol", "user", "target"), intrusive=True, install_hint="pipx install crackmapexec"))
_add(_t("netexec", "info-access", "nxc", "netexec",
       "CrackMapExec ka successor — same kaam, naya naam.",
       flags={"protocol": "smb/winrm/ldap/mssql", "user": "username", "pass": "password", "shares": ""},
       valued=("protocol", "user", "target"), intrusive=True, install_hint="pipx install netexec"))
_add(_t("smbclient-ng", "info-access", "smbclientng", "smbclientng",
       "Interactive SMB explorer (scriptable).",
       flags={"user": "user", "pass": "password"}, valued=("user", "target"), intrusive=True))
_add(_t("gobuster-dns", "info-access", "gobuster", "gobuster",
       "DNS subdomain brute-force (wordlist ke saath).",
       flags={"domain": "target domain", "wordlist": "path"}, valued=("domain", "wordlist", "target"),
       default_args=("dns",)))
_add(_t("httpx", "info-access", "httpx", "httpx-toolkit",
       "HTTP probe — status, title, tech, CDN (bahut fast).",
       flags={"title": "", "tech": "tech-detect", "status_code": "", "ports": "80,443,8080"},
       valued=("target", "ports"), install_hint="apt install httpx-toolkit (ya go install httpx)"))
_add(_t("katana", "info-access", "katana", "katana",
       "Modern crawler — JS endpoints, forms, hidden routes.",
       flags={"depth": "1-5", "js-crawl": "", "silent": ""}, valued=("target", "depth")))
_add(_t("gospider", "info-access", "gospider", "gospider",
       "Fast web spider — links + JS files.",
       flags={"depth": "1-3", "site": ""}, valued=("target", "depth")))
_add(_t("dalfox", "info-access", "dalfox", "dalfox",
       "XSS scanner (reflected/stored) — proof-of-concept payload only.",
       flags={"url": "target url", "blind": ""}, valued=("url", "target"), intrusive=True))
_add(_t("arjun", "info-access", "arjun", "arjun",
       "Hidden HTTP parameters discover karta hai.",
       flags={"method": "GET/POST", "stable": ""}, valued=("target", "method")))
_add(_t("paramspider", "info-access", "paramspider", "paramspider",
       "Archive se parameterized URLs nikalta hai.",
       flags={"domain": "target"}, valued=("target",)))

# ---- 3. VULNERABILITY ANALYSIS -------------------------------------------
_add(_t("nmap-vuln", "vuln", "nmap", "nmap",
       "Nmap NSE — vuln scripts, service CVEs (safe mode).",
       flags={"ports": "top200 / 1-1000 / 80,443", "scripts": "vuln / safe / default", "version": "sV"},
       valued=("target", "ports", "scripts"),
       default_args=("-T4", "-Pn", "--open", "--script", "vuln")))
_add(_t("nuclei", "vuln", "nuclei", "nuclei",
       "Template-based scanner — 9000+ CVEs, exposures, misconfigs (safe, non-destructive templates).",
       flags={"severity": "low,medium,high,critical", "tags": "cve,exposure,misconfig",
              "templates": "custom path (optional)", "rate": "req/sec"},
       valued=("severity", "tags", "templates", "target", "rate"),
       default_args=("-silent", "-nc", "-duc")))
_add(_t("nikto", "vuln", "nikto", "nikto",
       "Web server misconfig + outdated software scanner.",
       flags={"port": "80/443/etc", "ssl": "", "tuning": "1-9"},
       valued=("port", "target", "tuning"), default_args=("-nointeractive", "-ask", "no")))
_add(_t("wapiti", "vuln", "wapiti", "wapiti",
       "Black-box web app vulnerability scanner (XSS/SQLi/LFI/SSRF).",
       flags={"scope": "domain/folder/url", "format": "json/html/md"}, valued=("scope", "target", "format")))
_add(_t("zap-baseline", "vuln", "zaproxy", "zaproxy",
       "OWASP ZAP baseline scan (passive, safe).",
       flags={"config": "zap config path"}, valued=("target",)))
_add(_t("vuls", "vuln", "vuls", "vuls",
       "Agent-less CVE scan (Linux servers ke liye).",
       flags={"config": "config.toml"}, valued=("target",), install_hint="go install vuls (server inventory chahiye)"))
_add(_t("searchsploit", "vuln", "searchsploit", "exploitdb",
       "Exploit-DB offline search — CVE/version se PoC mapping.",
       flags={"json": "json output", "id": "EDB-ID"}, valued=("target", "id"), offline=True))
_add(_t("cve-search", "vuln", "cve-search", "cve-search",
       "Local CVE database query (offline).", valued=("target",), offline=True,
       install_hint="docker run cve-search (optional)"))
_add(_t("trivy", "vuln", "trivy", "trivy",
       "Container/filesystem CVE + secret scanner (apni image par).",
       flags={"severity": "HIGH,CRITICAL", "type": "image/fs/repo"}, valued=("target", "severity")))
_add(_t("gitleaks", "vuln", "gitleaks", "gitleaks",
       "Git repo me leaked secrets detect karta hai.",
       flags={"no-git": "", "verbose": ""}, valued=("target",)))
_add(_t("trufflehog", "vuln", "trufflehog", "trufflehog",
       "Kho jaate secrets/keys — verified detections.",
       flags={"only-verified": ""}, valued=("target",)))
_add(_t("semgrep", "vuln", "semgrep", "semgrep",
       "Code-level SAST (OWASP rules) — apne source par.",
       flags={"config": "auto/p/owasp-top-ten", "severity": "ERROR/WARNING"},
       valued=("config", "target", "severity")))

# ---- 4. WEB / API TESTING -------------------------------------------------
_add(_t("ffuf", "web", "ffuf", "ffuf",
       "Fast fuzzer — directories, vhosts, parameters.",
       flags={"wordlist": "path", "filter_code": "403,404", "threads": "1-40",
              "mode": "dir/vhost/param", "extensions": "php,txt"},
       valued=("wordlist", "filter_code", "threads", "mode", "target", "extensions"),
       default_args=("-s", "-noninteractive")))
_add(_t("gobuster-dir", "web", "gobuster", "gobuster",
       "Directory/file brute-force (stable, dependency-free).",
       flags={"wordlist": "path", "threads": "1-40", "extensions": "php,html"},
       valued=("wordlist", "threads", "extensions", "target"), default_args=("dir", "-q", "--no-progress")))
_add(_t("feroxbuster", "web", "feroxbuster", "feroxbuster",
       "Recursive content discovery (rust, fast).",
       flags={"wordlist": "path", "depth": "1-4"}, valued=("wordlist", "depth", "target")))
_add(_t("dirsearch", "web", "dirsearch", "dirsearch",
       "Directory scanner (python) — recursive optional.",
       flags={"wordlist": "path", "extensions": "php"}, valued=("wordlist", "extensions", "target")))
_add(_t("wpscan", "web", "wpscan", "wpscan",
       "WordPress specific — plugins, themes, users, core CVE.",
       flags={"enumerate": "vp,vt,u", "api_token": "wpscan api token (optional)"},
       valued=("enumerate", "target", "api_token")))
_add(_t("joomscan", "web", "joomscan", "joomscan",
       "Joomla vulnerability scan.", valued=("target",)))
_add(_t("droopescan", "web", "droopescan", "droopescan",
       "Drupal/SilverStripe/WordPress plugin scan.", valued=("target",)))
_add(_t("sqlmap", "web", "sqlmap", "sqlmap",
       "SQL injection detection (level 1-2, --batch). Approval mandatory.",
       flags={"level": "1-3", "risk": "1-2", "data": "POST body", "cookie": "session cookie",
              "dbms": "mysql/mssql/postgres", "forms": ""},
       valued=("level", "risk", "target", "dbms"), intrusive=True,
       default_args=("--batch", "--smart", "--threads", "4", "--timeout", "10")))
_add(_t("burp-scanner", "web", "burpsuite", "burpsuite",
       "Burp Suite CLI (headless scan) — GUI/binary ka path chahiye.",
       flags={"config": "burp config"}, valued=("target",), intrusive=True,
       install_hint="Burp Suite Pro (commercial) — apt me nahi milta"))
_add(_t("commix", "web", "commix", "commix",
       "Command injection detection (safe payload).",
       flags={"level": "1-3", "batch": ""}, valued=("target", "level"), intrusive=True))
_add(_t("xsstrike", "web", "xsstrike", "xsstrike",
       "XSS detection + payload fuzzing.", valued=("target",), intrusive=True))
_add(_t("jwt_tool", "web", "jwt_tool", "jwt-tool",
       "JWT attacks — alg confusion, weak secret, kid injection (non-destructive checks).",
       flags={"mode": "scan/all", "wordlist": "secret list"}, valued=("target", "mode", "wordlist")))
_add(_t("graphql-cop", "web", "graphql-cop", "graphql-cop",
       "GraphQL introspection + abuse checks.",
       valued=("target",)))
_add(_t("openapi-spec", "web", "curl", "curl",
       "API schema nikaalna (openapi.json / swagger.json) — recon ke liye.",
       valued=("target",), offline=False))
_add(_t("postman-newman", "web", "newman", "newman",
       "API collection (Postman) ko CI me chalana.",
       flags={"collection": "collection.json"}, valued=("collection", "target", "env")))
_add(_t("mitmproxy", "web", "mitmdump", "mitmproxy",
       "Traffic intercept (apni app ka mobile/API traffic).",
       flags={"mode": "regular/transparent", "read": "flow file"}, valued=("mode", "target"),
       install_hint="pipx install mitmproxy"))
_add(_t("websocat", "web", "websocat", "websocat",
       "WebSocket CLI — messages read/send (authorized).", valued=("target",)))
_add(_t("nmap-http", "web", "nmap", "nmap",
       "http-title/http-headers/http-enum NSE — endpoints + methods.",
       flags={"scripts": "http-title,http-headers", "ports": "80,443,8080"},
       valued=("target", "scripts", "ports"), default_args=("-T4", "-Pn", "--open", "-sV")))

# ---- 5. GAINING ACCESS / INITIAL FOOTHOLD --------------------------------
_add(_t("hydra", "gaining-access", "hydra", "hydra",
       "Login brute-force (ssh/ftp/rdp/http-form). Rate-limited + approval only.",
       flags={"service": "ssh/ftp/rdp/http-post-form", "user": "username",
              "userlist": "path", "passlist": "path", "threads": "1-8"},
       valued=("service", "user", "userlist", "passlist", "threads", "target"), intrusive=True,
       default_args=("-t", "4", "-f", "-V")))
_add(_t("medusa", "gaining-access", "medusa", "medusa",
       "Parallel login brute-force (hydra ka alternative).",
       flags={"module": "ssh/ftp/rdp", "user": "user", "passlist": "path"},
       valued=("module", "user", "passlist", "target"), intrusive=True))
_add(_t("patator", "gaining-access", "patator", "patator",
       "Modular brute-forcer (ssh, ftp, http).",
       flags={"module": "ssh_login/http_fuzz"}, valued=("module", "target"), intrusive=True))
_add(_t("ncrack", "gaining-access", "ncrack", "ncrack",
       "Nmap project ka auth cracker (network services).",
       flags={"service": "ssh/rdp/ftp"}, valued=("service", "target"), intrusive=True))
_add(_t("responder", "gaining-access", "responder", "responder",
       "LLMNR/NBT-NS/mDNS poisoner — internal AD assessment (approval, apne network me).",
       flags={"interface": "eth0/wlan0", "analyze": "sirf sunna (safe)", "wpad": ""},
       valued=("interface",), intrusive=True, install_hint="apt install responder (root)"))
_add(_t("evilginx", "gaining-access", "evilginx", "evilginx",
       "AiTM phishing (authorized red-team exercise ke liye) — legal review zaroori.",
       flags={"config": "phishlet"}, valued=("config",), intrusive=True,
       install_hint="manual build — sirf likhit authorization ke saath"))
_add(_t("bettercap", "gaining-access", "bettercap", "bettercap",
       "MITM framework (caplet ke saath) — internal network assessment.",
       flags={"caplet": "eval/all", "iface": "interface"}, valued=("caplet", "iface"), intrusive=True))
_add(_t("aircrack-ng", "gaining-access", "aircrack-ng", "aircrack-ng",
       "WPA handshake crack (apne capture par).",
       flags={"wordlist": "path", "bssid": "AP mac"}, valued=("wordlist", "bssid", "target"), intrusive=True))
_add(_t("setoolkit", "gaining-access", "setoolkit", "set",
       "Social-Engineering Toolkit (credential harvester) — authorized awareness campaign only.",
       intrusive=True, install_hint="apt install set (root, manual config)"))

# ---- 6. EXPLOITATION / PoC ------------------------------------------------
_add(_t("metasploit", "exploitation", "msfconsole", "metasploit-framework",
       "Metasploit — module search/info, aur check (non-destructive verification).",
       flags={"module": "exploit/windows/...", "rhosts": "target ip", "check": "sirf check (default)",
              "payload": "payload name (manual mode)"},
       valued=("module", "rhosts", "payload"), intrusive=True,
       default_args=("-q", "-x", "exit")))
_add(_t("msfvenom", "exploitation", "msfvenom", "metasploit-framework",
       "Payload generator (lab ke liye).",
       flags={"payload": "payload name", "lhost": "your ip", "lport": "port", "format": "exe/elf/raw"},
       valued=("payload", "lhost", "lport", "format"), intrusive=True))
_add(_t("searchsploit-poc", "exploitation", "searchsploit", "exploitdb",
       "CVE/version ka PoC local exploit DB se (sirf dikhana, chalana manual).",
       flags={"id": "EDB id"}, valued=("target", "id"), offline=True))
_add(_t("sqlmap-exploit", "exploitation", "sqlmap", "sqlmap",
       "SQLi confirm + data extraction (--dump sirf approval par).",
       flags={"level": "1-3", "risk": "1-2", "dump": "table dump (approval)", "db": "database"},
       valued=("level", "risk", "target", "db"), intrusive=True,
       default_args=("--batch", "--threads", "4")))
_add(_t("xsrfprobe", "exploitation", "xsrfprobe", "xsrfprobe",
       "CSRF proof-of-concept generator (authorized).", valued=("target",), intrusive=True))
_add(_t("corsy", "exploitation", "corsy", "corsy",
       "CORS misconfiguration detection (exploitable → PoC).", valued=("target",)))
_add(_t("ssrfmap", "exploitation", "ssrfmap", "ssrfmap",
       "SSRF PoC — parameter identify karke test (metadata URLs BLOCKED by agent).",
       flags={"param": "vulnerable param", "module": "readfiles/portscan"}, valued=("target", "param", "module"),
       intrusive=True))
_add(_t("ysoserial", "exploitation", "ysoserial", "ysoserial",
       "Java deserialization payloads (lab only).",
       flags={"gadget": "CommonsCollections6", "command": "id"}, valued=("gadget", "command"), intrusive=True))
_add(_t("beef", "exploitation", "beef-xss", "beef-xss",
       "Browser exploitation framework — authorized phishing simulation.",
       intrusive=True, install_hint="apt install beef-xss"))
_add(_t("routersploit", "exploitation", "rsf", "routersploit",
       "Embedded device exploit framework (apne routers par).",
       flags={"module": "scanners/routers/...", "target": "ip"}, valued=("module", "target"), intrusive=True))
_add(_t("impacket", "exploitation", "impacket-psexec", "impacket-scripts",
       "Impacket suite — psexec/wmiexec/secretsdump (creds ke saath, approval).",
       flags={"user": "domain/user", "hash": "ntlm hash", "command": "id"}, valued=("user", "target"), intrusive=True))

# ---- 7. POST-EXPLOITATION (approval-only, read-mostly) --------------------
_add(_t("linpeas", "post", "linpeas", "peass",
       "Linux privesc enumeration script (read-only, noisy-safe).",
       flags={"fast": "quick mode"}, valued=("target",), intrusive=True,
       install_hint="github.com/peass-ng/PEASS-ng (binary download)"))
_add(_t("winpeas", "post", "winpeas", "peass",
       "Windows privesc enumeration script.", intrusive=True,
       install_hint="github.com/peass-ng/PEASS-ng"))
_add(_t("lse", "post", "lse", "linux-smart-enumeration",
       "Linux Smart Enumeration — levels 0-2.", flags={"level": "0-2"}, valued=("level",), intrusive=True))
_add(_t("mimikatz", "post", "mimikatz", "mimikatz",
       "Windows credential extraction — sirf apne lab VM par, likhit permission ke saath.",
       intrusive=True, install_hint="manual download (antivirus flags) — high-risk"))
_add(_t("secretsdump", "post", "impacket-secretsdump", "impacket-scripts",
       "SAM/LSA/NTDS dump (creds ke saath — approval).",
       flags={"user": "domain/user", "hash": "ntlm"}, valued=("user", "target"), intrusive=True))
_add(_t("bloodhound", "post", "bloodhound-python", "bloodhound",
       "AD attack-path collection (BloodHound).",
       flags={"domain": "domain", "user": "user", "pass": "password", "collection": "All"},
       valued=("domain", "user", "collection"), intrusive=True))
_add(_t("chisel", "post", "chisel", "chisel",
       "Tunnel (SOCKS over HTTP) — pivot ke liye.",
       flags={"server": "server:port", "socks": "port"}, valued=("server", "socks"), intrusive=True))
_add(_t("ligolo", "post", "ligolo-proxy", "ligolo-ng",
       "Ligolo-ng pivot (TUN based).", intrusive=True, install_hint="manual download"))
_add(_t("proxychains", "post", "proxychains4", "proxychains4",
       "Kisi bhi tool ko proxy chain ke through chalana.",
       flags={"config": "proxychains.conf"}, valued=("config", "target")))

# ---- 8. PRIVILEGE ESCALATION CHECKS --------------------------------------
_add(_t("sudo-check", "privilege", "sudo", "sudo",
       "sudo -l style checks (apne user par, read-only).",
       flags={"list": ""}, valued=("target",), offline=True))
_add(_t("suid-finder", "privilege", "find", "findutils",
       "SUID/SGID binaries find karna (read-only).",
       flags={"path": "/", "suid": ""}, valued=("path",), offline=True))
_add(_t("getcap", "privilege", "getcap", "libcap2-bin",
       "Linux capabilities audit.", flags={"recursive": ""}, valued=("path",)))
_add(_t("pspy", "privilege", "pspy", "pspy",
       "Cron/process monitor — escalation paths detect (read-only).",
       flags={"interval": "seconds"}, intrusive=True))
_add(_t("linux-exploit-suggester", "privilege", "les.sh", "les",
       "Kernel version se known exploits suggest karta hai (chalata nahi).",
       install_hint="manual download (github mzet-)", offline=True))
_add(_t("winprivesc", "privilege", "winPEASx64.exe", "peass",
       "Windows privesc check (PowerShell alternatives bhi).", intrusive=True))
_add(_t("seatbelt", "privilege", "Seatbelt.exe", "seatbelt",
       "Windows host situational-awareness checks (C#).", intrusive=True,
       install_hint="GhostPack/Seatbelt (manual)"))

# ---- 9. PASSWORD / HASH ANALYSIS -----------------------------------------
_add(_t("hashid", "cracking", "hashid", "hashid",
       "Hash type identify (offline, safe).", flags={"mode": "0-3"}, valued=("target",), offline=True))
_add(_t("hashcat", "cracking", "hashcat", "hashcat",
       "GPU/CPU hash cracking — apne lab hashes par (approval).",
       flags={"mode": "0/1000/1800/22000", "wordlist": "path", "rules": "best64"},
       valued=("mode", "wordlist", "rules", "target"), intrusive=True, offline=True,
       default_args=("--potfile-disable", "--force", "-O")))
_add(_t("john", "cracking", "john", "john",
       "John the Ripper — wordlist + rules.",
       flags={"format": "raw-md5/nt", "wordlist": "path", "rules": ""},
       valued=("format", "wordlist", "target"), intrusive=True, offline=True))
_add(_t("ophcrack", "cracking", "ophcrack", "ophcrack",
       "Windows LM/NTLM rainbow lookup (offline).", intrusive=True, offline=True))
_add(_t("cewl", "cracking", "cewl", "cewl",
       "Target site se custom wordlist banana (authorized).",
       flags={"depth": "1-3", "min_length": "5"}, valued=("target", "depth", "min_length")))
_add(_t("crunch", "cracking", "crunch", "crunch",
       "Wordlist generator (specific pattern ke liye).",
       flags={"min": "n", "max": "n", "pattern": "charset"}, valued=("min", "max", "pattern"), offline=True))
_add(_t("rsmangler", "cracking", "rsmangler", "rsmangler",
       "Wordlist mutations (leetspeak, years, suffixes).", valued=("target",), offline=True))

# ---- 10. WIRELESS -------------------------------------------------------
_add(_t("airmon-ng", "wireless", "airmon-ng", "aircrack-ng",
       "Wireless interface monitor mode (apne adapter par).",
       flags={"iface": "wlan0"}, valued=("iface",), intrusive=True))
_add(_t("airodump-ng", "wireless", "airodump-ng", "aircrack-ng",
       "AP/client capture (apne SSID par).",
       flags={"iface": "wlan0mon", "bssid": "AP mac", "channel": "1-14",
              "write": "capture prefix"}, valued=("iface", "bssid", "channel", "write"), intrusive=True))
_add(_t("aireplay-ng", "wireless", "aireplay-ng", "aircrack-ng",
       "Deauth/capture (apne lab clients par — approval).",
       flags={"iface": "wlan0mon", "bssid": "AP", "count": "n"},
       valued=("iface", "bssid", "count"), intrusive=True))
_add(_t("wifite", "wireless", "wifite", "wifite",
       "Automated wireless audit (apne BSSID range par).", intrusive=True))
_add(_t("bettercap-wifi", "wireless", "bettercap", "bettercap",
       "WiFi recon + handshake capture (bettercap).",
       flags={"iface": "wlan0mon"}, valued=("iface",), intrusive=True))

# ---- 11. REPORTING ------------------------------------------------------
_add(_t("mkdir-evidence", "reporting", "mkdir", "coreutils",
       "Evidence folder banana (hash chain + timestamps).",
       flags={"path": "evidence/2026-..."}, valued=("path",), offline=True))
_add(_t("sha256sum", "reporting", "sha256sum", "coreutils",
       "Evidence file ka hash (integrity proof).", valued=("target",), offline=True))
_add(_t("gpg-sign", "reporting", "gpg", "gnupg",
       "Evidence ko sign karna (chain-of-custody).",
       flags={"sign": "", "key": "key id"}, valued=("target", "key"), offline=True))
_add(_t("report-audit", "reporting", "pdftotext", "poppler-utils",
       "Client report ko text me convert karke audit me attach karna.",
       valued=("target",), offline=True))

# ---- 12. UTILITY --------------------------------------------------------
_add(_t("curl", "utility", "curl", "curl",
       "HTTP request (headers, status, API calls, downloads).",
       flags={"method": "GET/HEAD/POST", "headers": "", "insecure": "sirf lab",
              "user_agent": "string", "max_time": "seconds"},
       valued=("method", "user_agent", "max_time", "target"),
       default_args=("-sS", "-i", "--max-time", "20")))
_add(_t("wget", "utility", "wget", "wget",
       "File download (authorized mirror/backup).",
       flags={"spider": "", "quiet": ""}, valued=("target",)))
_add(_t("nc", "utility", "nc", "netcat-openbsd",
       "Netcat — banner grab / port reachability.",
       flags={"verbose": "", "zero": "", "wait": "seconds"},
       valued=("target", "wait"), default_args=("-vz", "-w", "3")))
_add(_t("socat", "utility", "socat", "socat",
       "Relay/tunnel (advanced).", valued=("target",), intrusive=True))
_add(_t("jq", "utility", "jq", "jq",
       "JSON filter (output ko readable banana).", valued=("target",), offline=True))
_add(_t("openssl", "utility", "openssl", "openssl",
       "Cert parse, TLS connect, hash.",
       flags={"connect": "host:port", "servername": "SNI"}, valued=("connect", "servername")))
_add(_t("enum-ip", "utility", "whois", "whois",
       "IP ownership / ASN lookup.", flags={"asn": ""}, valued=("target",)))
_add(_t("proxychains-wrap", "utility", "proxychains4", "proxychains4",
       "Kisi command ko proxy ke through — manual mode.",
       flags={"config": "path"}, valued=("config", "target")))


# ---------------------------------------------------------------------------
# Scan profiles (direct, AI-free) — section-based presets
# ---------------------------------------------------------------------------
PROFILES: dict[str, dict] = {
    "recon": {
        "title": "Quick Recon",
        "description": "whois + DNS + headers + top ports (~2-4 min)",
        "tools": ["whois", "dig", "curl", "nmap-vuln"],
    },
    "web": {
        "title": "Web Surface",
        "description": "whatweb + httpx + nikto + gobuster (~4-7 min)",
        "tools": ["whatweb", "httpx", "nikto", "gobuster-dir"],
    },
    "vuln": {
        "title": "Vulnerability Sweep",
        "description": "nmap vuln scripts + nuclei CVE templates (~5-8 min)",
        "tools": ["nmap-vuln", "nuclei"],
    },
    "info": {
        "title": "Info Access",
        "description": "SMB/SNMP/LDAP/NFS enumeration (internal hosts)",
        "tools": ["enum4linux-ng", "snmpwalk", "nmap-vuln"],
    },
    "full": {
        "title": "Full Sweep",
        "description": "Recon + Web + Vuln — sabse detailed (10-15 min)",
        "tools": ["whois", "dig", "whatweb", "httpx", "nmap-vuln", "nikto", "nuclei"],
    },
}


def by_section() -> dict[str, list[Tool]]:
    out: dict[str, list[Tool]] = {key: [] for key in SECTIONS}
    for tool in TOOLS.values():
        out.setdefault(tool.section, []).append(tool)
    return out


def sections_payload() -> list[dict]:
    grouped = by_section()
    payload = []
    for key, meta in SECTIONS.items():
        tools = grouped.get(key, [])
        payload.append(
            {
                "id": key,
                "title": meta["title"],
                "icon": meta["icon"],
                "purpose": meta["purpose"],
                "count": len(tools),
                "tools": [
                    {
                        "name": t.name,
                        "binary": t.binary,
                        "package": t.package,
                        "summary": t.summary,
                        "intrusive": t.intrusive,
                        "offline": t.offline,
                        "install_hint": t.install_hint,
                        "flags": t.flags,
                        "example": t.example,
                        "installed": False,
                    }
                    for t in tools
                ],
            }
        )
    return payload


TOTAL_TOOLS = len(TOOLS)
INTRUSIVE_COUNT = sum(1 for t in TOOLS.values() if t.intrusive)
