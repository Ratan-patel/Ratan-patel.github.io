package com.ratansec.superagent

import org.json.JSONArray
import org.json.JSONObject
import java.net.HttpURLConnection
import java.net.URL

/**
 * On-device AI agent. API key phone par hi rehti hai aur seedha provider ko jaati hai
 * (beech me koi server nahi). Tool calls phone par execute hote hain, scope check ke baad.
 */
class Agent(private val store: Store, private val secrets: Secrets) {

    fun interface Listener {
        fun onEvent(event: JSONObject)
    }

    @Volatile
    var cancelled: Boolean = false

    private val probes = Probes(store)

    class AgentError(message: String) : Exception(message)

    private fun emit(listener: Listener, type: String, body: JSONObject.() -> Unit = {}) {
        listener.onEvent(JSONObject().put("type", type).apply(body))
    }

    /** Poora agent turn: model → tool calls → model, maxSteps tak. */
    fun run(history: JSONArray, listener: Listener) {
        cancelled = false
        val key = secrets.get()
        val localProvider = store.baseUrl.startsWith("http://127.") ||
            store.baseUrl.startsWith("http://localhost") ||
            store.baseUrl.contains("11434")
        if (key.isEmpty() && !localProvider) {
            throw AgentError("API key set nahi hai. Settings tab me apni key daalo.")
        }

        val messages = JSONArray()
        messages.put(JSONObject().put("role", "system").put("content", systemPrompt()))
        for (i in 0 until history.length()) messages.put(history.getJSONObject(i))

        var step = 0
        while (step < store.maxSteps) {
            if (cancelled) { emit(listener, "cancelled"); return }
            step += 1
            emit(listener, "step") { put("step", step); put("max", store.maxSteps) }

            val reply = chat(messages, key)
            val choice = reply.optJSONArray("choices")?.optJSONObject(0)
                ?: throw AgentError("Provider ne khali response bheja.")
            val message = choice.optJSONObject("message")
                ?: throw AgentError("Provider response me message nahi mila.")
            messages.put(message)

            val toolCalls = message.optJSONArray("tool_calls")
            if (toolCalls == null || toolCalls.length() == 0) {
                val text = message.optString("content").ifEmpty { "(model ne khali reply diya)" }
                emit(listener, "answer") { put("text", text); put("steps", step) }
                return
            }

            for (i in 0 until toolCalls.length()) {
                if (cancelled) { emit(listener, "cancelled"); return }
                val call = toolCalls.getJSONObject(i)
                val id = call.optString("id", "call_$i")
                val function = call.optJSONObject("function") ?: continue
                val name = function.optString("name")
                val arguments = runCatching {
                    JSONObject(function.optString("arguments", "{}"))
                }.getOrElse { JSONObject() }

                emit(listener, "tool") { put("name", name); put("args", arguments) }
                val output = runTool(name, arguments)
                emit(listener, "tool_result") { put("name", name); put("result", output) }

                messages.put(
                    JSONObject()
                        .put("role", "tool")
                        .put("tool_call_id", id)
                        .put("content", output.toString())
                )
            }
        }
        emit(listener, "answer") {
            put("text", "Step limit (${store.maxSteps}) poori hui. Aur detail ke liye dobara poocho ya Settings me steps badhao.")
            put("steps", step)
        }
    }

    private fun systemPrompt(): String {
        val targets = store.targets()
        val scope = if (targets.isEmpty()) "(koi target authorized nahi hai)"
        else targets.joinToString(", ") { it.host }
        return """
            You are RatanSec Agent, an on-device application-security assistant running inside an
            Android app. You help a professional perform AUTHORIZED security assessments.

            Rules:
            - Only test hosts listed in the authorized scope below. If a host is not in scope, say so
              and ask the user to add it in the Scope tab with written permission. Never try to bypass this.
            - Available tools are bounded and non-destructive: DNS resolution, response-header review,
              TLS certificate review, and two well-known public text files. You cannot run shell commands,
              exploit anything, brute force, or scan ports.
            - Call tools to gather real evidence before making claims. Never invent findings.
            - Report each observation with severity, the concrete evidence you saw, and a concrete fix.
            - Be concise and practical. Reply in the user's language (Hinglish if they write Hinglish).
            - If the user asks for something outside authorized assessment (malware, credential theft,
              attacking systems they do not own), refuse briefly and offer the defensive alternative.

            Authorized scope: $scope
        """.trimIndent()
    }

    private fun runTool(name: String, args: JSONObject): JSONObject = try {
        when (name) {
            "dns_lookup" -> probes.dns(Store.normalizeHost(args.optString("host")))
            "http_headers" -> probes.httpHeaders(args.optString("target"))
            "tls_inspect" -> probes.tls(Store.normalizeHost(args.optString("host")))
            "security_txt" -> probes.textFile(args.optString("target"), "security_txt")
            "robots_txt" -> probes.textFile(args.optString("target"), "robots")
            "list_scope" -> JSONObject().put("status", "ok").put("data", JSONObject().put("targets", store.targetsJson()))
            else -> JSONObject().put("status", "error").put("error", "Unknown tool: $name")
        }
    } catch (exc: Probes.ProbeError) {
        JSONObject().put("status", "blocked").put("error", exc.message ?: "Blocked by policy.")
    } catch (exc: Exception) {
        JSONObject().put("status", "error").put("error", exc.message ?: exc.javaClass.simpleName)
    }

    // --- Provider transport ------------------------------------------------
    private fun chat(messages: JSONArray, key: String): JSONObject {
        val base = store.baseUrl.trimEnd('/')
        if (!base.startsWith("https://") && !base.startsWith("http://")) {
            throw AgentError("Base URL http:// ya https:// se shuru hona chahiye.")
        }
        val payload = JSONObject()
            .put("model", store.model)
            .put("messages", messages)
            .put("tools", tools())
            .put("tool_choice", "auto")
            .put("temperature", 0.2)
            .put("max_tokens", 1800)
            .put("stream", false)

        val connection = URL("$base/chat/completions").openConnection() as HttpURLConnection
        try {
            connection.requestMethod = "POST"
            connection.connectTimeout = 30_000
            connection.readTimeout = 120_000
            connection.instanceFollowRedirects = false
            connection.doOutput = true
            connection.setRequestProperty("Content-Type", "application/json")
            connection.setRequestProperty("Accept", "application/json")
            connection.setRequestProperty("User-Agent", "RatanSecAgent/${Store.VERSION}")
            if (key.isNotEmpty()) connection.setRequestProperty("Authorization", "Bearer $key")
            if (store.provider == "openrouter") {
                connection.setRequestProperty("HTTP-Referer", "https://ratan-patel.github.io/")
                connection.setRequestProperty("X-Title", "RatanSec Agent")
            }
            connection.outputStream.use { it.write(payload.toString().toByteArray(Charsets.UTF_8)) }

            val code = connection.responseCode
            if (code !in 200..299) {
                // Provider body me key echo ho sakti hai — sirf status + short hint dete hain.
                val hint = when (code) {
                    401, 403 -> "API key galat ya expired hai (Settings me check karo)."
                    404 -> "Base URL ya model galat hai."
                    429 -> "Rate limit / credit khatam. Thodi der baad try karo."
                    else -> "Provider ne error diya."
                }
                throw AgentError("HTTP $code — $hint")
            }
            val text = connection.inputStream.use { stream ->
                val buffer = ByteArray(2_000_000)
                val read = stream.read(buffer)
                if (read <= 0) "" else String(buffer, 0, read, Charsets.UTF_8)
            }
            if (text.isEmpty()) throw AgentError("Provider ne khali body bheji.")
            return runCatching { JSONObject(text) }.getOrElse {
                throw AgentError("Provider ka response JSON nahi tha.")
            }
        } finally {
            connection.disconnect()
        }
    }

    /** Key verify karne ke liye chhota call (Settings ka "Test" button). */
    fun testConnection(): JSONObject {
        val key = secrets.get()
        val messages = JSONArray().put(
            JSONObject().put("role", "user").put("content", "Reply with the single word: ready")
        )
        val base = store.baseUrl.trimEnd('/')
        val payload = JSONObject()
            .put("model", store.model)
            .put("messages", messages)
            .put("max_tokens", 8)
            .put("stream", false)
        val connection = URL("$base/chat/completions").openConnection() as HttpURLConnection
        try {
            connection.requestMethod = "POST"
            connection.connectTimeout = 20_000
            connection.readTimeout = 45_000
            connection.instanceFollowRedirects = false
            connection.doOutput = true
            connection.setRequestProperty("Content-Type", "application/json")
            if (key.isNotEmpty()) connection.setRequestProperty("Authorization", "Bearer $key")
            if (store.provider == "openrouter") {
                connection.setRequestProperty("HTTP-Referer", "https://ratan-patel.github.io/")
                connection.setRequestProperty("X-Title", "RatanSec Agent")
            }
            connection.outputStream.use { it.write(payload.toString().toByteArray(Charsets.UTF_8)) }
            val code = connection.responseCode
            if (code !in 200..299) {
                val hint = when (code) {
                    401, 403 -> "Key reject hui — check karo."
                    404 -> "Base URL / model galat."
                    429 -> "Rate limit ya credit khatam."
                    else -> "Provider error."
                }
                return JSONObject().put("ok", false).put("message", "HTTP $code — $hint")
            }
            return JSONObject().put("ok", true).put("message", "Connected — ${store.model}")
        } catch (exc: Exception) {
            return JSONObject().put("ok", false).put("message", exc.message ?: "Connection fail")
        } finally {
            connection.disconnect()
        }
    }

    private fun tools(): JSONArray {
        fun tool(name: String, description: String, param: String, paramDesc: String): JSONObject =
            JSONObject()
                .put("type", "function")
                .put(
                    "function", JSONObject()
                        .put("name", name)
                        .put("description", description)
                        .put(
                            "parameters", JSONObject()
                                .put("type", "object")
                                .put("properties", JSONObject().put(param, JSONObject().put("type", "string").put("description", paramDesc)))
                                .put("required", JSONArray().put(param))
                        )
                )

        return JSONArray()
            .put(tool("dns_lookup", "Resolve a hostname to IP addresses (authorized hosts only).", "host", "Hostname, e.g. example.com"))
            .put(tool("http_headers", "Fetch HTTP response headers for an authorized URL and review security posture.", "target", "Full URL, e.g. https://example.com"))
            .put(tool("tls_inspect", "Inspect the TLS certificate and negotiated protocol of an authorized host.", "host", "Hostname, e.g. example.com"))
            .put(tool("security_txt", "Read /.well-known/security.txt of an authorized site.", "target", "Full URL of the site"))
            .put(tool("robots_txt", "Read /robots.txt of an authorized site.", "target", "Full URL of the site"))
            .put(
                JSONObject().put("type", "function").put(
                    "function", JSONObject()
                        .put("name", "list_scope")
                        .put("description", "List hosts the user has authorized for testing.")
                        .put("parameters", JSONObject().put("type", "object").put("properties", JSONObject()))
                )
            )
    }
}
