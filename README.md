<div align="right">

**Language** ／ 語言：
[English](#digest-agent) ·
[繁體中文](#digest-agent-繁體中文)

</div>

---

# digest-agent

> AI-powered news digest agent — RSS fetch → Gemini summarize → multi-channel publish

A standalone **Streamlit** application that automates your daily tech news workflow.
No backend server required — everything runs in a single Python process.

[![Python](https://img.shields.io/badge/python-3.11-blue)](https://python.org)
[![Streamlit](https://img.shields.io/badge/streamlit-1.35+-red)](https://streamlit.io)
[![uv](https://img.shields.io/badge/uv-package%20manager-orange)](https://github.com/astral-sh/uv)
[![License: MIT](https://img.shields.io/badge/license-MIT-green)](LICENSE)

---

## Features

- **📥 RSS Fetch** — Pull articles from multiple RSS sources with deduplication
- **🤖 AI Summarize** — Gemini 2.5 Flash generates structured Chinese summaries (title, 100-char summary, key points, tags)
- **📤 Multi-channel Publish** — Telegram · Email · LINE · Discord
- **📰 Article Dashboard** — Filter by status/tag, sort, inline status edit
- **⚙️ Dual-layer Config** — `.env` file + DB UI settings (DB overrides `.env`)
- **🗄️ SQLite → PostgreSQL** — Local dev with SQLite, Cloud Run with Supabase

---

## Quick Start

```bash
# 1. Clone
git clone https://github.com/jimmyliao/digest-agent.git
cd digest-agent

# 2. Install (requires uv)
uv sync --all-extras

# 3. Configure
cp .env.example .env
# Edit .env — add GEMINI_API_KEY at minimum

# 4. Run
uv run streamlit run src/app.py --server.port=8080
# Open http://localhost:8080
```

Or with `make`:
```bash
make install
make dev     # loads .env by default
```

**Alternative — use with AI Agent CLI:**

This repo includes [`AGENTS.md`](./AGENTS.md) with full project context for AI coding assistants.
Clone the repo and point your agent CLI directly at it:

```bash
# Claude Code
claude                        # auto-loads CLAUDE.md (symlink → AGENTS.md)

# Gemini CLI
gemini -p "@AGENTS.md Explain the publish pipeline"

# Any agent that reads AGENTS.md
cat AGENTS.md                 # project context, architecture, dev guidelines
```

> `CLAUDE.md` and `GEMINI.md` are both symlinks to `AGENTS.md` —
> each CLI picks up its own file automatically on startup.

---

## Architecture

```
User (Browser)
    │
    ▼
Streamlit App (port 8080)
├── pages/1_articles.py   → Article list, filter, sort
├── pages/2_publish.py    → Fetch / Summarize / Publish pipeline
└── pages/3_tasks.py      → Task history, stats
    │
    ├── src/fetcher/       ← feedparser (async)
    ├── src/llm/           ← google-genai (Gemini 2.5 Flash)
    ├── src/publishers/    ← Telegram, Email, LINE, Discord
    └── src/models/        ← SQLAlchemy (SQLite / PostgreSQL)
```

**Article lifecycle**: `pending` → `summarized` → `published` / `failed`

---

## Configuration

Copy `.env.example` to `.env` and fill in your credentials:

| Variable | Required | Description |
|----------|----------|-------------|
| `GEMINI_API_KEY` | ✅ | [Get from AI Studio](https://aistudio.google.com/app/apikey) — auto mock if unset |
| `TELEGRAM_BOT_TOKEN` / `TELEGRAM_CHAT_ID` | optional | via [@BotFather](https://t.me/botfather) |
| `SMTP_SERVER/PORT/USER/PASSWORD` + `EMAIL_TO` | optional | Gmail App Password recommended |
| `LINE_CHANNEL_TOKEN` / `LINE_USER_ID` | optional | LINE Developers Console |
| `DISCORD_WEBHOOK_URL` | optional | Server Settings → Integrations → Webhook |
| `DATABASE_URL` | optional | Default: `sqlite:///./data/digest.db` |

You can also configure channels directly in the UI under **⚙️ 渠道設定** — DB values override `.env`.

---

## Deployment (Cloud Run)

```bash
# Requires gcloud CLI + secrets set up in Secret Manager
make deploy
```

Secrets expected: `gemini-api-key`, `supabase-db-url`
See `.github/workflows/deploy.yml` for GitHub Actions CI/CD.

---

## Development

```bash
make test    # pytest (84/87 pass)
make lint    # ruff
make build   # docker build
make debug   # run pipeline without UI
```

---

## Project Structure

```
digest-agent/
├── src/
│   ├── app.py              ← Streamlit entry point
│   ├── pages/              ← 3 Streamlit pages
│   ├── fetcher/            ← RSS fetcher
│   ├── llm/                ← Gemini summarizer + prompt manager
│   ├── models/             ← SQLAlchemy DB models
│   ├── orchestrator.py     ← Pipeline orchestration
│   ├── processor/          ← Article dedup + cleaning
│   └── publishers/         ← Multi-channel publishers
├── tests/
├── Dockerfile
├── Makefile
└── pyproject.toml
```

---

<br>

---

# digest-agent 繁體中文

> AI 驅動的新聞摘要代理 — RSS 抓取 → Gemini 摘要 → 多渠道發佈

一個獨立的 **Streamlit** 應用程式，自動化你的每日科技新聞工作流程。
不需要後端伺服器，所有功能在單一 Python process 中運行。

---

## 功能特色

- **📥 RSS 抓取** — 從多個 RSS 來源拉取文章，自動去重
- **🤖 AI 摘要** — Gemini 2.5 Flash 生成結構化繁體中文摘要（標題、100字摘要、重點、標籤）
- **📤 多渠道發佈** — Telegram · Email · LINE · Discord
- **📰 文章管理介面** — 依狀態/標籤篩選、排序、行內狀態編輯
- **⚙️ 雙層設定** — `.env` 檔案 + DB UI 設定（DB 優先於 `.env`）
- **🗄️ SQLite → PostgreSQL** — 本地開發用 SQLite，Cloud Run 用 Supabase

---

## 快速開始

```bash
# 1. Clone
git clone https://github.com/jimmyliao/digest-agent.git
cd digest-agent

# 2. 安裝（需要 uv）
uv sync --all-extras

# 3. 設定環境變數
cp .env.example .env
# 編輯 .env，至少填入 GEMINI_API_KEY

# 4. 啟動
uv run streamlit run src/app.py --server.port=8080
# 開啟 http://localhost:8080
```

或用 `make`：
```bash
make install
make dev     # 預設讀取 ENV_FILE=~/workspace/.env
```

**也可以搭配 AI Agent CLI 使用：**

本 repo 內含 [`AGENTS.md`](./AGENTS.md)，提供完整專案架構與開發指南給 AI 工具讀取：

```bash
# Claude Code（自動載入 CLAUDE.md → 指向 AGENTS.md）
claude

# Gemini CLI
gemini -p "@AGENTS.md 說明發佈 pipeline 的流程"

# 直接查看專案說明
cat AGENTS.md
```

> `CLAUDE.md` 和 `GEMINI.md` 都是 symlink 指向同一個 `AGENTS.md`，
> 各 AI CLI 啟動時會自動載入對應的檔案。

---

## 架構說明

```
使用者（瀏覽器）
    │
    ▼
Streamlit App（port 8080）
├── pages/1_articles.py   → 文章列表、篩選、排序
├── pages/2_publish.py    → Fetch / Summarize / Publish pipeline
└── pages/3_tasks.py      → 任務記錄、統計
    │
    ├── src/fetcher/       ← feedparser（非同步）
    ├── src/llm/           ← google-genai（Gemini 2.5 Flash）
    ├── src/publishers/    ← Telegram、Email、LINE、Discord
    └── src/models/        ← SQLAlchemy（SQLite / PostgreSQL）
```

**文章狀態流程**：`pending` → `summarized` → `published` / `failed`

---

## 環境變數設定

複製 `.env.example` 為 `.env` 並填入實際值：

| 變數 | 必填 | 說明 |
|------|------|------|
| `GEMINI_API_KEY` | ✅ | [從 AI Studio 取得](https://aistudio.google.com/app/apikey)，未設定自動進入 Mock 模式 |
| `TELEGRAM_BOT_TOKEN` / `TELEGRAM_CHAT_ID` | 選填 | 透過 [@BotFather](https://t.me/botfather) 建立 |
| `SMTP_SERVER/PORT/USER/PASSWORD` + `EMAIL_TO` | 選填 | Gmail 建議使用應用程式密碼 |
| `LINE_CHANNEL_TOKEN` / `LINE_USER_ID` | 選填 | LINE Developers Console |
| `DISCORD_WEBHOOK_URL` | 選填 | 伺服器設定 → 整合 → Webhook |
| `DATABASE_URL` | 選填 | 預設：`sqlite:///./data/digest.db` |

也可以在 UI 的 **⚙️ 渠道設定** tab 直接設定，DB 值會覆蓋 `.env`。

---

## 部署到 Cloud Run

```bash
# 需要 gcloud CLI 且 Secret Manager 已設定好 secrets
make deploy
```

所需 secrets：`gemini-api-key`、`supabase-db-url`
CI/CD 設定請參考 `.github/workflows/deploy.yml`。

---

## 開發指令

```bash
make test    # pytest（84/87 通過）
make lint    # ruff
make build   # docker build
make debug   # 不透過 UI 直接執行 pipeline
```

---

**維護者**：[JimmyLiao](https://github.com/jimmyliao)
