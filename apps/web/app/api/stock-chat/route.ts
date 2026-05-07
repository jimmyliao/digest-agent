/**
 * POST /api/stock-chat — proxies a single user message to the deployed
 * Vertex AI Reasoning Engine and streams agent events back as SSE.
 *
 * Env:
 *   GEAP_RESOURCE_NAME  required, e.g. projects/.../reasoningEngines/NNNN
 *
 * Body: { "message": "鴻海 2317", "userId"?: "demo" }
 *
 * SSE events:
 *   data: {"type":"start"}\n\n
 *   data: {"type":"event","author":"news_collector","parts":[...]}\n\n
 *   data: {"type":"done"}\n\n
 *   data: {"type":"error","error":"..."}\n\n   (on failure)
 */

import { NextRequest } from 'next/server';
import { streamReasoningEngine } from '@/lib/vertex-ai-stream';

export const runtime = 'nodejs';
export const dynamic = 'force-dynamic';

export async function POST(req: NextRequest) {
  const engineName = process.env.GEAP_RESOURCE_NAME;
  if (!engineName) {
    return new Response(
      JSON.stringify({ error: 'GEAP_RESOURCE_NAME not set on server' }),
      { status: 500, headers: { 'Content-Type': 'application/json' } },
    );
  }

  const body = await req.json().catch(() => ({}));
  const message: string = body?.message ?? '';
  const userId: string = body?.userId ?? 'web-demo';
  if (!message.trim()) {
    return new Response(
      JSON.stringify({ error: 'message is required' }),
      { status: 400, headers: { 'Content-Type': 'application/json' } },
    );
  }

  const encoder = new TextEncoder();
  const stream = new ReadableStream({
    async start(controller) {
      const send = (obj: unknown) => {
        controller.enqueue(encoder.encode(`data: ${JSON.stringify(obj)}\n\n`));
      };

      send({ type: 'start', engine: engineName, message });

      // Quota meter — count Gemini API calls (events with role='model')
      // and tool invocations (function_call inside model events). Reported
      // in the final `done` event so the page can surface a "本次 N 次 LLM
      // 呼叫" line without consulting Cloud Console.
      const t0 = Date.now();
      let llmCalls = 0;
      let toolCalls = 0;

      try {
        for await (const event of streamReasoningEngine(
          engineName,
          userId,
          message,
          req.signal,
        )) {
          // Vertex AI returns events shaped as
          //   { author, content: { role, parts: [...] }, ... }
          // The page consumer expects parts at top level. Flatten so that
          // event.parts is the array.
          type RawPart = { function_call?: unknown; text?: unknown };
          type RawEvent = {
            author?: string;
            content?: { role?: string; parts?: RawPart[] };
            [k: string]: unknown;
          };
          const e = event as RawEvent;
          const parts: RawPart[] = e.content?.parts ?? (Array.isArray((e as { parts?: RawPart[] }).parts) ? (e as { parts?: RawPart[] }).parts! : []);
          const role = e.content?.role;

          if (role === 'model') {
            llmCalls += 1;
            for (const p of parts) {
              if (p?.function_call) toolCalls += 1;
            }
          }

          send({
            type: 'event',
            author: e.author,
            role,
            parts,
          });
        }
        send({
          type: 'done',
          llm_calls: llmCalls,
          tool_calls: toolCalls,
          duration_ms: Date.now() - t0,
        });
      } catch (err) {
        const msg = err instanceof Error ? err.message : String(err);
        send({ type: 'error', error: msg });
      } finally {
        controller.close();
      }
    },
  });

  return new Response(stream, {
    headers: {
      'Content-Type': 'text/event-stream; charset=utf-8',
      'Cache-Control': 'no-cache, no-transform',
      Connection: 'keep-alive',
      'X-Accel-Buffering': 'no',
    },
  });
}
