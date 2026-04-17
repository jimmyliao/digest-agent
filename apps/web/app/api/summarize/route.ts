import { NextRequest } from 'next/server';
import { initDb, getDb, updateArticleStatus, createTask, updateTask } from '@/lib/db';
import { getModel } from '@/lib/llm';
import { streamText } from 'ai';
import { randomUUID } from 'crypto';

export async function POST(req: NextRequest) {
  initDb();
  const db = getDb();

  const body = await req.json().catch(() => ({}));
  const provider = body.provider ?? process.env.LLM_PROVIDER ?? 'gemini';
  const articleIds: number[] | undefined = body.articleIds;

  // Get pending articles
  let articles: { id: number; title: string; content: string }[];
  if (articleIds?.length) {
    articles = articleIds
      .map(id => db.query('SELECT id, title, content FROM articles WHERE id = ?').get(id))
      .filter(Boolean) as { id: number; title: string; content: string }[];
  } else {
    articles = db
      .query("SELECT id, title, content FROM articles WHERE publish_status = 'pending' LIMIT 10")
      .all() as { id: number; title: string; content: string }[];
  }

  if (articles.length === 0) {
    return new Response(
      `data: ${JSON.stringify({ type: 'done', message: 'No pending articles' })}\n\n`,
      { headers: { 'Content-Type': 'text/event-stream', 'Cache-Control': 'no-cache' } }
    );
  }

  const taskId = randomUUID();
  createTask(taskId, 'summarize', articles.length);
  const model = getModel(provider as 'gemini' | 'claude');

  const encoder = new TextEncoder();

  const stream = new ReadableStream({
    async start(controller) {
      let completed = 0;

      // Send start event
      controller.enqueue(
        encoder.encode(
          `data: ${JSON.stringify({ type: 'start', task_id: taskId, total: articles.length, provider })}\n\n`
        )
      );

      for (const article of articles) {
        try {
          controller.enqueue(
            encoder.encode(
              `data: ${JSON.stringify({ type: 'article_start', id: article.id, title: article.title })}\n\n`
            )
          );

          // Use mock for test API keys
          let summary: string;
          if (
            (process.env.GEMINI_API_KEY ?? '').startsWith('test-') ||
            (process.env.ANTHROPIC_API_KEY ?? '').startsWith('test-')
          ) {
            summary = `[Mock] Summary of: ${article.title}`;
          } else {
            const result = await streamText({
              model,
              system: '你是新聞摘要助手。用繁體中文，3句話摘要以下新聞。簡潔、準確、重點突出。',
              prompt: `標題: ${article.title}\n\n內容: ${(article.content ?? '').slice(0, 2000)}`,
            });
            summary = '';
            for await (const chunk of result.textStream) {
              summary += chunk;
              controller.enqueue(
                encoder.encode(
                  `data: ${JSON.stringify({ type: 'chunk', id: article.id, chunk })}\n\n`
                )
              );
            }
          }

          updateArticleStatus(article.id, 'summarized', summary);
          completed++;
          updateTask(taskId, 'running', completed);

          controller.enqueue(
            encoder.encode(
              `data: ${JSON.stringify({ type: 'article_done', id: article.id, summary })}\n\n`
            )
          );
        } catch (err) {
          controller.enqueue(
            encoder.encode(
              `data: ${JSON.stringify({ type: 'article_error', id: article.id, error: String(err) })}\n\n`
            )
          );
        }
      }

      updateTask(taskId, 'completed', completed, JSON.stringify({ completed, total: articles.length }));
      controller.enqueue(
        encoder.encode(
          `data: ${JSON.stringify({ type: 'done', task_id: taskId, completed, total: articles.length })}\n\n`
        )
      );
      controller.close();
    },
  });

  return new Response(stream, {
    headers: {
      'Content-Type': 'text/event-stream',
      'Cache-Control': 'no-cache',
      'Connection': 'keep-alive',
    },
  });
}
