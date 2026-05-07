/**
 * /api/stock-history
 *
 * GET  → list current user's stock analyses (metadata only, no events_json)
 * POST → insert a new stock analysis for the current user
 *
 * Auth: relies on the global Basic Auth middleware. The username from the
 * Authorization header is used purely to partition rows; we never trust the
 * client to supply a user_id.
 */

import { NextRequest, NextResponse } from 'next/server';
import {
  initDb,
  insertStockAnalysis,
  listStockAnalysesByUser,
} from '@/lib/db';
import { getBasicAuthUser } from '@/lib/auth';

const DEFAULT_LIMIT = 20;
const MAX_LIMIT = 200;

const QUERY_MAX_LEN = 500;
const EVENTS_MAX_COUNT = 500;
const EVENTS_JSON_MAX_BYTES = 200_000;

function clampLimit(raw: string | null): number {
  const n = parseInt(raw ?? `${DEFAULT_LIMIT}`, 10);
  if (!Number.isFinite(n) || n <= 0) return DEFAULT_LIMIT;
  return Math.min(n, MAX_LIMIT);
}

export async function GET(req: NextRequest) {
  initDb();
  const userId = getBasicAuthUser(req);
  const { searchParams } = new URL(req.url);
  const limit = clampLimit(searchParams.get('limit'));

  const items = listStockAnalysesByUser(userId, limit);
  return NextResponse.json({ items });
}

export async function POST(req: NextRequest) {
  initDb();
  const userId = getBasicAuthUser(req);

  let body: unknown;
  try {
    body = await req.json();
  } catch {
    return NextResponse.json({ error: 'invalid_json' }, { status: 400 });
  }

  if (!body || typeof body !== 'object') {
    return NextResponse.json({ error: 'invalid_body' }, { status: 400 });
  }

  const b = body as Record<string, unknown>;

  // query: required, non-empty, trimmed, ≤ 500 chars
  if (typeof b.query !== 'string') {
    return NextResponse.json({ error: 'query_required' }, { status: 400 });
  }
  const query = b.query.trim();
  if (query.length === 0) {
    return NextResponse.json({ error: 'query_required' }, { status: 400 });
  }
  if (query.length > QUERY_MAX_LEN) {
    return NextResponse.json({ error: 'query_too_long' }, { status: 400 });
  }

  // events: required array, length ≤ 500
  if (!Array.isArray(b.events)) {
    return NextResponse.json({ error: 'events_required' }, { status: 400 });
  }
  if (b.events.length > EVENTS_MAX_COUNT) {
    return NextResponse.json({ error: 'events_too_many' }, { status: 400 });
  }

  // events_json size cap → 413
  let eventsJson: string;
  try {
    eventsJson = JSON.stringify(b.events);
  } catch {
    return NextResponse.json({ error: 'events_unserializable' }, { status: 400 });
  }
  const eventsSize = Buffer.byteLength(eventsJson, 'utf8');
  if (eventsSize > EVENTS_JSON_MAX_BYTES) {
    return NextResponse.json(
      { error: 'events_payload_too_large', size: eventsSize, max: EVENTS_JSON_MAX_BYTES },
      { status: 413 },
    );
  }

  const llmCalls = typeof b.llm_calls === 'number' && Number.isFinite(b.llm_calls)
    ? Math.trunc(b.llm_calls)
    : null;
  const toolCalls = typeof b.tool_calls === 'number' && Number.isFinite(b.tool_calls)
    ? Math.trunc(b.tool_calls)
    : null;
  const durationMs = typeof b.duration_ms === 'number' && Number.isFinite(b.duration_ms)
    ? Math.trunc(b.duration_ms)
    : null;

  const id = insertStockAnalysis({
    user_id: userId,
    query,
    events_json: eventsJson,
    events_size: eventsSize,
    llm_calls: llmCalls,
    tool_calls: toolCalls,
    duration_ms: durationMs,
  });

  return NextResponse.json({ id }, { status: 201 });
}
