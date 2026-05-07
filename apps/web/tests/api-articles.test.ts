import { describe, it, expect, beforeEach, beforeAll } from 'vitest';

// In-memory SQLite + isolated module graph. Must run before any import that
// transitively pulls in lib/db.ts.
process.env.DATABASE_PATH = ':memory:';

// Dynamic import after env override
const { GET } = await import('../app/api/articles/route');
const { initDb, insertArticle, getDb } = await import('../lib/db');

function makeReq(qs: string = ''): Request {
  const url = `http://localhost:3000/api/articles${qs}`;
  // The route only uses NextRequest features that overlap with Request
  // (`new URL(req.url)`), so a stock Request works fine here.
  return new Request(url) as unknown as Request;
}

async function callGET(qs: string = ''): Promise<{ status: number; body: { articles: Array<Record<string, unknown>>; count: number } }> {
  // Cast: GET expects NextRequest, but at runtime the route reads only
  // `req.url`, which Request provides.
  const res = await (GET as unknown as (r: Request) => Promise<Response>)(makeReq(qs));
  return { status: res.status, body: await res.json() };
}

function clearArticles() {
  const db = getDb();
  db.run('DELETE FROM articles');
}

describe('GET /api/articles', () => {
  beforeAll(() => {
    initDb();
  });

  beforeEach(() => {
    initDb();
    clearArticles();
  });

  it('returns { articles: [], count: 0 } with 200 on empty DB', async () => {
    const { status, body } = await callGET();
    expect(status).toBe(200);
    expect(body).toEqual({ articles: [], count: 0 });
  });

  it('default request returns shape { articles: [...], count: N }', async () => {
    insertArticle({ title: 'A', source_url: 'https://a.com', url_hash: 'a' });
    insertArticle({ title: 'B', source_url: 'https://b.com', url_hash: 'b' });

    const { status, body } = await callGET();
    expect(status).toBe(200);
    expect(Array.isArray(body.articles)).toBe(true);
    expect(body.count).toBe(body.articles.length);
    expect(body.count).toBeGreaterThanOrEqual(2);
  });

  it('?company=TSMC filters by title or content (LIKE %TSMC%)', async () => {
    insertArticle({
      title: 'TSMC announces 2nm node',
      content: 'foundry roadmap',
      source_url: 'https://news.example.com/tsmc-2nm',
      url_hash: 'tsmc-1',
    });
    insertArticle({
      title: 'NVIDIA Blackwell shipping',
      content: 'made by TSMC',
      source_url: 'https://news.example.com/nv',
      url_hash: 'nv-1',
    });
    insertArticle({
      title: 'Apple unveils M5',
      content: 'no foundry mention here',
      source_url: 'https://news.example.com/apple',
      url_hash: 'apple-1',
    });

    const { status, body } = await callGET('?company=TSMC');
    expect(status).toBe(200);
    // Must include the title hit and the content hit, exclude the unrelated.
    const titles = body.articles.map(a => a.title as string);
    expect(titles).toContain('TSMC announces 2nm node');
    expect(titles).toContain('NVIDIA Blackwell shipping');
    expect(titles).not.toContain('Apple unveils M5');
    expect(body.count).toBe(2);
  });

  it('?limit=5 returns at most 5 articles', async () => {
    for (let i = 0; i < 12; i++) {
      insertArticle({
        title: `Article ${i}`,
        source_url: `https://e.com/${i}`,
        url_hash: `h-${i}`,
      });
    }

    const { status, body } = await callGET('?limit=5');
    expect(status).toBe(200);
    expect(body.articles.length).toBeLessThanOrEqual(5);
    expect(body.count).toBe(body.articles.length);
  });

  it('?company=Foo with no matches returns empty list, status 200', async () => {
    insertArticle({ title: 'Bar baz', source_url: 'https://x.com', url_hash: 'x' });
    const { status, body } = await callGET('?company=NonExistentCompanyZZZ');
    expect(status).toBe(200);
    expect(body.articles).toEqual([]);
    expect(body.count).toBe(0);
  });

  it('?limit clamps invalid / oversize values', async () => {
    for (let i = 0; i < 3; i++) {
      insertArticle({
        title: `Row ${i}`,
        source_url: `https://r.com/${i}`,
        url_hash: `r-${i}`,
      });
    }
    // limit=0 → falls back to default; should still return rows
    const a = await callGET('?limit=0');
    expect(a.status).toBe(200);
    expect(a.body.count).toBeGreaterThan(0);

    // limit=99999 → silently clamped, still returns ≤ MAX_LIMIT (200)
    const b = await callGET('?limit=99999');
    expect(b.status).toBe(200);
    expect(b.body.articles.length).toBeLessThanOrEqual(200);
  });
});
