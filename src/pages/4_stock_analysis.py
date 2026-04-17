"""Stock Analysis — ADK Multi-Agent 個股分析頁面。

使用 Google ADK 的 multi-agent 架構，
透過 3 個專業 agent（新聞、產業、市場）協作完成個股分析。
"""

import asyncio
import os
from dataclasses import dataclass, field

import streamlit as st

# ADK 需要 GOOGLE_API_KEY，自動從 GEMINI_API_KEY fallback
if not os.environ.get("GOOGLE_API_KEY") and os.environ.get("GEMINI_API_KEY"):
    os.environ["GOOGLE_API_KEY"] = os.environ["GEMINI_API_KEY"]

st.set_page_config(page_title="📈 個股分析", page_icon="📈", layout="wide")


@dataclass
class AgentEvent:
    """單一 agent event 的摘要。"""

    agent: str = ""
    text: str = ""
    tool_calls: list = field(default_factory=list)
    tool_results: list = field(default_factory=list)


# --- ADK Runner setup ---
@st.cache_resource
def get_runner():
    """Initialize ADK runner (cached across reruns)."""
    from google.adk.runners import Runner
    from google.adk.sessions import InMemorySessionService

    from agents.stock import root_agent

    return Runner(
        agent=root_agent,
        app_name="stock_analysis",
        session_service=InMemorySessionService(),
    )


async def run_analysis(runner, user_id: str, query: str) -> tuple[str, list[AgentEvent]]:
    """Run the stock analysis pipeline and collect agent responses + debug info."""
    session = await runner.session_service.create_session(
        app_name="stock_analysis", user_id=user_id
    )

    from google.genai import types

    content = types.Content(
        role="user", parts=[types.Part.from_text(text=query)]
    )

    full_response = []
    events_log: list[AgentEvent] = []

    async for event in runner.run_async(
        user_id=user_id, session_id=session.id, new_message=content
    ):
        evt = AgentEvent(agent=getattr(event, "author", "") or "unknown")

        # Collect text content
        if event.content and event.content.parts:
            for part in event.content.parts:
                if part.text:
                    full_response.append(part.text)
                    evt.text = part.text[:500]
                # Collect function calls
                if hasattr(part, "function_call") and part.function_call:
                    fc = part.function_call
                    evt.tool_calls.append({
                        "tool": fc.name,
                        "args": dict(fc.args) if fc.args else {},
                    })
                # Collect function responses
                if hasattr(part, "function_response") and part.function_response:
                    fr = part.function_response
                    response_data = dict(fr.response) if fr.response else {}
                    # Truncate large responses
                    summary = str(response_data)[:300]
                    evt.tool_results.append({
                        "tool": fr.name,
                        "summary": summary,
                    })

        if evt.text or evt.tool_calls or evt.tool_results:
            events_log.append(evt)

    return "\n".join(full_response), events_log


# --- UI ---
st.title("📈 個股分析")
st.caption("ADK Multi-Agent 協作分析：新聞面 × 產業面 × 市場面")

# Sidebar info
with st.sidebar:
    st.markdown("### Agent 架構")
    st.markdown(
        """
    ```
    stock_analysis_pipeline (Sequential)
    ├── 1. news_collector    → DB/RSS 新聞
    ├── 2. industry_analyst  → 產業分析
    ├── 3. market_analyst    → 市場趨勢
    └── 4. stock_orchestrator → 整合報告
    ```
    """
    )
    st.markdown("---")
    st.markdown(
        "⚠️ **免責聲明**：分析結果僅供參考，不構成任何投資建議。"
    )

# Input
col1, col2 = st.columns([3, 1])
with col1:
    query = st.text_input(
        "輸入股票代號或公司名稱",
        placeholder="例如：2330 台積電、鴻海、聯發科",
    )
with col2:
    st.markdown("<br>", unsafe_allow_html=True)
    run_button = st.button("🔍 開始分析", type="primary", use_container_width=True)

# Execution
if run_button and query:
    with st.status("🤖 Agent 協作分析中...", expanded=True) as status:
        st.write("📰 news_collector：蒐集相關新聞...")
        st.write("🏭 industry_analyst：分析產業動態...")
        st.write("📊 market_analyst：評估市場趨勢...")
        st.write("📋 stock_orchestrator：整合分析報告...")

        try:
            runner = get_runner()
            result, events_log = asyncio.run(
                run_analysis(runner, "streamlit_user", query)
            )
            status.update(label="✅ 分析完成", state="complete")
        except Exception as e:
            status.update(label="❌ 分析失敗", state="error")
            st.error(f"錯誤：{e}")
            result = None
            events_log = []

    if result:
        st.markdown("---")
        st.markdown(result)

        # Debug expander — Agent 協作細節
        st.markdown("---")
        with st.expander("🔍 Agent 協作細節（DevTools）", expanded=False):
            st.caption("每個 agent 的回應與 tool 呼叫紀錄，等同 adk web 的 Events 面板")

            for i, evt in enumerate(events_log):
                agent_icon = {
                    "news_collector": "📰",
                    "industry_analyst": "🏭",
                    "market_analyst": "📊",
                    "stock_orchestrator": "📋",
                }.get(evt.agent, "🤖")

                st.markdown(f"**#{i+1} {agent_icon} {evt.agent}**")

                # Tool calls
                if evt.tool_calls:
                    for tc in evt.tool_calls:
                        st.code(
                            f"🔧 Tool: {tc['tool']}\n"
                            f"   Args: {tc['args']}",
                            language="text",
                        )

                # Tool results
                if evt.tool_results:
                    for tr in evt.tool_results:
                        st.code(
                            f"✅ Result: {tr['tool']}\n"
                            f"   {tr['summary']}",
                            language="text",
                        )

                # Text (truncated)
                if evt.text:
                    preview = evt.text[:200] + "..." if len(evt.text) > 200 else evt.text
                    st.markdown(f"> {preview}")

                st.markdown("---")

        # Export options
        col_a, col_b = st.columns(2)
        with col_a:
            st.download_button(
                "📥 下載報告 (Markdown)",
                data=result,
                file_name=f"stock_analysis_{query}.md",
                mime="text/markdown",
            )
        with col_b:
            if st.button("📤 推送到 Telegram"):
                st.info("Telegram 推送功能開發中（重用現有 publisher）")

elif run_button and not query:
    st.warning("請輸入股票代號或公司名稱")
