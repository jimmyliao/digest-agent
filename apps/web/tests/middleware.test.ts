/**
 * Tests for the Basic Auth middleware. Verifies:
 *  - public path (/api/health) bypasses auth
 *  - missing creds → 401 with WWW-Authenticate
 *  - wrong creds → 401
 *  - correct creds → next() (200-equivalent passthrough)
 *  - BASIC_AUTH_DISABLED=1 bypasses entirely
 */

import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import { NextRequest } from 'next/server';
import { middleware } from '@/middleware';

function makeReq(path: string, authHeader?: string): NextRequest {
  return new NextRequest('http://localhost' + path, {
    headers: authHeader ? { authorization: authHeader } : {},
  });
}

const basic = (u: string, p: string) =>
  'Basic ' + Buffer.from(`${u}:${p}`).toString('base64');

describe('middleware: HTTP Basic Auth', () => {
  beforeEach(() => {
    delete process.env.BASIC_AUTH_DISABLED;
    process.env.BASIC_AUTH_USER = 'jimmy';
    process.env.BASIC_AUTH_PASSWORD = 'secret';
  });

  afterEach(() => {
    delete process.env.BASIC_AUTH_USER;
    delete process.env.BASIC_AUTH_PASSWORD;
    delete process.env.BASIC_AUTH_DISABLED;
  });

  it('lets /api/health through with no auth', () => {
    const resp = middleware(makeReq('/api/health'));
    expect(resp.status).toBe(200); // NextResponse.next() default
  });

  it('returns 401 with no auth on protected path', () => {
    const resp = middleware(makeReq('/api/articles'));
    expect(resp.status).toBe(401);
    expect(resp.headers.get('www-authenticate')).toMatch(/Basic realm/i);
  });

  it('returns 401 on wrong creds', () => {
    const resp = middleware(
      makeReq('/api/articles', basic('jimmy', 'wrong')) as never,
    );
    expect(resp.status).toBe(401);
  });

  it('passes through on correct creds', () => {
    const resp = middleware(
      makeReq('/stock-analysis', basic('jimmy', 'secret')) as never,
    );
    expect(resp.status).toBe(200);
  });

  it('returns 503 when env unset (no silent defaults)', () => {
    delete process.env.BASIC_AUTH_USER;
    delete process.env.BASIC_AUTH_PASSWORD;
    const resp = middleware(makeReq('/'));
    expect(resp.status).toBe(503);
  });

  it('BASIC_AUTH_DISABLED=1 bypasses entirely', () => {
    process.env.BASIC_AUTH_DISABLED = '1';
    const resp = middleware(makeReq('/api/articles'));
    expect(resp.status).toBe(200);
  });
});
