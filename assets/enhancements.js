/* ==================================================================
   RATAN_PATEL.SEC — ADVANCED ENHANCEMENT LAYER
   Ctrl+K palette · telemetry HUD · red-alert · matrix rain ·
   magnetic UI · scramble fx · live GitHub stats · PWA
   Vanilla JS, zero dependencies, fails silently.
   ================================================================== */
(function () {
  'use strict';

  var $ = function (s, r) { return (r || document).querySelector(s); };
  var $$ = function (s, r) { return Array.prototype.slice.call((r || document).querySelectorAll(s)); };
  var RM = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  var HOVER = window.matchMedia && window.matchMedia('(hover:hover)').matches;
  var EMAIL = 'patelratan460@gmail.com';
  var PHONE = '+918700913645';

  function accent() {
    var v = getComputedStyle(document.body).getPropertyValue('--mint');
    return (v && v.trim()) || '#00ffc8';
  }

  /* ---------------- TOAST ---------------- */
  var toastEl, toastT;
  function toast(msg, warn) {
    if (!toastEl) {
      toastEl = document.createElement('div');
      toastEl.id = 'eToast';
      toastEl.setAttribute('role', 'status');
      document.body.appendChild(toastEl);
    }
    toastEl.className = warn ? 'warn' : '';
    toastEl.innerHTML = '<span class="tick">' + (warn ? '⚠' : '➤') + '</span><span></span>';
    toastEl.lastChild.textContent = msg;
    requestAnimationFrame(function () { toastEl.classList.add('on'); });
    clearTimeout(toastT);
    toastT = setTimeout(function () { toastEl.classList.remove('on'); }, 2800);
  }

  /* =============== 01 · COMMAND PALETTE (Ctrl+K) =============== */
  var COMMANDS = [];
  function cmd(group, title, keys, ico, run) {
    COMMANDS.push({ group: group, title: title, keys: (keys || '') + ' ' + title, ico: ico, run: run });
  }
  function go(sel) {
    return function () {
      var el = $(sel);
      if (el) el.scrollIntoView({ behavior: RM ? 'auto' : 'smooth', block: 'start' });
    };
  }
  function page(href) { return function () { window.location.href = href; }; }
  function ext(href) { return function () { window.open(href, '_blank', 'noopener'); }; }

  [ ['home', 'Home / Hero'], ['ratanos', 'RATAN OS'], ['soc', 'Live Attack Surface Grid'],
    ['lab', 'Security Console (terminal)'], ['dossier', 'Who is Ratan'], ['arsenal', 'Core Competencies'],
    ['trajectory', 'Operational Trajectory'], ['creds', 'Education & Certifications'],
    ['vault', 'CMU MSIS Handbook'], ['disclosure', 'Responsible Disclosure'], ['contact', 'Open a Secure Line']
  ].forEach(function (s) { cmd('NAVIGATE', s[1], 'goto scroll section', 'fas fa-crosshairs', go('#' + s[0])); });

  [ ['lab.html', 'Red-Team Lab (simulator)'], ['pentest-lab.html', 'Pentest Lab Arsenal'],
    ['services.html', 'VAPT Services'], ['ratan-monetization-launch-kit.html', 'Offers & Training'],
    ['ratan-os-release.html', 'RATAN OS Downloads'], ['ethical-hacking-foundation.html', 'Course: Ethical Hacking Foundation'],
    ['advanced-web-api-pentesting.html', 'Course: Web & API Pentesting'], ['red-team-adversary-simulation.html', 'Course: Red Team Simulation'],
    ['ai-security-llm-red-teaming.html', 'Course: AI Security & LLM'], ['cmu-msis-handbook.html', 'Handbook: CMU MSIS Book (read online)'],
    ['assets/courses/cmu_msis_handbook.docx', 'Handbook DOCX (download)'], ['ratan_patel_portfolio.html', 'Full Portfolio'],
    ['ratan_patel_resume.html', 'Resume / CV']
  ].forEach(function (p) { cmd('OPEN PAGE', p[1], 'open page file', 'fas fa-file-code', page(p[0])); });

  cmd('ACTION', 'Try RATAN AI assistant', 'ai chat assistant', 'fas fa-robot', ext('https://v1qmk5wx2361-d.space-z.ai/'));
  cmd('ACTION', 'Download CV (PDF)', 'cv resume pdf download', 'fas fa-download', ext('ratan_patel_cv.pdf'));
  cmd('ACTION', 'RATAN AI AGENT release page', 'agent app apk verify download page', 'fas fa-mobile-screen', page('ratan-ai-agent.html'));
  cmd('ACTION', 'Get RATAN AI Agent APK', 'apk android app download agent', 'fab fa-android',
      ext('https://github.com/Ratan-patel/Ratan-patel.github.io/releases/download/ratan-ai-agent-v2.1/Ratan-AI-Agent-2.1.0-release.apk'));
  cmd('ACTION', 'WhatsApp Ratan', 'whatsapp chat message', 'fab fa-whatsapp', ext('https://wa.me/' + PHONE));
  cmd('ACTION', 'Email Ratan', 'email mail contact', 'fas fa-envelope', function () { window.location.href = 'mailto:' + EMAIL; });
  cmd('ACTION', 'Copy email address', 'copy email clipboard', 'fas fa-copy', function () { copyText(EMAIL, 'EMAIL COPIED → ' + EMAIL); });
  cmd('ACTION', 'Toggle Matrix rain', 'matrix rain fx toggle', 'fas fa-code', function () { toggleRain(); });
  cmd('ACTION', 'Toggle RED ALERT mode', 'red alert theme konami', 'fas fa-radiation', function () { setRedAlert(!document.body.classList.contains('redalert')); });
  cmd('ACTION', 'Toggle Telemetry HUD', 'hud telemetry stats panel', 'fas fa-microchip', function () { toggleHud(); });
  cmd('ACTION', 'Back to top', 'top scroll up', 'fas fa-arrow-up', function () { window.scrollTo({ top: 0, behavior: RM ? 'auto' : 'smooth' }); });
  cmd('ACTION', 'GitHub profile', 'github profile repos', 'fab fa-github', ext('https://github.com/Ratan-patel'));
  cmd('ACTION', 'LinkedIn profile', 'linkedin profile social', 'fab fa-linkedin', ext('https://www.linkedin.com/in/ratan-kumar-patel-032a43367/'));

  var pkWrap, pkIn, pkList, sel = 0, view = [];
  function buildPalette() {
    pkWrap = document.createElement('div');
    pkWrap.id = 'pkWrap';
    pkWrap.innerHTML =
      '<div id="pkBox" role="dialog" aria-label="Command palette">' +
        '<div id="pkHead"><span class="pkPrompt">ratan@sec:~$</span>' +
        '<input id="pkIn" autocomplete="off" spellcheck="false" placeholder="type a command or search…" aria-label="Search commands">' +
        '<kbd>ESC</kbd></div>' +
        '<div id="pkList" role="listbox"></div>' +
        '<div id="pkFoot"><span><b>↑↓</b> navigate</span><span><b>↵</b> execute</span><span><b>esc</b> abort</span><span style="margin-left:auto">CTRL+K</span></div>' +
      '</div>';
    document.body.appendChild(pkWrap);
    pkIn = $('#pkIn'); pkList = $('#pkList');
    pkWrap.addEventListener('click', function (e) { if (e.target === pkWrap) closePk(); });
    pkIn.addEventListener('input', function () { render(pkIn.value); });
    pkIn.addEventListener('keydown', function (e) {
      if (e.key === 'ArrowDown') { e.preventDefault(); move(1); }
      else if (e.key === 'ArrowUp') { e.preventDefault(); move(-1); }
      else if (e.key === 'Enter') { e.preventDefault(); runSel(); }
    });
  }
  function score(q, text) {
    q = q.toLowerCase().trim(); text = text.toLowerCase();
    if (!q) return 1;
    if (text.indexOf(q) !== -1) return 100 - text.indexOf(q);
    var qi = 0, s = 0;
    for (var i = 0; i < text.length && qi < q.length; i++) {
      if (text[i] === q[qi]) { qi++; s += 2; }
    }
    return qi === q.length ? s : -1;
  }
  function render(q) {
    view = COMMANDS
      .map(function (c) { return { c: c, s: score(q, c.keys) }; })
      .filter(function (v) { return v.s > 0; })
      .sort(function (a, b) { return b.s - a.s; })
      .map(function (v) { return v.c; });
    sel = 0;
    if (!view.length) {
      pkList.innerHTML = '<div class="pkEmpty">// NO_MATCH — try "lab", "course", "cv", "matrix"…</div>';
      return;
    }
    var html = '', lastG = '';
    view.forEach(function (c, i) {
      if (c.group !== lastG) { html += '<div class="pkGroup">// ' + c.group + '</div>'; lastG = c.group; }
      html += '<div class="pkItem' + (i === sel ? ' sel' : '') + '" data-i="' + i + '" role="option">' +
              '<span class="pkIco"><i class="' + c.ico + '"></i></span><span>' + c.title + '</span>' +
              '<span class="pkKey">' + c.group.toLowerCase() + '</span></div>';
    });
    pkList.innerHTML = html;
    $$('.pkItem', pkList).forEach(function (el) {
      el.addEventListener('click', function () { sel = +el.getAttribute('data-i'); runSel(); });
      el.addEventListener('mousemove', function () { setSel(+el.getAttribute('data-i')); });
    });
  }
  function setSel(i) {
    sel = i;
    $$('.pkItem', pkList).forEach(function (el) {
      el.classList.toggle('sel', +el.getAttribute('data-i') === i);
    });
  }
  function move(d) {
    if (!view.length) return;
    setSel((sel + d + view.length) % view.length);
    var el = $('.pkItem.sel', pkList);
    if (el) el.scrollIntoView({ block: 'nearest' });
  }
  function runSel() { var c = view[sel]; closePk(); if (c) setTimeout(c.run, 40); }
  function openPk() {
    if (!pkWrap) buildPalette();
    pkWrap.classList.add('open');
    pkIn.value = ''; render('');
    setTimeout(function () { pkIn.focus(); }, 30);
  }
  function closePk() { if (pkWrap) pkWrap.classList.remove('open'); }

  document.addEventListener('keydown', function (e) {
    if ((e.ctrlKey || e.metaKey) && (e.key === 'k' || e.key === 'K')) {
      e.preventDefault();
      if (pkWrap && pkWrap.classList.contains('open')) closePk(); else openPk();
    } else if (e.key === 'Escape' && pkWrap && pkWrap.classList.contains('open')) {
      closePk();
    }
  });

  /* nav shortcut hint */
  var navIn = $('nav .navin');
  if (navIn) {
    var hint = document.createElement('button');
    hint.id = 'pkHint';
    hint.type = 'button';
    hint.innerHTML = '<i class="fas fa-terminal"></i><span class="lbl">SEARCH&nbsp;</span>⌘K';
    hint.setAttribute('aria-label', 'Open command palette');
    hint.addEventListener('click', openPk);
    navIn.appendChild(hint);
  }

  /* =============== 02 · TELEMETRY HUD =============== */
  var hud, spark, sparkCtx, flux = [], up0 = Date.now(), hudTimer = null;
  var visits = 1;
  try {
    visits = (parseInt(localStorage.getItem('rkp_visits') || '0', 10) || 0) + 1;
    localStorage.setItem('rkp_visits', String(visits));
  } catch (e) {}

  function buildHud() {
    hud = document.createElement('div');
    hud.id = 'hud';
    hud.innerHTML =
      '<div id="hudChip" role="button" tabindex="0" aria-label="Toggle telemetry HUD">' +
        '<span class="dot"></span>TELEMETRY<span class="tl" id="hudTl">LOW</span></div>' +
      '<div id="hudPanel">' +
        '<div class="hpHead"><span>// LIVE_TELEMETRY</span><em>sim-lab</em></div>' +
        '<div class="hpGrid">' +
          '<div class="hpCell"><b class="acc" id="hpClock">--:--:--</b><span>IST_LOCAL</span></div>' +
          '<div class="hpCell"><b id="hpUp">00:00</b><span>SESSION_UP</span></div>' +
          '<div class="hpCell"><b class="acc" id="hpVisit">#' + visits + '</b><span>OPERATIVE_VISIT</span></div>' +
          '<div class="hpCell"><b id="hpPkt">0</b><span>PKT/S_SIM</span></div>' +
          '<div class="hpCell"><b id="hpCore">—</b><span>CPU_CORES</span></div>' +
          '<div class="hpCell"><b id="hpNet">—</b><span>LINK</span></div>' +
        '</div>' +
        '<canvas id="hudSpark" width="260" height="38"></canvas>' +
        '<div class="hpBarWrap">' +
          '<div class="hpBar"><u>LAB_CPU</u><i><b id="barCpu" style="width:22%"></b></i><em id="emCpu">22%</em></div>' +
          '<div class="hpBar"><u>NET_IF</u><i><b id="barNet" style="width:14%"></b></i><em id="emNet">14%</em></div>' +
          '<div class="hpBar"><u>MEM_VM</u><i><b id="barMem" style="width:31%"></b></i><em id="emMem">31%</em></div>' +
        '</div>' +
      '</div>';
    document.body.appendChild(hud);
    $('#hudChip').addEventListener('click', toggleHud);
    $('#hudChip').addEventListener('keydown', function (e) { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); toggleHud(); } });
    spark = $('#hudSpark'); sparkCtx = spark.getContext('2d');
    for (var i = 0; i < 48; i++) flux.push(12 + Math.random() * 8);
    staticProbe();
    hudTimer = setInterval(tick, 1000);
    tick();
  }
  function toggleHud() {
    if (!hud) buildHud();
    hud.classList.toggle('open');
  }
  function staticProbe() {
    var cores = navigator.hardwareConcurrency;
    if (cores) $('#hpCore').textContent = cores + 'x';
    var mem = navigator.deviceMemory;
    if (cores && mem) $('#hpCore').textContent = cores + 'x · ~' + mem + 'GB';
    try {
      var c = navigator.connection;
      if (c) $('#hpNet').textContent = (c.effectiveType || '?').toUpperCase() + ' · ' + (c.downlink || '?') + 'Mb';
    } catch (e) {}
    try {
      if (navigator.getBattery) navigator.getBattery().then(function (b) {
        var el = $('#hpNet');
        if (el && !el.textContent) el.textContent = '';
      });
    } catch (e) {}
  }
  function pad(n) { return (n < 10 ? '0' : '') + n; }
  var wave = [22, 14, 31], wT = 0;
  function tick() {
    if (document.hidden) return;
    var d = new Date();
    var ist;
    try { ist = d.toLocaleTimeString('en-IN', { timeZone: 'Asia/Kolkata', hour12: false }); }
    catch (e) { ist = d.toLocaleTimeString(); }
    var up = Math.floor((Date.now() - up0) / 1000);
    var el;
    if ((el = $('#hpClock'))) el.textContent = ist;
    if ((el = $('#hpUp'))) el.textContent = pad(Math.floor(up / 60)) + ':' + pad(up % 60);

    wT += 1;
    wave = wave.map(function (v, i) {
      var t = v + Math.sin(wT / 3 + i * 2.1) * 6 + (Math.random() * 8 - 4);
      return Math.max(6, Math.min(96, t));
    });
    setBar('Cpu', wave[0]); setBar('Net', wave[1]); setBar('Mem', wave[2]);

    var pkt = Math.round(180 + wave[1] * 22 + Math.random() * 90);
    if ((el = $('#hpPkt'))) el.textContent = pkt;
    flux.push(Math.min(34, pkt / 60)); flux.shift();
    drawSpark();

    if (wT % 17 === 0) {
      var tl = $('#hudTl');
      if (tl) {
        var elv = Math.random() > 0.72;
        tl.textContent = elv ? 'ELEVATED' : 'LOW';
        tl.classList.toggle('elv', elv);
      }
    }
  }
  function setBar(k, v) {
    var b = $('#bar' + k), e = $('#em' + k);
    v = Math.round(v);
    if (b) b.style.width = v + '%';
    if (e) e.textContent = v + '%';
  }
  function drawSpark() {
    if (!sparkCtx) return;
    var w = spark.width, h = spark.height;
    sparkCtx.clearRect(0, 0, w, h);
    sparkCtx.beginPath();
    var step = w / (flux.length - 1);
    flux.forEach(function (v, i) {
      var y = h - (v / 34) * h;
      if (i === 0) sparkCtx.moveTo(0, y); else sparkCtx.lineTo(i * step, y);
    });
    sparkCtx.strokeStyle = accent();
    sparkCtx.lineWidth = 1.4;
    sparkCtx.shadowColor = accent();
    sparkCtx.shadowBlur = 6;
    sparkCtx.stroke();
    sparkCtx.lineTo(w, h); sparkCtx.lineTo(0, h); sparkCtx.closePath();
    sparkCtx.shadowBlur = 0;
    sparkCtx.globalAlpha = 0.08;
    sparkCtx.fillStyle = accent();
    sparkCtx.fill();
    sparkCtx.globalAlpha = 1;
  }
  buildHud();

  /* =============== 03 · BACK TO TOP (ring) =============== */
  var CIRC = 2 * Math.PI * 22;
  var topBtn = document.createElement('div');
  topBtn.id = 'topBtn';
  topBtn.setAttribute('role', 'button');
  topBtn.setAttribute('aria-label', 'Back to top');
  topBtn.innerHTML =
    '<svg viewBox="0 0 52 52"><circle class="ring" cx="26" cy="26" r="22"/>' +
    '<circle class="prog" cx="26" cy="26" r="22" stroke-dasharray="' + CIRC.toFixed(1) + '" stroke-dashoffset="' + CIRC.toFixed(1) + '"/></svg>' +
    '<span class="arr">↑</span>';
  document.body.appendChild(topBtn);
  var prog = $('.prog', topBtn);
  topBtn.addEventListener('click', function () { window.scrollTo({ top: 0, behavior: RM ? 'auto' : 'smooth' }); });
  function onScroll() {
    var max = document.documentElement.scrollHeight - window.innerHeight;
    var p = max > 0 ? window.scrollY / max : 0;
    prog.style.strokeDashoffset = String(CIRC * (1 - p));
    topBtn.classList.toggle('on', window.scrollY > 420);
  }
  window.addEventListener('scroll', onScroll, { passive: true });
  onScroll();

  /* =============== 04 · COPY CHIPS + CLIPBOARD =============== */
  function copyText(txt, msg) {
    function done() { toast(msg || 'COPIED → ' + txt); }
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(txt).then(done, function () { legacy(); });
    } else legacy();
    function legacy() {
      var ta = document.createElement('textarea');
      ta.value = txt; ta.style.position = 'fixed'; ta.style.opacity = '0';
      document.body.appendChild(ta); ta.select();
      try { document.execCommand('copy'); done(); } catch (e) { toast('COPY FAILED — select manually', true); }
      document.body.removeChild(ta);
    }
  }
  $$('#contact a.chan[href^="mailto:"]').forEach(function (a) { addChip(a, EMAIL, 'COPY_EMAIL'); });
  $$('#contact a.chan[href*="wa.me"]').forEach(function (a) { addChip(a, '+91 87009 13645', 'COPY_NUMBER'); });
  function addChip(a, txt, label) {
    if (a.querySelector('.copyChip')) return;
    var c = document.createElement('span');
    c.className = 'copyChip';
    c.innerHTML = '<i class="fas fa-copy"></i> ' + label;
    c.addEventListener('click', function (e) {
      e.preventDefault(); e.stopPropagation();
      copyText(txt, label.replace('_', ' ') + ' → ' + txt);
      c.classList.add('ok');
      setTimeout(function () { c.classList.remove('ok'); }, 900);
    });
    a.appendChild(c);
  }

  /* =============== 05 · RED ALERT (Konami ↑↑↓↓←→←→BA) =============== */
  var KONAMI = ['ArrowUp','ArrowUp','ArrowDown','ArrowDown','ArrowLeft','ArrowRight','ArrowLeft','ArrowRight','b','a'];
  var kBuf = [];
  document.addEventListener('keydown', function (e) {
    kBuf.push(e.key.length === 1 ? e.key.toLowerCase() : e.key);
    if (kBuf.length > KONAMI.length) kBuf.shift();
    if (KONAMI.every(function (k, i) { return kBuf[i] === k; })) {
      setRedAlert(!document.body.classList.contains('redalert'));
      kBuf = [];
    }
  });
  function setRedAlert(on) {
    document.body.classList.toggle('redalert', on);
    if (on) {
      var f = document.createElement('div');
      f.id = 'redFlash';
      document.body.appendChild(f);
      requestAnimationFrame(function () { f.style.opacity = '1'; });
      setTimeout(function () { f.style.opacity = '0'; setTimeout(function () { f.remove(); }, 600); }, 700);
      toast('RED ALERT MODE ENGAGED — access level: OVERWATCH', true);
    } else {
      toast('RED ALERT STAND DOWN — standard ops resumed');
    }
  }

  /* =============== 06 · MATRIX RAIN =============== */
  var rainCv, rainOn = false, rainRaf = 0, rainLast = 0, drops = [], rctx;
  var GLYPHS = 'アイウエオカキクケコサシスセソﾊﾋﾌ0123456789ABCDEF<>/\\{}[]$#*+=';
  function toggleRain() {
    rainOn = !rainOn;
    if (rainOn) startRain(); else stopRain();
    toast(rainOn ? 'MATRIX UPLINK ESTABLISHED' : 'MATRIX UPLINK SEVERED');
  }
  function startRain() {
    if (!rainCv) {
      rainCv = document.createElement('canvas');
      rainCv.id = 'mxRain';
      document.body.appendChild(rainCv);
      rctx = rainCv.getContext('2d');
    }
    rainCv.width = window.innerWidth;
    rainCv.height = window.innerHeight;
    var cols = Math.floor(rainCv.width / 16);
    drops = [];
    for (var i = 0; i < cols; i++) drops[i] = Math.random() * -50;
    rainCv.classList.add('on');
    rainRaf = requestAnimationFrame(rainLoop);
  }
  function stopRain() {
    if (rainCv) rainCv.classList.remove('on');
    cancelAnimationFrame(rainRaf);
  }
  function rainLoop(ts) {
    if (!rainOn) return;
    rainRaf = requestAnimationFrame(rainLoop);
    if (RM || document.hidden) return;
    if (ts - rainLast < 66) return;
    rainLast = ts;
    rctx.fillStyle = 'rgba(4,6,10,0.14)';
    rctx.fillRect(0, 0, rainCv.width, rainCv.height);
    rctx.fillStyle = accent();
    rctx.font = '14px "JetBrains Mono", monospace';
    for (var i = 0; i < drops.length; i++) {
      var ch = GLYPHS[(Math.random() * GLYPHS.length) | 0];
      rctx.fillText(ch, i * 16, drops[i] * 16);
      if (drops[i] * 16 > rainCv.height && Math.random() > 0.975) drops[i] = 0;
      drops[i]++;
    }
  }
  window.addEventListener('resize', function () { if (rainOn) startRain(); });

  /* =============== 07 · MAGNETIC BUTTONS + CARD TILT =============== */
  if (HOVER && !RM) {
    $$('.btn').forEach(function (b) {
      b.style.transition = 'transform .18s ease-out';
      b.addEventListener('pointermove', function (e) {
        var r = b.getBoundingClientRect();
        var dx = e.clientX - (r.left + r.width / 2);
        var dy = e.clientY - (r.top + r.height / 2);
        b.style.transform = 'translate(' + (dx * 0.18).toFixed(1) + 'px,' + (dy * 0.28).toFixed(1) + 'px)';
      });
      b.addEventListener('pointerleave', function () { b.style.transform = ''; });
    });
    $$('.pentest-card, .holo, #agent').forEach(function (c) {
      c.classList.add('tiltable');
      c.addEventListener('pointermove', function (e) {
        var r = c.getBoundingClientRect();
        var px = (e.clientX - r.left) / r.width - 0.5;
        var py = (e.clientY - r.top) / r.height - 0.5;
        c.style.transform = 'perspective(900px) rotateY(' + (px * 7).toFixed(2) + 'deg) rotateX(' + (-py * 7).toFixed(2) + 'deg)';
      });
      c.addEventListener('pointerleave', function () {
        c.style.transition = 'transform .5s cubic-bezier(.2,1,.3,1)';
        c.style.transform = '';
        setTimeout(function () { c.style.transition = ''; }, 500);
      });
    });
  }

  /* =============== 08 · KICKER SCRAMBLE FX =============== */
  var SCH = '!<>-_/[]{}=+*^?#01';
  function scramble(el) {
    var orig = el.getAttribute('data-orig') || el.textContent;
    el.setAttribute('data-orig', orig);
    if (RM || el.getAttribute('data-done')) return;
    el.setAttribute('data-done', '1');
    var frame = 0, total = Math.max(14, orig.length * 1.1);
    (function step() {
      var out = '', reveal = frame / total * orig.length;
      for (var i = 0; i < orig.length; i++) {
        out += i < reveal ? orig[i] : (orig[i] === ' ' ? ' ' : SCH[(Math.random() * SCH.length) | 0]);
      }
      el.textContent = out;
      if (frame++ < total) requestAnimationFrame(step);
      else el.textContent = orig;
    })();
  }
  try {
    var io = new IntersectionObserver(function (es) {
      es.forEach(function (en) {
        if (en.isIntersecting) { scramble(en.target); io.unobserve(en.target); }
      });
    }, { threshold: 0.4 });
    $$('.kicker').forEach(function (k) { io.observe(k); });
  } catch (e) {}

  /* =============== 09 · LIVE GITHUB TELEMETRY =============== */
  function ghStats() {
    var host = $('#dossier .wrap') || $('#dossier');
    if (!host) return;
    fetch('https://api.github.com/users/Ratan-patel')
      .then(function (r) { if (!r.ok) throw 0; return r.json(); })
      .then(function (d) {
        var s = document.createElement('div');
        s.id = 'ghStrip';
        s.innerHTML =
          '<span class="ghT">// LIVE_GITHUB_TELEMETRY</span>' +
          '<a class="ghV" href="https://github.com/Ratan-patel" target="_blank" rel="noopener">REPOS <b>' +
            (d.public_repos != null ? d.public_repos : '—') + '</b></a>' +
          '<a class="ghV" href="https://github.com/Ratan-patel?tab=followers" target="_blank" rel="noopener">FOLLOWERS <b>' +
            (d.followers != null ? d.followers : '—') + '</b></a>' +
          '<a class="ghV" href="https://github.com/Ratan-patel/ratan-os/releases" target="_blank" rel="noopener">RATAN_OS <b>RELEASES</b></a>' +
          '<span class="ghV" style="cursor:default">SYNC <b>' + new Date().toLocaleTimeString('en-IN', { hour12: false }) + '</b></span>';
        host.appendChild(s);
      })
      .catch(function () { /* offline / rate-limited — stay silent */ });
  }
  ghStats();

  /* =============== 10 · CONSOLE SIGNATURE =============== */
  try {
    console.log('%c RATAN_PATEL.SEC %c ACCESS GRANTED ',
      'background:#00ffc8;color:#04060a;font-weight:bold;padding:3px 6px;border-radius:3px 0 0 3px',
      'background:#04060a;color:#00ffc8;padding:3px 6px;border:1px solid #00ffc8;border-radius:0 3px 3px 0');
    console.log('%cPress CTRL+K — command palette. Try the KONAMI code. Authorized use only.',
      'color:#8ba0b2;font-family:monospace');
  } catch (e) {}

  /* =============== 11 · PWA SERVICE WORKER =============== */
  if ('serviceWorker' in navigator && /^https?:/.test(window.location.protocol)) {
    window.addEventListener('load', function () {
      navigator.serviceWorker.register('sw.js').catch(function () {});
    });
  }
})();
