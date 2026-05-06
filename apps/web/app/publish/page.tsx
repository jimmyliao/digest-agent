'use client';

import { useState, useRef, useEffect } from 'react';

type Step = 'fetch' | 'summarize' | 'publish';
type Provider = 'gemini' | 'claude';

interface StepResult {
  step: Step;
  success: boolean;
  data: unknown;
  error?: string;
}

interface PersistedState {
  provider: Provider;
  results: StepResult[];
  streamOutput: string[];
  savedAt: number;
}

const STORAGE_KEY = 'digest-agent:publish:v1';

function loadPersisted(): PersistedState | null {
  if (typeof window === 'undefined') return null;
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    return raw ? JSON.parse(raw) : null;
  } catch {
    return null;
  }
}

function formatRelative(ts: number): string {
  const diff = Date.now() - ts;
  const min = Math.floor(diff / 60000);
  if (min < 1) return '剛剛';
  if (min < 60) return `${min} 分鐘前`;
  const hr = Math.floor(min / 60);
  if (hr < 24) return `${hr} 小時前`;
  return `${Math.floor(hr / 24)} 天前`;
}

export default function PublishPage() {
  const [provider, setProvider] = useState<Provider>('gemini');
  const [running, setRunning] = useState<Step | null>(null);
  const [results, setResults] = useState<StepResult[]>([]);
  const [streamOutput, setStreamOutput] = useState<string[]>([]);
  const [savedAt, setSavedAt] = useState<number | null>(null);
  const [hydrated, setHydrated] = useState(false);
  const streamRef = useRef<HTMLDivElement>(null);

  // Hydrate from localStorage on mount
  useEffect(() => {
    const persisted = loadPersisted();
    if (persisted) {
      setProvider(persisted.provider);
      setResults(persisted.results);
      setStreamOutput(persisted.streamOutput);
      setSavedAt(persisted.savedAt);
    }
    setHydrated(true);
  }, []);

  // Persist on change (skip until hydrated to avoid overwriting with defaults)
  useEffect(() => {
    if (!hydrated) return;
    const ts = Date.now();
    const payload: PersistedState = { provider, results, streamOutput, savedAt: ts };
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(payload));
      setSavedAt(ts);
    } catch { /* quota exceeded — ignore */ }
  }, [provider, results, streamOutput, hydrated]);

  function clearPersisted() {
    localStorage.removeItem(STORAGE_KEY);
    setResults([]);
    setStreamOutput([]);
    setSavedAt(null);
  }

  useEffect(() => {
    if (streamRef.current) {
      streamRef.current.scrollTop = streamRef.current.scrollHeight;
    }
  }, [streamOutput]);

  function addStream(line: string) {
    setStreamOutput(prev => {
      const next = [...prev, line].slice(-50); // keep last 50 lines
      return next;
    });
    setTimeout(() => streamRef.current?.scrollTo(0, streamRef.current.scrollHeight), 50);
  }

  async function runFetch() {
    setRunning('fetch');
    addStream('▶ Fetching RSS feeds...');
    try {
      const res = await fetch('/api/fetch', { method: 'POST' });
      const data = await res.json();
      addStream(`✅ Fetched: ${data.fetched} articles, saved: ${data.saved}`);
      setResults(prev => [...prev, { step: 'fetch', success: data.success, data }]);
    } catch (err) {
      addStream(`❌ Fetch error: ${err}`);
      setResults(prev => [...prev, { step: 'fetch', success: false, data: {}, error: String(err) }]);
    } finally {
      setRunning(null);
    }
  }

  async function runSummarize() {
    setRunning('summarize');
    addStream(`▶ Summarizing with ${provider}...`);
    try {
      const res = await fetch('/api/summarize', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ provider }),
      });

      if (!res.body) throw new Error('No response body');
      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let done = false;

      while (!done) {
        const { value, done: d } = await reader.read();
        done = d;
        if (value) {
          const text = decoder.decode(value);
          const lines = text.split('\n').filter(l => l.startsWith('data: '));
          for (const line of lines) {
            try {
              const event = JSON.parse(line.replace('data: ', ''));
              if (event.type === 'start') addStream(`📋 ${event.total} articles to summarize`);
              else if (event.type === 'article_start') addStream(`  ⏳ ${event.title?.slice(0, 60)}...`);
              else if (event.type === 'chunk') process.stdout?.write?.(event.chunk ?? '');
              else if (event.type === 'article_done') addStream(`  ✅ Done: ${event.summary?.slice(0, 80)}...`);
              else if (event.type === 'done') {
                addStream(`✅ Summarized: ${event.completed}/${event.total}`);
                setResults(prev => [...prev, { step: 'summarize', success: true, data: event }]);
              }
            } catch { /* skip malformed */ }
          }
        }
      }
    } catch (err) {
      addStream(`❌ Summarize error: ${err}`);
      setResults(prev => [...prev, { step: 'summarize', success: false, data: {}, error: String(err) }]);
    } finally {
      setRunning(null);
    }
  }

  async function runPublish() {
    setRunning('publish');
    addStream('▶ Publishing to channels...');
    try {
      const res = await fetch('/api/publish', { method: 'POST' });
      const data = await res.json();
      addStream(`✅ Published: ${data.published} articles`);
      setResults(prev => [...prev, { step: 'publish', success: data.success, data }]);
    } catch (err) {
      addStream(`❌ Publish error: ${err}`);
      setResults(prev => [...prev, { step: 'publish', success: false, data: {}, error: String(err) }]);
    } finally {
      setRunning(null);
    }
  }

  const btnStyle = (disabled: boolean): React.CSSProperties => ({
    padding: '0.625rem 1.25rem',
    borderRadius: '0.375rem',
    border: 'none',
    cursor: disabled ? 'not-allowed' : 'pointer',
    opacity: disabled ? 0.5 : 1,
    fontWeight: 600,
    fontSize: '0.875rem',
  });

  return (
    <main style={{ padding: '2rem', fontFamily: 'monospace', maxWidth: '900px' }}>
      <h1 style={{ fontSize: '1.5rem', fontWeight: 'bold', marginBottom: '0.5rem' }}>🚀 Pipeline</h1>
      <p style={{ color: '#6b7280', marginBottom: '1.5rem', fontSize: '0.875rem' }}>
        Powered by{' '}
        <a href="https://leapchat.leapdesign.ai" style={{ color: '#46b3a5' }}>LeapChat</a> technology
      </p>

      {/* Provider selector */}
      <div style={{ marginBottom: '1.5rem', display: 'flex', alignItems: 'center', gap: '1rem' }}>
        <label style={{ fontWeight: 600, fontSize: '0.875rem' }}>LLM Provider:</label>
        <select
          value={provider}
          onChange={e => setProvider(e.target.value as Provider)}
          style={{ padding: '0.375rem 0.75rem', borderRadius: '0.375rem', border: '1px solid #d1d5db', fontSize: '0.875rem' }}
        >
          <option value="gemini">Gemini 2.5 Flash</option>
          <option value="claude">Claude Sonnet 4.6</option>
        </select>
      </div>

      {/* Action buttons */}
      <div style={{ display: 'flex', gap: '0.75rem', marginBottom: '1.5rem' }}>
        <button
          onClick={runFetch}
          disabled={running !== null}
          style={{ ...btnStyle(running !== null), background: '#f59e0b', color: 'white' }}
        >
          {running === 'fetch' ? '⏳ Fetching...' : '📡 Fetch'}
        </button>
        <button
          onClick={runSummarize}
          disabled={running !== null}
          style={{ ...btnStyle(running !== null), background: '#3b82f6', color: 'white' }}
        >
          {running === 'summarize' ? '⏳ Summarizing...' : '🤖 Summarize'}
        </button>
        <button
          onClick={runPublish}
          disabled={running !== null}
          style={{ ...btnStyle(running !== null), background: '#10b981', color: 'white' }}
        >
          {running === 'publish' ? '⏳ Publishing...' : '📤 Publish'}
        </button>
      </div>

      {/* Stream output */}
      <div
        ref={streamRef}
        style={{
          background: '#111827', color: '#d1fae5', fontFamily: 'monospace',
          fontSize: '0.8rem', padding: '1rem', borderRadius: '0.5rem',
          height: '300px', overflowY: 'auto', marginBottom: '1.5rem',
          lineHeight: '1.6',
        }}
      >
        {streamOutput.length === 0
          ? <span style={{ color: '#6b7280' }}>$ waiting for pipeline...</span>
          : streamOutput.map((line, i) => <div key={i}>{line}</div>)
        }
      </div>

      {/* Results */}
      {results.length > 0 && (
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '0.5rem' }}>
            <h2 style={{ fontSize: '1rem', fontWeight: 600, margin: 0 }}>Results</h2>
            {savedAt && (
              <span style={{ fontSize: '0.75rem', color: '#9ca3af' }}>
                上次執行：{formatRelative(savedAt)}
              </span>
            )}
            <button
              onClick={clearPersisted}
              style={{
                marginLeft: 'auto',
                padding: '0.25rem 0.625rem',
                fontSize: '0.7rem',
                border: '1px solid #e5e7eb',
                borderRadius: '0.25rem',
                background: 'white',
                color: '#6b7280',
                cursor: 'pointer',
              }}
            >
              清除
            </button>
          </div>
          {results.map((r, i) => (
            <div key={i} style={{
              padding: '0.5rem 0.75rem', marginBottom: '0.5rem',
              background: r.success ? '#f0fdf4' : '#fef2f2',
              borderLeft: `3px solid ${r.success ? '#10b981' : '#ef4444'}`,
              fontSize: '0.8rem',
            }}>
              <strong>{r.step}</strong>: {r.success ? '✅' : '❌'} {JSON.stringify(r.data).slice(0, 120)}
            </div>
          ))}
        </div>
      )}
    </main>
  );
}
