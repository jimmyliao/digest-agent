import Link from 'next/link';

export const metadata = {
  title: 'Digest Agent',
  description: 'AI-powered news digest',
}

const navItems = [
  { href: '/publish', label: '🚀 Pipeline' },
  { href: '/articles', label: '📰 Articles' },
  { href: '/tasks', label: '📋 Tasks' },
  { href: '/stock-analysis', label: '📈 Stock' },
];

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en">
      <body style={{ fontFamily: 'monospace', margin: 0 }}>
        <header style={{
          padding: '0.75rem 2rem',
          borderBottom: '1px solid #f3f4f6',
          display: 'flex',
          alignItems: 'center',
          gap: '1.5rem',
          flexWrap: 'wrap',
          position: 'sticky',
          top: 0,
          background: '#fff',
          zIndex: 10,
        }}>
          <Link href="/" style={{
            fontWeight: 700,
            fontSize: '1rem',
            textDecoration: 'none',
            color: 'inherit',
          }}>
            Digest Agent
          </Link>
          <nav style={{ display: 'flex', gap: '1rem', fontSize: '0.85rem' }}>
            {navItems.map(({ href, label }) => (
              <Link key={href} href={href} style={{
                textDecoration: 'none',
                color: '#6b7280',
              }}>
                {label}
              </Link>
            ))}
          </nav>
        </header>
        {children}
      </body>
    </html>
  )
}
