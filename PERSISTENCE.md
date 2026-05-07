# SQLite Persistence (Litestream + GCS) for Next.js `apps/web/`

> 把 `apps/web/` 的整顆 SQLite (`/data/digest.db`) 用 Litestream 即時複製到
> GCS bucket，讓 Cloud Run 重啟 / scale-to-zero / `make deploy-web` 重 build
> 都不會掉資料。**目標 UI 是 Next.js `apps/web/`**（AIA showcase + production
> endpoint），Streamlit `src/` 的 workshop 路徑保持原樣不動。

---

## Architecture

```
                ┌────────────────────────────────────┐
                │ GCS: gs://...-data/digest-db/      │
                │   ├ generations/.../snapshots/     │
                │   └ generations/.../wal/           │  ← 唯一 durable backing
                └─────▲──────────────────────────▲───┘
              restore │           replicate (10s) │
              (cold start)                        │
                     │                            │
              ┌──────┴──────────────────────────────┐
              │ Cloud Run: digest-agent-web (Next.js)│
              │  /data/digest.db ← 唯一 writer      │
              │  litestream replicate -exec         │
              │    "next start"                     │
              │  expose /api/articles, /api/fetch,  │
              │         /api/summarize, /api/publish│
              └──────┬──────────────────────────────┘
                     │ HTTPS GET /api/articles?company=...
                     │   (agent 目前只讀 articles 一個介面；
                     │    UI 自己的 /api/fetch /summarize
                     │    /publish 路徑全部是 server-side
                     │    寫進同一個 /data/digest.db，被
                     │    Litestream 整檔複製到 GCS)
                     │
              ┌──────▼──────────────────────────────┐
              │ Agent Runtime (GEAP)                │
              │  search_db_articles(company)        │
              │   → requests.get(DIGEST_API_URL...) │
              └─────────────────────────────────────┘

           [Streamlit workshop 路徑 完全不動]
           src/ + Dockerfile + make deploy-workshop
                  ↳ 仍 /tmp/digest.db ephemeral
                  ↳ 5/9 workshop 教材保持完整
```

---

## Three restart scenarios — what survives

| 情境 | Articles / summary / publish_status 是否還在？ | 機制 |
|------|------------------------------------------------|------|
| **Browser refresh** | ✅ 一切資料原樣 | DB 在 server 端，UI 只是 fetcher |
| **Cloud Run cold start**（scale-to-zero 後新請求） | ✅ 5–10s 內完成 restore，資料原樣 | `entrypoint.sh` 開機跑 `litestream restore -if-replica-exists -if-db-not-exists`，從 GCS 拉最新 snapshot + WAL 回 `/data/digest.db` |
| **`make deploy-web` 重 build 鏡像** | ✅ 新容器同樣 restore 後再啟 server，舊資料原樣 | 鏡像本身不帶 DB，Litestream 從 GCS bucket 復原；整顆 `digest.db` 所有 table（articles / channel_configs / 未來新加的 table）一起被覆蓋 |

> ❌ **唯一會掉資料的情境**：直接刪掉 GCS bucket（被 versioning + 30d
> noncurrent retention 額外保護一層）。誤砍可從 generation 救回。

---

## Local dev（不需要 GCS）

```bash
cd apps/web
npm install
npm run dev    # http://localhost:3000
```

`DATABASE_URL` 預設 `file:./data/digest.db`（相對 repo 根，三平台皆可寫）。
不需 litestream binary，不需 GCS 認證；`infra/entrypoint.sh` 在 container
內亦會 graceful fallback：`LITESTREAM_GCS_BUCKET` 未設 → 純跑 `node server.js`。

要走端到端測 agent HTTP 路徑：

```bash
DIGEST_API_URL=http://localhost:3000 \
  uv run python -m agents.stock.invoke_local "TSMC 營運分析"
```

---

## Cloud Shell 部署

```bash
gcloud cloud-shell ssh                  # 或在 console.cloud.google.com 開
git clone https://github.com/jimmyliao/digest-agent.git
cd digest-agent

# 一次性：建 GCS bucket + grant Cloud Run runtime SA
make setup-data-bucket
# 把印出的 LITESTREAM_GCS_BUCKET=... 加進 .env.deploy

# 部署 Next.js to Cloud Run
make deploy-web
# 部署完印出 https://digest-agent-web-xxxxx-uc.a.run.app
# 把這個 URL 加進 .env.deploy 當 DIGEST_API_URL=...，之後 GEAP 重 deploy 會用
```

Cloud Shell 內建 `gcloud` / `gsutil` / `make` / `bash`，不需額外安裝。

---

## WSL（Ubuntu）部署

跟 Cloud Shell 一樣的流程，差別只在第一次需要：

```bash
gcloud auth login
gcloud auth application-default login
gcloud auth application-default set-quota-project YOUR_PROJECT
```

然後：

```bash
make setup-data-bucket
make deploy-web
```

> ⚠️ WSL 用 Windows 編輯器（VS Code 的 CRLF 預設）改 shell script 容易把
> `entrypoint.sh` 行尾搞成 CRLF 讓容器啟動失敗。本 repo 已加
> `.gitattributes` 強制 `*.sh text eol=lf` 防呆。

---

## 成本（粗估 ~$0.50 USD/月）

以一個典型 demo / 個人用 digest-agent（articles 表幾百到幾千列）為例：

| 項目 | 估算 | 月費 |
|------|------|------|
| GCS standard storage（`us-central1`） | DB ~10 MB，含 WAL 與 30d noncurrent ~50 MB | < $0.001 |
| GCS Class A operations（write）| Litestream 每 10s 寫一次，~260k ops/月，但 5 GB/月**免費額度**內 | $0（額度內）|
| GCS Class B operations（read）| 冷啟讀回 + 列出，~1k ops/月 | < $0.01 |
| Cloud Run vCPU + memory（min instances=0）| Idle = 0，假設每天被叫 100 次每次 1s | ~$0.30 |
| Cloud Run egress | API JSON 體積小 | < $0.10 |
| **合計** | | **~$0.50 USD / 月** |

> 注意：實際成本受 Cloud Run 流量主導；如果 agent 大量打 `/api/articles`，
> 成本會線性上升。Cloud Run 有 2M 請求/月免費額度，對 demo 場景幾乎用不到。
> 設一個 `$5/月` budget alert（`make setup-billing-alert`）保險。

---

## Troubleshooting

### Litestream 看不到 GCS（log 印 `replica not found` 或 restore 失敗）
1. `gsutil ls gs://${LITESTREAM_GCS_BUCKET}/digest-db/` 是否存在路徑？
   - 第一次 deploy 還沒寫過 → 預期空，restore 跳過、server 直接啟動，**正常**
   - 應該有資料但拿不到 → 檢查 SA 權限（下一條）
2. `gsutil iam get gs://${LITESTREAM_GCS_BUCKET}` 是否包含
   `${PROJECT_NUMBER}-compute@developer.gserviceaccount.com` +
   `roles/storage.objectAdmin`？
   - 沒有 → `make setup-data-bucket` 重跑（idempotent）

### Cloud Run 啟動超慢 / cold start > 30s
- Litestream restore 大檔（>100 MB）會慢；確認 `digest.db` 還是合理大小
- 檢查容器 log：`gcloud run services logs read digest-agent-web --region us-central1 --limit 50`
- 若 restore 卡住 → 可能 GCS 區域與 Cloud Run 區域不同；`setup-data-bucket.sh`
  預設 `us-central1`，與 `deploy-web` 一致

### Agent 走了 SQLite fallback 而不是 HTTP（log 印 `source: "local_db"`）
- 確認 GEAP 部署時 `DIGEST_API_URL` 有被 inject：
  - `.env.deploy` 加 `DIGEST_API_URL=https://digest-agent-web-...run.app`
  - `make deploy-agent-engine` 重跑後新的 reasoning engine 會帶這個 env var
- 檢查 Cloud Run URL 從 GEAP runtime 是否可達（HTTPS、無 firewall 限制）
- 若 Cloud Run 端 5xx / timeout → agent 會自動 fallback 到本地 SQLite
  （這是 graceful degradation，不是 bug；但 GEAP 內無本地 DB 會回空 list）

### `make deploy-web` 報 `LITESTREAM_GCS_BUCKET` 缺值
先跑 `make setup-data-bucket`，把它印出的值寫進 `.env.deploy`，再跑 `make deploy-web`。

---

## 與 5/9 workshop 的關係

**Workshop 不教這個。**

- `make deploy-workshop` / `CLOUD_SHELL_WORKSHOP.md` / `bwai0509-taichung/` 全部
  保持原樣，`/tmp/digest.db` ephemeral 是教學示範刻意保留（讓學員體驗
  「為什麼 SQLite 在 Cloud Run 不夠」這個學習點，再教 PostgreSQL / Supabase）。
- 本文件描述的 Litestream 路徑是純為 **AIA showcase + production endpoint**
  ——讓 Next.js `apps/web/` 部署上去後 fetch + summary 真正持久。
- 兩條路徑共存於同 repo：
  - Streamlit workshop → root `Dockerfile` + `make deploy-workshop` → `digest-agent-workshop` Cloud Run
  - Next.js production → `apps/web/Dockerfile` + `make deploy-web` → `digest-agent-web` Cloud Run

---

See also: [`GEAP_DEPLOY.md`](./GEAP_DEPLOY.md)
