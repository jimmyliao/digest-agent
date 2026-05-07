/**
 * Stream events from a Vertex AI Reasoning Engine (GEAP).
 *
 * Calls the streamQuery REST endpoint with the ADK class_method
 * `async_stream_query`, parses the chunked NDJSON response, and yields
 * one event per line.
 *
 * Auth: uses Application Default Credentials. On Cloud Run this is the
 * runtime service account; locally this is whatever `gcloud auth
 * application-default login` set up.
 */

import { GoogleAuth } from 'google-auth-library';

export interface ReasoningEngineEvent {
  // ADK forwards the raw event dict; shape varies by step.
  // Common keys: parts (array of {text, function_call, function_response, ...}),
  // role ("model"|"user"), author (agent name).
  parts?: Array<{
    text?: string;
    function_call?: { name: string; args?: Record<string, unknown> };
    function_response?: { name: string; response?: Record<string, unknown> };
    [k: string]: unknown;
  }>;
  role?: string;
  author?: string;
  [k: string]: unknown;
}

const auth = new GoogleAuth({
  scopes: ['https://www.googleapis.com/auth/cloud-platform'],
});

function parseEngineLocation(engineName: string): string {
  // engineName: projects/PROJ/locations/LOC/reasoningEngines/ID
  const m = engineName.match(/locations\/([^/]+)\//);
  if (!m) throw new Error(`bad engineName: ${engineName}`);
  return m[1];
}

export async function* streamReasoningEngine(
  engineName: string,
  userId: string,
  message: string,
  signal?: AbortSignal,
): AsyncGenerator<ReasoningEngineEvent> {
  const location = parseEngineLocation(engineName);
  const url = `https://${location}-aiplatform.googleapis.com/v1/${engineName}:streamQuery?alt=sse`;

  const client = await auth.getClient();
  const tokenResp = await client.getAccessToken();
  const token = typeof tokenResp === 'string' ? tokenResp : tokenResp?.token;
  if (!token) throw new Error('failed to get ADC access token');

  const body = {
    class_method: 'async_stream_query',
    input: { user_id: userId, message },
  };

  const resp = await fetch(url, {
    method: 'POST',
    signal,
    headers: {
      Authorization: `Bearer ${token}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(body),
  });

  if (!resp.ok || !resp.body) {
    const errText = await resp.text().catch(() => '(no body)');
    throw new Error(`Vertex AI ${resp.status}: ${errText.slice(0, 500)}`);
  }

  const reader = resp.body.getReader();
  const decoder = new TextDecoder('utf-8');
  let buffer = '';

  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });

      // Vertex returns SSE-style lines OR NDJSON depending on alt= flag;
      // split on newline and try to parse anything that looks like JSON.
      let nl: number;
      while ((nl = buffer.indexOf('\n')) !== -1) {
        const line = buffer.slice(0, nl).trim();
        buffer = buffer.slice(nl + 1);
        if (!line) continue;
        const payload = line.startsWith('data: ') ? line.slice(6) : line;
        if (!payload || payload === '[DONE]') continue;
        try {
          yield JSON.parse(payload) as ReasoningEngineEvent;
        } catch {
          // ignore malformed line (partial JSON across chunks is handled by buffer)
        }
      }
    }
    // flush any trailing line
    const tail = buffer.trim();
    if (tail) {
      const payload = tail.startsWith('data: ') ? tail.slice(6) : tail;
      try {
        yield JSON.parse(payload) as ReasoningEngineEvent;
      } catch {
        /* ignore */
      }
    }
  } finally {
    reader.releaseLock();
  }
}
