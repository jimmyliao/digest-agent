import { NextRequest, NextResponse } from 'next/server';
import { initDb, getDb, updateArticleStatus, createTask, updateTask } from '@/lib/db';
import { publishAll } from '@/lib/publishers';
import { randomUUID } from 'crypto';

export async function POST(req: NextRequest) {
  initDb();
  const db = getDb();
  const body = await req.json().catch(() => ({}));
  const channels: string[] = body.channels ?? ['telegram'];
  const articleIds: number[] | undefined = body.articleIds;

  // Only publish summarized articles (enforce lifecycle: summarized → published)
  let summarizedArticles: { id: number; title: string; summary: string; source: string }[];
  if (articleIds?.length) {
    summarizedArticles = articleIds
      .map(id => db.query("SELECT id, title, summary, source FROM articles WHERE id = ? AND publish_status = 'summarized'").get(id))
      .filter(Boolean) as { id: number; title: string; summary: string; source: string }[];
  } else {
    summarizedArticles = db.query(
      "SELECT id, title, summary, source FROM articles WHERE publish_status = 'summarized' LIMIT 20"
    ).all() as { id: number; title: string; summary: string; source: string }[];
  }

  if (summarizedArticles.length === 0) {
    return NextResponse.json({
      success: true,
      message: 'No summarized articles to publish',
      published: 0,
      channels,
    });
  }

  const taskId = randomUUID();
  createTask(taskId, 'publish', summarizedArticles.length);

  try {
    const results = await publishAll(summarizedArticles, channels);

    const allOk = results.some(r => r.success);
    if (allOk) {
      for (const article of summarizedArticles) {
        updateArticleStatus(article.id, 'published');
      }
    }

    updateTask(taskId, 'completed', summarizedArticles.length, JSON.stringify({ results }));

    return NextResponse.json({
      success: allOk,
      task_id: taskId,
      published: summarizedArticles.length,
      channels: results,
    });
  } catch (err) {
    updateTask(taskId, 'failed', 0, undefined, String(err));
    return NextResponse.json({ success: false, error: String(err) }, { status: 500 });
  }
}
