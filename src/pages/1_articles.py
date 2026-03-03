"""文章列表頁面 - 瀏覽、篩選、管理文章."""

import json
from datetime import datetime

import streamlit as st

st.set_page_config(page_title="文章列表 - Digest Agent", page_icon="📰", layout="wide")

from src.models.database import ArticleDB, SessionLocal  # noqa: E402


def load_articles(status_filter=None, tag_filter=None, sort_by="created_at", sort_order="desc"):
    db = SessionLocal()
    try:
        query = db.query(ArticleDB)
        if status_filter and status_filter != "全部":
            query = query.filter(ArticleDB.publish_status == status_filter)

        col = getattr(ArticleDB, sort_by, ArticleDB.created_at)
        if sort_order == "desc":
            query = query.order_by(col.desc())
        else:
            query = query.order_by(col.asc())

        articles = query.all()

        if tag_filter and tag_filter != "全部":
            articles = [
                a for a in articles
                if tag_filter in json.loads(a.tags or "[]")
            ]

        return articles
    finally:
        db.close()


def collect_all_tags():
    db = SessionLocal()
    try:
        rows = db.query(ArticleDB.tags).all()
        tags = set()
        for (t,) in rows:
            try:
                tags.update(json.loads(t or "[]"))
            except Exception:
                pass
        return sorted(tags)
    finally:
        db.close()


def update_article_status(article_id: str, new_status: str):
    db = SessionLocal()
    try:
        article = db.query(ArticleDB).filter(ArticleDB.id == article_id).first()
        if article:
            article.publish_status = new_status
            db.commit()
    finally:
        db.close()


# --- UI ---
st.title("📰 文章列表")

# Filters
col1, col2, col3, col4 = st.columns([2, 2, 2, 1])
with col1:
    status_options = ["全部", "pending", "summarized", "published", "failed"]
    status_filter = st.selectbox("狀態篩選", status_options)
with col2:
    all_tags = ["全部"] + collect_all_tags()
    tag_filter = st.selectbox("Tag 篩選", all_tags)
with col3:
    sort_options = {"建立時間": "created_at", "發佈時間": "published_at", "標題": "title"}
    sort_label = st.selectbox("排序欄位", list(sort_options.keys()))
    sort_by = sort_options[sort_label]
with col4:
    sort_order = st.radio("順序", ["desc", "asc"], format_func=lambda x: "↓ 新→舊" if x == "desc" else "↑ 舊→新")

per_page = st.selectbox("每頁筆數", [20, 50, 100], index=0)

# Load
articles = load_articles(status_filter, tag_filter, sort_by, sort_order)
total = len(articles)

st.caption(f"共 {total} 篇文章（篩選後）")

if not articles:
    st.info("沒有符合條件的文章。請先到「發佈控制」頁面 Fetch 文章。")
else:
    page_count = (total + per_page - 1) // per_page
    page = st.number_input("頁碼", min_value=1, max_value=max(1, page_count), value=1, step=1) - 1
    page_articles = articles[page * per_page:(page + 1) * per_page]

    # Batch operations
    with st.expander("🔧 批次操作"):
        batch_col1, batch_col2 = st.columns(2)
        with batch_col1:
            if st.button("標記全頁為 pending", use_container_width=True):
                for a in page_articles:
                    update_article_status(a.id, "pending")
                st.rerun()
        with batch_col2:
            if st.button("標記全頁為 published", use_container_width=True):
                for a in page_articles:
                    update_article_status(a.id, "published")
                st.rerun()

    # Article table
    for article in page_articles:
        tags = json.loads(article.tags or "[]")
        status_icon = {
            "pending": "⏳",
            "summarized": "✅",
            "published": "📤",
            "failed": "⚠️",
        }.get(article.publish_status, "❓")

        with st.container():
            col_main, col_action = st.columns([5, 1])
            with col_main:
                st.markdown(f"**{status_icon} {article.title}**")
                meta_parts = [f"來源: {article.source or '—'}"]
                if article.published_at:
                    try:
                        dt = article.published_at
                        if hasattr(dt, 'strftime'):
                            meta_parts.append(dt.strftime("%Y-%m-%d %H:%M"))
                    except Exception:
                        pass
                meta_parts.append(f"`{article.publish_status}`")
                if tags:
                    tag_chips = " ".join([f"`{t}`" for t in tags[:5]])
                    meta_parts.append(tag_chips)
                st.caption(" · ".join(meta_parts))

                if article.summary:
                    with st.expander("摘要"):
                        try:
                            summary_data = json.loads(article.summary)
                            if isinstance(summary_data, dict):
                                st.write(summary_data.get("summary_zh", article.summary))
                                kp = summary_data.get("key_points", [])
                                if kp:
                                    for point in kp:
                                        st.write(f"• {point}")
                            else:
                                st.write(article.summary)
                        except Exception:
                            st.write(article.summary)

            with col_action:
                new_status = st.selectbox(
                    "狀態",
                    ["pending", "summarized", "published", "failed"],
                    index=["pending", "summarized", "published", "failed"].index(
                        article.publish_status if article.publish_status in ["pending", "summarized", "published", "failed"] else "pending"
                    ),
                    key=f"status_{article.id}",
                    label_visibility="collapsed",
                )
                if new_status != article.publish_status:
                    update_article_status(article.id, new_status)
                    st.rerun()

                if article.source_url:
                    st.link_button("🔗", article.source_url, use_container_width=True)

            st.divider()
