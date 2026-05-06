import crypto from 'crypto';

export interface RawArticle {
  title: string;
  content: string;
  source: string;
  sourceUrl: string;
  publishedAt: string;
  urlHash: string;
}

interface RssItem {
  title?: string;
  content?: string;
  contentSnippet?: string;
  link?: string;
  pubDate?: string;
  isoDate?: string;
}

function urlHash(url: string): string {
  return crypto.createHash('sha256').update(url).digest('hex').slice(0, 16);
}

async function fetchOneFeed(name: string, url: string, timeoutMs = 30000): Promise<RawArticle[]> {
  // Use rss-parser dynamically to avoid build-time issues
  const Parser = (await import('rss-parser')).default;
  const parser = new Parser({ timeout: timeoutMs });

  try {
    const feed = await parser.parseURL(url);
    return (feed.items as RssItem[]).slice(0, 20).map(item => ({
      title: item.title ?? '(no title)',
      content: item.content ?? item.contentSnippet ?? '',
      source: name,
      sourceUrl: item.link ?? url,
      publishedAt: item.isoDate ?? item.pubDate ?? new Date().toISOString(),
      urlHash: urlHash(item.link ?? item.title ?? Math.random().toString()),
    }));
  } catch (err) {
    console.warn(`[rss] Failed to fetch ${name}: ${err}`);
    return [];
  }
}

export interface FeedSource {
  name: string;
  url: string;
}

export async function fetchFeeds(sources: FeedSource[], maxConcurrent = 5): Promise<RawArticle[]> {
  const results: RawArticle[] = [];
  const seenHashes = new Set<string>();

  // Process in batches of maxConcurrent
  for (let i = 0; i < sources.length; i += maxConcurrent) {
    const batch = sources.slice(i, i + maxConcurrent);
    const batchResults = await Promise.allSettled(
      batch.map(s => fetchOneFeed(s.name, s.url))
    );
    for (const r of batchResults) {
      if (r.status === 'fulfilled') {
        for (const article of r.value) {
          if (!seenHashes.has(article.urlHash)) {
            seenHashes.add(article.urlHash);
            results.push(article);
          }
        }
      }
    }
  }

  return results;
}
