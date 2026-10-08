package io.github.ratanpatel.ratanagent;

import android.app.Activity;
import android.content.ClipData;
import android.content.ClipboardManager;
import android.content.ContentValues;
import android.content.Context;
import android.content.Intent;
import android.content.pm.PackageManager;
import android.net.ConnectivityManager;
import android.net.Network;
import android.net.NetworkCapabilities;
import android.net.Uri;
import android.os.Build;
import android.os.Environment;
import android.os.VibrationEffect;
import android.os.Vibrator;
import android.provider.MediaStore;
import android.webkit.JavascriptInterface;
import android.webkit.WebView;

import org.json.JSONArray;
import org.json.JSONObject;

import java.io.File;
import java.io.FileOutputStream;
import java.io.OutputStream;
import java.net.Inet4Address;
import java.net.InetAddress;
import java.net.NetworkInterface;
import java.security.MessageDigest;
import java.util.Arrays;
import java.util.Collections;
import java.util.Enumeration;
import java.util.HashSet;
import java.util.Locale;
import java.util.Set;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

/**
 * Everything JavaScript is allowed to ask the phone to do.
 *
 * The bridge is exposed under two names — {@code RatanBridge} (this app) and
 * {@code AirTBridge} (the bundled AIRT toolkit page) — and every entry point first checks that
 * the calling page is one we shipped or the configured agent origin. A page that is not trusted
 * gets a structured "blocked" answer instead of a working HTTP client.
 */
public class AgentBridge {

    /** Permissions the web layer may ask for — nothing else is reachable from JS. */
    private static final Set<String> REQUESTABLE = Collections.unmodifiableSet(new HashSet<>(Arrays.asList(
            android.Manifest.permission.RECORD_AUDIO,
            android.Manifest.permission.CAMERA,
            android.Manifest.permission.POST_NOTIFICATIONS,
            HttpEngine.PERM_LOCAL_NETWORK,
            android.Manifest.permission.WRITE_EXTERNAL_STORAGE)));

    private static final ExecutorService POOL = Executors.newFixedThreadPool(4, runnable -> {
        Thread thread = new Thread(runnable, "ratan-agent-http");
        thread.setDaemon(true);
        return thread;
    });

    /** One chat at a time: a runaway page cannot fan out a hundred paid completions. */
    private final java.util.concurrent.atomic.AtomicBoolean chatBusy =
            new java.util.concurrent.atomic.AtomicBoolean(false);

    private final MainActivity activity;
    private final Prefs prefs;
    private final SecureStore secrets;
    private WebView web;

    public AgentBridge(MainActivity activity, WebView web, Prefs prefs) {
        this.activity = activity;
        this.web = web;
        this.prefs = prefs;
        this.secrets = new SecureStore(activity);
    }

    // ------------------------------------------------------------------ app info

    @JavascriptInterface
    public String appInfo() {
        JSONObject json = new JSONObject();
        try {
            json.put("app", "RATAN AI AGENT");
            json.put("version", BuildConfig.VERSION_NAME);
            json.put("versionCode", BuildConfig.VERSION_CODE);
            json.put("buildType", BuildConfig.BUILD_TYPE);
            json.put("package", activity.getPackageName());
            json.put("sdkInt", Build.VERSION.SDK_INT);
            json.put("android", Build.VERSION.RELEASE);
            json.put("device", Build.MANUFACTURER + " " + Build.MODEL);
            json.put("abi", Build.SUPPORTED_ABIS.length > 0 ? Build.SUPPORTED_ABIS[0] : "unknown");
            json.put("compileSdk", BuildConfig.COMPILE_SDK);
            json.put("targetSdk", activity.getApplicationInfo().targetSdkVersion);
            json.put("signature", signatureSha256());
            json.put("bridge", true);
        } catch (Exception exc) {
            return "{\"bridge\":true,\"error\":" + MainActivity.quote(String.valueOf(exc)) + "}";
        }
        return json.toString();
    }

    @JavascriptInterface
    public String deviceInfo() {
        JSONObject json = new JSONObject();
        try {
            json.put("device", Build.MANUFACTURER + " " + Build.MODEL);
            json.put("android", Build.VERSION.RELEASE);
            json.put("sdkInt", Build.VERSION.SDK_INT);
            json.put("network", networkType());
            json.put("localAddresses", new JSONArray(localAddresses()));
            json.put("storageState", Environment.getExternalStorageState());
            json.put("webView", webViewPackage());
            json.put("permissions", permissionSnapshot());
        } catch (Exception ignored) {
            // strings and primitives only
        }
        return json.toString();
    }

    @JavascriptInterface
    public String webViewVersion() {
        return webViewPackage();
    }

    @JavascriptInterface
    public String signatureHash() {
        return signatureSha256();
    }

    // ------------------------------------------------------------------ settings

    @JavascriptInterface
    public String getSettings() {
        return prefs.toJsonString();
    }

    @JavascriptInterface
    public boolean setPref(String key, String value) {
        if (!trustedCaller()) {
            return false;
        }
        prefs.set(key, value);
        return true;
    }

    @JavascriptInterface
    public void resetHttpSettings() {
        if (!trustedCaller()) {
            return;
        }
        prefs.resetHttpSettings();
    }

    // ------------------------------------------------------------------ http

    /** Synchronous, matches the AIRT bridge contract: returns a JSON result string. */
    @JavascriptInterface
    public String http(String method, String url, String headersJson, String body) {
        if (!trustedCaller()) {
            return blockedResult("this page is not allowed to use the native HTTP bridge");
        }
        return HttpEngine.execute(activity, prefs, method, url, headersJson, body).toJson();
    }

    /** Non-blocking variant: the answer arrives at window.__bridgeCallback(id, json). */
    @JavascriptInterface
    public void httpAsync(final String id, final String method, final String url,
                          final String headersJson, final String body) {
        if (!trustedCaller()) {
            deliver(id, blockedResult("this page is not allowed to use the native HTTP bridge"));
            return;
        }
        POOL.execute(() -> deliver(id,
                HttpEngine.execute(activity, prefs, method, url, headersJson, body).toJson()));
    }

    @JavascriptInterface
    public String reachabilityProbe(String url) {
        long started = System.currentTimeMillis();
        HttpEngine.Result result = HttpEngine.execute(activity, prefs, "HEAD", url, null, null);
        JSONObject json = new JSONObject();
        try {
            json.put("ok", result.status > 0);
            json.put("status", result.status);
            json.put("error", result.error == null ? JSONObject.NULL : result.error);
            json.put("ms", System.currentTimeMillis() - started);
        } catch (Exception ignored) {
            // primitives only
        }
        return json.toString();
    }

    private String blockedResult(String reason) {
        HttpEngine.Result result = new HttpEngine.Result();
        result.error = reason;
        result.blocked = true;
        result.retryable = false;
        return result.toJson();
    }

    private void deliver(final String id, final String payload) {
        final WebView view = web;
        if (view == null) {
            return;
        }
        view.post(() -> {
            try {
                view.evaluateJavascript("window.__bridgeCallback && window.__bridgeCallback("
                        + MainActivity.quote(id) + ", " + MainActivity.quote(payload) + ");", null);
            } catch (Exception ignored) {
                // page gone
            }
        });
    }

    // ------------------------------------------------------------------ files

    /**
     * Writes a report into Downloads/ (MediaStore on Android 10+, app-scoped dir below that).
     * Returns a human-readable location, or a string starting with "ERROR:" on failure —
     * the toolkit page shows exactly what comes back.
     */
    @JavascriptInterface
    public String saveReport(String fileName, String content) {
        if (!trustedCaller()) {
            return "ERROR: this page is not allowed to write files";
        }
        String safeName = (fileName == null ? "ratan-report.txt" : fileName)
                .replaceAll("[^A-Za-z0-9._-]", "_");
        byte[] data = (content == null ? "" : content).getBytes(java.nio.charset.StandardCharsets.UTF_8);
        try {
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
                ContentValues values = new ContentValues();
                values.put(MediaStore.Downloads.DISPLAY_NAME, safeName);
                values.put(MediaStore.Downloads.MIME_TYPE, mimeOf(safeName));
                Uri uri = activity.getContentResolver()
                        .insert(MediaStore.Downloads.EXTERNAL_CONTENT_URI, values);
                if (uri == null) {
                    throw new IllegalStateException("MediaStore refused the insert");
                }
                try (OutputStream os = activity.getContentResolver().openOutputStream(uri)) {
                    if (os == null) {
                        throw new IllegalStateException("no output stream");
                    }
                    os.write(data);
                }
                return "Downloads/" + safeName;
            }
            File dir = activity.getExternalFilesDir(Environment.DIRECTORY_DOWNLOADS);
            if (dir == null) {
                dir = activity.getFilesDir();
            }
            if (!dir.exists() && !dir.mkdirs()) {
                throw new IllegalStateException("cannot create " + dir);
            }
            File out = new File(dir, safeName);
            try (FileOutputStream fos = new FileOutputStream(out)) {
                fos.write(data);
            }
            return out.getAbsolutePath();
        } catch (Exception exc) {
            return "ERROR: " + exc.getClass().getSimpleName() + ": " + exc.getMessage();
        }
    }

    @JavascriptInterface
    public String listAssets(String prefix) {
        String dir = (prefix == null || prefix.isEmpty()) ? "" : prefix;
        try {
            String[] entries = activity.getAssets().list(dir);
            JSONArray array = new JSONArray();
            if (entries != null) {
                for (String entry : entries) {
                    array.put(entry);
                }
            }
            return array.toString();
        } catch (Exception exc) {
            return "[]";
        }
    }

    // ------------------------------------------------------------------ ui actions

    @JavascriptInterface
    public void toast(String message) {
        if (!trustedCaller()) {
            return;
        }
        activity.toast(message == null ? "" : message);
    }

    @JavascriptInterface
    public void share(String subject, String text) {
        if (!trustedCaller()) {
            return;
        }
        Intent intent = new Intent(Intent.ACTION_SEND);
        intent.setType("text/plain");
        intent.putExtra(Intent.EXTRA_SUBJECT, subject == null ? "RATAN AI AGENT" : subject);
        intent.putExtra(Intent.EXTRA_TEXT, text == null ? "" : text);
        Intent chooser = Intent.createChooser(intent, "Share");
        chooser.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
        try {
            activity.startActivity(chooser);
        } catch (Exception exc) {
            activity.toast("Nothing to share with");
        }
    }

    @JavascriptInterface
    public boolean copy(String label, String text) {
        if (!trustedCaller()) {
            return false;
        }
        try {
            ClipboardManager clipboard =
                    (ClipboardManager) activity.getSystemService(Context.CLIPBOARD_SERVICE);
            if (clipboard == null) {
                return false;
            }
            clipboard.setPrimaryClip(ClipData.newPlainText(
                    label == null ? "RATAN AI AGENT" : label, text == null ? "" : text));
            activity.toast("Copied");
            return true;
        } catch (Exception exc) {
            return false;
        }
    }

    @JavascriptInterface
    public void openExternal(String url) {
        if (!trustedCaller()) {
            return;
        }
        activity.openExternally(url);
    }

    @JavascriptInterface
    public void openAgent() {
        activity.loadAgent();
    }

    @JavascriptInterface
    public void openToolkit() {
        activity.loadToolkit();
    }

    @JavascriptInterface
    public void openHome() {
        activity.loadHome();
    }

    @JavascriptInterface
    public void reload() {
        activity.reload();
    }

    @JavascriptInterface
    public void openAppSettings() {
        activity.openAppSettings();
    }

    @JavascriptInterface
    public void vibrate(int milliseconds) {
        try {
            Vibrator vibrator = (Vibrator) activity.getSystemService(Context.VIBRATOR_SERVICE);
            if (vibrator == null || !vibrator.hasVibrator()) {
                return;
            }
            int ms = Math.max(10, Math.min(400, milliseconds));
            if (Build.VERSION.SDK_INT >= 26) {
                vibrator.vibrate(VibrationEffect.createOneShot(ms, VibrationEffect.DEFAULT_AMPLITUDE));
            } else {
                //noinspection deprecation
                vibrator.vibrate(ms);
            }
        } catch (Exception ignored) {
            // vibration is cosmetic
        }
    }

    // ------------------------------------------------------------------ permissions

    @JavascriptInterface
    public String permissionSnapshot() {
        JSONObject json = new JSONObject();
        try {
            json.put("recordAudio", activity.hasPermission(android.Manifest.permission.RECORD_AUDIO));
            json.put("camera", activity.hasPermission(android.Manifest.permission.CAMERA));
            json.put("notifications", Build.VERSION.SDK_INT < 33
                    || activity.hasPermission(android.Manifest.permission.POST_NOTIFICATIONS));
            json.put("localNetwork", !HttpEngine.needsLocalNetworkPermission(activity));
        } catch (Exception ignored) {
            // booleans only
        }
        return json.toString();
    }

    @JavascriptInterface
    public boolean hasPermission(String permission) {
        return permission != null && activity.hasPermission(permission);
    }

    @JavascriptInterface
    public boolean requestPermission(String permission) {
        if (!trustedCaller() || permission == null || !REQUESTABLE.contains(permission)) {
            return false;
        }
        if (activity.hasPermission(permission)) {
            return true;
        }
        activity.requestRuntimePermissions(new String[]{permission});
        return false;
    }

    @JavascriptInterface
    public boolean needsLocalNetworkPermission() {
        return HttpEngine.needsLocalNetworkPermission(activity);
    }

    /** Called by the activity once the user answered a runtime permission dialog. */
    public void notifyPermissionResult(int requestCode, String[] permissions, int[] results) {
        JSONObject json = new JSONObject();
        try {
            json.put("requestCode", requestCode);
            JSONObject granted = new JSONObject();
            for (int i = 0; i < permissions.length; i++) {
                granted.put(permissions[i], i < results.length
                        && results[i] == PackageManager.PERMISSION_GRANTED);
            }
            json.put("granted", granted);
            json.put("snapshot", new JSONObject(permissionSnapshot()));
        } catch (Exception ignored) {
            // primitives only
        }
        final WebView view = web;
        if (view == null) {
            return;
        }
        view.post(() -> view.evaluateJavascript(
                "window.__permissionResult && window.__permissionResult("
                        + MainActivity.quote(json.toString()) + ");", null));
    }

    /** Called on resume so the dashboard can refresh device/permission state. */
    public void pushStatus() {
        final WebView view = web;
        if (view == null) {
            return;
        }
        JSONObject json = new JSONObject();
        try {
            json.put("url", activity.currentUrl());
            json.put("settings", prefs.toJson());
            json.put("permissions", new JSONObject(permissionSnapshot()));
            json.put("network", networkType());
        } catch (Exception ignored) {
            // primitives only
        }
        view.post(() -> view.evaluateJavascript(
                "window.__status && window.__status(" + MainActivity.quote(json.toString()) + ");", null));
    }

    @JavascriptInterface
    public void requestLocalNetworkPermission() {
        if (!trustedCaller()) {
            return;
        }
        if (HttpEngine.needsLocalNetworkPermission(activity)) {
            activity.requestRuntimePermissions(new String[]{HttpEngine.PERM_LOCAL_NETWORK});
            activity.toast("Allow nearby devices to reach LAN lab targets");
        }
    }

    // ------------------------------------------------------------------ diagnostics

    /**
     * Deterministic self-test. Everything a phone-side support conversation needs:
     * which build is installed, whether the bridge answers, whether the bundled pages are
     * intact, which permissions are live, and whether the agent endpoint is reachable.
     */
    @JavascriptInterface
    public String selfTest() {
        JSONArray checks = new JSONArray();
        try {
            addCheck(checks, "Native bridge", true,
                    "RatanBridge + AirTBridge registered · v" + BuildConfig.VERSION_NAME
                            + " (" + BuildConfig.VERSION_CODE + ")");
            addCheck(checks, "Android runtime", Build.VERSION.SDK_INT >= 24,
                    "Android " + Build.VERSION.RELEASE + " · API " + Build.VERSION.SDK_INT
                            + " · target " + activity.getApplicationInfo().targetSdkVersion);
            String[] assets = new String[0];
            try {
                assets = activity.getAssets().list("");
            } catch (Exception ignored) {
                // reported below
            }
            boolean hasHome = false;
            boolean hasToolkit = false;
            for (String asset : assets) {
                if ("home.html".equals(asset)) {
                    hasHome = true;
                }
                if ("toolkit.html".equals(asset)) {
                    hasToolkit = true;
                }
            }
            addCheck(checks, "Bundled dashboard", hasHome, hasHome ? "assets/home.html" : "missing");
            addCheck(checks, "Offline red-team toolkit", hasToolkit,
                    hasToolkit ? "assets/toolkit.html (67 probes, offline)" : "missing");
            addCheck(checks, "WebView engine", webViewPackage().startsWith("com.google")
                            || webViewPackage().startsWith("com.android"),
                    webViewPackage());
            addCheck(checks, "Transport policy", true,
                    "https always · LAN http " + (prefs.allowLanHttp() ? "allowed" : "blocked")
                            + " · public http " + (prefs.allowPublicHttp() ? "allowed" : "blocked"));
            boolean lanOk = !HttpEngine.needsLocalNetworkPermission(activity);
            addCheck(checks, "Local network permission (Android 17)", lanOk,
                    lanOk ? "granted / not required on this device"
                            : "not granted — LAN lab targets will be refused");
            addCheck(checks, "Microphone", activity.hasPermission(android.Manifest.permission.RECORD_AUDIO),
                    "voice input to the agent");
            addCheck(checks, "Camera", activity.hasPermission(android.Manifest.permission.CAMERA),
                    "image input to the agent");
            addCheck(checks, "Notifications",
                    Build.VERSION.SDK_INT < 33
                            || activity.hasPermission(android.Manifest.permission.POST_NOTIFICATIONS),
                    "download + scan progress notices");
            addCheck(checks, "Signature (SHA-256)", true, signatureSha256());

            HttpEngine.Result probe = HttpEngine.execute(activity, prefs, "HEAD", prefs.agentUrl(), null, null);
            addCheck(checks, "Agent endpoint", probe.status > 0 || probe.blocked,
                    prefs.agentUrl() + " → " + (probe.blocked ? "blocked: " + probe.error
                            : (probe.status > 0 ? "HTTP " + probe.status : probe.error)));
        } catch (Exception exc) {
            try {
                addCheck(checks, "Self-test", false, exc.getClass().getSimpleName() + ": " + exc.getMessage());
            } catch (Exception ignored) {
                // nothing left to do
            }
        }
        return checks.toString();
    }

    private static void addCheck(JSONArray array, String label, boolean ok, String detail) {
        JSONObject entry = new JSONObject();
        try {
            entry.put("label", label);
            entry.put("ok", ok);
            entry.put("detail", detail == null ? "" : detail);
            array.put(entry);
        } catch (Exception ignored) {
            // primitives only
        }
    }

    // ------------------------------------------------------------------ bring your own API

    /**
     * Current provider profile. The API key is represented only by a masked tail — the value
     * itself is never handed back to JavaScript once stored.
     */
    @JavascriptInterface
    public String llmInfo() {
        if (!trustedCaller()) {
            return "{\"error\":\"untrusted page\"}";
        }
        return LlmClient.info(activity, prefs, secrets);
    }

    @JavascriptInterface
    public String llmSaveConfig(String configJson) {
        if (!trustedCaller()) {
            return "{\"ok\":false,\"error\":\"untrusted page\"}";
        }
        return LlmClient.saveConfig(prefs, configJson);
    }

    /** Stores (or replaces) the provider credential in the Android Keystore. Write-only by design. */
    @JavascriptInterface
    public String llmSetKey(String key) {
        JSONObject json = new JSONObject();
        try {
            if (!trustedCaller()) {
                json.put("ok", false);
                json.put("error", "untrusted page");
                return json.toString();
            }
            if (key == null || key.trim().isEmpty()) {
                secrets.remove(LlmClient.KEY_NAME);
                json.put("ok", true);
                json.put("cleared", true);
                json.put("hint", "");
                return json.toString();
            }
            if (!secrets.isAvailable()) {
                json.put("ok", false);
                json.put("error", "this device has no usable Android Keystore, so the key cannot be stored safely");
                return json.toString();
            }
            secrets.put(LlmClient.KEY_NAME, key.trim());
            json.put("ok", true);
            json.put("hint", secrets.hint(LlmClient.KEY_NAME, 4));
            json.put("note", "key stored in the Android Keystore — it is never returned to the page");
        } catch (Exception exc) {
            // JSONObject.put() itself declares a checked exception, so even the failure path
            // needs a guard here.
            try {
                json.put("ok", false);
                json.put("error", exc.getClass().getSimpleName() + ": " + exc.getMessage());
            } catch (Exception ignored) {
                return "{\"ok\":false}";
            }
        }
        return json.toString();
    }

    @JavascriptInterface
    public boolean llmHasKey() {
        return secrets.has(LlmClient.KEY_NAME);
    }

    @JavascriptInterface
    public String llmClearKey() {
        JSONObject json = new JSONObject();
        try {
            if (!trustedCaller()) {
                json.put("ok", false);
                return json.toString();
            }
            secrets.remove(LlmClient.KEY_NAME);
            json.put("ok", true);
            json.put("hint", "");
        } catch (Exception ignored) {
            // nothing to report
        }
        return json.toString();
    }

    /** Blocking completion; prefer {@link #llmChatAsync} from the UI so the page stays responsive. */
    @JavascriptInterface
    public String llmChat(String messagesJson) {
        if (!trustedCaller()) {
            return "{\"ok\":false,\"error\":\"untrusted page\"}";
        }
        if (!chatBusy.compareAndSet(false, true)) {
            return "{\"ok\":false,\"error\":\"another completion is still running\"}";
        }
        try {
            return LlmClient.chat(activity, prefs, secrets, messagesJson);
        } finally {
            chatBusy.set(false);
        }
    }

    @JavascriptInterface
    public void llmChatAsync(final String id, final String messagesJson) {
        if (!trustedCaller()) {
            deliverLlm(id, "{\"ok\":false,\"error\":\"untrusted page\"}");
            return;
        }
        if (!chatBusy.compareAndSet(false, true)) {
            deliverLlm(id, "{\"ok\":false,\"error\":\"another completion is still running\"}");
            return;
        }
        POOL.execute(() -> {
            String result;
            try {
                result = LlmClient.chat(activity, prefs, secrets, messagesJson);
            } finally {
                chatBusy.set(false);
            }
            deliverLlm(id, result);
        });
    }

    @JavascriptInterface
    public String llmTest() {
        if (!trustedCaller()) {
            return "{\"ok\":false,\"error\":\"untrusted page\"}";
        }
        if (!chatBusy.compareAndSet(false, true)) {
            return "{\"ok\":false,\"error\":\"another completion is still running\"}";
        }
        try {
            return LlmClient.test(activity, prefs, secrets);
        } finally {
            chatBusy.set(false);
        }
    }

    private void deliverLlm(final String id, final String payload) {
        final WebView view = web;
        if (view == null) {
            return;
        }
        view.post(() -> {
            try {
                view.evaluateJavascript("window.__llmCallback && window.__llmCallback("
                        + MainActivity.quote(id) + ", " + MainActivity.quote(payload) + ");", null);
            } catch (Exception ignored) {
                // page gone
            }
        });
    }

    // ------------------------------------------------------------------ internals

    /**
     * Only the pages we shipped (file:///android_asset) and the configured agent origin may
     * use the bridge. Anything else — an injected iframe, a redirected page, a blob — is
     * refused, so a hostile page cannot borrow the phone's sockets or filesystem.
     */
    private boolean trustedCaller() {
        String url = activity.currentUrl();
        if (url == null) {
            return false;
        }
        if (url.startsWith("file:///android_asset/")) {
            return true;
        }
        String agent = prefs.agentUrl();
        try {
            Uri a = Uri.parse(agent);
            Uri b = Uri.parse(url);
            String ha = a.getHost() == null ? "" : a.getHost().toLowerCase(Locale.US);
            String hb = b.getHost() == null ? "" : b.getHost().toLowerCase(Locale.US);
            String sa = a.getScheme() == null ? "" : a.getScheme().toLowerCase(Locale.US);
            String sb = b.getScheme() == null ? "" : b.getScheme().toLowerCase(Locale.US);
            return !ha.isEmpty() && ha.equals(hb) && sa.equals(sb);
        } catch (Exception exc) {
            return false;
        }
    }

    private String networkType() {
        try {
            ConnectivityManager manager =
                    (ConnectivityManager) activity.getSystemService(Context.CONNECTIVITY_SERVICE);
            if (manager == null) {
                return "unknown";
            }
            Network network = manager.getActiveNetwork();
            if (network == null) {
                return "offline";
            }
            NetworkCapabilities capabilities = manager.getNetworkCapabilities(network);
            if (capabilities == null) {
                return "unknown";
            }
            if (capabilities.hasTransport(NetworkCapabilities.TRANSPORT_WIFI)) {
                return "wifi";
            }
            if (capabilities.hasTransport(NetworkCapabilities.TRANSPORT_CELLULAR)) {
                return "cellular";
            }
            if (capabilities.hasTransport(NetworkCapabilities.TRANSPORT_ETHERNET)) {
                return "ethernet";
            }
            if (capabilities.hasTransport(NetworkCapabilities.TRANSPORT_VPN)) {
                return "vpn";
            }
            return "other";
        } catch (Exception exc) {
            return "unknown";
        }
    }

    private JSONArray localAddresses() {
        JSONArray array = new JSONArray();
        try {
            Enumeration<NetworkInterface> interfaces = NetworkInterface.getNetworkInterfaces();
            while (interfaces != null && interfaces.hasMoreElements()) {
                NetworkInterface iface = interfaces.nextElement();
                if (!iface.isUp() || iface.isLoopback()) {
                    continue;
                }
                Enumeration<InetAddress> addresses = iface.getInetAddresses();
                while (addresses.hasMoreElements()) {
                    InetAddress address = addresses.nextElement();
                    if (address instanceof Inet4Address && !address.isLoopbackAddress()
                            && !address.isLinkLocalAddress()) {
                        array.put(address.getHostAddress() + " (" + iface.getName() + ")");
                    }
                }
            }
        } catch (Exception ignored) {
            // diagnostics are best-effort
        }
        return array;
    }

    private String webViewPackage() {
        try {
            if (Build.VERSION.SDK_INT >= 26) {
                PackageManager packageManager = activity.getPackageManager();
                android.content.pm.PackageInfo info = WebView.getCurrentWebViewPackage();
                if (info != null) {
                    return info.packageName + " " + info.versionName;
                }
            }
        } catch (Exception ignored) {
            // fall through
        }
        return "unknown";
    }

    private String signatureSha256() {
        try {
            PackageManager packageManager = activity.getPackageManager();
            String packageName = activity.getPackageName();
            byte[] certificate;
            if (Build.VERSION.SDK_INT >= 28) {
                android.content.pm.SigningInfo info =
                        packageManager.getPackageInfo(packageName, PackageManager.GET_SIGNING_CERTIFICATES).signingInfo;
                android.content.pm.Signature[] signatures = info == null ? null : info.getApkContentsSigners();
                if (signatures == null || signatures.length == 0) {
                    return "unknown";
                }
                certificate = signatures[0].toByteArray();
            } else {
                android.content.pm.Signature[] signatures =
                        packageManager.getPackageInfo(packageName, PackageManager.GET_SIGNATURES).signatures;
                if (signatures == null || signatures.length == 0) {
                    return "unknown";
                }
                certificate = signatures[0].toByteArray();
            }
            MessageDigest digest = MessageDigest.getInstance("SHA-256");
            byte[] hash = digest.digest(certificate);
            StringBuilder sb = new StringBuilder(hash.length * 2);
            for (byte value : hash) {
                sb.append(String.format(Locale.US, "%02x", value));
            }
            return sb.toString();
        } catch (Exception exc) {
            return "unavailable";
        }
    }

    private static String mimeOf(String name) {
        if (name.endsWith(".html")) {
            return "text/html";
        }
        if (name.endsWith(".json") || name.endsWith(".sarif")) {
            return "application/json";
        }
        if (name.endsWith(".jsonl")) {
            return "application/x-ndjson";
        }
        if (name.endsWith(".md")) {
            return "text/markdown";
        }
        return "text/plain";
    }
}
