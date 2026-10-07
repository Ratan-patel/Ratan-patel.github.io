package io.github.ratanpatel.airt;

import android.annotation.SuppressLint;
import android.app.Activity;
import android.content.ContentValues;
import android.content.Intent;
import android.net.Uri;
import android.os.Build;
import android.os.Bundle;
import android.os.Environment;
import android.provider.MediaStore;
import android.util.Base64;
import android.view.KeyEvent;
import android.view.View;
import android.webkit.JavascriptInterface;
import android.webkit.WebChromeClient;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.widget.Toast;

import org.json.JSONObject;

import java.io.File;
import java.io.FileOutputStream;
import java.io.OutputStream;
import java.net.HttpURLConnection;
import java.net.URL;
import java.nio.charset.StandardCharsets;
import java.util.Iterator;

/**
 * AIRT Scanner — thin native shell around the bundled single-file scanner UI.
 *
 * Why a WebView and not a pure web page? Because browsers block cross-origin HTTP from a
 * page (CORS) and refuse plain-HTTP staging endpoints. This activity performs the requests
 * natively (HttpURLConnection) and exposes them to the UI through {@link Bridge}, so any
 * endpoint reachable from the phone can be tested — no CORS, http:// allowed, custom headers.
 *
 * Nothing is uploaded anywhere: results stay on the device until the operator exports them.
 */
public class MainActivity extends Activity {

    private WebView web;

    @SuppressLint("SetJavaScriptEnabled")
    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        web = new WebView(this);
        setContentView(web);

        WebSettings s = web.getSettings();
        s.setJavaScriptEnabled(true);
        s.setDomStorageEnabled(true);
        s.setAllowFileAccess(true);
        s.setDatabaseEnabled(true);
        s.setUserAgentString(s.getUserAgentString() + " AIRT/1.0.0");

        web.setWebChromeClient(new WebChromeClient());
        web.setWebViewClient(new WebViewClient());
        web.addJavascriptInterface(new Bridge(), "AirTBridge");
        web.loadUrl("file:///android_asset/index.html");
    }

    @Override
    public boolean onKeyDown(int keyCode, KeyEvent event) {
        if (keyCode == KeyEvent.KEYCODE_BACK && web != null && web.canGoBack()) {
            web.goBack();
            return true;
        }
        return super.onKeyDown(keyCode, event);
    }

    /** Bridge exposed to JavaScript as window.AirTBridge */
    private class Bridge {

        /** Native HTTP call: bypasses CORS and allows cleartext http:// endpoints. */
        @JavascriptInterface
        public String http(String method, String url, String headersJson, String body) {
            JSONObject result = new JSONObject();
            HttpURLConnection conn = null;
            long started = System.currentTimeMillis();
            try {
                URL target = new URL(url);
                conn = (HttpURLConnection) target.openConnection();
                conn.setRequestMethod(method == null || method.isEmpty() ? "POST" : method.toUpperCase());
                conn.setConnectTimeout(15000);
                conn.setReadTimeout(60000);
                conn.setInstanceFollowRedirects(true);
                conn.setRequestProperty("Accept", "application/json, text/plain, */*");
                conn.setRequestProperty("User-Agent", "AIRT-Scanner/1.0 (+authorised-testing)");

                if (headersJson != null && !headersJson.isEmpty()) {
                    JSONObject headers = new JSONObject(headersJson);
                    for (Iterator<String> it = headers.keys(); it.hasNext(); ) {
                        String k = it.next();
                        conn.setRequestProperty(k, headers.getString(k));
                    }
                }

                boolean hasBody = body != null && !body.isEmpty()
                        && !"GET".equalsIgnoreCase(conn.getRequestMethod());
                if (hasBody) {
                    conn.setDoOutput(true);
                    if (conn.getRequestProperty("Content-Type") == null) {
                        conn.setRequestProperty("Content-Type", "application/json");
                    }
                    byte[] payload = body.getBytes(StandardCharsets.UTF_8);
                    conn.setFixedLengthStreamingMode(payload.length);
                    try (OutputStream os = conn.getOutputStream()) {
                        os.write(payload);
                    }
                }

                int status = conn.getResponseCode();
                java.io.InputStream stream = (status >= 400) ? conn.getErrorStream() : conn.getInputStream();
                StringBuilder sb = new StringBuilder();
                if (stream != null) {
                    byte[] buffer = new byte[8192];
                    int read;
                    while ((read = stream.read(buffer)) != -1) {
                        sb.append(new String(buffer, 0, read, StandardCharsets.UTF_8));
                    }
                    stream.close();
                }
                result.put("status", status);
                result.put("body", sb.toString());
                result.put("ms", System.currentTimeMillis() - started);
                result.put("error", JSONObject.NULL);
                result.put("retryable", status == 408 || status == 429 || status >= 500);
            } catch (Exception exc) {
                try {
                    result.put("status", 0);
                    result.put("body", "");
                    result.put("ms", System.currentTimeMillis() - started);
                    result.put("error", exc.getClass().getSimpleName() + ": " + exc.getMessage());
                    result.put("retryable", true);
                } catch (Exception ignored) { }
            } finally {
                if (conn != null) conn.disconnect();
            }
            return result.toString();
        }

        /** Encode arbitrary bytes (the offline HTML report) for transport through the bridge. */
        @JavascriptInterface
        public String base64(String text) {
            return Base64.encodeToString(text.getBytes(StandardCharsets.UTF_8), Base64.NO_WRAP);
        }

        /**
         * Save a report to the device. Android 10+: MediaStore Downloads (no permission).
         * Older: app-specific external files dir. Returns a human-readable location.
         */
        @JavascriptInterface
        public String saveReport(String fileName, String content) {
            String safeName = fileName.replaceAll("[^A-Za-z0-9._-]", "_");
            byte[] data = content.getBytes(StandardCharsets.UTF_8);
            try {
                if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
                    ContentValues values = new ContentValues();
                    values.put(MediaStore.Downloads.DISPLAY_NAME, safeName);
                    values.put(MediaStore.Downloads.MIME_TYPE, mimeOf(safeName));
                    Uri uri = getContentResolver()
                            .insert(MediaStore.Downloads.EXTERNAL_CONTENT_URI, values);
                    if (uri == null) throw new Exception("MediaStore refused the insert");
                    try (OutputStream os = getContentResolver().openOutputStream(uri)) {
                        if (os == null) throw new Exception("no output stream");
                        os.write(data);
                    }
                    return "Downloads/" + safeName;
                }
                File dir = getExternalFilesDir(Environment.DIRECTORY_DOWNLOADS);
                if (dir == null) dir = getFilesDir();
                if (!dir.exists() && !dir.mkdirs()) throw new Exception("cannot create " + dir);
                File out = new File(dir, safeName);
                try (FileOutputStream fos = new FileOutputStream(out)) {
                    fos.write(data);
                }
                return out.getAbsolutePath();
            } catch (Exception exc) {
                return "ERROR: " + exc.getClass().getSimpleName() + ": " + exc.getMessage();
            }
        }

        /** Open a URL in the device browser (used for the "documentation" link). */
        @JavascriptInterface
        public void openUrl(String url) {
            try {
                Intent intent = new Intent(Intent.ACTION_VIEW, Uri.parse(url));
                intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
                startActivity(intent);
            } catch (Exception exc) {
                toast("cannot open " + url);
            }
        }

        @JavascriptInterface
        public void toast(String message) {
            runOnUiThread(() -> Toast.makeText(MainActivity.this, message,
                    Toast.LENGTH_SHORT).show());
        }

        @JavascriptInterface
        public String appInfo() {
            JSONObject info = new JSONObject();
            try {
                info.put("platform", "android");
                info.put("version", "1.0.0");
                info.put("sdk", Build.VERSION.SDK_INT);
                info.put("device", Build.MANUFACTURER + " " + Build.MODEL);
            } catch (Exception ignored) { }
            return info.toString();
        }
    }

    private static String mimeOf(String name) {
        if (name.endsWith(".html")) return "text/html";
        if (name.endsWith(".json")) return "application/json";
        if (name.endsWith(".sarif")) return "application/json";
        if (name.endsWith(".jsonl")) return "application/x-ndjson";
        return "text/plain";
    }
}
