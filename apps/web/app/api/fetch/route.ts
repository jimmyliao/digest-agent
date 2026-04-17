import { NextResponse } from 'next/server';
import { initDb, getDb, insertArticle, createTask, updateTask } from '@/lib/db';
import { fetchFeeds } from '@/lib/rss';
import { randomUUID } from 'crypto';

export async function POST() {
  initDb();
  const db = getDb();

  const taskId = randomUUID();
  createTask(taskId, 'fetch');

  try {
    // Get enabled sources from DB
    const sources = db.query('SELECT name, url FROM sources WHERE enabled = 1').all() as { name: string; url: string }[];

    const articles = await fetchFeeds(sources);

    let saved = 0;
    for (const article of articles) {
      const id = insertArticle({
        title: article.title,
        content: article.content,
        source: article.source,
        source_url: article.sourceUrl,
        url_hash: article.urlHash,
        published_at: article.publishedAt,
      });
      if (id > 0) saved++;
    }

    updateTask(taskId, 'completed', saved, JSON.stringify({ fetched: articles.length, saved }));

    return NextResponse.json({
      success: true,
      task_id: taskId,
      fetched: articles.length,
      saved,
      deduplicated: articles.length - saved,
    });
  } catch (err) {
    updateTask(taskId, 'failed', 0, undefined, String(err));
    return NextResponse.json({ success: false, error: String(err) }, { status: 500 });
  }
}
