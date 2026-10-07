/* ============================================================================
   RATAN_PATEL.SEC — RATAN OS Advanced Edition build planner
   Client-side only. Produces a Debian live-build module manifest from the
   selections. Sizes are engineering estimates, not measurements.
   ============================================================================ */
(function () {
  "use strict";

  var GROUPS = [
    { id: "base", n: "1 · Base system" },
    { id: "ai", n: "2 · Offline AI runtime" },
    { id: "tools", n: "3 · Tool collections" },
    { id: "lab", n: "4 · Isolated lab profiles" },
    { id: "rel", n: "5 · Release engineering" }
  ];

  /* m(id, group, name, desc, MiB, packages, minRamMiB, recommendsDiskMiB, needs[], tag) */
  var MODULES = [];
  function m(id, g, n, d, size, pkgs, ram, disk, needs, tag) {
    MODULES.push({ id: id, g: g, n: n, d: d, size: size, pkgs: pkgs, ram: ram, disk: disk, needs: needs || [], tag: tag || "" });
  }

  /* ---- base ---- */
  m("base-minimal", "base", "Minimal live base", "Headless-friendly Debian Trixie live system with a lightweight window manager. Fastest to boot, smallest to download.", 320, 520, 512, 2048, [], "CORE");
  m("base-xfce", "base", "XFCE desktop base", "Full XFCE desktop, terminal, file manager and screenshot tooling — the desktop the shipped builds use.", 640, 980, 1024, 4096, [], "RECOMMENDED");
  m("base-persistence", "base", "Encrypted persistence", "Keep your notes, captures and lab state across reboots on an LUKS-encrypted persistence partition.", 45, 30, 0, 8192, ["base-xfce"], "OPTIONAL");

  /* ---- ai ---- */
  m("ai-llama", "ai", "llama.cpp CPU runtime", "CPU-only inference runtime compiled without network dependencies. Binds to loopback; makes no outbound calls.", 120, 18, 0, 0, [], "REQUIRED FOR AI");
  m("ai-qwen15", "ai", "Qwen2.5 1.5B (Q4)", "Lightweight quantised model. Runs on modest laptops; good for command reference and offline Q&A, weaker at multi-step reasoning.", 1050, 4, 3072, 0, ["ai-llama"], "LIGHT");
  m("ai-qwen3-4b", "ai", "Qwen3-4B Q4_K_M", "The model shipped in the v1.2.0 AI Edition. Solid balance of reasoning quality and CPU speed on a modern 4-core machine.", 2450, 4, 8192, 0, ["ai-llama"], "BALANCED");
  m("ai-qwen3-8b", "ai", "Qwen3-8B Q4_K_M", "Noticeably better reasoning, noticeably slower on CPU. Choose only on 16 GB machines where you will tolerate longer answers.", 4900, 4, 12288, 0, ["ai-llama"], "HEAVY");
  m("ai-ui", "ai", "Local browser console", "Chat interface served on 127.0.0.1 only, proxied locally. No account, no key, no external endpoint.", 35, 9, 0, 0, ["ai-llama"], "");
  m("ai-rag-docs", "ai", "Offline documentation corpus", "Local embeddings index over bundled security references so the assistant can cite material instead of inventing it.", 380, 14, 1024, 0, ["ai-llama"], "NICE TO HAVE");
  m("ai-toolbridge", "ai", "Local tool-call bridge", "Lets the assistant read output from the bundled scanners and summarise findings — never reaches outside the machine.", 25, 6, 0, 0, ["ai-llama"], "");
  m("ai-gpu", "ai", "GPU offload build", "Optional CUDA or Vulkan offload for machines with a discrete GPU. Adds driver weight and build complexity.", 210, 22, 0, 0, ["ai-llama"], "OPTIONAL");

  /* ---- tools ---- */
  m("tools-recon", "tools", "Recon & enumeration", "Passive and active discovery: DNS and subdomain enumeration, service fingerprinting, OSINT helpers.", 420, 96, 0, 0, [], "");
  m("tools-web", "tools", "Web & API testing", "Proxy, fuzzer, API client and request-crafting tooling for web and API assessment.", 610, 134, 0, 0, [], "CORE SHELF");
  m("tools-net", "tools", "Network assessment", "Packet capture and analysis, protocol tooling, and authorised wireless assessment utilities.", 380, 88, 0, 0, [], "");
  m("tools-exploit", "tools", "Exploitation framework", "Framework plus payload generation, for validating exploit detection on your own range.", 950, 210, 0, 0, [], "");
  m("tools-cred", "tools", "Credential & identity testing", "Password auditing, hash tooling and identity-path analysis for authorised internal assessments.", 240, 64, 0, 0, [], "");
  m("tools-c2", "tools", "C2 research sandbox", "Packaging for studying command-and-control architecture and, more usefully, its network telemetry. Read the C2 framing page before enabling.", 300, 42, 0, 0, [], "STUDY ONLY");
  m("tools-forensics", "tools", "Forensics & response", "Disk and memory acquisition, timeline and artefact analysis, triage collection.", 520, 142, 0, 0, [], "CORE SHELF");
  m("tools-reversing", "tools", "Reversing & triage", "Disassembler, debugger, binary inspection and lightweight malware triage tooling.", 780, 168, 0, 0, [], "");
  m("tools-ai-redteam", "tools", "AIRT LLM red-team scanner", "The zero-dependency AI Red-Teaming Scanner from this site: prompt injection, jailbreak and boundary probes with OWASP LLM Top-10 mapping.", 12, 0, 0, 0, [], "BUNDLED");
  m("tools-attack", "tools", "ATT&CK offline knowledge base", "Local ATT&CK technique data plus the coverage mapper, so you can plan and score engagements without an internet connection.", 55, 0, 0, 0, [], "BUNDLED");
  m("tools-wordlists", "tools", "Curated wordlists & rules", "Vetted wordlists and mutation rules. Large, and the single most over-selected module on this page.", 640, 12, 0, 0, [], "OPTIONAL");
  m("tools-report", "tools", "Evidence & report engine", "Timestamped operator logging, artefact capture and report scaffolding that emits per-technique findings.", 40, 16, 0, 0, [], "PRO SHELF");

  /* ---- lab ---- */
  m("lab-web", "lab", "Web & API range", "A deliberately vulnerable application and API target, fronted by a proxy, with server-side logs collected.", 1250, 0, 2048, 0, [], "PROFILE 01");
  m("lab-ad", "lab", "Active Directory range", "Domain controller plus two members on an internal switch, with Windows security event collection for detection review.", 3100, 0, 8192, 0, [], "PROFILE 02");
  m("lab-ai", "lab", "AI / LLM red-team range", "Local model endpoint wired to the AIRT scanner — the whole AI range runs with Wi-Fi off.", 900, 0, 4096, 0, ["tools-ai-redteam"], "PROFILE 03");
  m("lab-c2", "lab", "C2 sandbox range", "Internal-switch-only topology with egress denied, plus metadata capture for beacon analysis exercises.", 700, 0, 4096, 0, ["tools-c2"], "PROFILE 04");
  m("lab-forensics", "lab", "Forensics range", "Pre-captured disk and memory images with a known ground-truth timeline and an injected-activity log corpus.", 2900, 0, 3072, 0, ["tools-forensics"], "PROFILE 05");
  m("lab-telemetry", "lab", "Local telemetry stack", "Suricata plus a lightweight index, with egress denied. The piece that turns practice into measurable detection skill.", 1100, 0, 4096, 0, [], "ENABLER");
  m("lab-purple", "lab", "Purple-team range", "Technique execution linked to ATT&CK IDs in one loop with your own telemetry, ending in a coverage gap export.", 1650, 0, 6144, 0, ["lab-telemetry"], "PROFILE 06");

  /* ---- release engineering ---- */
  m("rel-signing", "rel", "GPG signing & verification", "Published project key, signature tooling and a written verification procedure for every artefact.", 8, 6, 0, 0, [], "");
  m("rel-repro", "rel", "Reproducible build scripts", "The committed live-build configuration plus an SBOM generator, so anyone can rebuild and diff the image.", 20, 4, 0, 0, [], "TRUST");
  m("rel-repo", "rel", "Signed local APT repository", "A project repository signed in-image, so post-boot package installs are verifiable rather than ad hoc.", 65, 5, 0, 0, ["rel-signing"], "TRUST");
  m("rel-secureboot", "rel", "Secure Boot chain", "Signed shim chain for machines that require Secure Boot to stay enabled.", 40, 8, 0, 0, ["rel-signing"], "OPTIONAL");
  m("rel-hardening", "rel", "Hardening baseline", "CIS-style baseline profile plus nftables default-deny egress, so the lab cannot leak onto your home network.", 18, 10, 0, 0, [], "SAFETY");

  /* --------------------------------- STATE -------------------------------- */
  var sel = {};

  function byId(id) {
    for (var i = 0; i < MODULES.length; i++) if (MODULES[i].id === id) return MODULES[i];
    return null;
  }
  function $id(s) { return document.getElementById(s); }
  function toast(msg) {
    var n = $id("toast");
    n.textContent = msg;
    n.classList.add("on");
    clearTimeout(toast._t);
    toast._t = setTimeout(function () { n.classList.remove("on"); }, 2400);
  }

  /* -------------------------------- RENDER -------------------------------- */
  function render() {
    GROUPS.forEach(function (G) {
      var host = $id("mg-" + G.id);
      if (!host) return;
      host.innerHTML = "";
      MODULES.filter(function (x) { return x.g === G.id; }).forEach(function (x) {
        var lab = document.createElement("label");
        lab.className = "mod";

        var cb = document.createElement("input");
        cb.type = "checkbox";
        cb.checked = !!sel[x.id];
        cb.id = "cb-" + x.id;
        cb.setAttribute("aria-describedby", "d-" + x.id);
        cb.addEventListener("change", function () {
          if (cb.checked) { sel[x.id] = true; resolve(x.id); }
          else { delete sel[x.id]; prune(x.id); }
          render(); compute();
        });

        var txt = document.createElement("div");
        txt.className = "txt";
        var b = document.createElement("b");
        b.textContent = x.n;
        var sp = document.createElement("span");
        sp.id = "d-" + x.id;
        sp.textContent = x.d;
        txt.appendChild(b); txt.appendChild(sp);

        var sz = document.createElement("span");
        sz.className = "size";
        sz.textContent = x.size === 0 ? "—" : (x.size >= 1024 ? (x.size / 1024).toFixed(1) + " GiB" : x.size + " MiB");

        lab.appendChild(cb); lab.appendChild(txt);
        if (x.tag) {
          var tg = document.createElement("span");
          tg.className = "req";
          tg.textContent = x.tag;
          lab.appendChild(tg);
        }
        lab.appendChild(sz);
        host.appendChild(lab);
      });
    });
  }

  /* auto-enable dependencies (and their transitive deps) */
  function resolve(id, chain) {
    chain = chain || [];
    var x = byId(id);
    if (!x) return;
    x.needs.forEach(function (n) {
      if (!sel[n]) {
        sel[n] = true;
        if (chain.indexOf(n) === -1) { chain.push(n); resolve(n, chain); }
      }
    });
    if (chain.length && id === chain[0]) {
      toast("Also enabled: " + chain.map(function (c) { return byId(c).n; }).join(", "));
    }
  }

  /* drop dependants when a dependency is unchecked */
  function prune(removedId) {
    var changed = true, dropped = [];
    while (changed) {
      changed = false;
      MODULES.forEach(function (x) {
        if (!sel[x.id]) return;
        for (var i = 0; i < x.needs.length; i++) {
          if (!sel[x.needs[i]]) {
            delete sel[x.id];
            dropped.push(x.n);
            changed = true;
            break;
          }
        }
      });
    }
    if (dropped.length) toast("Also disabled (needs a removed module): " + dropped.join(", "));
  }

  /* -------------------------------- METRICS ------------------------------- */
  function compute() {
    var picked = MODULES.filter(function (x) { return sel[x.id]; });
    var size = 0, pkgs = 0, ram = 0, disk = 0;
    picked.forEach(function (x) {
      size += x.size; pkgs += x.pkgs;
      if (x.ram > ram) ram = x.ram;
      if (x.disk > disk) disk = x.disk;
    });

    $id("s-count").textContent = picked.length;
    $id("s-pkgs").textContent = pkgs ? "~" + pkgs.toLocaleString("en-IN") : "0";
    $id("s-size").textContent = fmt(size);
    $id("s-total").textContent = fmt(size);
    $id("s-ram").textContent = ram ? fmt(ram) + " minimum" : "—";
    $id("s-disk").textContent = disk ? fmt(disk) + " (persistence)" : "—";
    $id("s-net").textContent = "No";

    /* warnings */
    var warns = [];
    var hasBase = picked.some(function (x) { return x.g === "base"; });
    if (!hasBase) warns.push("No base system selected — a live image cannot be built without one.");
    var hasModel = picked.some(function (x) { return x.id.indexOf("ai-qwen") === 0; });
    if (hasModel && !sel["ai-llama"]) warns.push("A model is selected without the llama.cpp runtime; the runtime is required to run inference.", true);
    if (ram >= 8192) warns.push("This build needs roughly " + fmt(ram) + " of RAM to run comfortably. Test it in QEMU before a physical boot.");
    if (size > 4096) warns.push("Estimated image is " + fmt(size) + ". Use a USB drive of at least " + fmt(Math.ceil((size * 1.15) / 1024) * 1024) + " and expect a long download.");
    var hasC2 = picked.some(function (x) { return x.id === "tools-c2" || x.id === "lab-c2"; });
    if (hasC2) warns.push("C2 modules are included. Run them only on an internal switch with egress denied, and read the C2 frameworks page first.");
    if (picked.length && !sel["rel-hardening"]) warns.push("Hardening is not selected. Without default-deny egress the lab can reach networks you did not intend to touch.", true);

    var wb = $id("s-warn");
    if (warns.length) {
      wb.hidden = false;
      wb.innerHTML = warns.map(function (t) { return "• " + escapeHtml(t); }).join("<br>");
    } else {
      wb.hidden = true; wb.innerHTML = "";
    }

    return { picked: picked, size: size, pkgs: pkgs, ram: ram, disk: disk, warns: warns };
  }

  function fmt(mib) {
    if (!mib) return "0 MiB";
    if (mib >= 1024) return (mib / 1024).toFixed(mib >= 10240 ? 0 : 1) + " GiB";
    return mib + " MiB";
  }
  function escapeHtml(s) {
    return String(s).replace(/[&<>"']/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
    });
  }

  /* -------------------------------- MANIFEST ------------------------------ */
  function manifest() {
    var s = compute();
    var L = [];
    var base = sel["base-minimal"] ? "minimal" : sel["base-xfce"] ? "xfce" : "none";
    var date = new Date().toISOString().slice(0, 10);

    L.push("# RATAN OS Advanced Edition — custom build manifest");
    L.push("# Generated by the build planner at https://ratan-patel.github.io/ratan-os-advanced.html");
    L.push("# Date: " + date);
    L.push("# Estimates are planning figures, not measurements.");
    L.push("");
    L.push("profile: ratan-os-advanced");
    L.push("distro: debian-trixie");
    L.push("architecture: amd64");
    L.push("desktop: " + (base === "none" ? "unset" : base));
    L.push("offline_by_design: true");
    L.push("");
    L.push("estimate:");
    L.push("  modules: " + s.picked.length);
    L.push("  packages: " + s.pkgs);
    L.push("  image_size: \"" + fmt(s.size) + "\"");
    L.push("  min_ram: \"" + fmt(s.ram || 0) + "\"");
    L.push("  persistence_disk: \"" + fmt(s.disk || 0) + "\"");
    L.push("");

    GROUPS.forEach(function (G) {
      var items = s.picked.filter(function (x) { return x.g === G.id; });
      if (!items.length) return;
      L.push("# --- " + G.n + " ---");
      L.push("modules:");
      items.forEach(function (x) {
        L.push("  - id: " + x.id);
        L.push("    name: \"" + x.n + "\"");
        L.push("    est_size_mib: " + x.size);
        L.push("    est_packages: " + x.pkgs);
        if (x.needs.length) L.push("    requires: [" + x.needs.join(", ") + "]");
      });
      L.push("");
    });

    L.push("# --- Debian live-build bootstrap (reference pipeline) ---");
    L.push("# 1. lb config --distribution trixie --architectures amd64 \\");
    L.push("#      --archive-areas \"main contrib non-free-firmware\" \\");
    L.push("#      --debian-installer false --bootappend-live \"boot=live components\"");
    L.push("# 2. Apply the module package lists above into config/package-lists/");
    L.push("# 3. Layer the offline AI runtime and model into config/includes.chroot/");
    L.push("# 4. sudo lb build");
    L.push("# 5. Verify: boot in QEMU with no network adapter attached, confirm the");
    L.push("#    assistant answers and that every lab profile cannot reach the internet.");
    L.push("");
    L.push("# --- Safety check before you boot ---");
    L.push("# [ ] Lab profiles bound to an internal virtual switch only");
    L.push("# [ ] No host bridge and no NAT on the lab network");
    L.push("# [ ] Default-deny egress rules in place");
    L.push("# [ ] Snapshots taken before the first exercise");
    L.push("# [ ] No production credentials or customer data anywhere on the image");
    L.push("");
    L.push("# Authorised use only — systems and networks you own or have written");
    L.push("# permission to test. See /acceptable-use.html");

    if (s.warns.length) {
      L.push("");
      L.push("# --- Planner warnings ---");
      s.warns.forEach(function (w) { L.push("# ! " + w); });
    }
    return L.join("\n");
  }

  /* --------------------------------- EVENTS ------------------------------- */
  function bind() {
    $id("b-manifest").addEventListener("click", function () {
      $id("mani").value = manifest();
      toast("Manifest generated");
    });
    $id("b-copy").addEventListener("click", function () {
      var v = $id("mani").value || manifest();
      $id("mani").value = v;
      var ok = function () { toast("Copied to clipboard"); };
      if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(v).then(ok, function () { $id("mani").select(); ok(); });
      } else { $id("mani").select(); document.execCommand("copy"); ok(); }
    });
    $id("b-iso").addEventListener("click", function () {
      sel = {};
      MODULES.forEach(function (x) { if (x.id !== "ai-qwen3-8b" && x.id !== "ai-gpu") sel[x.id] = true; });
      render(); compute(); $id("mani").value = manifest();
      toast("Full preset applied — everything except the heaviest AI options");
    });
    $id("b-lite").addEventListener("click", function () {
      sel = {};
      ["base-minimal", "ai-llama", "ai-qwen15", "ai-ui", "tools-ai-redteam", "tools-attack", "tools-report", "rel-signing", "rel-hardening"]
        .forEach(function (id) { sel[id] = true; });
      render(); compute(); $id("mani").value = manifest();
      toast("Lite preset applied — a compact offline-AI lab image");
    });
  }

  /* --------------------------------- BOOT --------------------------------- */
  /* Start from the shipped v1.2.0 AI Edition shape so the page opens on
     something realistic rather than an empty checklist. */
  ["base-xfce", "ai-llama", "ai-qwen3-4b", "ai-ui", "tools-ai-redteam", "tools-attack", "tools-report", "rel-signing", "rel-hardening"]
    .forEach(function (id) { sel[id] = true; });

  render();
  bind();
  compute();
  $id("mani").value = manifest();
})();
