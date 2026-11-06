/* RatanSec Super Agent — dashboard (vanilla JS, zero dependency) */
"use strict";

const $ = (s) => document.querySelector(s);
const $$ = (s) => Array.from(document.querySelectorAll(s));

const state = {
  sessionId: "s-" + Math.random().toString(36).slice(2, 10),
  status: null,
  sections: [],
  records: [],
  follows: {},
  termMode: "catalog",
  termHist: [],
  termIdx: -1,
  activeRun: "",
};

const esc = (s) =>
  String(s ?? "").replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");

function toast(msg, kind = "") {
  const el = $("#toast");
  el.textContent = msg;
  el.className = "toast " + kind;
  clearTimeout(el._t);
  el._t = setTimeout(() => (el.className = "toast hidden"), 4000);
}

async function api(path, { method = "GET", body = null } = {}) {
  const res = await fetch(path, {
    method,
    credentials: "same-origin",
    headers: body ? { "Content-Type": "application/json" } : {},
    body: body ? JSON.stringify(body) : null,
  });
  let data = null;
  try { data = await res.json(); } catch (_) {}
  if (!res.ok) {
    if (res.status === 401) showLogin();
    throw new Error((data && data.detail) || "HTTP " + res.status);
  }
  return data;
}

/* ---------------- markdown (mini) ---------------- */
function md(mdText) {
  const lines = String(mdText || "").split("\n");
  let out = "", inCode = false, inList = false, inTable = false;
  const closeList = () => { if (inList) { out += "</ul>"; inList = false; } };
  const closeTable = () => { if (inTable) { out += "</table>"; inTable = false; } };
  for (const raw of lines) {
    const line = raw.replace(/\s+$/, "");
    if (line.startsWith("```")) { closeList(); closeTable(); out += inCode ? "</code></pre>" : "<pre><code>"; inCode = !inCode; continue; }
    if (inCode) { out += esc(line) + "\n"; continue; }
    if (!line.trim()) { closeList(); closeTable(); continue; }
    if (line.startsWith("|") && line.endsWith("|")) {
      closeList();
      const cells = line.slice(1, -1).split("|").map((c) => c.trim());
      if (cells.every((c) => /^:?-{2,}:?$/.test(c))) continue;
      if (!inTable) { out += "<table><thead><tr>" + cells.map((c) => `<th>${inline(c)}</th>`).join("") + "</tr></thead><tbody>"; inTable = true; }
      else out += "<tr>" + cells.map((c) => `<td>${inline(c)}</td>`).join("") + "</tr>";
      continue;
    }
    closeTable();
    const h = line.match(/^(#{1,6})\s+(.*)$/);
    if (h) { closeList(); out += `<h${h[1].length}>${inline(h[2])}</h${h[1].length}>`; continue; }
    if (/^[-*]\s/.test(line)) { if (!inList) { out += "<ul>"; inList = true; } out += `<li>${inline(line.slice(2))}</li>`; continue; }
    if (line.startsWith("> ")) { closeList(); out += `<blockquote>${inline(line.slice(2))}</blockquote>`; continue; }
    if (line.trim() === "---") { closeList(); out += "<hr>"; continue; }
    closeList(); out += `<p>${inline(line)}</p>`;
  }
  closeList(); closeTable();
  if (inCode) out += "</code></pre>";
  return out;
}
function inline(t) {
  return esc(t)
    .replace(/`([^`]+)`/g, "<code>$1</code>")
    .replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>")
    .replace(/\[([^\]]+)\]\((https?:[^)]+)\)/g, '<a href="$2" target="_blank" rel="noopener">$1</a>');
}

/* ---------------- auth ---------------- */
function showLogin() { $("#login").classList.remove("hidden"); }
function hideLogin() { $("#login").classList.add("hidden"); }

$("#login-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const value = $("#login-password").value.trim();
  if (!value) return;
  try {
    await api("/api/login", { method: "POST", body: { password: value } });
    localStorage.setItem("sa_token", value);
    hideLogin();
    boot();
  } catch (err) {
    // ho sakta hai ye API token ho
    localStorage.setItem("sa_token", value);
    hideLogin();
    boot();
  }
});

$("#btn-logout").addEventListener("click", async () => {
  await api("/api/logout", { method: "POST" }).catch(() => {});
  showLogin();
});

/* ---------------- tabs ---------------- */
$$(".rail-btn").forEach((btn) =>
  btn.addEventListener("click", () => {
    $$(".rail-btn").forEach((b) => b.classList.remove("active"));
    btn.classList.add("active");
    $$(".tab").forEach((t) => t.classList.remove("active"));
    $("#tab-" + btn.dataset.tab).classList.add("active");
    const t = btn.dataset.tab;
    if (t === "runs") loadRuns();
    if (t === "approvals") loadApprovals();
    if (t === "records") loadRecords();
    if (t === "reports") loadReports();
    if (t === "audit") loadAudit();
    if (t === "arsenal") renderArsenal();
  })
);

/* ---------------- status ---------------- */
async function loadStatus() {
  const s = await api("/api/status");
  state.status = s;
  const ai = $("#c-ai");
  ai.textContent = s.ai.configured ? "AI " + s.ai.model.split("/").pop() : "AI off";
  ai.className = "chip " + (s.ai.configured ? "ok" : "warn");
  $("#c-tools").textContent = `Tools ${s.tools_total}`;
  $("#c-roe").textContent = `RoE ${s.records_active} active`;
  $("#c-roe").className = "chip " + (s.records_active ? "ok" : "warn");
  $("#c-shell").textContent = "Shell " + (s.shell_allowed ? "on" : "off");
  $("#c-shell").className = "chip " + (s.shell_allowed ? "" : "warn");
  $("#c-appr").classList.toggle("hidden", !s.approvals_pending);
  $("#c-appr").textContent = "Approvals " + s.approvals_pending;
  $("#rail-appr").classList.toggle("hidden", !s.approvals_pending);
  $("#rail-appr").textContent = s.approvals_pending;

  const banners = $("#banners");
  banners.innerHTML = "";
  if (!s.records_active) {
    banners.innerHTML += `<div class="banner">⚠ Koi active authorization record nahi — agent target scan nahi karega. <b>Records</b> tab me engagement record banao.</div>`;
  }
  if (!s.ai.configured) {
    banners.innerHTML += `<div class="banner bad">AI key set nahi (SUPERAGENT_API_KEY). Terminal + manual tools chalenge, chat nahi.</div>`;
  }
  if (s.auth_required === false) {
    banners.innerHTML += `<div class="banner bad">APP_PASSWORD/token set nahi — dashboard khula hai. Deploy se pehle set karo.</div>`;
  }
  return s;
}

/* ---------------- chat ---------------- */
function addMsg(role, html) {
  const el = document.createElement("div");
  el.className = "msg " + role;
  const icon = role === "user" ? "🧑‍💻" : role === "sys" ? "⚑" : "🥷";
  el.innerHTML = `<div class="avatar">${icon}</div><div class="body">${html}</div>`;
  $("#chat").appendChild(el);
  $("#chat").scrollTop = $("#chat").scrollHeight;
  return el;
}

function typing() {
  const el = addMsg("agent", `<span class="typing"><span>●</span><span>●</span><span>●</span> soch raha hoon…</span>`);
  return el;
}

function stepsHtml(steps) {
  return (steps || [])
    .map((s) => {
      if (s.type === "run") return `<div class="step run">▶ ${esc(s.command || s.run_id)}</div>`;
      if (s.type === "approval") return `<div class="step approval">⚑ approval: ${esc(s.summary || "")}</div>`;
      if (s.type === "report") return `<div class="step">📄 ${esc(s.file)}</div>`;
      return `<div class="step">${esc(s.tool || "tool")}</div>`;
    })
    .join("");
}

function jobHtml(job) {
  if (!job) return "";
  const badge = job.status === "done" ? "ok" : job.status === "error" || job.status === "timeout" ? "bad" : "warn";
  return `<div class="step">▶ <code>${esc(job.command || "")}</code>
    <span class="chip ${badge}" style="margin-left:6px">${esc(job.status)}${job.exit_code !== null && job.exit_code !== undefined ? " · exit " + job.exit_code : ""} · ${job.duration || 0}s</span></div>`;
}

async function sendChat(text) {
  if (!text.trim()) return;
  addMsg("user", `<p>${esc(text)}</p>`);
  $("#chat-input").value = "";
  const t = typing();
  try {
    const data = await api("/api/agent/chat", {
      method: "POST",
      body: { message: text, session_id: state.sessionId, auto_approve: $("#auto-approve").checked, model: $("#model").value.trim() || null },
    });
    state.sessionId = data.session_id || state.sessionId;
    t.remove();
    const el = addMsg("agent", stepsHtml(data.steps) + jobHtml(data.job) + `<div>${md(data.reply || "")}</div>`);
    if (data.awaiting_approval) {
      const p = data.needs_approval || {};
      addMsg("sys", `<p><b>Approval chahiye</b> — <code>${esc(p.id)}</code></p>
        <pre class="pre" style="font-family:var(--mono);font-size:11.5px;color:var(--muted)">${esc(p.command || "")}</pre>
        <div class="row">
          <button class="btn primary sm" onclick="decide('${p.id}', true)">Approve</button>
          <button class="btn danger sm" onclick="decide('${p.id}', false)">Deny</button>
        </div>`);
      loadStatus();
      pollFollowup(el);
    }
    if (data.runs && data.runs.length) state.lastRuns = data.runs;
  } catch (err) {
    t.remove();
    addMsg("sys", `<p>${esc(err.message)}</p>`);
  }
}

async function pollFollowup(targetEl) {
  let ticks = 0;
  clearInterval(state.followTimer);
  state.followTimer = setInterval(async () => {
    ticks++;
    if (ticks > 120) return clearInterval(state.followTimer);
    try {
      const data = await api("/api/agent/followup/" + state.sessionId);
      if (data.status === "ready") {
        clearInterval(state.followTimer);
        await api("/api/agent/followup/" + state.sessionId, { method: "DELETE" }).catch(() => {});
        const el = addMsg("agent", `<div class="step">✅ approval ke baad</div>` + stepsHtml(data.steps) + jobHtml(data.job) + `<div>${md(data.reply || "")}</div>`);
        el.scrollIntoView({ behavior: "smooth", block: "end" });
        loadStatus();
      } else if (data.status === "error") {
        clearInterval(state.followTimer);
        addMsg("sys", `<p>${esc(data.reply || "error")}</p>`);
      }
    } catch (_) {}
  }, 3000);
}

window.decide = async (id, approved) => {
  try {
    const data = await api("/api/approvals/" + id, { method: "POST", body: { approved } });
    toast(data.message, "ok");
    loadStatus();
    if (approved) pollFollowup();
  } catch (err) {
    toast(err.message, "err");
  }
};

$("#chat-form").addEventListener("submit", (e) => { e.preventDefault(); sendChat($("#chat-input").value); });
$("#chat-input").addEventListener("keydown", (e) => {
  if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); sendChat($("#chat-input").value); }
});
$("#btn-clear").addEventListener("click", async () => {
  await api("/api/agent/reset", { method: "POST", body: { session_id: state.sessionId } }).catch(() => {});
  $("#chat").innerHTML = "";
  state.sessionId = "s-" + Math.random().toString(36).slice(2, 10);
  greet();
});

const QUICK = [
  "Kaunse tools available hain? sections ke hisaab se batao",
  "Records dekho aur batao main kis target par kaam kar sakta hoon",
  "lab.local ka quick recon karo (scope check ke baad)",
  "Is target par critical/high CVE check karo nuclei se",
  "Ab tak ke findings ka report banao",
];
function renderQuick() {
  const box = $("#quick");
  box.innerHTML = "";
  QUICK.forEach((q) => {
    const b = document.createElement("button");
    b.className = "chip-btn";
    b.textContent = q;
    b.onclick = () => sendChat(q);
    box.appendChild(b);
  });
}

function greet() {
  $("#chat").innerHTML = "";
  addMsg(
    "agent",
    md(
      "**RatanSec Super Agent** ready.\n\nMain authorized targets par Kali tools chalata hoon — recon, enumeration, vuln analysis, web/API, approval ke baad gaining-access/exploitation, aur evidence-backed reporting.\n\n" +
        "Shuru karo:\n- *\"lab.local ka recon karo\"*\n- *\"Records dekho\"*\n- *\"nuclei se critical check karo\"*\n\n" +
        "> Har command ka record audit chain me jata hai. Intrusive tools hamesha approval maangte hain."
    )
  );
}

/* ---------------- terminal ---------------- */
function tprint(html, cls = "") {
  const el = document.createElement("div");
  if (cls) el.className = cls;
  el.innerHTML = html;
  $("#term").appendChild(el);
  $("#term").scrollTop = $("#term").scrollHeight;
}

async function termRun(line) {
  tprint(`<span class="cmd">${state.termMode === "shell" ? "!" : "$"} ${esc(line)}</span>`);
  const parts = line.trim().split(/\s+/);
  if (!parts[0]) return;
  if (parts[0] === "help") {
    tprint(
      `<span class="dim">catalog mode: tool target flag=value  (jaise: nmap-vuln lab.local ports=80,443)
shell mode : raw linux command (approval + guard)
  tool list : arsenal tab  ·  switch   : button se mode badlo
  agent <text> -> AI ko bhejo</span>`
    );
    return;
  }
  if (state.termMode === "shell" || line.startsWith("!")) {
    const cmd = line.replace(/^!/, "");
    try {
      const data = await api("/api/command/shell", { method: "POST", body: { command: cmd } });
      if (data.status === "approval_required") {
        tprint(`<span class="warn">⚑ approval chahiye: ${esc(data.approval.id)} — Approvals tab me approve karo</span>`);
        loadStatus();
        return;
      }
      follow(data.run);
    } catch (err) {
      tprint(`<span class="err">${esc(err.message)}</span>`);
    }
    return;
  }
  const tool = parts[0];
  let target = "";
  const flags = {};
  for (const token of parts.slice(1)) {
    if (token.includes("=")) {
      const [k, ...v] = token.split("=");
      flags[k] = v.join("=");
    } else if (!target) target = token;
  }
  try {
    const data = await api("/api/command", { method: "POST", body: { tool, target, flags } });
    if (data.status === "approval_required") {
      tprint(`<span class="warn">⚑ approval chahiye: ${esc(data.approval.id)} — Approvals tab</span>`);
      loadStatus();
      return;
    }
    follow(data.run);
  } catch (err) {
    tprint(`<span class="err">${esc(err.message)}</span>`);
  }
}

async function follow(run) {
  if (!run) return;
  state.activeRun = run.id;
  const line = document.createElement("div");
  line.className = "dim";
  line.textContent = `▶ ${run.display}  [${run.status}]`;
  $("#term").appendChild(line);
  const pre = document.createElement("pre");
  pre.style.margin = "2px 0 8px";
  $("#term").appendChild(pre);
  let seen = 0;
  for (let i = 0; i < 900; i++) {
    await new Promise((r) => setTimeout(r, 1200));
    let data;
    try { data = await api("/api/runs/" + run.id); } catch (_) { return; }
    const r = data.run;
    const out = r.output || "";
    if (out.length > seen) {
      pre.textContent += out.slice(seen);
      seen = out.length;
      $("#term").scrollTop = $("#term").scrollHeight;
    }
    line.textContent = `▶ ${r.display}  [${r.status}${r.exit_code !== null ? " · exit " + r.exit_code : ""} · ${r.duration}s]`;
    if (!["running", "queued"].includes(r.status)) {
      if (r.error) {
        const e = document.createElement("div");
        e.className = "err";
        e.textContent = r.error;
        $("#term").appendChild(e);
      }
      return;
    }
  }
}

$("#term-form").addEventListener("submit", (e) => {
  e.preventDefault();
  const line = $("#term-cmd").value;
  $("#term-cmd").value = "";
  if (!line.trim()) return;
  state.termHist.push(line);
  state.termIdx = state.termHist.length;
  termRun(line);
});
$("#term-cmd").addEventListener("keydown", (e) => {
  if (e.key === "ArrowUp") {
    e.preventDefault();
    if (state.termIdx > 0) $("#term-cmd").value = state.termHist[--state.termIdx] || "";
  } else if (e.key === "ArrowDown") {
    e.preventDefault();
    if (state.termIdx < state.termHist.length - 1) $("#term-cmd").value = state.termHist[++state.termIdx] || "";
    else { state.termIdx = state.termHist.length; $("#term-cmd").value = ""; }
  }
});
$("#btn-term-mode").addEventListener("click", () => {
  state.termMode = state.termMode === "catalog" ? "shell" : "catalog";
  const shell = state.termMode === "shell";
  $("#btn-term-mode").textContent = shell ? "Switch to catalog" : "Switch to shell";
  $("#term-mode-label").textContent = "mode: " + state.termMode;
  $("#term-prompt").textContent = shell ? "!" : "$";
  $("#term-cmd").placeholder = shell ? "uname -a; id; ip a" : "nmap-vuln lab.local ports=80,443";
});
$("#btn-term-clear").addEventListener("click", () => ($("#term").innerHTML = ""));

/* ---------------- arsenal ---------------- */
let arsenalLoaded = false;
async function renderArsenal(force = false) {
  if (arsenalLoaded && !force) return;
  const data = await api("/api/sections");
  state.sections = data.sections;
  arsenalLoaded = true;
  $("#arsenal-summary").textContent = `${data.total} tools · ${data.intrusive} approval-only`;
  drawArsenal();
}

function drawArsenal() {
  const q = ($("#arsenal-search").value || "").toLowerCase();
  const box = $("#arsenal");
  box.innerHTML = "";
  state.sections.forEach((sec) => {
    const tools = sec.tools.filter((t) => !q || t.name.toLowerCase().includes(q) || t.summary.toLowerCase().includes(q));
    if (!tools.length) return;
    const wrap = document.createElement("div");
    wrap.className = "section";
    wrap.innerHTML = `<div class="section-head"><h3>${sec.icon} ${esc(sec.title)}</h3>
      <span class="count">${sec.count} tools</span></div>
      <div class="section-body"></div>`;
    const body = wrap.querySelector(".section-body");
    tools.forEach((t) => {
      const el = document.createElement("div");
      el.className = "tool";
      el.innerHTML = `
        <div class="tool-top"><span class="dot ${t.installed ? "on" : ""}"></span><b>${esc(t.name)}</b>
          ${t.intrusive ? '<span class="tag">approval</span>' : ""}</div>
        <p>${esc(t.summary)}</p>
        <div class="flags">flags: ${esc(Object.keys(t.flags).join(", ") || "—")}</div>
        <div class="run-row">
          <input placeholder="target (authorized)" value="">
          <button class="btn sm ghost">▶</button>
        </div>`;
      const input = el.querySelector("input");
      el.querySelector("button").onclick = () => {
        const target = input.value.trim();
        const line = `${t.name} ${target}`.trim();
        $$(".rail-btn").forEach((b) => b.dataset.tab === "term" && b.click());
        $("#term-cmd").value = line;
        $("#term-cmd").focus();
      };
      body.appendChild(el);
    });
    box.appendChild(wrap);
  });
}
$("#arsenal-search").addEventListener("input", drawArsenal);

/* ---------------- runs ---------------- */
async function loadRuns() {
  const data = await api("/api/runs?limit=40");
  const list = $("#runs-list");
  list.innerHTML = "";
  (data.runs || []).forEach((r) => {
    const el = document.createElement("div");
    el.className = "list-item" + (r.id === state.activeRun ? " active" : "");
    const cls = r.status === "done" ? "ok" : r.status === "running" ? "warn" : r.status === "error" || r.status === "timeout" ? "bad" : "";
    el.innerHTML = `<div class="t">${esc(r.display.slice(0, 90))}</div>
      <div class="meta"><span class="chip ${cls}">${esc(r.status)}</span>
      <span class="muted small">${r.duration}s</span></div>`;
    el.onclick = () => openRun(r.id);
    list.appendChild(el);
  });
  if (!data.runs || !data.runs.length) list.innerHTML = `<p class="muted small">Abhi koi run nahi.</p>`;
}

async function openRun(id) {
  state.activeRun = id;
  const data = await api("/api/runs/" + id);
  const r = data.run;
  $("#run-detail").innerHTML = `
    <h3 style="margin-top:0;font-size:14px"><code>${esc(r.display)}</code></h3>
    <div class="meta"><span class="chip">${esc(r.status)}</span>
      <span class="muted small">exit ${r.exit_code} · ${r.duration}s · ${r.mode}</span></div>
    <pre>${esc(r.output || "(no output)")}</pre>
    ${r.error ? `<p class="muted small">${esc(r.error)}</p>` : ""}
    <button class="btn danger sm" onclick="cancelRun('${r.id}')">Cancel</button>`;
  loadRuns();
}
window.cancelRun = async (id) => {
  await api(`/api/runs/${id}/cancel`, { method: "POST" }).catch((e) => toast(e.message, "err"));
  toast("cancel request bheji", "ok");
};
$("#btn-runs-refresh").addEventListener("click", loadRuns);

/* ---------------- approvals ---------------- */
async function loadApprovals() {
  const data = await api("/api/approvals");
  const box = $("#approvals");
  box.innerHTML = "";
  const items = (data.approvals || []).filter((a) => a.status === "pending");
  const past = (data.approvals || []).filter((a) => a.status !== "pending").slice(0, 15);
  if (!items.length) box.innerHTML = `<p class="muted small">Koi pending approval nahi.</p>`;
  items.forEach((a) => {
    const el = document.createElement("div");
    el.className = "card pending";
    el.innerHTML = `<h4>⚑ ${esc(a.summary)}</h4>
      <div class="pre">${esc(a.command)}</div>
      <div class="meta"><span>${esc(a.kind)}</span><span>${esc(a.target)}</span>
        <span>${esc(a.actor)}</span><span>expires ${a.expires_in}s</span></div>
      <div class="acts">
        <button class="btn primary sm">Approve</button>
        <button class="btn danger sm">Deny</button>
      </div>`;
    el.querySelector(".btn.primary").onclick = () => decide(a.id, true).then(loadApprovals);
    el.querySelector(".btn.danger").onclick = () => decide(a.id, false).then(loadApprovals);
    box.appendChild(el);
  });
  if (past.length) {
    const h = document.createElement("h3");
    h.style.cssText = "grid-column:1/-1;font-size:13px;margin:16px 0 0;color:var(--muted)";
    h.textContent = "History";
    box.appendChild(h);
    past.forEach((a) => {
      const el = document.createElement("div");
      el.className = "card";
      el.innerHTML = `<h4>${esc(a.summary)}</h4>
        <div class="meta"><span class="chip">${esc(a.status)}</span><span>${esc(a.decided_by || "-")}</span></div>`;
      box.appendChild(el);
    });
  }
}
$("#btn-appr-refresh").addEventListener("click", loadApprovals);

/* ---------------- records ---------------- */
async function loadRecords() {
  const data = await api("/api/records");
  state.records = data.records || [];
  const box = $("#records");
  box.innerHTML = "";
  if (!state.records.length) box.innerHTML = `<p class="muted small">Koi record nahi — upar form se banao.</p>`;
  state.records.forEach((r) => {
    const el = document.createElement("div");
    el.className = "card" + (r.active ? " pending" : "");
    el.innerHTML = `<h4>${esc(r.client)} ${r.active ? '<span class="chip ok">ACTIVE</span>' : '<span class="chip">inactive</span>'}</h4>
      <div class="meta"><span>${esc(r.id)}</span><span>${esc(r.start_str)} → ${esc(r.end_str)}</span></div>
      <div class="pre">scope: ${esc(r.scope_text)}\nsections: ${esc(r.sections.join(", "))}\nsigner: ${esc(r.signer)} · ref: ${esc(r.signature)}</div>
      ${r.notes ? `<p class="muted small">${esc(r.notes)}</p>` : ""}
      ${r.active ? `<div class="acts"><button class="btn danger sm">Revoke</button></div>` : ""}`;
    const btn = el.querySelector("button");
    if (btn) btn.onclick = async () => {
      await api(`/api/records/${r.id}/revoke`, { method: "POST" }).catch((e) => toast(e.message, "err"));
      loadRecords(); loadStatus();
    };
    box.appendChild(el);
  });
  renderSectionPicks();
}

function renderSectionPicks() {
  const box = $("#roe-sections");
  if (box.dataset.done) return;
  box.dataset.done = "1";
  box.style.display = "contents";
  const all = document.createElement("label");
  all.innerHTML = `<input type="checkbox" name="roe-section" value="all" checked> all sections`;
  box.appendChild(all);
  // "all" aur specific sections saath me na chalein
  box.addEventListener("change", (e) => {
    if (e.target.name !== "roe-section") return;
    const boxes = Array.from(box.querySelectorAll('input[name="roe-section"]'));
    if (e.target.value === "all" && e.target.checked) boxes.forEach((b) => { if (b !== e.target) b.checked = false; });
    else if (e.target.value !== "all" && e.target.checked) boxes[0].checked = false;
    if (!boxes.some((b) => b.checked)) boxes[0].checked = true;
  });
  api("/api/sections").then((data) => {
    data.sections.forEach((s) => {
      const l = document.createElement("label");
      l.innerHTML = `<input type="checkbox" name="roe-section" value="${s.id}"> ${esc(s.title)}`;
      box.appendChild(l);
    });
  });
}

$("#record-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const f = e.target;
  const picked = Array.from(f.querySelectorAll('input[name="roe-section"]:checked')).map((i) => i.value);
  const sections = picked.includes("all") || !picked.length ? ["all"] : picked.filter((v) => v !== "all");
  const scope = f.scope.value.split(",").map((s) => s.trim()).filter(Boolean);
  try {
    const data = await api("/api/records", {
      method: "POST",
      body: {
        client: f.client.value, contact: f.contact.value, scope, sections,
        start: f.start.value, end: f.end.value, signer: f.signer.value,
        signature: f.signature.value, emergency: f.emergency.value, notes: f.notes.value,
      },
    });
    toast("Record saved: " + data.record.id, "ok");
    f.reset();
    loadRecords(); loadStatus();
  } catch (err) {
    toast(err.message, "err");
  }
});
$("#btn-seed").addEventListener("click", async () => {
  try {
    const data = await api("/api/records/seed-demo", { method: "POST" });
    toast("Demo record add hua: " + data.record.id, "ok");
    loadRecords(); loadStatus();
  } catch (err) { toast(err.message, "err"); }
});
$("#btn-chain").addEventListener("click", async () => {
  const data = await api("/api/audit/verify");
  toast(data.records.ok ? "RoE chain intact ✔" : "⚠ " + data.records.message, data.records.ok ? "ok" : "err");
});

/* ---------------- reports ---------------- */
async function loadReports() {
  const data = await api("/api/reports");
  const list = $("#reports-list");
  list.innerHTML = "";
  if (!data.reports.length) list.innerHTML = `<p class="muted small">Koi report nahi — agent se bolo "report banao".</p>`;
  data.reports.forEach((r) => {
    const el = document.createElement("div");
    el.className = "list-item";
    el.innerHTML = `<div class="t">${esc(r.name)}</div><div class="meta muted small">${esc(r.modified_str)} · ${(r.size / 1024).toFixed(1)} KB</div>`;
    el.onclick = () => openReport(r.name);
    list.appendChild(el);
  });
}
async function openReport(name) {
  const data = await api("/api/reports/" + encodeURIComponent(name));
  $("#report-detail").innerHTML = `<div class="row" style="justify-content:space-between">
      <h3 style="margin:0;font-size:14px">${esc(name)}</h3>
      <button class="btn ghost sm" id="btn-print">🖨 Print / PDF</button>
    </div><div class="md">${md(data.content)}</div>`;
  $("#btn-print").onclick = () => {
    const w = window.open("", "_blank");
    w.document.write(`<html><head><title>${esc(name)}</title><style>
      body{font:13px/1.6 system-ui;max-width:820px;margin:32px auto;padding:0 20px;color:#111}
      pre{background:#f4f4f6;padding:10px;overflow:auto}table{border-collapse:collapse}td,th{border:1px solid #ccc;padding:4px 8px}
    </style></head><body>${md(data.content)}</body></html>`);
    w.document.close();
    setTimeout(() => w.print(), 300);
  };
}
$("#btn-reports-refresh").addEventListener("click", loadReports);

/* ---------------- audit ---------------- */
async function loadAudit() {
  const data = await api("/api/audit?limit=150");
  const tbody = $("#audit-table tbody");
  tbody.innerHTML = "";
  (data.events || []).forEach((e) => {
    const tr = document.createElement("tr");
    const detail = Object.fromEntries(Object.entries(e).filter(([k]) => !["ts", "time", "event", "prev", "hash"].includes(k)));
    tr.innerHTML = `<td>${esc((e.time || "").slice(11))}</td><td>${esc(e.event)}</td><td>${esc(JSON.stringify(detail).slice(0, 260))}</td>`;
    tbody.appendChild(tr);
  });
  const v = data.verify || {};
  $("#audit-verify").innerHTML = v.ok
    ? `<span class="ok">✔ Audit chain intact</span> — ${v.records} records (hash chained).`
    : `<span class="bad">⚠ Chain problem:</span> ${esc(v.message || "")}`;
}
$("#btn-verify").addEventListener("click", loadAudit);
$("#btn-bundle").addEventListener("click", async () => {
  try {
    const data = await api("/api/evidence/bundle", { method: "POST" });
    toast("Bundle ready: " + data.file, "ok");
    window.location = data.download;
  } catch (err) { toast(err.message, "err"); }
});

/* ---------------- boot ---------------- */
async function boot() {
  try {
    const s = await loadStatus();
    if (s.auth_required && !s.authenticated) { showLogin(); return; }
    hideLogin();
    greet();
    renderQuick();
    loadApprovals().catch(() => {});
    setInterval(async () => { try { await loadStatus(); } catch (_) {} }, 15000);
  } catch (err) {
    console.error(err);
    showLogin();
  }
}

(async () => {
  const token = localStorage.getItem("sa_token");
  if (token) {
    // token mode: header ke through har request
    const origFetch = window.fetch;
    window.fetch = (url, opts = {}) => {
      opts.headers = { ...(opts.headers || {}), "X-Agent-Token": token };
      return origFetch(url, opts);
    };
  }
  boot();
})();
