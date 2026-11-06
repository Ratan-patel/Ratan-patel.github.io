package com.ratansec.superagent

import android.content.Context
import android.content.SharedPreferences
import org.json.JSONArray
import org.json.JSONObject

/**
 * On-device settings + authorization scope. Sab kuch phone par hi rehta hai.
 * API key yahan NAHI hai — woh [Secrets] (Keystore-encrypted) me hai.
 */
class Store(context: Context) {

    private val prefs: SharedPreferences =
        context.getSharedPreferences("ratansec_store", Context.MODE_PRIVATE)

    // --- Provider settings -------------------------------------------------
    var baseUrl: String
        get() = prefs.getString("base_url", DEFAULT_BASE_URL) ?: DEFAULT_BASE_URL
        set(value) { prefs.edit().putString("base_url", value.trim().trimEnd('/')).apply() }

    var model: String
        get() = prefs.getString("model", DEFAULT_MODEL) ?: DEFAULT_MODEL
        set(value) { prefs.edit().putString("model", value.trim()).apply() }

    var provider: String
        get() = prefs.getString("provider", "openrouter") ?: "openrouter"
        set(value) { prefs.edit().putString("provider", value.trim()).apply() }

    var maxSteps: Int
        get() = prefs.getInt("max_steps", 6).coerceIn(1, 12)
        set(value) { prefs.edit().putInt("max_steps", value.coerceIn(1, 12)).apply() }

    var allowPrivate: Boolean
        get() = prefs.getBoolean("allow_private", false)
        set(value) { prefs.edit().putBoolean("allow_private", value).apply() }

    // --- Authorization scope (RoE) ----------------------------------------
    /** Authorized targets: user ne likhit permission confirm ki hai. */
    fun targets(): List<Target> {
        val raw = prefs.getString("targets", "[]") ?: "[]"
        val out = mutableListOf<Target>()
        runCatching {
            val array = JSONArray(raw)
            for (i in 0 until array.length()) {
                val item = array.optJSONObject(i) ?: continue
                val host = item.optString("host").trim().lowercase()
                if (host.isEmpty()) continue
                if (item.optLong("expires", 0) < System.currentTimeMillis()) continue
                out.add(
                    Target(
                        host = host,
                        note = item.optString("note"),
                        added = item.optLong("added", 0),
                        expires = item.optLong("expires", 0)
                    )
                )
            }
        }
        return out
    }

    fun addTarget(host: String, note: String, days: Int): Target {
        val clean = normalizeHost(host)
        require(clean.isNotEmpty()) { "Host khali hai." }
        require(note.trim().length >= 8) { "Authorization note kam se kam 8 characters ka ho." }
        val now = System.currentTimeMillis()
        val target = Target(clean, note.trim(), now, now + days.coerceIn(1, 90) * 86_400_000L)
        val kept = targets().filter { it.host != clean } + target
        saveTargets(kept)
        return target
    }

    fun removeTarget(host: String) {
        saveTargets(targets().filter { it.host != host.lowercase() })
    }

    private fun saveTargets(items: List<Target>) {
        val array = JSONArray()
        items.forEach {
            array.put(
                JSONObject()
                    .put("host", it.host)
                    .put("note", it.note)
                    .put("added", it.added)
                    .put("expires", it.expires)
            )
        }
        prefs.edit().putString("targets", array.toString()).apply()
    }

    /** Exact host ya uske subdomain par hi permission milti hai. */
    fun authorized(host: String): Target? {
        val clean = host.trim().lowercase().trimEnd('.')
        if (clean.isEmpty()) return null
        return targets().firstOrNull { it.host == clean || clean.endsWith("." + it.host) }
    }

    fun settingsJson(hasKey: Boolean): JSONObject = JSONObject()
        .put("base_url", baseUrl)
        .put("model", model)
        .put("provider", provider)
        .put("max_steps", maxSteps)
        .put("allow_private", allowPrivate)
        .put("has_key", hasKey)
        .put("version", VERSION)

    fun targetsJson(): JSONArray {
        val array = JSONArray()
        targets().forEach {
            array.put(
                JSONObject()
                    .put("host", it.host)
                    .put("note", it.note)
                    .put("added", it.added)
                    .put("expires", it.expires)
            )
        }
        return array
    }

    data class Target(val host: String, val note: String, val added: Long, val expires: Long)

    companion object {
        const val VERSION = "3.0.0"
        const val DEFAULT_BASE_URL = "https://openrouter.ai/api/v1"
        const val DEFAULT_MODEL = "openai/gpt-4o-mini"

        /** "https://Example.com/path" -> "example.com" */
        fun normalizeHost(raw: String): String {
            var value = raw.trim().lowercase()
            if (value.isEmpty()) return ""
            value = value.substringAfter("://", value)
            value = value.substringBefore("/")
            value = value.substringBefore("?")
            value = value.substringBefore("#")
            if (value.contains("@")) return ""
            value = value.substringBefore(":")
            value = value.trimEnd('.')
            if (value.isEmpty() || value.length > 253) return ""
            if (!value.matches(Regex("^[a-z0-9._-]+$"))) return ""
            return value
        }
    }
}
