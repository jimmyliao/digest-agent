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

> Two parallel paths — Next.js is the **5/9 default**; Streamlit is the **fallback / backup** runbook.

### ⚛️ Path A: Next.js (5/9 BwAI 台中 default + AIA showcase)

```bash
git clone https://github.com/jimmyliao/digest-agent.git
cd digest-agent
make workshop-verify                           # onboard + smoke test (bun + uv + boot dev + curl /api/health)
vim apps/web/.env.local                        # set GEMINI_API_KEY (only if you want real LLM calls)
cd apps/web && bun run dev                     # http://localhost:3000
```

`make workshop-verify` is **idempotent + green/red signal**: works on Google Cloud Shell, macOS, Linux, WSL. Just want to install (without the smoke test)? Use `make onboard-cloudshell`.

### 🐍 Path B: Streamlit (fallback / backup if Next.js path stalls)

```bash
git clone https://github.com/jimmyliao/digest-agent.git
cd digest-agent
uv sync --all-extras                          # Python deps only — no bun, no workspace
cp .env.example .env && vim .env              # set GEMINI_API_KEY
make dev                                       # http://localhost:8080
```

Cloud Shell shortcut (no setup): `make dev-shell` (port 8080 with Web Preview). Battle-tested at the 4/18 桃園 workshop — keep it as your safety net.

For the 5/9 BwAI Cloud Shell workshop runbook (Magic Prompt + copy-paste bash), see [CLOUD_SHELL_WORKSHOP.md](./CLOUD_SHELL_WORKSHOP.md).
For a catalog of every script (purpose + `make` wrapper), see [scripts/README.md](./scripts/README.md).

**Alternative — use with AI Agent CLI:**

This repo includes [`AGENTS.md`](./AGENTS.md) with full project context for AI coding assistants.
Clone the repo and point your agent CLI directly at it:

```bash
# Claude Code
claude                        # auto-loads CLAUDE.md (symlink → AGENTS.md)

# Gemini CLI
gemini -p "@AGENTS.md Understand the RSS-to-publish pipeline architecture"

# 💡 Bonus: The AGENTS.md context lets Gemini CLI understand your entire project.
#    Want advanced usage patterns? Join our upcoming AI Agent Workshop for live demos!

# Any agent that reads AGENTS.md
cat AGENTS.md                 # project context, architecture, dev guidelines
```

> `CLAUDE.md` and `GEMINI.md` are both symlinks to `AGENTS.md` —
> each CLI picks up its own file automatically on startup.

---

## OSS vs. LeapCore Cloud — what's covered here?

This repo is a **personal / workshop demo**: single-tenant, SQLite + Litestream,
zero ops. Take it, run it, learn from it.

When you outgrow it, **LeapCore Cloud** picks up where this stops — multi-tenant
KM, audit log, SLA, custom RAG plug-ins, enterprise SSO.

| Feature | digest-agent OSS | LeapCore Cloud |
|---------|------------------|----------------|
| RSS fetch + Gemini summarize | ✅ | ✅ |
| ADK multi-agent (stock-analysis) | ✅ | ✅ |
| Cloud Run + Litestream + GEAP | ✅ | ✅ |
| Single-tenant (你自己用) | ✅ | — |
| **Multi-tenant + SSO** | — | ✅ |
| **Audit log / compliance** | — | ✅ |
| **Custom RAG plug-ins** (HISP/LISOC 級 ingestion) | — | ✅ |
| **Slack / Teams adapter** | — | ✅ |
| **SLA + on-call support** | — | ✅ |
| **On-prem / 私有 LLM** (LeapCore Enterprise) | — | ✅ |

### Want to try LeapCore Cloud / 商業合作

- 📲 LINE OA: [`@rls8912s`](https://line.me/R/ti/p/@rls8912s) — JimmyLiao | Advocate
- 💌 Email: `hi@leapdesign.ai`
- 📚 Subscribe: [leapdesign.ai/zh/subscribe](https://leapdesign.ai/zh/subscribe)

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

## Google Cloud Shell (Zero-setup)

No local install needed — run entirely from your browser.

### Step 0 — Verify Gemini CLI

Cloud Shell has `gemini` **pre-installed** — no `npm install` needed.

```bash
gemini --version
```

If you see `/usr/bin/env: 'node': No such file or directory`, click **⋮ → Restart** in the Cloud Shell toolbar and try again.

### Step 1 — One-time setup

```bash
# Install uv
curl -Ls https://astral.sh/uv/install.sh | sh && source ~/.bashrc

# Clone and install
git clone https://github.com/jimmyliao/digest-agent.git
cd digest-agent
uv sync --all-extras
```

**Authentication — two separate things:**

| | What for | How |
|--|----------|-----|
| **Gemini CLI itself** | AI assistant that runs your commands | `gemini auth login` (Google OAuth, no API key needed) |
| **digest-agent app** | Calls Gemini API to summarize news | Needs `GEMINI_API_KEY` in `.env` or shell env |

```bash
# 1. Authenticate Gemini CLI (Google account, no API key)
gemini auth login

# 2. Get a free API key for the app → https://aistudio.google.com/app/apikey
#    Then set it — pick ONE of:

# Option A: write to .env (local to project)
echo "GEMINI_API_KEY=your-key-here" > .env

# Option B: export to shell (Cloud Shell persists this across sessions if added to ~/.bashrc)
export GEMINI_API_KEY=your-key-here
echo 'export GEMINI_API_KEY=your-key-here' >> ~/.bashrc
```

> **Workshop tip:** If `GEMINI_API_KEY` is already exported in your shell, the app picks it up automatically — no `.env` editing needed.

### Step 2a — Local preview (Web Preview)

Paste this into Gemini CLI:

```bash
gemini -p "@GEMINI.md 我在 Google Cloud Shell 環境，依賴已安裝，GEMINI_API_KEY 已 export 到 shell。
請幫我：
1. 在背景執行：nohup make dev-shell &（不需要 .env，直接吃 shell env var）
2. 確認 port 8080 有在監聽（ss -tlnp 或 curl localhost:8080）
3. 說明如何點 Cloud Shell 右上角的 Web Preview 選 port 8080 開啟 Dashboard"
```

Then click **Web Preview → Preview on port 8080** in Cloud Shell toolbar.

### Step 2b — Deploy to Cloud Run

```bash
gemini -p "@GEMINI.md 我在 Google Cloud Shell，請依序幫我執行以下指令：
1. gcloud config set project YOUR_PROJECT_ID
2. gcloud services enable run.googleapis.com cloudbuild.googleapis.com artifactregistry.googleapis.com
3. GEMINI_API_KEY=YOUR_GEMINI_API_KEY make deploy-workshop
4. 部署完成後印出 Cloud Run URL
5. curl 驗證 URL 有正常回應"
```

Or directly:

```bash
GEMINI_API_KEY=your-key make deploy-workshop
```

**Required inputs:**

| Field | Required | Where to get |
|-------|----------|-------------|
| `GEMINI_API_KEY` | ✅ | [aistudio.google.com/app/apikey](https://aistudio.google.com/app/apikey) |
| `GCP_PROJECT_ID` | Deploy only | Cloud Shell project selector (top left) |
| Telegram Bot Token + Chat ID | Optional | @BotFather — takes 30 sec, great for live demo |

---

## Deployment

Three paths, pick what matches your workshop / showcase target.

### Path A — Streamlit → Cloud Run

```bash
make deploy            # Secret Manager: gemini-api-key, supabase-db-url
# OR for the workshop quick-deploy (no Secret Manager):
GEMINI_API_KEY=... make deploy-workshop
```

### Path B — Next.js → Cloud Run with Litestream + GCS persistence

```bash
make setup-data-bucket   # one-time: GCS bucket for Litestream WAL replication
make deploy-web          # Cloud Build (~3-5 min) → revision auto-rollout
```

`/data/digest.db` lives inside the container; Litestream replicates the WAL to GCS every 10s and restores on cold start. **Redeploys / restarts don't lose data.**

### Path C — ADK Agents → Vertex AI Agent Engine (GEAP)

```bash
GCP_PROJECT=… STAGING_BUCKET=gs://… GEMINI_API_KEY=… make deploy-agent-engine
make invoke-agent-engine    # smoke test the latest deployed engine
```

Hosts the Python `agents/stock/` SequentialAgent on Google's managed agent runtime. Cloud Run UI's `/api/stock-chat` calls this via SSE.

> Pre-flight checks (billing enabled, ADC quota project, IAM, bucket region) run automatically; see `make help` for the full target list and [`scripts/README.md`](./scripts/README.md) for what each script does.

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

> 兩條路徑 — Next.js 是 **5/9 預設主軸**，Streamlit 是 **備援 / fallback runbook**。

### ⚛️ Path A：Next.js（5/9 BwAI 台中 預設 + AIA showcase）

```bash
git clone https://github.com/jimmyliao/digest-agent.git
cd digest-agent
make workshop-verify                           # 安裝 bun + uv + 啟動 dev + curl /api/health
vim apps/web/.env.local                        # 設 GEMINI_API_KEY（要呼叫真 LLM 才需要）
cd apps/web && bun run dev                     # http://localhost:3000
```

`make workshop-verify` **idempotent + 綠/紅 signal**：跑得過 macOS / Cloud Shell / Linux / WSL。只想裝環境不跑 smoke 用 `make onboard-cloudshell`。

### 🐍 Path B：Streamlit（Next.js 卡關時的 fallback）

```bash
git clone https://github.com/jimmyliao/digest-agent.git
cd digest-agent
uv sync --all-extras                          # 純 Python 依賴，沒 bun、沒 workspace
cp .env.example .env && vim .env              # 填入 GEMINI_API_KEY
make dev                                       # http://localhost:8080
```

Cloud Shell 一鍵起：`make dev-shell`（port 8080，可開 Web Preview）。4/18 桃園 workshop 實戰過 — 留作安全網。

5/9 BwAI Cloud Shell workshop runbook（Magic Prompt + copy-paste bash）：[CLOUD_SHELL_WORKSHOP.md](./CLOUD_SHELL_WORKSHOP.md)。
所有 script 的用途總覽：[scripts/README.md](./scripts/README.md)。

**也可以搭配 AI Agent CLI 使用：**

本 repo 內含 [`AGENTS.md`](./AGENTS.md)，提供完整專案架構與開發指南給 AI 工具讀取：

```bash
# Claude Code（自動載入 CLAUDE.md → 指向 AGENTS.md）
claude

# Gemini CLI
gemini -p "@AGENTS.md 說明 RSS 到發佈的完整 pipeline 架構"

# 💡 進階提示：AGENTS.md 包含完整的專案上下文，讓 Gemini CLI 理解整個系統。
#    想看更深層的使用技巧嗎？敬請期待我們的 AI Agent Workshop 現場演示！

# 直接查看專案說明
cat AGENTS.md
```

> `CLAUDE.md` 和 `GEMINI.md` 都是 symlink 指向同一個 `AGENTS.md`，
> 各 AI CLI 啟動時會自動載入對應的檔案。

---

## OSS vs. LeapCore Cloud — 這個 repo 涵蓋什麼？

這個 repo 是 **個人 / Workshop demo**：單租戶、SQLite + Litestream、零維運。
拿去跑、拿去學。

當你的需求超出單人玩法，**LeapCore Cloud** 接手 — 多租戶 KM、audit log、
SLA、客製 RAG plug-ins、企業 SSO。

| 功能 | digest-agent OSS | LeapCore Cloud |
|------|------------------|----------------|
| RSS 抓取 + Gemini 摘要 | ✅ | ✅ |
| ADK 多代理（個股分析） | ✅ | ✅ |
| Cloud Run + Litestream + GEAP | ✅ | ✅ |
| 單租戶（自己用） | ✅ | — |
| **多租戶 + SSO** | — | ✅ |
| **Audit log / 合規** | — | ✅ |
| **客製 RAG plug-ins**（HISP/LISOC 級 ingestion） | — | ✅ |
| **Slack / Teams adapter** | — | ✅ |
| **SLA + on-call 支援** | — | ✅ |
| **私有部署 / 私有 LLM**（LeapCore Enterprise） | — | ✅ |

### 想試 LeapCore Cloud / 商業合作

- 📲 LINE OA: [`@rls8912s`](https://line.me/R/ti/p/@rls8912s) — JimmyLiao | Advocate
- 💌 Email: `hi@leapdesign.ai`
- 📚 訂閱: [leapdesign.ai/zh/subscribe](https://leapdesign.ai/zh/subscribe)

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

## Google Cloud Shell（零環境設定）

不需要本機安裝，直接在瀏覽器操作。

### Step 0 — 確認 Gemini CLI 可用

Cloud Shell **預裝了 `gemini`**，不需要 npm install。

```bash
gemini --version
```

若看到 `node: No such file or directory`，點工具列 **⋮ → 重新啟動**，重開後再試。

### Step 1 — 一次性設定

```bash
# 安裝 uv
curl -Ls https://astral.sh/uv/install.sh | sh && source ~/.bashrc

# Clone 並安裝依賴
git clone https://github.com/jimmyliao/digest-agent.git
cd digest-agent
uv sync --all-extras
```

**認證 — 兩件獨立的事：**

| | 用途 | 方式 |
|--|------|------|
| **Gemini CLI 本身** | AI assistant（幫你執行指令） | `gemini auth login`（Google 帳號 OAuth，不需要 API Key）|
| **digest-agent 應用程式** | 呼叫 Gemini API 摘要新聞 | 需要 `GEMINI_API_KEY` 在 `.env` 或 shell 環境變數 |

```bash
# 1. Gemini CLI 登入（用 Google 帳號，不需要 API Key）
gemini auth login

# 2. 取得免費 API Key 給 app 用 → https://aistudio.google.com/app/apikey
#    擇一設定：

# 方式 A：寫入 .env（只對這個專案有效）
echo "GEMINI_API_KEY=你的-key" > .env

# 方式 B：export 到 shell（加入 ~/.bashrc 後 Cloud Shell 跨 session 都有效）
export GEMINI_API_KEY=你的-key
echo 'export GEMINI_API_KEY=你的-key' >> ~/.bashrc
```

> **工作坊提示：** 如果 shell 已有 `GEMINI_API_KEY` 環境變數，app 會自動讀取，不需要編輯 `.env`。

### Step 2a — 本機預覽（Web Preview）

貼進 Gemini CLI：

```bash
gemini -p "@GEMINI.md 我在 Google Cloud Shell 環境，依賴已安裝，GEMINI_API_KEY 已 export 到 shell。
請幫我：
1. 在背景執行：nohup make dev-shell &（不需要 .env，直接吃 shell env var）
2. 確認 port 8080 有在監聽（ss -tlnp 或 curl localhost:8080）
3. 說明如何點 Cloud Shell 右上角的 Web Preview 選 port 8080 開啟 Dashboard"
```

完成後點 Cloud Shell 工具列的 **Web Preview → 在通訊埠 8080 上預覽**。

### Step 2b — 部署到 Cloud Run

```bash
gemini -p "@GEMINI.md 我在 Google Cloud Shell，要部署到 Cloud Run。
GCP_PROJECT_ID=你的-project-id
GEMINI_API_KEY=你的-key

請幫我：
1. 執行 gcloud config set project \$GCP_PROJECT_ID
2. 啟用必要 API：gcloud services enable run.googleapis.com cloudbuild.googleapis.com artifactregistry.googleapis.com
3. 執行 GEMINI_API_KEY=\$GEMINI_API_KEY make deploy-workshop
4. 部署完成後印出 Cloud Run URL
5. 用 curl 驗證 URL 回應正常"
```

或直接執行：

```bash
GEMINI_API_KEY=你的-key make deploy-workshop
```

**必填欄位：**

| 欄位 | 必填 | 取得方式 |
|------|------|---------|
| `GEMINI_API_KEY` | ✅ | [aistudio.google.com/app/apikey](https://aistudio.google.com/app/apikey) |
| `GCP_PROJECT_ID` | 部署才需要 | Cloud Shell 左上角 project selector |
| Telegram Bot Token + Chat ID | 選填 | @BotFather，30 秒取得，live demo 效果很好 |

---

## 部署

依目標選 path。

### Path A — Streamlit → Cloud Run

```bash
make deploy            # 需 Secret Manager 預先設好 gemini-api-key / supabase-db-url
# 或 workshop 快速部署（不需要 Secret Manager）：
GEMINI_API_KEY=... make deploy-workshop
```

### Path B — Next.js → Cloud Run + Litestream + GCS 持久化

```bash
make setup-data-bucket   # 一次性：建好 Litestream 用的 GCS bucket
make deploy-web          # Cloud Build（~3-5 分鐘）→ 自動 rollout 新 revision
```

`/data/digest.db` 在 container 內，Litestream 每 10 秒把 WAL replicate 到 GCS、cold start 自動 restore。**Redeploy / 重啟資料不會掉。**

### Path C — ADK Agents → Vertex AI Agent Engine（GEAP）

```bash
GCP_PROJECT=… STAGING_BUCKET=gs://… GEMINI_API_KEY=… make deploy-agent-engine
make invoke-agent-engine    # 部署後 smoke 一下最新 engine
```

把 Python `agents/stock/` SequentialAgent 部署到 Google 託管的 agent runtime；Cloud Run UI 的 `/api/stock-chat` SSE 串到這裡。

> 部署前 pre-flight（billing、ADC quota project、IAM、bucket region）會自動檢查；`make help` 看完整 target 清單，[`scripts/README.md`](./scripts/README.md) 看每個 script 做什麼。

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
