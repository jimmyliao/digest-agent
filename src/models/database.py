import os
from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Integer,
    String,
    Text,
    create_engine,
)
from sqlalchemy.orm import DeclarativeBase, sessionmaker

DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///./data/digest.db")

connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


class ArticleDB(Base):
    __tablename__ = "articles"

    id = Column(String, primary_key=True)
    title = Column(String, nullable=False)
    content = Column(Text, default="")
    summary = Column(Text, nullable=True)
    source = Column(String, default="")
    source_url = Column(String, unique=True)
    url_hash = Column(String, index=True)
    content_hash = Column(String, index=True)
    published_at = Column(DateTime, nullable=True)
    summarized_at = Column(DateTime, nullable=True)
    tags = Column(Text, default="[]")  # JSON stored as text for SQLite
    language = Column(String, default="en")
    publish_status = Column(String, default="pending")
    publish_channels = Column(Text, default="[]")
    published_at_channels = Column(Text, default="{}")
    error_log = Column(Text, nullable=True)
    metadata_json = Column(Text, default="{}")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class TaskRecordDB(Base):
    __tablename__ = "task_records"

    task_id = Column(String, primary_key=True)
    task_type = Column(String)  # fetch / summarize / publish
    status = Column(String, default="queued")  # queued / running / completed / failed
    progress_completed = Column(Integer, default=0)
    progress_total = Column(Integer, default=0)
    started_at = Column(DateTime)
    completed_at = Column(DateTime, nullable=True)
    result_json = Column(Text, nullable=True)  # JSON
    error_json = Column(Text, nullable=True)  # JSON


class SourceDB(Base):
    __tablename__ = "sources"
    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    url = Column(String, nullable=False, unique=True)
    type = Column(String, default="rss")
    enabled = Column(Boolean, default=True)
    frequency_hours = Column(Integer, default=24)
    category = Column(String, default="general")
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class ChannelConfigDB(Base):
    __tablename__ = "channel_configs"

    id = Column(String, primary_key=True)  # "email" | "telegram" | "line" | "discord"
    config_json = Column(Text, default="{}")  # channel credentials stored as JSON
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class ScheduleConfigDB(Base):
    __tablename__ = "schedule_configs"

    id = Column(String, primary_key=True)  # "fetch_summarize" | "publish"
    enabled = Column(Boolean, default=False)
    mode = Column(String, default="interval")  # "interval" | "cron"
    interval_hours = Column(Integer, default=24)
    time_of_day = Column(String, default="08:00")  # HH:MM for cron mode
    timezone = Column(String, default="Asia/Taipei")
    channels = Column(Text, default='["telegram"]')  # JSON list — publish only
    last_run = Column(DateTime(timezone=True), nullable=True)
    next_run = Column(DateTime(timezone=True), nullable=True)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


def get_db():
    """FastAPI dependency — yields a database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Create all tables if they don't exist, and seed default data."""
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        if db.query(SourceDB).count() == 0:
            defaults = [
                # Google 技術 Blog
                SourceDB(id="google-official", name="Google Official Blog", url="https://blog.google/rss/", type="rss", enabled=False, frequency_hours=6, category="official"),
                SourceDB(id="google-cloud", name="Google Cloud Blog", url="https://cloud.google.com/feeds/gcp-release-notes.xml", type="rss", enabled=True, frequency_hours=12, category="cloud"),
                SourceDB(id="google-research", name="Google Research Blog", url="https://blog.research.google/feeds/posts/default", type="rss", enabled=False, frequency_hours=24, category="research"),
                # 台股財經 — Phase 4 個股分析 news_collector 共用
                SourceDB(id="yahoo-tw-stock", name="Yahoo 台灣股市", url="https://tw.stock.yahoo.com/rss", type="rss", enabled=True, frequency_hours=6, category="finance_tw"),
                SourceDB(id="twse-news", name="TWSE 台灣證交所", url="https://www.twse.com.tw/rwd/zh/news/feed?type=rss", type="rss", enabled=True, frequency_hours=6, category="finance_tw"),
                SourceDB(id="technews-finance", name="TechNews 科技新報", url="https://technews.tw/feed/", type="rss", enabled=True, frequency_hours=12, category="finance_tw"),
            ]
            db.add_all(defaults)
            db.commit()
        if db.query(ScheduleConfigDB).count() == 0:
            db.add_all([
                ScheduleConfigDB(
                    id="fetch_summarize",
                    enabled=False,
                    mode="interval",
                    interval_hours=24,
                    time_of_day="08:00",
                    timezone="Asia/Taipei",
                    channels='[]',
                ),
                ScheduleConfigDB(
                    id="publish",
                    enabled=False,
                    mode="cron",
                    interval_hours=24,
                    time_of_day="08:00",
                    timezone="Asia/Taipei",
                    channels='["telegram"]',
                ),
            ])
            db.commit()
    finally:
        db.close()
