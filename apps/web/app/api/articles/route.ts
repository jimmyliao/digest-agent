import { NextRequest, NextResponse } from 'next/server';
import { initDb, getArticlesByStatus, getDb, type Article } from '@/lib/db';

const DEFAULT_LIMIT = 50;
const MAX_LIMIT = 200;

function clampLimit(raw: string | null): number {
  const n = parseInt(raw ?? `${DEFAULT_LIMIT}`, 10);
  if (!Number.isFinite(n) || n <= 0) return DEFAULT_LIMIT;
  return Math.min(n, MAX_LIMIT);
}

export async function GET(req: NextRequest) {
  initDb();
  const { searchParams } = new URL(req.url);
  const status = searchParams.get('status') ?? 'all';
  const company = searchParams.get('company');
  const limit = clampLimit(searchParams.get('limit'));

  let articles: Article[];

  if (company && company.trim().length > 0) {
    // LIKE-based filter on title and content. Keep status filter compatible
    // with the existing default-shape ({ articles, count }) endpoint.
    const db = getDb();
    const like = `%${company.trim()}%`;
    if (status === 'all') {
      articles = db
        .query(
          `SELECT * FROM articles
             WHERE (title LIKE ? OR content LIKE ?)
             ORDER BY created_at DESC
             LIMIT ?`
        )
        .all(like, like, limit) as Article[];
    } else {
      articles = db
        .query(
          `SELECT * FROM articles
             WHERE publish_status = ?
               AND (title LIKE ? OR content LIKE ?)
             ORDER BY created_at DESC
             LIMIT ?`
        )
        .all(status, like, like, limit) as Article[];
    }
  } else {
    articles = getArticlesByStatus(status, limit);
  }

  return NextResponse.json({ articles, count: articles.length });
}
