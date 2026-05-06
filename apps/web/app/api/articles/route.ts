import { NextRequest, NextResponse } from 'next/server';
import { initDb, getArticlesByStatus } from '@/lib/db';

export async function GET(req: NextRequest) {
  initDb();
  const { searchParams } = new URL(req.url);
  const status = searchParams.get('status') ?? 'all';
  const limit = parseInt(searchParams.get('limit') ?? '50', 10);

  const articles = getArticlesByStatus(status, limit);
  return NextResponse.json({ articles, count: articles.length });
}
