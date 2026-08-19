const MODEL = 'gemini-3.7-flash';
const GEMINI_ENDPOINT = 'https://generativelanguage.googleapis.com/v1beta/interactions';
const ALLOWED_ORIGIN = 'https://ratan-patel.github.io';
const MAX_MESSAGE_LENGTH = 4000;
const TRIAL_SECONDS = 5 * 60;
const TRIAL_KEY_PREFIX = 'ratan-ai-trial:v1:';
const PAYMENT_URL = 'https://ratan-patel.github.io/ratan-monetization-launch-kit.html#payment-methods';

function corsHeaders(origin) {
  const allowed = origin === ALLOWED_ORIGIN || origin === 'http://127.0.0.1:8765' || origin === 'http://localhost:8765';
  return {
    'Access-Control-Allow-Origin': allowed ? origin : ALLOWED_ORIGIN,
    'Access-Control-Allow-Headers': 'Content-Type, X-Ratan-Access-Code',
    'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
    'Vary': 'Origin',
  };
}

function json(data, status, origin, extraHeaders = {}) {
  return new Response(JSON.stringify(data), {
    status,
    headers: { 'Content-Type': 'application/json; charset=utf-8', 'Cache-Control': 'no-store', ...corsHeaders(origin), ...extraHeaders },
  });
}

function getOutputText(payload) {
  if (typeof payload?.output_text === 'string') return payload.output_text;
  const steps = Array.isArray(payload?.steps) ? payload.steps : [];
  return steps
    .flatMap(step => Array.isArray(step?.content) ? step.content : [])
    .map(item => item?.text)
    .filter(text => typeof text === 'string')
    .join('\n')
    .trim();
}

function cleanClientId(value) {
  return typeof value === 'string' ? value.trim().slice(0, 120) : '';
}

async function sha256Hex(value) {
  const bytes = new TextEncoder().encode(value);
  const digest = await crypto.subtle.digest('SHA-256', bytes);
  return [...new Uint8Array(digest)].map(byte => byte.toString(16).padStart(2, '0')).join('');
}

async function trialKey(request, clientId) {
  const ip = request.headers.get('CF-Connecting-IP') || 'unknown-ip';
  const userAgent = request.headers.get('User-Agent') || 'unknown-agent';
  const fingerprint = await sha256Hex(`${ip}|${userAgent}|${clientId}`);
  return `${TRIAL_KEY_PREFIX}${fingerprint}`;
}

function trialResponse(state, origin) {
  const now = Date.now();
  const active = Number(state?.expiresAt || 0) > now;
  return {
    status: active ? 'active' : 'expired',
    startedAt: Number(state?.startedAt || 0),
    expiresAt: Number(state?.expiresAt || 0),
    remainingSeconds: active ? Math.max(0, Math.ceil((Number(state.expiresAt) - now) / 1000)) : 0,
    trialSeconds: TRIAL_SECONDS,
    paymentUrl: PAYMENT_URL,
  };
}

async function getOrStartTrial(request, env, clientId) {
  if (!env.TRIAL_KV) return { error: 'Trial storage is not configured.' };
  if (!clientId) return { error: 'A browser trial identifier is required.' };
  const key = await trialKey(request, clientId);
  const existing = await env.TRIAL_KV.get(key, 'json');
  if (existing) return { state: existing, key };
  const now = Date.now();
  const state = { version: 1, startedAt: now, expiresAt: now + TRIAL_SECONDS * 1000 };
  await env.TRIAL_KV.put(key, JSON.stringify(state), { expirationTtl: 60 * 60 * 24 * 30 });
  return { state, key };
}

async function handleTrial(request, env, body, origin) {
  const clientId = cleanClientId(body?.clientId);
  const result = await getOrStartTrial(request, env, clientId);
  if (result.error) return json({ error: result.error }, 503, origin);
  return json(trialResponse(result.state, origin), 200, origin);
}

async function handleChat(request, env, body, origin) {
  if (!env.GEMINI_API_KEY) return json({ error: 'Gemini proxy is not configured.' }, 503, origin);
  const message = typeof body?.message === 'string' ? body.message.trim() : '';
  const previousInteractionId = typeof body?.previousInteractionId === 'string' ? body.previousInteractionId.trim().slice(0, 180) : '';
  const clientId = cleanClientId(body?.clientId);
  if (!message) return json({ error: 'Message is required.' }, 400, origin);
  if (message.length > MAX_MESSAGE_LENGTH) return json({ error: `Message must be ${MAX_MESSAGE_LENGTH} characters or fewer.` }, 413, origin);

  const accessCode = request.headers.get('X-Ratan-Access-Code') || '';
  const paidAccessEnabled = Boolean(env.PAID_ACCESS_CODE && accessCode && accessCode === env.PAID_ACCESS_CODE);
  const trialResult = await getOrStartTrial(request, env, clientId);
  if (trialResult.error) return json({ error: trialResult.error }, 503, origin);
  const active = Number(trialResult.state.expiresAt) > Date.now();
  if (!active && !paidAccessEnabled) {
    return json({
      error: 'Your 5-minute free trial has ended.',
      trialExpired: true,
      paymentUrl: PAYMENT_URL,
      message: 'Please complete payment and request manual activation. India: UPI. International: USDT ERC-20 only.',
    }, 402, origin);
  }

  const input = {
    model: MODEL,
    system_instruction: 'You are RATAN AI V5, a white-hat cybersecurity learning assistant. Help only with lawful education, defensive design, secure coding, authorized assessment planning, report writing, remediation, threat modeling, and safe lab exercises. Refuse requests for credential theft, malware, persistence, evasion, destructive actions, unauthorized access, or targeting real third-party systems. Do not request or repeat passwords, API keys, private keys, or confidential customer data. Prefer synthetic examples and explain authorization boundaries briefly when relevant.',
    input: message,
    generation_config: { thinking_level: 'low' },
  };
  if (previousInteractionId) input.previous_interaction_id = previousInteractionId;

  const upstream = await fetch(GEMINI_ENDPOINT, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'x-goog-api-key': env.GEMINI_API_KEY },
    body: JSON.stringify(input),
  });
  const payload = await upstream.json().catch(() => ({}));
  if (!upstream.ok) return json({ error: 'Gemini service returned an error.', detail: payload?.error?.message || undefined }, upstream.status >= 500 ? 502 : upstream.status, origin);
  const text = getOutputText(payload);
  if (!text) return json({ error: 'Gemini returned no text output.' }, 502, origin);
  return json({ text, interactionId: typeof payload?.id === 'string' ? payload.id : '' }, 200, origin);
}

export default {
  async fetch(request, env) {
    const origin = request.headers.get('Origin') || '';
    if (request.method === 'OPTIONS') return new Response(null, { status: 204, headers: corsHeaders(origin) });
    const url = new URL(request.url);
    const route = url.pathname.replace(/\/+$/, '') || '/';
    if (route === '/health' && request.method === 'GET') return json({ ok: true, service: 'ratan-ai-api' }, 200, origin);
    if (route === '/trial' && request.method === 'POST') {
      let body;
      try { body = await request.json(); } catch { return json({ error: 'Request body must be JSON.' }, 400, origin); }
      return handleTrial(request, env, body, origin);
    }
    if (route !== '/chat') return json({ error: 'Use POST /chat or POST /trial.' }, 404, origin);
    if (request.method !== 'POST') return json({ error: 'Use POST /chat.' }, 405, origin);
    let body;
    try { body = await request.json(); } catch { return json({ error: 'Request body must be JSON.' }, 400, origin); }
    return handleChat(request, env, body, origin);
  },
};
