import Link from 'next/link';
import { notFound } from 'next/navigation';

interface Article {
  id: number;
  title: string;
  content: string | null;
  summary: string | null;
  source: string | null;
  source_url: string | null;
  publish_status: string;
  published_at: string | null;
  created_at: string;
}

const statusColor: Record<string, string> = {
  pending: '#f59e0b',
  summarized: '#3b82f6',
  published: '#10b981',
  failed: '#ef4444',
};

export default async function ArticleDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id: idStr } = await params;
  const id = parseInt(idStr, 10);
  if (!Number.isFinite(id)) notFound();

  let article: Article | null = null;
  try {
    const { initDb, getArticleById } = await import('@/lib/db');
    initDb();
    article = getArticleById(id) as Article | null;
  } catch { /* db not ready */ }

  if (!article) notFound();

  return (
    <main style={{ padding: '2rem', fontFamily: 'monospace', maxWidth: '900px' }}>
      <Link href="/articles" style={{ fontSize: '0.85rem', color: '#6b7280', textDecoration: 'none' }}>
        ← 回 Articles
      </Link>

      <div style={{ marginTop: '0.75rem', display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
        <span style={{ fontSize: '0.75rem', color: '#9ca3af' }}>#{article.id}</span>
        <span style={{
          background: statusColor[article.publish_status] ?? '#6b7280',
          color: 'white',
          padding: '0.125rem 0.5rem',
          borderRadius: '9999px',
          fontSize: '0.75rem',
        }}>
          {article.publish_status}
        </span>
      </div>

      <h1 style={{ fontSize: '1.5rem', fontWeight: 'bold', marginTop: '0.5rem', marginBottom: '0.5rem', lineHeight: 1.3 }}>
        {article.title}
      </h1>

      <div style={{ fontSize: '0.85rem', color: '#6b7280', marginBottom: '1.5rem' }}>
        {article.source}
        {article.source_url && (
          <>
            {' · '}
            <a href={article.source_url} target="_blank" rel="noreferrer" style={{ color: '#46b3a5' }}>
              原文 ↗
            </a>
          </>
        )}
        {' · '}
        <span style={{ color: '#9ca3af' }}>建立於 {article.created_at?.slice(0, 16)}</span>
      </div>

      {article.summary && (
        <section style={{ marginBottom: '2rem' }}>
          <h2 style={{ fontSize: '0.95rem', fontWeight: 600, marginBottom: '0.5rem', color: '#3b82f6' }}>🤖 摘要</h2>
          <div style={{
            background: '#eff6ff',
            borderLeft: '3px solid #3b82f6',
            padding: '0.75rem 1rem',
            fontSize: '0.875rem',
            lineHeight: 1.7,
            whiteSpace: 'pre-wrap',
          }}>
            {article.summary}
          </div>
        </section>
      )}

      <section>
        <h2 style={{ fontSize: '0.95rem', fontWeight: 600, marginBottom: '0.5rem', color: '#6b7280' }}>原文內容</h2>
        <div style={{
          fontSize: '0.875rem',
          lineHeight: 1.7,
          color: '#374151',
          whiteSpace: 'pre-wrap',
        }}>
          {article.content || <em style={{ color: '#9ca3af' }}>（無內容）</em>}
        </div>
      </section>
    </main>
  );
}
