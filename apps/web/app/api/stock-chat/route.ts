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
          // event.parts is the array (preserving raw event under .raw for
          // anyone who needs the original shape).
          type RawEvent = {
            author?: string;
            content?: { role?: string; parts?: unknown[] };
            [k: string]: unknown;
          };
          const e = event as RawEvent;
          const parts = e.content?.parts ?? (Array.isArray((e as { parts?: unknown[] }).parts) ? (e as { parts?: unknown[] }).parts : []);
          send({
            type: 'event',
            author: e.author,
            role: e.content?.role,
            parts,
          });
        }
        send({ type: 'done' });
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
