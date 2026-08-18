# RATAN AI Gemini proxy

This Worker is the server-side bridge for `ai/chat/index.html`. It calls the Google Gemini Interactions API with the stable model string `gemini-3.7-flash`; the browser never receives `GEMINI_API_KEY`.

## Required secrets

Configure these as Worker secrets, not as source files or public variables:

```text
GEMINI_API_KEY       # Gemini API key from Google AI Studio
# No user email, access code, or paid-plan secret is required.
```

The Worker returns `503` until the Gemini secret exists. The chat is intentionally open and free at the application layer, while the Worker retains message-length limits and the lawful-use system instruction.

## Deployment shape

The GitHub Pages site serves `/ai/` and `/ai/chat/` as static pages. The Worker serves `POST /chat`. The chat frontend defaults to `/api/ai/chat`, which is suitable when a reverse proxy maps that path to the Worker. If the Worker is hosted on its own `workers.dev` hostname, set `window.RATAN_AI_PROXY_URL` before the chat script runs to the Worker URL plus `/chat`.

Example deployment commands from this directory are intentionally documented without any secret values:

```bash
npx wrangler deploy --config wrangler.toml
npx wrangler secret put GEMINI_API_KEY
```

The free chat is open without an email or access code. Restrict the Gemini API key to the Gemini API, monitor quota and billing, and rotate the key if it is ever exposed. Keep the lawful-use boundary and message-length limit enabled.

## Model and API references

The integration follows Google's Interactions API pattern and uses the current stable endpoint `gemini-3.7-flash`. See the [Gemini API key guidance](https://ai.google.dev/gemini-api/docs/api-key), [text-generation guide](https://ai.google.dev/gemini-api/docs/text-generation), and [model list](https://ai.google.dev/gemini-api/docs/models).
