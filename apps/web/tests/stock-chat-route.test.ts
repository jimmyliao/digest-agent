/**
 * Tests for POST /api/stock-chat — verify SSE encoding and error paths.
 * The actual GEAP call is mocked via vertex-ai-stream module.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { NextRequest } from 'next/server';

// Mock the streaming helper before importing the route handler.
vi.mock('@/lib/vertex-ai-stream', () => ({
  streamReasoningEngine: vi.fn(),
}));

import { streamReasoningEngine } from '@/lib/vertex-ai-stream';
import { POST } from '@/app/api/stock-chat/route';

const mockStream = streamReasoningEngine as unknown as ReturnType<typeof vi.fn>;

async function* yieldEvents(events: unknown[]) {
  for (const e of events) yield e as never;
}

async function readSse(resp: Response): Promise<Array<Record<string, unknown>>> {
  const text = await resp.text();
  const lines = text.split('\n').filter(l => l.startsWith('data: '));
  return lines.map(l => JSON.parse(l.slice(6)));
}

function makeReq(body: unknown): NextRequest {
  return new NextRequest('http://localhost/api/stock-chat', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
}

describe('POST /api/stock-chat', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    process.env.GEAP_RESOURCE_NAME =
      'projects/test/locations/us-central1/reasoningEngines/123';
  });

  it('returns 400 when message missing', async () => {
    const resp = await POST(makeReq({}));
    expect(resp.status).toBe(400);
    const body = await resp.json();
    expect(body.error).toMatch(/message is required/);
  });

  it('returns 500 when GEAP_RESOURCE_NAME unset', async () => {
    delete process.env.GEAP_RESOURCE_NAME;
    const resp = await POST(makeReq({ message: 'hi' }));
    expect(resp.status).toBe(500);
    const body = await resp.json();
    expect(body.error).toMatch(/GEAP_RESOURCE_NAME/);
  });

  it('streams SSE events: start → event(s) → done', async () => {
    mockStream.mockImplementation(() =>
      yieldEvents([
        { author: 'news_collector', parts: [{ text: 'fetched' }] },
        { author: 'stock_orchestrator', parts: [{ text: 'final report' }] },
      ]) as never,
    );

    const resp = await POST(makeReq({ message: '台積電' }));
    expect(resp.status).toBe(200);
    expect(resp.headers.get('Content-Type')).toMatch(/text\/event-stream/);

    const events = await readSse(resp);
    expect(events[0]).toMatchObject({ type: 'start', message: '台積電' });
    expect(events).toContainEqual(
      expect.objectContaining({ type: 'event', author: 'news_collector' }),
    );
    expect(events).toContainEqual(
      expect.objectContaining({ type: 'event', author: 'stock_orchestrator' }),
    );
    expect(events.at(-1)).toMatchObject({ type: 'done' });
  });

  it('emits error event when GEAP throws', async () => {
    mockStream.mockImplementation(() => {
      throw new Error('Vertex AI 401: unauthorized');
    });

    const resp = await POST(makeReq({ message: '台積電' }));
    const events = await readSse(resp);
    const errEvent = events.find(e => e.type === 'error');
    expect(errEvent?.error).toMatch(/Vertex AI 401/);
  });
});
