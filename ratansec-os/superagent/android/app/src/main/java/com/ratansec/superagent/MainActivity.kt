package com.ratansec.superagent

import android.annotation.SuppressLint
import android.app.AlertDialog
import android.content.Intent
import android.graphics.Color
import android.net.Uri
import android.os.Bundle
import android.text.InputType
import android.view.Gravity
import android.view.ViewGroup
import android.webkit.JavascriptInterface
import android.webkit.WebChromeClient
import android.webkit.WebResourceError
import android.webkit.WebResourceRequest
import android.webkit.WebResourceResponse
import android.webkit.WebSettings
import android.webkit.WebView
import android.webkit.WebViewClient
import android.widget.Button
import android.widget.EditText
import android.widget.LinearLayout
import android.widget.ProgressBar
import android.widget.TextView
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import androidx.webkit.WebViewAssetLoader

/**
 * RatanSec Super Agent — Android shell.
 *
 * App ek secure WebView hai jo aapke self-hosted Super Agent server ko kholta hai.
 * APK ke andar bundle kiya gaya web console (assets/web/connect.html) turant khulta hai
 * aur wahi se server URL set hota hai. Login server ke console par hota hai.
 *
 * AndroidManifest ke network_security_config se http (LAN/VPS) allowed hai; HTTPS recommended.
 */
class MainActivity : AppCompatActivity() {

    private lateinit var webView: WebView
    private lateinit var loadingBar: ProgressBar
    private val prefs by lazy { getSharedPreferences("superagent", MODE_PRIVATE) }
    private val localOrigin = "https://appassets.androidplatform.net"
    private val localConsole = "$localOrigin/assets/web/connect.html"

    /**
     * Bundled connect screen ko https://appassets.androidplatform.net/assets/... par serve karta hai.
     * Iske bina local URL resolve nahi hota (net::ERR_NAME_NOT_RESOLVED) aur app khali khulti hai.
     */
    private val assetLoader by lazy {
        WebViewAssetLoader.Builder()
            .setDomain("appassets.androidplatform.net")
            .addPathHandler("/assets/", WebViewAssetLoader.AssetsPathHandler(this))
            .build()
    }

    @SuppressLint("SetJavaScriptEnabled")
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        val root = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setBackgroundColor(Color.parseColor("#05070D"))
            layoutParams = ViewGroup.LayoutParams(MATCH, MATCH)
        }

        loadingBar = ProgressBar(this, null, android.R.attr.progressBarStyleHorizontal).apply {
            isIndeterminate = true
            visibility = android.view.View.GONE
        }

        webView = WebView(this).apply {
            layoutParams = LinearLayout.LayoutParams(MATCH, 0, 1f)
            setBackgroundColor(Color.parseColor("#05070D"))
            settings.apply {
                javaScriptEnabled = true
                domStorageEnabled = true
                databaseEnabled = true
                allowFileAccess = false
                allowContentAccess = false
                mixedContentMode = WebSettings.MIXED_CONTENT_NEVER_ALLOW
                cacheMode = WebSettings.LOAD_DEFAULT
                userAgentString = "$userAgentString RatanSecSuperAgent/2.0"
                mediaPlaybackRequiresUserGesture = true
                setSupportZoom(false)
            }
            addJavascriptInterface(Bridge(), "AndroidAgent")
            webViewClient = object : WebViewClient() {
                override fun shouldInterceptRequest(view: WebView, request: WebResourceRequest): WebResourceResponse? {
                    // Local (bundled) console ke liye assets serve karo; baaki requests normal network se.
                    return assetLoader.shouldInterceptRequest(request.url)
                }

                override fun shouldOverrideUrlLoading(view: WebView, request: WebResourceRequest): Boolean {
                    val url = request.url.toString()
                    val host = request.url.host ?: ""
                    // external links browser me kholo
                    if (!host.endsWith("androidplatform.net") && !isAgentHost(url)) {
                        startActivity(Intent(Intent.ACTION_VIEW, request.url))
                        return true
                    }
                    return false
                }

                override fun onPageFinished(view: WebView, url: String) {
                    super.onPageFinished(view, url)
                    loadingBar.visibility = android.view.View.GONE
                }

                override fun onReceivedError(view: WebView, request: WebResourceRequest, error: WebResourceError) {
                    super.onReceivedError(view, request, error)
                    if (request.isForMainFrame) showConnectError()
                }
            }
            webChromeClient = object : WebChromeClient() {
                override fun onProgressChanged(view: WebView, newProgress: Int) {
                    loadingBar.progress = newProgress
                    loadingBar.visibility = if (newProgress in 1..99) android.view.View.VISIBLE else android.view.View.GONE
                }
            }
        }

        root.addView(loadingBar)
        root.addView(webView)
        setContentView(root)

        handleDeepLink(intent)
        val saved = prefs.getString("server", null)
        loadConsole()
        if (saved != null) {
            webView.postDelayed({ openServer(saved) }, 350)
        }
    }

    override fun onNewIntent(intent: Intent) {
        super.onNewIntent(intent)
        handleDeepLink(intent)
    }

    private fun handleDeepLink(intent: Intent?) {
        val data: Uri = intent?.data ?: return
        val server = data.getQueryParameter("server") ?: return
        val origin = normalizeOrigin(server)
        if (origin.isNotEmpty()) prefs.edit().putString("server", origin).apply()
    }

    private fun loadConsole() {
        webView.loadUrl(localConsole)
    }

    /**
     * Server URL se sirf origin nikalta hai (scheme + host + port).
     * Path/query/fragment ignore — token ya credentials URL me kabhi nahi bheje jate.
     */
    private fun normalizeOrigin(raw: String): String {
        var s = raw.trim()
        if (s.isEmpty()) return ""
        if (!s.startsWith("http://") && !s.startsWith("https://")) {
            val local = Regex("^(localhost|127\\.|10\\.|192\\.168\\.|172\\.(1[6-9]|2\\d|3[01])\\.)")
            s = if (local.containsMatchIn(s)) "http://$s" else "https://$s"
        }
        val uri = runCatching { Uri.parse(s) }.getOrNull() ?: return ""
        val host = uri.host ?: return ""
        val scheme = uri.scheme ?: return ""
        if (scheme != "http" && scheme != "https") return ""
        if (!uri.userInfo.isNullOrEmpty()) return ""
        return if (uri.port != -1) "$scheme://$host:${uri.port}" else "$scheme://$host"
    }

    /** Origin save karke app ke andar hi console kholta hai. */
    private fun openServer(raw: String) {
        val origin = normalizeOrigin(raw)
        if (origin.isEmpty()) {
            Toast.makeText(this, "Invalid server URL", Toast.LENGTH_SHORT).show()
            return
        }
        prefs.edit().putString("server", origin).apply()
        // v2: token URL/query mein nahi bheja jata; login server ke console par hota hai.
        webView.loadUrl("$origin/mobile")
    }

    /** Sirf saved server origin ke links app ke andar khulte hain; baaki external browser me. */
    private fun isAgentHost(url: String): Boolean {
        val saved = prefs.getString("server", null) ?: return false
        val origin = normalizeOrigin(saved)
        if (origin.isEmpty()) return false
        return normalizeOrigin(url) == origin
    }

    private fun showConnectError() {
        AlertDialog.Builder(this)
            .setTitle("Connect nahi ho paya")
            .setMessage(
                "Server address check karo.\n\n" +
                    "· Laptop/VPS par: uvicorn superagent.webui:app --host 0.0.0.0 --port 8000\n" +
                    "· Phone aur server same Wi-Fi par hone chahiye\n" +
                    "· URL: http://192.168.x.x:8000"
            )
            .setPositiveButton("Retry") { _, _ -> loadConsole() }
            .setNegativeButton("Settings") { _, _ -> showSetup() }
            .setNeutralButton("Close") { _, _ -> finish() }
            .show()
    }

    /** Server URL setup dialog (login server console par hota hai). */
    private fun showSetup() {
        val layout = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(48, 24, 48, 8)
        }
        val serverInput = EditText(this).apply {
            hint = "http://192.168.1.5:8000"
            inputType = InputType.TYPE_TEXT_VARIATION_URI
            setText(prefs.getString("server", ""))
            setTextColor(Color.WHITE)
        }
        layout.addView(TextView(this).apply {
            text = "Server URL"
            setTextColor(Color.parseColor("#8B9BB4"))
            textSize = 12f
        })
        layout.addView(serverInput)

        AlertDialog.Builder(this)
            .setTitle("Super Agent connect karo")
            .setView(layout)
            .setPositiveButton("Connect") { _, _ ->
                val server = serverInput.text.toString()
                prefs.edit().putString("server", server).apply()
                if (server.isBlank()) {
                    Toast.makeText(this, "Server URL daalo", Toast.LENGTH_SHORT).show()
                } else {
                    openServer(server)
                }
            }
            .setNeutralButton("Connect screen") { _, _ -> loadConsole() }
            .setNegativeButton("Cancel", null)
            .show()
    }

    override fun onBackPressed() {
        when {
            webView.canGoBack() -> webView.goBack()
            else -> super.onBackPressed()
        }
    }

    /** JS bridge: bundled connect screen se server open karna + native setup / exit. */
    inner class Bridge {
        /**
         * connect.js isko call karta hai: origin native prefs me save hota hai aur console
         * app ke andar hi khulta hai (external browser me nahi).
         */
        @JavascriptInterface
        fun openServer(url: String) = runOnUiThread { this@MainActivity.openServer(url) }

        @JavascriptInterface
        fun setup() = runOnUiThread { showSetup() }

        @JavascriptInterface
        fun serverUrl(): String = prefs.getString("server", "") ?: ""

        @JavascriptInterface
        fun reload() = runOnUiThread { webView.reload() }

        @JavascriptInterface
        fun toast(message: String) = runOnUiThread {
            Toast.makeText(this@MainActivity, message, Toast.LENGTH_SHORT).show()
        }
    }

    companion object {
        private const val MATCH = ViewGroup.LayoutParams.MATCH_PARENT
    }
}
