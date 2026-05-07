/**
 * auth.ts — Basic Auth user extraction for API route handlers.
 *
 * Mirrors the parsing logic in `middleware.ts`, but is intended for use inside
 * route handlers (Node runtime) where we just need the username for row
 * partitioning. The middleware (Edge runtime) is the actual auth gate; this
 * helper assumes the request has already been authenticated and never throws.
 *
 * If BASIC_AUTH_DISABLED=1 (local dev), or if the Authorization header is
 * missing / malformed, returns 'anon'. We deliberately avoid importing from
 * middleware.ts to keep Node and Edge runtimes decoupled.
 */

export function getBasicAuthUser(req: Request): string {
  if (process.env.BASIC_AUTH_DISABLED === '1') return 'anon';

  const header = req.headers.get('authorization') ?? '';
  if (!header.startsWith('Basic ')) return 'anon';

  try {
    const encoded = header.slice('Basic '.length);
    // atob is available in Node 18+ and Edge runtimes. Fall back to Buffer
    // when running under older environments / tooling.
    const decoded =
      typeof atob === 'function'
        ? atob(encoded)
        : Buffer.from(encoded, 'base64').toString('utf-8');
    const idx = decoded.indexOf(':');
    if (idx <= 0) return 'anon';
    const user = decoded.slice(0, idx);
    return user.length > 0 ? user : 'anon';
  } catch {
    return 'anon';
  }
}
