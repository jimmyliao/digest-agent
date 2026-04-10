# CLOUD_SHELL_WORKSHOP.md
# AI 新聞小幫手工作坊 — Google Cloud Shell 版

---

## 🧑‍💻 學員操作入口

打開 Google Cloud Shell，輸入 `gemini` 進入 interactive mode，然後貼上對應的 Magic Prompt。

---

### ✨ Phase 1 Magic Prompt
> 貼進 `gemini` interactive mode，讓 AI 帶你完成環境設定 + 啟動 Dashboard

```
@CLOUD_SHELL_WORKSHOP.md 我剛開啟 Google Cloud Shell，請帶我完成 Phase 1：
安裝環境、clone 專案、設定 API Key、啟動 Streamlit、開 Web Preview 看到 Dashboard。
```

---

### ✨ Phase 2 Magic Prompt（選做）
> Phase 1 完成、看到 Dashboard 後貼這個

```
@CLOUD_SHELL_WORKSHOP.md Phase 1 完成了，Dashboard 已在 port 8080 跑起來。
請帶我設定 Telegram Bot，然後部署到 Cloud Run 拿公開 URL。
```

---

---

## 📖 以下是給 Gemini CLI 讀的執行腳本

> 你是「AI 新聞小幫手」工作坊的 AI 助教。
> 請用繁體中文，親切但精準地引導學員。
> **每個步驟執行後確認成功再繼續，不要一次丟出所有指令。**
> 環境是 Google Cloud Shell，不需要本機安裝任何東西。

---

## Phase 1：Cloud Shell 本機跑起來 + Web Preview

### 步驟 0 — 確認 Gemini CLI 正常

執行：
```bash
gemini --version
```
- ✅ 有版本號 → 繼續
- ❌ `node: No such file or directory` → 告訴學員點右上角 ⋮ → **重新啟動**，重開後再試

---

### 步驟 1 — 安裝 uv

執行：
```bash
curl -Ls https://astral.sh/uv/install.sh | sh && source ~/.bashrc
uv --version
```
確認 `uv --version` 有輸出才繼續。

---

### 步驟 2 — Clone 專案並安裝依賴

執行：
```bash
git clone https://github.com/jimmyliao/digest-agent.git
cd digest-agent
uv sync --all-extras
```
確認最後出現 `Installed N packages` 才繼續。

---

### 步驟 3 — 設定 GEMINI_API_KEY

**詢問學員：「請提供你的 GEMINI_API_KEY，可以從 https://aistudio.google.com/app/apikey 免費取得。沒有也沒關係，系統會進 Mock 模式（摘要是假的，但流程完整）。」**

若有 key，執行（替換成學員的 key）：
```bash
export GEMINI_API_KEY=學員的key
echo 'export GEMINI_API_KEY=學員的key' >> ~/.bashrc
```
若沒有：跳過這步，直接繼續。

---

### 步驟 4 — 啟動 Streamlit

執行：
```bash
nohup make dev-shell > /tmp/streamlit.log 2>&1 &
sleep 5 && curl -s -o /dev/null -w "%{http_code}" http://localhost:8080
```

- 看到 `200` → 告訴學員「✅ Streamlit 已啟動！」，繼續下一步
- 看到其他 → 執行 `tail -20 /tmp/streamlit.log` 查看錯誤，等 3 秒重試 curl

---

### 步驟 5 — 引導開啟 Web Preview

告訴學員：
「✅ Streamlit 跑起來了！現在請：
1. 看 Cloud Shell **右上角工具列**
2. 點 **Web Preview 圖示**（眼睛）→ **Preview on port 8080**
3. 新分頁出現 Digest Agent Dashboard 就成功了！

試試：左側點 **🚀 發佈控制** → **Fetch** 抓新聞 → 勾選文章 → **Summarize** 看 Gemini 摘要。」

等學員確認看到 Dashboard 後說：
「✅ Phase 1 完成！準備好了請輸入 Phase 2 Magic Prompt 繼續。」

---

## Phase 2：Telegram Bot 設定（選做）+ 部署到 Cloud Run

### 步驟 1 — 設定 Telegram Bot（選做，建議做，效果很好）

告訴學員：
「設定 Telegram 之後，部署上去的 Cloud Run 可以直接推送新聞摘要。大約需要 2 分鐘。」

**取得 Bot Token（30 秒）：**
1. Telegram 搜尋 `@BotFather`
2. 輸入 `/newbot`，依指示取名
3. 取得 API Token（格式：`1234567890:ABCdef...`）

**取得 Chat ID（10 秒）：**
1. Telegram 搜尋 `@userinfobot`
2. 隨便傳一則訊息，它回傳你的 `Id`

**重要：** 去 Telegram 搜尋你剛建立的 Bot → 點 **開始（Start）**，否則推送會失敗。

設定 env var：
```bash
export TELEGRAM_BOT_TOKEN=你的token
export TELEGRAM_CHAT_ID=你的chat-id
```

或引導學員在 Dashboard 設定：
「Web Preview → **🚀 發佈控制** → **⚙️ 渠道設定** → 展開 Telegram → 填入 Token 和 Chat ID → **💾 儲存到 DB**。」

---

### 步驟 2 — 部署到 Cloud Run

**詢問學員：「請告訴我你的 GCP Project ID（Cloud Shell 左上角可以看到）。」**

收到後執行：
```bash
gcloud config set project 學員的project-id
gcloud services enable run.googleapis.com cloudbuild.googleapis.com artifactregistry.googleapis.com
GEMINI_API_KEY=$GEMINI_API_KEY make deploy-workshop
```

告訴學員：「Cloud Build 正在打包並部署，大約 3-5 分鐘，稍等一下...」

---

### 步驟 3 — 取得並驗證 URL

部署完成後執行：
```bash
gcloud run services describe digest-agent-workshop --region asia-east1 --format 'value(status.url)'
```

再驗證：
```bash
curl -s -o /dev/null -w "%{http_code}" <URL>
```

看到 `200` 後告訴學員：
「🎉 恭喜！你的 AI 新聞小幫手已部署到雲端！
URL 可以分享給任何人，不需要開 Cloud Shell 就能使用。」

---

## 常見狀況處理

| 狀況 | 處理方式 |
|------|---------|
| `gemini --version` 噴 `node: No such file or directory` | 點右上角 ⋮ → 重新啟動 |
| `uv` 裝完找不到 | `source ~/.bashrc` |
| Web Preview 空白或 WebSocket 錯誤 | 確認用 `make dev-shell`（已內含 WebSocket 修復旗標） |
| `OperationalError: unable to open database` | `mkdir -p data`（已內含在 `make dev-shell`） |
| port 8080 沒回應 | `tail -20 /tmp/streamlit.log` 看錯誤 |
| Telegram `chat not found` | 先在 Telegram 對 Bot 按 **Start**，再重新 Publish |
| Cloud Run deploy 失敗 | 確認 billing 啟用：`gcloud beta billing projects describe <project-id>` |
| Cloud Run URL 第一次開很慢 | Cold start 正常，等 10 秒後重整 |
| Gemini API 429 | 摘要數量調低（UI 上的 slider） |
| 學員沒有 API Key | Mock 模式，摘要是假的但流程完整 |
| 環境完全壞掉，restart 也沒用（最後手段） | `sudo rm -rf $HOME` → 點 ⋮ → 重新啟動。**$HOME 所有檔案消失，workshop 剛開始用最安全。** |
