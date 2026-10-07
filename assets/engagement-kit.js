/* ============================================================================
   RATAN_PATEL.SEC — Engagement Kit
   Generates: Authorization to Test, Rules of Engagement, Scope & Exclusions,
   Abort Procedure and Engagement Log from one set of inputs.
   Runs entirely client-side. Nothing is transmitted or stored.

   NOT LEGAL ADVICE. These are templates for authorised security testing.
   ============================================================================ */
(function () {
  "use strict";

  /* ------------------------- PERMITTED ACTIVITIES ------------------------- */
  var PERMS = [
    { id: "scan", n: "Vulnerability scanning and manual testing", d: "Automated scanning plus manual verification of findings, strictly within the named assets.", flag: "BASELINE", on: true },
    { id: "auth", n: "Authenticated testing with provided accounts", d: "Testing using the test accounts listed in the scope. Assessor creates no additional accounts unless the next item is enabled.", flag: "BASELINE", on: true },
    { id: "exploit", n: "Safe exploitation to demonstrate impact", d: "Proof-of-concept exploitation sufficient to demonstrate that a finding is real. No destructive payloads, no data modification.", flag: "COMMON" },
    { id: "privesc", n: "Privilege escalation within scope", d: "Escalating from a provided or obtained account to a higher privilege level on in-scope assets.", flag: "COMMON" },
    { id: "lateral", n: "Lateral movement between in-scope hosts", d: "Pivoting between hosts that are named in the in-scope list. Movement to any unnamed host is a scope breach and triggers the abort procedure.", flag: "ADVANCED" },
    { id: "persist", n: "Persistence in the client environment", d: "Requires an implant register maintained throughout, egress notification to the client network team, and complete removal before sign-off.", flag: "HIGH IMPACT", danger: true },
    { id: "hashcrack", n: "Password cracking against obtained hashes", d: "Cracking is performed on assessor-controlled infrastructure. Client systems are not used for compute.", flag: "STANDARD" },
    { id: "phish", n: "Social engineering / phishing simulation", d: "Requires a named target population, an approved pretext, an exclusion list for sensitive roles (HR, legal, finance, executives on request), and a stop-the-campaign trigger.", flag: "HIGH IMPACT", danger: true, needs: "targets" },
    { id: "physical", n: "Physical security testing", d: "Requires named sites, an agreed approach notification for site security, and an escort arrangement where required by the client.", flag: "HIGH IMPACT", danger: true },
    { id: "dos", n: "Denial-of-service / load testing", d: "Can cause an outage. Requires a separate maintenance window, explicit business-owner sign-off, an agreed blast radius and monitoring in place before the first packet.", flag: "CRITICAL", danger: true },
    { id: "exfil", n: "Data exfiltration proof-of-concept", d: "Proof limited to an assessor-created canary file. No real client or personal data leaves the environment under any circumstances.", flag: "HIGH IMPACT", danger: true },
    { id: "c2", n: "Command-and-control infrastructure in the client environment", d: "Requires a documented implant and redirector register, egress notification, and confirmed destruction of all infrastructure at closure.", flag: "ADVANCED", danger: true },
    { id: "cloudapi", n: "Cloud / API provider-level testing", d: "Permitted only where the provider's own penetration-testing policy allows it. Record the policy version and date in the engagement reference.", flag: "CONDITIONAL", danger: true, needs: "provider" },
    { id: "thirdparty", n: "Testing third-party or shared infrastructure", d: "A client cannot authorise infrastructure they do not own. Enable only with the third party's own written permission on file.", flag: "BLOCKED BY DEFAULT", danger: true, needs: "thirdparty" }
  ];

  function $(id) { return document.getElementById(id); }
  function val(id) { return ($(id) && $(id).value || "").trim(); }
  function TBD(v) { return v ? v : "[TO BE COMPLETED]"; }
  function lines(id) {
    return val(id).split("\n").map(function (s) { return s.trim(); }).filter(Boolean);
  }
  function bullets(id, empty) {
    var l = lines(id);
    if (!l.length) return ["  - " + (empty || "[NONE LISTED — this is a gap, complete it]")];
    return l.map(function (s) { return "  - " + s; });
  }
  function numList(id, empty) {
    var l = lines(id);
    if (!l.length) return ["  [NONE LISTED — complete this before testing]"];
    return l.map(function (s, i) { return "  " + (i + 1) + ". " + s; });
  }
  function pad(s, n) { s = String(s); while (s.length < n) s += " "; return s; }
  function rule(ch) { ch = ch || "="; var s = ""; for (var i = 0; i < 76; i++) s += ch; return s; }
  function pretty(dt) {
    if (!dt) return "[NOT SET]";
    var d = new Date(dt);
    if (isNaN(d)) return dt;
    var months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
    var hh = d.getHours(), mm = d.getMinutes();
    var ap = hh >= 12 ? "PM" : "AM";
    var h12 = hh % 12; if (h12 === 0) h12 = 12;
    return pad(d.getDate(), 2) + " " + months[d.getMonth()] + " " + d.getFullYear() + ", " + pad(h12, 2) + ":" + pad(mm, 2) + " " + ap;
  }
  function today() { var d = new Date(); return pretty(d.toISOString().slice(0, 16)); }
  function enabled() {
    var out = [];
    PERMS.forEach(function (p) { if ($("perm-" + p.id) && $("perm-" + p.id).checked) out.push(p); });
    return out;
  }
  function permOn(id) { var e = $("perm-" + id); return !!(e && e.checked); }
  function toast(msg) {
    var n = $("toast"); n.textContent = msg; n.classList.add("on");
    clearTimeout(toast._t); toast._t = setTimeout(function () { n.classList.remove("on"); }, 2200);
  }
  function prodEnv() { return val("k-env").indexOf("Production") === 0 || val("k-env").indexOf("Both") === 0; }

  /* ==================== 01 · AUTHORISATION TO TEST ======================== */
  function docAuthorisation() {
    var L = [];
    L.push(rule("="));
    L.push("          AUTHORISATION TO TEST");
    L.push("          Permission to conduct authorised security testing");
    L.push(rule("="));
    L.push("");
    L.push("Engagement reference : " + TBD(val("k-ref")));
    L.push("Engagement type      : " + val("k-type"));
    L.push("Prepared for         : " + TBD(val("k-client")));
    L.push("Prepared by          : " + val("k-assessor") + " — " + val("k-assessororg"));
    L.push("Document date        : " + today());
    L.push("Governing law        : " + val("k-juris"));
    L.push("");
    L.push(rule("-"));
    L.push("1. GRANT OF PERMISSION");
    L.push(rule("-"));
    L.push("");
    L.push("I, " + TBD(val("k-signatory")) + ", acting with authority over the assets listed in");
    L.push("section 2 below, grant " + val("k-assessororg") + " (" + val("k-assessor") + ")");
    L.push("permission to perform the security assessment described in this document and in");
    L.push("the accompanying Rules of Engagement (the \"engagement\").");
    L.push("");
    L.push("I confirm that:");
    L.push("  (a) I hold the authority to grant this permission for every asset listed;");
    L.push("  (b) any asset not listed in section 2 is NOT authorised for testing;");
    L.push("  (c) testing of third-party or shared infrastructure requires that third party's");
    L.push("      own written permission, which is not granted by this document;");
    L.push("  (d) I will ensure the named contacts remain reachable during the authorised period.");
    L.push("");
    L.push(rule("-"));
    L.push("2. AUTHORISED ASSETS (IN SCOPE)");
    L.push(rule("-"));
    L.push("");
    numList("k-scope").forEach(function (s) { L.push(s); });
    L.push("");
    L.push("Only the assets above are authorised. Testing must not extend to any host, path,");
    L.push("account, tenant or environment not listed here.");
    L.push("");
    L.push(rule("-"));
    L.push("3. EXPLICITLY NOT AUTHORISED (OUT OF SCOPE)");
    L.push(rule("-"));
    L.push("");
    bullets("k-exclude", "[NO EXCLUSIONS LISTED — this section must be completed before testing begins]")
      .forEach(function (s) { L.push(s); });
    L.push("");
    L.push("The absence of an asset from section 3 does not place it in scope. Scope is defined");
    L.push("solely by inclusion in section 2.");
    L.push("");
    L.push(rule("-"));
    L.push("4. AUTHORISED PERIOD");
    L.push(rule("-"));
    L.push("");
    L.push("  From : " + pretty(val("k-window-from")) + " " + val("k-tz"));
    L.push("  To   : " + pretty(val("k-window-to")) + " " + val("k-tz"));
    L.push("");
    L.push("Testing performed before the start or after the end of this period is not authorised.");
    L.push("Any extension must be issued in writing and appended to this document.");
    L.push("");
    L.push(rule("-"));
    L.push("5. PERMITTED ACTIVITIES");
    L.push(rule("-"));
    L.push("");
    var ps = enabled();
    if (!ps.length) {
      L.push("  [NONE SELECTED — no activity is authorised until this list is populated]");
    } else {
      ps.forEach(function (p, i) { L.push("  " + (i + 1) + ". " + p.n); });
    }
    L.push("");
    L.push("Activities not listed above are not authorised, including but not limited to:");
    L.push("denial-of-service testing, physical intrusion, social engineering, deployment of");
    L.push("persistent access, and removal of any data from the environment.");
    L.push("");
    L.push(rule("-"));
    L.push("6. DATA HANDLING");
    L.push(rule("-"));
    L.push("");
    L.push("  Maximum data classification accessed : " + val("k-data"));
    L.push("  Evidence retention                   : " + TBD(val("k-retention")));
    L.push("  Evidence destruction date            : " + (val("k-destroy") ? val("k-destroy") : "[NOT SET]"));
    L.push("");
    L.push("Any data encountered is accessed only to the minimum extent required to demonstrate");
    L.push("impact, is stored on encrypted media controlled by the assessor, and is destroyed on");
    L.push("the date above with written confirmation to the client.");
    L.push("");
    L.push(rule("-"));
    L.push("7. IMPACT AND ESCALATION");
    L.push(rule("-"));
    L.push("");
    L.push("  Client technical contact : " + TBD(val("k-tc")) + " " + (val("k-tce") ? "(" + val("k-tce") + ")" : ""));
    L.push("  Emergency contact 1      : " + TBD(val("k-ec1")));
    L.push("  Emergency contact 2      : " + TBD(val("k-ec2")));
    L.push("  Client SOC / on-call     : " + TBD(val("k-soc")));
    L.push("  Defending team informed  : " + (val("k-blueknown") === "blind" ? "NO — blind test, approved in writing" : "Yes"));
    L.push("");
    L.push("If testing causes or may cause service disruption, data integrity impact, or any");
    L.push("unexpected effect outside the authorised assets, testing stops immediately and the");
    L.push("primary technical contact is notified without delay, followed by the emergency");
    L.push("contacts in the order listed.");
    L.push("");
    L.push(rule("-"));
    L.push("8. SIGNATURES");
    L.push(rule("-"));
    L.push("");
    L.push("Signed on behalf of the asset owner:");
    L.push("");
    L.push("  Signature : ______________________________________");
    L.push("");
    L.push("  Name      : " + TBD(val("k-signatory")));
    L.push("  Client    : " + TBD(val("k-client")));
    L.push("  Email     : " + TBD(val("k-signemail")));
    L.push("  Date      : ______________________________________");
    L.push("");
    L.push(rule("-"));
    L.push("");
    L.push("Acknowledged by the assessor:");
    L.push("");
    L.push("  Signature : ______________________________________");
    L.push("");
    L.push("  Name      : " + val("k-assessor"));
    L.push("  Company   : " + val("k-assessororg"));
    L.push("  Date      : ______________________________________");
    L.push("");
    L.push(rule("="));
    L.push(" This template is not legal advice. Have it reviewed by qualified counsel");
    L.push(" before signing. Retain the signed original where you can produce it quickly.");
    L.push(rule("="));
    return L.join("\n");
  }

  /* ==================== 02 · RULES OF ENGAGEMENT ========================== */
  function docROE() {
    var L = [];
    L.push(rule("="));
    L.push("          RULES OF ENGAGEMENT (RoE)");
    L.push(rule("="));
    L.push("");
    L.push("Engagement reference : " + TBD(val("k-ref")));
    L.push("Client               : " + TBD(val("k-client")));
    L.push("Assessor             : " + val("k-assessor") + " — " + val("k-assessororg"));
    L.push("Engagement type      : " + val("k-type"));
    L.push("Knowledge base       : " + val("k-mode"));
    L.push("Environment          : " + val("k-env"));
    L.push("Document date        : " + today());
    L.push("");
    L.push("These rules form part of the authorisation. Where they conflict with any other");
    L.push("document, the stricter rule applies.");
    L.push("");

    L.push(rule("-"));
    L.push("1. AUTHORITY AND CONTROL");
    L.push(rule("-"));
    L.push("");
    L.push("  Authorising signatory     : " + TBD(val("k-signatory")) + " (" + TBD(val("k-signemail")) + ")");
    L.push("  Technical contact         : " + TBD(val("k-tc")) + " " + TBD(val("k-tce")));
    L.push("  Emergency contact 1 (24x7): " + TBD(val("k-ec1")));
    L.push("  Emergency contact 2 (24x7): " + TBD(val("k-ec2")));
    L.push("  SOC / on-call             : " + TBD(val("k-soc")));
    L.push("");
    L.push("The authorising signatory is the only party who may expand scope, extend the test");
    L.push("window, or authorise additional activity. Any such change must be in writing and");
    L.push("appended to this document before the activity occurs.");
    L.push("");

    L.push(rule("-"));
    L.push("2. SCOPE");
    L.push(rule("-"));
    L.push("");
    L.push("IN SCOPE:");
    numList("k-scope").forEach(function (s) { L.push(s); });
    L.push("");
    L.push("OUT OF SCOPE:");
    bullets("k-exclude", "[NONE LISTED — complete this before testing begins]")
      .forEach(function (s) { L.push(s); });
    L.push("");
    L.push("Scope is defined by inclusion only. Any asset not listed as in scope is out of");
    L.push("scope, regardless of whether it was discovered during testing, whether it shares");
    L.push("credentials or infrastructure with an in-scope asset, or whether it appears trivially");
    L.push("reachable. Discovery of such an asset is reported, not tested.");
    L.push("");

    L.push(rule("-"));
    L.push("3. TEST WINDOW");
    L.push(rule("-"));
    L.push("");
    L.push("  Start : " + pretty(val("k-window-from")) + " " + val("k-tz"));
    L.push("  End   : " + pretty(val("k-window-to")) + " " + val("k-tz"));
    L.push("");
    L.push("  High-impact activity windows, if any:");
    if (permOn("dos")) L.push("    - Denial-of-service testing ONLY within a separately agreed maintenance window:");
    if (permOn("dos")) L.push("      " + TBD("") + " [SPECIFY THE MAINTENANCE WINDOW HERE BEFORE PROCEEDING]");
    if (permOn("phish")) L.push("    - Phishing simulation ONLY within: [SPECIFY CAMPAIGN WINDOW]");
    if (permOn("physical")) L.push("    - Physical testing ONLY within: [SPECIFY SITE AND WINDOW]");
    if (!permOn("dos") && !permOn("phish") && !permOn("physical")) L.push("    - None.");
    L.push("");

    L.push(rule("-"));
    L.push("4. PERMITTED TECHNIQUES");
    L.push(rule("-"));
    L.push("");
    var ps = enabled();
    if (!ps.length) {
      L.push("  [NONE SELECTED — no activity is authorised]");
    } else {
      ps.forEach(function (p, i) {
        L.push("  " + (i + 1) + ". " + p.n);
        L.push("     " + p.d);
        L.push("     Authority level: " + p.flag);
        if (p.danger) L.push("     *** HIGH-IMPACT ACTIVITY — confirm with the signatory that this is intended ***");
        L.push("");
      });
    }

    L.push(rule("-"));
    L.push("5. IMPACT CEILING AND PROHIBITED EFFECTS");
    L.push(rule("-"));
    L.push("");
    L.push("Regardless of what is listed as permitted, the following are prohibited unless");
    L.push("expressly authorised above:");
    L.push("");
    L.push("  - Causing a service outage, degradation visible to end users, or failover event");
    L.push("  - Modifying, deleting or corrupting any data");
    L.push("  - Locking out, disabling or altering any real user account");
    L.push("  - Deploying destructive payloads, wipers, or anything with self-propagation");
    L.push("  - Testing assets in section 2 of the authorisation that were not listed");
    L.push("  - Removing any real client or personal data from the environment");
    L.push("  - Touching safety-critical, medical, industrial-control or life-support systems");
    L.push("");
    L.push("  Environment note: " + (prodEnv()
      ? "PRODUCTION IS IN SCOPE for this engagement. Every technique must be re-evaluated "
        + "for production impact immediately before it is run, and any doubt is resolved in "
        + "favour of not running it. Activity is preferred outside business hours where the "
        + "client's peak load makes impact more likely."
      : "Staging / non-production only. If a technique cannot be demonstrated in this "
        + "environment, it is reported as untested rather than run against production."));
    L.push("");

    L.push(rule("-"));
    L.push("6. DEFENDER COORDINATION");
    L.push(rule("-"));
    L.push("");
    if (val("k-blueknown") === "blind") {
      L.push("  This is a BLIND engagement. The defending team has not been informed.");
      L.push("");
      L.push("  Required safeguards for a blind test:");
      L.push("    - A named business-level owner who can stop the engagement on request");
      L.push("    - The named emergency contacts remain reachable for the whole window");
      L.push("    - If the SOC raises an incident, the assessor does not simply disappear: the");
      L.push("      white-cell owner authorises a stand-down at their discretion");
      L.push("    - Any real incident occurring during the window is reported through the same");
      L.push("      emergency path, and testing pauses until the client clears resumption");
    } else {
      L.push("  The defending team is informed. Detection findings are recorded as evidence of");
      L.push("  the SOC's capability - the value of this engagement is as much in what was");
      L.push("  detected as in what was not. Assessor will not attempt to actively evade an");
      L.push("  informed responding analyst without agreeing this change in writing first.");
    }
    L.push("");

    L.push(rule("-"));
    L.push("7. DATA HANDLING AND EVIDENCE");
    L.push(rule("-"));
    L.push("");
    L.push("  Maximum data classification : " + val("k-data"));
    L.push("  Retention                   : " + TBD(val("k-retention")));
    L.push("  Destruction date            : " + (val("k-destroy") || "[NOT SET]"));
    L.push("");
    L.push("  - Evidence is stored on encrypted media controlled by the assessor");
    L.push("  - Screenshots are limited to the minimum needed to demonstrate impact");
    L.push("  - Personal data encountered is minimised, not collected");
    L.push("  - Destruction is confirmed in writing to the client on the stated date");
    L.push("  - Any credential obtained is reported so it can be rotated, not retained");
    L.push("");

    L.push(rule("-"));
    L.push("8. ABORT PROCEDURE");
    L.push(rule("-"));
    L.push("");
    L.push("Testing stops IMMEDIATELY, without waiting for confirmation, when any of these occur:");
    L.push("");
    L.push("  (a) unexpected service disruption, outage, or visible degradation");
    L.push("  (b) any unintended effect on an out-of-scope asset");
    L.push("  (c) a real security incident is detected in progress");
    L.push("  (d) any doubt arises about whether an action is authorised");
    L.push("  (e) the client issues a stop instruction through any named contact");
    L.push("");
    L.push("On abort, the assessor:");
    L.push("  1. stops activity within a single command;");
    L.push("  2. notifies the primary technical contact immediately, then the emergency");
    L.push("     contacts in order, using an out-of-band channel;");
    L.push("  3. records the time, the technique in progress, and the observed effect;");
    L.push("  4. reverts any change made, where safe to do so;");
    L.push("  5. does not resume until the authorising signatory confirms in writing.");
    L.push("");

    L.push(rule("-"));
    L.push("9. CLOSURE");
    L.push(rule("-"));
    L.push("");
    L.push("  Report delivery date : " + (val("k-report") || "[NOT SET]"));
    L.push("  Retest window        : " + TBD(val("k-retest")));
    L.push("");
    L.push("  At closure the assessor confirms in writing that:");
    L.push("    - every implant, account, file or configuration change was removed or reverted");
    L.push("    - any obtained credential was reported to the client for rotation");
    L.push("    - evidence remains within the retention and destruction terms above");
    L.push("");

    L.push(rule("-"));
    L.push("10. LIABILITY AND GOVERNING LAW");
    L.push(rule("-"));
    L.push("");
    L.push("  Governing jurisdiction : " + val("k-juris"));
    L.push("");
    L.push("  Authorisation to test is not a waiver of liability. Testing outside the authorised");
    L.push("  scope remains the assessor's responsibility regardless of this document. The");
    L.push("  assessor's professional indemnity cover, liability limits and any agreed");
    L.push("  insurance requirements are set out in the commercial agreement between the parties.");
    L.push("  This document does not create a warranty that the assessment will identify every");
    L.push("  vulnerability, and no such guarantee is given.");
    L.push("");
    L.push(rule("="));
    L.push(" ACCEPTANCE");
    L.push(rule("="));
    L.push("");
    L.push("  Authorising signatory : " + TBD(val("k-signatory")));
    L.push("  Signature             : ______________________________________");
    L.push("  Date                  : ______________________________________");
    L.push("");
    L.push("  Assessor              : " + val("k-assessor"));
    L.push("  Signature             : ______________________________________");
    L.push("  Date                  : ______________________________________");
    L.push("");
    L.push(rule("="));
    L.push(" Template — not legal advice. Review with qualified counsel before signing.");
    L.push(rule("="));
    return L.join("\n");
  }

  /* ==================== 03 · SCOPE CHECKLIST ============================== */
  function docScope() {
    var L = [];
    L.push(rule("="));
    L.push("          SCOPE & EXCLUSIONS CHECKLIST");
    L.push(rule("="));
    L.push("");
    L.push("Engagement : " + TBD(val("k-ref")) + "  |  " + val("k-type"));
    L.push("Client     : " + TBD(val("k-client")));
    L.push("Environment: " + val("k-env"));
    L.push("Date       : " + today());
    L.push("");
    L.push("Work through this before the first packet leaves your machine. Every unchecked");
    L.push("box in section A is a reason not to start.");
    L.push("");
    L.push(rule("-"));
    L.push("A. PRE-ENGAGEMENT GATE");
    L.push(rule("-"));
    L.push("");
    var p = val("k-signatory"), sc = lines("k-scope"), ex = lines("k-exclude");
    var w = val("k-window-from") && val("k-window-to");
    var contacts = val("k-ec1") && val("k-ec2");
    var gate = [
      ["Signed authorisation from a person with authority over the assets", !!p],
      ["Scope lists named assets (hosts, paths, tenants, accounts, builds)", sc.length > 0],
      ["Exclusions section completed and non-empty", ex.length > 0],
      ["Test window has both a start and an end", !!w],
      ["Two emergency contacts reachable 24x7", !!contacts],
      ["Out-of-band abort channel agreed (not the engagement chat)", false],
      ["Rollback / revert plan written for every change that will be made", false],
      ["Evidence storage is encrypted and access-controlled", false],
      ["Cloud / hosting provider policy checked, where infrastructure is hosted", false],
      ["Third-party written permission on file, where shared systems are involved", false],
      ["Data retention and destruction dates agreed", !!(val("k-retention") && val("k-destroy"))],
      ["Professional indemnity cover confirmed for this engagement type", false]
    ];
    gate.forEach(function (g) { L.push("  [ ] " + g[0] + (g[1] ? "        (data provided - still confirm verbally)" : "")); });
    L.push("");
    L.push(rule("-"));
    L.push("B. ASSETS IN SCOPE");
    L.push(rule("-"));
    L.push("");
    sc.forEach(function (s, i) {
      L.push("  [ ] " + (i + 1) + ". " + s);
      L.push("        Identifiers confirmed?  [ ] host/range  [ ] path/endpoint  [ ] tenant");
      L.push("        Environment confirmed?  [ ] staging  [ ] production");
      L.push("        Owner confirmed?        [ ] yes — name: ______________________");
    });
    if (!sc.length) L.push("  [ ] [NO IN-SCOPE ASSETS LISTED — nothing is authorised]");
    L.push("");
    L.push(rule("-"));
    L.push("C. EXPLICITLY OUT OF SCOPE");
    L.push(rule("-"));
    L.push("");
    ex.forEach(function (s) { L.push("  [x] " + s); });
    var defaults = [
      "Any asset not listed in section B",
      "Third-party, SaaS or shared infrastructure without that provider's permission",
      "Payment, billing and PCI-scoped systems",
      "Employee personal devices and personal accounts",
      "Safety-critical, medical and industrial-control systems"
    ];
    defaults.forEach(function (d) { L.push("  [x] " + d + "   (baseline exclusion — keep unless removed in writing)"); });
    if (!ex.length) L.push("  [ ] [NO EXCLUSIONS LISTED — silence is not a boundary. Complete this.]");
    L.push("");
    L.push(rule("-"));
    L.push("D. ACCOUNTS AND CREDENTIALS");
    L.push(rule("-"));
    L.push("");
    var acc = lines("k-accounts");
    if (acc.length) acc.forEach(function (s) { L.push("  [ ] " + s); });
    else L.push("  [ ] [NONE DESCRIBED — state which accounts are provided and their role]");
    L.push("");
    L.push("  [ ] Credentials received over an encrypted channel, not plain email");
    L.push("  [ ] Credentials marked for rotation at closure");
    L.push("  [ ] No production administrator credential used unless explicitly required");
    L.push("");
    L.push(rule("-"));
    L.push("E. ACTIVITY AUTHORISATION");
    L.push(rule("-"));
    L.push("");
    PERMS.forEach(function (pm) {
      var on = permOn(pm.id);
      L.push("  [" + (on ? "x" : " ") + "] " + pm.n + "   [" + pm.flag + "]");
      if (on && pm.danger) L.push("       ^ confirmed in writing with the signatory? [ ] yes  Date: __________");
    });
    L.push("");
    L.push(rule("-"));
    L.push("F. CONTACTS REACHABLE");
    L.push(rule("-"));
    L.push("");
    L.push("  Technical contact  : " + TBD(val("k-tc")) + "  " + TBD(val("k-tce")));
    L.push("  Emergency 1 (24x7) : " + TBD(val("k-ec1")));
    L.push("  Emergency 2 (24x7) : " + TBD(val("k-ec2")));
    L.push("  SOC / on-call      : " + TBD(val("k-soc")));
    L.push("  Defender awareness : " + (val("k-blueknown") === "blind" ? "BLIND — business owner still named and reachable" : "Informed"));
    L.push("");
    L.push("  [ ] All numbers tested before the window opens");
    L.push("  [ ] Escalation order agreed and written down");
    L.push("");
    L.push(rule("="));
    L.push(" No unchecked box in section A means: do not start.");
    L.push(rule("="));
    return L.join("\n");
  }

  /* ==================== 04 · ABORT PROCEDURE ============================== */
  function docAbort() {
    var L = [];
    L.push(rule("="));
    L.push("          ABORT PROCEDURE / KILL SWITCH");
    L.push(rule("="));
    L.push("");
    L.push("Engagement : " + TBD(val("k-ref")) + "  |  " + TBD(val("k-client")));
    L.push("Window     : " + pretty(val("k-window-from")) + "  to  " + pretty(val("k-window-to")) + " " + val("k-tz"));
    L.push("Date       : " + today());
    L.push("");
    L.push("This page is designed to be printed and kept next to the operator. Under stress,");
    L.push("nobody reads a long document. This one fits on one page on purpose.");
    L.push("");
    L.push(rule("-"));
    L.push("STOP IMMEDIATELY IF ANY OF THESE IS TRUE");
    L.push(rule("-"));
    L.push("");
    L.push("  [ ] Unexpected outage, degradation, or visible service impact");
    L.push("  [ ] Any effect on an asset that is not in the in-scope list");
    L.push("  [ ] A real security incident appears to be in progress");
    L.push("  [ ] Any doubt about whether the current action is authorised");
    L.push("  [ ] The client issues a stop instruction through any named contact");
    L.push("  [ ] Loss of contact with the person who can authorise the engagement");
    L.push("");
    L.push("When in doubt: STOP. An aborted engagement is a recoverable problem. An");
    L.push("outage during a test is not.");
    L.push("");
    L.push(rule("-"));
    L.push("THE ABORT IN FOUR STEPS");
    L.push(rule("-"));
    L.push("");
    L.push("  STEP 1 - STOP");
    L.push("    Cease activity within a single command. Terminate sessions, beacons and");
    L.push("    any background process. Do not 'finish the current step first'.");
    L.push("");
    L.push("  STEP 2 - CALL, OUT OF BAND");
    L.push("    Use a channel other than the engagement chat.");
    L.push("");
    L.push("      1st  " + TBD(val("k-tc")) + "   " + TBD(val("k-tce")));
    L.push("      2nd  " + TBD(val("k-ec1")));
    L.push("      3rd  " + TBD(val("k-ec2")));
    L.push("      CC   " + TBD(val("k-soc")) + "   (SOC / on-call)");
    L.push("");
    L.push("  STEP 3 - RECORD");
    L.push("    Time:  __________  Tactic in progress:  ____________________________");
    L.push("    Asset: ____________________________  Observed effect: ______________");
    L.push("    Last successful command: __________________________________________");
    L.push("");
    L.push("  STEP 4 - REVERT AND WAIT");
    L.push("    Reverse any change made, where it is safe to do so. Do not resume until the");
    L.push("    authorising signatory confirms resumption IN WRITING.");
    L.push("");
    L.push(rule("-"));
    L.push("SCOPE-BREACH VARIANT");
    L.push(rule("-"));
    L.push("");
    L.push("If an out-of-scope asset is touched, accidentally or through a pivot:");
    L.push("");
    L.push("  1. Stop instantly. Do not continue to see how far it goes.");
    L.push("  2. Do not remove, modify or 'clean up' anything on that asset beyond what you");
    L.push("     did - preserve the actual state so the client can assess it accurately.");
    L.push("  3. Notify the technical contact as a priority, not at end of day.");
    L.push("  4. Provide a written account of exactly what was accessed, when, and how,");
    L.push("     within 24 hours. Ambiguity here is what turns a mistake into a dispute.");
    L.push("  5. Await written instruction before touching anything further.");
    L.push("");
    L.push(rule("-"));
    L.push("DESIGNATED DECISION MAKERS");
    L.push(rule("-"));
    L.push("");
    L.push("  May issue a stop instruction : " + TBD(val("k-tc")) + ", " + TBD(val("k-ec1")) + ", " + TBD(val("k-ec2")) + ", " + TBD(val("k-signatory")));
    L.push("  May authorise resumption    : " + TBD(val("k-signatory")) + " (in writing only)");
    L.push("  Assessor's abort authority   : " + val("k-assessor") + " - unconditional, no justification required");
    L.push("");
    L.push(rule("="));
    L.push(" The assessor may always stop. Nobody needs permission to abort.");
    L.push(rule("="));
    return L.join("\n");
  }

  /* ==================== 05 · ENGAGEMENT LOG =============================== */
  function docLog() {
    var L = [];
    L.push(rule("="));
    L.push("          ENGAGEMENT LOG TEMPLATE");
    L.push(rule("="));
    L.push("");
    L.push("Engagement : " + TBD(val("k-ref")) + "  |  " + val("k-type"));
    L.push("Assessor   : " + val("k-assessor") + " — " + val("k-assessororg"));
    L.push("Client     : " + TBD(val("k-client")));
    L.push("");
    L.push("Log every action as it happens, not from memory afterwards. This log is the");
    L.push("evidence that your activity stayed inside the authorised scope, and it is the");
    L.push("first thing anyone asks for when a question arises.");
    L.push("");
    L.push(rule("-"));
    L.push("ACTION LOG");
    L.push(rule("-"));
    L.push("");
    L.push(pad("TIME", 20) + pad("ASSET", 26) + "ACTION / TECHNIQUE");
    L.push(pad("", 20, "-") + pad("", 26, "-") + "------------------");
    L.push(pad("[hh:mm] [tz]", 20) + pad("[host / url]", 26) + "[command or technique]");
    L.push(pad("", 20) + pad("", 26) + "ATT&CK:  [Txxxx]   Result: [ ] detected  [ ] blocked  [ ] nothing");
    L.push(pad("", 20) + pad("", 26) + "Notes: ______________________________________________");
    L.push("");
    L.push("(repeat the three-line block above for every action)");
    L.push("");
    L.push(rule("-"));
    L.push("CHANGE REGISTER");
    L.push(rule("-"));
    L.push("");
    L.push("Any change made to the client environment must appear here and must be reverted.");
    L.push("");
    L.push(pad("WHAT", 30) + pad("WHERE", 24) + "REVERTED?");
    L.push(pad("", 30, "-") + pad("", 24, "-") + "---------");
    L.push(pad("[account / file / config / implant]", 30) + pad("[host]", 24) + "[ ] yes  Date: ______");
    L.push("");
    if (permOn("persist") || permOn("c2")) {
      L.push("  IMPLANT / INFRASTRUCTURE REGISTER (required for this engagement)");
      L.push("");
      L.push(pad("  ID", 8) + pad("TYPE", 18) + pad("HOST", 22) + "STATUS");
      L.push(pad("  -----", 8, "-") + pad("", 18, "-") + pad("", 22, "-") + "-------");
      L.push(pad("  IMP-1", 8) + pad("[beacon / svc]", 18) + pad("[host]", 22) + "[ ] live  [ ] removed");
      L.push("");
      L.push("  Egress notification to client network team sent?  [ ] yes  Date: __________");
      L.push("");
    }
    L.push(rule("-"));
    L.push("CREDENTIALS OBTAINED");
    L.push(rule("-"));
    L.push("");
    L.push(pad("ACCOUNT", 34) + pad("SOURCE", 24) + "ROTATED?");
    L.push(pad("", 34, "-") + pad("", 24, "-") + "---------");
    L.push(pad("[user / key id]", 34) + pad("[how obtained]", 24) + "[ ] yes  Date: ______");
    L.push("");
    L.push("Report every credential so it can be rotated. Never retain a working credential");
    L.push("beyond the evidence needed to demonstrate the finding.");
    L.push("");
    L.push(rule("-"));
    L.push("DETECTION OBSERVATIONS");
    L.push(rule("-"));
    L.push("");
    L.push(pad("TECHNIQUE", 14) + pad("DETECTED?", 14) + pad("TIME TO ALERT", 18) + "NOTES");
    L.push(pad("", 14, "-") + pad("", 14, "-") + pad("", 18, "-") + "-----");
    L.push(pad("[Txxxx.xxx]", 14) + pad("[y/n/partial]", 14) + pad("[mm:ss]", 18) + "[rule / analyst / nothing]");
    L.push("");
    L.push("Record who detected it and how: a rule firing and an analyst noticing are very");
    L.push("different levels of defensive capability, and a report that conflates them is");
    L.push("misleading in a way that hurts the client later.");
    L.push("");
    L.push(rule("-"));
    L.push("INCIDENT / ABORT ENTRIES");
    L.push(rule("-"));
    L.push("");
    L.push("  If the abort procedure was invoked, record here:");
    L.push("");
    L.push("  Time of abort     : ______________");
    L.push("  Trigger           : ______________________________________");
    L.push("  Notified          : ______________________________________");
    L.push("  Reverted          : ______________________________________");
    L.push("  Resumed (by whom, when, written confirmation received): ______________");
    L.push("");
    L.push(rule("-"));
    L.push("CLOSURE CONFIRMATION");
    L.push(rule("-"));
    L.push("");
    L.push("  [ ] Every entry in the change register reverted and verified");
    L.push("  [ ] Every implant and piece of C2 infrastructure destroyed");
    L.push("  [ ] Every obtained credential reported for rotation");
    L.push("  [ ] Evidence retained only within the agreed retention period");
    L.push("  [ ] Evidence destruction date confirmed : " + (val("k-destroy") || "[NOT SET]"));
    L.push("  [ ] Report delivered : " + (val("k-report") || "[NOT SET]"));
    L.push("  [ ] Retest window    : " + TBD(val("k-retest")));
    L.push("");
    L.push("  Assessor signature : ______________________________________");
    L.push("  Date               : " + today());
    L.push("");
    L.push(rule("="));
    return L.join("\n");
  }

  /* ============================ READINESS ================================= */
  function checks() {
    var c = [];
    function add(ok, level, title, detail) { c.push({ ok: ok, level: level, title: title, detail: detail }); }

    var named = val("k-client") && val("k-signatory");
    add(!!named, named ? "ok" : "bad", "Authorisation parties named",
      named ? "Signatory recorded — confirm they hold authority over every listed asset." : "A client and an authorising signatory must be named before anything is generated that looks like permission.");

    var sc = lines("k-scope");
    add(sc.length > 0, sc.length ? "ok" : "bad", "Assets named in scope",
      sc.length ? sc.length + " asset" + (sc.length === 1 ? "" : "s") + " listed. Confirm each identifier resolves unambiguously." : "Category-level scope is not scope. Name hosts, paths, tenants, accounts and builds.");

    var ex = lines("k-exclude");
    add(ex.length > 0, ex.length ? "ok" : "bad", "Exclusions completed",
      ex.length ? ex.length + " exclusion" + (ex.length === 1 ? "" : "s") + " recorded." : "An empty exclusions section is the single most common gap. Silence is not a boundary.");

    var w = val("k-window-from") && val("k-window-to");
    var wOk = w && new Date(val("k-window-to")) > new Date(val("k-window-from"));
    add(!!wOk, wOk ? "ok" : "bad", "Test window valid",
      wOk ? "Window closes after it opens. Testing outside it is unauthorised." : (w ? "The end time is before the start time." : "Both a start and an end are required, in a stated timezone."));

    var ct = val("k-ec1") && val("k-ec2");
    add(!!ct, ct ? "ok" : "warn", "Two emergency contacts",
      ct ? "Escalation path exists if the primary contact is unreachable." : "One contact is a single point of failure. Two people, 24x7, reachable out of band.");

    add(!!val("k-soc"), false, val("k-soc") ? "ok" : "warn", "SOC / on-call notified",
      val("k-soc") ? "Defenders have a name to call if they detect you." : "A blind test is legitimate, but an on-call engineer paged at 2am with no context is not.");

    add(!!(val("k-retention") && val("k-destroy")), (val("k-retention") && val("k-destroy")) ? "ok" : "warn", "Evidence lifecycle agreed",
      (val("k-retention") && val("k-destroy")) ? "Retention period and destruction date recorded." : "Set a retention period and an explicit destruction date. Credentials and captures left on a laptop indefinitely become the audit finding.");

    if (permOn("dos")) add(false, "warn", "Denial-of-service testing enabled",
      "Requires a separate maintenance window, explicit business-owner sign-off, an agreed blast radius, and monitoring already in place. Confirm all four in writing before enabling.");
    if (permOn("phish")) add(false, "warn", "Phishing simulation enabled",
      "Needs a named target population, an approved pretext, an exclusion list for sensitive roles, and a stop-the-campaign trigger.");
    if (permOn("physical")) add(false, "warn", "Physical testing enabled",
      "Name the sites, notify site security of the approach, and agree escort requirements. Unannounced entry attempts are how police get called.");
    if (permOn("persist")) add(false, "warn", "Persistence enabled",
      "Maintain a live implant register, notify the client's network team about egress, and remove everything before sign-off. Un-removed persistence is a backdoor you built.");
    if (permOn("exfil")) add(false, "warn", "Exfiltration proof enabled",
      "Limit proof to an assessor-created canary file. No real client or personal data leaves the environment under any circumstances.");
    if (permOn("thirdparty")) add(false, "bad", "Third-party testing enabled",
      "A client cannot authorise infrastructure they do not own. Do not proceed without the third party's own written permission on file.");
    if (permOn("cloudapi")) add(false, "warn", "Cloud / provider-level testing enabled",
      "Confirm the provider's own penetration-testing policy permits this, and record the policy version and date in the engagement reference.");

    if (prodEnv() && (permOn("dos") || permOn("persist") || permOn("exfil"))) {
      add(false, "bad", "Production plus high-impact activity",
      "You have selected production as the environment and at least one high-impact activity. This combination needs an explicit business-owner decision, a maintenance window, and a named person who can halt it. Rethink whether the objective can be met in staging.");
    }
    var en = enabled();
    add(!en.length, en.length ? "ok" : "bad", "At least one permitted activity",
      en.length ? en.length + " activity type" + (en.length === 1 ? "" : "s") + " authorised." : "The authorisation currently grants nothing. Select only what the client has consciously agreed to.");

    return c;
  }

  function renderChecks() {
    var host = $("k-ready");
    host.innerHTML = "";
    checks().forEach(function (c) {
      var d = document.createElement("div");
      d.className = "chk " + (c.ok ? "ok" : c.level);
      var ic = document.createElement("span");
      ic.className = "ic";
      ic.textContent = c.ok ? "[OK]" : (c.level === "bad" ? "[FIX]" : "[!]");
      var t = document.createElement("span");
      var b = document.createElement("b");
      b.textContent = c.title + " — ";
      t.appendChild(b);
      t.appendChild(document.createTextNode(c.detail));
      d.appendChild(ic); d.appendChild(t);
      host.appendChild(d);
    });
  }

  /* ============================== TABS ==================================== */
  var DOCS = {
    auth: { name: "AUTHORISATION TO TEST", fn: docAuthorisation },
    roe: { name: "RULES OF ENGAGEMENT", fn: docROE },
    scope: { name: "SCOPE & EXCLUSIONS CHECKLIST", fn: docScope },
    abort: { name: "ABORT PROCEDURE / KILL SWITCH", fn: docAbort },
    log: { name: "ENGAGEMENT LOG TEMPLATE", fn: docLog }
  };
  var current = "auth";

  function renderDoc() {
    var d = DOCS[current];
    var text = d.fn();
    $("k-out").value = text;
    $("k-docname").textContent = d.name;
    $("k-docsize").textContent = text.split("\n").length + " lines · " + text.length.toLocaleString("en-IN") + " chars";
    Object.keys(DOCS).forEach(function (k) {
      var t = $("tab-" + k);
      if (t) t.setAttribute("aria-selected", String(k === current));
    });
  }

  function renderAll() {
    renderChecks();
    renderDoc();
  }

  /* ============================ PERMISSION UI ============================= */
  function renderPerms() {
    var host = $("perms");
    host.innerHTML = "";
    PERMS.forEach(function (p) {
      var lab = document.createElement("label");
      lab.className = "perm" + (p.danger ? " danger" : "");
      var cb = document.createElement("input");
      cb.type = "checkbox";
      cb.id = "perm-" + p.id;
      cb.checked = !!p.on;
      cb.addEventListener("change", function () { renderAll(); });
      var t = document.createElement("div");
      t.className = "t";
      var b = document.createElement("b");
      b.textContent = p.n;
      var sp = document.createElement("span");
      sp.textContent = p.d;
      t.appendChild(b); t.appendChild(sp);
      var f = document.createElement("span");
      f.className = "flag" + (p.danger ? " red" : "");
      f.textContent = p.flag;
      lab.appendChild(cb);
      lab.appendChild(t);
      lab.appendChild(f);
      host.appendChild(lab);
    });
  }

  /* ============================== EXPORT ================================== */
  function download(filename, text) {
    var blob = new Blob([text], { type: "text/markdown;charset=utf-8" });
    var a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = filename;
    document.body.appendChild(a); a.click(); document.body.removeChild(a);
    setTimeout(function () { URL.revokeObjectURL(a.href); }, 2000);
  }
  function refSlug() {
    var r = val("k-ref") || val("k-client") || "engagement";
    return r.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "") || "engagement";
  }
  function fullPack() {
    var L = [];
    L.push("# Engagement Kit — " + TBD(val("k-ref")));
    L.push("");
    L.push("**Client:** " + TBD(val("k-client")) + "  ");
    L.push("**Assessor:** " + val("k-assessor") + " — " + val("k-assessororg") + "  ");
    L.push("**Generated:** " + new Date().toISOString() + "  ");
    L.push("**Engagement type:** " + val("k-type") + " · " + val("k-mode") + " · " + val("k-env"));
    L.push("");
    L.push("> Templates for authorised security testing only. **Not legal advice.** Have these reviewed by qualified counsel before signing. Generated locally in the browser; nothing was transmitted.");
    L.push("");
    ["auth", "roe", "scope", "abort", "log"].forEach(function (k) {
      L.push("");
      L.push("---");
      L.push("");
      L.push("## " + DOCS[k].name);
      L.push("");
      L.push("```text");
      L.push(DOCS[k].fn());
      L.push("```");
      L.push("");
    });
    return L.join("\n");
  }

  /* ============================== EVENTS ================================== */
  function bind() {
    var ids = ["k-client", "k-signatory", "k-signemail", "k-assessor", "k-assessororg", "k-ref",
      "k-type", "k-mode", "k-env", "k-window-from", "k-window-to", "k-tz",
      "k-scope", "k-exclude", "k-accounts", "k-tc", "k-tce", "k-ec1", "k-ec2", "k-soc",
      "k-blueknown", "k-data", "k-retention", "k-destroy", "k-report", "k-retest", "k-juris"];
    ids.forEach(function (id) {
      var e = $(id);
      if (!e) return;
      e.addEventListener("input", function () { renderChecks(); });
      e.addEventListener("change", function () { renderChecks(); renderDoc(); });
    });

    Object.keys(DOCS).forEach(function (k) {
      var t = $("tab-" + k);
      if (!t) return;
      t.addEventListener("click", function () { current = k; renderDoc(); });
      t.addEventListener("keydown", function (e) {
        if (e.key === "Enter" || e.key === " ") { e.preventDefault(); current = k; renderDoc(); }
      });
    });

    $("k-build").addEventListener("click", function () { renderAll(); toast("All five documents regenerated"); });
    $("k-copy").addEventListener("click", function () {
      var v = $("k-out").value || DOCS[current].fn();
      $("k-out").value = v;
      var ok = function () { toast("Copied to clipboard"); };
      if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(v).then(ok, function () { $("k-out").select(); ok(); });
      } else { $("k-out").select(); document.execCommand("copy"); ok(); }
    });
    $("k-dl").addEventListener("click", function () {
      download(refSlug() + "-" + current + ".md", "# " + DOCS[current].name + "\n\n```text\n" + DOCS[current].fn() + "\n```\n");
      toast(DOCS[current].name + " downloaded");
    });
    $("k-dlall").addEventListener("click", function () {
      download(refSlug() + "-engagement-pack.md", fullPack());
      toast("Full engagement pack downloaded");
    });
    $("k-print").addEventListener("click", function () {
      $("k-out").value = DOCS[current].fn();
      window.print();
    });
    $("k-reset").addEventListener("click", function () {
      if (!window.confirm("Clear all fields, including the assessor defaults?")) return;
      var keep = { "k-assessor": "Ratan Kumar Patel", "k-assessororg": "RATAN_PATEL.SEC" };
      ids.forEach(function (id) {
        var e = $(id); if (!e) return;
        if (keep[id]) { e.value = keep[id]; return; }
        if (e.tagName === "SELECT") e.selectedIndex = 0;
        else if (e.type === "datetime-local" || e.type === "date") e.value = "";
        else e.value = "";
      });
      PERMS.forEach(function (p) {
        var e = $("perm-" + p.id);
        if (e) e.checked = (p.id === "scan" || p.id === "auth");
      });
      renderAll();
      toast("Form cleared");
    });
  }

  /* =============================== BOOT =================================== */
  renderPerms();
  bind();
  renderAll();
})();
