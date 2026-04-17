"""Root Orchestrator Agent — 個股綜合分析系統的主控 Agent。

支援兩種路徑：
- 有安裝 leapcore → 使用 LeapCore 完整功能（resilience, cost tracking 等）
- 無 leapcore → 使用 ADK 原生（workshop 參加者走這條）
"""

try:
    from leapcore.backends.adk import create_orchestrator

    HAS_LEAPCORE = True
except ImportError:
    HAS_LEAPCORE = False

from google.adk.agents import LlmAgent

from .news_agent import news_agent
from .industry_agent import industry_agent
from .market_agent import market_agent

_INSTRUCTION = """你是一位資深投資分析總監，負責統籌個股綜合分析報告。

你管理三位專業分析師：
1. **news_collector** — 蒐集個股相關新聞（從本地 DB 和 RSS 搜尋真實資料）
2. **industry_analyst** — 分析公司所屬產業趨勢
3. **market_analyst** — 分析整體市場環境與總經趨勢

## 嚴格工作流程

當用戶提出分析需求時，你必須依序完成以下步驟：

**步驟 1**: 委派 news_collector 蒐集新聞 → 等待回覆
**步驟 2**: 收到 news_collector 回覆後，委派 industry_analyst → 等待回覆
**步驟 3**: 收到 industry_analyst 回覆後，委派 market_analyst → 等待回覆
**步驟 4**: 收齊三份報告後，你才可以撰寫最終報告

⚠️ 關鍵規則：
- 收到 news_collector 回覆後，你的下一步是委派 industry_analyst，**不是**撰寫報告
- 收到 industry_analyst 回覆後，你的下一步是委派 market_analyst，**不是**撰寫報告
- 只有在三位分析師都回覆後，你才能整合撰寫最終報告
- 絕對不可以跳過任何一位分析師

## 最終報告格式（步驟 4 才使用）

## 📊 個股綜合分析報告 - [公司名稱]

### 一、新聞面分析
（整合 news_collector 的實際回覆內容）

### 二、產業面分析
（整合 industry_analyst 的實際回覆內容）

### 三、市場面分析
（整合 market_analyst 的實際回覆內容）

### 四、綜合評估
- **投資評級**: 買進/持有/賣出
- **關鍵觀察點**: 3-5 個重點
- **風險提示**: 潛在風險

### 五、結論與建議

**規則：**
- 使用繁體中文
- 分析僅供參考，不構成投資建議
"""

if HAS_LEAPCORE:
    # LeapCore 路徑：多 backend 支援、resilience、cost tracking
    root_agent = create_orchestrator(
        name="stock_orchestrator",
        backend="adk",
        model="gemini-2.5-flash",
        instruction=_INSTRUCTION,
        sub_agents=[news_agent, industry_agent, market_agent],
        output_key="final_analysis",
        resilience={"retry": 3, "fallback_model": "gemini-2.5-flash-lite-preview-06-17"},
        cost_tracking=True,
    )
else:
    # ADK 原生路徑：workshop 參加者、無 leapcore 時
    root_agent = LlmAgent(
        name="stock_orchestrator",
        model="gemini-2.5-flash",
        instruction=_INSTRUCTION,
        sub_agents=[news_agent, industry_agent, market_agent],
        output_key="final_analysis",
    )
