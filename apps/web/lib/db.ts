/**
 * db.ts — Cross-runtime SQLite adapter
 *
 * Runtime detection:
 *   - Bun  → uses bun:sqlite (native, zero-dependency)
 *   - Node → uses better-sqlite3 (npm package)
 *
 * Next.js dev server runs under Node, so we use better-sqlite3 there.
 * `bun run start` (standalone) runs under Bun and uses bun:sqlite.
 */

import path from 'path';

/**
 * Resolve the SQLite path from environment.
 *
 * Priority:
 *   1. DATABASE_PATH         — raw path override (legacy / test convenience).
 *                              Supports ":memory:" for in-process tests.
 *   2. DATABASE_URL          — preferred, file:-style URL.
 *                                "file:./data/digest.db"  → "./data/digest.db"
 *                                "file:/data/digest.db"   → "/data/digest.db"
 *   3. Default               — "/data/digest.db" (container-ready, matches
 *                              Litestream replication mount in production).
 *                              Local dev should set DATABASE_URL=file:./data/digest.db
 *                              in .env.local to keep the DB inside the workspace.
 */
export function resolveDbPath(): string {
  const raw = process.env.DATABASE_PATH;
  if (raw && raw.length > 0) return raw;

  const url = process.env.DATABASE_URL;
  if (url && url.length > 0) {
    // Strip optional file: scheme; everything else is treated as a literal path
    if (url.startsWith('file:')) return url.slice('file:'.length);
    return url;
  }

  return '/data/digest.db';
}

const DB_PATH = resolveDbPath();

// ── Unified thin interface ──────────────────────────────────────────────────
interface StmtLike {
  run(...args: unknown[]): { lastInsertRowid: number | bigint; changes?: number };
  all(...args: unknown[]): unknown[];
  get(...args: unknown[]): unknown;
}

interface DbLike {
  run(sql: string, params?: unknown[]): void;
  prepare(sql: string): StmtLike;
  query(sql: string): StmtLike;
}

// ── Bun adapter ──────────────────────────────────────────────────────────────
// `bun:sqlite` types ship with `bun-types`, which we deliberately don't add as
// a devDependency (this app's build runs under Node, not Bun). The shape is
// duck-typed at runtime; we accept a structural fragment here.
type BunSqliteModule = {
  Database: new (
    path: string,
    opts?: { create?: boolean; readwrite?: boolean }
  ) => {
    run: (sql: string, params?: unknown[]) => void;
    prepare: (sql: string) => {
      run: (...args: unknown[]) => { lastInsertRowid: number | bigint; changes: number };
      all: (...args: unknown[]) => unknown[];
      get: (...args: unknown[]) => unknown;
    };
    query: (sql: string) => {
      run: (...args: unknown[]) => { lastInsertRowid: number | bigint; changes: number };
      all: (...args: unknown[]) => unknown[];
      get: (...args: unknown[]) => unknown;
    };
  };
};

function makeBunDb(bunSqlite: BunSqliteModule): DbLike {
  const { Database } = bunSqlite;
  const raw = new Database(DB_PATH, { create: true });
  raw.run('PRAGMA journal_mode = WAL');
  raw.run('PRAGMA foreign_keys = ON');

  return {
    run(sql, params = []) { raw.run(sql, params as string[]); },
    prepare(sql) {
      const stmt = raw.prepare(sql);
      return {
        run: (...args) => {
          const r = stmt.run(...args as string[]);
          return { lastInsertRowid: r.lastInsertRowid as number, changes: r.changes as number };
        },
        all: (...args) => stmt.all(...args as string[]),
        get:  (...args) => stmt.get(...args as string[]),
      };
    },
    query(sql) {
      const stmt = raw.query(sql);
      return {
        run: (...args) => {
          const r = stmt.run(...args as string[]);
          return { lastInsertRowid: r.lastInsertRowid as number, changes: r.changes as number };
        },
        all: (...args) => stmt.all(...args as string[]),
        get:  (...args) => stmt.get(...args as string[]),
      };
    },
  };
}

// ── Node adapter (better-sqlite3) ────────────────────────────────────────────
function makeNodeDb(BetterSqlite3: typeof import('better-sqlite3')): DbLike {
  const raw = new BetterSqlite3(DB_PATH, { fileMustExist: false });
  raw.pragma('journal_mode = WAL');
  raw.pragma('foreign_keys = ON');

  return {
    run(sql, params = []) { raw.prepare(sql).run(...params); },
    prepare(sql) {
      const stmt = raw.prepare(sql);
      return {
        run: (...args) => {
          const r = stmt.run(...args) as { lastInsertRowid: number; changes: number };
          return { lastInsertRowid: r.lastInsertRowid, changes: r.changes };
        },
        all: (...args) => stmt.all(...args) as unknown[],
        get:  (...args) => stmt.get(...args),
      };
    },
    query(sql) {
      const stmt = raw.prepare(sql);
      return {
        run: (...args) => {
          const r = stmt.run(...args) as { lastInsertRowid: number; changes: number };
          return { lastInsertRowid: r.lastInsertRowid, changes: r.changes };
        },
        all: (...args) => stmt.all(...args) as unknown[],
        get:  (...args) => stmt.get(...args),
      };
    },
  };
}

// ── Singleton ────────────────────────────────────────────────────────────────
let _db: DbLike | null = null;

function getDb(): DbLike {
  if (_db) return _db;

  // Ensure data directory exists
  const fs = require('fs') as typeof import('fs');
  const dir = path.dirname(DB_PATH);
  if (!fs.existsSync(dir)) fs.mkdirSync(dir, { recursive: true });

  const isBun = typeof (globalThis as { Bun?: unknown }).Bun !== 'undefined';
  if (isBun) {
    // eslint-disable-next-line @typescript-eslint/no-require-imports
    const bunSqlite = require('bun:sqlite') as BunSqliteModule;
    _db = makeBunDb(bunSqlite);
  } else {
    // eslint-disable-next-line @typescript-eslint/no-require-imports
    const BetterSqlite3 = require('better-sqlite3') as typeof import('better-sqlite3');
    _db = makeNodeDb(BetterSqlite3);
  }
  return _db;
}

function initDb(): void {
  const db = getDb();

  db.run(`CREATE TABLE IF NOT EXISTS articles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    content TEXT,
    summary TEXT,
    source TEXT,
    source_url TEXT UNIQUE,
    url_hash TEXT UNIQUE,
    published_at TEXT,
    publish_status TEXT NOT NULL DEFAULT 'pending',
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
  )`);

  db.run(`CREATE TABLE IF NOT EXISTS task_records (
    task_id TEXT PRIMARY KEY,
    task_type TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'queued',
    progress_completed INTEGER DEFAULT 0,
    progress_total INTEGER DEFAULT 0,
    started_at TEXT,
    completed_at TEXT,
    result_json TEXT,
    error_json TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
  )`);

  db.run(`CREATE TABLE IF NOT EXISTS sources (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    url TEXT UNIQUE NOT NULL,
    enabled INTEGER NOT NULL DEFAULT 1,
    category TEXT,
    frequency_hours INTEGER NOT NULL DEFAULT 12
  )`);

  db.run(`CREATE TABLE IF NOT EXISTS channel_configs (
    id TEXT PRIMARY KEY,
    config_json TEXT NOT NULL,
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
  )`);

  // Seed RSS sources if empty
  const count = (db.query('SELECT COUNT(*) as c FROM sources').get() as { c: number }).c;
  if (count === 0) {
    const insert = db.prepare('INSERT OR IGNORE INTO sources (name, url, category, frequency_hours) VALUES (?, ?, ?, ?)');
    const sources: [string, string, string, number][] = [
      ['Google Official Blog', 'https://blog.google/rss/', 'official', 6],
      ['Google Cloud Blog', 'https://cloud.google.com/feeds/gcp-release-notes.xml', 'cloud', 12],
      ['Google AI Blog', 'https://blog.google/technology/ai/rss/', 'ai', 24],
      ['Yahoo Taiwan Stock', 'https://tw.news.yahoo.com/rss/stock', 'finance_tw', 6],
      ['TWSE News', 'https://www.twse.com.tw/rss/news.xml', 'finance_tw', 6],
      ['TechNews Taiwan', 'https://technews.tw/feed/', 'tech', 12],
      ['iThome', 'https://www.ithome.com.tw/rss', 'tech', 12],
    ];
    for (const [name, url, category, freq] of sources) {
      insert.run(name, url, category, freq);
    }
  }
}

// ── Article CRUD ─────────────────────────────────────────────────────────────
export interface Article {
  id?: number;
  title: string;
  content?: string;
  summary?: string;
  source?: string;
  source_url?: string;
  url_hash?: string;
  published_at?: string;
  publish_status?: 'pending' | 'summarized' | 'published';
  created_at?: string;
}

function insertArticle(article: Article): number {
  const db = getDb();
  const stmt = db.prepare(`
    INSERT OR IGNORE INTO articles (title, content, source, source_url, url_hash, published_at)
    VALUES (?, ?, ?, ?, ?, ?)
  `);
  const result = stmt.run(
    article.title, article.content ?? null, article.source ?? null,
    article.source_url ?? null, article.url_hash ?? null, article.published_at ?? null
  );
  // changes === 0 means the row was ignored (duplicate) — return 0 to signal no-op
  if (result.changes === 0) return 0;
  return result.lastInsertRowid as number;
}

function getArticlesByStatus(status: string = 'all', limit: number = 50, offset: number = 0): Article[] {
  const db = getDb();
  if (status === 'all') {
    return db.query(`SELECT * FROM articles ORDER BY created_at DESC LIMIT ? OFFSET ?`).all(limit, offset) as Article[];
  }
  return db.query(`SELECT * FROM articles WHERE publish_status = ? ORDER BY created_at DESC LIMIT ? OFFSET ?`).all(status, limit, offset) as Article[];
}

function countArticlesByStatus(status: string = 'all'): number {
  const db = getDb();
  if (status === 'all') {
    const row = db.query(`SELECT COUNT(*) AS n FROM articles`).get() as { n: number };
    return row.n;
  }
  const row = db.query(`SELECT COUNT(*) AS n FROM articles WHERE publish_status = ?`).get(status) as { n: number };
  return row.n;
}

function getArticleById(id: number): Article | null {
  const db = getDb();
  return (db.query(`SELECT * FROM articles WHERE id = ?`).get(id) as Article | undefined) ?? null;
}

function updateArticleStatus(id: number, status: string, summary?: string): void {
  const db = getDb();
  if (summary !== undefined) {
    db.run('UPDATE articles SET publish_status = ?, summary = ? WHERE id = ?', [status, summary, id]);
  } else {
    db.run('UPDATE articles SET publish_status = ? WHERE id = ?', [status, id]);
  }
}

// ── Task records ─────────────────────────────────────────────────────────────
function createTask(taskId: string, taskType: string, total: number = 0): void {
  const db = getDb();
  db.run(
    `INSERT INTO task_records (task_id, task_type, status, progress_total, started_at)
     VALUES (?, ?, 'running', ?, datetime('now'))`,
    [taskId, taskType, total]
  );
}

function updateTask(taskId: string, status: string, completed: number, resultJson?: string, errorJson?: string): void {
  const db = getDb();
  db.run(
    `UPDATE task_records SET status = ?, progress_completed = ?, completed_at = datetime('now'), result_json = ?, error_json = ?
     WHERE task_id = ?`,
    [status, completed, resultJson ?? null, errorJson ?? null, taskId]
  );
}

function getRecentTasks(limit: number = 20): unknown[] {
  return getDb().query('SELECT * FROM task_records ORDER BY created_at DESC LIMIT ?').all(limit);
}

export { getDb, initDb, insertArticle, getArticlesByStatus, countArticlesByStatus, getArticleById, updateArticleStatus, createTask, updateTask, getRecentTasks };
