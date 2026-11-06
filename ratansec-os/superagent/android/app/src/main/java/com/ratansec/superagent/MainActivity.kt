package com.ratansec.superagent

import android.annotation.SuppressLint
import android.app.AlertDialog
import android.content.Intent
import android.graphics.Color
import android.net.Uri
import android.os.Bundle
import android.view.ViewGroup
import android.webkit.JavascriptInterface
import android.webkit.WebChromeClient
import android.webkit.WebResourceRequest
import android.webkit.WebResourceResponse
import android.webkit.WebSettings
import android.webkit.WebView
import android.webkit.WebViewClient
import android.widget.LinearLayout
import android.widget.ProgressBar
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import androidx.webkit.WebViewAssetLoader
import org.json.JSONArray
import org.json.JSONObject
import java.util.concurrent.Executors

/**
 * RatanSec Agent v3 — standalone. Koi server nahi chahiye.
 *
 * UI app ke andar bundled hai (assets/app/). API key Android Keystore me encrypt hokar
 * rehti hai aur native code hi provider ko bhejta hai — JS ko key kabhi nahi milti.
 * Tools (DNS/headers/TLS) phone par hi chalte hain, scope check ke baad.
 */
class MainActivity : AppCompatActivity() {

    private lateinit var webView: WebView
    private lateinit var loadingBar: ProgressBar
    private lateinit var store: Store
    private lateinit var secrets: Secrets
    private lateinit var agent: Agent

    private val worker = Executors.newSingleThreadExecutor()
    private val localOrigin = "https://appassets.androidplatform.net"

    private val assetLoader by lazy {
        WebViewAssetLoader.Builder()
            .setDomain("appassets.androidplatform.net")
            .addPathHandler("/assets/", WebViewAssetLoader.AssetsPathHandler(this))
            .build()
    }

    @SuppressLint("SetJavaScriptEnabled")
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        store = Store(this)
        secrets = Secrets(this)
        agent = Agent(store, secrets)

        val root = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setBackgroundColor(Color.parseColor("#070B12"))
            layoutParams = ViewGroup.LayoutParams(MATCH, MATCH)
        }
        loadingBar = ProgressBar(this, null, android.R.attr.progressBarStyleHorizontal).apply {
            isIndeterminate = true
            visibility = android.view.View.GONE
        }
        webView = WebView(this).apply {
            layoutParams = LinearLayout.LayoutParams(MATCH, 0, 1f)
            setBackgroundColor(Color.parseColor("#070B12"))
            settings.apply {
                javaScriptEnabled = true
                domStorageEnabled = true
                allowFileAccess = false
                allowContentAccess = false
                mixedContentMode = WebSettings.MIXED_CONTENT_NEVER_ALLOW
                cacheMode = WebSettings.LOAD_NO_CACHE
                userAgentString = "$userAgentString RatanSecAgent/${Store.VERSION}"
                setSupportZoom(false)
            }
            addJavascriptInterface(Bridge(), "Native")
            webViewClient = object : WebViewClient() {
                override fun shouldInterceptRequest(view: WebView, request: WebResourceRequest): WebResourceResponse? =
                    assetLoader.shouldInterceptRequest(request.url)

                override fun shouldOverrideUrlLoading(view: WebView, request: WebResourceRequest): Boolean {
                    val host = request.url.host ?: ""
                    if (host == "appassets.androidplatform.net") return false
                    // Bahar ke links browser me — WebView me sirf bundled UI chalti hai.
                    runCatching { startActivity(Intent(Intent.ACTION_VIEW, request.url)) }
                    return true
                }

                override fun onPageFinished(view: WebView, url: String) {
                    loadingBar.visibility = android.view.View.GONE
                }
            }
            webChromeClient = object : WebChromeClient() {
                override fun onProgressChanged(view: WebView, newProgress: Int) {
                    loadingBar.visibility =
                        if (newProgress in 1..99) android.view.View.VISIBLE else android.view.View.GONE
                }
            }
        }
        root.addView(loadingBar)
        root.addView(webView)
        setContentView(root)

        webView.loadUrl("$localOrigin/assets/app/index.html")
    }

    private fun send(event: JSONObject) {
        val payload = JSONObject.quote(event.toString())
        runOnUiThread {
            webView.evaluateJavascript("window.onNativeEvent && window.onNativeEvent($payload)", null)
        }
    }

    private fun toast(message: String) {
        runOnUiThread { Toast.makeText(this, message, Toast.LENGTH_SHORT).show() }
    }

    /** JS bridge. Key sirf native side par rehti hai. */
    inner class Bridge {

        @JavascriptInterface
        fun settings(): String = store.settingsJson(secrets.has()).toString()

        @JavascriptInterface
        fun saveSettings(json: String): String = runCatching {
            val value = JSONObject(json)
            if (value.has("base_url")) {
                val url = value.optString("base_url").trim().trimEnd('/')
                require(url.startsWith("https://") || url.startsWith("http://")) {
                    "Base URL http:// ya https:// se shuru hona chahiye."
                }
                store.baseUrl = url
            }
            if (value.has("model")) {
                val model = value.optString("model").trim()
                require(model.isNotEmpty()) { "Model khali nahi ho sakta." }
                store.model = model
            }
            if (value.has("provider")) store.provider = value.optString("provider")
            if (value.has("max_steps")) store.maxSteps = value.optInt("max_steps", 6)
            if (value.has("allow_private")) store.allowPrivate = value.optBoolean("allow_private", false)
            JSONObject().put("ok", true).put("settings", store.settingsJson(secrets.has())).toString()
        }.getOrElse { JSONObject().put("ok", false).put("message", it.message ?: "Save fail").toString() }

        /** Key native Keystore me jaati hai; JS ko wapas nahi milti. */
        @JavascriptInterface
        fun saveKey(key: String): String = runCatching {
            secrets.put(key.trim())
            JSONObject().put("ok", true).put("has_key", secrets.has()).toString()
        }.getOrElse { JSONObject().put("ok", false).put("message", "Key save nahi hui: ${it.message}").toString() }

        @JavascriptInterface
        fun clearKey(): String {
            secrets.clear()
            return JSONObject().put("ok", true).put("has_key", false).toString()
        }

        @JavascriptInterface
        fun targets(): String = store.targetsJson().toString()

        @JavascriptInterface
        fun addTarget(host: String, note: String, days: Int): String = runCatching {
            val target = store.addTarget(host, note, days)
            JSONObject().put("ok", true).put("host", target.host).put("targets", store.targetsJson()).toString()
        }.getOrElse { JSONObject().put("ok", false).put("message", it.message ?: "Add fail").toString() }

        @JavascriptInterface
        fun removeTarget(host: String): String {
            store.removeTarget(host)
            return JSONObject().put("ok", true).put("targets", store.targetsJson()).toString()
        }

        @JavascriptInterface
        fun testConnection() {
            worker.execute {
                val result = runCatching { agent.testConnection() }
                    .getOrElse { JSONObject().put("ok", false).put("message", it.message ?: "Test fail") }
                send(JSONObject().put("type", "test_result").put("result", result))
            }
        }

        /** Agent turn background thread par; events JS ko jaate hain. */
        @JavascriptInterface
        fun chat(historyJson: String) {
            worker.execute {
                try {
                    val history = JSONArray(historyJson)
                    agent.run(history) { event -> send(event) }
                    send(JSONObject().put("type", "done"))
                } catch (exc: Exception) {
                    send(JSONObject().put("type", "error").put("message", exc.message ?: "Agent fail"))
                    send(JSONObject().put("type", "done"))
                }
            }
        }

        @JavascriptInterface
        fun stop() {
            agent.cancelled = true
        }

        /** Direct probe (Scope tab ka "Run checks" button). */
        @JavascriptInterface
        fun runChecks(host: String) {
            worker.execute {
                val clean = Store.normalizeHost(host)
                val probes = Probes(store)
                val results = JSONArray()
                if (store.authorized(clean) == null) {
                    send(JSONObject().put("type", "error").put("message", "'$clean' scope me nahi hai."))
                    send(JSONObject().put("type", "done"))
                    return@execute
                }
                val target = "https://$clean"
                listOf(
                    { probes.dns(clean) },
                    { probes.httpHeaders(target) },
                    { probes.tls(clean) },
                    { probes.textFile(target, "security_txt") }
                ).forEach { probe ->
                    val result = runCatching { probe() }.getOrElse {
                        JSONObject().put("status", "blocked").put("error", it.message ?: "Blocked")
                    }
                    results.put(result)
                    send(JSONObject().put("type", "tool_result").put("name", result.optString("id", "check")).put("result", result))
                }
                send(JSONObject().put("type", "checks_done").put("results", results))
                send(JSONObject().put("type", "done"))
            }
        }

        @JavascriptInterface
        fun exportReport(text: String) {
            runOnUiThread {
                val intent = Intent(Intent.ACTION_SEND).apply {
                    type = "text/plain"
                    putExtra(Intent.EXTRA_SUBJECT, "RatanSec Agent — assessment notes")
                    putExtra(Intent.EXTRA_TEXT, text)
                }
                runCatching { startActivity(Intent.createChooser(intent, "Report share karo")) }
                    .onFailure { toast("Share app nahi mili.") }
            }
        }

        @JavascriptInterface
        fun toast(message: String) = this@MainActivity.toast(message)

        @JavascriptInterface
        fun openUrl(url: String) {
            runCatching { startActivity(Intent(Intent.ACTION_VIEW, Uri.parse(url))) }
        }

        @JavascriptInterface
        fun confirmExit(): Boolean {
            runOnUiThread {
                AlertDialog.Builder(this@MainActivity)
                    .setTitle("App band karein?")
                    .setPositiveButton("Haan") { _, _ -> finish() }
                    .setNegativeButton("Nahi", null)
                    .show()
            }
            return true
        }
    }

    @Deprecated("Deprecated in Java")
    override fun onBackPressed() {
        if (webView.canGoBack()) webView.goBack() else super.onBackPressed()
    }

    override fun onDestroy() {
        worker.shutdownNow()
        super.onDestroy()
    }

    companion object {
        private const val MATCH = ViewGroup.LayoutParams.MATCH_PARENT
    }
}
