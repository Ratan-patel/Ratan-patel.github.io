package io.github.ratanpatel.ratanagent;

import android.content.Context;
import android.content.pm.PackageManager;
import android.os.Build;

import org.json.JSONObject;

import java.io.ByteArrayOutputStream;
import java.io.InputStream;
import java.net.HttpURLConnection;
import java.net.URL;
import java.util.Arrays;
import java.util.HashSet;
import java.util.Iterator;
import java.util.List;
import java.util.Locale;
import java.util.Set;
import java.util.zip.GZIPInputStream;

/**
 * The shell's HTTP client.
 *
 * Why not let JavaScript do the fetching? Because a browser page cannot reach a lab bot on
 * plain http://192.168.x.x (CORS + cleartext rules), and a pentest tool that cannot reach the
 * target is decoration. Doing it natively also buys: per-hop policy checks, response caps,
 * gzip, manual redirect control, and a structured result the UI can reason about.
 *
 * The JSON contract is intentionally identical to the AIRT scanner app so the bundled
 * toolkit page runs unmodified.
 */
public final class HttpEngine {

    /** Declared as a literal so the file still compiles on SDKs that predate the constant. */
    public static final String PERM_LOCAL_NETWORK = "android.permission.ACCESS_LOCAL_NETWORK";
    /** Android 17 (API 37) — first release where the local-network permission is enforced. */
    public static final int LOCAL_NETWORK_PERMISSION_SDK = 37;

    private static final Set<String> ALLOWED_METHODS = new HashSet<>(Arrays.asList(
            "GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"));

    /** Headers we refuse to forward: they either break the connection or enable smuggling. */
    private static final Set<String> BLOCKED_HEADERS = new HashSet<>(Arrays.asList(
            "host", "content-length", "connection", "transfer-encoding", "upgrade",
            "accept-encoding", "proxy-authorization"));

    private static final int MAX_REDIRECTS = 5;
    private static final int MAX_HEADER_COUNT = 40;
    private static final int MAX_BODY_CHARS = 4 * 1024 * 1024;

    public static final class Result {
        public int status;
        public String body = "";
        public long ms;
        public String error;
        public boolean retryable;
        public boolean blocked;
        public boolean truncated;
        public int hops;
        public String finalUrl = "";

        public String toJson() {
            JSONObject json = new JSONObject();
            try {
                json.put("status", status);
                json.put("body", body);
                json.put("ms", ms);
                json.put("error", error == null ? JSONObject.NULL : error);
                json.put("retryable", retryable);
                json.put("blocked", blocked);
                json.put("truncated", truncated);
                json.put("hops", hops);
                json.put("url", finalUrl);
                json.put("bytes", body.getBytes(java.nio.charset.StandardCharsets.UTF_8).length);
            } catch (Exception ignored) {
                // primitives and strings only
            }
            return json.toString();
        }
    }

    private HttpEngine() {
    }

    public static Result execute(Context context, Prefs prefs, String method, String url,
                                 String headersJson, String body) {
        Result result = new Result();
        long started = System.currentTimeMillis();
        HttpURLConnection conn = null;
        try {
            String verb = (method == null || method.trim().isEmpty())
                    ? "POST" : method.trim().toUpperCase(Locale.US);
            if (!ALLOWED_METHODS.contains(verb)) {
                return blocked(result, started, "method " + verb + " is not allowed");
            }
            if (url == null || url.trim().isEmpty()) {
                return blocked(result, started, "empty target URL");
            }
            if (body != null && body.length() > MAX_BODY_CHARS) {
                return blocked(result, started, "request body too large (" + body.length() + " chars)");
            }

            URL target = new URL(url.trim());
            String currentHeaders = headersJson;
            String currentBody = body;

            for (int hop = 0; hop <= MAX_REDIRECTS; hop++) {
                String verdict = policyViolation(context, prefs, target.getProtocol(), target.getHost());
                if (verdict != null) {
                    return blocked(result, started, verdict);
                }
                result.hops = hop;
                result.finalUrl = target.toString();

                conn = (HttpURLConnection) target.openConnection();
                conn.setInstanceFollowRedirects(false);
                conn.setRequestMethod(verb);
                conn.setConnectTimeout(prefs.connectTimeoutMs());
                conn.setReadTimeout(prefs.readTimeoutMs());
                conn.setUseCaches(false);
                conn.setRequestProperty("Accept", "application/json, text/plain, */*");
                conn.setRequestProperty("Accept-Encoding", "gzip");
                conn.setRequestProperty("User-Agent", "RatanAgent/" + BuildConfig.VERSION_NAME
                        + " (Android " + Build.VERSION.RELEASE + "; authorised-testing)");
                if (currentHeaders != null && !currentHeaders.isEmpty()) {
                    applyHeaders(conn, currentHeaders);
                }
                boolean hasBody = currentBody != null && !currentBody.isEmpty()
                        && !"GET".equals(verb) && !"HEAD".equals(verb);
                if (hasBody) {
                    conn.setDoOutput(true);
                    if (conn.getRequestProperty("Content-Type") == null) {
                        conn.setRequestProperty("Content-Type", "application/json");
                    }
                    byte[] payload = currentBody.getBytes(java.nio.charset.StandardCharsets.UTF_8);
                    conn.setFixedLengthStreamingMode(payload.length);
                    try (java.io.OutputStream os = conn.getOutputStream()) {
                        os.write(payload);
                    }
                }

                int status = conn.getResponseCode();
                result.status = status;

                if (isRedirect(status)) {
                    String location = conn.getHeaderField("Location");
                    conn.disconnect();
                    conn = null;
                    if (location == null || location.isEmpty()) {
                        result.error = "redirect without Location header";
                        result.retryable = false;
                        result.ms = System.currentTimeMillis() - started;
                        return result;
                    }
                    URL next = new URL(target, location);
                    // never leak credentials across hosts on a redirect
                    if (!sameHost(target, next)) {
                        currentHeaders = stripSecretHeaders(currentHeaders);
                    }
                    if ("POST".equals(verb) && (status == 301 || status == 302 || status == 303)) {
                        currentBody = "";
                    }
                    if (target.getProtocol().equals("https") && next.getProtocol().equals("http")) {
                        return blocked(result, started,
                                "refusing https -> http downgrade to " + next.getHost());
                    }
                    target = next;
                    continue;
                }

                readBody(conn, prefs, result);
                result.ms = System.currentTimeMillis() - started;
                result.retryable = status == 408 || status == 429 || status >= 500;
                return result;
            }
            result.error = "too many redirects (>" + MAX_REDIRECTS + ")";
            result.retryable = false;
            result.ms = System.currentTimeMillis() - started;
            return result;

        } catch (java.net.SocketTimeoutException exc) {
            result.status = 0;
            result.error = "timeout: " + exc.getMessage();
            result.retryable = true;
            result.ms = System.currentTimeMillis() - started;
            return result;
        } catch (java.net.UnknownHostException exc) {
            result.status = 0;
            result.error = "unknown host: " + exc.getMessage();
            result.retryable = true;
            result.ms = System.currentTimeMillis() - started;
            return result;
        } catch (javax.net.ssl.SSLException exc) {
            result.status = 0;
            result.error = "TLS failure: " + exc.getMessage();
            result.retryable = false;
            result.ms = System.currentTimeMillis() - started;
            return result;
        } catch (Exception exc) {
            result.status = 0;
            result.error = exc.getClass().getSimpleName() + ": " + exc.getMessage();
            result.retryable = true;
            result.ms = System.currentTimeMillis() - started;
            return result;
        } finally {
            if (conn != null) {
                conn.disconnect();
            }
        }
    }

    // ------------------------------------------------------------------ internals

    private static Result blocked(Result result, long started, String reason) {
        result.status = 0;
        result.body = "";
        result.error = reason;
        result.blocked = true;
        result.retryable = false;
        result.ms = System.currentTimeMillis() - started;
        return result;
    }

    /** Returns null when the request may proceed, otherwise the reason it may not. */
    public static String policyViolation(Context context, Prefs prefs, String scheme, String host) {
        String lower = scheme == null ? "" : scheme.toLowerCase(Locale.US);
        if (!"http".equals(lower) && !"https".equals(lower)) {
            return "blocked scheme: " + scheme;
        }
        boolean local = NetPolicy.isPrivateHost(host);
        if (local && needsLocalNetworkPermission(context)) {
            return "local-network-permission-required";
        }
        if ("http".equals(lower)) {
            if (local && !prefs.allowLanHttp()) {
                return "cleartext http to " + host + " is disabled in settings";
            }
            if (!local && !prefs.allowPublicHttp()) {
                return "cleartext http to a public host is disabled in settings";
            }
        }
        return null;
    }

    /** True only on Android 17+ when the runtime permission has not been granted yet. */
    public static boolean needsLocalNetworkPermission(Context context) {
        if (Build.VERSION.SDK_INT < LOCAL_NETWORK_PERMISSION_SDK) {
            return false;
        }
        return context.checkSelfPermission(PERM_LOCAL_NETWORK) != PackageManager.PERMISSION_GRANTED;
    }

    private static void applyHeaders(HttpURLConnection conn, String headersJson) {
        JSONObject headers;
        try {
            headers = new JSONObject(headersJson);
        } catch (Exception exc) {
            return;
        }
        int count = 0;
        for (Iterator<String> it = headers.keys(); it.hasNext() && count < MAX_HEADER_COUNT; ) {
            String key = it.next();
            count++;
            if (key == null || key.isEmpty()) {
                continue;
            }
            String lowered = key.toLowerCase(Locale.US).trim();
            if (BLOCKED_HEADERS.contains(lowered)) {
                continue;
            }
            String value;
            try {
                value = headers.get(key).toString();
            } catch (Exception exc) {
                continue;
            }
            if (value == null) {
                continue;
            }
            // header injection guard
            if (value.indexOf('\n') >= 0 || value.indexOf('\r') >= 0) {
                continue;
            }
            try {
                conn.setRequestProperty(key.trim(), value);
            } catch (Exception ignored) {
                // some headers are restricted by the platform; skipping is safe
            }
        }
    }

    private static void readBody(HttpURLConnection conn, Prefs prefs, Result result) throws Exception {
        int status = conn.getResponseCode();
        InputStream stream = (status >= 400) ? conn.getErrorStream() : conn.getInputStream();
        if (stream == null) {
            result.body = "";
            return;
        }
        String encoding = conn.getContentEncoding();
        if (encoding != null && encoding.toLowerCase(Locale.US).contains("gzip")) {
            stream = new GZIPInputStream(stream);
        }
        int cap = prefs.maxResponseKb() * 1024;
        ByteArrayOutputStream buffer = new ByteArrayOutputStream(Math.min(cap, 64 * 1024));
        byte[] chunk = new byte[8192];
        int total = 0;
        int read;
        while ((read = stream.read(chunk)) != -1) {
            if (total + read > cap) {
                buffer.write(chunk, 0, Math.max(0, cap - total));
                total = cap;
                result.truncated = true;
                break;
            }
            buffer.write(chunk, 0, read);
            total += read;
        }
        stream.close();
        result.body = new String(buffer.toByteArray(), java.nio.charset.StandardCharsets.UTF_8);
        if (result.truncated) {
            result.error = "response truncated at " + prefs.maxResponseKb() + " KB (raise the cap in settings)";
        }
    }

    private static boolean isRedirect(int status) {
        return status == 301 || status == 302 || status == 303 || status == 307 || status == 308;
    }

    private static boolean sameHost(URL a, URL b) {
        String ha = a.getHost() == null ? "" : a.getHost().toLowerCase(Locale.US);
        String hb = b.getHost() == null ? "" : b.getHost().toLowerCase(Locale.US);
        return ha.equals(hb);
    }

    private static final List<String> SECRET_HEADERS = Arrays.asList(
            "authorization", "cookie", "x-api-key", "api-key", "x-auth-token", "proxy-authorization");

    private static String stripSecretHeaders(String headersJson) {
        if (headersJson == null || headersJson.isEmpty()) {
            return headersJson;
        }
        try {
            JSONObject original = new JSONObject(headersJson);
            JSONObject cleaned = new JSONObject();
            for (Iterator<String> it = original.keys(); it.hasNext(); ) {
                String key = it.next();
                if (SECRET_HEADERS.contains(key.toLowerCase(Locale.US).trim())) {
                    continue;
                }
                cleaned.put(key, original.get(key));
            }
            return cleaned.toString();
        } catch (Exception exc) {
            return "{}";
        }
    }
}
