package io.github.ratanpatel.ratanagent;

import android.content.Context;
import android.content.SharedPreferences;

import org.json.JSONObject;

import java.util.Arrays;
import java.util.Collections;
import java.util.HashSet;
import java.util.Locale;
import java.util.Set;

/**
 * Small typed wrapper around SharedPreferences — the app's whole configuration surface.
 *
 * Note that no credential lives here. API keys go to {@link SecureStore} (Android Keystore,
 * AES-GCM); this file only holds the non-secret profile around them — which provider, which
 * endpoint, which model.
 */
public final class Prefs {

    /** Change this one string to point the app at a self-hosted RATAN AI deployment. */
    public static final String DEFAULT_AGENT_URL = "https://v1qmk5wx2361-d.space-z.ai/";

    public static final String MODE_HOSTED = "hosted";
    public static final String MODE_CUSTOM = "custom";

    private static final String FILE = "ratan_agent";
    private static final String KEY_AGENT_URL = "agentUrl";
    private static final String KEY_ALLOW_LAN_HTTP = "allowLanHttp";
    private static final String KEY_ALLOW_PUBLIC_HTTP = "allowPublicHttp";
    private static final String KEY_CONNECT_TIMEOUT = "connectTimeoutMs";
    private static final String KEY_READ_TIMEOUT = "readTimeoutMs";
    private static final String KEY_MAX_RESPONSE = "maxResponseKb";
    private static final String KEY_OPEN_EXTERNAL = "openExternal";
    private static final String KEY_KEEP_AWAKE = "keepAwake";

    // ---- bring-your-own-API profile -----------------------------------------------------------------
    private static final String KEY_LLM_MODE = "llmMode";
    private static final String KEY_LLM_PROVIDER = "llmProvider";
    private static final String KEY_LLM_BASE_URL = "llmBaseUrl";
    private static final String KEY_LLM_MODEL = "llmModel";
    private static final String KEY_LLM_PATH = "llmPath";
    private static final String KEY_LLM_SYSTEM = "llmSystemPrompt";
    private static final String KEY_LLM_TEMPERATURE = "llmTemperature";
    private static final String KEY_LLM_MAX_TOKENS = "llmMaxTokens";
    private static final String KEY_LLM_CUSTOM_HEADERS = "llmCustomHeaders";
    private static final String KEY_LLM_CUSTOM_BODY = "llmCustomBody";
    private static final String KEY_LLM_RESPONSE_PATH = "llmResponsePath";

    /** Keys the web layer is allowed to write through {@link #set(String, String)}. */
    public static final Set<String> LLM_KEYS = Collections.unmodifiableSet(new HashSet<>(Arrays.asList(
            KEY_LLM_MODE, KEY_LLM_PROVIDER, KEY_LLM_BASE_URL, KEY_LLM_MODEL, KEY_LLM_PATH,
            KEY_LLM_SYSTEM, KEY_LLM_TEMPERATURE, KEY_LLM_MAX_TOKENS, KEY_LLM_CUSTOM_HEADERS,
            KEY_LLM_CUSTOM_BODY, KEY_LLM_RESPONSE_PATH)));

    private final SharedPreferences sp;

    public Prefs(Context context) {
        this.sp = context.getApplicationContext().getSharedPreferences(FILE, Context.MODE_PRIVATE);
    }

    // ------------------------------------------------------------------ agent endpoint

    public String agentUrl() {
        String value = sp.getString(KEY_AGENT_URL, DEFAULT_AGENT_URL);
        if (value == null || value.trim().isEmpty()) {
            return DEFAULT_AGENT_URL;
        }
        value = value.trim();
        if (!value.startsWith("http://") && !value.startsWith("https://")) {
            value = "https://" + value;
        }
        return value;
    }

    public void setAgentUrl(String url) {
        sp.edit().putString(KEY_AGENT_URL, url == null ? DEFAULT_AGENT_URL : url.trim()).apply();
    }

    // ------------------------------------------------------------------ transport policy

    public boolean allowLanHttp() {
        return sp.getBoolean(KEY_ALLOW_LAN_HTTP, true);
    }

    public boolean allowPublicHttp() {
        return sp.getBoolean(KEY_ALLOW_PUBLIC_HTTP, false);
    }

    public int connectTimeoutMs() {
        return clamp(sp.getInt(KEY_CONNECT_TIMEOUT, 5000), 1000, 60000);
    }

    public int readTimeoutMs() {
        return clamp(sp.getInt(KEY_READ_TIMEOUT, 30000), 1000, 300000);
    }

    public int maxResponseKb() {
        return clamp(sp.getInt(KEY_MAX_RESPONSE, 512), 16, 8192);
    }

    public boolean openExternal() {
        return sp.getBoolean(KEY_OPEN_EXTERNAL, true);
    }

    public boolean keepAwake() {
        return sp.getBoolean(KEY_KEEP_AWAKE, false);
    }

    // ------------------------------------------------------------------ provider profile

    /** {@link #MODE_HOSTED} drives the hosted assistant; {@link #MODE_CUSTOM} lets the operator chat here. */
    public String llmMode() {
        String value = sp.getString(KEY_LLM_MODE, MODE_HOSTED);
        return MODE_CUSTOM.equalsIgnoreCase(value) ? MODE_CUSTOM : MODE_HOSTED;
    }

    public String llmProvider() {
        String value = sp.getString(KEY_LLM_PROVIDER, LlmClient.PROVIDER_OPENAI);
        return value == null ? LlmClient.PROVIDER_OPENAI : value.trim().toLowerCase(Locale.US);
    }

    public String llmBaseUrl() {
        return sp.getString(KEY_LLM_BASE_URL, "");
    }

    public String llmModel() {
        return sp.getString(KEY_LLM_MODEL, "");
    }

    public String llmPath() {
        return sp.getString(KEY_LLM_PATH, "");
    }

    public String llmSystemPrompt() {
        return sp.getString(KEY_LLM_SYSTEM, "");
    }

    public double llmTemperature() {
        try {
            return Double.parseDouble(sp.getString(KEY_LLM_TEMPERATURE, "0.7"));
        } catch (Exception exc) {
            return 0.7;
        }
    }

    public int llmMaxTokens() {
        return clamp(sp.getInt(KEY_LLM_MAX_TOKENS, 1024), 16, 32768);
    }

    public String llmCustomHeaders() {
        return sp.getString(KEY_LLM_CUSTOM_HEADERS, "");
    }

    public String llmCustomBody() {
        return sp.getString(KEY_LLM_CUSTOM_BODY, "");
    }

    public String llmResponsePath() {
        return sp.getString(KEY_LLM_RESPONSE_PATH, "");
    }

    // ------------------------------------------------------------------ generic setter

    public void set(String key, String value) {
        if (key == null) {
            return;
        }
        switch (key) {
            case KEY_AGENT_URL:
                setAgentUrl(value);
                break;
            case KEY_ALLOW_LAN_HTTP:
                sp.edit().putBoolean(KEY_ALLOW_LAN_HTTP, truthy(value, true)).apply();
                break;
            case KEY_ALLOW_PUBLIC_HTTP:
                sp.edit().putBoolean(KEY_ALLOW_PUBLIC_HTTP, truthy(value, false)).apply();
                break;
            case KEY_OPEN_EXTERNAL:
                sp.edit().putBoolean(KEY_OPEN_EXTERNAL, truthy(value, true)).apply();
                break;
            case KEY_KEEP_AWAKE:
                sp.edit().putBoolean(KEY_KEEP_AWAKE, truthy(value, false)).apply();
                break;
            case KEY_CONNECT_TIMEOUT:
                sp.edit().putInt(KEY_CONNECT_TIMEOUT, (int) number(value, 5000)).apply();
                break;
            case KEY_READ_TIMEOUT:
                sp.edit().putInt(KEY_READ_TIMEOUT, (int) number(value, 30000)).apply();
                break;
            case KEY_MAX_RESPONSE:
                sp.edit().putInt(KEY_MAX_RESPONSE, (int) number(value, 512)).apply();
                break;
            case KEY_LLM_MODE:
                sp.edit().putString(KEY_LLM_MODE,
                        MODE_CUSTOM.equalsIgnoreCase(String.valueOf(value).trim()) ? MODE_CUSTOM : MODE_HOSTED).apply();
                break;
            case KEY_LLM_PROVIDER:
                sp.edit().putString(KEY_LLM_PROVIDER,
                        value == null ? LlmClient.PROVIDER_OPENAI : value.trim().toLowerCase(Locale.US)).apply();
                break;
            case KEY_LLM_BASE_URL:
                sp.edit().putString(KEY_LLM_BASE_URL, value == null ? "" : value.trim()).apply();
                break;
            case KEY_LLM_MODEL:
                sp.edit().putString(KEY_LLM_MODEL, value == null ? "" : value.trim()).apply();
                break;
            case KEY_LLM_PATH:
                sp.edit().putString(KEY_LLM_PATH, value == null ? "" : value.trim()).apply();
                break;
            case KEY_LLM_SYSTEM:
                sp.edit().putString(KEY_LLM_SYSTEM, value == null ? "" : value).apply();
                break;
            case KEY_LLM_TEMPERATURE: {
                double parsed = number(value, 0.7);
                sp.edit().putString(KEY_LLM_TEMPERATURE, String.valueOf(Math.max(0, Math.min(2, parsed)))).apply();
                break;
            }
            case KEY_LLM_MAX_TOKENS:
                sp.edit().putInt(KEY_LLM_MAX_TOKENS, clamp((int) number(value, 1024), 16, 32768)).apply();
                break;
            case KEY_LLM_CUSTOM_HEADERS:
                sp.edit().putString(KEY_LLM_CUSTOM_HEADERS, value == null ? "" : value).apply();
                break;
            case KEY_LLM_CUSTOM_BODY:
                sp.edit().putString(KEY_LLM_CUSTOM_BODY, value == null ? "" : value).apply();
                break;
            case KEY_LLM_RESPONSE_PATH:
                sp.edit().putString(KEY_LLM_RESPONSE_PATH, value == null ? "" : value.trim()).apply();
                break;
            default:
                // unknown keys are ignored on purpose: the web layer cannot invent settings
                break;
        }
    }

    public void resetHttpSettings() {
        sp.edit()
                .putBoolean(KEY_ALLOW_LAN_HTTP, true)
                .putBoolean(KEY_ALLOW_PUBLIC_HTTP, false)
                .putInt(KEY_CONNECT_TIMEOUT, 5000)
                .putInt(KEY_READ_TIMEOUT, 30000)
                .putInt(KEY_MAX_RESPONSE, 512)
                .apply();
    }

    // ------------------------------------------------------------------ diagnostics

    public JSONObject toJson() {
        JSONObject json = new JSONObject();
        try {
            json.put(KEY_AGENT_URL, agentUrl());
            json.put(KEY_ALLOW_LAN_HTTP, allowLanHttp());
            json.put(KEY_ALLOW_PUBLIC_HTTP, allowPublicHttp());
            json.put(KEY_CONNECT_TIMEOUT, connectTimeoutMs());
            json.put(KEY_READ_TIMEOUT, readTimeoutMs());
            json.put(KEY_MAX_RESPONSE, maxResponseKb());
            json.put(KEY_OPEN_EXTERNAL, openExternal());
            json.put(KEY_KEEP_AWAKE, keepAwake());
            json.put(KEY_LLM_MODE, llmMode());
            json.put(KEY_LLM_PROVIDER, llmProvider());
            json.put(KEY_LLM_BASE_URL, llmBaseUrl());
            json.put(KEY_LLM_MODEL, llmModel());
            json.put(KEY_LLM_PATH, llmPath());
            json.put(KEY_LLM_CUSTOM_HEADERS, llmCustomHeaders());
            json.put(KEY_LLM_CUSTOM_BODY, llmCustomBody());
            json.put(KEY_LLM_RESPONSE_PATH, llmResponsePath());
        } catch (Exception ignored) {
            // JSONObject never throws for these primitive puts
        }
        return json;
    }

    public String toJsonString() {
        return toJson().toString();
    }

    // ------------------------------------------------------------------ helpers

    private static boolean truthy(String value, boolean fallback) {
        if (value == null) {
            return fallback;
        }
        switch (value.trim().toLowerCase(Locale.US)) {
            case "1":
            case "true":
            case "yes":
            case "on":
                return true;
            case "0":
            case "false":
            case "no":
            case "off":
                return false;
            default:
                return fallback;
        }
    }

    private static double number(String value, double fallback) {
        try {
            return Double.parseDouble(value.trim());
        } catch (Exception exc) {
            return fallback;
        }
    }

    private static int clamp(int value, int min, int max) {
        return Math.max(min, Math.min(max, value));
    }
}
