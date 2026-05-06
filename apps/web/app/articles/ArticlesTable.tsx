'use client';

import { useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';

interface Article {
  id: number;
  title: string;
  source: string;
  publish_status: string;
  created_at: string;
}

const statusColor: Record<string, string> = {
  pending: '#f59e0b',
  summarized: '#3b82f6',
  published: '#10b981',
  failed: '#ef4444',
};

export default function ArticlesTable({ articles }: { articles: Article[] }) {
  const router = useRouter();
  const [selected, setSelected] = useState<Set<number>>(new Set());
  const [busy, setBusy] = useState<'summarize' | 'publish' | null>(null);
  const [msg, setMsg] = useState<string>('');

  function toggle(id: number) {
    setSelected(prev => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }

  function toggleAll() {
    if (selected.size === articles.length) {
      setSelected(new Set());
    } else {
      setSelected(new Set(articles.map(a => a.id)));
    }
  }

  async function summarizeSelected() {
    if (!selected.size) return;
    setBusy('summarize');
    setMsg(`▶ Summarizing ${selected.size}...`);
    try {
      const res = await fetch('/api/summarize', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ articleIds: [...selected] }),
      });
      // drain SSE
      const text = await res.text();
      const last = text.trim().split('\n').filter(l => l.startsWith('data:')).pop();
      const evt = last ? JSON.parse(last.replace('data: ', '')) : {};
      setMsg(`✅ Summarized: ${evt.completed ?? 0}/${evt.total ?? selected.size}`);
      setSelected(new Set());
      router.refresh();
    } catch (err) {
      setMsg(`❌ ${err}`);
    } finally {
      setBusy(null);
    }
  }

  async function publishSelected() {
    if (!selected.size) return;
    setBusy('publish');
    setMsg(`▶ Publishing ${selected.size}...`);
    try {
      const res = await fetch('/api/publish', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ articleIds: [...selected] }),
      });
      const data = await res.json();
      setMsg(data.success ? `✅ Published: ${data.published}` : `❌ ${data.error ?? 'failed'}`);
      setSelected(new Set());
      router.refresh();
    } catch (err) {
      setMsg(`❌ ${err}`);
    } finally {
      setBusy(null);
    }
  }

  const allChecked = articles.length > 0 && selected.size === articles.length;
  const someChecked = selected.size > 0 && selected.size < articles.length;

  // Count eligible articles for each action based on lifecycle
  const selectedArticles = articles.filter(a => selected.has(a.id));
  const eligibleSummarize = selectedArticles.filter(a => a.publish_status === 'pending').length;
  const eligiblePublish = selectedArticles.filter(a => a.publish_status === 'summarized').length;

  return (
    <>
      {/* Bulk actions toolbar */}
      <div style={{
        display: 'flex',
        gap: '0.5rem',
        alignItems: 'center',
        marginBottom: '0.75rem',
        fontSize: '0.85rem',
        minHeight: '2rem',
        flexWrap: 'wrap',
      }}>
        <span style={{ color: '#6b7280' }}>
          已選 <strong>{selected.size}</strong> / {articles.length}
        </span>
        <button
          onClick={summarizeSelected}
          disabled={!eligibleSummarize || busy !== null}
          style={btn('#3b82f6', !eligibleSummarize || busy !== null)}
          title="只處理 pending 狀態的文章"
        >
          {busy === 'summarize' ? '⏳ Summarize…' : `🤖 Summarize ${eligibleSummarize} pending`}
        </button>
        <button
          onClick={publishSelected}
          disabled={!eligiblePublish || busy !== null}
          style={btn('#10b981', !eligiblePublish || busy !== null)}
          title="只處理 summarized 狀態的文章"
        >
          {busy === 'publish' ? '⏳ Publish…' : `📤 Publish ${eligiblePublish} summarized`}
        </button>
        {selected.size > eligibleSummarize + eligiblePublish && (
          <span style={{ color: '#9ca3af', fontSize: '0.75rem' }}>
            （{selected.size - eligibleSummarize - eligiblePublish} 篇狀態不符會跳過）
          </span>
        )}
        {msg && <span style={{ marginLeft: '0.5rem', color: '#6b7280', fontSize: '0.8rem' }}>{msg}</span>}
      </div>

      <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.875rem' }}>
        <thead>
          <tr style={{ borderBottom: '2px solid #e5e7eb', textAlign: 'left' }}>
            <th style={{ padding: '0.5rem', width: '2rem' }}>
              <input
                type="checkbox"
                checked={allChecked}
                ref={el => { if (el) el.indeterminate = someChecked; }}
                onChange={toggleAll}
                aria-label="select all"
              />
            </th>
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
              <td style={{ padding: '0.5rem' }}>
                <input
                  type="checkbox"
                  checked={selected.has(a.id)}
                  onChange={() => toggle(a.id)}
                  aria-label={`select article ${a.id}`}
                />
              </td>
              <td style={{ padding: '0.5rem', color: '#9ca3af' }}>{a.id}</td>
              <td style={{ padding: '0.5rem', maxWidth: '420px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                <Link href={`/articles/${a.id}`} style={{ color: '#1f2937', textDecoration: 'none' }}>
                  {a.title}
                </Link>
              </td>
              <td style={{ padding: '0.5rem', color: '#6b7280' }}>{a.source}</td>
              <td style={{ padding: '0.5rem' }}>
                <span style={{
                  background: statusColor[a.publish_status] ?? '#6b7280',
                  color: 'white',
                  padding: '0.125rem 0.5rem',
                  borderRadius: '9999px',
                  fontSize: '0.75rem',
                }}>
                  {a.publish_status}
                </span>
              </td>
              <td style={{ padding: '0.5rem', color: '#9ca3af', fontSize: '0.75rem' }}>{a.created_at?.slice(0, 16)}</td>
            </tr>
          ))}
          {articles.length === 0 && (
            <tr><td colSpan={6} style={{ padding: '2rem', textAlign: 'center', color: '#9ca3af' }}>沒有符合條件的文章</td></tr>
          )}
        </tbody>
      </table>
    </>
  );
}

function btn(bg: string, disabled: boolean): React.CSSProperties {
  return {
    padding: '0.375rem 0.875rem',
    background: disabled ? '#e5e7eb' : bg,
    color: disabled ? '#9ca3af' : 'white',
    border: 'none',
    borderRadius: '0.375rem',
    fontSize: '0.8rem',
    fontWeight: 600,
    cursor: disabled ? 'not-allowed' : 'pointer',
  };
}
