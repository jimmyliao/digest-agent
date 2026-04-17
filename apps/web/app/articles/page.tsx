export default async function ArticlesPage() {
  let articles: { id: number; title: string; source: string; publish_status: string; created_at: string }[] = [];
  try {
    const res = await fetch('http://localhost:3000/api/articles?limit=50', { cache: 'no-store' });
    const data = await res.json();
    articles = data.articles ?? [];
  } catch {
    // dev: server may not be running yet
  }

  const statusColor: Record<string, string> = {
    pending: '#f59e0b',
    summarized: '#3b82f6',
    published: '#10b981',
  };

  return (
    <main style={{ padding: '2rem', fontFamily: 'monospace' }}>
      <h1 style={{ fontSize: '1.5rem', fontWeight: 'bold', marginBottom: '1rem' }}>
        📰 Articles ({articles.length})
      </h1>
      <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.875rem' }}>
        <thead>
          <tr style={{ borderBottom: '2px solid #e5e7eb', textAlign: 'left' }}>
            <th style={{ padding: '0.5rem' }}>ID</th>
            <th style={{ padding: '0.5rem' }}>Title</th>
            <th style={{ padding: '0.5rem' }}>Source</th>
            <th style={{ padding: '0.5rem' }}>Status</th>
            <th style={{ padding: '0.5rem' }}>Created</th>
          </tr>
        </thead>
        <tbody>
          {articles.map(a => (
            <tr key={a.id} style={{ borderBottom: '1px solid #f3f4f6' }}>
              <td style={{ padding: '0.5rem', color: '#9ca3af' }}>{a.id}</td>
              <td style={{ padding: '0.5rem', maxWidth: '400px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{a.title}</td>
              <td style={{ padding: '0.5rem', color: '#6b7280' }}>{a.source}</td>
              <td style={{ padding: '0.5rem' }}>
                <span style={{ background: statusColor[a.publish_status] ?? '#6b7280', color: 'white', padding: '0.125rem 0.5rem', borderRadius: '9999px', fontSize: '0.75rem' }}>
                  {a.publish_status}
                </span>
              </td>
              <td style={{ padding: '0.5rem', color: '#9ca3af', fontSize: '0.75rem' }}>{a.created_at?.slice(0, 16)}</td>
            </tr>
          ))}
          {articles.length === 0 && (
            <tr><td colSpan={5} style={{ padding: '2rem', textAlign: 'center', color: '#9ca3af' }}>No articles yet — run Fetch from the Publish page</td></tr>
          )}
        </tbody>
      </table>
    </main>
  );
}
