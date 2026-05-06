# Overnight Build Report — feat/nextjs-showcase
**Date**: 2026-04-18
**Duration**: ~3 hours
**Build**: digest-agent Next.js 15 + Bun showcase

---

## 完成項目

### 基礎架構（P0）
- [x] `apps/web/next.config.ts` — standalone output, LLM_PROVIDER env
- [x] `apps/web/lib/db.ts` — cross-runtime SQLite (bun:sqlite + better-sqlite3)
- [x] `apps/web/lib/rss.ts` — rss-parser fetcher, SHA256[:16] urlHash dedup
- [x] `packages/leapcore-iface/src/index.ts` — 5 TypeScript abstract classes

### API Routes（P1a）
- [x] `GET /api/health` — db + llm provider check
- [x] `POST /api/fetch` — RSS -> DB (60 articles from 7 sources)
- [x] `GET /api/articles` — status filter, limit
- [x] `POST /api/summarize` — SSE streaming, mock on test-* keys
- [x] `POST /api/pipeline` — sequential orchestration

### Publishers（P1b）
- [x] `apps/web/lib/publishers.ts` — Telegram + Discord
- [x] `POST /api/publish` — mock mode on test-* tokens

### UI Pages（P2a）
- [x] `app/articles/page.tsx` — server component with status badges
- [x] `app/publish/page.tsx` — SSE terminal, provider switcher (Gemini/Claude)
- [x] `app/tasks/page.tsx` — recent task records
- [x] `app/page.tsx` — home nav + LeapChat soft promo

### Tests（P2b）
- [x] `vitest.config.ts`
- [x] `tests/lib/db.test.ts` (7 tests)
- [x] `tests/lib/rss.test.ts` (7 tests)
- [x] `tests/lib/llm.test.ts` (4 tests)
- [x] `tests/lib/publishers.test.ts` (7 tests)

### 驗證（P3 + P4）
- [x] Smoke tests: 6/6
- [x] Vitest: 25/25
- [x] E2E pages: 4/4
- [x] Full pipeline API: OK

### DevOps
- [x] `.claude/hooks/guard_rails.sh` — PreToolUse protection
- [x] `.claude/settings.json` — MCP servers (GitHub + filesystem)
- [x] `AIA_SUBMISSION.md` — 3-page PDF + 90-sec demo script

---

## 測試摘要

| 類型 | 結果 |
|------|------|
| Vitest 單元測試 | 25/25 |
| API Smoke Tests | 6/6 |
| E2E Page Tests | 4/4 |

---

## 關鍵技術決策

1. **bun:sqlite cross-runtime adapter**: Next.js webpack 無法 resolve Bun built-in，改用 `typeof globalThis.Bun` 切換 better-sqlite3
2. **SSE without Edge Runtime**: 直接用 `ReadableStream` 在 Node.js route，避免 bun:sqlite 不相容
3. **Mock mode**: API keys 以 `test-` 開頭 -> 離線模式，不需真實 API key

---

## 未完成項目

- Playwright MCP 瀏覽器截圖（環境未安裝，改 curl 驗證）
- Cloud Run 部署設定（Dockerfile 需更新）
- AIA PDF 設計（需 brief designer）
- AIA 影片錄製（demo.sh 需 real API key）

---

## 下一步

1. **AIA 投稿** (deadline 5/7/2026): https://s.sted.tw/iuyYZg
2. `make dev` 測試真實 API（設定 .env）
3. 錄製 90 秒 demo 影片
4. Brief designer for AIA 3-page PDF
5. 考慮 Vercel 部署（`apps/web` standalone）

---

## Git Log（最近 15 commits）

```
26c7ab4 test: E2E browser verification — all pages load
681258f fix(db): cross-runtime SQLite adapter (bun:sqlite + better-sqlite3) + integration report
2705fc7 test: vitest unit tests — db, rss, llm, publishers
47a7e57 feat(ui): articles, publish (SSE streaming), tasks pages + home nav
1c9f2f6 feat(api+publish): API routes + Telegram/Discord publishers
19393ce feat(setup): merge P0 — db schema + rss fetcher + next.config
36f2e3a feat(setup): db schema (bun:sqlite) + rss fetcher + next.config + package.json
3283aaa feat: add Claude Code hooks + MCP config + AIA submission draft
2802486 feat: scaffold Next.js monorepo + leapcore-iface TypeScript + ADK stubs
664d060 fix: track data/ directory via .gitkeep to prevent SQLite init failure
70a590f fix: Fix environment file loading failure due to missing shell built-in command source
aeac51f fix: Fix missing quoting of the SMTP_FROM_NAME env value assignment
656a923 docs: add Cloud Shell restart magic prompt for resumed sessions
18bfcab docs: add API key verification step before starting server
2f0ef3c fix: use .env file for API keys instead of shell export
```
