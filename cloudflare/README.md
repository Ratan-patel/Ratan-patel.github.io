# RATAN AI Gemini proxy

This Worker is the server-side bridge for `ai/chat/index.html`. It calls the Google Gemini Interactions API with the stable model string `gemini-3.7-flash`; the browser never receives `GEMINI_API_KEY`.

## Access model

RATAN AI now provides a five-minute guest trial. The Worker stores a short-lived, hashed browser/network trial record in the `RATAN_AI_TRIALS` KV namespace through the `TRIAL_KV` binding. The `/trial` endpoint initializes or returns the server-checked expiry time, while `/chat` refuses new requests after the five-minute window.

There is no new payment gateway in this update. After expiry, the chat links to the existing payment page, which keeps the current India UPI/INR and international USDT ERC-20 instructions. Payment confirmation and access activation remain manual. If an administrator sets the optional `PAID_ACCESS_CODE` Worker secret, the activation code entered by a user is checked server-side on subsequent chat requests.

A guest trial is not an identity system: clearing browser storage, changing devices or using a different network can create a new guest fingerprint. For stronger one-trial-per-person enforcement, add authentication or a verified payment/account system later.

## Required Worker binding and secrets

The source-controlled `wrangler.toml` binds the Cloudflare KV namespace `RATAN_AI_TRIALS` as `TRIAL_KV`. Configure these as Worker secrets, never as source files or public variables:

```text
GEMINI_API_KEY       # Gemini API key from Google AI Studio
PAID_ACCESS_CODE     # Optional administrator-issued code after manual payment confirmation
```

The Worker returns `503` until the Gemini secret exists. The lawful-use system instruction and message-length limit remain enabled.

## Deployment

From this directory:

```bash
npx wrangler deploy --config wrangler.toml
npx wrangler secret put GEMINI_API_KEY
# Optional, only after choosing an activation-code workflow:
npx wrangler secret put PAID_ACCESS_CODE
```

The GitHub Pages site serves `/ai/` and `/ai/chat/` as static pages. The Worker serves `POST /chat` and `POST /trial`. The chat frontend defaults to `/api/ai/chat` and `/api/ai/trial`, which requires a reverse proxy mapping those paths to the Worker. If the Worker is hosted on its own `workers.dev` hostname, set `window.RATAN_AI_PROXY_URL` to the Worker URL plus `/chat` and optionally set `window.RATAN_AI_TRIAL_URL` to the Worker URL plus `/trial` before the chat script runs.

## Payment safety

India payments remain on the existing UPI/INR route. International payments remain on USDT ERC-20 only. Users should wait for written confirmation of the amount and network before paying, and should never share a UPI PIN, OTP, password, seed phrase or private key.

## Model and API references

The integration follows Google's Interactions API pattern and uses the current stable endpoint `gemini-3.7-flash`. See the [Gemini API key guidance](https://ai.google.dev/gemini-api/docs/api-key), [text-generation guide](https://ai.google.dev/gemini-api/docs/text-generation), and [model list](https://ai.google.dev/gemini-api/docs/models).
