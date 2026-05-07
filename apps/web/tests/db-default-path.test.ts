import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import { resolveDbPath } from '../lib/db';

describe('resolveDbPath', () => {
  const originalUrl = process.env.DATABASE_URL;
  const originalPath = process.env.DATABASE_PATH;

  beforeEach(() => {
    delete process.env.DATABASE_URL;
    delete process.env.DATABASE_PATH;
  });

  afterEach(() => {
    if (originalUrl === undefined) delete process.env.DATABASE_URL;
    else process.env.DATABASE_URL = originalUrl;
    if (originalPath === undefined) delete process.env.DATABASE_PATH;
    else process.env.DATABASE_PATH = originalPath;
  });

  it('defaults to /data/digest.db when neither DATABASE_URL nor DATABASE_PATH is set', () => {
    expect(resolveDbPath()).toBe('/data/digest.db');
  });

  it('honours DATABASE_URL with file:./ prefix (relative)', () => {
    process.env.DATABASE_URL = 'file:./data/digest.db';
    expect(resolveDbPath()).toBe('./data/digest.db');
  });

  it('honours DATABASE_URL with file:/ prefix (absolute)', () => {
    process.env.DATABASE_URL = 'file:/var/lib/digest.db';
    expect(resolveDbPath()).toBe('/var/lib/digest.db');
  });

  it('passes through DATABASE_URL without scheme as a literal path', () => {
    process.env.DATABASE_URL = '/tmp/raw.db';
    expect(resolveDbPath()).toBe('/tmp/raw.db');
  });

  it('DATABASE_PATH overrides DATABASE_URL', () => {
    process.env.DATABASE_URL = 'file:./should-be-ignored.db';
    process.env.DATABASE_PATH = ':memory:';
    expect(resolveDbPath()).toBe(':memory:');
  });

  it('empty DATABASE_URL is treated as unset', () => {
    process.env.DATABASE_URL = '';
    expect(resolveDbPath()).toBe('/data/digest.db');
  });

  it('empty DATABASE_PATH is treated as unset (falls through to URL/default)', () => {
    process.env.DATABASE_PATH = '';
    process.env.DATABASE_URL = 'file:/custom.db';
    expect(resolveDbPath()).toBe('/custom.db');
  });
});
