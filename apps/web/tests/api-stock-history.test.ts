/**
 * Tests for /api/stock-history (list + insert) and /api/stock-history/[id].
 *
 * Uses an in-memory SQLite + dynamic-import pattern, mirroring
 * api-articles.test.ts.
 */

import { describe, it, expect, beforeEach, beforeAll } from 'vitest';

process.env.DATABASE_PATH = ':memory:';
// Ensure auth helper does not short-circuit to 'anon' for everyone.
delete process.env.BASIC_AUTH_DISABLED;

const { GET: listGET, POST: listPOST } = await import(
  '../app/api/stock-history/route'
);
const { GET: itemGET } = await import('../app/api/stock-history/[id]/route');
const { initDb, getDb } = await import('../lib/db');

function basicAuthHeader(user: string, pass: string = 'pw'): string {
  return 'Basic ' + Buffer.from(`${user}:${pass}`).toString('base64');
}

function makeReq(
  qs: string = '',
  init: { method?: string; body?: unknown; auth?: string } = {},
): Request {
  const url = `http://localhost:3000/api/stock-history${qs}`;
  const headers: Record<string, string> = {};
  if (init.auth) headers.authorization = init.auth;
  const reqInit: RequestInit = { method: init.method ?? 'GET', headers };
  if (init.body !== undefined) {
    headers['content-type'] = 'application/json';
    reqInit.body = JSON.stringify(init.body);
  }
  return new Request(url, reqInit);
}

function makeItemReq(id: string | number, auth?: string): Request {
  const url = `http://localhost:3000/api/stock-history/${id}`;
  const headers: Record<string, string> = {};
  if (auth) headers.authorization = auth;
  return new Request(url, { method: 'GET', headers });
}

type RouteFn = (req: Request) => Promise<Response>;
type ItemRouteFn = (
  req: Request,
  ctx: { params: Promise<{ id: string }> },
) => Promise<Response>;

async function callListGET(qs: string, auth: string) {
  const res = await (listGET as unknown as RouteFn)(makeReq(qs, { auth }));
  return { status: res.status, body: (await res.json()) as Record<string, unknown> };
}

async function callPOST(body: unknown, auth: string) {
  const res = await (listPOST as unknown as RouteFn)(
    makeReq('', { method: 'POST', body, auth }),
  );
  return { status: res.status, body: (await res.json()) as Record<string, unknown> };
}

async function callItemGET(id: string | number, auth: string) {
  const res = await (itemGET as unknown as ItemRouteFn)(
    makeItemReq(id, auth),
    { params: Promise.resolve({ id: String(id) }) },
  );
  return { status: res.status, body: (await res.json()) as Record<string, unknown> };
}

const ALICE = basicAuthHeader('alice');
const BOB = basicAuthHeader('bob');

function clearTable() {
  const db = getDb();
  db.run('DELETE FROM stock_analyses');
}

describe('/api/stock-history', () => {
  beforeAll(() => {
    initDb();
  });

  beforeEach(() => {
    initDb();
    clearTable();
  });

  it('POST then GET list → record visible to same user', async () => {
    const post = await callPOST(
      {
        query: 'TSMC outlook',
        events: [{ type: 'thought', text: 'analyzing' }],
        llm_calls: 2,
        tool_calls: 1,
        duration_ms: 1234,
      },
      ALICE,
    );
    expect(post.status).toBe(201);
    expect(typeof post.body.id).toBe('number');

    const list = await callListGET('', ALICE);
    expect(list.status).toBe(200);
    const items = list.body.items as Array<Record<string, unknown>>;
    expect(items.length).toBe(1);
    expect(items[0].query).toBe('TSMC outlook');
    expect(items[0].llm_calls).toBe(2);
    expect(items[0].tool_calls).toBe(1);
    expect(items[0].duration_ms).toBe(1234);
    // Metadata-only: must NOT include events_json
    expect(items[0].events_json).toBeUndefined();
    expect(items[0].events).toBeUndefined();
  });

  it('GET /[id] returns parsed events', async () => {
    const events = [
      { type: 'thought', text: 'step 1' },
      { type: 'tool', name: 'search', args: { q: 'TSMC' } },
    ];
    const post = await callPOST(
      { query: 'TSMC outlook', events, llm_calls: 3 },
      ALICE,
    );
    const id = post.body.id as number;

    const got = await callItemGET(id, ALICE);
    expect(got.status).toBe(200);
    expect(got.body.id).toBe(id);
    expect(got.body.query).toBe('TSMC outlook');
    expect(got.body.events).toEqual(events);
    expect(got.body.llm_calls).toBe(3);
  });

  it('user_id isolation: alice and bob only see their own rows', async () => {
    await callPOST({ query: 'alice q', events: [{ a: 1 }] }, ALICE);
    await callPOST({ query: 'bob q1', events: [{ b: 1 }] }, BOB);
    await callPOST({ query: 'bob q2', events: [{ b: 2 }] }, BOB);

    const aliceList = await callListGET('', ALICE);
    const bobList = await callListGET('', BOB);

    expect((aliceList.body.items as unknown[]).length).toBe(1);
    expect((bobList.body.items as unknown[]).length).toBe(2);
    const aliceQueries = (aliceList.body.items as Array<Record<string, unknown>>).map(
      x => x.query,
    );
    expect(aliceQueries).toEqual(['alice q']);
  });

  it('limit clamps oversize values to 200', async () => {
    // Insert just a few; we mainly check the response doesn't blow up and
    // that limit is applied via the SQL LIMIT (≤ 200).
    for (let i = 0; i < 3; i++) {
      await callPOST({ query: `q${i}`, events: [] }, ALICE);
    }
    const list = await callListGET('?limit=9999', ALICE);
    expect(list.status).toBe(200);
    const items = list.body.items as unknown[];
    expect(items.length).toBeLessThanOrEqual(200);
    expect(items.length).toBe(3);
  });

  it('POST without query → 400', async () => {
    const a = await callPOST({ events: [] }, ALICE);
    expect(a.status).toBe(400);

    const b = await callPOST({ query: '   ', events: [] }, ALICE);
    expect(b.status).toBe(400);
  });

  it('POST with > 500 events → 400', async () => {
    const events = Array.from({ length: 501 }, (_, i) => ({ i }));
    const r = await callPOST({ query: 'big', events }, ALICE);
    expect(r.status).toBe(400);
    expect(r.body.error).toBe('events_too_many');
  });

  it('POST with events_json > 200KB → 413', async () => {
    // 50 events × ~5KB each ≈ 250KB > 200KB cap
    const filler = 'x'.repeat(5000);
    const events = Array.from({ length: 50 }, (_, i) => ({ i, filler }));
    const r = await callPOST({ query: 'huge', events }, ALICE);
    expect(r.status).toBe(413);
    expect(r.body.error).toBe('events_payload_too_large');
  });

  it('GET single with wrong user → 404 (no leakage)', async () => {
    const post = await callPOST({ query: 'aliceonly', events: [] }, ALICE);
    const id = post.body.id as number;

    const asBob = await callItemGET(id, BOB);
    expect(asBob.status).toBe(404);
    // Same response shape as a truly missing row
    const missing = await callItemGET(999_999, BOB);
    expect(missing.status).toBe(404);
  });

  it('POST with query > 500 chars → 400', async () => {
    const r = await callPOST(
      { query: 'a'.repeat(501), events: [] },
      ALICE,
    );
    expect(r.status).toBe(400);
    expect(r.body.error).toBe('query_too_long');
  });

  it('POST without events array → 400', async () => {
    const r = await callPOST({ query: 'foo' }, ALICE);
    expect(r.status).toBe(400);
    expect(r.body.error).toBe('events_required');
  });
});
