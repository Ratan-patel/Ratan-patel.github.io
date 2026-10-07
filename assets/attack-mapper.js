/* ============================================================================
   RATAN_PATEL.SEC — MITRE ATT&CK Mapper & Coverage Cockpit
   Alignment: MITRE ATT&CK Enterprise v19 (Stealth / Defense Impairment split)
   Runs entirely client-side. Nothing is transmitted anywhere.
   Curated technique subset — verify IDs against attack.mitre.org before shipping
   detection-as-code. See mitre-attack-mapper.html for the accuracy note.
   ============================================================================ */
(function () {
  "use strict";

  /* ----------------------------- TACTICS ---------------------------------- */
  /* Order = attacker kill-chain order, used to prioritise the gap list.      */
  var TACTICS = [
    { k: "RECON",     id: "TA0043", n: "Reconnaissance" },
    { k: "RESDEV",    id: "TA0042", n: "Resource Development" },
    { k: "INITIAL",   id: "TA0001", n: "Initial Access" },
    { k: "EXEC",      id: "TA0002", n: "Execution" },
    { k: "PERSIST",   id: "TA0003", n: "Persistence" },
    { k: "PRIVESC",   id: "TA0004", n: "Privilege Escalation" },
    { k: "STEALTH",   id: "TA0005", n: "Stealth" },
    { k: "IMPAIR",    id: "TA0112", n: "Defense Impairment" },
    { k: "CRED",      id: "TA0006", n: "Credential Access" },
    { k: "DISCOVERY", id: "TA0007", n: "Discovery" },
    { k: "LATERAL",   id: "TA0008", n: "Lateral Movement" },
    { k: "COLLECTION",id: "TA0009", n: "Collection" },
    { k: "C2",        id: "TA0011", n: "Command and Control" },
    { k: "EXFIL",     id: "TA0010", n: "Exfiltration" },
    { k: "IMPACT",    id: "TA0040", n: "Impact" }
  ];

  /* --------------------------- TECHNIQUES --------------------------------- */
  /* t(id, name, tacticKey, detectionTelemetryHint, legacyId)                  */
  var TECHNIQUES = [];
  function t(id, name, tac, hint, legacy) {
    TECHNIQUES.push({ id: id, n: name, tac: tac, hint: hint || "", legacy: legacy || "" });
  }

  /* Reconnaissance */
  t("T1595", "Active Scanning", "RECON", "edge/IDS scan traffic, perimeter firewall deny logs");
  t("T1595.002", "Vulnerability Scanning", "RECON", "WAF + IDS signatures, user-agent and path anomalies");
  t("T1592", "Gather Victim Host Information", "RECON", "honeypot interactions, DNS/CT logs, recruitment-site scraping");
  t("T1589", "Gather Victim Identity Information", "RECON", "breach-corpus monitoring, credential-stuffing traffic");
  t("T1590", "Gather Victim Network Information", "RECON", "DNS zone-transfer attempts, WHOIS/ASN lookups, CT logs");
  t("T1591", "Gather Victim Org Information", "RECON", "OSINT monitoring, lookalike-domain registration feeds");
  t("T1598", "Phishing for Information", "RECON", "mail-gateway reply anomalies, credential-harvest page hits");
  t("T1596", "Search Open Technical Databases", "RECON", "Shodan/Censys-style scans of owned ranges");
  t("T1593", "Search Open Websites/Domains", "RECON", "social-media and code-repo scraping of employee data");
  t("T1594", "Search Victim-Owned Websites", "RECON", "web-server logs: directory brute force, sitemap crawling");

  /* Resource Development */
  t("T1583", "Acquire Infrastructure", "RESDEV", "lookalike-domain registration, new-ASN infrastructure monitoring");
  t("T1584", "Compromise Infrastructure", "RESDEV", "third-party compromise reports, malicious-resolver feeds");
  t("T1585", "Establish Accounts", "RESDEV", "new-account signup abuse, disposable-email detection");
  t("T1586", "Compromise Accounts", "RESDEV", "identity-provider impossible-travel, session-token anomalies");
  t("T1587", "Develop Capabilities", "RESDEV", "malware-family intelligence, code-repo monitoring");
  t("T1588", "Obtain Capabilities", "RESDEV", "dark-web marketplace intelligence, CVE-exploit correlation");
  t("T1608", "Stage Capabilities", "RESDEV", "newly-seen hosting delivering payloads, TLS cert pivots");

  /* Initial Access */
  t("T1566", "Phishing", "INITIAL", "mail gateway verdicts, attachment detonation, external sender rules");
  t("T1566.001", "Spearphishing Attachment", "INITIAL", "mail attachment types, macro enablement, child-process from Office");
  t("T1566.002", "Spearphishing Link", "INITIAL", "URL rewriting click logs, gateway time-of-click verdicts");
  t("T1566.003", "Spearphishing via Service", "INITIAL", "third-party messaging connectors, social-platform link telemetry");
  t("T1190", "Exploit Public-Facing Application", "INITIAL", "web-server 4xx/5xx bursts, WAF blocks, unexpected child processes from web service accounts");
  t("T1133", "External Remote Services", "INITIAL", "VPN/RDP gateway auth logs, impossible travel, off-hours logons");
  t("T1078", "Valid Accounts", "INITIAL", "identity logs: anomalous geolocation, MFA fatigue, impossible travel");
  t("T1189", "Drive-by Compromise", "INITIAL", "browser exploitation telemetry, malicious ad-network blocks");
  t("T1195", "Supply Chain Compromise", "INITIAL", "software-integrity monitoring, vendor update-channel anomalies");
  t("T1199", "Trusted Relationship", "INITIAL", "third-party SSO and federation audit logs; unusual MSP access");
  t("T1200", "Hardware Additions", "INITIAL", "USB device-connection telemetry, endpoint device-control logs");
  t("T1091", "Replication Through Removable Media", "INITIAL", "autorun events, write-then-launch patterns on removable media");

  /* Execution */
  t("T1059", "Command and Scripting Interpreter", "EXEC", "process creation with parent/child lineage; scripting engine invocation");
  t("T1059.001", "PowerShell", "EXEC", "Script Block Logging (4104), Module Logging, encoded-command flags");
  t("T1059.003", "Windows Command Shell", "EXEC", "cmd.exe child processes, unusual parent lineage, net.exe usage");
  t("T1059.004", "Unix Shell", "EXEC", "auditd execve records, shell spawned by web/app service accounts");
  t("T1059.005", "Visual Basic", "EXEC", "wscript/cscript execution, Office macro child processes");
  t("T1059.006", "Python", "EXEC", "python interpreter spawned by service accounts or web servers");
  t("T1204", "User Execution", "EXEC", "endpoint execution of user-downloaded files; browser-to-process lineage");
  t("T1204.001", "Malicious Link", "EXEC", "click-then-execute correlation, gateway verdict on final URL");
  t("T1204.002", "Malicious File", "EXEC", "Mark-of-the-Web inheritance, archive extraction then launch");
  t("T1203", "Exploitation for Client Execution", "EXEC", "crash-then-child-process sequences in Office, browser, PDF readers");
  t("T1047", "Windows Management Instrumentation", "EXEC", "WMI process-creation events, wmic/wmiprvse remote invocation");
  t("T1053", "Scheduled Task/Job", "EXEC", "Task Scheduler 4698/4702, schtasks.exe creation, crontab writes");
  t("T1053.005", "Scheduled Task", "EXEC", "Security 4698 plus task action path reputation");
  t("T1569.002", "Service Execution", "EXEC", "Service Control Manager 7045, sc.exe create, new service binary paths");
  t("T1072", "Software Deployment Tools", "EXEC", "SCCM/Intune deployment logs, admin-console remote script execution");
  t("T1106", "Native API", "EXEC", "EDR API-call telemetry, unusual direct syscall patterns");

  /* Persistence */
  t("T1547", "Boot or Logon Autostart Execution", "PERSIST", "Run-key, startup-folder and logon-script writes");
  t("T1547.001", "Registry Run Keys / Startup Folder", "PERSIST", "registry 13/14 events on Run keys, startup-folder file drops");
  t("T1136", "Create Account", "PERSIST", "Security 4720/4726, cloud directory user-creation audit logs");
  t("T1098", "Account Manipulation", "PERSIST", "group-membership changes, credential and consent-grant modifications");
  t("T1543", "Create or Modify System Process", "PERSIST", "new service installs, systemd unit writes, launchd plist creation");
  t("T1546", "Event Triggered Execution", "PERSIST", "WMI event subscriptions, AppInit DLLs, persistence via telemetry hooks");
  t("T1574", "Hijack Execution Flow", "PERSIST", "DLL search-order anomalies, PATH hijack, unquoted service paths");
  t("T1505.003", "Web Shell", "PERSIST", "web-server child processes, newly written script files in webroot, anomalous HTTP POST bodies");
  t("T1137", "Office Application Startup", "PERSIST", "Office add-in and template registry writes; outlook-load persistence");
  t("T1542", "Pre-OS Boot", "PERSIST", "bootloader/firmware integrity attestation, Secure Boot state changes");
  t("T1525", "Implant Internal Image", "PERSIST", "container-image provenance, unexpected image-layer modifications");
  t("T1078.004", "Valid Accounts: Cloud Accounts", "PERSIST", "new access keys, new device registrations, token-lifetime anomalies");

  /* Privilege Escalation */
  t("T1548", "Abuse Elevation Control Mechanism", "PRIVESC", "UAC prompts, sudo events, elevated-child-process lineage");
  t("T1548.002", "Bypass User Account Control", "PRIVESC", "process integrity-level jumps, elevated binaries from user-writable paths");
  t("T1134", "Access Token Manipulation", "PRIVESC", "token duplication API calls, process created with another user's token");
  t("T1068", "Exploitation for Privilege Escalation", "PRIVESC", "kernel-mode crash then SYSTEM process, unpatched local-exploit artefacts");
  t("T1055", "Process Injection", "PRIVESC", "remote thread creation, cross-process memory writes, EDR injection telemetry");
  t("T1484", "Domain Policy Modification", "PRIVESC", "GPO object modifications, SYSVOL writes, directory-service change events");
  t("T1611", "Escape to Host", "PRIVESC", "container escape syscalls, privileged-container runtime anomalies");
  t("T1546.004", "Unix Shell Configuration Modification", "PRIVESC", ".bashrc/.profile writes by non-owner accounts");
  t("T1574.006", "Dynamic Linker Hijacking", "PRIVESC", "LD_PRELOAD / DYLD_INSERT_LIBRARIES process environment anomalies");

  /* Stealth (TA0005, formerly Defense Evasion) */
  t("T1070", "Indicator Removal", "STEALTH", "log-source gaps, event-ID sequence breaks, file-deletion telemetry");
  t("T1070.001", "Clear Windows Event Logs", "STEALTH", "Security 1102 and System 104 — high-confidence, low-noise rule");
  t("T1070.003", "Clear Command History", "STEALTH", "history-file truncation, empty shell history with active sessions");
  t("T1070.004", "File Deletion", "STEALTH", "delete-then-immediate-exit patterns, mass deletion bursts");
  t("T1036", "Masquerading", "STEALTH", "binary-name/path reputation mismatch, mismatched file metadata");
  t("T1036.005", "Match Legitimate Name or Location", "STEALTH", "system-named binaries running from user-writable directories");
  t("T1027", "Obfuscated Files or Information", "STEALTH", "high-entropy command lines, encoded PowerShell, packed binaries");
  t("T1027.013", "Encrypted/Encoded File", "STEALTH", "base64-heavy arguments, decoder-then-execute lineage");
  t("T1218", "System Binary Proxy Execution", "STEALTH", "LOLBin invocation with remote/odd arguments; signed-binary network egress");
  t("T1218.011", "Rundll32", "STEALTH", "rundll32 with remote DLL or unusual export names");
  t("T1216", "System Script Proxy Execution", "STEALTH", "signed script hosts (mshta, wscript) fetching remote content");
  t("T1140", "Deobfuscate/Decode Files or Information", "STEALTH", "certutil/base64 decode sequences followed by execution");
  t("T1202", "Indirect Command Execution", "STEALTH", "forfiles/pcaluate-style proxy execution and command-history gaps");
  t("T1497", "Virtualization/Sandbox Evasion", "STEALTH", "sandbox-detection API calls, timing checks, VM artefact enumeration");
  t("T1620", "Reflective Code Loading", "STEALTH", "memory-only module loads with no file write — memory-scan telemetry");
  t("T1622", "Debugger Evasion", "STEALTH", "debugger-detection API usage, anti-analysis process inspection");
  t("T1222", "File and Directory Permissions Modification", "STEALTH", "icacls/chmod mass permission changes on sensitive paths");
  t("T1564.001", "Hidden Files and Directories", "STEALTH", "hidden-attribute file writes, dot-file persistence in home dirs");
  t("T1553", "Subvert Trust Controls", "STEALTH", "unsigned binaries with valid-looking metadata, cert-store writes");
  t("T1211", "Exploitation for Stealth", "STEALTH", "exploitation of security tooling itself; EDR process tampering", "T1211 = Exploitation for Defense Evasion pre-v19");
  t("T1480", "Execution Guardrails", "STEALTH", "environment-key checks, geo/time gates before payload runs");
  t("T1014", "Rootkit", "STEALTH", "kernel-module integrity, hidden-process detection, bootkit attestation");
  t("T1578", "Modify Cloud Compute Configurations", "STEALTH", "cloud API calls creating/exposing instances for staging");

  /* Defense Impairment (TA0112 — new tactic in v19) */
  t("T1685", "Disable or Modify Tools", "IMPAIR", "security-service stop events, EDR sensor tamper alerts, uninstall attempts", "T1562.001 + T1562.006 merged here in v19");
  t("T1687", "Exploitation for Defense Impairment", "IMPAIR", "vulnerability exploitation targeting the security stack itself");
  t("T1686.003", "Disable or Modify System Firewall: Windows Host Firewall", "IMPAIR", "netsh advfirewall changes, firewall service stopped, rule deletions");
  t("T1562.002", "Impair Defenses: Disable Windows Event Logging", "IMPAIR", "audit-policy changes (4719), log-service stop events");
  t("T1562.008", "Impair Defenses: Disable or Modify Cloud Logs", "IMPAIR", "CloudTrail/audit-log stop or delete API calls");
  t("T1562.010", "Impair Defenses: Downgrade Attack", "IMPAIR", "protocol-downgrade negotiation, weaker-auth fallback events");

  /* Credential Access */
  t("T1110", "Brute Force", "CRED", "failed-auth velocity, account lockout spikes, source-IP clustering");
  t("T1110.003", "Password Spraying", "CRED", "many accounts, few attempts each, single source — identity-provider analytics");
  t("T1003", "OS Credential Dumping", "CRED", "LSASS access by non-approved processes — the classic high-signal rule");
  t("T1003.001", "LSASS Memory", "CRED", "handle requests to lsass.exe, credential-dump drivers loaded");
  t("T1003.002", "Security Account Manager", "CRED", "SAM/SECURITY registry hive reads, shadow-copy abuse");
  t("T1003.003", "NTDS", "CRED", "ntds.dit access, volume-shadow-copy creation on domain controllers");
  t("T1555", "Credentials from Password Stores", "CRED", "browser credential-store file access, DPAPI blob decryption");
  t("T1056.001", "Keylogging", "CRED", "keyboard-input hooks, SetWindowsHookEx from unexpected processes");
  t("T1552", "Unsecured Credentials", "CRED", "secret-file and environment-variable reads, cloud metadata-service queries");
  t("T1557", "Adversary-in-the-Middle", "CRED", "ARP/DNS spoofing indicators, rogue-relay authentication, NTLM relay patterns");
  t("T1558.003", "Kerberoasting", "CRED", "4769 with RC4 encryption in bulk — well-supported detection in most SIEMs");
  t("T1621", "Multi-Factor Authentication Request Generation", "CRED", "MFA prompt flooding, repeated denied push notifications");
  t("T1528", "Steal Application Access Token", "CRED", "OAuth token reuse from new user agents, impossible token provenance");
  t("T1550.002", "Pass the Hash", "CRED", "NTLM authentication without prior interactive logon; lateral auth anomalies");
  t("T1539", "Steal Web Session Cookie", "CRED", "session-cookie reuse from a new IP/device without re-authentication");

  /* Discovery */
  t("T1087", "Account Discovery", "DISCOVERY", "net user/Get-ADUser enumeration bursts, directory-query rate spikes");
  t("T1018", "Remote System Discovery", "DISCOVERY", "net view/nltest sweeps, LDAP computer-object enumeration");
  t("T1082", "System Information Discovery", "DISCOVERY", "systeminfo/wmic queries, host-profiling command sequences");
  t("T1083", "File and Directory Discovery", "DISCOVERY", "recursive directory listing bursts, dir /s, find over shares");
  t("T1046", "Network Service Discovery", "DISCOVERY", "internal port-scan patterns, Nmap/masscan signatures on the wire");
  t("T1057", "Process Discovery", "DISCOVERY", "tasklist/ps enumeration, security-tool discovery by process name");
  t("T1012", "Query Registry", "DISCOVERY", "bulk registry reads, reg query against security-relevant keys");
  t("T1016", "System Network Configuration Discovery", "DISCOVERY", "ipconfig/ifconfig/route enumeration bursts");
  t("T1033", "System Owner/User Discovery", "DISCOVERY", "whoami/query user commands in scripted sequences");
  t("T1049", "System Network Connections Discovery", "DISCOVERY", "netstat/Get-NetTCPConnection enumeration for pivot targets");
  t("T1069", "Permission Groups Discovery", "DISCOVERY", "group-membership enumeration, high-privilege group queries");
  t("T1518", "Software Discovery", "DISCOVERY", "installed-software inventory queries, security-product enumeration");
  t("T1201", "Password Policy Discovery", "DISCOVERY", "net accounts / domain-policy reads preceding spray attempts");
  t("T1482", "Domain Trust Discovery", "DISCOVERY", "nltest /domain_trusts, trust-enumeration LDAP queries");
  t("T1538", "Cloud Service Dashboard", "DISCOVERY", "cloud console enumeration APIs, resource-listing bursts");
  t("T1654", "Log Enumeration", "DISCOVERY", "queries against SIEM/log APIs from unusual identities");

  /* Lateral Movement */
  t("T1021", "Remote Services", "LATERAL", "remote-session auth logs, source/target pair baselines");
  t("T1021.001", "Remote Desktop Protocol", "LATERAL", "RDP 4624 type 10, new source pairs, RDP from workstations to servers");
  t("T1021.002", "SMB/Windows Admin Shares", "LATERAL", "admin-share access 5140/5145, PsExec-style service creation");
  t("T1021.003", "DCOM", "LATERAL", "DCOM object instantiation, MMC20/ShellWindows abuse telemetry");
  t("T1021.004", "SSH", "LATERAL", "SSH key reuse across hosts, new key fingerprints, agent forwarding");
  t("T1021.006", "Windows Remote Management", "LATERAL", "WinRM 91/WSMan connection events, remote PowerShell sessions");
  t("T1210", "Exploitation of Remote Services", "LATERAL", "exploit-then-new-session sequences on internal services");
  t("T1570", "Lateral Tool Transfer", "LATERAL", "file writes to admin shares, copy utilities with internal destinations");
  t("T1563", "Remote Session Hijacking", "LATERAL", "session takeover events, RDP session shadowing abuse");
  t("T1080", "Taint Shared Content", "LATERAL", "writes to shared drives/templates by non-owners, shared-macro modifications");

  /* Collection */
  t("T1005", "Data from Local System", "COLLECTION", "mass file reads, archiving utilities on user-data directories");
  t("T1039", "Data from Network Shared Drive", "COLLECTION", "bulk share enumeration plus copy-out volume anomalies");
  t("T1074.001", "Local Data Staging", "COLLECTION", "archive creation in temp paths, staging-directory write bursts");
  t("T1113", "Screen Capture", "COLLECTION", "screenshot API calls from unexpected processes");
  t("T1115", "Clipboard Data", "COLLECTION", "clipboard-access API usage by non-interactive processes");
  t("T1114", "Email Collection", "COLLECTION", "mailbox-rule creation, bulk mailbox export, forwarding rules to external domains");
  t("T1119", "Automated Collection", "COLLECTION", "scripted collection patterns on a fixed schedule");
  t("T1213", "Data from Information Repositories", "COLLECTION", "bulk wiki/SharePoint/Jira export API calls");
  t("T1530", "Data from Cloud Storage", "COLLECTION", "mass object-download API calls, storage-access anomalies");
  t("T1185", "Browser Session Hijacking", "COLLECTION", "remote-debugging port abuse, browser-profile theft");

  /* Command and Control */
  t("T1071", "Application Layer Protocol", "C2", "beacon-shaped HTTP(S) traffic: fixed intervals with jitter");
  t("T1071.001", "Web Protocols", "C2", "non-browser JA3/JA4 to unusual endpoints, long-lived POST sessions");
  t("T1071.004", "DNS", "C2", "high-volume TXT/NXDOMAIN patterns, DNS-tunnelling length entropy");
  t("T1095", "Non-Application Layer Protocol", "C2", "raw TCP/UDP sessions to external hosts, ICMP payload anomalies");
  t("T1573", "Encrypted Channel", "C2", "self-signed certificates, JA3/JA4 mismatch, no SNI on TLS");
  t("T1572", "Protocol Tunneling", "C2", "protocol-wrapped tunnelling, unusual SSH port forwards");
  t("T1090", "Proxy", "C2", "internal proxies, egress via a small set of external relays");
  t("T1090.003", "Multi-hop Proxy", "C2", "TOR exit-node contact, chained-proxy latency fingerprints");
  t("T1090.004", "Domain Fronting", "C2", "SNI/Host header mismatch on TLS to CDN ranges");
  t("T1105", "Ingress Tool Transfer", "C2", "download activity from newly-seen hosts, direct IP fetching");
  t("T1102", "Web Service", "C2", "beaconing to legitimate SaaS APIs (paste sites, cloud storage, IM)");
  t("T1205", "Traffic Signaling", "C2", "port-knock patterns, magic-packet wake-ups on filtered ports");
  t("T1568", "Dynamic Resolution", "C2", "fast-flux DNS rotation, short-TTL record churn");
  t("T1568.002", "Domain Generation Algorithms", "C2", "NXDOMAIN bursts with high-entropy subdomains — strong DNS rule");
  t("T1132", "Data Encoding", "C2", "base64/hex payload shaping inside otherwise normal protocols");
  t("T1001", "Data Obfuscation", "C2", "protocol steganography, padding to fixed message sizes");

  /* Exfiltration */
  t("T1041", "Exfiltration Over C2 Channel", "EXFIL", "egress volume spike on an existing C2 session");
  t("T1048", "Exfiltration Over Alternative Protocol", "EXFIL", "large transfers over FTP/ICMP/DNS that bypass web controls");
  t("T1567", "Exfiltration Over Web Service", "EXFIL", "uploads to personal cloud storage, paste sites, file-transfer services");
  t("T1567.002", "Exfiltration to Cloud Storage", "EXFIL", "bulk object PUT to external buckets, sync-client anomalies");
  t("T1029", "Scheduled Transfer", "EXFIL", "fixed-interval egress transfers, off-hours data movement");
  t("T1030", "Data Transfer Size Limits", "EXFIL", "many small uniform transfers that each stay under quota alerts");
  t("T1052", "Exfiltration Over Physical Medium", "EXFIL", "removable-media writes of archive files, USB mass-storage events");
  t("T1537", "Transfer Data to Cloud Account", "EXFIL", "cross-account cloud snapshot and storage sharing operations");
  t("T1011", "Exfiltration Over Other Network Medium", "EXFIL", "cellular/Wi-Fi bridging devices, out-of-band egress paths");

  /* Impact */
  t("T1486", "Data Encrypted for Impact", "IMPACT", "mass file rename/entropy change, shadow-copy deletion, ransom-note drops");
  t("T1485", "Data Destruction", "IMPACT", "mass overwrite/delete operations, storage-level wipe commands");
  t("T1489", "Service Stop", "IMPACT", "bulk service-stop events, database/backup agent termination");
  t("T1490", "Inhibit System Recovery", "IMPACT", "vssadmin delete shadows, backup-catalogue deletion — very high signal");
  t("T1491", "Defacement", "IMPACT", "unexpected webroot file modifications, index-page hash change alerts");
  t("T1498", "Network Denial of Service", "IMPACT", "traffic-volume anomalies, upstream scrubbing triggers");
  t("T1499", "Endpoint Denial of Service", "IMPACT", "resource-exhaustion spikes on endpoints, hung-service storms");
  t("T1529", "System Shutdown/Reboot", "IMPACT", "unexpected mass shutdown events, boot-configuration tampering");
  t("T1561.001", "Disk Content Wipe", "IMPACT", "raw-disk write access, boot-sector modification");
  t("T1496", "Resource Hijacking", "IMPACT", "sustained CPU/GPU saturation, mining-pool network connections");
  t("T1657", "Financial Theft", "IMPACT", "payment-profile changes, invoice-fraud mailbox rules, wire-fraud indicators");
  t("T1531", "Account Access Removal", "IMPACT", "mass password resets and account lock/disable events");

  /* ------------------------------ SYNONYMS -------------------------------- */
  /* Practitioners search in tool names and jargon, not ATT&CK vocabulary.
     "kerberos" must find Kerberoasting; "mimikatz" must find LSASS Memory.
     These strings are folded into the search haystack only.               */
  var SYN = {
    "T1003": "mimikatz sekurlsa credential dumping lsass sam ntds hashdump secretsdump",
    "T1003.001": "mimikatz lsass dump procdump comsvcs minidump lsadump",
    "T1003.002": "sam hive hashdump registry hive secrets",
    "T1003.003": "ntds dit dcsync domain controller hashes secretsdump",
    "T1558": "kerberos golden ticket silver ticket ms14-068 governance",
    "T1558.003": "kerberos spn service ticket roasting rc4 tgs",
    "T1550.002": "pass the hash pth ntlm overpass relay",
    "T1550": "pass the ticket alternate authentication ptt golden",
    "T1482": "kerberos trust nltest domain trusts enumeration",
    "T1059.001": "powershell ps1 psscriptblock encoded command amsi empire",
    "T1059.003": "cmd batch bat net shell",
    "T1059.005": "vba visual basic macro office",
    "T1047": "wmi wmic wmiprvse impacket",
    "T1021.001": "rdp remote desktop mstsc terminal server",
    "T1021.002": "smb psexec admin share cifs impacket",
    "T1021.004": "ssh scp sftp key",
    "T1021.006": "winrm wsman powershell remoting evil-winrm",
    "T1547.001": "run key registry persistence autoruns startup",
    "T1053.005": "schtasks scheduled task task scheduler at cron",
    "T1053": "scheduled task cron at systemd timer",
    "T1505.003": "webshell web shell aspx php jsp china chopper",
    "T1068": "local privilege escalation lpe kernel exploit cve",
    "T1548.002": "uac bypass user account control fodhelper",
    "T1055": "process injection dll injection hollowing reflective apc",
    "T1134": "token impersonation steal token potato",
    "T1218": "lolbin lolbas proxy execution signed binary",
    "T1218.011": "rundll32 dll export",
    "T1140": "decode certutil base64 obfuscation",
    "T1140x": "",
    "T1027": "obfuscation encoded packed encrypted evasion",
    "T1070.001": "clear logs event log wevtutil 1102 anti-forensics",
    "T1564.001": "hidden file attrib hide artifact",
    "T1553": "signature subvert code signing certificate",
    "T1014": "rootkit kernel bootkit",
    "T1497": "sandbox evasion vm detection anti-analysis",
    "T1071.001": "http https beacon web c2 cobalt sliver",
    "T1071.004": "dns tunnel exfil iodine dnscat c2",
    "T1573": "tls encryption cipher channel certificate",
    "T1090.003": "proxy tor multi-hop relay",
    "T1090.004": "domain fronting cdn fastly cloudfront",
    "T1105": "download ingress tool transfer curl wget certutil bits",
    "T1102": "web service dropbox pastebin telegram slack discord dead drop",
    "T1568.002": "dga domain generation algorithm",
    "T1071": "application layer protocol c2 beacon",
    "T1041": "exfil over c2 channel upload",
    "T1048": "exfil alternative protocol ftp icmp dns",
    "T1567.002": "exfil cloud storage s3 dropbox mega gdrive",
    "T1486": "ransomware encrypt encryption locked ransomware note",
    "T1490": "delete shadow copies vssadmin inhibit recovery wbadmin",
    "T1485": "wiper destroy data destruction",
    "T1496": "cryptomining miner xmrig resource hijacking",
    "T1657": "wire fraud bec business email compromise invoice",
    "T1566": "phishing email spearphishing mail",
    "T1566.001": "attachment macro invoice docm xlsm",
    "T1566.002": "link url credential harvest",
    "T1190": "exploit public facing web app cve vulnerability",
    "T1133": "vpn rdp external remote citrix pulse",
    "T1078": "valid accounts credential abuse default password",
    "T1078.004": "cloud account azure aws gcp access key",
    "T1110.003": "password spray spraying lockout",
    "T1110": "brute force guessing hydra",
    "T1621": "mfa fatigue push bombing prompt",
    "T1539": "session cookie token theft aitm",
    "T1557": "aitm relay ntlm relay responder arp spoof",
    "T1555": "password store browser credential vault keychain dpapi",
    "T1552": "unsecured credentials secrets env file metadata imds",
    "T1528": "oauth token application access steal",
    "T1098": "account manipulation consent grant role assignment persistence",
    "T1136": "create account backdoor user add",
    "T1543": "service systemd launchd persistence",
    "T1574": "dll hijack search order path hijack dylib",
    "T1546": "event triggered wmi subscription appinit",
    "T1046": "port scan nmap network discovery masscan",
    "T1087": "account enumeration net user aduser",
    "T1018": "remote system discovery net view arp",
    "T1082": "systeminfo host recon os discovery",
    "T1083": "file discovery dir listing find",
    "T1012": "registry query reg enum",
    "T1057": "process discovery tasklist ps",
    "T1482x": "",
    "T1685": "disable edr antivirus defender tamper kill av",
    "T1686.003": "firewall netsh disable defender port",
    "T1562.002": "event log disable audit policy tamper",
    "T1687": "exploit security tool edr vulnerability",
    "T1562.008": "cloudtrail disable logging cloud audit",
    "T1113": "screenshot screen capture",
    "T1115": "clipboard copy",
    "T1114": "email collection mailbox forward rule",
    "T1530": "cloud storage bucket s3 blob collection",
    "T1213": "sharepoint confluence jira wiki collection",
    "T1185": "browser session hijack cookie stealer",
    "T1074.001": "staging archive zip rar collect",
    "T1005": "local data collection file grab",
    "T1039": "network share collection smb",
    "T1029": "scheduled transfer timed exfil",
    "T1030": "size limits chunked exfil",
    "T1052": "usb removable media physical exfil",
    "T1537": "cloud account transfer snapshot share",
    "T1489": "service stop kill database backup",
    "T1491": "defacement website deface",
    "T1498": "ddos denial of service network flood",
    "T1499": "endpoint dos resource exhaustion",
    "T1529": "shutdown reboot",
    "T1561.001": "disk wipe overwrite mbr",
    "T1531": "account access removal lockout disable",
    "T1542": "pre-os boot firmware uefi bootkit",
    "T1525": "container image implant docker",
    "T1611": "container escape host breakout",
    "T1578": "cloud compute modify instance",
    "T1595": "scanning active port scan recon",
    "T1595.002": "vulnerability scan nuclei nessus",
    "T1195": "supply chain compromise vendor software",
    "T1199": "trusted relationship msp third party vendor",
    "T1200": "hardware additions usb implant",
    "T1091": "removable media usb autorun",
    "T1203": "client exploitation browser office pdf exploit",
    "T1204": "user execution click open",
    "T1569.002": "service execution sc create psexec",
    "T1222": "permissions chmod icacls acl",
    "T1480": "execution guardrails environment key gate",
    "T1620": "reflective loading in-memory memory only",
    "T1654": "log enumeration siem query"
  };

  /* ---------------------- v19 AI & SOCIAL-ENGINEERING --------------------- */
  /* Listed separately: v19 added these as new coverage. Tactic placement for */
  /* brand-new entries is still settling in the release, so this tool does    */
  /* not assert a column for them. Verify on attack.mitre.org.               */
  var V19_ADDITIONS = [
    { id: "T1684", n: "Social Engineering", d: "New parent technique absorbing impersonation and spoofing behaviour that was previously scattered across Initial Access." },
    { id: "T1684.001", n: "Impersonation", d: "Adversary presents as a trusted person or brand. Detection lives in mail-gateway header analysis and helpdesk procedural controls, not in endpoint logs." },
    { id: "T1684.002", n: "Email Spoofing", d: "Forged sender identity. Detection: SPF/DKIM/DMARC failure correlation with inbound volume." },
    { id: "T1682", n: "Query Public AI Services", d: "Adversaries querying public AI services during operations — reconnaissance and target research at scale. Detection is mostly egress policy and SaaS-usage governance." },
    { id: "T1683", n: "Generate Content", d: "AI-generated lure content at volume. Detection is quality-of-writing heuristics and campaign clustering, not signatures." }
  ];

  /* --------------------------- ADVERSARY PROFILES -------------------------- */
  /* Well-documented, publicly-mapped tradecraft. Technique lists are curated  */
  /* to this tool's dataset rather than exhaustive ATT&CK mappings.           */
  var PROFILES = {
    "APT29": {
      group: "G0016",
      blurb: "State-sponsored espionage. Quiet, identity-centric, long dwell time. Prioritise credential access, cloud persistence, stealth.",
      tech: ["T1583","T1585","T1566.001","T1566.002","T1195","T1199","T1078","T1078.004","T1059.001","T1059.003","T1047","T1547.001","T1098","T1136","T1078.004","T1003.001","T1552","T1528","T1110.003","T1087","T1018","T1082","T1012","T1021.001","T1021.002","T1021.006","T1071.001","T1071.004","T1573","T1090.003","T1102","T1005","T1114","T1567.002","T1070.001","T1070.004","T1036","T1027","T1027.013","T1218.011","T1620","T1497","T1564.001","T1553","T1685"]
    },
    "Lazarus Group": {
      group: "G0032",
      blurb: "Financially and strategically motivated. Supply-chain interest, cryptocurrency theft, destructive capability.",
      tech: ["T1595","T1595.002","T1583","T1189","T1566.002","T1204.001","T1204.002","T1059.001","T1059.004","T1059.006","T1203","T1543","T1546","T1574","T1134","T1055","T1003","T1003.001","T1056.001","T1555","T1113","T1115","T1071.001","T1071.004","T1105","T1102","T1090.003","T1568.002","T1041","T1048","T1567","T1496","T1485","T1486","T1027","T1140","T1218","T1216","T1620","T1553","T1480","T1562.002","T1685"]
    },
    "Scattered Spider": {
      group: "G1015",
      blurb: "Social engineering first. Helpdesk impersonation, MFA fatigue, identity-provider abuse, fast extortion timeline.",
      tech: ["T1585","T1586","T1566","T1566.003","T1598","T1133","T1078","T1078.004","T1621","T1528","T1539","T1098","T1136","T1110.003","T1003.001","T1078.004","T1059.001","T1059.003","T1053.005","T1569.002","T1021.001","T1021.002","T1021.006","T1570","T1087","T1069","T1083","T1538","T1114","T1213","T1530","T1071.001","T1102","T1041","T1567.002","T1486","T1490","T1489","T1491","T1657","T1531","T1036.005","T1070","T1685","T1562.008"]
    },
    "Volt Typhoon": {
      group: "G1017",
      blurb: "Living-off-the-land espionage against critical infrastructure. Almost no malware: built-in tools, valid accounts, long pre-positioning.",
      tech: ["T1595","T1190","T1133","T1078","T1078.004","T1059.003","T1047","T1059.001","T1106","T1053.005","T1098","T1134","T1003","T1003.002","T1003.003","T1552","T1012","T1018","T1082","T1083","T1046","T1057","T1016","T1049","T1033","T1518","T1021.001","T1021.002","T1021.006","T1570","T1005","T1074.001","T1530","T1071.001","T1090.001","T1095","T1105","T1041","T1567","T1560", "T1036","T1218","T1202","T1070.004","T1564.001","T1014","T1562.002","T1685","T1686.003"]
    },
    "APT41": {
      group: "G0096",
      blurb: "Dual-purpose: espionage plus financially motivated crime. Aggressive supply-chain and web-facing exploitation.",
      tech: ["T1595","T1595.002","T1190","T1195","T1566.001","T1189","T1078","T1059.001","T1059.003","T1059.005","T1059.006","T1204.002","T1203","T1505.003","T1543","T1546","T1574","T1134","T1055","T1003.001","T1003.003","T1555","T1056.001","T1552","T1087","T1018","T1082","T1083","T1046","T1021.001","T1021.002","T1021.004","T1570","T1005","T1039","T1074.001","T1113","T1071.001","T1095","T1105","T1205","T1568.002","T1041","T1048","T1567.002","T1486","T1485","T1490","T1496","T1027","T1027.013","T1140","T1218.011","T1620","T1497","T1036","T1070.001","T1070.004","T1553","T1685"]
    },
    "Ransomware (double extortion)": {
      group: "composite",
      blurb: "Composite profile from documented big-game-hunting operations: initial access broker entry, fast lateral movement, exfil-then-encrypt.",
      tech: ["T1133","T1190","T1566.001","T1078","T1059.001","T1059.003","T1047","T1569.002","T1543","T1484","T1134","T1003.001","T1003.002","T1003.003","T1555","T1552","T1110.003","T1018","T1082","T1083","T1046","T1021.001","T1021.002","T1570","T1005","T1039","T1074.001","T1560","T1071.001","T1105","T1090.003","T1572","T1132","T1041","T1048","T1567.002","T1490","T1486","T1489","T1485","T1491","T1657","T1529","T1561.001","T1070","T1070.001","T1070.004","T1036.005","T1027","T1218","T1480","T1685","T1686.003","T1562.002"]
    }
  };

  /* -------------------------------- STATE --------------------------------- */
  var KEY = "ratan.attack.mapper.v1";
  var STATUS_LABEL = ["Unassessed", "Gap", "Partial", "Covered"];
  var state = { st: {}, tactic: "", filter: "all", q: "", profile: "" };
  var byId = {};
  TECHNIQUES.forEach(function (x) { byId[x.id] = x; });

  /* --------------------------------- UTILS -------------------------------- */
  function $(s, r) { return (r || document).querySelector(s); }
  function el(tag, cls, txt) {
    var e = document.createElement(tag);
    if (cls) e.className = cls;
    if (txt != null) e.textContent = txt;
    return e;
  }
  function esc(s) {
    return String(s).replace(/[&<>"']/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
    });
  }
  function toast(msg) {
    var n = $("#toast");
    n.textContent = msg;
    n.classList.add("on");
    clearTimeout(toast._t);
    toast._t = setTimeout(function () { n.classList.remove("on"); }, 2100);
  }
  function statusOf(id) { return state.st[id] || 0; }

  /* Search: exact substring first, then all query tokens must appear somewhere
     in the haystack (name + ID + telemetry hint + tactic + synonyms). This is
     what makes "delete shadow copies" find T1490 and "mimikatz" find T1003.001. */
  function matchQuery(hay, name, q) {
    if (hay.indexOf(q) !== -1) return true;
    var tokens = q.split(/\s+/).filter(function (t) { return t.length > 1; });
    if (tokens.length < 2) return false;
    return tokens.every(function (tk) { return hay.indexOf(tk) !== -1; });
  }

  /* ------------------------------ PERSISTENCE ----------------------------- */
  function save() {
    try { localStorage.setItem(KEY, JSON.stringify({ st: state.st, profile: state.profile })); } catch (e) {}
  }
  function load() {
    try {
      var raw = localStorage.getItem(KEY);
      if (!raw) return;
      var d = JSON.parse(raw);
      if (d && d.st && typeof d.st === "object") state.st = d.st;
      if (d && d.profile) { state.profile = d.profile; }
    } catch (e) {}
  }

  /* -------------------------------- METRICS ------------------------------- */
  var ORDER = {};
  TACTICS.forEach(function (x, i) { ORDER[x.k] = i; });

  function inScope() {
    return TECHNIQUES.filter(function (x) {
      var s = statusOf(x.id);
      if (state.filter === "assessed" && s === 0) return false;
      if (state.filter === "open" && s !== 1 && s !== 2) return false;
      if (state.filter === "unassessed" && s !== 0) return false;
      if (state.tactic && x.tac !== state.tactic) return false;
      if (state.q) {
        var hay = (x.id + " " + x.n + " " + x.hint + " " + tacName(x.tac) + " " + (SYN[x.id] || "")).toLowerCase();
        if (!matchQuery(hay, x.n, state.q)) return false;
      }
      return true;
    });
  }
  function tacName(k) {
    for (var i = 0; i < TACTICS.length; i++) if (TACTICS[i].k === k) return TACTICS[i].n;
    return k;
  }
  function metrics(list) {
    var m = { total: list.length, cov: 0, part: 0, gap: 0, un: 0, pct: 0 };
    list.forEach(function (x) {
      var s = statusOf(x.id);
      if (s === 3) m.cov++; else if (s === 2) m.part++; else if (s === 1) m.gap++; else m.un++;
    });
    if (m.total) m.pct = Math.round(((m.cov + m.part * 0.5) / m.total) * 100);
    return m;
  }

  /* -------------------------------- RENDER -------------------------------- */
  function renderDash() {
    var all = TECHNIQUES;
    var m = metrics(all);
    $("#k-pct").textContent = m.pct + "%";
    $("#k-covered").textContent = m.cov;
    $("#k-partial").textContent = m.part;
    $("#k-gap").textContent = m.gap;
    $("#k-total").textContent = m.total;
  }

  function renderMatrix() {
    var wrap = $("#matrix");
    wrap.innerHTML = "";
    var list = inScope();

    TACTICS.forEach(function (T) {
      var items = list.filter(function (x) { return x.tac === T.k; });
      if (state.tactic && state.tactic !== T.k) return;
      if ((state.filter !== "all" || state.q) && !items.length) return;

      var col = el("section", "tac" + (state.tactic === T.k ? " focus" : ""));
      col.setAttribute("aria-label", T.n + " tactic");

      var m = metrics(TECHNIQUES.filter(function (x) { return x.tac === T.k; }));
      var hd = el("div", "tac-hd");
      hd.appendChild(el("div", "tid", T.id));
      hd.appendChild(el("h3", null, T.n));
      var meta = el("div", "tmeta");
      meta.appendChild(el("span", null, m.cov + m.part + "/" + m.total + " assessed"));
      meta.appendChild(el("span", null, m.pct + "%"));
      hd.appendChild(meta);
      var bar = el("div", "covbar" + (m.pct < 40 ? " tan" : ""));
      var fill = el("i");
      fill.style.width = m.pct + "%";
      bar.appendChild(fill);
      hd.appendChild(bar);
      col.appendChild(hd);

      var body = el("div", "tac-body");
      var all = TECHNIQUES.filter(function (x) { return x.tac === T.k; });
      var shown = items.length ? items : all;
      shown.forEach(function (x) { body.appendChild(techButton(x)); });
      if (!shown.length) body.appendChild(el("div", "empty", "No techniques match the filter."));
      col.appendChild(body);
      wrap.appendChild(col);
    });

    if (!wrap.children.length) {
      wrap.appendChild(el("div", "empty", "Nothing matches this filter. Clear the search or choose a different view."));
    }
    renderBars();
    renderGaps();
  }

  function techButton(x) {
    var s = statusOf(x.id);
    var b = el("button", "tech");
    b.type = "button";
    b.dataset.st = s;
    b.dataset.legacy = x.legacy ? "1" : "";
    b.dataset.id = x.id;
    b.title = x.n + " — " + STATUS_LABEL[s] + (x.hint ? "\nTelemetry: " + x.hint : "") + "\n\nClick to change status";
    b.setAttribute("aria-label", x.id + " " + x.n + ", status " + STATUS_LABEL[s]);

    var c = el("span", "code", (x.legacy ? "◆ " : "") + x.id);
    var n = el("span", "nm");
    if (state.q) {
      var low = x.n.toLowerCase(), qi = low.indexOf(state.q);
      if (qi > -1) {
        n.appendChild(document.createTextNode(x.n.slice(0, qi)));
        var mk = el("mark", null, x.n.slice(qi, qi + state.q.length));
        n.appendChild(mk);
        n.appendChild(document.createTextNode(x.n.slice(qi + state.q.length)));
      } else n.textContent = x.n;
    } else n.textContent = x.n;
    var m = el("span", "mk", s === 3 ? "OK" : s === 2 ? "PART" : s === 1 ? "GAP" : "—");
    b.appendChild(c); b.appendChild(n); b.appendChild(m);

    b.addEventListener("click", function () {
      var cur = statusOf(x.id);
      var nxt = (cur + 1) % 4;
      if (nxt === 0) delete state.st[x.id]; else state.st[x.id] = nxt;
      b.dataset.st = nxt;
      b.querySelector(".mk").textContent = nxt === 3 ? "OK" : nxt === 2 ? "PART" : nxt === 1 ? "GAP" : "—";
      b.setAttribute("aria-label", x.id + " " + x.n + ", status " + STATUS_LABEL[nxt]);
      b.title = x.n + " — " + STATUS_LABEL[nxt] + (x.hint ? "\nTelemetry: " + x.hint : "") + "\n\nClick to change status";
      save(); renderDash(); renderBars(); renderGaps();
    });
    return b;
  }

  function renderBars() {
    var host = $("#bars");
    host.innerHTML = "";
    TACTICS.forEach(function (T) {
      var list = TECHNIQUES.filter(function (x) { return x.tac === T.k; });
      var m = metrics(list);
      var row = el("div", "bar-row");
      row.appendChild(el("span", null, T.n.toUpperCase()));
      var bar = el("div", "covbar" + (m.pct < 40 ? " tan" : ""));
      var fill = el("i");
      fill.style.width = m.pct + "%";
      bar.appendChild(fill);
      row.appendChild(bar);
      row.appendChild(el("span", "val", m.pct + "%"));
      host.appendChild(row);
    });
  }

  function renderGaps() {
    var host = $("#gap-list");
    host.innerHTML = "";
    var gaps = TECHNIQUES.filter(function (x) { return statusOf(x.id) === 1; });
    gaps.sort(function (a, b) { return ORDER[a.tac] - ORDER[b.tac]; });
    if (!gaps.length) {
      host.appendChild(el("li", "empty", "No gaps marked yet. Load an adversary profile, then assess each technique as Covered, Partial or Gap."));
      return;
    }
    gaps.forEach(function (x) {
      var li = el("li");
      var left = el("span");
      left.appendChild(el("span", "gcode", (x.legacy ? "◆ " : "") + x.id + "  "));
      left.appendChild(el("span", "gname", x.n));
      li.appendChild(left);
      li.appendChild(el("span", "gtac", tacName(x.tac)));
      host.appendChild(li);
    });
    var p = el("li");
    p.style.borderBottom = "0";
    p.style.color = "var(--muted)";
    p.style.fontSize = "12px";
    p.textContent = gaps.length + " open gap" + (gaps.length === 1 ? "" : "s") + " — earliest-stage gaps first.";
    host.appendChild(p);
  }

  /* --------------------------- EMULATION PLAN ----------------------------- */
  function buildPlan() {
    var gaps = TECHNIQUES.filter(function (x) { return statusOf(x.id) === 1; });
    var parts = TECHNIQUES.filter(function (x) { return statusOf(x.id) === 2; });
    gaps.sort(function (a, b) { return ORDER[a.tac] - ORDER[b.tac]; });
    parts.sort(function (a, b) { return ORDER[a.tac] - ORDER[b.tac]; });

    var m = metrics(TECHNIQUES);
    var prof = state.profile && PROFILES[state.profile] ? state.profile : "";
    var L = [];
    var rule = "============================================================";

    L.push(rule);
    L.push(" ADVERSARY EMULATION TEST PLAN");
    L.push(" Generated by RATAN_PATEL.SEC — MITRE ATT&CK Mapper (ATT&CK v19 aligned)");
    L.push(" " + new Date().toISOString().slice(0, 16).replace("T", " ") + " UTC");
    L.push(rule);
    L.push("");
    L.push("AUTHORISATION GATE — complete before any step runs");
    L.push("  [ ] Written approval naming the test window and the asset list");
    L.push("  [ ] Named white-cell owner who can halt the run");
    L.push("  [ ] Out-of-band abort channel agreed (not the engagement chat)");
    L.push("  [ ] Rollback plan for every configuration change");
    L.push("  [ ] Lab or staging target — not production, not real customer data");
    L.push("");

    if (prof) {
      L.push("EMULATED ADVERSARY");
      L.push("  Profile      : " + prof + (PROFILES[prof].group !== "composite" ? "  (ATT&CK " + PROFILES[prof].group + ")" : ""));
      L.push("  Rationale    : " + PROFILES[prof].blurb);
      L.push("");
    }

    L.push("BASELINE COVERAGE");
    L.push("  Techniques in scope : " + m.total);
    L.push("  Covered             : " + m.cov);
    L.push("  Partial             : " + m.part);
    L.push("  Gaps                : " + m.gap);
    L.push("  Unassessed          : " + m.un);
    L.push("  Weighted coverage   : " + m.pct + "%  (partial counts as half — it is not detection)");
    L.push("");

    L.push("PER-TACTIC BREAKDOWN");
    TACTICS.forEach(function (T) {
      var list = TECHNIQUES.filter(function (x) { return x.tac === T.k; });
      var tm = metrics(list);
      var flag = tm.pct < 40 ? "  <-- weakest visibility" : "";
      L.push("  " + pad(T.id, 8) + pad(T.n, 22) + pad(tm.pct + "%", 6) + tm.cov + "C/" + tm.part + "P/" + tm.gap + "G" + flag);
    });
    L.push("");

    if (gaps.length) {
      L.push(rule);
      L.push(" PHASE 1 — GAP VALIDATION  (" + gaps.length + " technique" + (gaps.length === 1 ? "" : "s") + ")");
      L.push(" For each: state the hypothesis, run one atomic action, record what fired.");
      L.push(rule);
      L.push("");
      var curTac = "";
      gaps.forEach(function (x, i) {
        if (x.tac !== curTac) {
          curTac = x.tac;
          L.push("--- " + tacName(curTac).toUpperCase() + " ---");
        }
        L.push(pad("  " + (i + 1) + ".", 7) + x.id + "  " + x.n);
        L.push("        Hypothesis : our stack would alert on this behaviour within 10 minutes and name the host");
        L.push("        Telemetry  : " + (x.hint || "to be identified"));
        L.push("        Expected   : NO reliable alert (marked as gap)");
        L.push("        Record     : start time, source host, whether any event fired, which log source saw it");
        if (x.legacy) L.push("        ATT&CK note: " + x.legacy);
        L.push("");
      });
    } else {
      L.push("PHASE 1 — no gaps marked. Assess the matrix first, or the plan has nothing to test.");
      L.push("");
    }

    if (parts.length) {
      L.push(rule);
      L.push(" PHASE 2 — PARTIAL TO DETECTION  (" + parts.length + ")");
      L.push(" Telemetry exists here; the missing piece is a tuned rule plus a triage path.");
      L.push(rule);
      L.push("");
      parts.forEach(function (x) {
        L.push("  " + pad(x.id, 12) + x.n);
        L.push("        Have       : " + (x.hint || "raw logging"));
        L.push("        Task       : write the analytic, set a threshold, define the triage runbook owner");
        L.push("");
      });
    }

    L.push(rule);
    L.push(" PHASE 3 — REPORTING (per technique, not per tool)");
    L.push(rule);
    L.push("  For every technique write exactly three lines:");
    L.push("    1. Behaviour performed (technique ID + one sentence)");
    L.push("    2. What the defenders saw (alert / no alert / log only / nothing)");
    L.push("    3. The single change that would have caught it, with an owner and a date");
    L.push("");
    L.push("  Do not report tools. Do not report a percentage. Report the sentence");
    L.push("  that costs money to fix — that is the deliverable.");
    L.push("");
    L.push(rule);
    L.push(" Generated locally in the browser. Nothing here was uploaded.");
    L.push(" Verify technique IDs against attack.mitre.org before publishing.");
    L.push(" Authorised testing only — systems you own or have written permission to test.");
    L.push(rule);

    return L.join("\n");
  }
  function pad(s, n) {
    s = String(s);
    while (s.length < n) s += " ";
    return s;
  }

  /* --------------------------------- EVENTS ------------------------------- */
  function bind() {
    /* profile dropdown */
    var sel = $("#profile");
    Object.keys(PROFILES).forEach(function (k) {
      var o = document.createElement("option");
      o.value = k;
      o.textContent = k + (PROFILES[k].group !== "composite" ? " (" + PROFILES[k].group + ")" : "");
      sel.appendChild(o);
    });
    sel.value = state.profile || "";

    sel.addEventListener("change", function () {
      var v = sel.value;
      state.profile = v;
      if (!v) { toast("Profile cleared — your statuses are untouched"); save(); return; }
      var p = PROFILES[v];
      state.st = {};
      p.tech.forEach(function (id) { if (byId[id]) state.st[id] = 1; });
      save(); renderDash(); renderMatrix();
      $("#out").value = buildPlan();
      toast("Loaded " + v + " — " + (p.tech.length) + " techniques marked as gaps");
    });

    $("#q").addEventListener("input", function (e) {
      state.q = e.target.value.trim().toLowerCase();
      renderMatrix();
    });
    $("#filter").addEventListener("change", function (e) {
      state.filter = e.target.value;
      renderMatrix();
    });

    $("#btn-focus").addEventListener("click", function () {
      var names = TACTICS.map(function (T) { return T.n; });
      var pick = window.prompt("Focus on which tactic?\n\n" + names.map(function (n, i) { return (i + 1) + ") " + n; }).join("\n") + "\n\nEnter a number, or leave blank for all.");
      if (pick === null) return;
      if (!pick.trim()) { state.tactic = ""; }
      else {
        var idx = parseInt(pick, 10) - 1;
        if (isNaN(idx) || idx < 0 || idx >= TACTICS.length) { toast("Not a valid choice"); return; }
        state.tactic = TACTICS[idx].k;
      }
      renderMatrix();
      toast(state.tactic ? "Focused: " + tacName(state.tactic) : "Showing all tactics");
    });

    $("#btn-gaps").addEventListener("click", function () {
      TECHNIQUES.forEach(function (x) { if (statusOf(x.id) !== 3) state.st[x.id] = 1; });
      save(); renderDash(); renderMatrix(); toast("Everything not covered is now marked as a gap");
    });

    $("#btn-clear").addEventListener("click", function () {
      if (!window.confirm("Reset all statuses and the emulation plan? This cannot be undone.")) return;
      state.st = {}; state.profile = "";
      $("#profile").value = "";
      $("#out").value = "";
      save(); renderDash(); renderMatrix(); toast("Matrix reset");
    });

    $("#btn-plan").addEventListener("click", function () {
      $("#out").value = buildPlan();
      toast("Plan generated");
    });

    $("#btn-copy").addEventListener("click", function () {
      var txt = $("#out").value || buildPlan();
      $("#out").value = txt;
      var done = function () { toast("Copied to clipboard"); };
      if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(txt).then(done, function () { $("#out").select(); done(); });
      } else { $("#out").select(); document.execCommand("copy"); done(); }
    });

    $("#btn-export").addEventListener("click", function () {
      var payload = {
        tool: "RATAN_PATEL.SEC ATT&CK Mapper",
        attackVersion: "v19",
        exportedAt: new Date().toISOString(),
        profile: state.profile || null,
        coverage: metrics(TECHNIQUES),
        statuses: state.st,
        plan: $("#out").value || buildPlan()
      };
      var blob = new Blob([JSON.stringify(payload, null, 2)], { type: "application/json" });
      var a = document.createElement("a");
      a.href = URL.createObjectURL(blob);
      a.download = "attack-coverage-" + new Date().toISOString().slice(0, 10) + ".json";
      document.body.appendChild(a); a.click(); document.body.removeChild(a);
      setTimeout(function () { URL.revokeObjectURL(a.href); }, 1500);
      toast("Exported JSON");
    });

    $("#btn-import").addEventListener("click", function () { $("#file").click(); });
    $("#file").addEventListener("change", function (e) {
      var f = e.target.files && e.target.files[0];
      if (!f) return;
      var r = new FileReader();
      r.onload = function () {
        try {
          var d = JSON.parse(r.result);
          if (!d || !d.statuses) throw new Error("bad file");
          state.st = {};
          Object.keys(d.statuses).forEach(function (k) {
            var v = parseInt(d.statuses[k], 10);
            if (byId[k] && v >= 1 && v <= 3) state.st[k] = v;
          });
          state.profile = d.profile && PROFILES[d.profile] ? d.profile : "";
          $("#profile").value = state.profile;
          $("#out").value = d.plan || buildPlan();
          save(); renderDash(); renderMatrix();
          toast("Imported — statuses restored");
        } catch (err) { toast("That file did not parse as a mapper export"); }
      };
      r.readAsText(f);
      e.target.value = "";
    });

    $("#btn-print").addEventListener("click", function () {
      if (!$("#out").value) $("#out").value = buildPlan();
      window.print();
    });

    /* keyboard: "/" focuses search */
    document.addEventListener("keydown", function (e) {
      if (e.key === "/" && document.activeElement !== $("#q") && !/input|textarea|select/i.test(document.activeElement.tagName)) {
        e.preventDefault(); $("#q").focus();
      }
    });
  }

  /* --------------------------------- BOOT --------------------------------- */
  load();
  bind();
  renderDash();
  renderMatrix();
  if (state.profile && PROFILES[state.profile]) $("#out").value = buildPlan();
})();
