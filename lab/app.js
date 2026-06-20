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

    // Simulation function for tools
    window.runTool = function(toolName) {
        const outputConsole = document.getElementById(`${toolName}-output`);
        outputConsole.innerHTML = `Running ${toolName} simulation...\n`;

        let simulationOutput = "";
        switch (toolName) {
            case "nmap":
                simulationOutput = `
Starting Nmap 7.92 ( https://nmap.org ) at 2026-06-21 10:30 IST
Nmap scan report for target.com (192.168.1.1)
Host is up (0.0020s latency).
Not shown: 997 closed tcp ports (conn-refused)
PORT     STATE SERVICE VERSION
22/tcp   open  ssh     OpenSSH 8.2p1 Ubuntu 4ubuntu0.2
80/tcp   open  http    Apache httpd 2.4.41 ((Ubuntu))
443/tcp  open  ssl/http Apache httpd 2.4.41 ((Ubuntu))

Service detection performed. Please report any incorrect results at https://nmap.org/submit/ .
Nmap done: 1 IP address (1 host up) scanned in 2.54 seconds
                `;
                break;
            case "nikto":
                simulationOutput = `
- Nikto v2.1.6
---------------------------------------------------------------------------
+ Target IP:          192.168.1.1
+ Target Hostname:    target.com
+ Target Port:        80
+ Start Time:         2026-06-21 10:31:00 (GMT+5:30)
---------------------------------------------------------------------------
+ Server: Apache/2.4.41 (Ubuntu)
+ The anti-clickjacking X-Frame-Options header is not present.
+ No X-Content-Type-Options header found.
+ Uncommon header 'x-powered-by' found, with contents: PHP/7.4.3
+ OSVDB-3233: /icons/README: Apache default file found.
+ OSVDB-3092: /index.php: This might be a PHP page, which often contain vulnerabilities.
+ 7800 requests: 0 error(s); 5 item(s) found on remote host
+ End Time:           2026-06-21 10:31:45 (GMT+5:30) (45 seconds)
---------------------------------------------------------------------------
+ 1 host(s) tested
                `;
                break;
            case "metasploit":
                simulationOutput = `
[*] Started reverse TCP handler on 192.168.1.100:4444 
[*] Sending stage (201283 bytes) to 192.168.1.1
[*] Meterpreter session 1 opened (192.168.1.100:4444 -> 192.168.1.1:49172) at 2026-06-21 10:32:10 (GMT+5:30)

meterpreter > sysinfo
Computer        : TARGET-PC
OS              : Windows 10 (Build 19041). 
Architecture    : x64
System Language : en_US
Meterpreter     : x64/windows
                `;
                break;
            case "mimikatz":
                simulationOutput = `
_ .\n / \   .   ( (o) )   .  / \  _\n( (o) )  / \ /  _  \ / \  ( (o) )\n \ /  _  \ ( (o) ) /  _  \  \ /
  .  ( (o) ) \ /  .  \ ( (o) )  .
     \ /  .      .  \ /
      .

mimikatz # sekurlsa::logonpasswords

Authentication Id : 0 ; 999 (00000000:000003e7)
Session           : Interactive from 1
User Name         : Administrator
Domain            : TARGET-PC
Logon Server      : TARGET-PC
Logon Time        : 2026-06-21 10:00:00
SID               : S-1-5-21-1234567890-123456789-123456789-500
        msv : 
         [00000003] Primary
         * Username : Administrator
         * Domain   : TARGET-PC
         * NTLM     : 1a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d
         * SHA1     : 1a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9a0b
                `;
                break;
            default:
                simulationOutput = `Unknown tool: ${toolName}`;
        }

        outputConsole.innerHTML += simulationOutput;
        outputConsole.scrollTop = outputConsole.scrollHeight; // Scroll to bottom
    };
});
