export default async function TasksPage() {
  let tasks: { task_id: string; task_type: string; status: string; progress_completed: number; progress_total: number; started_at: string; completed_at: string }[] = [];
  try {
    // Import db directly in server component
    const { initDb, getRecentTasks } = await import('@/lib/db');
    initDb();
    tasks = getRecentTasks(20) as typeof tasks;
  } catch { /* db not ready */ }

  const statusColor: Record<string, string> = {
    completed: '#10b981', running: '#3b82f6', failed: '#ef4444', queued: '#f59e0b',
  };

  return (
    <main style={{ padding: '2rem', fontFamily: 'monospace' }}>
      <h1 style={{ fontSize: '1.5rem', fontWeight: 'bold', marginBottom: '1rem' }}>
        📋 Task Records ({tasks.length})
      </h1>
      <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.875rem' }}>
        <thead>
          <tr style={{ borderBottom: '2px solid #e5e7eb', textAlign: 'left' }}>
            <th style={{ padding: '0.5rem' }}>Type</th>
            <th style={{ padding: '0.5rem' }}>Status</th>
            <th style={{ padding: '0.5rem' }}>Progress</th>
            <th style={{ padding: '0.5rem' }}>Started</th>
            <th style={{ padding: '0.5rem' }}>Task ID</th>
          </tr>
        </thead>
        <tbody>
          {tasks.map(t => (
            <tr key={t.task_id} style={{ borderBottom: '1px solid #f3f4f6' }}>
              <td style={{ padding: '0.5rem', fontWeight: 600 }}>{t.task_type}</td>
              <td style={{ padding: '0.5rem' }}>
                <span style={{ background: statusColor[t.status] ?? '#6b7280', color: 'white', padding: '0.125rem 0.5rem', borderRadius: '9999px', fontSize: '0.75rem' }}>
                  {t.status}
                </span>
              </td>
              <td style={{ padding: '0.5rem', color: '#6b7280' }}>{t.progress_completed}/{t.progress_total}</td>
              <td style={{ padding: '0.5rem', color: '#9ca3af', fontSize: '0.75rem' }}>{t.started_at?.slice(0, 16)}</td>
              <td style={{ padding: '0.5rem', color: '#9ca3af', fontSize: '0.75rem' }}>{t.task_id?.slice(0, 8)}…</td>
            </tr>
          ))}
          {tasks.length === 0 && (
            <tr><td colSpan={5} style={{ padding: '2rem', textAlign: 'center', color: '#9ca3af' }}>No tasks yet</td></tr>
          )}
        </tbody>
      </table>
    </main>
  );
}
