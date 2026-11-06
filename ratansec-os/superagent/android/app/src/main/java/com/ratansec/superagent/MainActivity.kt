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

/**
 * RatanSec Super Agent — Android shell.
 *
 * App ek secure WebView hai jo aapke self-hosted Super Agent server ko kholta hai.
 * APK ke andar bundle kiya gaya web console (assets/web/mobile.html) turant khulta hai
 * aur wahi se server URL + token set hota hai.
 *
 * AndroidManifest ke network_security_config se http (LAN/VPS) allowed hai; HTTPS recommended.
 */
class MainActivity : AppCompatActivity() {

    private lateinit var webView: WebView
    private lateinit var loadingBar: ProgressBar
    private val prefs by lazy { getSharedPreferences("superagent", MODE_PRIVATE) }
    private val localOrigin = "https://appassets.androidplatform.net"
    private val localConsole = "$localOrigin/assets/web/mobile.html"

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
                mixedContentMode = WebSettings.MIXED_CONTENT_ALWAYS_ALLOW
                cacheMode = WebSettings.LOAD_DEFAULT
                userAgentString = "$userAgentString RatanSecSuperAgent/1.0"
                mediaPlaybackRequiresUserGesture = true
                setSupportZoom(false)
            }
            addJavascriptInterface(Bridge(), "AndroidAgent")
            webViewClient = object : WebViewClient() {
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
        val token = data.getQueryParameter("token")
        prefs.edit().putString("server", server).apply()
        if (!token.isNullOrBlank()) prefs.edit().putString("token", token).apply()
    }

    private fun loadConsole() {
        webView.loadUrl(localConsole)
    }

    /** Server URL normalize: trailing slash hata do, scheme add karo, /mobile lagao. */
    private fun normalizeServer(raw: String): String {
        var s = raw.trim()
        if (s.isEmpty()) return ""
        if (!s.startsWith("http://") && !s.startsWith("https://")) {
            s = if (s.startsWith("localhost") || s.startsWith("127.") || s.startsWith("10.") ||
                s.startsWith("192.168.") || s.contains(":8") || s.contains(":3")) "http://$s" else "https://$s"
        }
        s = s.trimEnd('/')
        if (s.endsWith("/mobile")) s = s.removeSuffix("/mobile")
        return if (s.endsWith("/mobile.html")) s else "$s/mobile"
    }

    private fun openServer(raw: String) {
        val url = normalizeServer(raw)
        if (url.isEmpty()) return
        val token = prefs.getString("token", "") ?: ""
        // token ek baar URL se console ko de do (phir localStorage me rehta hai)
        val full = if (token.isNotBlank()) "$url?token=${Uri.encode(token)}" else url
        webView.loadUrl(full)
    }

    private fun isAgentHost(url: String): Boolean {
        val saved = prefs.getString("server", null) ?: return false
        return url.startsWith(saved.trimEnd('/')) || url.contains(saved.trimEnd('/'))
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

    /** Server + token ka setup dialog (native, WebView ke bahar). */
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
        val tokenInput = EditText(this).apply {
            hint = "SUPERAGENT_MOBILE_TOKEN"
            inputType = InputType.TYPE_CLASS_TEXT or InputType.TYPE_TEXT_VARIATION_PASSWORD
            setText(prefs.getString("token", ""))
            setTextColor(Color.WHITE)
        }
        layout.addView(TextView(this).apply {
            text = "Server URL"
            setTextColor(Color.parseColor("#8B9BB4"))
            textSize = 12f
        })
        layout.addView(serverInput)
        layout.addView(TextView(this).apply {
            text = "\nMobile token (SUPERAGENT_MOBILE_TOKEN)"
            setTextColor(Color.parseColor("#8B9BB4"))
            textSize = 12f
        })
        layout.addView(tokenInput)

        AlertDialog.Builder(this)
            .setTitle("Super Agent connect karo")
            .setView(layout)
            .setPositiveButton("Connect") { _, _ ->
                val server = serverInput.text.toString()
                val token = tokenInput.text.toString()
                prefs.edit().putString("server", server).putString("token", token).apply()
                if (server.isBlank()) {
                    Toast.makeText(this, "Server URL daalo", Toast.LENGTH_SHORT).show()
                } else {
                    openServer(server)
                }
            }
            .setNeutralButton("Demo console") { _, _ -> loadConsole() }
            .setNegativeButton("Cancel", null)
            .show()
    }

    override fun onBackPressed() {
        when {
            webView.canGoBack() -> webView.goBack()
            else -> super.onBackPressed()
        }
    }

    /** JS bridge: console ke menu se native setup / exit. */
    inner class Bridge {
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
