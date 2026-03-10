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
    ScheduleConfigDB,
    SessionLocal,
    SourceDB,
    TaskRecordDB,
)
from src.orchestrator import DigestOrchestrator  # noqa: E402
from src.scheduler import is_running, sync_scheduler_state  # noqa: E402


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


def load_schedule_config(cfg_id: str) -> ScheduleConfigDB | None:
    db = SessionLocal()
    try:
        return db.query(ScheduleConfigDB).filter(ScheduleConfigDB.id == cfg_id).first()
    finally:
        db.close()


def save_schedule_config(cfg_id: str, enabled: bool, mode: str, interval_hours: int,
                          time_of_day: str, tz_name: str, channels: list):
    db = SessionLocal()
    try:
        row = db.query(ScheduleConfigDB).filter(ScheduleConfigDB.id == cfg_id).first()
        if row:
            row.enabled = enabled
            row.mode = mode
            row.interval_hours = interval_hours
            row.time_of_day = time_of_day
            row.timezone = tz_name
            row.channels = json.dumps(channels)
            row.updated_at = datetime.now(timezone.utc)
        else:
            row = ScheduleConfigDB(
                id=cfg_id, enabled=enabled, mode=mode,
                interval_hours=interval_hours, time_of_day=time_of_day,
                timezone=tz_name, channels=json.dumps(channels),
            )
            db.add(row)
        db.commit()
    finally:
        db.close()


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

tab1, tab2, tab3, tab4 = st.tabs(["🔄 Pipeline 操作", "📡 RSS Sources", "⚙️ 渠道設定", "⏰ 排程設定"])

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
        max_summarize = st.slider("摘要數量上限", min_value=1, max_value=min(len(pending), 50) if len(pending) > 0 else 10, value=min(len(pending), 1) if len(pending) > 0 else 1)

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
                    ).limit(max_summarize).all()

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


# ── Tab 4: Schedule Config ────────────────────────────────────
with tab4:
    st.subheader("⏰ 排程設定")
    if is_running():
        st.success("🟢 背景排程器執行中（每分鐘 check 一次）", icon=None)
    else:
        st.info("⚪ 背景排程器未啟動 — 啟用任一排程後自動啟動")

    SCHEDULE_DEFS = [
        ("fetch_summarize", "📥 Fetch + Summarize", False),
        ("publish",         "📤 Publish",           True),   # True = show channels selector
    ]

    for cfg_id, cfg_label, show_channels in SCHEDULE_DEFS:
        cfg = load_schedule_config(cfg_id)
        if cfg is None:
            st.warning(f"找不到 `{cfg_id}` 設定，請重新初始化 DB（make shell）")
            continue

        cur_channels = json.loads(cfg.channels or '["telegram"]')

        with st.expander(f"{cfg_label}", expanded=True):
            with st.form(f"sched_form_{cfg_id}"):
                c_enable, c_mode = st.columns([1, 2])
                with c_enable:
                    new_enabled = st.toggle("啟用排程", value=cfg.enabled, key=f"sched_en_{cfg_id}")
                with c_mode:
                    mode_opts = ["interval", "cron"]
                    mode_idx = mode_opts.index(cfg.mode) if cfg.mode in mode_opts else 0
                    new_mode = st.radio(
                        "排程模式",
                        mode_opts,
                        index=mode_idx,
                        format_func=lambda x: "每隔 N 小時" if x == "interval" else "每天固定時間",
                        horizontal=True,
                        key=f"sched_mode_{cfg_id}",
                    )

                c_hours, c_time, c_tz = st.columns(3)
                with c_hours:
                    new_interval = st.number_input(
                        "間隔（小時）",
                        min_value=1, max_value=168,
                        value=cfg.interval_hours,
                        disabled=(new_mode != "interval"),
                        key=f"sched_hours_{cfg_id}",
                    )
                with c_time:
                    new_time = st.text_input(
                        "固定時間（HH:MM）",
                        value=cfg.time_of_day or "08:00",
                        disabled=(new_mode != "cron"),
                        key=f"sched_time_{cfg_id}",
                        placeholder="08:00",
                    )
                with c_tz:
                    new_tz = st.text_input(
                        "時區",
                        value=cfg.timezone or "Asia/Taipei",
                        key=f"sched_tz_{cfg_id}",
                    )

                if show_channels:
                    new_channels = st.multiselect(
                        "發佈渠道",
                        ["telegram", "email", "line", "discord"],
                        default=cur_channels,
                        key=f"sched_ch_{cfg_id}",
                    )
                else:
                    new_channels = []

                # Display last_run / next_run
                info_col1, info_col2 = st.columns(2)
                with info_col1:
                    last_str = cfg.last_run.strftime("%Y-%m-%d %H:%M") if cfg.last_run else "—"
                    st.caption(f"上次執行：{last_str}")
                with info_col2:
                    next_str = cfg.next_run.strftime("%Y-%m-%d %H:%M") if cfg.next_run else "—"
                    st.caption(f"下次執行：{next_str}")

                if st.form_submit_button("💾 儲存排程設定", use_container_width=True, type="primary"):
                    save_schedule_config(
                        cfg_id,
                        enabled=new_enabled,
                        mode=new_mode,
                        interval_hours=int(new_interval),
                        time_of_day=new_time,
                        tz_name=new_tz,
                        channels=new_channels if show_channels else [],
                    )
                    sync_scheduler_state()  # 有啟用才 start，全停用才 stop
                    st.success("✅ 排程設定已儲存")
                    st.rerun()

    st.divider()
    st.subheader("▶ 立即執行完整 Pipeline")
    st.caption("手動觸發：依序執行 Fetch → Summarize → Publish（使用排程中設定的發佈渠道）")

    publish_cfg = load_schedule_config("publish")
    manual_channels = json.loads(publish_cfg.channels or '["telegram"]') if publish_cfg else ["telegram"]

    override_channels = st.multiselect(
        "本次發佈渠道（覆蓋排程設定）",
        ["telegram", "email", "line", "discord"],
        default=manual_channels,
        key="manual_run_channels",
    )

    if st.button("🚀 立即執行 Fetch → Summarize → Publish", type="primary", use_container_width=True,
                 disabled=not override_channels):
        task_id = f"full-{uuid.uuid4().hex[:8]}"

        # Step 1: Fetch
        with st.status("執行中...", expanded=True) as status_box:
            st.write("**Step 1/3** — Fetch 文章")
            try:
                sources_enabled = [
                    {"id": s.id, "url": s.url, "name": s.name, "enabled": s.enabled}
                    for s in list_sources() if s.enabled
                ]
                orch = DigestOrchestrator()
                fetch_result = asyncio.run(orch.run_fetch_pipeline(sources=sources_enabled))
                st.write(f"✅ Fetch 完成：新增 {fetch_result.articles_fetched} 篇")
            except Exception as e:
                st.error(f"❌ Fetch 失敗：{e}")
                status_box.update(label="Pipeline 失敗", state="error")
                st.stop()

            # Step 2: Summarize
            st.write("**Step 2/3** — Summarize 摘要")
            try:
                from src.llm.gemini_summarizer import GeminiSummarizer
                summarizer = GeminiSummarizer()
                db = SessionLocal()
                summarized_count = 0
                try:
                    pending_rows = db.query(ArticleDB).filter(
                        ArticleDB.publish_status == "pending"
                    ).all()
                    for article in pending_rows:
                        result_sum = asyncio.run(summarizer.summarize({
                            "title": article.title,
                            "content": article.content or "",
                        }))
                        article.summary = json.dumps({
                            "title_zh": result_sum.title_zh,
                            "summary_zh": result_sum.summary_zh,
                            "key_points": result_sum.key_points,
                            "tags": result_sum.tags,
                        })
                        article.tags = json.dumps(result_sum.tags)
                        article.publish_status = "summarized"
                        article.summarized_at = datetime.now(timezone.utc)
                        db.commit()
                        summarized_count += 1
                finally:
                    db.close()
                st.write(f"✅ Summarize 完成：處理 {summarized_count} 篇")
            except Exception as e:
                st.error(f"❌ Summarize 失敗：{e}")
                status_box.update(label="Pipeline 失敗（Fetch 已完成）", state="error")
                st.stop()

            # Step 3: Publish
            st.write(f"**Step 3/3** — Publish → {override_channels}")
            try:
                db = SessionLocal()
                try:
                    summarized_rows = db.query(ArticleDB).filter(
                        ArticleDB.publish_status == "summarized"
                    ).all()
                    article_dicts = []
                    for a in summarized_rows:
                        try:
                            sd = json.loads(a.summary or "{}")
                        except Exception:
                            sd = {}
                        article_dicts.append({
                            "id": a.id,
                            "title": sd.get("title_zh") or a.title,
                            "summary": sd.get("summary_zh", ""),
                            "url": a.source_url or "",
                            "source": a.source or "",
                            "tags": json.loads(a.tags or "[]"),
                        })
                finally:
                    db.close()

                pub_result = asyncio.run(orch.run_publish_pipeline(
                    articles=article_dicts, channels=override_channels,
                ))

                db = SessionLocal()
                try:
                    for ad in article_dicts:
                        row = db.query(ArticleDB).filter(ArticleDB.id == ad["id"]).first()
                        if row:
                            row.publish_status = "published" if pub_result.success else "failed"
                            row.published_at_channels = json.dumps({
                                ch: datetime.now(timezone.utc).isoformat()
                                for ch in override_channels
                            })
                    db.commit()

                    # Update schedule last_run
                    for cfg_id_upd in ("fetch_summarize", "publish"):
                        sc = db.query(ScheduleConfigDB).filter(
                            ScheduleConfigDB.id == cfg_id_upd
                        ).first()
                        if sc:
                            sc.last_run = datetime.now(timezone.utc)
                    db.commit()
                finally:
                    db.close()

                st.write(f"✅ Publish 完成：{pub_result.published_count} 次成功")
            except Exception as e:
                st.error(f"❌ Publish 失敗：{e}")
                status_box.update(label="Pipeline 失敗（Fetch+Summarize 已完成）", state="error")
                st.stop()

            status_box.update(label="✅ Full Pipeline 完成！", state="complete")
