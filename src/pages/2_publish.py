"""發佈控制頁面 - Fetch / Summarize / Publish + Sources + 渠道設定."""

import asyncio
import json
import os
import uuid
from datetime import datetime, timezone

import streamlit as st

st.set_page_config(page_title="發佈控制 - Digest Agent", page_icon="🚀", layout="wide")

from src.models.database import (  # noqa: E402
    ArticleDB,
    ChannelConfigDB,
    SessionLocal,
    SourceDB,
    TaskRecordDB,
)
from src.orchestrator import DigestOrchestrator  # noqa: E402


# ── DB helpers ──────────────────────────────────────────────

def list_sources():
    db = SessionLocal()
    try:
        return db.query(SourceDB).all()
    finally:
        db.close()


def add_source(name: str, url: str, category: str = "general", freq: int = 24):
    db = SessionLocal()
    try:
        src = SourceDB(
            id=str(uuid.uuid4())[:8],
            name=name, url=url,
            type="rss", enabled=True,
            frequency_hours=freq, category=category,
        )
        db.add(src)
        db.commit()
    finally:
        db.close()


def toggle_source(source_id: str, enabled: bool):
    db = SessionLocal()
    try:
        src = db.query(SourceDB).filter(SourceDB.id == source_id).first()
        if src:
            src.enabled = enabled
            db.commit()
    finally:
        db.close()


def delete_source(source_id: str):
    db = SessionLocal()
    try:
        src = db.query(SourceDB).filter(SourceDB.id == source_id).first()
        if src:
            db.delete(src)
            db.commit()
    finally:
        db.close()


def list_pending_articles():
    db = SessionLocal()
    try:
        return db.query(ArticleDB).filter(ArticleDB.publish_status == "pending").all()
    finally:
        db.close()


def list_summarized_articles():
    db = SessionLocal()
    try:
        return db.query(ArticleDB).filter(ArticleDB.publish_status == "summarized").all()
    finally:
        db.close()


def save_task_record(task_id: str, task_type: str):
    db = SessionLocal()
    try:
        record = TaskRecordDB(
            task_id=task_id,
            task_type=task_type,
            status="running",
            started_at=datetime.now(timezone.utc),
        )
        db.add(record)
        db.commit()
    finally:
        db.close()


def update_task_record(task_id: str, status: str, result_json: str = None, error_json: str = None):
    db = SessionLocal()
    try:
        record = db.query(TaskRecordDB).filter(TaskRecordDB.task_id == task_id).first()
        if record:
            record.status = status
            record.completed_at = datetime.now(timezone.utc)
            if result_json:
                record.result_json = result_json
            if error_json:
                record.error_json = error_json
            db.commit()
    finally:
        db.close()


# env var defaults per channel
_ENV_DEFAULTS = {
    "telegram": {
        "bot_token": lambda: os.environ.get("TELEGRAM_BOT_TOKEN", ""),
        "chat_id":   lambda: os.environ.get("TELEGRAM_CHAT_ID", ""),
    },
    "email": {
        "smtp_server": lambda: os.environ.get("SMTP_SERVER", ""),
        "smtp_port":   lambda: os.environ.get("SMTP_PORT", "587"),
        "username":    lambda: os.environ.get("SMTP_USER", ""),
        "password":    lambda: os.environ.get("SMTP_PASSWORD", ""),
        "to_address":  lambda: os.environ.get("EMAIL_TO", ""),
        "from_name":   lambda: os.environ.get("SMTP_FROM_NAME", "Digest Agent"),
    },
    "line": {
        "channel_access_token": lambda: os.environ.get("LINE_CHANNEL_TOKEN", ""),
        "to":                   lambda: os.environ.get("LINE_USER_ID", ""),
    },
    "discord": {
        "webhook_url": lambda: os.environ.get("DISCORD_WEBHOOK_URL", ""),
    },
}


def get_channel_config(channel_id: str) -> tuple[dict, dict]:
    """Return (effective_config, source_map).

    effective_config: DB value overrides env var (same as orchestrator).
    source_map: per-key source label — "db" | "env" | "unset".
    """
    # 1. env var defaults
    effective = {k: fn() for k, fn in _ENV_DEFAULTS.get(channel_id, {}).items()}
    source_map = {k: ("env" if v else "unset") for k, v in effective.items()}

    # 2. DB overrides
    db = SessionLocal()
    try:
        row = db.query(ChannelConfigDB).filter(ChannelConfigDB.id == channel_id).first()
        if row:
            db_cfg = json.loads(row.config_json or "{}")
            for k, v in db_cfg.items():
                if v:
                    effective[k] = v
                    source_map[k] = "db"
    finally:
        db.close()

    return effective, source_map


def save_channel_config(channel_id: str, config: dict):
    db = SessionLocal()
    try:
        row = db.query(ChannelConfigDB).filter(ChannelConfigDB.id == channel_id).first()
        if row:
            existing = json.loads(row.config_json or "{}")
            # Don't overwrite masked values
            for k, v in config.items():
                if v and v != "••••••":
                    existing[k] = v
            row.config_json = json.dumps(existing)
            row.updated_at = datetime.now(timezone.utc)
        else:
            row = ChannelConfigDB(
                id=channel_id,
                config_json=json.dumps({k: v for k, v in config.items() if v and v != "••••••"}),
                updated_at=datetime.now(timezone.utc),
            )
            db.add(row)
        db.commit()
    finally:
        db.close()


# ── Main UI ──────────────────────────────────────────────────

st.title("🚀 發佈控制")

tab1, tab2, tab3 = st.tabs(["🔄 Pipeline 操作", "📡 RSS Sources", "⚙️ 渠道設定"])

# ── Tab 1: Pipeline ──────────────────────────────────────────
with tab1:
    col_fetch, col_summarize, col_publish = st.columns(3)

    with col_fetch:
        st.subheader("1️⃣ Fetch 文章")
        sources = list_sources()
        enabled_sources = [s for s in sources if s.enabled]
        st.caption(f"已啟用 {len(enabled_sources)} / {len(sources)} 個 Sources")

        force_refresh = st.checkbox("強制重新抓取（跳過去重）", key="force_refresh")

        if st.button("▶ 開始 Fetch", use_container_width=True, type="primary"):
            task_id = f"fetch-{uuid.uuid4().hex[:8]}"
            save_task_record(task_id, "fetch")
            with st.spinner("Fetching articles..."):
                try:
                    src_dicts = [
                        {"id": s.id, "url": s.url, "name": s.name, "enabled": s.enabled}
                        for s in enabled_sources
                    ]
                    orch = DigestOrchestrator()
                    result = asyncio.run(orch.run_fetch_pipeline(
                        sources=src_dicts,
                        force_refresh=force_refresh,
                    ))
                    update_task_record(task_id, "completed", result_json=json.dumps({
                        "articles_fetched": result.articles_fetched,
                    }))
                    st.success(f"✅ 抓取完成！新增 {result.articles_fetched} 篇文章")
                    if result.errors:
                        st.warning(f"部分錯誤：{result.errors}")
                except Exception as e:
                    update_task_record(task_id, "failed", error_json=json.dumps({"error": str(e)}))
                    st.error(f"❌ Fetch 失敗：{e}")

    with col_summarize:
        st.subheader("2️⃣ Summarize 摘要")
        pending = list_pending_articles()
        st.caption(f"待摘要：{len(pending)} 篇")

        if st.button("▶ 開始 Summarize", use_container_width=True, type="primary", disabled=len(pending) == 0):
            task_id = f"summarize-{uuid.uuid4().hex[:8]}"
            save_task_record(task_id, "summarize")
            progress_bar = st.progress(0)
            status_text = st.empty()

            try:
                from src.llm.gemini_summarizer import GeminiSummarizer
                summarizer = GeminiSummarizer()

                db = SessionLocal()
                try:
                    articles_to_summarize = db.query(ArticleDB).filter(
                        ArticleDB.publish_status == "pending"
                    ).all()

                    total = len(articles_to_summarize)
                    for i, article in enumerate(articles_to_summarize):
                        status_text.text(f"摘要中 {i+1}/{total}：{article.title[:40]}...")
                        progress_bar.progress((i + 1) / total)

                        result = asyncio.run(summarizer.summarize({
                            "title": article.title,
                            "content": article.content or "",
                        }))

                        article.summary = json.dumps({
                            "title_zh": result.title_zh,
                            "summary_zh": result.summary_zh,
                            "key_points": result.key_points,
                            "tags": result.tags,
                        })
                        article.tags = json.dumps(result.tags)
                        article.publish_status = "summarized"
                        article.summarized_at = datetime.now(timezone.utc)
                        db.commit()

                    update_task_record(task_id, "completed", result_json=json.dumps({"count": total}))
                    status_text.text("完成！")
                    st.success(f"✅ 摘要完成！處理 {total} 篇文章")
                finally:
                    db.close()

            except Exception as e:
                update_task_record(task_id, "failed", error_json=json.dumps({"error": str(e)}))
                st.error(f"❌ Summarize 失敗：{e}")

    with col_publish:
        st.subheader("3️⃣ Publish 發佈")
        summarized = list_summarized_articles()
        st.caption(f"待發佈：{len(summarized)} 篇")

        channel_options = ["telegram", "email", "line", "discord"]
        selected_channels = st.multiselect(
            "選擇發佈渠道",
            channel_options,
            default=["telegram"],
        )

        if st.button("▶ 開始 Publish", use_container_width=True, type="primary", disabled=len(summarized) == 0):
            task_id = f"publish-{uuid.uuid4().hex[:8]}"
            save_task_record(task_id, "publish")
            with st.spinner(f"Publishing to {selected_channels}..."):
                try:
                    article_dicts = []
                    for a in summarized:
                        try:
                            summary_data = json.loads(a.summary or "{}")
                        except Exception:
                            summary_data = {}
                        article_dicts.append({
                            "id": a.id,
                            "title": summary_data.get("title_zh") or a.title,
                            "summary": summary_data.get("summary_zh", ""),
                            "url": a.source_url or "",
                            "source": a.source or "",
                            "tags": json.loads(a.tags or "[]"),
                        })

                    orch = DigestOrchestrator()
                    result = asyncio.run(orch.run_publish_pipeline(
                        articles=article_dicts,
                        channels=selected_channels,
                    ))

                    # Update statuses
                    db = SessionLocal()
                    try:
                        for a in summarized:
                            a_row = db.query(ArticleDB).filter(ArticleDB.id == a.id).first()
                            if a_row:
                                a_row.publish_status = "published" if result.success else "failed"
                                a_row.published_at_channels = json.dumps({
                                    ch: datetime.now(timezone.utc).isoformat()
                                    for ch in selected_channels
                                })
                        db.commit()
                    finally:
                        db.close()

                    update_task_record(task_id, "completed", result_json=json.dumps({
                        "published_count": result.published_count,
                        "channels": selected_channels,
                    }))
                    if result.success:
                        st.success(f"✅ 發佈完成！{result.published_count} 次成功")
                    else:
                        st.warning(f"⚠️ 部分失敗：{result.errors}")
                except Exception as e:
                    update_task_record(task_id, "failed", error_json=json.dumps({"error": str(e)}))
                    st.error(f"❌ Publish 失敗：{e}")


# ── Tab 2: Sources ────────────────────────────────────────────
with tab2:
    st.subheader("📡 RSS Sources 管理")

    sources = list_sources()
    for src in sources:
        col_name, col_url, col_toggle, col_del = st.columns([2, 3, 1, 1])
        with col_name:
            st.write(f"**{src.name}**")
            st.caption(f"`{src.category}` · 每 {src.frequency_hours}h")
        with col_url:
            st.code(src.url, language=None)
        with col_toggle:
            enabled = st.toggle("啟用", value=src.enabled, key=f"toggle_{src.id}")
            if enabled != src.enabled:
                toggle_source(src.id, enabled)
                st.rerun()
        with col_del:
            if st.button("🗑️", key=f"del_{src.id}", help=f"刪除 {src.name}"):
                delete_source(src.id)
                st.rerun()

    st.divider()
    with st.expander("➕ 新增 RSS Source"):
        with st.form("add_source_form"):
            new_name = st.text_input("名稱", placeholder="Google AI Blog")
            new_url = st.text_input("RSS URL", placeholder="https://example.com/feed.xml")
            new_category = st.text_input("分類", value="general")
            new_freq = st.number_input("抓取頻率（小時）", min_value=1, max_value=168, value=24)
            submitted = st.form_submit_button("新增")
            if submitted:
                if new_name and new_url:
                    add_source(new_name, new_url, new_category, int(new_freq))
                    st.success(f"✅ 已新增：{new_name}")
                    st.rerun()
                else:
                    st.error("請填入名稱和 URL")


# ── Tab 3: Channel Config ─────────────────────────────────────
with tab3:
    st.subheader("⚙️ 渠道設定")

    CHANNEL_FIELDS = {
        "telegram": [
            ("bot_token", "Bot Token", "password", "透過 @BotFather 取得"),
            ("chat_id", "Chat ID", "text", "傳訊息給 Bot 後呼叫 getUpdates"),
        ],
        "email": [
            ("smtp_server", "SMTP Server", "text", "例：smtp.gmail.com"),
            ("smtp_port", "SMTP Port", "text", "預設 587"),
            ("username", "SMTP User", "text", "Gmail 帳號"),
            ("password", "SMTP Password", "password", "Gmail → 安全性 → 應用程式密碼"),
            ("to_address", "收件人 Email", "text", ""),
            ("from_name", "寄件人名稱", "text", "預設 Digest Agent"),
        ],
        "line": [
            ("channel_access_token", "Channel Access Token", "password", "LINE Developers Console"),
            ("to", "User ID", "text", "LINE Developers → Basic Settings → Your user ID"),
        ],
        "discord": [
            ("webhook_url", "Webhook URL", "text", "伺服器設定 → 整合 → Webhook"),
        ],
    }

    CHANNEL_LABELS = {
        "telegram": "📱 Telegram",
        "email": "📧 Email",
        "line": "💬 LINE",
        "discord": "🎮 Discord",
    }

    SOURCE_BADGE = {"db": "🔵 DB", "env": "🟢 .env", "unset": "⚪ 未設定"}

    for channel_id, label in CHANNEL_LABELS.items():
        effective, source_map = get_channel_config(channel_id)
        is_set = any(v for v in effective.values())
        status_icon = "✅" if is_set else "❌"

        with st.expander(f"{status_icon} {label}"):
            # Source legend
            badges = {}
            for k, src in source_map.items():
                badges.setdefault(src, []).append(k)
            legend = "  ".join(
                f"{SOURCE_BADGE[s]}: {', '.join(ks)}"
                for s, ks in badges.items() if s != "unset" or any(ks)
            )
            if legend:
                st.caption(f"設定來源 → {legend}")

            fields = CHANNEL_FIELDS[channel_id]

            with st.form(f"channel_form_{channel_id}"):
                new_values = {}
                for field_key, field_label, field_type, hint in fields:
                    current_val = effective.get(field_key, "")
                    src = source_map.get(field_key, "unset")
                    src_badge = SOURCE_BADGE[src]
                    full_hint = f"{src_badge}  {hint}".strip(" ")

                    # Mask password fields that are already set
                    display_val = "••••••" if current_val and field_type == "password" else current_val
                    if field_type == "password":
                        val = st.text_input(
                            field_label,
                            value=display_val,
                            type="password",
                            help=full_hint,
                            key=f"{channel_id}_{field_key}",
                        )
                    else:
                        val = st.text_input(
                            field_label,
                            value=display_val,
                            help=full_hint,
                            key=f"{channel_id}_{field_key}",
                        )
                    new_values[field_key] = val

                col_save, col_clear = st.columns([3, 1])
                with col_save:
                    if st.form_submit_button(f"💾 儲存到 DB（覆蓋 .env）", use_container_width=True):
                        save_channel_config(channel_id, new_values)
                        st.success("✅ 已儲存到 DB")
                        st.rerun()
                with col_clear:
                    if st.form_submit_button("🗑️ 清除 DB", use_container_width=True):
                        db = SessionLocal()
                        try:
                            row = db.query(ChannelConfigDB).filter(ChannelConfigDB.id == channel_id).first()
                            if row:
                                db.delete(row)
                                db.commit()
                        finally:
                            db.close()
                        st.info("DB 設定已清除，改用 .env")
                        st.rerun()
