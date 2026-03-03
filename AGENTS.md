# AGENTS.md — digest-agent Project Context

> AI agent configuration file for Claude Code, Gemini CLI, and other AI tools.
> Provides project context, architecture, and development guidelines.

---

## Project Overview

**digest-agent** is a standalone Streamlit application that automates the full
news digest pipeline: RSS fetch → AI summarize (Gemini 2.5 Flash) → multi-channel publish.

- **Repo**: https://github.com/jimmyliao/digest-agent (public)
- **Author**: JimmyLiao <jimmyliao@leapdesign.ai>
- **Stack**: Python 3.11, Streamlit, SQLAlchemy, google-genai, uv

---

## Directory Structure

```
digest-agent/
├── src/
│   ├── app.py                  ← Streamlit entry point (init_db + page config)
│   ├── pages/
│   │   ├── 1_articles.py       ← Article list + filter + sort + inline status edit
│   │   ├── 2_publish.py        ← Fetch / Summarize / Publish + Sources + channel config
│   │   └── 3_tasks.py          ← Task records + stats + auto-refresh
│   ├── fetcher/rss_fetcher.py  ← feedparser-based async RSS fetcher
│   ├── llm/
│   │   ├── gemini_summarizer.py ← google-genai client, rate limiter, mock mode
│   │   └── prompt_manager.py   ← System/user prompt templates
│   ├── models/database.py      ← SQLAlchemy models + init_db() + seed
│   ├── orchestrator.py         ← Pipeline: fetch → _save_articles → summarize → publish
│   ├── processor/processor.py  ← Dedup, clean HTML, language detect
│   └── publishers/             ← Email, Telegram, LINE, Discord, MultiChannel
├── tests/                      ← pytest (84/87 pass; 3 retry-mock tests are pre-existing)
├── config/settings.yaml        ← App settings
├── pyproject.toml              ← uv project (name: digest-agent-jimmyliao)
├── Makefile                    ← make dev / test / build / deploy
└── Dockerfile                  ← Cloud Run single image (port 8080)
```

---

## Key Architecture Decisions

### No FastAPI — Streamlit Direct Import
Streamlit pages import Python modules directly. No HTTP layer needed.
`asyncio.run()` wraps async pipeline calls inside Streamlit callbacks.

### DB: SQLite local → PostgreSQL on Cloud Run
```
DATABASE_URL=sqlite:///./data/digest.db          # local default
DATABASE_URL=postgresql+psycopg2://...           # Cloud Run (Supabase)
```
`connect_args` is conditionally set based on URL prefix (SQLite vs PostgreSQL).

### Channel Config: .env + DB dual-layer
Priority: **DB > .env** (same in both orchestrator and UI).
- `.env` / `~/workspace/.env` → loaded via `make dev` (`set -a && source`)
- DB (`channel_configs` table) → set via "⚙️ 渠道設定" tab in UI
- UI shows source badge per field: 🔵 DB / 🟢 .env / ⚪ 未設定
- "🗑️ 清除 DB" button → falls back to .env

### Article Lifecycle
```
pending → summarized → published
               └──────→ failed
```
`_save_articles()` in orchestrator persists fetched articles as `pending`.
Summarize updates to `summarized` + stores JSON summary.
Publish updates to `published` / `failed`.

---

## Development

```bash
# Install
uv sync --all-extras

# Run (loads ~/workspace/.env)
make dev        # http://localhost:8080

# Test
make test       # pytest tests/ -v

# Debug pipeline without UI
make debug
```

### Environment Variables
| Variable | Required | Description |
|----------|----------|-------------|
| `GEMINI_API_KEY` | ✅ | Gemini API key (auto mock if unset) |
| `DATABASE_URL` | optional | Default: `sqlite:///./data/digest.db` |
| `TELEGRAM_BOT_TOKEN` / `TELEGRAM_CHAT_ID` | optional | Telegram publish |
| `SMTP_SERVER/PORT/USER/PASSWORD` / `EMAIL_TO` | optional | Email publish |
| `LINE_CHANNEL_TOKEN` / `LINE_USER_ID` | optional | LINE publish |
| `DISCORD_WEBHOOK_URL` | optional | Discord publish |
| `GEMINI_RATE_LIMIT_PER_MINUTE` | optional | Default: 14 |

---

## AI Agent Guidelines

### For Claude Code (Agent-Eva)
- Working dir: `/Users/jimmyliao/workspace/digest-agent/digest-agent`
- Run via: `make dev` in tmux session `gde`, window `ws`, left-up pane
- Local DB: `data/digest.db` (SQLite, NOT committed to git)
- Credentials: `~/workspace/.env` (NOT in repo)
- Co-Author: `agent-jimmy <agent+jimmyliao@leapdesign.ai>`

### For Gemini CLI
- Use for files > 300 lines or large codebase analysis
- Key large files: `uv.lock` (ignore), `src/pages/2_publish.py`

### Known Issues / Notes
- 3 retry-mock tests in `tests/test_gemini_summarizer.py` fail due to SDK API mismatch — pre-existing, not regressions
- `data/digest.db` on macOS may have `com.apple.provenance` xattr; use `sqlite3 .dump | sqlite3 new.db` to create a writable copy
- SQLite file lock: do NOT symlink to a DB held by another process
