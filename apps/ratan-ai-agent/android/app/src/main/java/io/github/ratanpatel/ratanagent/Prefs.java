package io.github.ratanpatel.ratanagent;

import android.content.Context;
import android.content.SharedPreferences;

import org.json.JSONObject;

import java.util.Locale;

/** Small typed wrapper around SharedPreferences — the app's whole configuration surface. */
public final class Prefs {

    /** Change this one string to point the app at a self-hosted RATAN AI deployment. */
    public static final String DEFAULT_AGENT_URL = "https://v1qmk5wx2361-d.space-z.ai/";

    private static final String FILE = "ratan_agent";
    private static final String KEY_AGENT_URL = "agentUrl";
    private static final String KEY_ALLOW_LAN_HTTP = "allowLanHttp";
    private static final String KEY_ALLOW_PUBLIC_HTTP = "allowPublicHttp";
    private static final String KEY_CONNECT_TIMEOUT = "connectTimeoutMs";
    private static final String KEY_READ_TIMEOUT = "readTimeoutMs";
    private static final String KEY_MAX_RESPONSE = "maxResponseKb";
    private static final String KEY_OPEN_EXTERNAL = "openExternal";
    private static final String KEY_KEEP_AWAKE = "keepAwake";

    private final SharedPreferences sp;

    public Prefs(Context context) {
        this.sp = context.getApplicationContext().getSharedPreferences(FILE, Context.MODE_PRIVATE);
    }

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
        } catch (Exception ignored) {
            // JSONObject never throws for these primitive puts
        }
        return json;
    }

    public String toJsonString() {
        return toJson().toString();
    }

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
