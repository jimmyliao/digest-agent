import { NextRequest, NextResponse } from 'next/server';
import { initDb, createTask, updateTask } from '@/lib/db';
import { randomUUID } from 'crypto';

export async function POST(req: NextRequest) {
  initDb();
  const body = await req.json().catch(() => ({}));
  const steps: string[] = body.steps ?? ['fetch', 'summarize', 'publish'];
  const provider: string = body.provider ?? process.env.LLM_PROVIDER ?? 'gemini';

  const taskId = randomUUID();
  createTask(taskId, 'pipeline', steps.length);

  const results: Record<string, unknown> = {};
  let completed = 0;

  const baseUrl = process.env.NEXTAUTH_URL ?? 'http://localhost:3000';

  try {
    for (const step of steps) {
      if (step === 'fetch') {
        const res = await fetch(`${baseUrl}/api/fetch`, { method: 'POST' });
        results.fetch = await res.json();
      } else if (step === 'summarize') {
        // For pipeline, use non-streaming summarize via collecting SSE
        const res = await fetch(`${baseUrl}/api/summarize`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ provider }),
        });
        // Drain SSE stream and get last event
        const text = await res.text();
        const lastDataLine = text
          .trim()
          .split('\n')
          .filter(l => l.startsWith('data:'))
          .pop();
        results.summarize = lastDataLine ? JSON.parse(lastDataLine.replace('data: ', '')) : {};
      } else if (step === 'publish') {
        const res = await fetch(`${baseUrl}/api/publish`, { method: 'POST' });
        results.publish = await res.json();
      }
      completed++;
      updateTask(taskId, 'running', completed);
    }

    updateTask(taskId, 'completed', completed, JSON.stringify(results));
    return NextResponse.json({ success: true, task_id: taskId, results });
  } catch (err) {
    updateTask(taskId, 'failed', completed, undefined, String(err));
    return NextResponse.json({ success: false, task_id: taskId, error: String(err) }, { status: 500 });
  }
}
