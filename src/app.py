"""Digest Agent - Streamlit 主入口."""

import logging
import os

import streamlit as st
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=os.environ.get("LOG_LEVEL", "INFO"),
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)

from src.models.database import init_db  # noqa: E402

init_db()

st.set_page_config(
    page_title="Digest Agent",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.sidebar.title("⚡ Digest Agent")
st.sidebar.caption("AI-powered news digest")

st.title("⚡ Digest Agent")
st.write("👈 使用左側選單切換頁面")

col1, col2, col3 = st.columns(3)
with col1:
    st.info("📰 **文章列表**\n\n瀏覽、篩選、管理所有抓取的文章")
with col2:
    st.info("🚀 **發佈控制**\n\nFetch / Summarize / Publish 操作")
with col3:
    st.info("📊 **任務狀態**\n\n即時查看背景任務執行進度")
