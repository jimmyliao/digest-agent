import Link from 'next/link';

export default function HomePage() {
  return (
    <main style={{ padding: '2rem', fontFamily: 'monospace', maxWidth: '700px' }}>
      <h1 style={{ fontSize: '2rem', fontWeight: 'bold', marginBottom: '0.5rem' }}>
        Digest Agent
      </h1>
      <p style={{ color: '#6b7280', marginBottom: '2rem' }}>
        AI-powered news digest &bull;{' '}
        <a href="https://leapchat.leapdesign.ai" style={{ color: '#46b3a5' }}>
          LeapChat
        </a>{' '}
        technology &middot; <a href="https://leapchat.leapdesign.ai" style={{ color: '#f09a3e' }}>Request beta access</a>
      </p>

      <nav style={{ display: 'flex', gap: '1rem', marginBottom: '3rem', flexWrap: 'wrap' }}>
        {[
          { href: '/publish', label: '🚀 Pipeline', desc: 'Fetch → Summarize → Publish' },
          { href: '/articles', label: '📰 Articles', desc: 'Browse fetched articles' },
          { href: '/tasks', label: '📋 Tasks', desc: 'Task execution history' },
        ].map(({ href, label, desc }) => (
          <Link key={href} href={href} style={{
            display: 'block', padding: '1rem 1.5rem', border: '1px solid #e5e7eb',
            borderRadius: '0.5rem', textDecoration: 'none', color: 'inherit',
            minWidth: '180px',
          }}>
            <div style={{ fontWeight: 700, marginBottom: '0.25rem' }}>{label}</div>
            <div style={{ fontSize: '0.8rem', color: '#9ca3af' }}>{desc}</div>
          </Link>
        ))}
      </nav>

      <div style={{ fontSize: '0.8rem', color: '#d1d5db', borderTop: '1px solid #f3f4f6', paddingTop: '1rem' }}>
        <strong>leapcore-iface</strong> &middot; ADK TypeScript &middot; Vercel AI SDK (Gemini + Claude) &middot; Claude Code
      </div>
    </main>
  );
}
