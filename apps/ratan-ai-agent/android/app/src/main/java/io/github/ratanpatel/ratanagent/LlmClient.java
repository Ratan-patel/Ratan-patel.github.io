package io.github.ratanpatel.ratanagent;

import android.content.Context;

import org.json.JSONArray;
import org.json.JSONObject;

import java.util.Iterator;
import java.util.Locale;

/**
 * Bring-your-own-API chat client.
 *
 * The app ships pointed at the hosted RATAN AI assistant, but an operator may prefer to drive it
 * with their own provider: an OpenAI-compatible endpoint, Anthropic, a local Ollama server, or a
 * private/custom JSON API. This class turns the stored provider profile into one HTTP call.
 *
 * Two rules are load-bearing and must not be relaxed:
 *
 *  1. **The destination is never decided by the web layer.** JavaScript contributes messages and
 *     nothing else; the URL comes from the stored profile. That is what stops a page from asking
 *     the shell to attach the operator's credential to a request of the page's choosing.
 *  2. **The credential never travels back to JavaScript.** It is read from the Keystore, written
 *     into a header here, and any occurrence of it in an error string is redacted before the
 *     result is returned.
 */
public final class LlmClient {

    public static final String KEY_NAME = "llm_api_key";

    public static final String PROVIDER_OPENAI = "openai";
    public static final String PROVIDER_ANTHROPIC = "anthropic";
    public static final String PROVIDER_OLLAMA = "ollama";
    public static final String PROVIDER_CUSTOM = "custom";

    private static final String MODE_HOSTED = Prefs.MODE_HOSTED;

    private static final int MAX_MESSAGES = 24;
    private static final int MAX_CONTENT_CHARS = 12000;
    private static final String DEFAULT_SYSTEM_PROMPT =
            "You are RATAN AI, an assistant for authorised penetration testing and defensive "
                    + "security work. Be precise, cite the tool or technique you mean, and refuse "
                    + "requests that target systems the user does not own or have written "
                    + "permission to test.";

    private LlmClient() {
    }

    // ------------------------------------------------------------------ configuration surface

    public static String info(Context context, Prefs prefs, SecureStore store) {
        JSONObject json = new JSONObject();
        try {
            String mode = prefs.llmMode();
            String provider = prefs.llmProvider();
            String baseUrl = effectiveBaseUrl(prefs);
            json.put("mode", mode);
            json.put("provider", provider);
            json.put("baseUrl", baseUrl);
            json.put("model", prefs.llmModel());
            json.put("temperature", prefs.llmTemperature());
            json.put("maxTokens", prefs.llmMaxTokens());
            json.put("systemPrompt", prefs.llmSystemPrompt());
            json.put("customHeaders", prefs.llmCustomHeaders());
            json.put("customBody", prefs.llmCustomBody());
            json.put("customPath", prefs.llmPath());
            json.put("responsePath", prefs.llmResponsePath());
            json.put("keystore", store.isAvailable() ? "available" : "unavailable");
            json.put("hasKey", store.has(KEY_NAME));
            json.put("keyHint", store.hint(KEY_NAME, 4));
            json.put("endpoint", requestUrl(prefs));      // what a chat would actually hit
            boolean hostedMode = MODE_HOSTED.equals(mode);
            String note = hostedMode ? null : validate(prefs, store, false);
            json.put("ready", !hostedMode && note == null);
            json.put("note", note == null ? JSONObject.NULL : note);
            json.put("providers", new JSONArray(new String[]{
                    PROVIDER_OPENAI, PROVIDER_ANTHROPIC, PROVIDER_OLLAMA, PROVIDER_CUSTOM}));
            json.put("defaultSystemPrompt", DEFAULT_SYSTEM_PROMPT);
        } catch (Exception ignored) {
            // primitives and strings only
        }
        return json.toString();
    }

    /** Applies a profile update from the dashboard. The API key is handled separately. */
    public static String saveConfig(Prefs prefs, String configJson) {
        JSONObject json = new JSONObject();
        try {
            JSONObject input = new JSONObject(configJson == null ? "{}" : configJson);
            for (Iterator<String> it = input.keys(); it.hasNext(); ) {
                String key = it.next();
                if (!Prefs.LLM_KEYS.contains(key)) {
                    continue;              // the web layer cannot invent settings
                }
                Object raw = input.opt(key);
                if (raw == null || raw == JSONObject.NULL) {
                    continue;
                }
                // optString() silently drops numbers, and the dashboard may send either
                String value = (raw instanceof String) ? (String) raw : String.valueOf(raw);
                prefs.set(key, value);
            }
            json.put("ok", true);
            json.put("note", validate(prefs, null, false));
        } catch (Exception exc) {
            try {
                json.put("ok", false);
                json.put("error", exc.getClass().getSimpleName() + ": " + exc.getMessage());
            } catch (Exception ignored) {
                return "{\"ok\":false}";
            }
        }
        return json.toString();
    }

    // ------------------------------------------------------------------ connectivity check

    /** One tiny round-trip so the operator learns about a bad key before a real question. */
    public static String test(Context context, Prefs prefs, SecureStore store) {
        JSONObject request = new JSONObject();
        try {
            JSONArray messages = new JSONArray();
            JSONObject probe = new JSONObject();
            probe.put("role", "user");
            probe.put("content", "Reply with the single word: ready");
            messages.put(probe);
            request.put("messages", messages);
            request.put("maxTokens", 8);
            request.put("temperature", 0);
            String raw = chat(context, prefs, store, request.toString());
            JSONObject result = new JSONObject(raw);
            JSONObject json = new JSONObject();
            json.put("ok", result.optBoolean("ok"));
            json.put("provider", result.optString("provider"));
            json.put("model", result.optString("model"));
            json.put("ms", result.optLong("ms"));
            json.put("status", result.optInt("status"));
            json.put("reply", result.optString("text"));
            json.put("error", result.opt("error"));
            json.put("hint", result.opt("hint"));
            json.put("endpoint", result.optString("url"));
            return json.toString();
        } catch (Exception exc) {
            return "{\"ok\":false,\"error\":" + MainActivity.quote(String.valueOf(exc)) + "}";
        }
    }

    // ------------------------------------------------------------------ chat

    /**
     * Runs one completion. {@code messagesJson} is {@code {"messages":[{"role","content"}...]}}
     * plus optional {@code model}/{@code temperature}/{@code maxTokens} overrides.
     */
    public static String chat(Context context, Prefs prefs, SecureStore store, String messagesJson) {
        long started = System.currentTimeMillis();
        String provider = prefs.llmProvider();
        JSONObject out = new JSONObject();
        String key = store.get(KEY_NAME);
        try {
            String problem = validate(prefs, store, providerNeedsKey(provider) && (key == null || key.isEmpty()));
            if (problem != null) {
                out.put("ok", false);
                out.put("provider", provider);
                out.put("error", problem);
                out.put("hint", "open the dashboard and finish the API setup");
                out.put("ms", 0);
                return out.toString();
            }

            JSONObject request = new JSONObject(messagesJson == null ? "{}" : messagesJson);
            JSONArray messages = sanitizeMessages(request.optJSONArray("messages"));
            if (messages.length() == 0) {
                out.put("ok", false);
                out.put("provider", provider);
                out.put("error", "no messages supplied");
                return out.toString();
            }
            String model = request.optString("model", prefs.llmModel()).trim();
            double temperature = request.has("temperature")
                    ? request.optDouble("temperature", prefs.llmTemperature())
                    : prefs.llmTemperature();
            int maxTokens = request.optInt("maxTokens", prefs.llmMaxTokens());

            String system = prefs.llmSystemPrompt();
            if (system == null || system.trim().isEmpty()) {
                system = DEFAULT_SYSTEM_PROMPT;
            }

            String url = requestUrl(prefs);
            String headers = buildHeaders(prefs, provider, key);
            String body = buildBody(prefs, provider, model, system, messages, temperature, maxTokens);
            if (url == null || body == null) {
                out.put("ok", false);
                out.put("provider", provider);
                out.put("error", "provider profile is incomplete");
                return out.toString();
            }

            HttpEngine.Result response = HttpEngine.execute(context, prefs, "POST", url, headers, body);
            long ms = System.currentTimeMillis() - started;

            out.put("provider", provider);
            out.put("model", model);
            out.put("url", response.finalUrl.isEmpty() ? url : response.finalUrl);
            out.put("status", response.status);
            out.put("ms", ms);
            out.put("truncated", response.truncated);

            if (response.blocked) {
                out.put("ok", false);
                out.put("error", redact(response.error, key));
                out.put("hint", "transport policy blocked this call — check the base URL, or grant "
                        + "local-network access for a LAN endpoint");
                return out.toString();
            }
            if (response.status == 0) {
                out.put("ok", false);
                out.put("error", redact(response.error, key));
                out.put("hint", "no HTTP response: raise the read timeout in settings, check the "
                        + "network, or verify the endpoint host");
                return out.toString();
            }
            if (response.status >= 400) {
                out.put("ok", false);
                out.put("error", redact(providerError(response.body, response.status), key));
                out.put("hint", hintForStatus(response.status));
                return out.toString();
            }

            String text = extractText(prefs, provider, response.body);
            if (text == null || text.trim().isEmpty()) {
                out.put("ok", false);
                out.put("error", "the provider answered HTTP " + response.status
                        + " but no completion text was found");
                out.put("hint", provider == PROVIDER_CUSTOM
                        ? "check the response path (for example choices[0].message.content)"
                        : "the reply shape did not match " + provider);
                out.put("raw", redact(truncate(response.body, 800), key));
                return out.toString();
            }
            out.put("ok", true);
            out.put("text", text);
            out.put("usage", usage(provider, response.body));
            return out.toString();

        } catch (org.json.JSONException exc) {
            return error(out, provider, "malformed request/response JSON: " + exc.getMessage(), null, started);
        } catch (Exception exc) {
            return error(out, provider, exc.getClass().getSimpleName() + ": " + exc.getMessage(), null, started);
        }
    }

    private static String error(JSONObject out, String provider, String message, String hint, long started) {
        try {
            out.put("ok", false);
            out.put("provider", provider);
            out.put("error", message);
            if (hint != null) {
                out.put("hint", hint);
            }
            out.put("ms", System.currentTimeMillis() - started);
        } catch (Exception ignored) {
            return "{\"ok\":false}";
        }
        return out.toString();
    }

    // ------------------------------------------------------------------ provider plumbing

    private static boolean providerNeedsKey(String provider) {
        return !PROVIDER_OLLAMA.equals(provider);
    }

    private static String validate(Prefs prefs, SecureStore store, boolean missingKey) {
        String provider = prefs.llmProvider();
        if (Prefs.MODE_HOSTED.equals(prefs.llmMode())) {
            return "mode is set to the hosted agent";
        }
        if (!PROVIDER_OPENAI.equals(provider) && !PROVIDER_ANTHROPIC.equals(provider)
                && !PROVIDER_OLLAMA.equals(provider) && !PROVIDER_CUSTOM.equals(provider)) {
            return "unknown provider: " + provider;
        }
        if (PROVIDER_CUSTOM.equals(provider)) {
            String headers = prefs.llmCustomHeaders();
            if (headers != null && !headers.trim().isEmpty()) {
                try {
                    new JSONObject(headers);
                } catch (Exception exc) {
                    return "custom headers are not valid JSON";
                }
            }
            String body = prefs.llmCustomBody();
            if (body == null || body.trim().isEmpty()) {
                return "custom body template is empty";
            }
        }
        if (!PROVIDER_OLLAMA.equals(provider) && (prefs.llmModel() == null || prefs.llmModel().isEmpty())) {
            return "set the model name (for example gpt-4o-mini, claude-sonnet-4-5, qwen2.5:7b)";
        }
        if (missingKey) {
            if (store != null && !store.isAvailable()) {
                return "this device has no usable Android Keystore, so a key cannot be stored safely";
            }
            return "no API key saved for " + provider;
        }
        return null;
    }

    /** Provider base URL, or the stored override when the operator set one. */
    private static String defaultBaseUrl(String provider) {
        switch (provider) {
            case PROVIDER_ANTHROPIC:
                return "https://api.anthropic.com";
            case PROVIDER_OLLAMA:
                return "http://127.0.0.1:11434";
            case PROVIDER_OPENAI:
                return "https://api.openai.com";
            default:
                return "";
        }
    }

    public static String effectiveBaseUrl(Prefs prefs) {
        String configured = prefs.llmBaseUrl();
        if (configured != null && !configured.trim().isEmpty()) {
            return trimSlash(configured.trim());
        }
        return defaultBaseUrl(prefs.llmProvider());
    }

    /** The exact URL a chat would POST to. Built only from stored config — never from JS input. */
    public static String requestUrl(Prefs prefs) {
        String provider = prefs.llmProvider();
        String base = effectiveBaseUrl(prefs);
        String path = prefs.llmPath();
        if (PROVIDER_CUSTOM.equals(provider)) {
            if (base == null || base.isEmpty()) {
                return null;
            }
            if (path != null && !path.trim().isEmpty()) {
                return trimSlash(base) + (path.startsWith("/") ? path : "/" + path);
            }
            return base;
        }
        if (base == null || base.isEmpty()) {
            return null;
        }
        switch (provider) {
            case PROVIDER_OPENAI:
                if (base.endsWith("/chat/completions")) {
                    return base;
                }
                if (base.endsWith("/v1")) {
                    return base + "/chat/completions";
                }
                return base + "/v1/chat/completions";
            case PROVIDER_ANTHROPIC:
                if (base.endsWith("/v1/messages")) {
                    return base;
                }
                if (base.endsWith("/v1")) {
                    return base + "/messages";
                }
                return base + "/v1/messages";
            case PROVIDER_OLLAMA:
                if (base.endsWith("/api/chat")) {
                    return base;
                }
                return base + "/api/chat";
            default:
                return base;
        }
    }

    private static String buildHeaders(Prefs prefs, String provider, String key) {
        JSONObject headers = new JSONObject();
        try {
            switch (provider) {
                case PROVIDER_OPENAI:
                    if (key != null && !key.isEmpty()) {
                        headers.put("Authorization", "Bearer " + key);
                    }
                    break;
                case PROVIDER_ANTHROPIC:
                    if (key != null && !key.isEmpty()) {
                        headers.put("x-api-key", key);
                    }
                    headers.put("anthropic-version", "2023-06-01");
                    break;
                case PROVIDER_OLLAMA:
                    if (key != null && !key.isEmpty()) {
                        headers.put("Authorization", "Bearer " + key);
                    }
                    break;
                case PROVIDER_CUSTOM:
                    String template = prefs.llmCustomHeaders();
                    if (template != null && !template.trim().isEmpty()) {
                        JSONObject configured = new JSONObject(template);
                        for (Iterator<String> it = configured.keys(); it.hasNext(); ) {
                            String name = it.next();
                            String value = configured.optString(name, "");
                            headers.put(name, value.replace("{{KEY}}", key == null ? "" : key));
                        }
                    }
                    break;
                default:
                    break;
            }
        } catch (Exception ignored) {
            // a malformed extra header must not stop the call
        }
        return headers.toString();
    }

    private static String buildBody(Prefs prefs, String provider, String model, String system,
                                    JSONArray messages, double temperature, int maxTokens) {
        try {
            switch (provider) {
                case PROVIDER_OPENAI: {
                    JSONObject body = new JSONObject();
                    body.put("model", model);
                    JSONArray payload = new JSONArray();
                    if (system != null && !system.trim().isEmpty()) {
                        JSONObject sys = new JSONObject();
                        sys.put("role", "system");
                        sys.put("content", system);
                        payload.put(sys);
                    }
                    for (int i = 0; i < messages.length(); i++) {
                        payload.put(messages.get(i));
                    }
                    body.put("messages", payload);
                    body.put("temperature", temperature);
                    if (maxTokens > 0) {
                        body.put("max_tokens", maxTokens);
                    }
                    body.put("stream", false);
                    return body.toString();
                }
                case PROVIDER_ANTHROPIC: {
                    JSONObject body = new JSONObject();
                    body.put("model", model);
                    body.put("max_tokens", maxTokens > 0 ? maxTokens : 1024);
                    if (system != null && !system.trim().isEmpty()) {
                        body.put("system", system);
                    }
                    JSONArray payload = new JSONArray();
                    for (int i = 0; i < messages.length(); i++) {
                        JSONObject message = messages.getJSONObject(i);
                        if ("system".equals(message.optString("role"))) {
                            continue;      // Anthropic takes the system prompt out of band
                        }
                        payload.put(message);
                    }
                    body.put("messages", payload);
                    body.put("temperature", temperature);
                    body.put("stream", false);
                    return body.toString();
                }
                case PROVIDER_OLLAMA: {
                    JSONObject body = new JSONObject();
                    body.put("model", model.isEmpty() ? "llama3.1" : model);
                    JSONArray payload = new JSONArray();
                    if (system != null && !system.trim().isEmpty()) {
                        JSONObject sys = new JSONObject();
                        sys.put("role", "system");
                        sys.put("content", system);
                        payload.put(sys);
                    }
                    for (int i = 0; i < messages.length(); i++) {
                        payload.put(messages.get(i));
                    }
                    body.put("messages", payload);
                    body.put("stream", false);
                    JSONObject options = new JSONObject();
                    options.put("temperature", temperature);
                    body.put("options", options);
                    return body.toString();
                }
                case PROVIDER_CUSTOM: {
                    String template = prefs.llmCustomBody();
                    if (template == null || template.trim().isEmpty()) {
                        return null;
                    }
                    String prompt = "";
                    for (int i = messages.length() - 1; i >= 0; i--) {
                        JSONObject message = messages.getJSONObject(i);
                        if ("user".equals(message.optString("role"))) {
                            prompt = message.optString("content", "");
                            break;
                        }
                    }
                    String rendered = template
                            .replace("{{MESSAGES}}", messages.toString())
                            .replace("{{SYSTEM}}", jsonString(system == null ? "" : system))
                            .replace("{{PROMPT}}", jsonString(prompt))
                            .replace("{{MODEL}}", jsonString(model))
                            .replace("{{TEMPERATURE}}", String.valueOf(temperature))
                            .replace("{{MAX_TOKENS}}", String.valueOf(maxTokens > 0 ? maxTokens : 1024));
                    new JSONObject(rendered);        // fail early on a broken template
                    return rendered;
                }
                default:
                    return null;
            }
        } catch (Exception exc) {
            return null;
        }
    }

    // ------------------------------------------------------------------ response parsing

    private static String extractText(Prefs prefs, String provider, String body) {
        try {
            if (PROVIDER_CUSTOM.equals(provider) && prefs.llmResponsePath() != null
                    && !prefs.llmResponsePath().trim().isEmpty()) {
                Object value = extractPath(new JSONObject(body), prefs.llmResponsePath().trim());
                if (value != null) {
                    return value instanceof String ? (String) value : String.valueOf(value);
                }
            }
            JSONObject json = new JSONObject(body);
            switch (provider) {
                case PROVIDER_ANTHROPIC: {
                    JSONArray content = json.optJSONArray("content");
                    StringBuilder sb = new StringBuilder();
                    for (int i = 0; content != null && i < content.length(); i++) {
                        JSONObject block = content.optJSONObject(i);
                        if (block != null && "text".equals(block.optString("type"))) {
                            sb.append(block.optString("text"));
                        }
                    }
                    if (sb.length() > 0) {
                        return sb.toString();
                    }
                    break;
                }
                case PROVIDER_OLLAMA: {
                    JSONObject message = json.optJSONObject("message");
                    if (message != null) {
                        return message.optString("content");
                    }
                    if (json.has("response")) {
                        return json.optString("response");
                    }
                    break;
                }
                default: {
                    JSONArray choices = json.optJSONArray("choices");
                    if (choices != null && choices.length() > 0) {
                        JSONObject choice = choices.optJSONObject(0);
                        if (choice != null) {
                            JSONObject message = choice.optJSONObject("message");
                            if (message != null && message.has("content")) {
                                return stringifyContent(message.opt("content"));
                            }
                            if (choice.has("text")) {
                                return choice.optString("text");
                            }
                        }
                    }
                    // generic fallbacks for OpenAI-compatible-ish servers
                    for (String candidate : new String[]{"response", "output_text", "text", "content"}) {
                        if (json.has(candidate) && json.opt(candidate) instanceof String) {
                            return json.optString(candidate);
                        }
                    }
                    break;
                }
            }
            return null;
        } catch (Exception exc) {
            return null;
        }
    }

    private static String stringifyContent(Object content) {
        if (content instanceof String) {
            return (String) content;
        }
        if (content instanceof JSONArray) {
            StringBuilder sb = new StringBuilder();
            JSONArray parts = (JSONArray) content;
            for (int i = 0; i < parts.length(); i++) {
                Object part = parts.opt(i);
                if (part instanceof JSONObject) {
                    JSONObject block = (JSONObject) part;
                    if (block.has("text")) {
                        sb.append(block.optString("text"));
                    } else if (block.has("content")) {
                        sb.append(block.optString("content"));
                    }
                } else if (part != null) {
                    sb.append(part);
                }
            }
            return sb.toString();
        }
        return content == null ? null : String.valueOf(content);
    }

    private static JSONObject usage(String provider, String body) {
        JSONObject usage = new JSONObject();
        try {
            JSONObject json = new JSONObject(body);
            JSONObject source;
            if (PROVIDER_ANTHROPIC.equals(provider)) {
                source = json;
            } else if (PROVIDER_OLLAMA.equals(provider)) {
                source = json;
            } else {
                source = json.optJSONObject("usage");
            }
            if (source != null) {
                usage.put("prompt", source.optInt("prompt_tokens", source.optInt("prompt_eval_count", 0)));
                usage.put("completion",
                        source.optInt("completion_tokens", source.optInt("eval_count", source.optInt("output_tokens", 0))));
                usage.put("total", source.optInt("total_tokens", 0));
            }
        } catch (Exception ignored) {
            // usage is cosmetic
        }
        return usage;
    }

    /** Pulls a human-useful message out of a provider error envelope. */
    private static String providerError(String body, int status) {
        try {
            JSONObject json = new JSONObject(body);
            Object error = json.opt("error");
            if (error instanceof JSONObject) {
                String message = ((JSONObject) error).optString("message", null);
                if (message != null && !message.isEmpty()) {
                    return "HTTP " + status + ": " + message;
                }
            }
            if (error instanceof String && !((String) error).isEmpty()) {
                return "HTTP " + status + ": " + error;
            }
            if (json.has("message")) {
                return "HTTP " + status + ": " + json.optString("message");
            }
            if (json.has("detail")) {
                return "HTTP " + status + ": " + json.optString("detail");
            }
        } catch (Exception ignored) {
            // fall through to the raw snippet
        }
        return "HTTP " + status + ": " + truncate(body == null ? "" : body.trim(), 300);
    }

    private static String hintForStatus(int status) {
        switch (status) {
            case 400:
                return "the request was rejected — usually an unknown model name or a field the "
                        + "provider does not accept";
            case 401:
            case 403:
                return "the API key was rejected: check the key value, its permissions and whether "
                        + "that key may call this model";
            case 404:
                return "endpoint not found — check the base URL and the path for this provider";
            case 408:
                return "the provider timed out";
            case 413:
                return "the prompt is too large for this model";
            case 422:
                return "the provider could not parse the request body";
            case 429:
                return "rate limited or out of quota — wait, or switch to another key/model";
            case 500:
            case 502:
            case 503:
            case 504:
                return "the provider had a server error — retry, or point at another endpoint";
            default:
                return "provider returned HTTP " + status;
        }
    }

    // ------------------------------------------------------------------ helpers

    private static JSONArray sanitizeMessages(JSONArray input) {
        JSONArray clean = new JSONArray();
        if (input == null) {
            return clean;
        }
        int start = Math.max(0, input.length() - MAX_MESSAGES);
        for (int i = start; i < input.length(); i++) {
            JSONObject message = input.optJSONObject(i);
            if (message == null) {
                continue;
            }
            String role = message.optString("role", "user").toLowerCase(Locale.US);
            if (!"system".equals(role) && !"user".equals(role) && !"assistant".equals(role)) {
                role = "user";
            }
            String content = message.optString("content", "");
            if (content.isEmpty()) {
                continue;
            }
            if (content.length() > MAX_CONTENT_CHARS) {
                content = content.substring(0, MAX_CONTENT_CHARS) + "\n[truncated by the app]";
            }
            try {
                JSONObject entry = new JSONObject();
                entry.put("role", role);
                entry.put("content", content);
                clean.put(entry);
            } catch (Exception ignored) {
                // skip this message
            }
        }
        return clean;
    }

    /** Replaces the credential with a marker so it can never appear in a log or a toast. */
    static String redact(String text, String secret) {
        if (text == null) {
            return null;
        }
        if (secret == null || secret.length() < 6) {
            return text;
        }
        return text.replace(secret, "***redacted***");
    }

    private static String truncate(String text, int max) {
        if (text == null) {
            return "";
        }
        return text.length() <= max ? text : text.substring(0, max) + "…";
    }

    private static String trimSlash(String value) {
        String trimmed = value == null ? "" : value.trim();
        while (trimmed.endsWith("/")) {
            trimmed = trimmed.substring(0, trimmed.length() - 1);
        }
        return trimmed;
    }

    private static String jsonString(String value) {
        return MainActivity.quote(value == null ? "" : value);
    }

    /** Minimal dot/bracket path lookup: {@code choices[0].message.content}. */
    static Object extractPath(JSONObject root, String path) {
        Object current = root;
        StringBuilder token = new StringBuilder();
        String normalized = path.replace("[", ".").replace("]", "");
        for (String part : normalized.split("\\.")) {
            if (part.isEmpty()) {
                continue;
            }
            if (current == null) {
                return null;
            }
            if (current instanceof JSONArray) {
                int index;
                try {
                    index = Integer.parseInt(part);
                } catch (Exception exc) {
                    return null;
                }
                current = ((JSONArray) current).opt(index);
            } else if (current instanceof JSONObject) {
                current = ((JSONObject) current).opt(part);
            } else {
                return null;
            }
            token.append(part).append('.');
        }
        return current;
    }
}
