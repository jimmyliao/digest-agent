'use client';

/**
 * 個股分析 — Streamlit src/pages/4_stock_analysis.py 的 Next.js port.
 *
 * Streams agent events from the deployed GEAP reasoning engine via
 * /api/stock-chat (SSE). Renders a per-agent timeline plus the final
 * report (concatenated text from all model turns).
 */

import { useState, useRef, useEffect, useMemo } from 'react';

// localStorage cache so a browser refresh doesn't wipe the last analysis.
// Stored as JSON: { query, events, savedAt }. TTL not enforced — cleared
// manually via the "🗑 清除" button or when a new analysis starts.
const CACHE_KEY = 'digest-stock-last-analysis-v1';

interface AgentEvent {
  type: 'start' | 'event' | 'done' | 'error';
  engine?: string;
  message?: string;
  error?: string;
  // GEAP event passthrough (only present when type === 'event')
  author?: string;
  role?: string;
  parts?: Array<{
    text?: string;
    function_call?: { name: string; args?: Record<string, unknown> };
    function_response?: { name: string; response?: Record<string, unknown> };
  }>;
  // Quota meter (only present on type === 'done')
  llm_calls?: number;
  tool_calls?: number;
  duration_ms?: number;
}

const AGENT_ICONS: Record<string, string> = {
  news_collector: '📰',
  industry_analyst: '🏭',
  market_analyst: '📊',
  stock_orchestrator: '📋',
  report_writer: '📝',
};

export default function StockAnalysisPage() {
  const [query, setQuery] = useState('');
  const [running, setRunning] = useState(false);
  const [events, setEvents] = useState<AgentEvent[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [showDevTools, setShowDevTools] = useState(false);
  const [restoredAt, setRestoredAt] = useState<string | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  // Restore last analysis from localStorage on mount (no SSR access).
  useEffect(() => {
    try {
      const raw = typeof window !== 'undefined' && window.localStorage.getItem(CACHE_KEY);
      if (!raw) return;
      const cached = JSON.parse(raw) as { query: string; events: AgentEvent[]; savedAt: string };
      if (cached.events?.length) {
        setQuery(cached.query ?? '');
        setEvents(cached.events);
        setRestoredAt(cached.savedAt);
      }
    } catch { /* ignore corrupt cache */ }
    return () => abortRef.current?.abort();
  }, []);

  // Persist final state when analysis completes (running flips false with events).
  useEffect(() => {
    if (running) return;
    if (!events.some(e => e.type === 'event')) return;
    if (typeof window === 'undefined') return;
    try {
      window.localStorage.setItem(
        CACHE_KEY,
        JSON.stringify({ query, events, savedAt: new Date().toISOString() }),
      );
    } catch { /* quota / private mode → silently skip */ }
  }, [running, events, query]);

  function clearHistory() {
    if (typeof window !== 'undefined') window.localStorage.removeItem(CACHE_KEY);
    setEvents([]);
    setRestoredAt(null);
    setError(null);
  }

  // Memoized so typing in the input box doesn't re-flatMap on every keystroke.
  const finalText = useMemo(
    () => events
      .filter(e => e.type === 'event')
      .flatMap(e => (e.parts ?? []).map(p => p.text).filter(Boolean))
      .join('\n'),
    [events],
  );

  // Quota meter (from `done` event); falsy when run is in-flight or errored
  // before completion.
  const meter = useMemo(() => {
    const done = events.find(e => e.type === 'done');
    if (!done) return null;
    return {
      llm: done.llm_calls ?? 0,
      tool: done.tool_calls ?? 0,
      seconds: ((done.duration_ms ?? 0) / 1000).toFixed(1),
    };
  }, [events]);

  async function handleSubmit() {
    if (!query.trim() || running) return;
    setRunning(true);
    setEvents([]);
    setError(null);
    setRestoredAt(null);
    abortRef.current = new AbortController();
    try {
      const resp = await fetch('/api/stock-chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: query, userId: 'web-demo' }),
        signal: abortRef.current.signal,
      });
      if (!resp.body) throw new Error('no response body');
      const reader = resp.body.getReader();
      const decoder = new TextDecoder();
      let buf = '';
      while (true) {
        const { value, done } = await reader.read();
        if (done) break;
        buf += decoder.decode(value, { stream: true });
        let nl: number;
        while ((nl = buf.indexOf('\n\n')) !== -1) {
          const chunk = buf.slice(0, nl);
          buf = buf.slice(nl + 2);
          for (const line of chunk.split('\n')) {
            if (!line.startsWith('data: ')) continue;
            try {
              const evt = JSON.parse(line.slice(6)) as AgentEvent;
              setEvents(prev => [...prev, evt]);
              if (evt.type === 'error') setError(evt.error ?? 'unknown');
            } catch { /* skip malformed */ }
          }
        }
      }
    } catch (err) {
      if ((err as Error).name === 'AbortError') return;
      setError((err as Error).message);
    } finally {
      setRunning(false);
    }
  }

  return (
    <main style={{ padding: '2rem', fontFamily: 'monospace', maxWidth: '900px' }}>
      <h1 style={{ fontSize: '1.75rem', fontWeight: 'bold', marginBottom: '0.5rem' }}>
        📈 個股分析
      </h1>
      <p style={{ color: '#6b7280', marginBottom: '1.5rem', fontSize: '0.9rem' }}>
        ADK Multi-Agent 協作分析（GEAP）：新聞面 × 產業面 × 市場面
      </p>

      <div style={{ display: 'flex', gap: '0.5rem', marginBottom: '1rem' }}>
        <input
          type="text"
          value={query}
          onChange={e => setQuery(e.target.value)}
          onKeyDown={e => e.key === 'Enter' && handleSubmit()}
          placeholder="例如：2330 台積電、鴻海、聯發科"
          disabled={running}
          style={{
            flex: 1, padding: '0.5rem 0.75rem', fontSize: '0.95rem',
            border: '1px solid #e5e7eb', borderRadius: '0.375rem',
            fontFamily: 'inherit',
          }}
        />
        <button
          onClick={handleSubmit}
          disabled={running || !query.trim()}
          style={{
            padding: '0.5rem 1rem',
            background: running ? '#d1d5db' : '#46b3a5',
            color: 'white', border: 'none', borderRadius: '0.375rem',
            cursor: running ? 'not-allowed' : 'pointer',
            fontFamily: 'inherit', fontSize: '0.9rem',
          }}
        >
          {running ? '🤖 分析中...' : '🔍 開始分析'}
        </button>
        {(events.length > 0 || restoredAt) && !running && (
          <button
            onClick={clearHistory}
            title="清除瀏覽器快取的最後一次分析"
            style={{
              padding: '0.5rem 0.75rem', background: 'transparent',
              color: '#6b7280', border: '1px solid #e5e7eb',
              borderRadius: '0.375rem', cursor: 'pointer',
              fontFamily: 'inherit', fontSize: '0.85rem',
            }}
          >
            🗑 清除
          </button>
        )}
      </div>

      {restoredAt && !running && (
        <div style={{
          marginBottom: '1rem', padding: '0.5rem 0.75rem',
          background: '#fffbeb', border: '1px solid #fde68a',
          borderRadius: '0.375rem', fontSize: '0.8rem', color: '#92400e',
        }}>
          📂 從 localStorage 還原上次分析（{new Date(restoredAt).toLocaleString('zh-TW')}）。再次按「開始分析」會覆蓋。
        </div>
      )}

      {running && (
        <div style={{
          marginBottom: '1rem', padding: '0.75rem 1rem',
          background: '#f9fafb', borderRadius: '0.375rem',
          fontSize: '0.85rem', color: '#4b5563',
        }}>
          📰 news_collector → 🏭 industry_analyst → 📊 market_analyst → 📋 stock_orchestrator
          <br />
          串流中… 此頁直接連到 GEAP，每個 agent 完成會即時顯示。
        </div>
      )}

      {error && (
        <div style={{
          marginBottom: '1rem', padding: '0.75rem 1rem',
          background: '#fef2f2', border: '1px solid #fecaca',
          borderRadius: '0.375rem', color: '#991b1b', fontSize: '0.85rem',
        }}>
          ❌ {error}
        </div>
      )}

      {finalText && (
        <section style={{
          padding: '1rem 1.25rem', border: '1px solid #e5e7eb',
          borderRadius: '0.5rem', marginBottom: '1rem',
          whiteSpace: 'pre-wrap', fontSize: '0.9rem', lineHeight: 1.6,
        }}>
          {finalText}
        </section>
      )}

      {meter && (
        <div style={{
          marginBottom: '1rem', padding: '0.5rem 0.75rem',
          background: '#eff6ff', border: '1px solid #bfdbfe',
          borderRadius: '0.375rem', fontSize: '0.78rem', color: '#1e40af',
          fontFamily: 'monospace',
        }}>
          📊 本次：<strong>{meter.llm}</strong> 次 LLM 呼叫 ·{' '}
          <strong>{meter.tool}</strong> tool 呼叫 ·{' '}
          <strong>{meter.seconds}s</strong>
          {meter.llm > 0 && (
            <span style={{ color: '#6b7280', marginLeft: '0.75rem' }}>
              （Gemini free tier 1500 RPD ÷ {meter.llm} ≈ {Math.floor(1500 / meter.llm)} 次/天/key）
            </span>
          )}
        </div>
      )}

      {events.filter(e => e.type === 'event').length > 0 && (
        <section>
          <button
            onClick={() => setShowDevTools(s => !s)}
            style={{
              background: 'none', border: 'none', cursor: 'pointer',
              fontFamily: 'inherit', fontSize: '0.85rem', color: '#6b7280',
              padding: '0.25rem 0', marginBottom: '0.5rem',
            }}
          >
            {showDevTools ? '▼' : '▶'} 🔍 Agent 協作細節（{events.filter(e => e.type === 'event').length} 個事件）
          </button>
          {showDevTools && (
            <ol style={{ listStyle: 'none', padding: 0, margin: 0, fontSize: '0.8rem' }}>
              {events.filter(e => e.type === 'event').map((evt, i) => {
                const agent = evt.author ?? 'unknown';
                const icon = AGENT_ICONS[agent] ?? '🤖';
                return (
                  <li key={i} style={{
                    padding: '0.5rem 0.75rem',
                    borderLeft: '3px solid #46b3a5',
                    background: '#f9fafb', marginBottom: '0.5rem',
                  }}>
                    <strong>#{i + 1} {icon} {agent}</strong>
                    {(evt.parts ?? []).map((p, j) => (
                      <div key={j} style={{ marginTop: '0.25rem' }}>
                        {p.function_call && (
                          <code style={{ display: 'block', background: '#fff', padding: '0.25rem 0.5rem' }}>
                            🔧 {p.function_call.name}({JSON.stringify(p.function_call.args ?? {})})
                          </code>
                        )}
                        {p.function_response && (
                          <code style={{ display: 'block', background: '#fff', padding: '0.25rem 0.5rem', color: '#059669' }}>
                            ✅ {p.function_response.name} → {JSON.stringify(p.function_response.response ?? {}).slice(0, 200)}
                          </code>
                        )}
                        {p.text && (
                          <div style={{ color: '#4b5563', whiteSpace: 'pre-wrap' }}>
                            {p.text.length > 300 ? p.text.slice(0, 300) + '…' : p.text}
                          </div>
                        )}
                      </div>
                    ))}
                  </li>
                );
              })}
            </ol>
          )}
        </section>
      )}

      <p style={{ color: '#9ca3af', fontSize: '0.75rem', marginTop: '2rem' }}>
        ⚠️ 分析結果僅供參考，不構成任何投資建議。
      </p>
    </main>
  );
}
