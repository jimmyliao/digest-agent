"""Root Orchestrator Agent — 個股綜合分析系統的主控 Agent。

使用 SequentialAgent 保證三位分析師依序執行，
最後由 report_writer 整合三份報告。

支援兩種路徑：
- 有安裝 leapcore → 使用 LeapCore 完整功能（resilience, cost tracking 等）
- 無 leapcore → 使用 ADK 原生（workshop 參加者走這條）
"""

try:
    from leapcore.backends.adk import create_orchestrator

    HAS_LEAPCORE = True
except ImportError:
    HAS_LEAPCORE = False

from google.adk.agents import LlmAgent, SequentialAgent

from .industry_agent import industry_agent
from .market_agent import market_agent
from .news_agent import news_agent

# 第四個 agent：讀取前三位的 output_key，整合成最終報告
report_writer = LlmAgent(
    name="stock_orchestrator",
    model="gemini-2.5-flash",
    instruction="""你是一位資深投資分析總監，負責整合三位分析師的報告。

你可以從 session state 中讀取以下資料：
- **news_analysis**: news_collector 蒐集的新聞分析
- **industry_analysis**: industry_analyst 的產業分析
- **market_analysis**: market_analyst 的市場分析

請根據這三份報告，撰寫一份完整的個股綜合分析報告。

## 報告格式

## 📊 個股綜合分析報告

### 一、新聞面分析
（整合 news_analysis 的內容，保留具體新聞標題、來源、利多/利空分類）

### 二、產業面分析
（整合 industry_analysis 的內容）

### 三、市場面分析
（整合 market_analysis 的內容）

### 四、綜合評估
- **投資評級**: 買進/持有/賣出
- **關鍵觀察點**: 3-5 個重點
- **風險提示**: 潛在風險

### 五、結論與建議
（綜合三方觀點的最終結論）

**規則：**
- 使用繁體中文
- 分析僅供參考，不構成投資建議
- 確保報告包含三個面向的實際內容，不可遺漏
""",
    output_key="final_analysis",
)

if HAS_LEAPCORE:
    root_agent = create_orchestrator(
        name="stock_analysis_pipeline",
        backend="adk",
        model="gemini-2.5-flash",
        instruction="個股綜合分析 pipeline",
        sub_agents=[news_agent, industry_agent, market_agent, report_writer],
        output_key="final_analysis",
        resilience={"retry": 3, "fallback_model": "gemini-2.5-flash-lite-preview-06-17"},
        cost_tracking=True,
    )
else:
    # SequentialAgent: 保證 news → industry → market → report 依序執行
    root_agent = SequentialAgent(
        name="stock_analysis_pipeline",
        sub_agents=[news_agent, industry_agent, market_agent, report_writer],
    )
