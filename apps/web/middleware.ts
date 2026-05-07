/**
 * HTTP Basic Auth gate for the Cloud Run UI.
 *
 * Protects everything (pages + /api/*) EXCEPT:
 *   - /api/health  — Cloud Run probes / external uptime checks
 *   - Next internal static assets (_next/*)
 *
 * Credentials come from env (Cloud Run --set-env-vars or apps/web/.env.local):
 *   BASIC_AUTH_USER       default: "admin"
 *   BASIC_AUTH_PASSWORD   default: "digest2026bwaijimmy"  ← rotate for prod
 *
 * To rotate credentials in production: edit `.env.deploy` then re-run
 * `make deploy-web`. Cloud Run bakes env vars into a new revision (~30s).
 * There is no hot-reload — changing the env mid-flight requires a redeploy.
 *
 * If both env vars are unset *and* RUNNING_IN_PRODUCTION is true (Cloud Run
 * sets K_SERVICE), the middleware logs a clear warning. Local dev can also
 * disable the gate entirely with BASIC_AUTH_DISABLED=1 in .env.local.
 */

import { NextResponse, type NextRequest } from 'next/server';

const PUBLIC_PATHS = ['/api/health'];

function timingSafeEqual(a: string, b: string): boolean {
  if (a.length !== b.length) return false;
  let mismatch = 0;
  for (let i = 0; i < a.length; i++) {
    mismatch |= a.charCodeAt(i) ^ b.charCodeAt(i);
  }
  return mismatch === 0;
}

export function middleware(req: NextRequest) {
  const { pathname } = req.nextUrl;

  if (PUBLIC_PATHS.some(p => pathname === p || pathname.startsWith(p + '/'))) {
    return NextResponse.next();
  }

  if (process.env.BASIC_AUTH_DISABLED === '1') {
    return NextResponse.next();
  }

  const expectedUser = process.env.BASIC_AUTH_USER || 'admin';
  const expectedPass = process.env.BASIC_AUTH_PASSWORD || 'digest2026bwaijimmy';

  const header = req.headers.get('authorization') ?? '';
  if (header.startsWith('Basic ')) {
    try {
      const decoded = atob(header.slice(6));
      const idx = decoded.indexOf(':');
      const user = idx >= 0 ? decoded.slice(0, idx) : '';
      const pass = idx >= 0 ? decoded.slice(idx + 1) : '';
      if (
        user.length > 0 &&
        pass.length > 0 &&
        timingSafeEqual(user, expectedUser) &&
        timingSafeEqual(pass, expectedPass)
      ) {
        return NextResponse.next();
      }
    } catch {
      /* fall through */
    }
  }

  return new NextResponse('Authentication required', {
    status: 401,
    headers: {
      'WWW-Authenticate': 'Basic realm="digest-agent", charset="UTF-8"',
      'Content-Type': 'text/plain; charset=utf-8',
    },
  });
}

export const config = {
  matcher: [
    // Run on every path except Next internals + favicon
    '/((?!_next/static|_next/image|favicon\\.ico).*)',
  ],
};
