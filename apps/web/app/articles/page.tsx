import Link from 'next/link';
import ArticlesTable from './ArticlesTable';

const STATUSES = ['all', 'pending', 'summarized', 'published', 'failed'] as const;
const PAGE_SIZE = 20;

export default async function ArticlesPage({
  searchParams,
}: {
  searchParams: Promise<{ status?: string; page?: string }>;
}) {
  const params = await searchParams;
  const status = (params.status && STATUSES.includes(params.status as typeof STATUSES[number]))
    ? params.status
    : 'all';
  const page = Math.max(1, parseInt(params.page ?? '1', 10) || 1);
  const offset = (page - 1) * PAGE_SIZE;

  let articles: { id: number; title: string; source: string; publish_status: string; created_at: string }[] = [];
  let total = 0;
  let counts: Record<string, number> = {};
  try {
    const { initDb, getArticlesByStatus, countArticlesByStatus } = await import('@/lib/db');
    initDb();
    articles = getArticlesByStatus(status, PAGE_SIZE, offset) as typeof articles;
    total = countArticlesByStatus(status);
    for (const s of STATUSES) counts[s] = countArticlesByStatus(s);
  } catch { /* db not ready */ }

  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));

  return (
    <main style={{ padding: '2rem', fontFamily: 'monospace' }}>
      <h1 style={{ fontSize: '1.5rem', fontWeight: 'bold', marginBottom: '0.75rem' }}>
        📰 Articles ({total})
      </h1>

      {/* Status filter chips */}
      <div style={{ display: 'flex', gap: '0.5rem', marginBottom: '1rem', flexWrap: 'wrap' }}>
        {STATUSES.map(s => {
          const active = s === status;
          return (
            <Link
              key={s}
              href={`/articles?status=${s}`}
              style={{
                padding: '0.3rem 0.75rem',
                fontSize: '0.8rem',
                borderRadius: '9999px',
                border: `1px solid ${active ? '#1f2937' : '#e5e7eb'}`,
                background: active ? '#1f2937' : 'white',
                color: active ? 'white' : '#6b7280',
                textDecoration: 'none',
                fontWeight: active ? 600 : 400,
              }}
            >
              {s} <span style={{ color: active ? '#9ca3af' : '#9ca3af', fontSize: '0.75rem' }}>({counts[s] ?? 0})</span>
            </Link>
          );
        })}
      </div>

      <ArticlesTable articles={articles} />

      {/* Pagination */}
      {totalPages > 1 && (
        <div style={{ display: 'flex', gap: '0.5rem', marginTop: '1rem', alignItems: 'center', fontSize: '0.85rem' }}>
          <PageLink status={status} page={page - 1} disabled={page <= 1} label="← 上一頁" />
          <span style={{ color: '#6b7280' }}>{page} / {totalPages}</span>
          <PageLink status={status} page={page + 1} disabled={page >= totalPages} label="下一頁 →" />
          <span style={{ marginLeft: '0.5rem', color: '#9ca3af', fontSize: '0.75rem' }}>
            顯示 {offset + 1}-{Math.min(offset + PAGE_SIZE, total)} / {total}
          </span>
        </div>
      )}
    </main>
  );
}

function PageLink({ status, page, disabled, label }: {
  status: string;
  page: number;
  disabled: boolean;
  label: string;
}) {
  const style: React.CSSProperties = {
    padding: '0.3rem 0.75rem',
    border: '1px solid #e5e7eb',
    borderRadius: '0.375rem',
    fontSize: '0.8rem',
    textDecoration: 'none',
    color: disabled ? '#d1d5db' : '#374151',
    pointerEvents: disabled ? 'none' : 'auto',
    background: 'white',
  };
  if (disabled) return <span style={style}>{label}</span>;
  return <Link href={`/articles?status=${status}&page=${page}`} style={style}>{label}</Link>;
}
