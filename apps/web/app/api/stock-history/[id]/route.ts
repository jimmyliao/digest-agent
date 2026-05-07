/**
 * /api/stock-history/[id]
 *
 * GET → return one stock analysis record (with parsed events) for the
 *       current user. Returns 404 if the row does not exist OR if it belongs
 *       to a different user — we never leak existence to other users.
 */

import { NextRequest, NextResponse } from 'next/server';
import { initDb, getStockAnalysisById } from '@/lib/db';
import { getBasicAuthUser } from '@/lib/auth';

export async function GET(
  req: NextRequest,
  ctx: { params: Promise<{ id: string }> },
) {
  initDb();
  const userId = getBasicAuthUser(req);

  const { id: rawId } = await ctx.params;
  const id = parseInt(rawId, 10);
  if (!Number.isFinite(id) || id <= 0) {
    return NextResponse.json({ error: 'not_found' }, { status: 404 });
  }

  const row = getStockAnalysisById(id);
  if (!row || row.user_id !== userId) {
    return NextResponse.json({ error: 'not_found' }, { status: 404 });
  }

  let events: unknown[] = [];
  try {
    const parsed = JSON.parse(row.events_json);
    events = Array.isArray(parsed) ? parsed : [];
  } catch {
    events = [];
  }

  return NextResponse.json({
    id: row.id,
    query: row.query,
    events,
    llm_calls: row.llm_calls,
    tool_calls: row.tool_calls,
    duration_ms: row.duration_ms,
    created_at: row.created_at,
  });
}
