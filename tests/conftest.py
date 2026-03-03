"""Shared test fixtures for Streamlit / standalone tests."""

import json
import uuid
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from src.models.database import ArticleDB, Base, TaskRecordDB


@pytest.fixture()
def db_session():
    """Create an in-memory SQLite database for each test.

    Uses StaticPool so all connections share the same in-memory DB.
    """
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    TestingSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = TestingSession()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture()
def sample_articles(db_session):
    """Insert a set of sample articles into the test DB."""
    now = datetime.now(timezone.utc)
    articles = []
    sources = ["google-ai", "google-cloud", "tech-news"]
    statuses = ["pending", "summarized", "published"]

    for i in range(10):
        art = ArticleDB(
            id=str(uuid.uuid4()),
            title=f"Test Article {i}: AI Breakthrough #{i}",
            content=f"<p>Content of article {i} about technology.</p>",
            summary=f"Summary of article {i}" if statuses[i % 3] != "pending" else None,
            source=sources[i % 3],
            source_url=f"https://example.com/article-{i}",
            url_hash=f"hash{i:04d}",
            content_hash=f"chash{i:04d}",
            published_at=now - timedelta(days=i),
            summarized_at=(now - timedelta(days=i, hours=-1)) if statuses[i % 3] != "pending" else None,
            tags=json.dumps(["AI", "Tech"]),
            language="en",
            publish_status=statuses[i % 3],
            publish_channels=json.dumps(["email"]) if statuses[i % 3] == "published" else "[]",
            published_at_channels="{}",
            metadata_json="{}",
            created_at=now,
        )
        db_session.add(art)
        articles.append(art)

    db_session.commit()
    return articles


@pytest.fixture()
def sample_task(db_session):
    """Insert a sample task record."""
    now = datetime.now(timezone.utc)
    task = TaskRecordDB(
        task_id="test-task-001",
        task_type="fetch",
        status="completed",
        progress_completed=3,
        progress_total=3,
        started_at=now - timedelta(minutes=5),
        completed_at=now,
        result_json=json.dumps({
            "articles_fetched": 10,
            "sources_processed": 3,
            "sources_failed": 0,
        }),
    )
    db_session.add(task)
    db_session.commit()
    return task
