import { describe, it, expect, beforeEach, beforeAll } from 'vitest';

// Override DATABASE_PATH to use in-memory DB for tests
// Must be set before the module is first imported
process.env.DATABASE_PATH = ':memory:';

// Re-import after env override (top-level await requires ESM)
const {
  initDb,
  insertArticle,
  getArticlesByStatus,
  updateArticleStatus,
  createTask,
  updateTask,
  getRecentTasks,
} = await import('../../lib/db');

describe('db', () => {
  beforeEach(() => {
    initDb();
  });

  it('init creates tables without throwing', () => {
    expect(() => initDb()).not.toThrow();
  });

  it('insertArticle returns id > 0 for new article', () => {
    const id = insertArticle({
      title: 'Test Article',
      content: 'Test content',
      source: 'Test Source',
      source_url: 'https://example.com/1',
      url_hash: 'abc123',
      published_at: new Date().toISOString(),
    });
    expect(id).toBeGreaterThan(0);
  });

  it('insertArticle returns 0 for duplicate url_hash', () => {
    insertArticle({ title: 'A', source_url: 'https://dup.com', url_hash: 'dup1' });
    const id2 = insertArticle({ title: 'B', source_url: 'https://dup.com/2', url_hash: 'dup1' });
    expect(id2).toBe(0);
  });

  it('getArticlesByStatus returns inserted articles with correct status', () => {
    insertArticle({ title: 'Test', source_url: 'https://a.com', url_hash: 'h1' });
    const articles = getArticlesByStatus('pending');
    expect(articles.length).toBeGreaterThanOrEqual(1);
    expect(articles[0].publish_status).toBe('pending');
  });

  it('updateArticleStatus changes status and sets summary', () => {
    const id = insertArticle({ title: 'T', source_url: 'https://b.com', url_hash: 'h2' });
    updateArticleStatus(id, 'summarized', 'My summary');
    const articles = getArticlesByStatus('summarized');
    expect(articles.some(a => a.id === id)).toBe(true);
    const updated = articles.find(a => a.id === id);
    expect(updated?.summary).toBe('My summary');
  });

  it('createTask and updateTask work correctly', () => {
    createTask('task-1', 'fetch', 10);
    updateTask('task-1', 'completed', 10, JSON.stringify({ ok: true }));
    const tasks = getRecentTasks(5);
    expect(tasks.length).toBeGreaterThanOrEqual(1);
    const task = (tasks as Array<{ task_id: string; status: string }>)
      .find(t => t.task_id === 'task-1');
    expect(task).toBeDefined();
    expect(task?.status).toBe('completed');
  });

  it('getArticlesByStatus with "all" returns all articles', () => {
    insertArticle({ title: 'All1', source_url: 'https://all1.com', url_hash: 'all1' });
    insertArticle({ title: 'All2', source_url: 'https://all2.com', url_hash: 'all2' });
    const all = getArticlesByStatus('all');
    expect(all.length).toBeGreaterThanOrEqual(2);
  });
});
