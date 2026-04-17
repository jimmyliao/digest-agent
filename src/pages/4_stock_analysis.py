"""Stock Analysis — ADK Multi-Agent 個股分析頁面。

使用 Google ADK 的 multi-agent 架構，
透過 3 個專業 agent（新聞、產業、市場）協作完成個股分析。
"""

import asyncio

import streamlit as st

st.set_page_config(page_title="📈 個股分析", page_icon="📈", layout="wide")


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


async def run_analysis(runner, user_id: str, query: str) -> str:
    """Run the stock analysis pipeline and collect agent responses."""
    session = await runner.session_service.create_session(
        app_name="stock_analysis", user_id=user_id
    )

    from google.genai import types

    content = types.Content(
        role="user", parts=[types.Part.from_text(text=query)]
    )

    full_response = []
    async for event in runner.run_async(
        user_id=user_id, session_id=session.id, new_message=content
    ):
        if event.content and event.content.parts:
            for part in event.content.parts:
                if part.text:
                    full_response.append(part.text)

    return "\n".join(full_response)


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
            result = asyncio.run(run_analysis(runner, "streamlit_user", query))
            status.update(label="✅ 分析完成", state="complete")
        except Exception as e:
            status.update(label="❌ 分析失敗", state="error")
            st.error(f"錯誤：{e}")
            result = None

    if result:
        st.markdown("---")
        st.markdown(result)

        # Export options
        st.markdown("---")
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
