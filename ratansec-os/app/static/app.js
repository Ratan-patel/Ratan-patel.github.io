/* RatanSec OS — dashboard front-end (vanilla JS, koi dependency nahi) */
"use strict";

const $ = (sel) => document.querySelector(sel);
const $$ = (sel) => Array.from(document.querySelectorAll(sel));

const state = {
  status: null,
  profile: "quick",
  runs: [],
  activeRunId: null,
  conversationId: "conv-" + Math.random().toString(36).slice(2, 10),
  messages: [],
  followupTimer: null,
  followupWaits: 0,
  tools: [],
  profiles: [],
};

/* ------------------------------------------------------------------ utils */
const esc = (s) =>
  String(s ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");

function toast(message, kind = "") {
  const el = $("#toast");
  el.textContent = message;
  el.className = "toast " + (kind === "ok" ? "ok" : kind === "err" ? "err" : "");
  el.classList.remove("hidden");
  clearTimeout(el._t);
  el._t = setTimeout(() => el.classList.add("hidden"), 4200);
}

async function api(path, { method = "GET", body = null } = {}) {
  const res = await fetch(path, {
    method,
    credentials: "same-origin",
    headers: body ? { "Content-Type": "application/json" } : {},
    body: body ? JSON.stringify(body) : null,
  });
  let data = null;
  try {
    data = await res.json();
  } catch (_) {
    /* empty body */
  }
  if (!res.ok) {
    if (res.status === 401) showLogin();
    const detail = data && data.detail ? data.detail : `HTTP ${res.status}`;
    throw new Error(detail);
  }
  return data;
}

/* --------------------------------------------------- mini markdown render */
function mdToHtml(md) {
  let text = esc(md || "");
  const blocks = [];
  text = text.replace(/```([\s\S]*?)```/g, (_, code) => {
    blocks.push(code.replace(/^\n/, ""));
    return `\u0000BLOCK${blocks.length - 1}\u0000`;
  });

  const lines = text.split("\n");
  const out = [];
  let list = null;
  let table = null;

  const closeList = () => {
    if (list) {
      out.push(`</${list}>`);
      list = null;
    }
  };
  const closeTable = () => {
    if (table) {
      out.push("</tbody></table>");
      table = null;
    }
  };

  const inline = (s) =>
    s
      .replace(/`([^`]+)`/g, "<code>$1</code>")
      .replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>")
      .replace(/(^|\s)\*([^*\n]+)\*/g, "$1<em>$2</em>")
      .replace(/\[([^\]]+)\]\((https?:[^)\s]+)\)/g, '<a href="$2" target="_blank" rel="noopener">$1</a>');

  for (const raw of lines) {
    const line = raw.replace(/\s+$/, "");

    if (/^\u0000BLOCK\d+\u0000$/.test(line.trim()) || line.includes("\u0000BLOCK")) {
      closeList();
      closeTable();
      out.push(line.replace(/\u0000BLOCK(\d+)\u0000/g, (_, i) => `<pre class="term">${blocks[Number(i)]}</pre>`));
      continue;
    }

    const tableRow = /^\s*\|(.+)\|\s*$/.exec(line);
    if (tableRow) {
      const cells = tableRow[1].split("|").map((c) => c.trim());
      if (/^[\s|:-]+$/.test(line)) continue;
      if (!table) {
        closeList();
        out.push('<table><thead><tr>' + cells.map((c) => `<th>${inline(c)}</th>`).join("") + "</tr></thead><tbody>");
        table = true;
      } else {
        out.push("<tr>" + cells.map((c) => `<td>${inline(c)}</td>`).join("") + "</tr>");
      }
      continue;
    }
    closeTable();

    const heading = /^(#{1,6})\s+(.*)$/.exec(line);
    if (heading) {
      closeList();
      const level = Math.min(4, heading[1].length + 1);
      out.push(`<h${level}>${inline(heading[2])}</h${level}>`);
      continue;
    }

    const bullet = /^\s*[-*+]\s+(.*)$/.exec(line);
    const numbered = /^\s*\d+[.)]\s+(.*)$/.exec(line);
    if (bullet || numbered) {
      const want = bullet ? "ul" : "ol";
      if (list !== want) {
        closeList();
        out.push(`<${want}>`);
        list = want;
      }
      out.push(`<li>${inline((bullet || numbered)[1])}</li>`);
      continue;
    }
    closeList();

    if (/^\s*&gt;\s?/.test(line) || /^\s*>\s?/.test(raw)) {
      out.push(`<blockquote>${inline(line.replace(/^\s*&gt;\s?|^\s*>\s?/, ""))}</blockquote>`);
      continue;
    }
    if (/^\s*(-{3,}|\*{3,})\s*$/.test(line)) {
      out.push("<hr>");
      continue;
    }
    if (!line.trim()) continue;

    out.push(`<p>${inline(line)}</p>`);
  }
  closeList();
  closeTable();
  return out.join("\n");
}

/* ------------------------------------------------------------------ login */
function showLogin() {
  $("#login-overlay").classList.remove("hidden");
}
function hideLogin() {
  $("#login-overlay").classList.add("hidden");
}

$("#login-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  try {
    await api("/api/login", { method: "POST", body: { password: $("#login-password").value } });
    $("#login-password").value = "";
    hideLogin();
    boot();
  } catch (err) {
    toast(err.message, "err");
  }
});

$("#btn-logout").addEventListener("click", async () => {
  await api("/api/logout", { method: "POST" });
  location.reload();
});

$("#btn-api-docs").addEventListener("click", () => window.open("/api/docs", "_blank"));

/* ------------------------------------------------------------------- tabs */
$$(".tab").forEach((tab) =>
  tab.addEventListener("click", () => {
    $$(".tab").forEach((t) => t.classList.remove("active"));
    $$(".tab-panel").forEach((p) => p.classList.remove("active"));
    tab.classList.add("active");
    $("#tab-" + tab.dataset.tab).classList.add("active");
    if (tab.dataset.tab === "runs") loadRuns();
    if (tab.dataset.tab === "reports") loadReports();
    if (tab.dataset.tab === "tools") loadTools();
    if (tab.dataset.tab === "audit") loadAudit();
  })
);

/* ----------------------------------------------------------------- status */
async function loadStatus() {
  state.status = await api("/api/status");
  const s = state.status;

  $("#brand-sub").textContent = `${s.app} v${s.version}`;
  const chipAI = $("#chip-ai");
  chipAI.textContent = s.ai.configured ? `AI: ${s.ai.model.split("/").pop()}` : "AI: off";
  chipAI.className = "chip " + (s.ai.configured ? "ok" : "bad");

  const scope = s.scope || {};
  const chipMode = $("#chip-mode");
  if (scope.allowed_targets && scope.allowed_targets.length) {
    chipMode.textContent = `Mode: scope (${scope.allowed_targets.slice(0, 2).join(", ")}${scope.allowed_targets.length > 2 ? "…" : ""})`;
    chipMode.className = "chip ok";
  } else if (scope.approval_mode === "manual") {
    chipMode.textContent = "Mode: approval";
    chipMode.className = "chip warn";
  } else {
    chipMode.textContent = "Mode: auto";
    chipMode.className = "chip";
  }

  if (s.tools) {
    const chipTools = $("#chip-tools");
    chipTools.textContent = `Tools: ${s.tools.installed}/${s.tools.total}`;
    chipTools.className = "chip " + (s.tools.missing === 0 ? "ok" : "warn");
    $("#btn-install-missing").classList.toggle("hidden", !(scope.install_allowed && s.tools.missing > 0));
  }

  $("#chip-runs").textContent = `Scans: ${s.runs_active}`;
  const chipAp = $("#chip-approvals");
  chipAp.textContent = `Approvals: ${s.approvals_pending}`;
  chipAp.classList.toggle("hidden", !s.approvals_pending);
  $("#chip-os").textContent = `OS: ${(s.environment && s.environment.distribution ? s.environment.distribution : "unknown").split(" ")[0]}`;
  $("#btn-logout").classList.toggle("hidden", !s.auth_required);
  $("#btn-api-docs").classList.toggle("hidden", !s.authenticated);

  const banners = [];
  if (!s.auth_required) {
    banners.push(
      `<div class="banner warn">⚠️ <strong>APP_PASSWORD set nahi hai</strong> — koi bhi is dashboard ko access kar sakta hai. Public deploy par password zaroor lagao.</div>`
    );
  }
  if (!s.ai.configured) {
    banners.push(
      `<div class="banner warn">🧠 <strong>OPENROUTER_API_KEY set nahi hai</strong> — AI chat/report analysis off hai. Env var add karke restart karo. (Scans/tools kaam kar rahe hain.)</div>`
    );
  } else if (!scope.allowed_targets || !scope.allowed_targets.length) {
    banners.push(
      `<div class="banner warn">🎯 <strong>Scope allowlist khaali hai</strong> — har scan ke liye tumhe manually approve karna padega. VPS par <code>ALLOWED_TARGETS</code> set karoge to auto mode mil jayega.</div>`
    );
  } else {
    banners.push(`<div class="banner ok">✅ Scope active: <code>${esc(scope.allowed_targets.join(", "))}</code> — in targets par scans auto-approve honge.</div>`);
  }
  $("#banners").innerHTML = banners.join("");

  const modelInput = $("#model-input");
  if (modelInput && !modelInput.value) modelInput.placeholder = s.ai.model || "default model";

  return s;
}

/* ------------------------------------------------------------------- chat */
function addMessage(role, html, raw) {
  const wrap = document.createElement("div");
  wrap.className = "msg " + role;
  const body = document.createElement("div");
  body.className = "msg-body";
  body.innerHTML = raw ? html : mdToHtml(html);
  wrap.appendChild(body);
  $("#chat-log").appendChild(wrap);
  $("#chat-log").scrollTop = $("#chat-log").scrollHeight;
  return body;
}

function addTyping(label = "Soch raha hoon") {
  const wrap = document.createElement("div");
  wrap.className = "msg assistant";
  wrap.innerHTML = `<div class="msg-body"><span class="typing">${esc(label)} <i></i><i></i><i></i></span></div>`;
  $("#chat-log").appendChild(wrap);
  $("#chat-log").scrollTop = $("#chat-log").scrollHeight;
  return wrap;
}

function renderSteps(container, steps) {
  if (!steps || !steps.length) return;
  const box = document.createElement("div");
  box.className = "steps";
  for (const step of steps) {
    const chip = document.createElement("span");
    const kind = step.type || "tool";
    chip.className = "step-chip " + (step.status || kind);
    const label =
      kind === "scan"
        ? `scan ${step.profile} · ${step.run_id}`
        : kind === "approval"
        ? `approval ${step.approval_id}`
        : kind === "command"
        ? `${step.tool} · ${step.status}`
        : kind === "report"
        ? `report ${step.file}`
        : `${step.tool || kind}`;
    chip.textContent = label;
    box.appendChild(chip);
  }
  container.appendChild(box);
  $("#chat-log").scrollTop = $("#chat-log").scrollHeight;
}

function approvalCard(container, pending, { onDone } = {}) {
  const card = document.createElement("div");
  card.className = "approval-card";
  card.innerHTML = `
    <h4>⚠️ Approval chahiye</h4>
    <div>${esc(pending.summary || "Action")}</div>
    ${pending.reason ? `<p class="hint">${esc(pending.reason)}</p>` : ""}
    ${pending.command ? `<pre class="term">${esc(pending.command)}</pre>` : ""}
    <div class="approval-actions">
      <button class="btn ok" data-approve>Approve &amp; run</button>
      <button class="btn danger" data-deny>Deny</button>
    </div>`;
  container.appendChild(card);

  const finish = (approved) =>
    api(`/api/approvals/${encodeURIComponent(pending.id)}`, { method: "POST", body: { approved } })
      .then((res) => {
        card.classList.add(approved ? "resolved" : "denied");
        card.querySelector(".approval-actions").innerHTML = `<span class="badge ${approved ? "done" : "error"}">${approved ? "approved" : "denied"}</span>`;
        loadStatus().catch(() => {});
        if (onDone) onDone(approved);
      })
      .catch((err) => toast(err.message, "err"));

  card.querySelector("[data-approve]").addEventListener("click", () => finish(true));
  card.querySelector("[data-deny]").addEventListener("click", () => finish(false));
  return card;
}

async function sendChat(text) {
  if (!text.trim()) return;
  addMessage("user", text);
  state.messages.push({ role: "user", content: text });
  $("#chat-input").value = "";
  const typing = addTyping("Analysis kar raha hoon");
  $("#btn-send").disabled = true;

  try {
    const data = await api("/api/chat", {
      method: "POST",
      body: {
        messages: state.messages,
        conversation_id: state.conversationId,
        model: ($("#model-input") || {}).value || undefined,
      },
    });
    typing.remove();
    state.messages.push({ role: "assistant", content: data.reply });
    const body = addMessage("assistant", data.reply || "(koi jawab nahi)");
    renderSteps(body, data.steps);
    if (data.needs_approval) {
      approvalCard(body, data.needs_approval, { onDone: (ok) => ok && startFollowupPoll() });
      startFollowupPoll();
    }
    loadStatus().catch(() => {});
    if (data.runs && data.runs.length) loadRuns().catch(() => {});
  } catch (err) {
    typing.remove();
    addMessage("assistant", `⚠️ ${err.message}`);
  } finally {
    $("#btn-send").disabled = false;
  }
}

function startFollowupPoll() {
  if (state.followupTimer) clearInterval(state.followupTimer);
  state.followupWaits = 0;
  const typing = addTyping("Approved — scan chal raha hai");
  state.followupTimer = setInterval(async () => {
    state.followupWaits += 1;
    try {
      const data = await api(`/api/chat/followup/${encodeURIComponent(state.conversationId)}`);
      if (data.status === "ready") {
        clearInterval(state.followupTimer);
        state.followupTimer = null;
        typing.remove();
        state.messages.push({ role: "assistant", content: data.reply });
        const body = addMessage("assistant", data.reply || "(result nahi mila)");
        renderSteps(body, data.steps);
        await api(`/api/chat/followup/${encodeURIComponent(state.conversationId)}`, { method: "DELETE" }).catch(() => {});
        loadRuns().catch(() => {});
        loadStatus().catch(() => {});
      } else if (data.status === "error") {
        clearInterval(state.followupTimer);
        state.followupTimer = null;
        typing.remove();
        addMessage("assistant", `⚠️ ${esc(data.reply || "error")}`);
      } else if (state.followupWaits > 200) {
        clearInterval(state.followupTimer);
        state.followupTimer = null;
        typing.remove();
        addMessage("assistant", "⏳ Result abhi tak nahi aaya — Runs tab me check kar lo.");
      }
    } catch (err) {
      clearInterval(state.followupTimer);
      state.followupTimer = null;
      typing.remove();
      addMessage("assistant", `⚠️ ${err.message}`);
    }
  }, 2500);
}

$("#chat-form").addEventListener("submit", (event) => {
  event.preventDefault();
  sendChat($("#chat-input").value);
});

$("#chat-input").addEventListener("keydown", (event) => {
  if (event.key === "Enter" && !event.shiftKey) {
    event.preventDefault();
    sendChat($("#chat-input").value);
  }
});

$$("#quick-chips .chip-btn").forEach((btn) =>
  btn.addEventListener("click", () => {
    $("#chat-input").value = btn.textContent.trim();
    sendChat(btn.textContent.trim());
  })
);

$("#btn-clear-chat").addEventListener("click", () => {
  state.messages = [];
  state.conversationId = "conv-" + Math.random().toString(36).slice(2, 10);
  $("#chat-log").innerHTML = "";
  addMessage("assistant", "Chat clear ho gaya. Naya target batao!");
});

/* ------------------------------------------------------------------- scan */
function renderProfileGrid() {
  const grid = $("#profile-grid");
  grid.innerHTML = "";
  for (const profile of state.profiles) {
    const card = document.createElement("button");
    card.type = "button";
    card.className = "profile-card" + (profile.name === state.profile ? " selected" : "");
    card.innerHTML = `<strong>${esc(profile.title)}</strong><span>${esc(profile.description)}</span>
      ${profile.needs_wordlist ? '<span class="flag">⚠️ wordlist missing</span>' : ""}`;
    card.addEventListener("click", () => {
      state.profile = profile.name;
      $$(".profile-card").forEach((c) => c.classList.remove("selected"));
      card.classList.add("selected");
    });
    grid.appendChild(card);
  }
}

$("#scan-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const target = $("#scan-target").value.trim();
  if (!target) return;
  $("#scan-approval").innerHTML = "";
  $("#scan-output").innerHTML = '<p class="muted">Scan request bheji ja rahi hai…</p>';
  try {
    const data = await api("/api/scan", { method: "POST", body: { target, profile: state.profile } });
    if (data.status === "approval_required") {
      $("#scan-output").innerHTML = "";
      approvalCard($("#scan-approval"), {
        id: data.approval.id,
        summary: data.approval.summary,
        command: data.approval.command,
        reason: data.reason,
      }, { onDone: (ok) => ok && watchRun(data.run.id, $("#scan-output")) });
      toast("Approval ka wait hai — card approve karo", "");
    } else {
      toast(`Scan start: ${data.run.id}`, "ok");
      watchRun(data.run.id, $("#scan-output"));
    }
    loadRuns().catch(() => {});
    loadStatus().catch(() => {});
  } catch (err) {
    $("#scan-output").innerHTML = "";
    toast(err.message, "err");
  }
});

async function watchRun(runId, container, { interval = 3000, maxTicks = 240 } = {}) {
  let ticks = 0;
  const render = (detail) => {
    container.innerHTML = runDetailHtml(detail, false);
    const cancelBtn = container.querySelector("[data-cancel]");
    if (cancelBtn) cancelBtn.addEventListener("click", () => cancelRun(runId));
  };
  const tick = async () => {
    ticks += 1;
    try {
      const data = await api(`/api/runs/${runId}`);
      render(data.run);
      if (["done", "error", "cancelled"].includes(data.run.status) || ticks > maxTicks) {
        clearInterval(timer);
        loadStatus().catch(() => {});
      }
    } catch (err) {
      clearInterval(timer);
      container.innerHTML = `<p class="muted">Run load nahi hua: ${esc(err.message)}</p>`;
    }
  };
  await tick();
  const timer = setInterval(tick, interval);
  return () => clearInterval(timer);
}

/* ------------------------------------------------------------------- runs */
async function loadRuns() {
  const data = await api("/api/runs");
  state.runs = data.runs || [];
  const list = $("#runs-list");
  list.innerHTML = state.runs.length ? "" : '<p class="muted">Abhi koi run nahi hua.</p>';
  for (const run of state.runs) {
    const item = document.createElement("div");
    item.className = "list-item" + (run.id === state.activeRunId ? " active" : "");
    item.innerHTML = `
      <div class="li-top"><span class="li-target">${esc(run.target)}</span><span class="badge ${run.status}">${run.status}</span></div>
      <div class="li-meta"><span>${esc(run.profile)}</span><span>${run.steps_done}/${run.steps_total} steps</span><span>${esc(run.id)}</span><span>${esc(run.source)}</span></div>`;
    item.addEventListener("click", () => openRun(run.id));
    list.appendChild(item);
  }
  if (state.activeRunId) {
    const still = state.runs.some((r) => r.id === state.activeRunId);
    if (still && $("#run-detail").dataset.live === "1") openRun(state.activeRunId, true);
  }
}

function runStatusBadge(status) {
  return `<span class="badge ${status}">${status}</span>`;
}

function runDetailHtml(run, interactive = true) {
  const steps = (run.steps || [])
    .map(
      (step) => `
      <div class="step-block">
        <div class="step-head">
          <strong>${step.index + 1}. ${esc(step.label)}</strong>
          ${runStatusBadge(step.status)}
          <span class="muted small">${step.duration ? step.duration + "s" : ""} ${step.exit_code !== null && step.exit_code !== undefined ? "· exit " + step.exit_code : ""}</span>
          <span class="cmd">${esc(step.command)}</span>
        </div>
        ${step.output ? `<pre class="term">${esc(step.output)}</pre>` : ""}
        ${step.error ? `<p class="hint" style="padding:0 13px 10px">⚠️ ${esc(step.error)}</p>` : ""}
        ${step.truncated ? `<p class="hint" style="padding:0 13px 10px">output truncated</p>` : ""}
      </div>`
    )
    .join("");

  const actions = interactive
    ? `<div class="head-actions" style="margin-bottom:10px">
         <button class="btn ghost" data-cancel>Cancel</button>
         <button class="btn primary" data-report>AI report banao</button>
         <button class="btn ghost" data-refresh>Refresh</button>
         <button class="btn danger" data-delete>Delete</button>
       </div>`
    : `<div class="head-actions" style="margin-bottom:10px"><button class="btn ghost" data-cancel>Cancel</button></div>`;

  return `
    <h3>${esc(run.target)} · ${esc(run.profile)}</h3>
    <div class="li-meta" style="margin-bottom:12px">
      ${runStatusBadge(run.status)} <span>run <code>${esc(run.id)}</code></span>
      <span>started ${new Date(run.created * 1000).toLocaleString()}</span>
      ${run.finished ? `<span>finished ${new Date(run.finished * 1000).toLocaleString()}</span>` : ""}
      <span>actor ${esc(run.actor || "-")}</span>
    </div>
    ${run.note ? `<p class="hint">${esc(run.note)}</p>` : ""}
    ${actions}
    ${steps || '<p class="muted">Koi step nahi.</p>'}`;
}

async function openRun(runId, silent = false) {
  try {
    const data = await api(`/api/runs/${runId}`);
    state.activeRunId = runId;
    const box = $("#run-detail");
    box.dataset.live = ["queued", "running"].includes(data.run.status) ? "1" : "0";
    box.innerHTML = runDetailHtml(data.run, true);
    box.querySelector("[data-cancel]").addEventListener("click", () => cancelRun(runId));
    box.querySelector("[data-refresh]").addEventListener("click", () => openRun(runId));
    box.querySelector("[data-delete]").addEventListener("click", async () => {
      if (!confirm("Yeh run delete karna hai?")) return;
      await api(`/api/runs/${runId}`, { method: "DELETE" });
      state.activeRunId = null;
      $("#run-detail").innerHTML = '<p class="muted">Run delete ho gaya.</p>';
      loadRuns();
    });
    box.querySelector("[data-report]").addEventListener("click", async (event) => {
      const btn = event.currentTarget;
      btn.disabled = true;
      btn.textContent = "AI analysis ho rahi hai…";
      try {
        const res = await api(`/api/runs/${runId}/report`, { method: "POST", body: { ai: true } });
        toast(`Report save: ${res.file}`, "ok");
        if (res.ai_summary) {
          const ai = document.createElement("div");
          ai.innerHTML = `<h4>AI Analysis</h4>${mdToHtml(res.ai_summary)}`;
          box.insertBefore(ai, box.querySelector(".step-block") || null);
        }
        loadReports().catch(() => {});
      } catch (err) {
        toast(err.message, "err");
      } finally {
        btn.disabled = false;
        btn.textContent = "AI report banao";
      }
    });
    $$("#runs-list .list-item").forEach((it) => it.classList.toggle("active", it.textContent.includes(runId)));
    if (!silent) $$(".tab").forEach((t) => t.dataset.tab === "runs" && t.click());
  } catch (err) {
    toast(err.message, "err");
  }
}

async function cancelRun(runId) {
  try {
    await api(`/api/runs/${runId}/cancel`, { method: "POST" });
    toast("Cancel request bheji gayi", "");
    setTimeout(() => openRun(runId), 1200);
  } catch (err) {
    toast(err.message, "err");
  }
}

$("#btn-refresh-runs").addEventListener("click", () => loadRuns());

/* ---------------------------------------------------------------- reports */
async function loadReports() {
  const data = await api("/api/reports");
  const list = $("#reports-list");
  list.innerHTML = (data.reports || []).length ? "" : '<p class="muted">Abhi koi report nahi bani.</p>';
  for (const item of data.reports) {
    const el = document.createElement("div");
    el.className = "list-item";
    el.innerHTML = `<div class="li-top"><span class="li-target">${esc(item.name)}</span><span class="badge">${Math.round(item.size / 1024)} KB</span></div>
      <div class="li-meta"><span>${new Date(item.modified * 1000).toLocaleString()}</span></div>`;
    el.addEventListener("click", () => openReport(item.name, el));
    list.appendChild(el);
  }
}

async function openReport(name, el) {
  try {
    const data = await api(`/api/reports/${encodeURIComponent(name)}`);
    $$("#reports-list .list-item").forEach((i) => i.classList.remove("active"));
    if (el) el.classList.add("active");
    const box = $("#report-detail");
    box.innerHTML = `<div class="head-actions" style="margin-bottom:12px">
        <button class="btn primary" data-download>Download .md</button>
        <button class="btn danger" data-delete>Delete</button>
      </div><div id="report-body">${mdToHtml(data.content)}</div>`;
    box.querySelector("[data-download]").addEventListener("click", () => {
      const blob = new Blob([data.content], { type: "text/markdown" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = name;
      a.click();
      URL.revokeObjectURL(url);
    });
    box.querySelector("[data-delete]").addEventListener("click", async () => {
      if (!confirm("Report delete karni hai?")) return;
      await api(`/api/reports/${encodeURIComponent(name)}`, { method: "DELETE" });
      box.innerHTML = '<p class="muted">Report delete ho gayi.</p>';
      loadReports();
    });
  } catch (err) {
    toast(err.message, "err");
  }
}

$("#btn-refresh-reports").addEventListener("click", () => loadReports());

/* ------------------------------------------------------------------ tools */
async function loadTools(refresh = false) {
  const data = await api(`/api/tools${refresh ? "?refresh=true" : ""}`);
  state.tools = data.tools || [];
  const tbody = $("#tools-table tbody");
  tbody.innerHTML = "";
  for (const tool of state.tools) {
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td><strong>${esc(tool.name)}</strong><br><span class="hint">${esc(tool.binary)}</span></td>
      <td>${esc(tool.category)}${tool.needs_approval ? '<br><span class="hint">approval required</span>' : ""}</td>
      <td>${tool.installed ? '<span class="badge done">installed</span>' : '<span class="badge error">missing</span>'}</td>
      <td class="hint">${esc((tool.version || "-").slice(0, 60))}</td>
      <td>${tool.installed ? `<span class="hint">${esc(tool.description)}</span>` : `<code>apt-get install -y ${esc(tool.package)}</code>`}</td>`;
    tbody.appendChild(tr);
  }
  const installed = state.tools.filter((t) => t.installed).length;
  $("#tools-summary").textContent = `${installed}/${state.tools.length} tools ready. Missing tools ke install commands table me diye hain.`;
}

$("#btn-refresh-tools").addEventListener("click", async () => {
  toast("Versions check ho rahe hain…");
  await loadTools(true);
  toast("Tool status refresh ho gaya", "ok");
});

$("#btn-install-missing").addEventListener("click", async (event) => {
  const btn = event.currentTarget;
  if (!confirm("Missing tools install karne hain? (apt-get chalega — kuch minute lagega)")) return;
  btn.disabled = true;
  btn.textContent = "Install ho raha hai…";
  try {
    const res = await api("/api/install", { method: "POST", body: {} });
    toast(res.ok ? "Install complete" : "Install me issue aaya — Tools output dekho", res.ok ? "ok" : "err");
    await loadTools(true);
  } catch (err) {
    toast(err.message, "err");
  } finally {
    btn.disabled = false;
    btn.textContent = "Install missing";
  }
});

/* ------------------------------------------------------------------ audit */
async function loadAudit() {
  const data = await api("/api/audit?limit=200");
  const tbody = $("#audit-table tbody");
  tbody.innerHTML = "";
  for (const event of data.events || []) {
    const { ts, event: name, ...rest } = event;
    const tr = document.createElement("tr");
    tr.innerHTML = `<td class="hint">${new Date(ts * 1000).toLocaleString()}</td>
      <td><span class="badge">${esc(name)}</span></td>
      <td class="hint">${esc(JSON.stringify(rest).slice(0, 400))}</td>`;
    tbody.appendChild(tr);
  }
}

$("#btn-refresh-audit").addEventListener("click", () => loadAudit());

/* ------------------------------------------------------------------- boot */
async function boot() {
  try {
    const s = await loadStatus();
    if (s.auth_required && !s.authenticated) {
      showLogin();
      return;
    }
    hideLogin();
    const meta = await api("/api/meta");
    state.profiles = meta.profiles || [];
    renderProfileGrid();
    await Promise.all([loadTools(), loadRuns(), loadReports()]);
    loadStatus().catch(() => {});
    setInterval(() => loadStatus().catch(() => {}), 8000);
  } catch (err) {
    toast(err.message, "err");
  }
}

boot();
