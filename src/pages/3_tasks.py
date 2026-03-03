"""任務狀態頁面 - 查看背景任務執行進度."""

import json
from datetime import datetime

import streamlit as st

st.set_page_config(page_title="任務狀態 - Digest Agent", page_icon="📊", layout="wide")

from src.models.database import ArticleDB, SessionLocal, TaskRecordDB  # noqa: E402


def load_tasks(limit: int = 50):
    db = SessionLocal()
    try:
        return db.query(TaskRecordDB).order_by(TaskRecordDB.started_at.desc()).limit(limit).all()
    finally:
        db.close()


def load_stats():
    db = SessionLocal()
    try:
        total = db.query(ArticleDB).count()
        pending = db.query(ArticleDB).filter(ArticleDB.publish_status == "pending").count()
        summarized = db.query(ArticleDB).filter(ArticleDB.publish_status == "summarized").count()
        published = db.query(ArticleDB).filter(ArticleDB.publish_status == "published").count()
        failed = db.query(ArticleDB).filter(ArticleDB.publish_status == "failed").count()
        return {
            "total": total,
            "pending": pending,
            "summarized": summarized,
            "published": published,
            "failed": failed,
        }
    finally:
        db.close()


def delete_task(task_id: str):
    db = SessionLocal()
    try:
        task = db.query(TaskRecordDB).filter(TaskRecordDB.task_id == task_id).first()
        if task:
            db.delete(task)
            db.commit()
    finally:
        db.close()


# ── UI ───────────────────────────────────────────────────────

st.title("📊 任務狀態")

# Auto-refresh toggle
col1, col2 = st.columns([3, 1])
with col1:
    auto_refresh = st.toggle("🔄 自動更新（每 5 秒）", value=False)
with col2:
    if st.button("立即更新", use_container_width=True):
        st.rerun()

# Stats overview
stats = load_stats()
st.subheader("📈 文章統計")
metric_cols = st.columns(5)
metric_cols[0].metric("總文章數", stats["total"])
metric_cols[1].metric("⏳ 待摘要", stats["pending"])
metric_cols[2].metric("✅ 已摘要", stats["summarized"])
metric_cols[3].metric("📤 已發佈", stats["published"])
metric_cols[4].metric("⚠️ 失敗", stats["failed"])

st.divider()

# Task records
st.subheader("📋 任務記錄")

tasks = load_tasks(50)
if not tasks:
    st.info("尚無任務記錄。請先到「發佈控制」頁面執行操作。")
else:
    STATUS_ICON = {
        "queued": "⏳",
        "running": "🔄",
        "completed": "✅",
        "failed": "❌",
    }
    TYPE_LABEL = {
        "fetch": "📥 Fetch",
        "summarize": "🤖 Summarize",
        "publish": "📤 Publish",
    }

    for task in tasks:
        icon = STATUS_ICON.get(task.status, "❓")
        type_label = TYPE_LABEL.get(task.task_type, task.task_type)

        with st.container():
            col_info, col_time, col_del = st.columns([3, 2, 1])
            with col_info:
                st.write(f"{icon} **{type_label}** · `{task.task_id}`")
                st.caption(f"狀態：{task.status}")

                if task.result_json:
                    try:
                        result_data = json.loads(task.result_json)
                        result_str = "  ".join([f"{k}: {v}" for k, v in result_data.items()])
                        st.caption(f"結果：{result_str}")
                    except Exception:
                        st.caption(f"結果：{task.result_json}")

                if task.error_json:
                    try:
                        error_data = json.loads(task.error_json)
                        st.caption(f"❌ 錯誤：{error_data.get('error', task.error_json)}")
                    except Exception:
                        st.caption(f"❌ 錯誤：{task.error_json}")

            with col_time:
                if task.started_at:
                    try:
                        st.caption(f"開始：{task.started_at.strftime('%m-%d %H:%M:%S')}")
                    except Exception:
                        pass
                if task.completed_at:
                    try:
                        elapsed = (task.completed_at - task.started_at).total_seconds()
                        st.caption(f"完成：{task.completed_at.strftime('%m-%d %H:%M:%S')} ({elapsed:.1f}s)")
                    except Exception:
                        pass

            with col_del:
                if st.button("🗑️", key=f"del_{task.task_id}", help="刪除此記錄"):
                    delete_task(task.task_id)
                    st.rerun()

            st.divider()

# Auto-refresh
if auto_refresh:
    import time
    time.sleep(5)
    st.rerun()
