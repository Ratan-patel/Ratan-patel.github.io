"use strict";
// RatanSec Agent v3 — standalone UI. Sab kuch native bridge ke through device par.
const N = window.Native;
const $ = (s) => document.querySelector(s);
const $$ = (s) => Array.from(document.querySelectorAll(s));
const state = { history: [], busy: false, settings: null, findings: [] };

const BASES = {
  openrouter: ["https://openrouter.ai/api/v1", "openai/gpt-4o-mini"],
  openai: ["https://api.openai.com/v1", "gpt-4o-mini"],
  groq: ["https://api.groq.com/openai/v1", "llama-3.3-70b-versatile"],
  deepseek: ["https://api.deepseek.com/v1", "deepseek-chat"],
  ollama: ["http://127.0.0.1:11434/v1", "qwen2.5:7b"],
  custom: ["", ""]
};

function parse(json, fallback) {
  try { return JSON.parse(json); } catch (_) { return fallback; }
}
function esc(text) {
  return String(text == null ? "" : text).replace(/[&<>"']/g, (c) =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}
function toast(message, kind) {
  const el = $("#toast");
  el.textContent = message;
  el.className = "toast " + (kind || "");
  clearTimeout(el._t);
  el._t = setTimeout(() => el.classList.add("hidden"), 3200);
}

// --- navigation ----------------------------------------------------------
$$(".tab").forEach((tab) => {
  tab.onclick = () => {
    $$(".tab").forEach((t) => t.classList.toggle("active", t === tab));
    $$(".view").forEach((v) => v.classList.toggle("active", v.id === "view-" + tab.dataset.view));
    if (tab.dataset.view === "scope") loadTargets();
  };
});
function go(view) { const tab = $('.tab[data-view="' + view + '"]'); if (tab) tab.click(); }

// --- settings ------------------------------------------------------------
function loadSettings() {
  const s = parse(N.settings(), {});
  state.settings = s;
  $("#s-provider").value = s.provider || "openrouter";
  $("#s-base").value = s.base_url || "";
  $("#s-model").value = s.model || "";
  $("#s-steps").value = String(s.max_steps || 6);
  $("#s-private").checked = !!s.allow_private;
  $("#version-line").textContent = "RatanSec Agent v" + (s.version || "3.0.0") + " · standalone (no server)";
  paintKey(!!s.has_key);
}
function paintKey(hasKey) {
  const pill = $("#key-pill");
  pill.textContent = hasKey ? "key saved 🔒" : "key not set";
  pill.className = "pill " + (hasKey ? "ok" : "bad");
  $("#setup-banner").classList.toggle("hidden", hasKey);
  $("#s-key").value = "";
  $("#s-key").placeholder = hasKey ? "•••••••• (saved — badalne ke liye nayi daalo)" : "sk-…";
}
$("#s-provider").onchange = () => {
  const preset = BASES[$("#s-provider").value];
  if (preset && preset[0]) { $("#s-base").value = preset[0]; $("#s-model").value = preset[1]; }
};
function saveSettings(withKey) {
  const payload = {
    provider: $("#s-provider").value,
    base_url: $("#s-base").value.trim(),
    model: $("#s-model").value.trim(),
    max_steps: parseInt($("#s-steps").value, 10) || 6,
    allow_private: $("#s-private").checked
  };
  const res = parse(N.saveSettings(JSON.stringify(payload)), {});
  if (!res.ok) { $("#settings-status").textContent = res.message || "Save fail"; toast(res.message || "Save fail", "err"); return false; }
  const key = $("#s-key").value.trim();
  if (withKey && key) {
    const saved = parse(N.saveKey(key), {});
    if (!saved.ok) { toast(saved.message || "Key save fail", "err"); return false; }
    paintKey(!!saved.has_key);
  }
  state.settings = res.settings;
  $("#settings-status").textContent = "Saved ✓";
  return true;
}
$("#save-settings").onclick = () => { if (saveSettings(true)) toast("Settings saved", "ok"); };
$("#save-agent").onclick = () => { if (saveSettings(false)) toast("Agent settings saved", "ok"); };
$("#clear-key").onclick = () => {
  N.clearKey(); paintKey(false); toast("Key hata di gayi", "ok");
};
$("#test-conn").onclick = () => {
  if (!saveSettings(true)) return;
  $("#settings-status").textContent = "Test ho raha hai…";
  N.testConnection();
};

// --- scope ---------------------------------------------------------------
function loadTargets() {
  const list = parse(N.targets(), []);
  const box = $("#target-list");
  if (!list.length) {
    box.innerHTML = '<div class="empty">Abhi koi target nahi. Upar se add karo.</div>';
    return;
  }
  box.innerHTML = list.map((t) => {
    const days = Math.max(0, Math.ceil((t.expires - Date.now()) / 86400000));
    return '<div class="target"><div class="h"><b>' + esc(t.host) + '</b></div>' +
      '<div class="note">' + esc(t.note) + '</div>' +
      '<div class="exp">' + days + ' din baaki</div>' +
      '<div class="acts"><button data-run="' + esc(t.host) + '">Run checks</button>' +
      '<button class="rm" data-rm="' + esc(t.host) + '">Hatao</button></div></div>';
  }).join("");
  box.querySelectorAll("[data-rm]").forEach((b) => {
    b.onclick = () => { N.removeTarget(b.dataset.rm); loadTargets(); toast("Scope se hata diya", "ok"); };
  });
  box.querySelectorAll("[data-run]").forEach((b) => {
    b.onclick = () => {
      go("chat");
      startChecks(b.dataset.run);
    };
  });
}
$("#add-target").onclick = () => {
  const host = $("#t-host").value.trim();
  const note = $("#t-note").value.trim();
  if (!$("#t-confirm").checked) { $("#scope-status").textContent = "Pehle permission wala checkbox tick karo."; return; }
  const res = parse(N.addTarget(host, note, parseInt($("#t-days").value, 10) || 30), {});
  if (!res.ok) { $("#scope-status").textContent = res.message || "Add fail"; return; }
  $("#scope-status").textContent = "Added ✓";
  $("#t-host").value = ""; $("#t-note").value = ""; $("#t-confirm").checked = false;
  loadTargets();
  toast(res.host + " scope me add hua", "ok");
};

// --- chat ----------------------------------------------------------------
function scrollDown() { const m = $("#messages"); m.scrollTop = m.scrollHeight; }
function clearHello() { const h = $(".hello"); if (h) h.remove(); }
function addMsg(role, text) {
  clearHello();
  const wrap = document.createElement("div");
  wrap.className = "msg " + role;
  wrap.innerHTML = '<div class="who">' + (role === "user" ? "You" : "Agent") + '</div><div class="bubble">' + esc(text) + "</div>";
  $("#messages").appendChild(wrap);
  scrollDown();
  return wrap.querySelector(".bubble");
}
function addTool(name, result) {
  clearHello();
  const blocked = result && (result.status === "blocked" || result.status === "error");
  const el = document.createElement("div");
  el.className = "tool" + (blocked ? " blocked" : "");
  let inner = "<b>🔧 " + esc(name) + "</b>";
  if (blocked) {
    inner += "<pre>" + esc(result.error || "blocked") + "</pre>";
  } else if (result) {
    const findings = result.findings || [];
    findings.forEach((f) => {
      state.findings.push(f);
      inner += '<div class="finding ' + esc(f.severity) + '"><b>' + esc(f.title) +
        '<span class="sev">' + esc(f.severity) + "</span></b><p>" + esc(f.evidence) +
        "</p><p>➜ " + esc(f.remediation) + "</p></div>";
    });
    const data = result.data ? JSON.stringify(result.data, null, 1) : "";
    if (data) inner += "<pre>" + esc(data.slice(0, 1200)) + "</pre>";
    if (!findings.length && !data) inner += "<pre>ok</pre>";
  }
  el.innerHTML = inner;
  $("#messages").appendChild(el);
  scrollDown();
}
let typingEl = null;
function typing(on, label) {
  if (typingEl) { typingEl.remove(); typingEl = null; }
  if (!on) return;
  clearHello();
  typingEl = document.createElement("div");
  typingEl.className = "typing";
  typingEl.textContent = label || "Agent soch raha hai…";
  $("#messages").appendChild(typingEl);
  scrollDown();
}
function setBusy(busy) {
  state.busy = busy;
  $("#send").classList.toggle("hidden", busy);
  $("#stop").classList.toggle("hidden", !busy);
  $("#input").disabled = busy;
}
function send(text) {
  const message = (text || $("#input").value).trim();
  if (!message || state.busy) return;
  if (state.settings && !state.settings.has_key &&
      !/^http:\/\/(127\.|localhost)/.test(state.settings.base_url || "")) {
    toast("Pehle Settings me API key daalo", "err"); go("settings"); return;
  }
  $("#input").value = "";
  $("#input").style.height = "auto";
  addMsg("user", message);
  state.history.push({ role: "user", content: message });
  if (state.history.length > 20) state.history = state.history.slice(-20);
  setBusy(true);
  typing(true);
  N.chat(JSON.stringify(state.history));
}
function startChecks(host) {
  if (state.busy) return;
  addMsg("user", "Run posture checks on " + host);
  setBusy(true);
  typing(true, host + " par checks chal rahe hain…");
  N.runChecks(host);
}
$("#send").onclick = () => send();
$("#stop").onclick = () => { N.stop(); typing(false); setBusy(false); toast("Rok diya"); };
$("#input").addEventListener("keydown", (e) => {
  if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); send(); }
});
$("#input").addEventListener("input", (e) => {
  e.target.style.height = "auto";
  e.target.style.height = Math.min(e.target.scrollHeight, 120) + "px";
});
$$(".chip").forEach((c) => { c.onclick = () => send(c.dataset.ask); });

// --- native events -------------------------------------------------------
window.onNativeEvent = (json) => {
  const event = parse(json, {});
  switch (event.type) {
    case "step":
      typing(true, "Step " + event.step + "/" + event.max + " — model soch raha hai…");
      break;
    case "tool":
      typing(true, "🔧 " + event.name + " chal raha hai…");
      break;
    case "tool_result":
      typing(false);
      addTool(event.name, event.result);
      break;
    case "answer":
      typing(false);
      addMsg("agent", event.text);
      state.history.push({ role: "assistant", content: event.text });
      break;
    case "checks_done": {
      typing(false);
      const total = state.findings.length;
      addMsg("agent", "Checks poore hue" + (total ? " — " + total + " observations mile (upar dekho)." : " — koi observation nahi mila."));
      if (total) {
        const el = document.createElement("div");
        el.className = "row";
        el.innerHTML = '<button class="btn" id="share-report">Report share karo</button>';
        $("#messages").appendChild(el);
        el.querySelector("#share-report").onclick = shareReport;
      }
      break;
    }
    case "cancelled":
      typing(false); addMsg("agent", "Rok diya gaya."); break;
    case "error":
      typing(false); toast(event.message || "Error", "err"); addMsg("agent", "⚠️ " + (event.message || "Error")); break;
    case "test_result": {
      const r = event.result || {};
      $("#settings-status").textContent = (r.ok ? "✓ " : "✗ ") + (r.message || "");
      toast(r.message || "", r.ok ? "ok" : "err");
      break;
    }
    case "done":
      typing(false); setBusy(false); break;
    default: break;
  }
};

function shareReport() {
  const lines = ["RatanSec Agent — assessment notes", new Date().toISOString(), ""];
  state.findings.forEach((f, i) => {
    lines.push((i + 1) + ". [" + f.severity + "] " + f.title);
    lines.push("   Evidence: " + f.evidence);
    lines.push("   Fix: " + f.remediation, "");
  });
  lines.push("Authorized testing only. Observations, not verified vulnerabilities.");
  N.exportReport(lines.join("\n"));
}

loadSettings();
loadTargets();
