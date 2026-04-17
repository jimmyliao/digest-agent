# AIA x Claude Code: Showcase Submission
## digest-agent — 用 Claude Code 重寫自己

**活動**: AIA x Claude Code: Call for Showcases
**截止**: 2026/5/7 18:00
**展示日**: 2026/5/18 政大公企中心 A431
**登記連結**: https://s.sted.tw/iuyYZg

---

## SECTION 1: 3-Page PDF Content

> 備注給設計師：A4 橫式或直式均可，建議深色底（黑/深灰）+ 螢光色重點標示。
> 三頁獨立版面，不要把內容縮小塞滿，要有呼吸感。程式碼區塊用 monospace。

---

### PAGE 1 — The Problem & Solution

---

**HEADLINE (large, bold):**

> **I asked Claude Code to rewrite itself.**
> *A Streamlit news agent, rebuilt live in Next.js + ADK TypeScript — by the AI that wrote this presentation.*

---

**THE PROBLEM (3 bullets)**

- **Streamlit is a prototype trap.** Great for demos, wrong for production. No SSR, no streaming, no composable UI. The v1 digest-agent hit that ceiling in 6 months.
- **Python ↔ TypeScript ecosystem split.** Google ADK TypeScript just shipped. Vercel AI SDK lives in TS. Staying in Python meant forking the agent stack permanently.
- **Framework lock-in kills long-term bets.** Today it's ADK. Tomorrow it's Claude Agent SDK or Semantic Kernel. Rewriting business logic every time a new framework wins is untenable.

---

**THE SOLUTION**

Claude Code acted as the lead architect for the rewrite. Not as a code completer — as an agent team:
- Parallel sub-agents refactored Python modules independently
- Hooks guarded sensitive directories (`data/`, `.env`) during the live session
- MCP servers (GitMCP + filesystem) gave Claude Code direct repo access
- The entire session — including this submission — was produced inside Claude Code

**Key stat:**

> *From Streamlit/Python to Next.js/ADK TypeScript in a single Claude Code session.*
> *The rewrite is the demo. The demo is the showcase.*

---

**TECH STACK DELTA**

| Before | After |
|--------|-------|
| Streamlit (Python) | Next.js 16 + Bun |
| google-genai (Python) | `@ai-sdk/google` + `@ai-sdk/anthropic` (Vercel AI SDK) |
| Single LLM (Gemini only) | Dual-LLM: Gemini 2.5 Flash + Claude Sonnet 4.6 |
| No agent framework | Google ADK TypeScript (just announced) |
| Manual agent code | leapcore-iface: framework-agnostic agent ABCs |
| Cloud Run deploy | Vercel deploy |

---

### PAGE 2 — Architecture

---

**ARCHITECTURE OVERVIEW (3 layers)**

```
┌─────────────────────────────────────────────────────────────────┐
│  LAYER 3: Next.js 16 App (Bun runtime)                          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐  │
│  │  /api/digest │  │  /api/stream │  │  React UI (shadcn)   │  │
│  │  (news fetch)│  │  (LLM SSE)   │  │  real-time streaming │  │
│  └──────┬───────┘  └──────┬───────┘  └──────────────────────┘  │
│         │                 │                                      │
├─────────┼─────────────────┼──────────────────────────────────────┤
│  LAYER 2: ADK TypeScript Agents                                  │
│  ┌──────┴──────┐  ┌───────┴──────┐  ┌──────────────────────┐  │
│  │ NewsAgent   │  │ SummaryAgent │  │  IndustryAgent       │  │
│  │ (RSS fetch) │  │ (LLM route)  │  │  (sector analysis)   │  │
│  └─────────────┘  └─────────────┘  └──────────────────────┘  │
│         ↑                ↑                   ↑                   │
├─────────┼────────────────┼───────────────────┼──────────────────┤
│  LAYER 1: leapcore-iface (framework-agnostic ABCs)              │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  AgentBase(name, model, instruction, tools)              │   │
│  │  ToolBase(name, description, execute, execute_async)     │   │
│  │  PipelineBase  OrchestratorBase  MemoryBase              │   │
│  └──────────────────────────────────────────────────────────┘   │
│  Today: Google ADK  →  Tomorrow: Claude Agent SDK / Sem. Kernel  │
└─────────────────────────────────────────────────────────────────┘
```

---

**DUAL-LLM ROUTING TABLE**

| Task | Provider | Model | Why |
|------|----------|-------|-----|
| RSS fetch + initial triage | Gemini 2.5 Flash | `gemini-2.5-flash` | Speed, low cost, grounding |
| Deep summarization | Claude Sonnet 4.6 | `claude-sonnet-4-6` | Nuanced compression, instruction follow |
| Stock/industry analysis | Gemini 2.5 Flash | ADK multi-agent | Parallel tool calls |
| Stream to UI | Either (switchable) | `LLM_PROVIDER=gemini\|claude` | One env var to swap |

Provider selection via `LLM_PROVIDER` env var — no code change needed.

---

**CLAUDE CODE INTEGRATION**

```
Claude Code Session
├── Hooks (BeforeTool — .claude/settings.json)
│   ├── scripts/deny-env-edit.sh     ← blocks any write to .env
│   └── scripts/guard_rails.sh       ← blocks rm -rf data/ or deletion of app.py
├── MCP Servers
│   ├── GitMCP (gitmcp.io/jimmyliao/digest-agent)
│   │   ├── Issue #2 (data/.gitkeep) → fixed + committed 664d060
│   │   ├── PR #1 (SMTP credential quoting) → merged
│   │   └── PR #3 (Makefile source→.) → merged
│   └── @modelcontextprotocol/server-filesystem
│       └── direct repo read/write without shell escapes
└── Agent Teams (parallel sub-agents)
    ├── Sub-agent A: refactor src/ modules
    ├── Sub-agent B: scaffold Next.js app structure
    └── Sub-agent C: write tests + docs
```

---

**PRODUCTION CONNECTION: LeapChat**

> `leapchat.leapdesign.ai` (private beta) — Jimmy's enterprise AI assistant product — is built on the **same tech stack**: Next.js + Vercel AI SDK + ADK TypeScript + leapcore-iface.
>
> digest-agent is the open-source reference implementation. LeapChat is the production deployment of the same pattern.

---

### PAGE 3 — Demo Flow + Call to Action

---

**90-SECOND DEMO PATH** (詳見 Section 2)

```
0:00  Hook intercepts rm -rf data/          → guard_rails in action
0:15  MCP GitMCP: show Issue #2 + PR #1 + PR #3  → 3 real bugs, all AI-committed, live in repo
0:30  LLM_PROVIDER=claude streaming digest  → Claude Sonnet 4.6 streaming in browser
0:50  vercel deploy → live URL              → from terminal to production in 20s
1:10  leapcore-iface slide                  → swap ADK → Claude Agent SDK, zero diff
1:20  QR code + LeapChat                    → "same stack, private beta"
```

---

**QR CODES (設計師：請並排放兩個 QR)**

```
[QR: github.com/jimmyliao/digest-agent]    [QR: leapchat.leapdesign.ai]
    Open-source repo                           LeapChat private beta signup
```

---

**SPEAKER BIO**

**Jimmy Liao**
Google Developer Expert (GDE) in AI/ML · Founder, LeapDesign
Building enterprise AI assistants for Taiwan's research institutions.
Currently shipping LeapChat + HISP RAG (NTU/HISP production).
`jimmyliao@leapdesign.ai` · GitHub: `@jimmyliao`

---

## SECTION 2: 90-Second Demo Script

> 這份腳本是逐秒對照版本，練習時請跟著計時。建議錄影前先走 3 次，確保 `vercel deploy` 已 cache 速度夠快。

**實際 Commit/PR 參考（現場備查）**:
| 項目 | Hash / PR | 說明 |
|------|-----------|------|
| Issue #2 | `664d060` | `fix: track data/ via .gitkeep — SQLite init failure on fresh clone` |
| PR #1 | GitHub PR #1 | SMTP credential quoting fix (`email_publisher.py`) |
| PR #3 | GitHub PR #3 | Makefile `source .env` → `. .env` (POSIX compatibility) |

**事前準備清單（Before you hit record）**:
- [ ] Terminal 字體放大到 20px 以上，深色主題
- [ ] `LLM_PROVIDER=claude` 已在 `.env` 設好
- [ ] `vercel link` 已完成（project 已綁定）
- [ ] 瀏覽器分頁：`localhost:3000`（或 Next.js dev port）已開
- [ ] GitMCP MCP server 在 Claude Code 已啟用，確認可以 `mcp list`
- [ ] Issue #2 已關閉（commit `664d060`）；PR #1（SMTP quoting fix）和 PR #3（Makefile source→.）也已 merge，準備好在 GitMCP 回應後補充說明
- [ ] `scripts/guard_rails.sh` 和 `scripts/deny-env-edit.sh` hook 已在 `.claude/settings.json` 設好（BeforeTool）
- [ ] `.claude/settings.json` 範本：
  ```json
  {
    "hooks": {
      "BeforeTool": [
        { "command": "bash", "args": ["scripts/guard_rails.sh"] },
        { "command": "bash", "args": ["scripts/deny-env-edit.sh"] }
      ]
    }
  }
  ```

---

### Demo Script Table

| Timestamp | Screen | Action | Speech (EN / 繁中) |
|-----------|--------|--------|--------------------|
| **0:00 – 0:05** | Terminal: Claude Code session open | Type: `rm -rf data/` → press Enter | "Watch what happens when I try to delete the data directory." / 「來試試看刪掉 data 資料夾。」 |
| **0:05 – 0:15** | Hook fires — red warning in terminal | Hook output: `⚠️ guard_rails: rm -rf data/ blocked. Protected path.` | "Claude Code's BeforeTool hook intercepted that. This runs before any shell command — no confirmation dialog needed." / 「Claude Code 的 Hook 在指令執行前攔截了它，不是事後補救，是根本不讓它跑。」 |
| **0:15 – 0:22** | Claude Code chat panel | Type in Claude Code: `Use GitMCP to list the last closed issue in jimmyliao/digest-agent` | "Now let me show MCP. I'm asking Claude Code to query GitHub directly." / 「現在用 MCP 直接查 GitHub。」 |
| **0:22 – 0:32** | Claude Code chat: GitMCP response showing closed issues | GitMCP returns list: `Issue #2: track data/ via .gitkeep — closed by commit 664d060` + mentions PR #1 (SMTP quoting) and PR #3 (Makefile source→.) already merged | "These are real bugs Claude Code fixed in previous sessions — Issue #2 was a missing `.gitkeep` that caused SQLite to crash on fresh clone. PR #1 fixed SMTP credential quoting. PR #3 fixed a Makefile sourcing bug. All committed, all in the public repo." / 「這些都是 Claude Code 在上一個 session 真實修掉的 bug — Issue #2 是 SQLite 在新 clone 時崩潰，PR #1 是 SMTP 引號問題，PR #3 是 Makefile source 語法。全部 commit 進去，看得到 log。」 |
| **0:32 – 0:35** | Split: terminal left, browser right | `export LLM_PROVIDER=claude` in terminal | "Switching to Claude Sonnet 4.6 — one env var." / 「切換到 Claude，一個環境變數。」 |
| **0:35 – 0:50** | Browser: Next.js app UI, streaming active | Click "Fetch + Summarize" in UI; SSE stream appears token-by-token | "Claude Sonnet 4.6 is streaming the news digest. Same app, different LLM, zero code change — that's what the Vercel AI SDK provider abstraction gives you." / 「Claude Sonnet 4.6 正在串流摘要，同一份程式碼，換掉 provider，零修改。」 |
| **0:50 – 0:55** | Terminal | `vercel deploy --prod` | "Deploying to Vercel." |
| **0:55 – 1:10** | Terminal: Vercel deploy output scrolling | Vercel outputs build logs → `Production: https://digest-agent-xxxx.vercel.app` | "20 seconds. That's it. From terminal to a global CDN." / 「20 秒。這就是 Vercel。」 |
| **1:10 – 1:20** | Slide / code split: leapcore-iface `agent.py` | Show `AgentBase` ABC on screen | "leapcore-iface is the reason none of this is framework-locked. `AgentBase` doesn't know about ADK or Claude Agent SDK. Swap the binding, keep the business logic." / 「leapcore-iface 讓這整套架構不被任何框架綁死。ADK、Claude Agent SDK、Semantic Kernel — 換 binding，不換邏輯。」 |
| **1:20 – 1:30** | QR codes slide (two QRs side by side) | Hold steady, point at screen | "Repo is public — link on the left. Right QR is LeapChat — same stack, built for enterprise. Private beta is open." / 「左邊是開源 repo，右邊是 LeapChat，同一套架構的企業版，private beta 現在開放。」 |

---

**Backup talking points** (如果某段卡住或時間超了):
- Hook demo 太短: 多解釋 "This is a BeforeTool hook — it runs synchronously before Claude executes any bash command. You can write any shell logic in it."
- Vercel deploy 太慢: "While this deploys, let me show you the architecture diagram on page 2..."
- GitMCP response slow: Skip the live query, show `git log --oneline -5` instead and say "The commit from that MCP session is right here — commit `664d060`, message: 'fix: track data/ directory via .gitkeep to prevent SQLite init failure'. That's Issue #2. PR #1 and #3 are right above it."

---

## SECTION 3: Registration Form Text

> 登記表單用：https://s.sted.tw/iuyYZg
> 下面每個欄位直接複製貼上，英文優先。

---

### Project Name (選 1 個，3 個選項)

**Option A (推薦):**
```
digest-agent: Live Rewrite with Claude Code
```

**Option B (技術感強):**
```
From Streamlit to ADK TypeScript — A Claude Code-Directed Rewrite
```

**Option C (故事感):**
```
I Asked Claude Code to Rebuild My App. Here's What Happened.
```

---

### One-Line Description (under 100 chars, English)

```
AI news digest agent rebuilt live from Python/Streamlit to Next.js/ADK TypeScript by Claude Code itself.
```

*(96 chars)*

---

### Claude Code Usage (2-3 sentences)

```
Claude Code was the primary architect of this project's rewrite — not a code autocompleter. It orchestrated parallel sub-agent teams to refactor Python modules, scaffold the Next.js app, and write tests simultaneously. Hooks (BeforeTool) enforced data safety policies during the live session, and MCP servers gave Claude Code direct repository access to query GitHub issues and commit fixes without shell escapes.
```

---

### MCP Usage (1-2 sentences)

```
Two MCP servers are live in the demo: GitMCP (github.com/modelcontextprotocol/servers) for direct GitHub issue inspection and auto-commit, and @modelcontextprotocol/server-filesystem for structured repo read/write. Together they eliminate the "copy-paste from GitHub to terminal" loop that slows down real agent-driven development workflows.
```

---

### What Makes It WOW (2-3 sentences for judges)

```
The meta-layer is the story: Claude Code rewrote the app that is being demoed, and this submission was also produced inside Claude Code. The timing is deliberate — Google ADK TypeScript was announced days before the deadline, and this project integrated it immediately, showing how leapcore-iface's framework-agnostic ABCs let you adopt a new agent runtime without touching business logic. The dual-LLM architecture (Gemini 2.5 Flash + Claude Sonnet 4.6, switchable via one env var) demonstrates the Vercel AI SDK provider abstraction in a real production-pattern app, not a toy example.
```

---

### Speaker Bio (English, 2-3 sentences)

```
Jimmy Liao is a Google Developer Expert (GDE) in AI/ML and the founder of LeapDesign, a Taipei-based AI product studio. He builds enterprise AI assistants for Taiwan's research institutions, including HISP RAG (deployed at NTU) and LeapChat, a production multi-tenant AI assistant currently in private beta. He runs workshops on Claude Code, Gemini CLI, and agent architecture across Taiwan's developer community.
```

---

## SECTION 4: Pre-Submission Checklist

> 截止：2026/5/7 18:00。建議 5/5 前全部完成，留 2 天緩衝。

---

### Code Items

- [ ] `feature/nextjs-rewrite` branch merged to `main` (or demo-ready branch exists)
- [ ] Vercel project linked (`vercel link` done, confirm with `vercel ls`)
- [ ] Live Vercel URL works and is publicly accessible
- [ ] `LLM_PROVIDER=claude` path tested end-to-end (streaming confirmed in browser)
- [ ] `LLM_PROVIDER=gemini` path tested end-to-end
- [ ] `scripts/guard_rails.sh` hook wired in `.claude/settings.json` as `BeforeTool`
- [ ] `scripts/deny-env-edit.sh` hook wired and tested
- [ ] GitMCP MCP server confirmed working (`claude mcp list` shows it)
- [ ] Issue #2 closed, commit hash noted for demo script
- [ ] `leapcore-iface` package importable from Next.js app (or Python module path clear for slide)
- [ ] README updated with new stack description + demo video link
- [ ] `github.com/jimmyliao/digest-agent` repo is public and up to date

---

### PDF Items

- [ ] Brief designer with Page 1-3 content from Section 1 above
- [ ] Architecture ASCII art converted to proper diagram (Figma / Excalidraw)
- [ ] QR codes generated:
  - [ ] `github.com/jimmyliao/digest-agent`
  - [ ] `leapchat.leapdesign.ai` (or beta signup form URL)
- [ ] Speaker bio photo ready (headshot, min 300dpi for print)
- [ ] PDF exported at 3 pages exactly (check page count before submit)
- [ ] PDF file size under 10 MB
- [ ] Proofread all English text (no typos in headlines — judges screenshot everything)

---

### Video Items

- [ ] Demo environment rehearsed 3+ times (timing must be under 90s)
- [ ] Terminal font size 20px+, dark theme, no notifications
- [ ] Screen recording software ready (QuickTime / OBS, 1920x1080 min)
- [ ] Microphone tested (no echo, no fan noise — use external mic if on MBP)
- [ ] Record 3 takes, pick the cleanest
- [ ] Edit: trim silence at start/end, add captions if time allows
- [ ] Upload to YouTube (unlisted OK) or Google Drive
- [ ] Confirm video URL is shareable before putting in form
- [ ] Video is exactly ≤ 90 seconds (re-record if over)

---

### Form Items

- [ ] Registration form open: https://s.sted.tw/iuyYZg
- [ ] Project name selected (recommend Option A from Section 3)
- [ ] One-line description copied from Section 3
- [ ] Claude Code usage text ready to paste
- [ ] MCP usage text ready to paste
- [ ] WOW factor text ready to paste
- [ ] Speaker bio text ready to paste
- [ ] PDF attached
- [ ] Video URL entered
- [ ] Speaker email confirmed: `max.jy.liao@gmail.com`
- [ ] Form submitted before 2026/5/7 18:00
- [ ] Confirmation email received and archived

---

### Day-of Items (5/18 政大公企中心 A431)

- [ ] Arrive 30 min early (audience 800 — room will be set up early)
- [ ] Bring MacBook + USB-C dongle (HDMI + USB-A)
- [ ] Test projector connection before session starts
- [ ] Have demo environment running locally as fallback (if Vercel URL fails)
- [ ] `.env` with both `GEMINI_API_KEY` and `ANTHROPIC_API_KEY` loaded
- [ ] Backup: pre-recorded video on local disk (in case live demo fails)
- [ ] Business cards / QR code for LeapChat beta signup

---

## 附錄：架構補充說明（給自己備忘）

### leapcore-iface 的定位解釋（口頭版）

> "Think of it like the Vercel AI SDK — but for the agent layer, not the model layer.
> Vercel AI SDK lets you swap `@ai-sdk/google` for `@ai-sdk/anthropic` without changing your chat interface.
> leapcore-iface does the same for ADK vs Claude Agent SDK vs Semantic Kernel — you swap the *agent runtime binding*, not the business logic."

### 為什麼現在時機對

1. Google ADK TypeScript 剛宣布 → 率先整合，timing signal 很強
2. Vercel AI SDK dual-provider 是目前最成熟的 TS AI SDK → 搭配 ADK 是自然組合
3. Claude Code Hooks + MCP 是本屆 showcase 核心主題 → 完整展示兩個功能
4. 整個 session 是 meta showcase：用 Claude Code 做 Claude Code showcase 的內容

### 常見 Q&A 備案

**Q: leapcore-iface 是 npm package 嗎？**
A: 目前是 in-repo Python module，TypeScript port 進行中。核心概念是公開的，可以直接用。

**Q: 為什麼不直接用 ADK，要加一層 leapcore-iface？**
A: 因為 ADK TypeScript 剛出來，API 還在變。抽象層讓我不用每次 ADK breaking change 都重寫整個 orchestrator。

**Q: LeapChat 和 digest-agent 什麼關係？**
A: digest-agent 是開源 reference implementation。LeapChat 是同架構的企業產品，用在 NTU HISP 和其他客戶。

**Q: 為什麼同時用 Gemini 和 Claude？**
A: 不同任務有不同最佳解。Gemini 2.5 Flash 快、grounding 好，適合 RSS triage。Claude Sonnet 4.6 instruction following 強，適合精細摘要壓縮。用 Vercel AI SDK 讓切換成本趨近於零。
