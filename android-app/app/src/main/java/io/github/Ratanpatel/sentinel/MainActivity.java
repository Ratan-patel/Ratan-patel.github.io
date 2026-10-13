package io.github.Ratanpatel.sentinel;

import android.app.Activity;
import android.content.Intent;
import android.content.SharedPreferences;
import android.graphics.Color;
import android.graphics.Typeface;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.text.InputType;
import android.view.View;
import android.widget.ArrayAdapter;
import android.widget.Button;
import android.widget.CheckBox;
import android.widget.EditText;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.Spinner;
import android.widget.TextView;

import org.json.JSONArray;
import org.json.JSONObject;

import java.io.BufferedReader;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.io.OutputStream;
import java.net.HttpURLConnection;
import java.net.InetSocketAddress;
import java.net.Socket;
import java.net.URL;
import java.nio.charset.StandardCharsets;
import java.security.cert.Certificate;
import java.security.cert.X509Certificate;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Collection;
import java.util.Date;
import java.util.HashSet;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Set;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

import javax.net.ssl.HttpsURLConnection;
import javax.net.ssl.SSLPeerUnverifiedException;
import javax.net.ssl.SSLSocket;
import javax.net.ssl.SSLSocketFactory;

/**
 * Sentinel — authorized security-assessment agent (Android edition).
 *
 * Read-only audits of assets you own or hold written permission to test.
 * The authorization guard in this file mirrors sentinel/sentinel/authz.py:
 * hard prohibitions cannot be overridden by the scope list, every decision is
 * shown on screen, and no tool sends a payload, credential attempt or exploit.
 */
public class MainActivity extends Activity {

    // ------------------------------------------------------------- hard rules
    // Ports never probed: ICS/SCADA, medical, out-of-band mgmt, abuse vectors.
    private static final Set<Integer> PROTECTED_PORTS = new HashSet<>(Arrays.asList(
            21, 23, 25, 53, 102, 123, 161, 162, 389, 465, 502, 587, 623, 636,
            1801, 1900, 2000, 2323, 2404, 3109, 3110, 3389, 4000, 4001, 4002,
            4840, 4843, 5900, 5901, 5902, 7171, 7172, 8291, 9004, 9005, 9100,
            10101, 10102, 10443, 10444, 11111, 11211, 20000, 20001, 44818, 47808,
            50100, 50110, 50200));

    private static final String[] PROTECTED_SUFFIXES = {
            "google.com", "googleapis.com", "amazonaws.com", "microsoft.com",
            "microsoftonline.com", "azure.com", "openai.com", "chatgpt.com",
            "anthropic.com", "claude.ai", "github.com", "gitlab.com",
            "cloudflare.com", "apple.com", "icloud.com", "facebook.com",
            "instagram.com", "twitter.com", "x.com", "linkedin.com",
            "stripe.com", "paypal.com", "netflix.com", "oraclecloud.com",
            "salesforce.com", "okta.com", "auth0.com"};

    private static final String[] PROTECTED_TLDS = {".mil", ".gov", ".int"};

    private static final String[] CRITICAL_FRAGMENTS = {
            "scada", "plc", "substation", "satellite", "satcom", "groundstation",
            "ground-station", "telemetry", "uplink", "downlink", "airtraffic",
            "nuclear", "reactor", "powerplant", "election", "voting-machine",
            "hospital-pacs", "dicom", "rail-signalling", "swiftnet",
            "core-banking", "emergency", "dispatch"};

    private static final String[] SHARED_HOSTING_SUFFIXES = {
            "github.io", "vercel.app", "netlify.app", "pages.dev", "workers.dev",
            "herokuapp.com", "onrender.com", "firebaseapp.com", "web.app"};

    private static final int[] DEFAULT_PORTS = {
            22, 80, 443, 3000, 3306, 5432, 6379, 8000, 8080, 8443, 8888, 9090,
            9200, 27017};

    // ------------------------------------------------------------------- UI
    private EditText scopeInput, targetInput, baseUrlInput, modelInput, keyInput, askInput;
    private Spinner toolSpinner;
    private CheckBox ownCheck, activeCheck;
    private TextView outputView;
    private Button runButton;
    private final ExecutorService executor = Executors.newSingleThreadExecutor();
    private final Handler mainHandler = new Handler(Looper.getMainLooper());
    private String lastReport = "";
    private SharedPreferences prefs;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        prefs = getSharedPreferences("sentinel", MODE_PRIVATE);
        buildUi();
        log("Sentinel ready.\nSirf wahi assets daalo jo tumhare apne hain, ya jinke liye tumhare paas written permission hai. Baaki sab refuse hoga.\n");
    }

    private EditText field(String hint, boolean password) {
        EditText e = new EditText(this);
        e.setHint(hint);
        e.setTextColor(Color.rgb(230, 237, 243));
        e.setHintTextColor(Color.rgb(120, 130, 140));
        e.setTextSize(14);
        if (password) {
            e.setInputType(InputType.TYPE_CLASS_TEXT | InputType.TYPE_TEXT_VARIATION_PASSWORD);
        }
        return e;
    }

    private TextView label(String text) {
        TextView t = new TextView(this);
        t.setText(text);
        t.setTextColor(Color.rgb(88, 214, 141));
        t.setTextSize(13);
        t.setTypeface(Typeface.DEFAULT_BOLD);
        t.setPadding(0, 18, 0, 4);
        return t;
    }

    private void buildUi() {
        ScrollView scroll = new ScrollView(this);
        scroll.setBackgroundColor(Color.rgb(13, 17, 23));
        LinearLayout root = new LinearLayout(this);
        root.setOrientation(LinearLayout.VERTICAL);
        root.setPadding(32, 32, 32, 32);
        scroll.addView(root);

        TextView title = new TextView(this);
        title.setText("🛡 SENTINEL");
        title.setTextColor(Color.rgb(88, 214, 141));
        title.setTextSize(24);
        title.setTypeface(Typeface.DEFAULT_BOLD);
        root.addView(title);

        TextView sub = new TextView(this);
        sub.setText("Authorized security assessment • read-only • scope-enforced");
        sub.setTextColor(Color.rgb(160, 170, 180));
        sub.setTextSize(12);
        root.addView(sub);

        root.addView(label("1) SCOPE — mere apne / authorized assets (ek line mein ek)"));
        scopeInput = field("e.g.\nmy-app.example.com\n10.0.0.5\n192.168.1.0/24", false);
        scopeInput.setMinLines(3);
        scopeInput.setText(prefs.getString("scope", "127.0.0.1\nlocalhost"));
        root.addView(scopeInput);

        ownCheck = new CheckBox(this);
        ownCheck.setText("Ye assets mere apne hain / mere paas written permission hai");
        ownCheck.setTextColor(Color.rgb(230, 237, 243));
        root.addView(ownCheck);

        root.addView(label("2) TARGET"));
        targetInput = field("https://my-app.example.com  ya  192.168.1.10", false);
        targetInput.setText(prefs.getString("target", ""));
        root.addView(targetInput);

        root.addView(label("3) TOOL"));
        toolSpinner = new Spinner(this);
        String[] tools = {"HTTP Headers Audit", "TLS / Certificate Audit",
                "Port Discovery (connect-only)", "Ask AI (model se poochho)"};
        ArrayAdapter<String> adapter = new ArrayAdapter<>(this,
                android.R.layout.simple_spinner_dropdown_item, tools);
        toolSpinner.setAdapter(adapter);
        root.addView(toolSpinner);

        activeCheck = new CheckBox(this);
        activeCheck.setText("Active probing allow karo (sirf Port Discovery ke liye)");
        activeCheck.setTextColor(Color.rgb(230, 237, 243));
        root.addView(activeCheck);

        root.addView(label("4) MODEL / PRIVATE API (sirf 'Ask AI' ke liye)"));
        baseUrlInput = field("Base URL — e.g. https://api.openai.com/v1  ya  http://127.0.0.1:11434/v1", false);
        baseUrlInput.setText(prefs.getString("baseUrl", ""));
        root.addView(baseUrlInput);
        modelInput = field("Model — e.g. gpt-4o-mini / llama3.1", false);
        modelInput.setText(prefs.getString("model", ""));
        root.addView(modelInput);
        keyInput = field("API Key (phone par hi rehta hai, kahin upload nahi hota)", true);
        keyInput.setText(prefs.getString("apiKey", ""));
        root.addView(keyInput);

        root.addView(label("5) SAWAL (sirf 'Ask AI' ke liye)"));
        askInput = field("e.g. is site ki security posture kaisi hai?", false);
        askInput.setText("Is target ki security posture ka short assessment do. Findings ko severity ke hisaab se batao.");
        root.addView(askInput);

        runButton = new Button(this);
        runButton.setText("▶  RUN");
        runButton.setOnClickListener(v -> onRun());
        root.addView(runButton);

        Button shareButton = new Button(this);
        shareButton.setText("Share / Copy Report");
        shareButton.setOnClickListener(v -> {
            if (lastReport.isEmpty()) { log("\nPehle kuch run karo.\n"); return; }
            Intent send = new Intent(Intent.ACTION_SEND);
            send.setType("text/plain");
            send.putExtra(Intent.EXTRA_TEXT, lastReport);
            startActivity(Intent.createChooser(send, "Report share karo"));
        });
        root.addView(shareButton);

        root.addView(label("OUTPUT / REPORT"));
        outputView = new TextView(this);
        outputView.setTextColor(Color.rgb(220, 228, 235));
        outputView.setTextSize(12.5f);
        outputView.setTypeface(Typeface.MONOSPACE);
        outputView.setTextIsSelectable(true);
        root.addView(outputView);

        setContentView(scroll);
    }

    // ------------------------------------------------------------ guard logic

    private void savePrefs() {
        prefs.edit()
                .putString("scope", scopeInput.getText().toString())
                .putString("target", targetInput.getText().toString())
                .putString("baseUrl", baseUrlInput.getText().toString())
                .putString("model", modelInput.getText().toString())
                .putString("apiKey", keyInput.getText().toString())
                .apply();
    }

    /** Returns a refusal reason, or null if the hard prohibitions do not fire. */
    private String prohibited(String host, Integer port, boolean active) {
        if (port != null && PROTECTED_PORTS.contains(port)) {
            return "port " + port + " ICS/SCADA/medical/management protocol hai — Sentinel use kabhi probe nahi karta.";
        }
        String h = host.toLowerCase(Locale.US);
        for (String suffix : PROTECTED_SUFFIXES) {
            if (h.equals(suffix) || h.endsWith("." + suffix)) {
                return "'" + suffix + "' third-party public infrastructure hai. Isko scan karne ke liye provider ki apni written permission ya unka bug-bounty/VDP program chahiye — khud ka scope note kaafi nahi hai.";
            }
        }
        for (String tld : PROTECTED_TLDS) {
            if (h.endsWith(tld) || h.contains(tld + ".")) {
                return "yeh military/government domain hai. Us organisation ke published VDP/bug-bounty program se jao.";
            }
        }
        for (String frag : CRITICAL_FRAGMENTS) {
            if (h.contains(frag)) {
                return "target critical infrastructure jaisa lagta hai ('" + frag + "'). Sentinel is class ke system ko kabhi probe nahi karta.";
            }
        }
        if (active) {
            for (String suffix : SHARED_HOSTING_SUFFIXES) {
                if (h.equals(suffix) || h.endsWith("." + suffix)) {
                    return "yeh shared hosting hai (" + suffix + "). Tumhare apne subdomain ka passive audit theek hai, lekin port probing us platform ki machine par hogi — isliye refused.";
                }
            }
        }
        return null;
    }

    private List<String> scopeEntries() {
        List<String> out = new ArrayList<>();
        for (String line : scopeInput.getText().toString().split("\\n")) {
            String s = line.trim().toLowerCase(Locale.US);
            if (!s.isEmpty()) out.add(s);
        }
        return out;
    }

    private boolean inScope(String host) {
        String h = host.toLowerCase(Locale.US);
        for (String entry : scopeEntries()) {
            String e = entry.replaceFirst("^https?://", "").split("/")[0].split(":")[0];
            if (e.contains("/")) { // CIDR
                if (cidrContains(e, h)) return true;
                continue;
            }
            if (h.equals(e) || h.endsWith("." + e)) return true;
        }
        return false;
    }

    private boolean cidrContains(String cidr, String ip) {
        try {
            String[] parts = cidr.split("/");
            String[] a = parts[0].split("\\."), b = ip.split("\\.");
            if (a.length != 4 || b.length != 4) return false;
            int prefix = Integer.parseInt(parts[1]);
            long ipA = 0, ipB = 0;
            for (int i = 0; i < 4; i++) {
                ipA = (ipA << 8) + Integer.parseInt(a[i]);
                ipB = (ipB << 8) + Integer.parseInt(b[i]);
            }
            long mask = prefix == 0 ? 0 : (0xFFFFFFFFL << (32 - prefix)) & 0xFFFFFFFFL;
            return (ipA & mask) == (ipB & mask);
        } catch (Exception e) {
            return false;
        }
    }

    /** Full check: returns null if allowed, else the on-screen refusal text. */
    private String guard(String target, Integer port, boolean active) {
        String host = hostOf(target);
        if (host == null || host.isEmpty()) return "Target samajh nahi aaya. URL ya hostname/IP daalo.";
        String hard = prohibited(host, port, active);
        if (hard != null) return hard;
        if (!ownCheck.isChecked()) {
            return "Pehle checkbox tick karo: ye asset mera apna hai / mere paas written permission hai. Bina authorization ke koi scan nahi hoga.";
        }
        if (!inScope(host)) {
            return "'" + host + "' tumhare scope mein nahi hai. Agar ye tumhara asset hai to use SCOPE list mein add karo; agar nahi hai, to use touch hi mat karo.";
        }
        return null;
    }

    private static String hostOf(String target) {
        try {
            String t = target.trim();
            if (!t.contains("://")) t = "https://" + t;
            String host = new URL(t).getHost();
            return host == null ? null : host.toLowerCase(Locale.US);
        } catch (Exception e) {
            return null;
        }
    }

    // -------------------------------------------------------------------- run

    private void onRun() {
        savePrefs();
        String target = targetInput.getText().toString().trim();
        int tool = toolSpinner.getSelectedItemPosition();
        boolean activeTool = tool == 2;
        setBusy(true);
        outputView.setText("");

        String refusal = guard(target, null, activeTool);
        if (activeTool && !activeCheck.isChecked() && refusal == null) {
            refusal = "Port Discovery ek active-probe tool hai. Pehle 'Active probing allow karo' tick karo, aur confirm karo ki target tumhara hai aur active scanning allowed hai.";
        }
        if (refusal != null) {
            log("⛔ REFUSED: " + refusal + "\n\nKuch probe nahi hua. Koi request nahi bheji gayi.\n");
            lastReport = outputView.getText().toString();
            setBusy(false);
            return;
        }

        log("Target: " + target + "\nScope check: ✅ in scope, authorization confirmed\n\n");
        executor.execute(() -> {
            String result;
            try {
                switch (tool) {
                    case 0: result = httpAudit(target); break;
                    case 1: result = tlsAudit(target); break;
                    case 2: result = portDiscovery(target); break;
                    default: result = askAi(target); break;
                }
            } catch (Exception e) {
                result = "Error: " + e.getClass().getSimpleName() + ": " + e.getMessage();
            }
            final String done = result;
            mainHandler.post(() -> {
                log(done);
                lastReport = outputView.getText().toString();
                setBusy(false);
            });
        });
    }

    private void setBusy(boolean busy) {
        runButton.setEnabled(!busy);
        runButton.setText(busy ? "Running…" : "▶  RUN");
    }

    private void log(String text) {
        outputView.append(text);
    }

    // ------------------------------------------------------------------ tools

    private String httpAudit(String target) throws Exception {
        String url = target.trim();
        if (!url.contains("://")) url = "https://" + url;
        HttpURLConnection conn = (HttpURLConnection) new URL(url).openConnection();
        conn.setRequestMethod("GET");
        conn.setInstanceFollowRedirects(false);
        conn.setConnectTimeout(12000);
        conn.setReadTimeout(12000);
        conn.setRequestProperty("User-Agent", "sentinel-audit/1.0 (authorized-security-assessment)");
        int status = conn.getResponseCode();
        Map<String, List<String>> headers = conn.getHeaderFields();

        StringBuilder sb = new StringBuilder();
        sb.append("HTTP AUDIT — ").append(url).append("\nStatus: ").append(status).append("\n");
        List<String> findings = new ArrayList<>();

        if ("http".equals(new URL(url).getProtocol())) {
            findings.add("[CRITICAL] Site plain HTTP par hai — sab kuch cleartext mein travel karta hai. HTTPS only + HSTS lagao.");
        }
        checkHeader(headers, "strict-transport-security", "[HIGH] HSTS missing — pehli request downgrade ho sakti hai. Fix: Strict-Transport-Security: max-age=31536000; includeSubDomains", findings, true);
        checkHeader(headers, "content-security-policy", "[HIGH] CSP missing — injected script ko browser-side rok nahi hai. Fix: Content-Security-Policy: default-src 'self'", findings, false);
        checkHeader(headers, "x-content-type-options", "[MEDIUM] X-Content-Type-Options missing. Fix: nosniff", findings, false);
        checkHeader(headers, "x-frame-options", "[MEDIUM] X-Frame-Options / CSP frame-ancestors missing — clickjacking possible.", findings, false);
        checkHeader(headers, "referrer-policy", "[LOW] Referrer-Policy missing — URLs (tokens ke saath) leak ho sakte hain.", findings, false);
        checkHeader(headers, "permissions-policy", "[LOW] Permissions-Policy missing — camera/mic/location restrict nahi hain.", findings, false);

        List<String> cookies = headerValues(headers, "set-cookie");
        for (String cookie : cookies) {
            String lower = cookie.toLowerCase(Locale.US);
            String name = cookie.split("=", 2)[0];
            if (!lower.contains("secure;") && !lower.endsWith("secure")) findings.add("[HIGH] Cookie '" + name + "' par Secure flag nahi hai.");
            if (!lower.contains("httponly")) findings.add("[MEDIUM] Cookie '" + name + "' par HttpOnly nahi hai — JS use padh sakta hai.");
            if (!lower.contains("samesite")) findings.add("[MEDIUM] Cookie '" + name + "' par SameSite nahi hai — CSRF risk.");
        }

        String server = firstHeader(headers, "server");
        String powered = firstHeader(headers, "x-powered-by");
        if (server != null || powered != null) {
            findings.add("[LOW] Version disclose ho raha hai: Server=" + server + " X-Powered-By=" + powered + " — proxy par strip karo.");
        }
        String acao = firstHeader(headers, "access-control-allow-origin");
        String acac = firstHeader(headers, "access-control-allow-credentials");
        if ("*".equals(acao) && "true".equalsIgnoreCase(acac)) {
            findings.add("[CRITICAL] CORS wildcard (*) credentials ke saath — origin allowlist use karo, kabhi reflect mat karo.");
        }

        int score = headerScore(headers);
        sb.append("Header score: ").append(score).append("/100\n\n");
        if (findings.isEmpty()) {
            sb.append("✅ Koi finding nahi. Posture achha hai.\n");
        } else {
            sb.append("FINDINGS (").append(findings.size()).append("):\n");
            for (String f : findings) sb.append("• ").append(f).append("\n");
        }
        sb.append("\n( sirf GET request gayi — koi form submit nahi hua, koi payload nahi gaya.)\n");
        conn.disconnect();
        return sb.toString();
    }

    private void checkHeader(Map<String, List<String>> headers, String name,
                             String finding, List<String> findings, boolean httpsOnly) {
        if (headerValues(headers, name).isEmpty()) findings.add(finding);
    }

    private int headerScore(Map<String, List<String>> headers) {
        Map<String, Integer> weights = new LinkedHashMap<>();
        weights.put("strict-transport-security", 25);
        weights.put("content-security-policy", 25);
        weights.put("x-content-type-options", 12);
        weights.put("x-frame-options", 12);
        weights.put("referrer-policy", 6);
        weights.put("permissions-policy", 6);
        weights.put("cross-origin-opener-policy", 6);
        weights.put("cross-origin-resource-policy", 2);
        String csp = firstHeader(headers, "content-security-policy");
        int total = 0, got = 0;
        for (Map.Entry<String, Integer> e : weights.entrySet()) {
            total += e.getValue();
            boolean present = !headerValues(headers, e.getKey()).isEmpty();
            if (!present && e.getKey().equals("x-frame-options") && csp != null
                    && csp.toLowerCase(Locale.US).contains("frame-ancestors")) present = true;
            if (present) got += e.getValue();
        }
        return total == 0 ? 0 : Math.round(100f * got / total);
    }

    private List<String> headerValues(Map<String, List<String>> headers, String name) {
        List<String> out = new ArrayList<>();
        for (Map.Entry<String, List<String>> e : headers.entrySet()) {
            if (e.getKey() != null && e.getKey().equalsIgnoreCase(name) && e.getValue() != null) {
                out.addAll(e.getValue());
            }
        }
        return out;
    }

    private String firstHeader(Map<String, List<String>> headers, String name) {
        List<String> v = headerValues(headers, name);
        return v.isEmpty() ? null : v.get(0);
    }

    private String tlsAudit(String target) throws Exception {
        String host = hostOf(target);
        int port = 443;
        SSLSocketFactory factory = (SSLSocketFactory) SSLSocketFactory.getDefault();
        StringBuilder sb = new StringBuilder();
        sb.append("TLS AUDIT — ").append(host).append(":").append(port).append("\n");
        try (SSLSocket socket = (SSLSocket) factory.createSocket()) {
            socket.connect(new InetSocketAddress(host, port), 12000);
            socket.setSoTimeout(12000);
            socket.startHandshake();
            sb.append("Protocol: ").append(socket.getSession().getProtocol()).append("\n");
            sb.append("Cipher: ").append(socket.getSession().getCipherSuite()).append("\n\n");
            Certificate[] chain = socket.getSession().getPeerCertificates();
            X509Certificate leaf = (X509Certificate) chain[0];
            Date now = new Date();
            long days = (leaf.getNotAfter().getTime() - now.getTime()) / 86400000L;
            sb.append("Subject: ").append(leaf.getSubjectX500Principal().getName()).append("\n");
            sb.append("Issuer: ").append(leaf.getIssuerX500Principal().getName()).append("\n");
            sb.append("Valid till: ").append(leaf.getNotAfter()).append(" (").append(days).append(" din bache)\n");
            List<String> findings = new ArrayList<>();
            String proto = socket.getSession().getProtocol();
            if (proto.equals("TLSv1") || proto.equals("TLSv1.1") || proto.equals("SSLv3")) {
                findings.add("[CRITICAL] Deprecated protocol negotiated: " + proto + " — sirf TLS 1.2/1.3 rakho (RFC 8996).");
            }
            if (days < 0) findings.add("[CRITICAL] Certificate EXPIRE ho chuka hai.");
            else if (days <= 14) findings.add("[HIGH] Certificate " + days + " din mein expire hoga — abhi renew karo, ACME automate karo.");
            else if (days <= 30) findings.add("[MEDIUM] Certificate " + days + " din mein expire hoga.");
            try {
                Collection<List<?>> sans = leaf.getSubjectAlternativeNames();
                boolean covers = false;
                List<String> names = new ArrayList<>();
                if (sans != null) {
                    for (List<?> san : sans) {
                        if (san.size() >= 2 && Integer.valueOf(7).equals(san.get(0)) == false) {
                            String n = String.valueOf(san.get(1)).toLowerCase(Locale.US);
                            names.add(n);
                            if (n.equals(host) || (n.startsWith("*.") && host.endsWith(n.substring(1))
                                    && host.split("\\.").length == n.split("\\.").length)) covers = true;
                        }
                    }
                }
                sb.append("SANs: ").append(names).append("\n");
                if (sans == null) findings.add("[HIGH] Certificate mein SAN nahi hai — browsers reject karenge.");
                else if (!covers) findings.add("[HIGH] Hostname certificate SANs mein cover nahi hota.");
            } catch (Exception ignored) { }
            sb.append("\n");
            if (findings.isEmpty()) sb.append("✅ Koi finding nahi.\n");
            else for (String f : findings) sb.append("• ").append(f).append("\n");
        } catch (SSLPeerUnverifiedException e) {
            sb.append("❌ Certificate verify nahi hua: ").append(e.getMessage()).append("\n");
        }
        sb.append("\n( sirf TLS handshake hua — koi application request nahi gayi.)\n");
        return sb.toString();
    }

    private String portDiscovery(String target) {
        String host = hostOf(target);
        StringBuilder sb = new StringBuilder();
        sb.append("PORT DISCOVERY — ").append(host).append(" (connect-only, koi banner/payload nahi)\n\n");
        List<String> open = new ArrayList<>();
        List<Integer> refusedProtected = new ArrayList<>();
        for (int port : DEFAULT_PORTS) {
            if (PROTECTED_PORTS.contains(port)) { refusedProtected.add(port); continue; }
            String hard = prohibited(host, port, true);
            if (hard != null) continue;
            try (Socket socket = new Socket()) {
                socket.connect(new InetSocketAddress(host, port), 900);
                open.add(port + " (" + serviceName(port) + ")");
            } catch (Exception ignored) { /* closed/filtered */ }
            try { Thread.sleep(120); } catch (InterruptedException ignored) { }
        }
        if (open.isEmpty()) sb.append("Koi common port open nahi mila.\n");
        else {
            sb.append("Open ports:\n");
            for (String o : open) sb.append("• ").append(o).append("\n");
        }
        sb.append("\nNote: database/cache ports (3306, 5432, 6379, 9200, 27017) agar public par open hain to turant firewall/bind-address theek karo — ye internal services hain.\n");
        return sb.toString();
    }

    private String serviceName(int port) {
        switch (port) {
            case 22: return "ssh"; case 80: return "http"; case 443: return "https";
            case 3000: return "dev-server"; case 3306: return "mysql";
            case 5432: return "postgresql"; case 6379: return "redis";
            case 8000: return "http-alt"; case 8080: return "http-proxy";
            case 8443: return "https-alt"; case 8888: return "http-alt";
            case 9090: return "prometheus"; case 9200: return "elasticsearch";
            case 27017: return "mongodb"; default: return "";
        }
    }

    private String askAi(String target) throws Exception {
        String base = baseUrlInput.getText().toString().trim();
        String model = modelInput.getText().toString().trim();
        String key = keyInput.getText().toString().trim();
        if (base.isEmpty() || model.isEmpty()) {
            return "Model configured nahi hai.\nSection 4 mein Base URL aur Model daalo.\n\nExamples:\n• https://api.openai.com/v1  +  gpt-4o-mini\n• http://127.0.0.1:11434/v1  +  llama3.1  (Ollama, apne network par)\n• Tumhara private gateway URL + uska model id\n\nKey environment jaisa hi treat hota hai — sirf is phone par save hota hai.";
        }
        String endpoint = base.endsWith("/chat/completions") ? base
                : (base.endsWith("/v1") ? base + "/chat/completions" : base + "/v1/chat/completions");

        // Pehle khud audit chalao, phir model ko wahi data do — model guess nahi karega.
        String audit = "";
        try { audit = httpAudit(target); } catch (Exception e) { audit = "(HTTP audit nahi ho paya: " + e.getMessage() + ")"; }

        JSONObject payload = new JSONObject();
        payload.put("model", model);
        payload.put("temperature", 0.2);
        JSONArray messages = new JSONArray();
        messages.put(new JSONObject().put("role", "system").put("content",
                "You are Sentinel, a defensive security assessment agent. Tum sirf usi data par bolo jo tool ne diya hai. Kabhi findings invent mat karo. Hindi/Hinglish mein short, prioritized jawab do. Agar koi target scope se bahar ya kisi aur ka system ho, to mana kar do."));
        messages.put(new JSONObject().put("role", "user").put("content",
                "Target: " + target + "\n\nTool ka actual result:\n" + audit + "\n\nSawal: " + askInput.getText().toString()));
        payload.put("messages", messages);

        HttpURLConnection conn = (HttpURLConnection) new URL(endpoint).openConnection();
        conn.setRequestMethod("POST");
        conn.setDoOutput(true);
        conn.setConnectTimeout(20000);
        conn.setReadTimeout(60000);
        conn.setRequestProperty("Content-Type", "application/json");
        if (!key.isEmpty()) conn.setRequestProperty("Authorization", "Bearer " + key);
        try (OutputStream os = conn.getOutputStream()) {
            os.write(payload.toString().getBytes(StandardCharsets.UTF_8));
        }
        int status = conn.getResponseCode();
        InputStream stream = status >= 400 ? conn.getErrorStream() : conn.getInputStream();
        StringBuilder body = new StringBuilder();
        try (BufferedReader reader = new BufferedReader(new InputStreamReader(stream, StandardCharsets.UTF_8))) {
            String line;
            while ((line = reader.readLine()) != null) body.append(line);
        }
        if (status >= 400) return "Model API error (HTTP " + status + "):\n" + body.substring(0, Math.min(500, body.length()));
        JSONObject response = new JSONObject(body.toString());
        String text = response.getJSONArray("choices").getJSONObject(0)
                .getJSONObject("message").optString("content", "(khaali jawab)");
        return "MODEL: " + model + "\n\n" + text + "\n\n---\n" + audit;
    }
}
