# RATAN AI Gemini proxy

This Worker is the server-side bridge for `ai/chat/index.html`. It calls the Google Gemini Interactions API with the stable model string `gemini-3.7-flash`; the browser never receives `GEMINI_API_KEY`.

## Required secrets

Configure these as Worker secrets, not as source files or public variables:

```text
GEMINI_API_KEY       # Gemini API key from Google AI Studio
RATAN_AI_ACCESS_CODE # private access code issued after access confirmation
```

The Worker deliberately returns `503` until both secrets exist and returns `401` when the access-code header is invalid. This prevents an accidental public, unlimited Gemini endpoint.

## Deployment shape

The GitHub Pages site serves `/ai/` and `/ai/chat/` as static pages. The Worker serves `POST /chat`. The chat frontend defaults to `/api/ai/chat`, which is suitable when a reverse proxy maps that path to the Worker. If the Worker is hosted on its own `workers.dev` hostname, set `window.RATAN_AI_PROXY_URL` before the chat script runs to the Worker URL plus `/chat`.

Example deployment commands from this directory are intentionally documented without any secret values:

```bash
npx wrangler deploy --config wrangler.toml
npx wrangler secret put GEMINI_API_KEY
npx wrangler secret put RATAN_AI_ACCESS_CODE
```

Before production use, configure a real identity provider or a managed access layer. The static email/access-code gate in the page is only a UI gate; the Worker access-code check is the security boundary until full authentication is added. Restrict the Gemini API key to the Gemini API, monitor quota and billing, and rotate the key if it is ever exposed.

## Model and API references

The integration follows Google's Interactions API pattern and uses the current stable endpoint `gemini-3.7-flash`. See the [Gemini API key guidance](https://ai.google.dev/gemini-api/docs/api-key), [text-generation guide](https://ai.google.dev/gemini-api/docs/text-generation), and [model list](https://ai.google.dev/gemini-api/docs/models).
