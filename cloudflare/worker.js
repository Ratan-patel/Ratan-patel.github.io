const MODEL = 'gemini-3.7-flash';
const GEMINI_ENDPOINT = 'https://generativelanguage.googleapis.com/v1beta/interactions';
const ALLOWED_ORIGIN = 'https://ratan-patel.github.io';
const MAX_MESSAGE_LENGTH = 4000;

function corsHeaders(origin) {
  const allowed = origin === ALLOWED_ORIGIN || origin === 'http://127.0.0.1:8765' || origin === 'http://localhost:8765';
  return {
    'Access-Control-Allow-Origin': allowed ? origin : ALLOWED_ORIGIN,
    'Access-Control-Allow-Headers': 'Content-Type, X-Ratan-Access-Code',
    'Access-Control-Allow-Methods': 'POST, OPTIONS',
    'Vary': 'Origin',
  };
}

function json(data, status, origin) {
  return new Response(JSON.stringify(data), {
    status,
    headers: { 'Content-Type': 'application/json; charset=utf-8', ...corsHeaders(origin) },
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

export default {
  async fetch(request, env) {
    const origin = request.headers.get('Origin') || '';
    if (request.method === 'OPTIONS') return new Response(null, { status: 204, headers: corsHeaders(origin) });
    if (request.method !== 'POST') return json({ error: 'Use POST /chat.' }, 405, origin);
    if (!env.GEMINI_API_KEY) return json({ error: 'Gemini proxy is not configured.' }, 503, origin);
    if (!env.RATAN_AI_ACCESS_CODE) return json({ error: 'RATAN AI access is not configured yet.' }, 503, origin);
    if (request.headers.get('X-Ratan-Access-Code') !== env.RATAN_AI_ACCESS_CODE) return json({ error: 'Valid RATAN AI access is required.' }, 401, origin);

    let body;
    try { body = await request.json(); } catch { return json({ error: 'Request body must be JSON.' }, 400, origin); }
    const message = typeof body?.message === 'string' ? body.message.trim() : '';
    const email = typeof body?.email === 'string' ? body.email.trim().slice(0, 160) : '';
    const previousInteractionId = typeof body?.previousInteractionId === 'string' ? body.previousInteractionId.trim().slice(0, 180) : '';
    if (!message) return json({ error: 'Message is required.' }, 400, origin);
    if (message.length > MAX_MESSAGE_LENGTH) return json({ error: `Message must be ${MAX_MESSAGE_LENGTH} characters or fewer.` }, 413, origin);
    if (!email || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) return json({ error: 'A valid email is required.' }, 400, origin);

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
  },
};
