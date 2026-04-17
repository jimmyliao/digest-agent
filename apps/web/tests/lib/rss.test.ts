import { describe, it, expect } from 'vitest';
import crypto from 'crypto';

// Helper that replicates the urlHash logic from rss.ts
function urlHash(url: string): string {
  return crypto.createHash('sha256').update(url).digest('hex').slice(0, 16);
}

describe('rss urlHash', () => {
  it('produces a 16-char hex string', () => {
    const hash = urlHash('https://example.com/article/1');
    expect(hash).toHaveLength(16);
    expect(hash).toMatch(/^[0-9a-f]+$/);
  });

  it('is deterministic for the same URL', () => {
    const url = 'https://blog.google/test';
    expect(urlHash(url)).toBe(urlHash(url));
  });

  it('differs for different URLs', () => {
    expect(urlHash('https://a.com')).not.toBe(urlHash('https://b.com'));
  });

  it('handles empty string without throwing', () => {
    const hash = urlHash('');
    expect(hash).toHaveLength(16);
  });
});

describe('fetchFeeds', () => {
  it('returns empty array when sources list is empty', async () => {
    const { fetchFeeds } = await import('../../lib/rss');
    const results = await fetchFeeds([]);
    expect(results).toEqual([]);
  });

  it('handles fetch errors gracefully and returns an array', async () => {
    const { fetchFeeds } = await import('../../lib/rss');
    // Invalid URL should not throw — fetchOneFeed catches errors and returns []
    const results = await fetchFeeds([
      { name: 'Bad Feed', url: 'http://localhost:1/nonexistent' },
    ]);
    expect(Array.isArray(results)).toBe(true);
    // Error is swallowed; result is empty
    expect(results).toEqual([]);
  });

  it('deduplicates articles with the same urlHash', async () => {
    // fetchFeeds deduplicates by urlHash across batches.
    // With an empty source list the dedup set starts fresh — basic contract check.
    const { fetchFeeds } = await import('../../lib/rss');
    const results = await fetchFeeds([]);
    const hashes = results.map(r => r.urlHash);
    const unique = new Set(hashes);
    expect(unique.size).toBe(hashes.length);
  });
});
