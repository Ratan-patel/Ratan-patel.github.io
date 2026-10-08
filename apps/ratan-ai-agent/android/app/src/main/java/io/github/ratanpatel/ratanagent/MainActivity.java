package io.github.ratanpatel.ratanagent;

import android.annotation.SuppressLint;
import android.app.Activity;
import android.app.DownloadManager;
import android.content.ActivityNotFoundException;
import android.content.Context;
import android.content.Intent;
import android.content.pm.PackageManager;
import android.net.Uri;
import android.os.Build;
import android.os.Bundle;
import android.os.Environment;
import android.provider.Settings;
import android.view.View;
import android.view.ViewGroup;
import android.view.Window;
import android.view.WindowInsets;
import android.view.WindowManager;
import android.webkit.CookieManager;
import android.webkit.PermissionRequest;
import android.webkit.URLUtil;
import android.webkit.ValueCallback;
import android.webkit.WebChromeClient;
import android.webkit.WebResourceError;
import android.webkit.WebResourceRequest;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.widget.FrameLayout;
import android.widget.ProgressBar;
import android.widget.Toast;
import android.window.OnBackInvokedCallback;
import android.window.OnBackInvokedDispatcher;

import java.util.ArrayList;
import java.util.List;
import java.util.Locale;

/**
 * RATAN AI AGENT 2.0 — hardened, edge-to-edge native shell for the RATAN AI assistant.
 *
 * Design notes (why it looks like this):
 *  - The remote assistant keeps working without an app update, but the shell owns everything
 *    a browser cannot do: CORS-free HTTP to lab endpoints, Downloads writing, file pickers,
 *    microphone/camera hand-off, and the Android 17 local-network permission.
 *  - Only trusted pages ever run inside this WebView (bundled assets + the configured agent
 *    origin). Every other link leaves the app, because a WebView with a JavaScript bridge is
 *    an attack surface the moment it renders a page we do not control.
 *  - The bundled offline toolkit (AIRT scanner) is the same corpus as the desktop CLI; the
 *    bridge is exposed under both "RatanBridge" and the legacy "AirTBridge" name so the
 *    toolkit page does not need a fork.
 */
public class MainActivity extends Activity {

    public static final String HOME_URL = "file:///android_asset/home.html";
    public static final String TOOLKIT_URL = "file:///android_asset/toolkit.html";

    public static final int REQ_FILE_CHOOSER = 4011;
    public static final int REQ_WEB_PERMISSIONS = 4012;
    public static final int REQ_RUNTIME_PERMISSIONS = 4013;

    private FrameLayout root;
    private ProgressBar progress;
    private WebView web;
    private AgentBridge bridge;
    private Prefs prefs;

    private ValueCallback<Uri[]> pendingFileChooser;
    private final List<PermissionRequest> pendingWebPermissions = new ArrayList<>();
    private OnBackInvokedCallback backCallback;

    /** Last URL committed by the main frame (updated on the UI thread, read from bridge threads). */
    private volatile String currentUrl = HOME_URL;
    private volatile String pendingOfflineNotice = null;

    @SuppressLint("SetJavaScriptEnabled")
    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        prefs = new Prefs(this);

        root = new FrameLayout(this);
        root.setBackgroundColor(0xFF060A16);
        progress = new ProgressBar(this, null, android.R.attr.progressBarStyleHorizontal);
        progress.setMax(100);
        progress.setVisibility(View.GONE);
        FrameLayout.LayoutParams progressParams = new FrameLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, dpToPx(3));
        progressParams.gravity = android.view.Gravity.TOP;
        root.addView(progress, progressParams);
        setContentView(root);

        applyEdgeToEdge();
        installInsetsHandler();
        createWebView();

        if (Build.VERSION.SDK_INT >= 33) {
            backCallback = this::handleBack;
            getOnBackInvokedDispatcher().registerOnBackInvokedCallback(
                    OnBackInvokedDispatcher.PRIORITY_DEFAULT, backCallback);
        }

        getWindow().setSoftInputMode(WindowManager.LayoutParams.SOFT_INPUT_ADJUST_RESIZE);

        if (savedInstanceState != null && web.restoreState(savedInstanceState) != null) {
            // restored (possibly mid-scan) — nothing else to do
        } else {
            web.loadUrl(HOME_URL);
        }
    }

    // ------------------------------------------------------------------ webview

    @SuppressLint({"SetJavaScriptEnabled", "AddJavascriptInterface"})
    private void createWebView() {
        if (web != null) {
            root.removeView(web);
            web.destroy();
        }
        web = new WebView(this);
        web.setBackgroundColor(0xFF060A16);
        FrameLayout.LayoutParams params = new FrameLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.MATCH_PARENT);
        root.addView(web, params);

        WebSettings s = web.getSettings();
        s.setJavaScriptEnabled(true);
        s.setDomStorageEnabled(true);
        s.setDatabaseEnabled(false);
        s.setAllowFileAccess(true);                 // bundled assets live on file:///android_asset
        s.setAllowContentAccess(false);
        s.setAllowFileAccessFromFileURLs(false);    // never let a local page read arbitrary files
        s.setAllowUniversalAccessFromFileURLs(false);
        s.setJavaScriptCanOpenWindowsAutomatically(false);
        s.setSupportMultipleWindows(false);
        s.setMixedContentMode(WebSettings.MIXED_CONTENT_NEVER_ALLOW);
        s.setGeolocationEnabled(false);
        s.setSaveFormData(false);
        s.setMediaPlaybackRequiresUserGesture(true);
        s.setBuiltInZoomControls(false);
        s.setDisplayZoomControls(false);
        s.setLoadWithOverviewMode(false);
        s.setUseWideViewPort(true);
        s.setTextZoom(100);
        s.setCacheMode(WebSettings.LOAD_DEFAULT);
        s.setUserAgentString(s.getUserAgentString() + " RatanAgent/"
                + BuildConfig.VERSION_NAME + " (Android " + Build.VERSION.RELEASE + ")");
        if (Build.VERSION.SDK_INT >= 26) {
            s.setSafeBrowsingEnabled(true);
        }
        if (Build.VERSION.SDK_INT >= 30) {
            s.setForceDark(WebSettings.FORCE_DARK_AUTO);
        }

        CookieManager cookies = CookieManager.getInstance();
        cookies.setAcceptCookie(true);
        if (Build.VERSION.SDK_INT >= 30) {
            cookies.setAcceptThirdPartyCookies(web, false);
        }

        if (BuildConfig.DEBUG) {
            WebView.setWebContentsDebuggingEnabled(true);
        }

        bridge = new AgentBridge(this, web, prefs);
        web.addJavascriptInterface(bridge, "RatanBridge");
        // legacy alias so the bundled AIRT toolkit page runs unmodified
        web.addJavascriptInterface(bridge, "AirTBridge");

        web.setWebViewClient(new WebViewClient() {

            @Override
            public boolean shouldOverrideUrlLoading(WebView view, WebResourceRequest request) {
                Uri uri = request == null ? null : request.getUrl();
                if (uri == null) {
                    return false;
                }
                String url = uri.toString();
                if (isBundledAsset(url)) {
                    return false;                       // in-app: our own page
                }
                if (isTrustedOrigin(url)) {
                    return false;                       // in-app: the configured agent
                }
                if (!prefs.openExternal()) {
                    toast("External links are disabled in settings");
                    return true;
                }
                openExternally(url);                    // everything else leaves the app
                return true;
            }

            @Override
            public void onPageStarted(WebView view, String url, android.graphics.Bitmap favicon) {
                if (url != null) {
                    currentUrl = url;
                }
                progress.setVisibility(View.VISIBLE);
            }

            @Override
            public void onPageFinished(WebView view, String url) {
                progress.setVisibility(View.GONE);
                if (url != null) {
                    currentUrl = url;
                }
                String notice = pendingOfflineNotice;
                if (notice != null && url != null && url.startsWith("file:///android_asset/")) {
                    pendingOfflineNotice = null;
                    view.evaluateJavascript(
                            "window.__offlineNotice && window.__offlineNotice(" + quote(notice) + ")",
                            null);
                }
                view.evaluateJavascript(
                        "document.documentElement.dataset.ratanShell='android';", null);
            }

            @Override
            public void onReceivedError(WebView view, WebResourceRequest request, WebResourceError error) {
                if (request == null || !request.isForMainFrame()) {
                    return;
                }
                String url = request.getUrl() == null ? "" : request.getUrl().toString();
                if (url.startsWith("file://")) {
                    toast("Bundled page failed to load: " + url);
                    return;
                }
                String reason = error == null ? "network error" : String.valueOf(error.getDescription());
                pendingOfflineNotice = "Agent unreachable — " + reason
                        + ". You are on the offline dashboard; the red-team toolkit still works.";
                view.loadUrl(HOME_URL);
            }

            @Override
            public boolean onRenderProcessGone(WebView view, android.webkit.RenderProcessGoneDetail detail) {
                // Returning true tells the framework we handled the crash ourselves: the shell
                // rebuilds its WebView instead of taking the whole app down with it.
                toast("WebView engine restarted");
                createWebView();
                web.loadUrl(HOME_URL);
                return true;
            }
        });

        web.setWebChromeClient(new WebChromeClient() {
            @Override
            public void onProgressChanged(WebView view, int newProgress) {
                progress.setProgress(newProgress);
                progress.setVisibility(newProgress >= 100 ? View.GONE : View.VISIBLE);
            }

            @Override
            public void onPermissionRequest(final PermissionRequest request) {
                handleWebPermissionRequest(request);
            }

            @Override
            public void onGeolocationPermissionsShowPrompt(String origin,
                                                           android.webkit.GeolocationPermissions.Callback callback) {
                callback.invoke(origin, false, false);   // the shell deliberately has no location access
            }

            @Override
            public boolean onShowFileChooser(WebView view, ValueCallback<Uri[]> callback,
                                             FileChooserParams params) {
                if (pendingFileChooser != null) {
                    pendingFileChooser.onReceiveValue(null);
                }
                pendingFileChooser = callback;
                try {
                    Intent intent = params.createIntent();
                    intent.addCategory(Intent.CATEGORY_OPENABLE);
                    startActivityForResult(Intent.createChooser(intent, "Select file"), REQ_FILE_CHOOSER);
                    return true;
                } catch (Exception exc) {
                    toast("No file picker available");
                    pendingFileChooser = null;
                    return false;
                }
            }
        });

        web.setDownloadListener((url, userAgent, contentDisposition, mimeType, contentLength) -> {
            if (url == null || url.startsWith("blob:") || url.startsWith("data:")) {
                toast("Use the app's own export buttons to save that report");
                return;
            }
            try {
                DownloadManager.Request request = new DownloadManager.Request(Uri.parse(url));
                if (mimeType != null) {
                    request.setMimeType(mimeType);
                }
                if (userAgent != null) {
                    request.addRequestHeader("User-Agent", userAgent);
                }
                String cookie = CookieManager.getInstance().getCookie(url);
                if (cookie != null) {
                    request.addRequestHeader("Cookie", cookie);
                }
                String name = URLUtil.guessFileName(url, contentDisposition, mimeType);
                request.setTitle(name);
                request.setDescription("RATAN AI AGENT download");
                request.setNotificationVisibility(
                        DownloadManager.Request.VISIBILITY_VISIBLE_NOTIFY_COMPLETED);
                request.setDestinationInExternalPublicDir(Environment.DIRECTORY_DOWNLOADS, name);
                DownloadManager manager = (DownloadManager) getSystemService(Context.DOWNLOAD_SERVICE);
                if (manager == null) {
                    throw new IllegalStateException("no DownloadManager");
                }
                manager.enqueue(request);
                toast("Downloading " + name);
            } catch (Exception exc) {
                toast("Download failed: " + exc.getMessage());
                openExternally(url);
            }
        });
    }

    private void handleWebPermissionRequest(final PermissionRequest request) {
        List<String> needed = new ArrayList<>();
        for (String resource : request.getResources()) {
            if (PermissionRequest.RESOURCE_AUDIO_CAPTURE.equals(resource)
                    && !hasPermission(android.Manifest.permission.RECORD_AUDIO)) {
                needed.add(android.Manifest.permission.RECORD_AUDIO);
            } else if (PermissionRequest.RESOURCE_VIDEO_CAPTURE.equals(resource)
                    && !hasPermission(android.Manifest.permission.CAMERA)) {
                needed.add(android.Manifest.permission.CAMERA);
            }
        }
        if (needed.isEmpty()) {
            runOnUiThread(() -> {
                try {
                    request.grant(request.getResources());
                } catch (Exception ignored) {
                    // page navigated away
                }
            });
            return;
        }
        pendingWebPermissions.add(request);
        runOnUiThread(() -> requestPermissions(needed.toArray(new String[0]), REQ_WEB_PERMISSIONS));
    }

    // ------------------------------------------------------------------ navigation

    public void loadHome() {
        runOnUiThread(() -> web.loadUrl(HOME_URL));
    }

    public void loadToolkit() {
        runOnUiThread(() -> web.loadUrl(TOOLKIT_URL));
    }

    public void loadAgent() {
        final String url = prefs.agentUrl();
        runOnUiThread(() -> web.loadUrl(url));
    }

    public void reload() {
        runOnUiThread(() -> {
            String url = web.getUrl();
            if (url == null || url.startsWith("file://")) {
                web.loadUrl(HOME_URL);
            } else {
                web.reload();
            }
        });
    }

    private void handleBack() {
        runOnUiThread(() -> {
            if (web.canGoBack()) {
                web.goBack();
                return;
            }
            String url = currentUrl == null ? "" : currentUrl;
            if (!url.startsWith("file:///android_asset/home.html")) {
                web.loadUrl(HOME_URL);
                return;
            }
            finish();
        });
    }

    @Override
    @SuppressWarnings("deprecation")
    public void onBackPressed() {
        if (Build.VERSION.SDK_INT >= 33) {
            super.onBackPressed();          // framework drives OnBackInvokedCallback instead
            return;
        }
        handleBack();
    }

    /** Bundled pages may run in-app; anything else must match the configured agent origin. */
    private boolean isBundledAsset(String url) {
        return url != null && url.startsWith("file:///android_asset/");
    }

    private boolean isTrustedOrigin(String url) {
        if (url == null || !(url.startsWith("http://") || url.startsWith("https://"))) {
            return false;
        }
        String agent = prefs.agentUrl();
        try {
            Uri a = Uri.parse(agent);
            Uri b = Uri.parse(url);
            String schemeA = a.getScheme() == null ? "" : a.getScheme().toLowerCase(Locale.US);
            String schemeB = b.getScheme() == null ? "" : b.getScheme().toLowerCase(Locale.US);
            if (!schemeA.equals(schemeB)) {
                return false;
            }
            String hostA = a.getHost() == null ? "" : a.getHost().toLowerCase(Locale.US);
            String hostB = b.getHost() == null ? "" : b.getHost().toLowerCase(Locale.US);
            if (!hostA.equals(hostB)) {
                return false;
            }
            int portA = a.getPort();
            int portB = b.getPort();
            if (portA == -1) {
                portA = "https".equals(schemeA) ? 443 : 80;
            }
            if (portB == -1) {
                portB = "https".equals(schemeB) ? 443 : 80;
            }
            return portA == portB;
        } catch (Exception exc) {
            return false;
        }
    }

    /** Opens a link in the device browser. Only web schemes are ever forwarded. */
    public void openExternally(String url) {
        if (url == null) {
            return;
        }
        String lower = url.toLowerCase(Locale.US);
        if (!(lower.startsWith("http://") || lower.startsWith("https://") || lower.startsWith("mailto:")
                || lower.startsWith("tel:") || lower.startsWith("market:"))) {
            toast("Blocked link: " + url);
            return;
        }
        try {
            Intent intent = new Intent(Intent.ACTION_VIEW, Uri.parse(url));
            intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
            runOnUiThread(() -> {
                try {
                    startActivity(intent);
                } catch (ActivityNotFoundException exc) {
                    toast("No app can open that link");
                }
            });
        } catch (Exception exc) {
            toast("Blocked link: " + url);
        }
    }

    public void openAppSettings() {
        try {
            Intent intent = new Intent(Settings.ACTION_APPLICATION_DETAILS_SETTINGS,
                    Uri.fromParts("package", getPackageName(), null));
            intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
            startActivity(intent);
        } catch (Exception exc) {
            toast("Cannot open app settings");
        }
    }

    // ------------------------------------------------------------------ system glue

    private void applyEdgeToEdge() {
        Window window = getWindow();
        window.setStatusBarColor(0x00000000);
        window.setNavigationBarColor(0x00000000);
        if (Build.VERSION.SDK_INT >= 30) {
            window.setDecorFitsSystemWindows(false);
        } else {
            //noinspection deprecation
            window.getDecorView().setSystemUiVisibility(
                    View.SYSTEM_UI_FLAG_LAYOUT_STABLE
                            | View.SYSTEM_UI_FLAG_LAYOUT_FULLSCREEN
                            | View.SYSTEM_UI_FLAG_LAYOUT_HIDE_NAVIGATION);
        }
        if (Build.VERSION.SDK_INT >= 29) {
            window.setNavigationBarContrastEnforced(false);
            window.setStatusBarContrastEnforced(false);
        }
    }

    private void installInsetsHandler() {
        root.setOnApplyWindowInsetsListener((view, insets) -> {
            int top;
            int bottom;
            int left;
            int right;
            if (Build.VERSION.SDK_INT >= 30) {
                android.graphics.Insets bars = insets.getInsets(WindowInsets.Type.systemBars());
                android.graphics.Insets ime = insets.getInsets(WindowInsets.Type.ime());
                top = bars.top;
                bottom = Math.max(bars.bottom, insets.isVisible(WindowInsets.Type.ime()) ? ime.bottom : 0);
                left = bars.left;
                right = bars.right;
            } else {
                //noinspection deprecation
                top = insets.getSystemWindowInsetTop();
                //noinspection deprecation
                bottom = insets.getSystemWindowInsetBottom();
                //noinspection deprecation
                left = insets.getSystemWindowInsetLeft();
                //noinspection deprecation
                right = insets.getSystemWindowInsetRight();
            }
            view.setPadding(left, top, right, bottom);
            if (web != null) {
                // CSS pixels are density-independent, so the page gets values it can use directly
                web.evaluateJavascript("document.documentElement.style.setProperty('--shell-top', '"
                        + pxToCss(top) + "px');document.documentElement.style.setProperty('--shell-bottom', '"
                        + pxToCss(bottom) + "px');", null);
            }
            return insets;
        });
    }

    @Override
    public void onRequestPermissionsResult(int requestCode, String[] permissions, int[] results) {
        super.onRequestPermissionsResult(requestCode, permissions, results);
        if (requestCode == REQ_WEB_PERMISSIONS) {
            boolean allGranted = results.length > 0;
            for (int result : results) {
                if (result != PackageManager.PERMISSION_GRANTED) {
                    allGranted = false;
                }
            }
            for (final PermissionRequest request : new ArrayList<>(pendingWebPermissions)) {
                runOnUiThread(() -> {
                    try {
                        if (allGranted) {
                            request.grant(request.getResources());
                        } else {
                            request.deny();
                        }
                    } catch (Exception ignored) {
                        // page navigated away
                    }
                });
            }
            pendingWebPermissions.clear();
        } else if (requestCode == REQ_RUNTIME_PERMISSIONS) {
            bridge.notifyPermissionResult(requestCode, permissions, results);
        }
    }

    @Override
    protected void onActivityResult(int requestCode, int resultCode, Intent data) {
        super.onActivityResult(requestCode, resultCode, data);
        if (requestCode != REQ_FILE_CHOOSER) {
            return;
        }
        ValueCallback<Uri[]> callback = pendingFileChooser;
        pendingFileChooser = null;
        if (callback == null) {
            return;
        }
        Uri[] uris = null;
        if (resultCode == RESULT_OK && data != null) {
            if (data.getClipData() != null) {
                int count = data.getClipData().getItemCount();
                uris = new Uri[count];
                for (int i = 0; i < count; i++) {
                    uris[i] = data.getClipData().getItemAt(i).getUri();
                }
            } else if (data.getData() != null) {
                uris = new Uri[]{data.getData()};
            }
        }
        callback.onReceiveValue(uris);
    }

    @Override
    protected void onSaveInstanceState(Bundle outState) {
        super.onSaveInstanceState(outState);
        if (web != null) {
            web.saveState(outState);
        }
    }

    @Override
    protected void onPause() {
        if (web != null) {
            web.onPause();
            web.pauseTimers();
        }
        super.onPause();
    }

    @Override
    protected void onResume() {
        super.onResume();
        if (web != null) {
            web.resumeTimers();
            web.onResume();
        }
        if (bridge != null) {
            bridge.pushStatus();
        }
    }

    @Override
    protected void onDestroy() {
        if (Build.VERSION.SDK_INT >= 33 && backCallback != null) {
            getOnBackInvokedDispatcher().unregisterOnBackInvokedCallback(backCallback);
            backCallback = null;
        }
        if (web != null) {
            root.removeView(web);
            web.destroy();
            web = null;
        }
        super.onDestroy();
    }

    // ------------------------------------------------------------------ helpers

    public boolean hasPermission(String permission) {
        return checkSelfPermission(permission) == PackageManager.PERMISSION_GRANTED;
    }

    public void requestRuntimePermissions(String[] permissions) {
        runOnUiThread(() -> requestPermissions(permissions, REQ_RUNTIME_PERMISSIONS));
    }

    public Prefs prefs() {
        return prefs;
    }

    public WebView webView() {
        return web;
    }

    public String currentUrl() {
        return currentUrl;
    }

    public void toast(final String message) {
        runOnUiThread(() -> Toast.makeText(MainActivity.this, message, Toast.LENGTH_SHORT).show());
    }

    /** density-independent pixels -> device pixels */
    private int dpToPx(int value) {
        float density = getResources().getDisplayMetrics().density;
        return Math.max(1, Math.round(value * density));
    }

    /** device pixels -> density-independent pixels (CSS px) */
    private int pxToCss(int value) {
        float density = getResources().getDisplayMetrics().density;
        return density <= 0f ? value : Math.round(value / density);
    }

    static String quote(String raw) {
        if (raw == null) {
            return "null";
        }
        StringBuilder sb = new StringBuilder(raw.length() + 16);
        sb.append('"');
        for (int i = 0; i < raw.length(); i++) {
            char c = raw.charAt(i);
            switch (c) {
                case '"':
                    sb.append("\\\"");
                    break;
                case '\\':
                    sb.append("\\\\");
                    break;
                case '\n':
                    sb.append("\\n");
                    break;
                case '\r':
                    sb.append("\\r");
                    break;
                case '\t':
                    sb.append("\\t");
                    break;
                default:
                    if (c < 0x20) {
                        sb.append(String.format(Locale.US, "\\u%04x", (int) c));
                    } else {
                        sb.append(c);
                    }
            }
        }
        sb.append('"');
        return sb.toString();
    }
}
