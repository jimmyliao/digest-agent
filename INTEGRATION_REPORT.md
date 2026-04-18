# Integration Report — feat/nextjs-showcase
Date: 2026-04-18

## Summary
P3 Integration Agent successfully integrated the Next.js showcase (`apps/web`).
Key fix: `lib/db.ts` was refactored to support both Bun (`bun:sqlite`) and Node.js
(`better-sqlite3`) runtimes, resolving a critical `Cannot find module 'bun:sqlite'`
error in Next.js dev mode (which runs under Node.js/webpack).

## Smoke Test Results
| Route | Method | Status | Notes |
|-------|--------|--------|-------|
| /api/health | GET | ✅ | `{"status":"ok","db":true,"llm_provider":"gemini"}` |
| /api/fetch | POST | ✅ | Fetched 60 articles from 7 RSS feeds, saved 60, 0 deduplicated |
| /api/articles | GET | ✅ | Returns paginated articles with full metadata |
| /api/summarize | POST | ✅ | SSE streaming, mock mode triggered by `test-` API key |
| /api/publish | POST | ✅ | Mock Telegram: `[Telegram Mock] Would publish N articles` |
| /api/pipeline | POST | ✅ | `{"success":true,"results":{"fetch":{...},"summarize":{...}}}` |

## Vitest Results
```
 Test Files  4 passed (4)
      Tests  25 passed (25)
   Start at  13:42:42
   Duration  244ms

Tests by file:
  ✓ tests/lib/publishers.test.ts  (7 tests)
  ✓ tests/lib/db.test.ts          (7 tests)
  ✓ tests/lib/rss.test.ts         (7 tests)
  ✓ tests/lib/llm.test.ts         (4 tests)
```

## Issues Found & Fixed

### 1. `bun:sqlite` incompatible with Next.js webpack (FIXED)
- **Root cause**: `lib/db.ts` used `import { Database } from 'bun:sqlite'` directly,
  which webpack cannot resolve in Next.js dev (Node.js runtime).
- **Fix**: Refactored `lib/db.ts` with runtime detection:
  - `typeof globalThis.Bun !== 'undefined'` → use `bun:sqlite`
  - otherwise → use `better-sqlite3` (installed as new dep)
- **Config**: Added `serverExternalPackages: ['better-sqlite3', 'bun:sqlite']` to `next.config.ts`

### 2. `insertArticle` returned wrong id on `INSERT OR IGNORE` duplicate (FIXED)
- **Root cause**: `better-sqlite3` returns previous `lastInsertRowid` on IGNORE (not 0),
  differing from `bun:sqlite` behavior expected by the test.
- **Fix**: Check `result.changes === 0` → return `0` to signal no-op insertion.
- **Test**: `db.test.ts > insertArticle returns 0 for duplicate url_hash` now passes.

## Files Changed
- `apps/web/lib/db.ts` — cross-runtime SQLite adapter (Bun + Node.js)
- `apps/web/next.config.ts` — added `serverExternalPackages`
- `apps/web/package.json` — added `better-sqlite3` + `@types/better-sqlite3`

## Next Steps
- [ ] P4 E2E (Playwright MCP) — smoke tests all pass, ready for E2E
- [ ] Push origin feat/nextjs-showcase
- [ ] Consider `bun --bun next dev` flag to run Next.js under Bun's runtime (eliminates need for better-sqlite3 in dev)
