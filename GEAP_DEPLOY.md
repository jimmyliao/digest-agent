# Deploy `agents/stock` to Gemini Enterprise Agent Platform

> Optional path. Workshop students do not need this — `make dev-shell` + `make deploy-workshop` (Streamlit + Cloud Run) covers Phase 1-4.
>
> Use this when you want the ADK SequentialAgent as a **managed production endpoint** callable by other systems (vs. a Streamlit dashboard for humans).

---

## 為何用 GEAP / Agent Engine

| | Cloud Run (`make deploy-workshop`) | GEAP Agent Engine (`make deploy-agent-engine`) |
|---|------------------------------------|------------------------------------------------|
| 部署單位 | 容器 image（Streamlit app） | ADK agent object（managed runtime）|
| 適合場景 | 給人看的 dashboard、UI 互動 | API endpoint 給其他系統 / agent 串接 |
| 計費 | 用量 + cold start | per-request + idle session |
| Region | asia-east1 OK | 多在 us-central1（亞洲 rollout 中）|
| 對 ADK 1.x 相容 | 不適用 | ✅（透過 `google-cloud-aiplatform[agent_engines,adk]`）|

兩者**不互斥**。你可以同時部署：Cloud Run 跑 UI，UI 在 server side 呼叫 Agent Engine 的 endpoint。

---

## 前置條件

### 1. gcloud 環境
```bash
gcloud auth application-default login
gcloud config set project YOUR_PROJECT_ID
gcloud services enable aiplatform.googleapis.com storage.googleapis.com
```

### 2. IAM roles（執行 deploy 的帳號）
- `roles/aiplatform.user`
- `roles/storage.admin`

```bash
# 例：給自己加 role
USER=$(gcloud config get account)
gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
  --member="user:$USER" --role="roles/aiplatform.user"
gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
  --member="user:$USER" --role="roles/storage.admin"
```

### 3. Staging bucket（Cloud Storage）
Agent Engine 需要 staging bucket 暫放打包後的 agent artifact。

```bash
PROJECT=YOUR_PROJECT_ID
gsutil mb -l us-central1 gs://$PROJECT-agents
```

### 4. Python deps
```bash
uv sync --extra geap
# 等同：uv add 'google-cloud-aiplatform[agent_engines,adk]>=1.112'
```

---

## Deploy

```bash
GCP_PROJECT=YOUR_PROJECT_ID \
STAGING_BUCKET=gs://YOUR_PROJECT_ID-agents \
GEMINI_API_KEY=YOUR_KEY \
make deploy-agent-engine
```

完成後印出：
```
✅ Deployed: projects/PROJECT_NUM/locations/us-central1/reasoningEngines/NNNN
```

deploy 約 3-5 分鐘（背景跑 Cloud Build）。

---

## 呼叫 deployed agent

```python
import vertexai
import asyncio

PROJECT = "YOUR_PROJECT_ID"
LOCATION = "us-central1"
RESOURCE = "projects/.../reasoningEngines/NNNN"  # deploy 完印出的 resource ID

client = vertexai.Client(project=PROJECT, location=LOCATION)
remote = client.agent_engines.get(RESOURCE)

async def run():
    async for event in remote.async_stream_query(
        user_id="demo-user",
        message="分析台積電 AI 晶片供應鏈"
    ):
        print(event)

asyncio.run(run())
```

---

## 清理

```python
remote.delete(force=True)
```

或從 GCP Console：Vertex AI → Agent Builder → Reasoning Engines → 選 → Delete。

---

## 支援的 Region

`us-central1` 最完整。其他 region 在 rollout — deploy 前查 [agent locations](https://docs.cloud.google.com/gemini-enterprise-agent-platform/resources/agent-locations)。

亞洲區（asia-*）多數還沒上 Agent Engine，需指定 `GCP_LOCATION=us-central1`（預設）。

---

## 與 Workshop 的關係

5/9 GDG Build with AI Taichung **不教這個**。Phase 1-4 學員照 Streamlit + Cloud Run + ADK Multi-Agent 走，這份 doc 是 stretch goal / 後續 production 用。

5/18 AIA Showcase 可作為「ADK agent 從 demo → production endpoint」的延伸 talking point。

---

## 不修改的部分

- `agents/stock/agent.py` 不動 — 仍 ADK 1.x SequentialAgent
- `src/` Streamlit pages 不動 — 仍 in-process Runner
- `Makefile` `deploy-workshop` 不動 — Cloud Run 路徑保留
- `pyproject.toml` base deps 不動 — `geap` 是 optional group
