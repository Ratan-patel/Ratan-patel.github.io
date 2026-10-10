// Dynamic stats animations on load
document.addEventListener('DOMContentLoaded', () => {
  // Set current year in footer
  document.getElementById('current-year').textContent = new Date().getFullYear();
});

// Mock Interactive Terminal Command Handler
function runTerminalCommand(cmd) {
  const history = document.getElementById('terminal-history');
  const input = document.getElementById('terminal-input');

  if (!cmd) {
    cmd = input.value.trim().toLowerCase();
    input.value = '';
  } else {
    cmd = cmd.toLowerCase();
  }

  if (cmd === '') return;

  // Add the prompt line to history
  let cmdLine = document.createElement('div');
  cmdLine.innerHTML = `<span class="text-emerald-400">ratan@security-hotline:~$</span> <span class="text-white">${cmd}</span>`;
  history.appendChild(cmdLine);

  let response = document.createElement('div');
  response.className = "text-slate-300 pl-4 py-1 border-l border-slate-800";

  switch (cmd) {
    case 'help':
      response.innerHTML = `
        <span class="text-emerald-400 font-bold">Available commands:</span><br>
        - <span class="text-cyan-400">whoami</span>   : Display professional profile of Ratan Kumar Patel<br>
        - <span class="text-cyan-400">skills</span>   : Print core security competencies & tools used<br>
        - <span class="text-cyan-400">exp</span>      : Print complete professional work history<br>
        - <span class="text-cyan-400">certs</span>    : List cybersecurity academic records & certifications<br>
        - <span class="text-cyan-400">contact</span>  : Display secure messenger links & hotlines<br>
        - <span class="text-cyan-400">nmap</span>     : Simulate an offensive port vulnerability scan<br>
        - <span class="text-cyan-400">matrix</span>   : Stream falling green matrix digital rain<br>
        - <span class="text-cyan-400">crack</span>    : Simulate brute-forcing an encrypted vault<br>
        - <span class="text-cyan-400">socials</span>  : Show direct links to social network channels<br>
        - <span class="text-cyan-400">clear</span>    : Clear terminal console screen
      `;
      break;

    case 'whoami':
      response.innerHTML = `
        <span class="text-white font-bold">Ratan Kumar Patel</span><br>
        Role: <span class="text-emerald-400">CEH Cyber Security Trainer & Hacking Expert</span><br>
        Exp : <span class="text-cyan-400">6+ Years in Ethical Hacking & VAPT</span><br>
        Bio : Specializes in training corporate networks, setting up CTF labs, and auditing system servers. Trained 500+ security aspirants with practical workshops.
      `;
      break;

    case 'skills':
      response.innerHTML = `
        <span class="text-white font-bold">Core Competencies:</span><br>
        [+] <span class="text-emerald-400">Penetration Testing</span> : Web apps (OWASP), Networks, Firewall hardening<br>
        [+] <span class="text-emerald-400">Offensive Technologies</span> : Red Teaming, CTF Lab Engineering, Exploit Building<br>
        [+] <span class="text-emerald-400">Tool Stack</span> : Metasploit, Burp Suite, Nmap, Wireshark, Nessus, Kali Linux
      `;
      break;

    case 'exp':
      response.innerHTML = `
        <span class="text-white font-bold">Work Experience Summary:</span><br>
        1. <span class="text-emerald-400">Equator Cyber Solutions (2020-2026)</span> : Technical Security Manager & Trainer<br>
           - Designing OWASP curricula & custom practical labs<br>
           - Delivered corporate workshops & cyber security bootcamps<br>
        2. <span class="text-cyan-400">Silent Front & Software Solutions (2018-2020)</span> : Tech Security Executive<br>
           - Executed comprehensive VAPT audits on enterprise web interfaces
      `;
      break;

    case 'certs':
      response.innerHTML = `
        <span class="text-white font-bold">Verifiable Academic Records:</span><br>
        [✓] <span class="text-emerald-400">Certified Ethical Hacker (CEH) v12</span> - EC-Council (Issued: Jul 2024, ID: ECC92840)<br>
        [✓] <span class="text-emerald-400">MS in Cybersecurity & Information Assurance</span> - Western Governors University (2023)<br>
        [✓] <span class="text-cyan-400">PG Diploma in Computer Application</span> - Board of Technical Education, U.P (2013)
      `;
      break;

    case 'contact':
      response.innerHTML = `
        <span class="text-white font-bold">Secure Gateway Channels:</span><br>
        - Email : <a class="text-emerald-400 hover:underline" href="mailto:patelratan460@gmail.com">patelratan460@gmail.com</a><br>
        - Phone : +91-8700913645 / 9650053559<br>
        - WhatsApp : <a class="text-emerald-400 hover:underline" href="https://wa.me/918700913645" target="_blank">Start Secure Chat</a><br>
        - LinkedIn : <a class="text-cyan-400 hover:underline" href="https://www.linkedin.com/in/ratan-kumar-patel-032a43367/" target="_blank">LinkedIn Profile</a>
      `;
      break;

    case 'matrix':
      response.innerHTML = `<span class="text-emerald-400 animate-pulse">[SYS] Establishing neural interface... Streaming digital rain.</span>`;
      history.appendChild(response);
      scrollTerminal();

      let linesCount = 0;
      const matrixInterval = setInterval(() => {
        if (linesCount >= 15) {
          clearInterval(matrixInterval);
          let doneLine = document.createElement('div');
          doneLine.className = "text-emerald-400 font-bold pl-4 py-1 border-l border-slate-800";
          doneLine.innerHTML = "[+] Signal stream terminated successfully.";
          history.appendChild(doneLine);
          scrollTerminal();
          return;
        }
        let rainLine = document.createElement('div');
        rainLine.className = "text-emerald-500 font-mono text-xs pl-4 py-0.5 border-l border-slate-800 tracking-widest";

        // Generate random binary & hacker code strings
        let chars = "010101010101010101ABCDEFGHIJKLMNOPQRSTUVWXYZ@#$*&%+=?/";
        let str = "";
        for (let i = 0; i < 35; i++) {
          str += chars[Math.floor(Math.random() * chars.length)];
        }
        rainLine.textContent = str;
        history.appendChild(rainLine);
        scrollTerminal();
        linesCount++;
      }, 150);
      return;

    case 'crack':
    case 'hack':
      response.innerHTML = `<span class="text-cyan-400 animate-pulse">[SYS] Targeting local encrypted node... Initiating decryption...</span>`;
      history.appendChild(response);
      scrollTerminal();

      setTimeout(() => {
        let targetLog = document.createElement('div');
        targetLog.className = "text-slate-400 pl-4 py-1 border-l border-slate-800";
        targetLog.innerHTML = `
          [+] Node Target: secure-vault.local (10.0.8.21)<br>
          [+] Attack Vector: SSH Dictionary Probe<br>
          [+] Active Wordlist: rockyou.txt (14,344,392 hashes)
        `;
        history.appendChild(targetLog);
        scrollTerminal();
      }, 600);

      let pct = 0;
      let crackLine = document.createElement('div');
      crackLine.className = "text-amber-500 font-bold pl-4 py-1 border-l border-slate-800";

      setTimeout(() => {
        crackLine.innerHTML = `[>] Cracking credential hash: 0%`;
        history.appendChild(crackLine);
        scrollTerminal();
      }, 1300);

      const crackInterval = setInterval(() => {
        pct += Math.floor(Math.random() * 16) + 4;
        if (pct >= 100) {
          pct = 100;
          clearInterval(crackInterval);
          crackLine.innerHTML = `[>] Cracking credential hash: ${pct}% [COMPLETE]`;

          let successLog = document.createElement('div');
          successLog.className = "text-emerald-400 font-bold pl-4 py-1 border-l border-slate-800";
          successLog.innerHTML = `
            [SUCCESS] Match found: "rpatel_sec_admin_pass"<br>
            [SUCCESS] Decrypting node partition... Mounting root file system...<br>
            Welcome, RATAN_PATEL. Access granted. Shell fully established.
          `;
          history.appendChild(successLog);
          scrollTerminal();
        } else {
          crackLine.innerHTML = `[>] Cracking credential hash: ${pct}%...`;
          scrollTerminal();
        }
      }, 350);
      return;

    case 'socials':
      response.innerHTML = `
        <span class="text-white font-bold">Ratan Kumar Patel - Professional Networks:</span><br>
        - <span class="text-cyan-400">LinkedIn</span>: <a class="text-emerald-400 hover:underline" href="https://www.linkedin.com/in/ratan-kumar-patel-032a43367/" target="_blank">linkedin.com/in/ratan-kumar-patel-032a43367/</a><br>
        - <span class="text-cyan-400">GitHub</span>: <a class="text-emerald-400 hover:underline" href="https://github.com/ratan-patel" target="_blank">github.com/ratan-patel</a><br>
        - <span class="text-cyan-400">WhatsApp</span>: <a class="text-emerald-400 hover:underline" href="https://wa.me/918700913645" target="_blank">Start WhatsApp Chat</a>
      `;
      break;

    case 'clear':
      history.innerHTML = '';
      return;

    case 'nmap':
      response.innerHTML = `<span class="text-slate-400 animate-pulse">[INFO] Initiating simulated Nmap Port Discovery Scan...</span>`;
      history.appendChild(response);

      // Multi-step animated response for Nmap
      setTimeout(() => {
        let log1 = document.createElement('div');
        log1.className = "text-slate-400 pl-4 py-1 border-l border-slate-800";
        log1.innerHTML = `
          Starting Nmap 7.93 ( https://nmap.org ) at ${new Date().toISOString()}<br>
          Nmap scan report for secure-target.server (192.168.1.104)<br>
          Host is up (0.0034s latency).
        `;
        history.appendChild(log1);
        scrollTerminal();
      }, 500);

      setTimeout(() => {
        let log2 = document.createElement('div');
        log2.className = "text-slate-400 pl-4 py-1 border-l border-slate-800";
        log2.innerHTML = `
          Not shown: 997 closed tcp ports (reset)<br>
          PORT &nbsp;&nbsp;&nbsp;&nbsp;STATE &nbsp;&nbsp;&nbsp;SERVICE &nbsp;&nbsp;&nbsp;&nbsp;VERSION<br>
          22/tcp &nbsp;&nbsp;<span class="text-red-500">OPEN</span> &nbsp;&nbsp;&nbsp;&nbsp;ssh &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;OpenSSH 8.9p1 (Secure Keyed)<br>
          80/tcp &nbsp;&nbsp;<span class="text-emerald-500">FILTERED</span> http &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;Apache httpd 2.4.52<br>
          443/tcp &nbsp;<span class="text-emerald-500">FILTERED</span> https &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;Nginx SSL Gateway (TLSv1.3)
        `;
        history.appendChild(log2);
        scrollTerminal();
      }, 1200);

      setTimeout(() => {
        let log3 = document.createElement('div');
        log3.className = "text-emerald-400 font-bold pl-4 py-1 border-l border-slate-800";
        log3.innerHTML = `
          [✔] Scan Complete: 0 vulnerabilities found. Target system is properly hardened.<br>
          Nmap done: 1 IP address (1 host up) scanned in 1.84 seconds.
        `;
        history.appendChild(log3);
        scrollTerminal();
      }, 2000);
      return;

    default:
      response.innerHTML = `<span class="text-red-500">bash: command not found: ${cmd}</span>. Type <span class="text-emerald-400 font-bold">'help'</span> to view available operations.`;
  }

  history.appendChild(response);
  scrollTerminal();
}

function scrollTerminal() {
  const termBody = document.getElementById('terminal-body');
  termBody.scrollTop = termBody.scrollHeight;
}

// Hook up keyboard ENTER to the terminal input
document.getElementById('terminal-input').addEventListener('keydown', (e) => {
  if (e.key === 'Enter') {
    runTerminalCommand();
  }
});

// Certificate Scanner Modal handler
function scanCertificate(certName, bgGradient, fontAwesomeIcon, docUrl) {
  const modal = document.getElementById('scanner-modal');
  const title = document.getElementById('modal-cert-title');
  const status = document.getElementById('modal-cert-status');
  const progressBar = document.getElementById('modal-cert-progress');
  const iconContainer = document.getElementById('modal-cert-icon-container');
  const iconElement = document.getElementById('modal-cert-icon');
  const viewBtn = document.getElementById('modal-cert-view-btn');

  // Logs
  const log1 = document.getElementById('modal-cert-log-1');
  const log2 = document.getElementById('modal-cert-log-2');
  const log3 = document.getElementById('modal-cert-log-3');
  const log4 = document.getElementById('modal-cert-log-4');

  // Set visual properties
  modal.classList.remove('hidden');
  title.textContent = `Validating: ${certName}`;
  status.textContent = 'CONNECTING VERIFICATION SYSTEM...';
  status.className = 'text-cyan-400 font-bold uppercase animate-pulse';
  progressBar.style.width = '0%';
  iconContainer.style.background = bgGradient;
  iconElement.className = `fa ${fontAwesomeIcon} text-4xl text-white`;

  // Hide the view credentials button by default
  if (viewBtn) {
    viewBtn.classList.add('hidden');
    viewBtn.href = '#';
  }

  // Clear previous log visibility
  log1.classList.add('hidden');
  log2.classList.add('hidden');
  log3.classList.add('hidden');
  log4.classList.add('hidden');

  // Start sequence animation
  setTimeout(() => {
    progressBar.style.width = '30%';
    status.textContent = 'SCANNING DIGEST HASH...';
    status.className = 'text-amber-400 font-bold uppercase animate-pulse';
    log1.classList.remove('hidden');
  }, 600);

  setTimeout(() => {
    progressBar.style.width = '65%';
    status.textContent = 'VERIFYING AGAINST DISTRIBUTED LEDGER...';
    log2.classList.remove('hidden');
  }, 1300);

  setTimeout(() => {
    progressBar.style.width = '100%';
    status.textContent = 'ACCESS GRANTED - VERIFIED GENUINE';
    status.className = 'text-emerald-400 font-bold uppercase animate-bounce';
    log3.classList.remove('hidden');
    log4.classList.remove('hidden');

    // Reveal direct download/view link button upon success
    if (docUrl && viewBtn) {
      viewBtn.href = docUrl;
      viewBtn.classList.remove('hidden');
    }
  }, 2200);
}

function closeModal() {
  const modal = document.getElementById('scanner-modal');
  if (modal) modal.classList.add('hidden');

  const viewBtn = document.getElementById('modal-cert-view-btn');
  if (viewBtn) {
    viewBtn.classList.add('hidden');
    viewBtn.href = '#';
  }
}

// Contact form secure dispatch simulator with custom high-tech on-page Toast
function handleFormDispatch(e) {
  e.preventDefault();
  const name = document.getElementById('contact-name').value.trim();
  const email = document.getElementById('contact-email').value.trim();
  const subject = document.getElementById('contact-subject').value.trim();
  const message = document.getElementById('contact-message').value.trim();

  if (!name || !email || !message) return;

  const toast = document.getElementById('secure-toast');
  const progress = document.getElementById('toast-progress');
  const logs = document.getElementById('toast-log-container');

  if (!toast || !progress || !logs) {
    // Fallback if elements not found
    alert(`[SECURE DISPATCH]\n\nThank you, ${name}! Your message was successfully encrypted and transmitted.`);
    return;
  }

  // Show toast
  toast.classList.remove('hidden');
  setTimeout(() => {
    toast.classList.remove('translate-y-10', 'opacity-0');
  }, 50);

  // Reset progress and log
  progress.style.width = '0%';
  logs.innerHTML = `
    <div class="flex items-center gap-1.5 text-slate-500">
      <span>[INFO]</span> <span>Establishing secure handshake protocol...</span>
    </div>
  `;

  // Animate progress and show multi-step log feedback
  setTimeout(() => {
    progress.style.width = '35%';
    logs.innerHTML += `
      <div class="flex items-center gap-1.5 text-cyan-400">
        <span>[SYS]</span> <span>Encrypting dispatch (AES-256-GCM)...</span>
      </div>
    `;
  }, 700);

  setTimeout(() => {
    progress.style.width = '70%';
    logs.innerHTML += `
      <div class="flex items-center gap-1.5 text-amber-400">
        <span>[NET]</span> <span>Routing packet through secure proxy...</span>
      </div>
    `;
  }, 1600);

  setTimeout(() => {
    progress.style.width = '100%';
    logs.innerHTML += `
      <div class="flex items-center gap-1.5 text-emerald-400 font-bold">
        <span>[OK]</span> <span>DISPATCH RECEIVED. Secure channels open.</span>
      </div>
    `;

    // Clear form
    document.getElementById('contact-name').value = '';
    document.getElementById('contact-email').value = '';
    document.getElementById('contact-subject').value = '';
    document.getElementById('contact-message').value = '';
  }, 2600);

  // Auto-hide toast after 6 seconds
  setTimeout(() => {
    toast.classList.add('translate-y-10', 'opacity-0');
    setTimeout(() => {
      toast.classList.add('hidden');
    }, 500);
  }, 6500);
}

// Collapsible Mobile Menu Toggle
function toggleMobileMenu() {
  const menu = document.getElementById('mobile-menu');
  const btnIcon = document.querySelector('#mobile-menu-btn i');
  if (menu.classList.contains('hidden')) {
    menu.classList.remove('hidden');
    btnIcon.classList.remove('fa-bars');
    btnIcon.classList.add('fa-xmark');
  } else {
    menu.classList.add('hidden');
    btnIcon.classList.remove('fa-xmark');
    btnIcon.classList.add('fa-bars');
  }
}
