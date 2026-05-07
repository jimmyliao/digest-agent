"""Tests for HTTP fallback in agents.stock.tools.news_tools.search_db_articles.

Covers:
- HTTP success (DIGEST_API_URL set, 200 → source=remote_api)
- HTTP 5xx (DIGEST_API_URL set, 500 → fallback to SQLite, source=local_db)
- HTTP timeout (DIGEST_API_URL set, requests.Timeout → fallback)
- DIGEST_API_URL unset → SQLite path, requests.get never called
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
import requests

from agents.stock.tools import news_tools


class _FakeQuery:
    """Stand-in for SQLAlchemy query() — supports .order_by(...).all()."""

    def order_by(self, *args, **kwargs):
        return self

    def all(self):
        return []


class _FakeSession:
    """Stand-in for SessionLocal() — supports .query(...).order_by().all() and .close()."""

    def query(self, *args, **kwargs):
        return _FakeQuery()

    def close(self):
        pass


@pytest.fixture()
def stub_sqlite(monkeypatch):
    """Patch src.models.database.SessionLocal so SQLite path returns no articles."""
    fake_session_local = MagicMock(return_value=_FakeSession())
    # The import is local inside search_db_articles; patch the module attribute
    # so the local `from src.models.database import SessionLocal, ArticleDB`
    # resolves to our fake.
    import src.models.database as db_module

    monkeypatch.setattr(db_module, "SessionLocal", fake_session_local)
    # ArticleDB is referenced but not used since query returns []; leave as-is.
    return fake_session_local


def test_http_success_returns_remote_api(monkeypatch):
    """Case 1: DIGEST_API_URL set, 200 OK → source=remote_api, articles populated."""
    monkeypatch.setenv("DIGEST_API_URL", "http://example.com")

    fake_response = MagicMock()
    fake_response.status_code = 200
    fake_response.json.return_value = {
        "articles": [
            {
                "title": "TSMC up",
                "content": "TSMC stock surged today...",
                "source": "yahoo-tw-stock",
                "source_url": "https://example.com/tsmc",
                "published_at": "2026-05-07T10:00:00Z",
            }
        ],
        "count": 1,
    }

    with patch.object(news_tools.requests, "get", return_value=fake_response) as mock_get:
        result = news_tools.search_db_articles("台積電", ticker="2330", limit=10)

    assert result["status"] == "success"
    assert result["source"] == "remote_api"
    assert len(result["articles"]) == 1
    assert result["articles"][0]["title"] == "TSMC up"
    assert result["total_matched"] == 1
    assert result["total_in_db"] == 1
    mock_get.assert_called_once()
    # Ensure URL was constructed correctly
    call_args, call_kwargs = mock_get.call_args
    assert call_args[0] == "http://example.com/api/articles"
    assert call_kwargs["params"]["company"] == "台積電"
    assert call_kwargs["params"]["limit"] == 10
    assert call_kwargs["timeout"] == 10


def test_http_500_falls_back_to_sqlite(monkeypatch, stub_sqlite):
    """Case 2: DIGEST_API_URL set but server returns 500 → fallback, source=local_db."""
    monkeypatch.setenv("DIGEST_API_URL", "http://example.com")

    fake_response = MagicMock()
    fake_response.status_code = 500
    fake_response.json.return_value = {}

    with patch.object(news_tools.requests, "get", return_value=fake_response):
        result = news_tools.search_db_articles("台積電")

    assert result["status"] == "success"
    assert result["source"] == "local_db"
    assert result["articles"] == []
    assert result["total_in_db"] == 0


def test_http_timeout_falls_back_to_sqlite(monkeypatch, stub_sqlite):
    """Case 3: DIGEST_API_URL set, requests raises Timeout → fallback to SQLite."""
    monkeypatch.setenv("DIGEST_API_URL", "http://example.com")

    with patch.object(news_tools.requests, "get", side_effect=requests.Timeout("boom")):
        result = news_tools.search_db_articles("台積電")

    assert result["status"] == "success"
    assert result["source"] == "local_db"
    assert result["articles"] == []


def test_no_env_var_uses_sqlite_directly(monkeypatch, stub_sqlite):
    """Case 4: DIGEST_API_URL unset → SQLite path; requests.get is never called."""
    monkeypatch.delenv("DIGEST_API_URL", raising=False)

    with patch.object(news_tools.requests, "get") as mock_get:
        result = news_tools.search_db_articles("台積電")

    assert result["status"] == "success"
    assert result["source"] == "local_db"
    mock_get.assert_not_called()
