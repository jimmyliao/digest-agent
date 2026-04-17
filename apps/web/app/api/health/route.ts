import { NextResponse } from 'next/server';
import { getDb, initDb } from '@/lib/db';

export async function GET() {
  try {
    initDb();
    const db = getDb();
    db.query('SELECT 1').get();
    return NextResponse.json({
      status: 'ok',
      db: true,
      llm_provider: process.env.LLM_PROVIDER ?? 'gemini',
      timestamp: new Date().toISOString(),
    });
  } catch (err) {
    return NextResponse.json({ status: 'error', db: false, error: String(err) }, { status: 500 });
  }
}
