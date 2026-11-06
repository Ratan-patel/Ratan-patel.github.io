"use strict";
// Connect screen: sirf server URL leta hai. Password/API key agle screen par (server ke console me).
const input = document.querySelector("#server");
const statusEl = document.querySelector("#status");
const native = window.AndroidAgent || null;

const saved = localStorage.getItem("sa_server") || (native ? native.serverUrl() : "");
if (saved) input.value = saved;

function open(rawInput) {
  let raw = rawInput.trim();
  if (!raw) { statusEl.textContent = "Server URL daalo."; return; }
  if (!/^https?:\/\//i.test(raw)) {
    raw = (/^(localhost|127\.|10\.|192\.168\.|172\.(1[6-9]|2\d|3[01])\.)/i.test(raw) ? "http://" : "https://") + raw;
  }
  let url;
  try {
    url = new URL(raw);
    if (url.username || url.password || url.search || url.hash) throw new Error("bad url");
  } catch {
    statusEl.textContent = "Invalid URL. Credentials/query/fragment mat daalo.";
    return;
  }
  try { localStorage.setItem("sa_server", url.origin); } catch (_) { /* private mode */ }
  statusEl.textContent = "Connecting…";
  // Android app: native bridge se origin save hota hai aur console app ke andar khulta hai.
  if (native && typeof native.openServer === "function") native.openServer(url.origin);
  else location.href = url.origin + "/mobile";
}

document.querySelector("#connect").onclick = () => open(input.value);
input.addEventListener("keydown", (e) => { if (e.key === "Enter") open(input.value); });